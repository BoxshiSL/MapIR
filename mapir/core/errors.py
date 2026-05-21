"""Project-specific exceptions."""

from __future__ import annotations


class MapIRError(Exception):
    """Base error for all MapIR failures shown to the user."""


class IRTypeError(MapIRError):
    """Raised when a JSON file has missing or unknown `ir_type`."""


class IRLoadError(MapIRError):
    """Raised when a JSON file cannot be read or parsed."""
