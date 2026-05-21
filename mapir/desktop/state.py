"""Shared application state for MapIR Studio.

Holds the currently-loaded document, its validation report, raw JSON, and
last-export paths. Pages bind to its signals to stay in sync without
direct coupling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..core.models import SceneIR, WorldIR
from ..core.validation import ValidationReport
from ..core.validation import validate as run_validation
from ..export import blender_exporter, obj_exporter
from ..render import svg_renderer
from ..utils.io import dump_text, load_json
from ..utils.paths import ensure_output_dirs, output_dir


@dataclass
class _PathCache:
    last_open_dir: Path | None = None
    last_export_dir: Path | None = None
    last_exports: dict[str, Path] = field(default_factory=dict)


class AppState(QObject):
    """Mutable runtime state. Pages read fields and listen to signals."""

    document_loaded = Signal()  # current_document changed (or cleared)
    validation_changed = Signal()  # validation_report changed
    export_completed = Signal(str, str)  # (kind, path_as_str)
    status_message = Signal(str)  # transient status for the statusbar

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.current_path: Path | None = None
        self.current_document: WorldIR | SceneIR | None = None
        self.current_raw_json: dict[str, Any] | None = None
        self.validation_report: ValidationReport | None = None
        self.paths = _PathCache()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_json_file(self, path: Path | str) -> None:
        """Load a JSON file, parse it as IR, run validation, fire signals.

        Raises a wrapped exception on failure — caller is expected to surface
        the message in a QMessageBox. The state is left untouched on error.
        """
        from ..utils.io import load_ir  # local import keeps module import light

        p = Path(path)
        raw = load_json(p)
        ir = load_ir(p)

        self.current_path = p
        self.current_document = ir
        self.current_raw_json = raw
        self.paths.last_open_dir = p.parent
        self.document_loaded.emit()

        # Always run validation after a load so badges/panels are accurate.
        self.validation_report = run_validation(ir)
        self.validation_changed.emit()
        self.status_message.emit(f"Loaded {p.name}")

    def clear(self) -> None:
        self.current_path = None
        self.current_document = None
        self.current_raw_json = None
        self.validation_report = None
        self.document_loaded.emit()
        self.validation_changed.emit()
        self.status_message.emit("Closed document")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_current(self) -> ValidationReport | None:
        if self.current_document is None:
            return None
        report = run_validation(self.current_document)
        self.validation_report = report
        self.validation_changed.emit()
        if report.is_valid:
            self.status_message.emit("Validation OK")
        else:
            self.status_message.emit(
                f"Validation: {len(report.errors)} error(s), " f"{len(report.warnings)} warning(s)"
            )
        return report

    # ------------------------------------------------------------------
    # Rendering / export helpers
    # ------------------------------------------------------------------

    def render_svg_string(self) -> str | None:
        if self.current_document is None:
            return None
        return svg_renderer.render(self.current_document)

    def default_export_path(self, kind: str) -> Path:
        """Suggest a sensible filename under output/desktop_exports/."""
        ensure_output_dirs()
        base = output_dir() / "desktop_exports"
        stem = self.current_path.stem if self.current_path else "untitled"
        return base / f"{stem}.{kind}"

    def export_svg(self, out: Path | str) -> Path:
        if self.current_document is None:
            raise RuntimeError("No document loaded")
        out_path = Path(out)
        text = svg_renderer.render(self.current_document)
        dump_text(out_path, text)
        self.paths.last_exports["svg"] = out_path
        self.paths.last_export_dir = out_path.parent
        self.export_completed.emit("svg", str(out_path))
        self.status_message.emit(f"Exported SVG → {out_path}")
        return out_path

    def export_obj(self, out: Path | str) -> Path:
        if self.current_document is None:
            raise RuntimeError("No document loaded")
        out_path = Path(out)
        text = obj_exporter.export(self.current_document)
        dump_text(out_path, text)
        self.paths.last_exports["obj"] = out_path
        self.paths.last_export_dir = out_path.parent
        self.export_completed.emit("obj", str(out_path))
        self.status_message.emit(f"Exported OBJ → {out_path}")
        return out_path

    def export_blender(self, out: Path | str) -> Path:
        if self.current_document is None:
            raise RuntimeError("No document loaded")
        out_path = Path(out)
        text = blender_exporter.export(self.current_document)
        dump_text(out_path, text)
        self.paths.last_exports["blender"] = out_path
        self.paths.last_export_dir = out_path.parent
        self.export_completed.emit("blender", str(out_path))
        self.status_message.emit(f"Exported Blender script → {out_path}")
        return out_path

    # ------------------------------------------------------------------
    # Introspection helpers used by pages
    # ------------------------------------------------------------------

    def raw_json_pretty(self) -> str:
        if self.current_raw_json is None:
            return ""
        return json.dumps(self.current_raw_json, indent=2, ensure_ascii=False)

    def doc_type(self) -> str:
        if isinstance(self.current_document, WorldIR):
            return "world"
        if isinstance(self.current_document, SceneIR):
            return "scene"
        return ""

    def doc_name(self) -> str:
        doc = self.current_document
        if doc is None:
            return ""
        return getattr(doc, "name", "?")
