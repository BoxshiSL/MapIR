"""Reusable tkinter widgets for the MapIR UI."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from ..core.validation import ValidationReport
from ..core.models import SceneIR, WorldIR


class ExampleList(ttk.Frame):
    """Two-section list of example files (worlds + scenes)."""

    def __init__(self, parent: tk.Misc,
                 worlds: list[Path], scenes: list[Path],
                 on_select: Callable[[Path], None]) -> None:
        super().__init__(parent, padding=4)
        self._on_select = on_select

        ttk.Label(self, text="Examples", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self._tree = ttk.Treeview(self, show="tree", selectmode="browse", height=20)
        self._tree.pack(fill="both", expand=True)
        self._path_by_iid: dict[str, Path] = {}

        if worlds:
            worlds_root = self._tree.insert("", "end", text="Worlds", open=True)
            for w in worlds:
                iid = self._tree.insert(worlds_root, "end", text=w.stem)
                self._path_by_iid[iid] = w
        if scenes:
            scenes_root = self._tree.insert("", "end", text="Scenes", open=True)
            for s in scenes:
                iid = self._tree.insert(scenes_root, "end", text=s.stem)
                self._path_by_iid[iid] = s

        self._tree.bind("<<TreeviewSelect>>", self._handle_select)

    def _handle_select(self, _event: object) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        path = self._path_by_iid.get(sel[0])
        if path is not None:
            self._on_select(path)

    def select_first_leaf(self) -> Path | None:
        for iid, path in self._path_by_iid.items():
            self._tree.selection_set(iid)
            self._tree.see(iid)
            return path
        return None


class InfoPanel(ttk.LabelFrame):
    """Key/value summary mirroring ``mapir.cli inspect``."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Summary", padding=8)
        self._text = tk.Text(self, height=10, width=44, wrap="word",
                             font=("Consolas", 9), state="disabled",
                             relief="flat", background="#fafafa")
        self._text.pack(fill="both", expand=True)

    def show(self, ir: WorldIR | SceneIR) -> None:
        rows = _summary_rows(ir)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        width = max(len(k) for k, _ in rows) if rows else 0
        for k, v in rows:
            self._text.insert("end", f"{k.ljust(width)}  {v}\n")
        self._text.configure(state="disabled")


def _summary_rows(ir: WorldIR | SceneIR) -> list[tuple[str, str]]:
    if isinstance(ir, WorldIR):
        return [
            ("Type", "world"),
            ("ID", ir.world_id),
            ("Name", ir.name),
            ("Theme", ir.theme),
            ("Scale", f"{ir.scale.width_m} x {ir.scale.depth_m} m"),
            ("Districts", str(len(ir.districts))),
            ("Roads", str(len(ir.roads))),
            ("Water bodies", str(len(ir.water_bodies))),
            ("POIs", str(len(ir.pois))),
            ("Scene slots", str(len(ir.scene_slots))),
            ("Constraints", str(len(ir.constraints))),
        ]
    scene: SceneIR = ir
    return [
        ("Type", "scene"),
        ("ID", scene.scene_id),
        ("Name", scene.name),
        ("Theme", scene.theme),
        ("Scene type", scene.scene_type.value),
        ("Preset", scene.preset.value),
        ("Bounds", f"{scene.bounds.width_m} x {scene.bounds.depth_m} x {scene.bounds.height_m} m"),
        ("Standalone", str(scene.standalone)),
        ("Zones", str(len(scene.zones))),
        ("Entrances", str(len(scene.entrances))),
        ("Paths", str(len(scene.paths))),
        ("Objects", str(len(scene.objects))),
        ("Markers", str(len(scene.gameplay_markers))),
        ("Constraints", str(len(scene.constraints))),
    ]


class ValidationPanel(ttk.LabelFrame):
    """Compact list of validation issues."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Validation", padding=8)
        self._status = ttk.Label(self, text="-", font=("Segoe UI", 10, "bold"))
        self._status.pack(anchor="w")
        self._text = tk.Text(self, height=8, width=44, wrap="word",
                             font=("Consolas", 9), state="disabled",
                             relief="flat", background="#fafafa")
        self._text.pack(fill="both", expand=True, pady=(4, 0))

    def show(self, report: ValidationReport) -> None:
        if report.is_valid and not report.warnings:
            self._status.configure(text="OK — no issues.", foreground="#1b7f3a")
        elif report.is_valid:
            self._status.configure(
                text=f"OK with {len(report.warnings)} warning(s).",
                foreground="#a26a00",
            )
        else:
            self._status.configure(
                text=f"{len(report.errors)} error(s), {len(report.warnings)} warning(s).",
                foreground="#a51c1c",
            )
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        for issue in report.all():
            self._text.insert(
                "end",
                f"[{issue.severity.value.upper()}] {issue.code}: {issue.message}\n"
                f"        {issue.path}\n",
            )
        self._text.configure(state="disabled")
