from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import TargetRepoError


@dataclass(frozen=True)
class GitState:
    tracked: frozenset[str]
    staged: frozenset[str]


def find_git_dir(target_repo: Path) -> Path:
    dot_git = target_repo / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        content = dot_git.read_text(encoding="utf-8").strip()
        prefix = "gitdir:"
        if content.startswith(prefix):
            git_dir = Path(content[len(prefix) :].strip())
            if not git_dir.is_absolute():
                git_dir = target_repo / git_dir
            return git_dir.resolve()
    raise TargetRepoError(f"target repository is not a Git worktree: {target_repo}")


def ensure_target_repo(target_repo: Path) -> Path:
    resolved = target_repo.expanduser().resolve()
    if not resolved.is_dir():
        raise TargetRepoError(f"target repository does not exist: {target_repo}")
    find_git_dir(resolved)
    return resolved


def _run_git(target_repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target_repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _split_nul_paths(output: str) -> set[str]:
    return {part for part in output.split("\0") if part}


def read_git_state(target_repo: Path, files: tuple[str, ...]) -> GitState:
    if not files:
        return GitState(tracked=frozenset(), staged=frozenset())

    tracked_proc = _run_git(target_repo, ["ls-files", "-z", "--", *files])
    if tracked_proc.returncode != 0:
        raise TargetRepoError(tracked_proc.stderr.strip() or "failed to read Git files")

    staged_proc = _run_git(
        target_repo,
        ["diff", "--cached", "--name-only", "-z", "--", *files],
    )
    if staged_proc.returncode != 0:
        raise TargetRepoError(
            staged_proc.stderr.strip() or "failed to read staged Git files"
        )

    return GitState(
        tracked=frozenset(_split_nul_paths(tracked_proc.stdout)),
        staged=frozenset(_split_nul_paths(staged_proc.stdout)),
    )
