"""MapIR Studio entrypoint.

Run from the CLI::

    python -m mapir.cli desktop                 # opens the window
    python -m mapir.cli desktop --no-browser    # headless smoke (CI)

Or directly::

    python -m mapir.desktop.app
"""

from __future__ import annotations

import os
import sys


def _ensure_qt_can_run() -> None:
    """Set ``QT_QPA_PLATFORM=offscreen`` when no display is available.

    Used in CI where Windows runners do have a session but Linux ones may not.
    We only fall back when the variable is unset and the platform is Linux
    without ``DISPLAY``/``WAYLAND_DISPLAY``.
    """
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if sys.platform.startswith("linux"):
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "offscreen"


def run(*, headless: bool = False, argv: list[str] | None = None) -> int:
    """Construct the QApplication, show the window, and run the event loop.

    Returns a process-style exit code.

    ``headless=True`` builds the QApplication and MainWindow, runs the event
    loop briefly to flush pending events, then exits with 0 — used by CI to
    check that imports and constructors don't crash without forcing the
    desktop session to actually show a window.
    """
    _ensure_qt_can_run()

    # Imports are local so that just importing this module doesn't pull Qt in.
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow
    from .state import AppState
    from .theme import apply_theme

    app = QApplication.instance() or QApplication(argv or sys.argv)
    apply_theme(app)

    state = AppState()
    window = MainWindow(state)

    if headless:
        # Don't show the window, but do allow it to be fully constructed
        # so we exercise widget wiring. Quit on the next tick.
        QTimer.singleShot(0, app.quit)
        return app.exec()

    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    return run(headless=False, argv=argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
