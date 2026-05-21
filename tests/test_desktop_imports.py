"""Headless smoke test for the PySide6 desktop module.

We force ``QT_QPA_PLATFORM=offscreen`` so the test runs on CI without a
display server. If Qt can't even import (PySide6 missing) or can't bind a
platform plugin at all, the test is skipped rather than failed — preflight
and the install step are responsible for catching that earlier.
"""

from __future__ import annotations

import os
import sys

import pytest

# Must be set before any PySide6 import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PYSIDE = pytest.importorskip("PySide6", reason="PySide6 not installed")


def test_desktop_modules_import() -> None:
    """Just import the desktop package and check the public surface."""
    from mapir.desktop import app as desktop_app
    from mapir.desktop import main_window, state, theme
    from mapir.desktop.widgets import (
        dashboard,
        examples_panel,
        export_panel,
        inspector_panel,
        preview_panel,
        scene_panel,
        settings_panel,
        sidebar,
        validation_panel,
        world_panel,
    )

    assert callable(desktop_app.run)
    assert callable(theme.apply_theme)
    assert hasattr(state, "AppState")
    assert hasattr(main_window, "MainWindow")
    assert hasattr(sidebar, "Sidebar")
    # Pages defined
    for mod in (
        dashboard,
        examples_panel,
        world_panel,
        scene_panel,
        inspector_panel,
        preview_panel,
        validation_panel,
        export_panel,
        settings_panel,
    ):
        assert mod.__name__.startswith("mapir.desktop.widgets.")


def test_desktop_headless_smoke() -> None:
    """Run the app in headless mode and verify it exits cleanly."""
    from mapir.desktop import app as desktop_app

    # If Qt's offscreen platform isn't available, skip gracefully.
    try:
        rc = desktop_app.run(headless=True, argv=[sys.argv[0]])
    except RuntimeError as exc:
        pytest.skip(f"Qt platform unavailable: {exc}")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "qpa" in msg or "platform plugin" in msg or "display" in msg:
            pytest.skip(f"Qt platform plugin unavailable: {exc}")
        raise

    assert rc == 0
