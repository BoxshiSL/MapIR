"""Settings / About page."""

from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from ... import __version__
from ...utils.paths import (
    app_root,
    examples_dir,
    is_frozen,
    output_dir,
    schemas_dir,
)


def _qt_version() -> str:
    try:
        from PySide6 import __version__ as pyside_version
        from PySide6.QtCore import qVersion

        return f"PySide6 {pyside_version} / Qt {qVersion()}"
    except Exception as exc:  # noqa: BLE001
        return f"unknown ({exc})"


class SettingsPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Settings / About")
        title.setProperty("role", "pageTitle")

        subtitle = QLabel(f"Read-only environment summary for v{__version__}.")
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        about = QGroupBox("MapIR Studio")
        about_lay = QVBoxLayout(about)
        about_text = QLabel(
            f"<b>Version:</b> v{__version__}<br>"
            "<b>Mode:</b> Desktop (PySide6)<br>"
            f"<b>Qt:</b> {_qt_version()}<br>"
            f"<b>Python:</b> {sys.version.split()[0]} ({platform.python_implementation()})<br>"
            f"<b>Platform:</b> {platform.system()} {platform.release()}<br>"
            f"<b>Frozen build:</b> {'yes' if is_frozen() else 'no'}"
        )
        about_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        about_text.setTextFormat(Qt.RichText)
        about_lay.addWidget(about_text)
        root.addWidget(about)

        paths_box = QGroupBox("Paths")
        paths_lay = QVBoxLayout(paths_box)
        paths_text = QLabel(
            f"<b>App root:</b> {app_root()}<br>"
            f"<b>Examples:</b> {examples_dir()}<br>"
            f"<b>Schemas:</b> {schemas_dir()}<br>"
            f"<b>Output:</b> {output_dir()}"
        )
        paths_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        paths_text.setTextFormat(Qt.RichText)
        paths_text.setWordWrap(True)
        paths_lay.addWidget(paths_text)
        root.addWidget(paths_box)

        scope_box = QGroupBox("What MapIR v0.5 is — and what it is not yet")
        scope_lay = QVBoxLayout(scope_box)
        scope_text = QLabel(
            "<b>v0.5 is:</b> a guided desktop tool for designing game worlds, "
            "scenes, and interiors. It bundles a New Project Wizard, a neutral "
            "template gallery, a sketch canvas (polygons, roads, POIs, scene "
            "slots), a District Inspector with gameplay profiles, a "
            "deterministic generation pipeline (roads → parcels → buildings → "
            "landmarks → scene slots → guidance), curated design rules, and "
            "structural plus design-aware validation. Local LLM drafting from "
            "v0.4 is kept and integrated into the workflow.<br><br>"
            "<b>v0.5 is not yet:</b> a UE5 / Unity exporter, a real GLB/FBX "
            "asset importer, a full 3D viewport, an installer, a freehand "
            "sketch recognizer, or a final art pipeline. Those remain on the "
            "v0.6+ roadmap."
        )
        scope_text.setWordWrap(True)
        scope_text.setTextFormat(Qt.RichText)
        scope_lay.addWidget(scope_text)
        root.addWidget(scope_box)

        root.addStretch(1)
