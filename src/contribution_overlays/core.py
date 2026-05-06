from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import OverlayProject
from .errors import TargetRepoError
from .exclude import add_exclude_entries, read_exclude, remove_exclude_entries
from .git import read_git_state
from .paths import target_path_for
from .status import OverlayStatus


@dataclass(frozen=True)
class PathStatus:
    relative_path: str
    status: OverlayStatus
    target_path: Path
    source_path: Path | None = None
    detail: str | None = None


@dataclass(frozen=True)
class OperationResult:
    statuses: tuple[PathStatus, ...]
    actions: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _same_symlink_target(link_path: Path, expected_path: Path) -> bool:
    try:
        link_target = os.readlink(link_path)
    except OSError:
        return False
    link_target_path = Path(link_target)
    if not link_target_path.is_absolute():
        link_target_path = link_path.parent / link_target_path
    return link_target_path.resolve(strict=False) == expected_path.resolve(strict=True)


def _is_broken_symlink(path: Path) -> bool:
    return path.is_symlink() and not path.exists()


def scan_project(target_repo: Path, project: OverlayProject) -> tuple[PathStatus, ...]:
    exclude_file = read_exclude(target_repo)
    git_state = read_git_state(target_repo, project.files)
    statuses: list[PathStatus] = []

    for relative_path in project.files:
        target_path = target_path_for(target_repo, relative_path)
        source_path = project.source_for(relative_path)
        is_excluded = exclude_file.has(relative_path)

        if relative_path in git_state.staged:
            statuses.append(
                PathStatus(
                    relative_path,
                    OverlayStatus.STAGED,
                    target_path,
                    source_path,
                    "path is staged in target repository",
                )
            )
            continue

        if relative_path in git_state.tracked:
            statuses.append(
                PathStatus(
                    relative_path,
                    OverlayStatus.TRACKED,
                    target_path,
                    source_path,
                    "path is tracked in target repository",
                )
            )
            continue

        if not target_path.exists() and not target_path.is_symlink():
            statuses.append(
                PathStatus(
                    relative_path,
                    OverlayStatus.MISSING,
                    target_path,
                    source_path,
                )
            )
            if not is_excluded:
                statuses.append(
                    PathStatus(
                        relative_path,
                        OverlayStatus.IGNORE_MISSING,
                        target_path,
                        source_path,
                    )
                )
        elif _is_broken_symlink(target_path):
            statuses.append(
                PathStatus(
                    relative_path,
                    OverlayStatus.BROKEN,
                    target_path,
                    source_path,
                )
            )
            if not is_excluded:
                statuses.append(
                    PathStatus(
                        relative_path,
                        OverlayStatus.IGNORE_MISSING,
                        target_path,
                        source_path,
                    )
                )
        elif target_path.is_symlink():
            if _same_symlink_target(target_path, source_path):
                if is_excluded:
                    statuses.append(
                        PathStatus(
                            relative_path,
                            OverlayStatus.OK,
                            target_path,
                            source_path,
                        )
                    )
                else:
                    statuses.append(
                        PathStatus(
                            relative_path,
                            OverlayStatus.IGNORE_MISSING,
                            target_path,
                            source_path,
                        )
                    )
            else:
                statuses.append(
                    PathStatus(
                        relative_path,
                        OverlayStatus.WRONG,
                        target_path,
                        source_path,
                        "symlink points to another target",
                    )
                )
                if not is_excluded:
                    statuses.append(
                        PathStatus(
                            relative_path,
                            OverlayStatus.IGNORE_MISSING,
                            target_path,
                            source_path,
                        )
                    )
        else:
            statuses.append(
                PathStatus(
                    relative_path,
                    OverlayStatus.CONFLICT,
                    target_path,
                    source_path,
                    "regular file or directory already exists",
                )
            )

    return tuple(statuses)


def find_extra_symlinks(target_repo: Path, project: OverlayProject) -> tuple[PathStatus, ...]:
    overlay_root = project.overlay_dir.resolve()
    declared = set(project.files)
    extras: list[PathStatus] = []

    for root, dirs, files in os.walk(target_repo):
        root_path = Path(root)
        if root_path == target_repo / ".git":
            dirs[:] = []
            continue
        if ".git" in dirs:
            dirs.remove(".git")

        names = [*dirs, *files]
        for name in names:
            candidate = root_path / name
            if not candidate.is_symlink():
                continue
            try:
                relative_path = candidate.relative_to(target_repo).as_posix()
            except ValueError:
                continue
            if relative_path in declared:
                continue

            try:
                raw_target = os.readlink(candidate)
            except OSError:
                continue
            target = Path(raw_target)
            if not target.is_absolute():
                target = candidate.parent / target
            target_resolved = target.resolve(strict=False)
            try:
                target_resolved.relative_to(overlay_root)
            except ValueError:
                continue

            extras.append(
                PathStatus(
                    relative_path=relative_path,
                    status=OverlayStatus.EXTRA,
                    target_path=candidate,
                    source_path=target_resolved,
                    detail="symlink points into this project's overlay directory",
                )
            )

    return tuple(sorted(extras, key=lambda item: item.relative_path))


def check_overlay(
    target_repo: Path,
    project: OverlayProject,
    *,
    include_extra: bool = True,
) -> OperationResult:
    statuses = list(scan_project(target_repo, project))
    if include_extra:
        statuses.extend(find_extra_symlinks(target_repo, project))
    return OperationResult(statuses=tuple(statuses), actions=tuple(), errors=tuple())


def _create_or_replace_symlink(
    status: PathStatus,
    *,
    dry_run: bool,
    replace_existing_symlink: bool = False,
) -> str:
    source_path = status.source_path
    if source_path is None:
        raise TargetRepoError(f"missing source path for {status.relative_path}")

    action = f"link {status.relative_path} -> {source_path}"
    if dry_run:
        return action

    status.target_path.parent.mkdir(parents=True, exist_ok=True)
    if status.target_path.is_symlink():
        if replace_existing_symlink or _is_broken_symlink(status.target_path):
            status.target_path.unlink()
        else:
            raise TargetRepoError(f"refusing to replace symlink: {status.target_path}")
    status.target_path.symlink_to(source_path)
    return action


def sync_overlay(
    target_repo: Path,
    project: OverlayProject,
    *,
    dry_run: bool = False,
    prune: bool = False,
    clean_exclude: bool = False,
    replace_wrong: bool = False,
) -> OperationResult:
    statuses = list(scan_project(target_repo, project))
    actions: list[str] = []
    errors: list[str] = []

    for status in statuses:
        if status.status in {OverlayStatus.TRACKED, OverlayStatus.STAGED}:
            errors.append(
                f"{status.status.value}: {status.relative_path}: protected by target Git"
            )
        elif status.status == OverlayStatus.CONFLICT:
            errors.append(
                f"CONFLICT: {status.relative_path}: regular file or directory exists"
            )

    if errors:
        return OperationResult(tuple(statuses), tuple(actions), tuple(errors))

    replaced_wrong: set[str] = set()

    for status in statuses:
        if status.status in {OverlayStatus.MISSING, OverlayStatus.BROKEN}:
            actions.append(_create_or_replace_symlink(status, dry_run=dry_run))
        elif status.status == OverlayStatus.IGNORE_MISSING:
            continue
        elif status.status == OverlayStatus.WRONG:
            if replace_wrong:
                actions.append(
                    _create_or_replace_symlink(
                        status,
                        dry_run=dry_run,
                        replace_existing_symlink=True,
                    )
                )
                replaced_wrong.add(status.relative_path)
            else:
                errors.append(
                    f"WRONG: {status.relative_path}: use --replace-wrong to update"
                )

    missing_exclude = [
        status.relative_path
        for status in statuses
        if status.status
        in {
            OverlayStatus.OK,
            OverlayStatus.MISSING,
            OverlayStatus.BROKEN,
            OverlayStatus.IGNORE_MISSING,
        }
        or status.relative_path in replaced_wrong
    ]
    added_exclude = add_exclude_entries(
        target_repo,
        missing_exclude,
        dry_run=dry_run,
    )
    actions.extend(f"exclude {path}" for path in added_exclude)

    extra_statuses: tuple[PathStatus, ...] = tuple()
    if prune or clean_exclude:
        extra_statuses = find_extra_symlinks(target_repo, project)
        statuses.extend(extra_statuses)

    if prune:
        for extra in extra_statuses:
            actions.append(f"unlink extra {extra.relative_path}")
            if not dry_run:
                extra.target_path.unlink()
    elif extra_statuses:
        for extra in extra_statuses:
            errors.append(f"EXTRA: {extra.relative_path}: use --prune to remove")

    if clean_exclude:
        active_files = set(project.files)
        extra_files = {extra.relative_path for extra in extra_statuses}
        existing = set(read_exclude(target_repo).entries)
        remove_candidates = (existing - active_files) & extra_files
        removed = remove_exclude_entries(
            target_repo,
            remove_candidates,
            dry_run=dry_run,
        )
        actions.extend(f"remove exclude {path}" for path in removed)

    return OperationResult(tuple(statuses), tuple(actions), tuple(errors))


def unlink_overlay(
    target_repo: Path,
    project: OverlayProject,
    *,
    dry_run: bool = False,
    clean_exclude: bool = False,
) -> OperationResult:
    statuses = list(scan_project(target_repo, project))
    actions: list[str] = []
    errors: list[str] = []

    for status in statuses:
        if status.status in {OverlayStatus.TRACKED, OverlayStatus.STAGED}:
            errors.append(
                f"{status.status.value}: {status.relative_path}: protected by target Git"
            )
            continue
        if status.target_path.is_symlink():
            actions.append(f"unlink {status.relative_path}")
            if not dry_run:
                status.target_path.unlink()
        elif status.status == OverlayStatus.CONFLICT:
            errors.append(
                f"CONFLICT: {status.relative_path}: refusing to delete regular file or directory"
            )

    if clean_exclude:
        removed = remove_exclude_entries(
            target_repo,
            set(project.files),
            dry_run=dry_run,
        )
        actions.extend(f"remove exclude {path}" for path in removed)

    return OperationResult(tuple(statuses), tuple(actions), tuple(errors))
