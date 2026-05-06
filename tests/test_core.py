from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from contribution_overlays.config import load_project
from contribution_overlays.core import check_overlay, sync_overlay, unlink_overlay
from contribution_overlays.git import ensure_target_repo
from contribution_overlays.status import OverlayStatus


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class CoreTests(unittest.TestCase):
    def make_fixture(self, files: list[str] | None = None):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        source_root = root / "source"
        target_repo = root / "target"
        project_root = source_root / "projects" / "owner-repo"
        overlay_dir = project_root / "overlay"
        target_repo.mkdir(parents=True)
        git(target_repo, "init")
        git(target_repo, "config", "user.email", "test@example.invalid")
        git(target_repo, "config", "user.name", "Test User")

        files = files or ["AGENTS.md", "docs/AGENTS.md"]
        for relative_path in files:
            overlay_file = overlay_dir / relative_path
            overlay_file.parent.mkdir(parents=True, exist_ok=True)
            overlay_file.write_text(f"{relative_path}\n", encoding="utf-8")

        project_root.mkdir(parents=True, exist_ok=True)
        rendered_files = ", ".join(f'"{path}"' for path in files)
        (project_root / "overlay.toml").write_text(
            f'project = "owner-repo"\nfiles = [{rendered_files}]\n',
            encoding="utf-8",
        )

        project = load_project(source_root, "owner-repo")
        return temp, source_root, ensure_target_repo(target_repo), project

    def test_sync_creates_symlinks_and_exclude_entries(self) -> None:
        temp, _source_root, target_repo, project = self.make_fixture()
        with temp:
            before = check_overlay(target_repo, project)
            self.assertEqual(
                [status.status for status in before.statuses],
                [
                    OverlayStatus.MISSING,
                    OverlayStatus.IGNORE_MISSING,
                    OverlayStatus.MISSING,
                    OverlayStatus.IGNORE_MISSING,
                ],
            )

            result = sync_overlay(target_repo, project)

            self.assertTrue(result.ok)
            self.assertTrue((target_repo / "AGENTS.md").is_symlink())
            self.assertTrue((target_repo / "docs" / "AGENTS.md").is_symlink())
            exclude = (target_repo / ".git" / "info" / "exclude").read_text(
                encoding="utf-8"
            )
            self.assertIn("AGENTS.md", exclude)
            self.assertIn("docs/AGENTS.md", exclude)

            check = check_overlay(target_repo, project)
            self.assertEqual(
                [status.status for status in check.statuses],
                [OverlayStatus.OK, OverlayStatus.OK],
            )

    def test_sync_refuses_regular_file_conflict(self) -> None:
        temp, _source_root, target_repo, project = self.make_fixture(["AGENTS.md"])
        with temp:
            (target_repo / "AGENTS.md").write_text("real file\n", encoding="utf-8")

            result = sync_overlay(target_repo, project)

            self.assertFalse(result.ok)
            self.assertEqual(result.statuses[0].status, OverlayStatus.CONFLICT)
            self.assertEqual(
                (target_repo / "AGENTS.md").read_text(encoding="utf-8"),
                "real file\n",
            )

    def test_sync_refuses_tracked_path(self) -> None:
        temp, _source_root, target_repo, project = self.make_fixture(["AGENTS.md"])
        with temp:
            (target_repo / "AGENTS.md").write_text("tracked\n", encoding="utf-8")
            git(target_repo, "add", "AGENTS.md")
            git(target_repo, "commit", "-m", "track agents")

            result = sync_overlay(target_repo, project)

            self.assertFalse(result.ok)
            self.assertEqual(result.statuses[0].status, OverlayStatus.TRACKED)
            self.assertEqual(
                (target_repo / "AGENTS.md").read_text(encoding="utf-8"),
                "tracked\n",
            )

    def test_replace_wrong_symlink_requires_option(self) -> None:
        temp, _source_root, target_repo, project = self.make_fixture(["AGENTS.md"])
        with temp:
            wrong_source = target_repo / "wrong.md"
            wrong_source.write_text("wrong\n", encoding="utf-8")
            (target_repo / "AGENTS.md").symlink_to(wrong_source)

            refused = sync_overlay(target_repo, project)
            self.assertFalse(refused.ok)
            self.assertEqual(refused.statuses[0].status, OverlayStatus.WRONG)

            replaced = sync_overlay(target_repo, project, replace_wrong=True)
            self.assertTrue(replaced.ok)
            self.assertEqual(
                os.readlink(target_repo / "AGENTS.md"),
                str(project.source_for("AGENTS.md")),
            )

    def test_unlink_removes_only_symlinks(self) -> None:
        temp, _source_root, target_repo, project = self.make_fixture(["AGENTS.md"])
        with temp:
            sync_overlay(target_repo, project)

            result = unlink_overlay(target_repo, project)

            self.assertTrue(result.ok)
            self.assertFalse((target_repo / "AGENTS.md").exists())

    def test_unlink_refuses_regular_file(self) -> None:
        temp, _source_root, target_repo, project = self.make_fixture(["AGENTS.md"])
        with temp:
            (target_repo / "AGENTS.md").write_text("real file\n", encoding="utf-8")

            result = unlink_overlay(target_repo, project)

            self.assertFalse(result.ok)
            self.assertTrue((target_repo / "AGENTS.md").is_file())


if __name__ == "__main__":
    unittest.main()
