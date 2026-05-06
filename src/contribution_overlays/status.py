from __future__ import annotations

from enum import Enum


class OverlayStatus(str, Enum):
    OK = "OK"
    MISSING = "MISSING"
    BROKEN = "BROKEN"
    WRONG = "WRONG"
    CONFLICT = "CONFLICT"
    TRACKED = "TRACKED"
    STAGED = "STAGED"
    IGNORE_MISSING = "IGNORE_MISSING"
    EXTRA = "EXTRA"


AUTO_REPAIRABLE = frozenset(
    {
        OverlayStatus.MISSING,
        OverlayStatus.BROKEN,
        OverlayStatus.IGNORE_MISSING,
    }
)

OPTION_REQUIRED = frozenset(
    {
        OverlayStatus.WRONG,
        OverlayStatus.EXTRA,
    }
)

PROTECTED = frozenset(
    {
        OverlayStatus.CONFLICT,
        OverlayStatus.TRACKED,
        OverlayStatus.STAGED,
    }
)


def describe_status(status: OverlayStatus) -> str:
    descriptions = {
        OverlayStatus.OK: "ok",
        OverlayStatus.MISSING: "missing",
        OverlayStatus.BROKEN: "broken symlink",
        OverlayStatus.WRONG: "symlink points to a different target",
        OverlayStatus.CONFLICT: "regular file or directory exists",
        OverlayStatus.TRACKED: "tracked by target Git",
        OverlayStatus.STAGED: "staged in target Git index",
        OverlayStatus.IGNORE_MISSING: "missing from .git/info/exclude",
        OverlayStatus.EXTRA: "extra overlay symlink",
    }
    return descriptions[status]
