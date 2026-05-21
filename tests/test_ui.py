from __future__ import annotations

from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")

from mapir.ui import canvas_renderer  # noqa: E402
from mapir.ui.app import run_app  # noqa: E402
from mapir.utils.io import load_ir  # noqa: E402


def _can_open_display() -> bool:
    try:
        root = tk.Tk()
    except tk.TclError:
        return False
    root.destroy()
    return True


pytestmark = pytest.mark.skipif(
    not _can_open_display(),
    reason="No Tk display available (headless CI without xvfb).",
)


def test_run_app_headless_returns_zero() -> None:
    assert run_app(headless=True) == 0


def test_canvas_renderer_draws_each_example(world_files: list[Path],
                                            scene_files: list[Path]) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        canvas = tk.Canvas(root, width=800, height=600)
        canvas.pack()
        root.update_idletasks()
        for path in [*world_files, *scene_files]:
            ir = load_ir(path)
            canvas_renderer.render(canvas, ir)
            assert canvas.find_all(), f"canvas empty after rendering {path.name}"
    finally:
        root.destroy()
