from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .git import find_git_dir


@dataclass(frozen=True)
class ExcludeFile:
    path: Path
    lines: tuple[str, ...]

    @property
    def entries(self) -> frozenset[str]:
        return frozenset(line.strip() for line in self.lines if _is_managed_entry(line))

    def has(self, relative_path: str) -> bool:
        return relative_path in self.entries


def _is_managed_entry(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def read_exclude(target_repo: Path) -> ExcludeFile:
    git_dir = find_git_dir(target_repo)
    exclude_path = git_dir / "info" / "exclude"
    if not exclude_path.exists():
        return ExcludeFile(path=exclude_path, lines=tuple())
    return ExcludeFile(
        path=exclude_path,
        lines=tuple(exclude_path.read_text(encoding="utf-8").splitlines()),
    )


def add_exclude_entries(
    target_repo: Path,
    relative_paths: list[str],
    *,
    dry_run: bool,
) -> list[str]:
    exclude_file = read_exclude(target_repo)
    existing = exclude_file.entries
    missing: list[str] = []
    seen: set[str] = set()
    for path in relative_paths:
        if path not in existing and path not in seen:
            missing.append(path)
            seen.add(path)
    if not missing or dry_run:
        return missing

    exclude_file.path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "\n" if exclude_file.path.exists() and exclude_file.path.stat().st_size else ""
    with exclude_file.path.open("a", encoding="utf-8") as handle:
        handle.write(prefix)
        handle.write("# contribution-overlays\n")
        for path in missing:
            handle.write(f"{path}\n")
    return missing


def remove_exclude_entries(
    target_repo: Path,
    relative_paths: set[str],
    *,
    dry_run: bool,
) -> list[str]:
    if not relative_paths:
        return []

    exclude_file = read_exclude(target_repo)
    existing = exclude_file.entries
    removed = sorted(relative_paths & set(existing))
    if not removed or dry_run:
        return removed

    remove_set = set(removed)
    new_lines = [
        line for line in exclude_file.lines if line.strip() not in remove_set
    ]

    if new_lines:
        exclude_file.path.parent.mkdir(parents=True, exist_ok=True)
        exclude_file.path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    elif exclude_file.path.exists():
        exclude_file.path.write_text("", encoding="utf-8")
    return removed
