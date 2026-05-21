"""Preview page — interactive 2D view of the loaded IR via QGraphicsView."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QWheelEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.io import dump_text
from ..preview_scene import build_scene
from ..state import AppState


class _ZoomGraphicsView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom and drag pan."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        # Y-flip is already baked into the scene coordinates.

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self.scale(factor, factor)


class PreviewPage(QWidget):
    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Preview")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Interactive 2D view. Scroll to zoom, drag to pan. "
            "SVG export uses the same data — see Export."
        )
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("role", "primary")
        self.btn_fit = QPushButton("Fit")
        self.btn_zoom_in = QPushButton("Zoom +")
        self.btn_zoom_out = QPushButton("Zoom −")
        self.btn_save_svg = QPushButton("Save SVG…")
        for b in (
            self.btn_refresh,
            self.btn_fit,
            self.btn_zoom_in,
            self.btn_zoom_out,
            self.btn_save_svg,
        ):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        self.info_label = QLabel()
        self.info_label.setProperty("role", "muted")
        toolbar.addWidget(self.info_label)
        root.addLayout(toolbar)

        self.view = _ZoomGraphicsView()
        root.addWidget(self.view, 1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_fit.clicked.connect(self._fit)
        self.btn_zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        self.btn_zoom_out.clicked.connect(lambda: self.view.scale(1 / 1.2, 1 / 1.2))
        self.btn_save_svg.clicked.connect(self._save_svg)

        state.document_loaded.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        doc = self._state.current_document
        if doc is None:
            self.view.setScene(None)
            self.info_label.setText("No document loaded.")
            for b in (self.btn_fit, self.btn_zoom_in, self.btn_zoom_out, self.btn_save_svg):
                b.setEnabled(False)
            return
        scene = build_scene(doc)
        self.view.setScene(scene)
        for b in (self.btn_fit, self.btn_zoom_in, self.btn_zoom_out, self.btn_save_svg):
            b.setEnabled(True)
        self._fit()
        kind = self._state.doc_type()
        self.info_label.setText(f"{kind.upper()} — {self._state.doc_name()}")

    def _fit(self) -> None:
        if self.view.scene() is None:
            return
        rect = self.view.scene().sceneRect()
        if rect.isNull() or rect.isEmpty():
            return
        self.view.fitInView(rect, Qt.KeepAspectRatio)

    def _save_svg(self) -> None:
        if self._state.current_document is None:
            return
        default = self._state.default_export_path("svg")
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save SVG", str(default), "SVG (*.svg);;All files (*)"
        )
        if not chosen:
            return
        try:
            text = self._state.render_svg_string() or ""
            dump_text(chosen, text)
            self._state.paths.last_exports["svg"] = type(default)(chosen)
            self._state.export_completed.emit("svg", chosen)
        except Exception as exc:  # noqa: BLE001 — surface to user
            QMessageBox.critical(self, "Save SVG failed", str(exc))
