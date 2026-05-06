from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError
from .paths import normalize_relative_path


@dataclass(frozen=True)
class OverlayProject:
    name: str
    root: Path
    overlay_dir: Path
    files: tuple[str, ...]
    description: str | None = None

    def source_for(self, relative_path: str) -> Path:
        return self.overlay_dir / relative_path


def load_project(source_root: Path, project_name: str) -> OverlayProject:
    projects_dir = source_root / "projects"
    project_root = projects_dir / project_name
    config_path = project_root / "overlay.toml"

    if not config_path.is_file():
        raise ConfigError(f"overlay.toml not found: {config_path}")

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    configured_name = data.get("project")
    if configured_name != project_name:
        raise ConfigError(
            f"project value must be {project_name!r}, got {configured_name!r}"
        )

    raw_files = data.get("files")
    if not isinstance(raw_files, list):
        raise ConfigError("files must be a list of relative paths")

    files: list[str] = []
    seen: set[str] = set()
    for raw_path in raw_files:
        relative_path = normalize_relative_path(raw_path)
        if relative_path in seen:
            raise ConfigError(f"duplicate overlay path: {relative_path}")
        seen.add(relative_path)
        files.append(relative_path)

    overlay_dir = project_root / "overlay"
    if not overlay_dir.is_dir():
        raise ConfigError(f"overlay directory not found: {overlay_dir}")

    for relative_path in files:
        source_path = overlay_dir / relative_path
        if not source_path.is_file():
            raise ConfigError(
                f"overlay file listed in overlay.toml is missing: {source_path}"
            )

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        raise ConfigError("description must be a string when provided")

    return OverlayProject(
        name=project_name,
        root=project_root,
        overlay_dir=overlay_dir,
        files=tuple(files),
        description=description,
    )
