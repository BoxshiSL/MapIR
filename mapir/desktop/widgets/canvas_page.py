"""Canvas page — Phase A scaffold.

Phase A delivers the page shell, the toolbar, and a status banner. The actual
interactive sketch tools (Select / Draw District Polygon / Draw Road / Add
POI / Add Scene Slot / Delete) land in Phase B together with the
``SketchDocument`` model and ``CanvasToolController``.

The placeholder keeps the sidebar workflow path visible to users even before
Phase B is shipped, and lets the test harness import the page without
crashing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState


_CANVAS_TOOLS: tuple[tuple[str, str], ...] = (
    ("select", "Select / Move"),
    ("draw_district", "Draw District"),
    ("draw_road", "Draw Road"),
    ("add_poi", "Add POI"),
    ("add_scene_slot", "Add Scene Slot"),
    ("delete", "Delete"),
)


class CanvasPage(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Canvas")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Sketch district polygons, roads, POIs, and scene slots. The "
            "sketch lives in a SketchLayer that is separate from the "
            "validated IR — nothing here mutates your document until you "
            "press Generate on the Generation page."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        for tool_id, label in _CANVAS_TOOLS:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setObjectName(f"tool_{tool_id}")
            b.setEnabled(False)  # Phase B will enable
            self._tool_group.addButton(b)
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self._banner = QLabel(
            "Phase A scaffold: the Canvas surface ships in v0.5 Phase B "
            "alongside the SketchLayer model. For now use the New Project "
            "Wizard or Templates Gallery to instantiate a document, then "
            "preview/validate/export from the existing pages."
        )
        self._banner.setWordWrap(True)
        self._banner.setProperty("role", "muted")
        self._banner.setStyleSheet(
            "background: #1f2630; border: 1px solid #2a3340; "
            "color: #d0d6dd; padding: 12px; border-radius: 6px;"
        )
        root.addWidget(self._banner)

        self._view = QGraphicsView()
        self._view.setRenderHints(self._view.renderHints())
        self._view.setFrameShape(QFrame.StyledPanel)
        self._view.setAlignment(Qt.AlignCenter)
        root.addWidget(self._view, 1)

        state.document_loaded.connect(self._refresh)
        state.sketch_changed.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        if self._state.current_document is None:
            self._view.setScene(None)
            return
        # Re-use the preview renderer for read-only context while the real
        # sketch surface is unimplemented. The Canvas surface in Phase B
        # will host its own scene.
        from ..preview_scene import PreviewOptions, build_scene

        scene = build_scene(self._state.current_document, PreviewOptions())
        self._view.setScene(scene)
        rect = scene.sceneRect()
        if not rect.isNull() and not rect.isEmpty():
            self._view.fitInView(rect, Qt.KeepAspectRatio)
