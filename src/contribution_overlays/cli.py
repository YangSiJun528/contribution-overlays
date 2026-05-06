from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_project
from .core import check_overlay, sync_overlay, unlink_overlay
from .errors import OverlayError
from .git import ensure_target_repo
from .status import OverlayStatus, describe_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contribution-overlays",
        description="Manage symlink overlays for contribution instruction files.",
    )
    parser.add_argument(
        "--source-root",
        default=".",
        help="repository root containing projects/ (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync", help="apply an overlay to a target repo")
    sync.add_argument("--dry-run", action="store_true", help="show planned changes only")
    sync.add_argument("--prune", action="store_true", help="remove extra overlay symlinks")
    sync.add_argument(
        "--clean-exclude",
        action="store_true",
        help="remove stale .git/info/exclude entries when possible",
    )
    sync.add_argument(
        "--replace-wrong",
        action="store_true",
        help="replace symlinks pointing at a different target",
    )
    sync.add_argument("target_repo")
    sync.add_argument("project_name")

    check = subparsers.add_parser("check", help="inspect overlay state")
    check.add_argument("target_repo")
    check.add_argument("project_name")

    unlink = subparsers.add_parser("unlink", help="remove overlay symlinks")
    unlink.add_argument("--dry-run", action="store_true", help="show planned changes only")
    unlink.add_argument(
        "--clean-exclude",
        action="store_true",
        help="remove overlay entries from .git/info/exclude",
    )
    unlink.add_argument("target_repo")
    unlink.add_argument("project_name")

    return parser


def _status_line(status) -> str:
    detail = f" ({status.detail})" if status.detail else ""
    return (
        f"{status.status.value:14} {status.relative_path} - "
        f"{describe_status(status.status)}{detail}"
    )


def _print_result(result, *, show_ok: bool = True) -> None:
    for status in result.statuses:
        if show_ok or status.status != OverlayStatus.OK:
            print(_status_line(status))

    if result.actions:
        print("\nactions:")
        for action in result.actions:
            print(f"  {action}")

    if result.errors:
        print("\nerrors:", file=sys.stderr)
        for error in result.errors:
            print(f"  {error}", file=sys.stderr)


def run(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root).expanduser().resolve()
    target_repo = ensure_target_repo(Path(args.target_repo))
    project = load_project(source_root, args.project_name)

    if args.command == "check":
        result = check_overlay(target_repo, project)
        _print_result(result)
        return 0 if all(status.status == OverlayStatus.OK for status in result.statuses) else 1

    if args.command == "sync":
        result = sync_overlay(
            target_repo,
            project,
            dry_run=args.dry_run,
            prune=args.prune,
            clean_exclude=args.clean_exclude,
            replace_wrong=args.replace_wrong,
        )
        _print_result(result)
        return 0 if result.ok else 1

    if args.command == "unlink":
        result = unlink_overlay(
            target_repo,
            project,
            dry_run=args.dry_run,
            clean_exclude=args.clean_exclude,
        )
        _print_result(result)
        return 0 if result.ok else 1

    raise AssertionError(f"unhandled command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except OverlayError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
