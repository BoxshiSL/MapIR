"""Preview page — interactive 2D view of the loaded IR via QGraphicsView.

v0.5 additions:

* a label-scale slider (0.5x – 2.0x) that affects the live preview;
* per-layer visibility toggles (districts/water/roads/POIs/scene slots
  for worlds; zones/objects/paths/entrances/markers for scenes);
* a tiny readability hint when the renderer suppresses overlapping labels
  (so the validator catches "too cluttered" without us doing pixel work).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...utils.io import dump_text
from ..preview_scene import (
    SCENE_LAYERS,
    WORLD_LAYERS,
    PreviewOptions,
    build_scene,
    default_layer_visibility,
)
from ..state import AppState


_LAYER_LABELS: dict[str, str] = {
    "districts": "Districts",
    "water": "Water",
    "roads": "Roads",
    "pois": "POIs",
    "scene_slots": "Scene Slots",
    "zones": "Zones",
    "objects": "Objects",
    "paths": "Paths",
    "entrances": "Entrances",
    "markers": "Markers",
}


class _ZoomGraphicsView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom and drag pan."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

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
        self._visibility: dict[str, bool] = default_layer_visibility()
        self._layer_checks: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Preview")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Interactive 2D view. Scroll to zoom, drag to pan. Use the "
            "controls below to toggle layers or rescale labels — SVG export "
            "uses the same data."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
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

        controls = QHBoxLayout()
        controls.setSpacing(12)

        # Label scale slider
        scale_box = QGroupBox("Label scale")
        scale_layout = QHBoxLayout(scale_box)
        scale_layout.setContentsMargins(8, 4, 8, 4)
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200)  # 0.5x .. 2.0x in 1%-steps
        self.scale_slider.setValue(100)
        self.scale_slider.setSingleStep(5)
        self.scale_slider.setPageStep(10)
        self.scale_slider.setFixedWidth(160)
        self.scale_value_label = QLabel("1.00×")
        self.scale_value_label.setProperty("role", "muted")
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_value_label)
        controls.addWidget(scale_box)

        # Per-layer visibility checkboxes
        self.layers_box = QGroupBox("Layers")
        layers_layout = QHBoxLayout(self.layers_box)
        layers_layout.setContentsMargins(8, 4, 8, 4)
        layers_layout.setSpacing(8)
        for layer in (*WORLD_LAYERS, *[L for L in SCENE_LAYERS if L not in WORLD_LAYERS]):
            cb = QCheckBox(_LAYER_LABELS.get(layer, layer))
            cb.setChecked(True)
            cb.setProperty("layer_id", layer)
            cb.stateChanged.connect(self._on_layer_toggle)
            layers_layout.addWidget(cb)
            self._layer_checks[layer] = cb
        controls.addWidget(self.layers_box, 1)
        root.addLayout(controls)

        self.dropped_label = QLabel()
        self.dropped_label.setProperty("role", "muted")
        root.addWidget(self.dropped_label)

        self.view = _ZoomGraphicsView()
        root.addWidget(self.view, 1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_fit.clicked.connect(self._fit)
        self.btn_zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        self.btn_zoom_out.clicked.connect(lambda: self.view.scale(1 / 1.2, 1 / 1.2))
        self.btn_save_svg.clicked.connect(self._save_svg)
        self.scale_slider.valueChanged.connect(self._on_scale_change)

        state.document_loaded.connect(self.refresh)
        self.refresh()

    # ---- controls ------------------------------------------------------

    def _on_scale_change(self, value: int) -> None:
        scale = value / 100.0
        self.scale_value_label.setText(f"{scale:.2f}×")
        self.refresh()

    def _on_layer_toggle(self) -> None:
        for layer, cb in self._layer_checks.items():
            self._visibility[layer] = cb.isChecked()
        self.refresh()

    def _current_options(self) -> PreviewOptions:
        scale = self.scale_slider.value() / 100.0
        return PreviewOptions(
            label_scale=scale,
            layer_visibility=dict(self._visibility),
            suppress_overlap=True,
            auto_scale=True,
        )

    # ---- render --------------------------------------------------------

    def refresh(self) -> None:
        doc = self._state.current_document
        if doc is None:
            self.view.setScene(None)
            self.info_label.setText("No document loaded.")
            self.dropped_label.setText("")
            for b in (self.btn_fit, self.btn_zoom_in, self.btn_zoom_out, self.btn_save_svg):
                b.setEnabled(False)
            return
        options = self._current_options()
        scene = build_scene(doc, options)
        self.view.setScene(scene)
        for b in (self.btn_fit, self.btn_zoom_in, self.btn_zoom_out, self.btn_save_svg):
            b.setEnabled(True)
        self._fit()
        kind = self._state.doc_type()
        self.info_label.setText(f"{kind.upper()} — {self._state.doc_name()}")
        if options.dropped_labels > 0:
            self.dropped_label.setText(
                f"Note: {options.dropped_labels} label(s) hidden to reduce clutter. "
                "Increase Label scale or zoom in to inspect."
            )
        else:
            self.dropped_label.setText("")

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
