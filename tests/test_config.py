from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contribution_overlays.config import load_project
from contribution_overlays.errors import ConfigError


class ConfigTests(unittest.TestCase):
    def test_loads_valid_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "projects" / "owner-repo"
            (project / "overlay" / "docs").mkdir(parents=True)
            (project / "overlay" / "AGENTS.md").write_text("root\n", encoding="utf-8")
            (project / "overlay" / "docs" / "AGENTS.md").write_text(
                "docs\n",
                encoding="utf-8",
            )
            (project / "overlay.toml").write_text(
                'project = "owner-repo"\nfiles = ["AGENTS.md", "docs/AGENTS.md"]\n',
                encoding="utf-8",
            )

            loaded = load_project(root, "owner-repo")

            self.assertEqual(loaded.name, "owner-repo")
            self.assertEqual(loaded.files, ("AGENTS.md", "docs/AGENTS.md"))

    def test_rejects_unsafe_paths(self) -> None:
        for unsafe in ["/AGENTS.md", "../AGENTS.md", ".git/info/exclude", "a/../b"]:
            with self.subTest(unsafe=unsafe):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    project = root / "projects" / "owner-repo"
                    (project / "overlay").mkdir(parents=True)
                    (project / "overlay.toml").write_text(
                        f'project = "owner-repo"\nfiles = ["{unsafe}"]\n',
                        encoding="utf-8",
                    )

                    with self.assertRaises(ConfigError):
                        load_project(root, "owner-repo")

    def test_rejects_duplicate_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "projects" / "owner-repo"
            (project / "overlay").mkdir(parents=True)
            (project / "overlay" / "AGENTS.md").write_text("root\n", encoding="utf-8")
            (project / "overlay.toml").write_text(
                'project = "owner-repo"\nfiles = ["AGENTS.md", "AGENTS.md"]\n',
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_project(root, "owner-repo")


if __name__ == "__main__":
    unittest.main()

