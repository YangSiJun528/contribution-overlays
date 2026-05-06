from __future__ import annotations


class OverlayError(Exception):
    """Base exception for expected user-facing errors."""


class ConfigError(OverlayError):
    """Raised when an overlay project definition is invalid."""


class TargetRepoError(OverlayError):
    """Raised when the target repository cannot be used safely."""
