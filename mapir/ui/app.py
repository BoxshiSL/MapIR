"""MapIR desktop UI — read-only browser for example WorldIR / SceneIR files.

Usage:
    from mapir.ui.app import run_app
    run_app()                 # opens the window
    run_app(headless=True)    # builds the app, renders once, then exits with 0
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import __version__
from ..core.models import SceneIR, WorldIR
from ..core.validation import validate as run_validation
from ..export import blender_exporter, obj_exporter
from ..render import svg_renderer
from ..utils.io import dump_text, load_ir
from . import canvas_renderer
from .widgets import ExampleList, InfoPanel, ValidationPanel

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
OUTPUT_DIR = REPO_ROOT / "output"


class MapIRApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"MapIR v{__version__}")
        self.geometry("1200x780")
        self.minsize(900, 600)

        self._current_ir: WorldIR | SceneIR | None = None
        self._current_path: Path | None = None

        self._build_layout()
        self._populate_examples()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 6))
        ttk.Label(header, text="MapIR", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Label(header, text=f"v{__version__}",
                  foreground="#666").pack(side="left", padx=(6, 0))
        ttk.Label(header, text=" — local preview of WorldIR / SceneIR examples",
                  foreground="#888").pack(side="left", padx=(8, 0))

        main = ttk.PanedWindow(root, orient="horizontal")
        main.pack(fill="both", expand=True)

        # Left: example list (placeholder, populated in _populate_examples).
        self._left_container = ttk.Frame(main)
        main.add(self._left_container, weight=1)
        self._example_list: ExampleList | None = None

        # Right: canvas + info + actions.
        right = ttk.Frame(main)
        main.add(right, weight=4)

        self._canvas = tk.Canvas(right, background="#f5f5f5",
                                 highlightthickness=1, highlightbackground="#ccc")
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>", self._on_canvas_resized)

        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(6, 0))

        self._info = InfoPanel(bottom)
        self._info.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self._validation = ValidationPanel(bottom)
        self._validation.pack(side="left", fill="both", expand=True, padx=(4, 0))

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(6, 0))
        self._status = ttk.Label(actions, text="Select an example to begin.",
                                 foreground="#666")
        self._status.pack(side="left")

        btns = ttk.Frame(actions)
        btns.pack(side="right")
        self._btn_svg = ttk.Button(btns, text="Save SVG", command=self._save_svg,
                                   state="disabled")
        self._btn_obj = ttk.Button(btns, text="Export OBJ", command=self._export_obj,
                                   state="disabled")
        self._btn_blender = ttk.Button(btns, text="Export Blender",
                                       command=self._export_blender, state="disabled")
        self._btn_svg.pack(side="left", padx=2)
        self._btn_obj.pack(side="left", padx=2)
        self._btn_blender.pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Data plumbing
    # ------------------------------------------------------------------

    def _populate_examples(self) -> None:
        worlds = sorted((EXAMPLES_DIR / "worlds").glob("*.json"))
        scenes = sorted((EXAMPLES_DIR / "scenes").glob("*.json"))
        self._example_list = ExampleList(self._left_container, worlds, scenes,
                                         on_select=self._load_path)
        self._example_list.pack(fill="both", expand=True)

    def select_first_example(self) -> Path | None:
        if self._example_list is None:
            return None
        return self._example_list.select_first_leaf()

    def _load_path(self, path: Path) -> None:
        try:
            ir = load_ir(path)
        except Exception as exc:  # noqa: BLE001  (UI surface; show, don't crash)
            messagebox.showerror("Failed to load", f"{path.name}\n\n{exc}")
            return
        self._current_ir = ir
        self._current_path = path
        report = run_validation(ir)
        self._info.show(ir)
        self._validation.show(report)
        self._redraw()
        for btn in (self._btn_svg, self._btn_obj, self._btn_blender):
            btn.configure(state="normal")
        self._status.configure(text=f"Loaded {path.name}", foreground="#1b7f3a")

    def _redraw(self) -> None:
        if self._current_ir is None:
            return
        canvas_renderer.render(self._canvas, self._current_ir)

    def _on_canvas_resized(self, _event: tk.Event) -> None:
        self._redraw()

    # ------------------------------------------------------------------
    # Export actions
    # ------------------------------------------------------------------

    def _export_target(self, subdir: str, suffix: str) -> Path | None:
        if self._current_path is None:
            return None
        default = OUTPUT_DIR / subdir / f"{self._current_path.stem}{suffix}"
        chosen = filedialog.asksaveasfilename(
            initialdir=str(default.parent),
            initialfile=default.name,
            defaultextension=suffix,
        )
        return Path(chosen) if chosen else None

    def _save_svg(self) -> None:
        if self._current_ir is None:
            return
        out = self._export_target("svg", ".svg")
        if out is None:
            return
        text = svg_renderer.render(self._current_ir)
        dump_text(out, text)
        self._status.configure(text=f"Wrote {out}", foreground="#1b7f3a")

    def _export_obj(self) -> None:
        if self._current_ir is None:
            return
        out = self._export_target("obj", ".obj")
        if out is None:
            return
        text = obj_exporter.export(self._current_ir)
        dump_text(out, text)
        self._status.configure(text=f"Wrote {out}", foreground="#1b7f3a")

    def _export_blender(self) -> None:
        if self._current_ir is None:
            return
        out = self._export_target("blender", ".py")
        if out is None:
            return
        text = blender_exporter.export(self._current_ir)
        dump_text(out, text)
        self._status.configure(text=f"Wrote {out}", foreground="#1b7f3a")


def run_app(*, headless: bool = False) -> int:
    """Construct and run the UI. Returns the process-style exit code.

    ``headless=True`` builds the window, loads the first example, renders once,
    then destroys the root and returns 0 without showing anything. Used by the
    ``--no-browser`` CLI flag and CI smoke tests.
    """
    app = MapIRApp()
    if headless:
        app.withdraw()
        first = app.select_first_example()
        if first is not None:
            app.update_idletasks()
        app.update()
        app.destroy()
        return 0
    app.mainloop()
    return 0
