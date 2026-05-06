from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import ConfigError, TargetRepoError


def normalize_relative_path(raw: object) -> str:
    if not isinstance(raw, str):
        raise ConfigError(f"file path must be a string: {raw!r}")
    if raw == "":
        raise ConfigError("file path must not be empty")

    path = PurePosixPath(raw)
    if path.is_absolute():
        raise ConfigError(f"absolute paths are not allowed: {raw}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ConfigError(f"'.', '..', and empty path segments are not allowed: {raw}")
    if path.parts[0] == ".git":
        raise ConfigError(f"paths under .git are not allowed: {raw}")

    return path.as_posix()


def ensure_inside(base: Path, candidate: Path) -> Path:
    base_resolved = base.resolve()
    parent_resolved = candidate.parent.resolve(strict=False)
    candidate_resolved = parent_resolved / candidate.name
    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise TargetRepoError(f"path escapes target repository: {candidate}") from exc
    return candidate_resolved


def target_path_for(target_repo: Path, relative_path: str) -> Path:
    target = target_repo / relative_path
    ensure_inside(target_repo, target)
    return target
