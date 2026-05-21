"""Path helpers that work both from source tree and from a PyInstaller bundle.

PyInstaller, when ``--onedir``/``--onefile``, sets ``sys.frozen`` to ``True`` and
exposes the extraction directory as ``sys._MEIPASS``. We treat that directory
as the application root; otherwise we walk up from this file to the repo root.

Single source of truth — both CLI and desktop UI use these helpers so that
PyInstaller-built ``MapIR Studio.exe`` finds bundled ``examples/`` and
``mapir/schemas/`` without any path hacks at the call site.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller-built executable."""
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """Root directory containing bundled resources.

    * Frozen build → ``sys._MEIPASS`` (PyInstaller extraction dir).
    * Source tree  → repo root (parent of the ``mapir`` package).
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    # mapir/utils/paths.py → repo root = parents[2]
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str | Path) -> Path:
    """Resolve a path relative to :func:`app_root`."""
    return app_root().joinpath(*parts)


def examples_dir() -> Path:
    return resource_path("examples")


def schemas_dir() -> Path:
    return resource_path("mapir", "schemas")


def output_dir() -> Path:
    """User-writable output directory.

    From a frozen exe, the bundle dir is read-only (and gets cleaned up
    between runs), so we prefer a directory next to the exe.
    """
    if is_frozen():
        exe = Path(sys.executable).resolve()
        return exe.parent / "output"
    return Path(__file__).resolve().parents[2] / "output"


def ensure_output_dirs() -> Path:
    """Create the standard output sub-directories if missing. Returns the root."""
    base = output_dir()
    for sub in ("svg", "obj", "blender", "desktop_exports"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def env_repo_root() -> Path | None:
    """Optional override used by tests (`MAPIR_REPO_ROOT` env var)."""
    val = os.environ.get("MAPIR_REPO_ROOT")
    return Path(val) if val else None
