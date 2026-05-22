"""Generation page — runs the v0.5 deterministic pipeline.

Stages are toggleable; ``Run All`` runs every enabled stage in order.
Stage status (``idle`` / ``ok`` / ``warn`` / ``fail``) and summary stats
come back from ``AppState.run_generation_pipeline``.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...generation.pipeline import PipelineStage
from ..state import AppState


_STAGE_LABELS: dict[PipelineStage, tuple[str, str]] = {
    PipelineStage.ZONING: ("Zoning plan", "Districts kept from sketch."),
    PipelineStage.ROADS: ("Roads", "Arterial / collector / local network."),
    PipelineStage.PARCELS: ("Parcels", "Subdivide districts along roads."),
    PipelineStage.BUILDINGS: ("Building footprints", "Footprints inside parcels."),
    PipelineStage.LANDMARKS: ("Landmarks", "Orientation anchors per major district."),
    PipelineStage.SCENE_SLOTS: ("Scene slots", "≥ 1 slot per major district."),
    PipelineStage.GUIDANCE: ("Guidance cues", "Leading lines, breadcrumbs (Phase C)."),
    PipelineStage.CONVERT_TO_IR: ("Convert to IR", "Materialise WorldIR/SceneIR."),
    PipelineStage.VALIDATE: ("Validate", "Structural + design rules."),
}


class GenerationPage(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Generation")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Staged deterministic pipeline. Toggle which stages to run, then "
            "click Run All. The pipeline reads the current SketchDocument "
            "and writes a GeneratedLayout + an updated IR."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.addWidget(QLabel("Enable"), 0, 0)
        grid.addWidget(QLabel("Stage"), 0, 1)
        grid.addWidget(QLabel("Description"), 0, 2)
        grid.addWidget(QLabel("Status"), 0, 3)

        self._rows: dict[PipelineStage, dict] = {}
        for i, stage in enumerate(PipelineStage, start=1):
            label, desc = _STAGE_LABELS[stage]
            cb = QCheckBox()
            cb.setChecked(True)
            grid.addWidget(cb, i, 0)
            grid.addWidget(QLabel(label), i, 1)
            d_label = QLabel(desc)
            d_label.setProperty("role", "muted")
            d_label.setWordWrap(True)
            grid.addWidget(d_label, i, 2)
            status = QLabel("—")
            status.setStyleSheet("color: #aab4c0;")
            grid.addWidget(status, i, 3)
            self._rows[stage] = {"enabled": cb, "status": status}
        root.addLayout(grid)

        actions = QHBoxLayout()
        self.btn_run_all = QPushButton("Run All")
        self.btn_run_all.setProperty("role", "primary")
        self.btn_run_all.setEnabled(False)
        actions.addWidget(self.btn_run_all)
        self.btn_reset = QPushButton("Re-enable all stages")
        actions.addWidget(self.btn_reset)
        actions.addStretch(1)
        root.addLayout(actions)

        root.addWidget(QLabel("Log:"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Generation output will appear here.")
        self._log.setFixedHeight(220)
        root.addWidget(self._log)
        root.addStretch(1)

        self.btn_run_all.clicked.connect(self._run_all)
        self.btn_reset.clicked.connect(self._reset_stages)
        state.sketch_changed.connect(self._refresh_enabled)
        state.layout_changed.connect(self._refresh_status_from_layout)
        self._refresh_enabled()

    # ---- helpers -------------------------------------------------------

    def _refresh_enabled(self) -> None:
        has_sketch = self._state.current_sketch is not None
        self.btn_run_all.setEnabled(has_sketch)

    def _reset_stages(self) -> None:
        for row in self._rows.values():
            row["enabled"].setChecked(True)
            row["status"].setText("—")

    def _enabled_stages(self) -> list[PipelineStage]:
        return [stage for stage, row in self._rows.items() if row["enabled"].isChecked()]

    def _set_status(self, stage: PipelineStage, text: str, *, kind: str = "info") -> None:
        row = self._rows[stage]
        colors = {
            "info": "#aab4c0",
            "ok": "#27ae60",
            "warn": "#f1c40f",
            "fail": "#c0392b",
        }
        row["status"].setText(text)
        row["status"].setStyleSheet(f"color: {colors.get(kind, '#aab4c0')};")

    def _run_all(self) -> None:
        stages = self._enabled_stages()
        if not stages:
            self._log.appendPlainText("[warn] no stages enabled.")
            return
        for stage in stages:
            self._set_status(stage, "running…")
        msg = self._state.run_generation_pipeline(stages=stages)
        self._log.appendPlainText(msg)
        # Stage statuses come back via _refresh_status_from_layout()

    def _refresh_status_from_layout(self) -> None:
        layout = self._state.current_layout
        if layout is None:
            return
        # Reset every row first
        for stage in PipelineStage:
            self._set_status(stage, "—")
        for sr in layout.stage_results:
            try:
                stage = PipelineStage(sr.stage_id)
            except ValueError:
                continue
            kind = (
                "ok"
                if sr.status.value == "ok"
                else "warn"
                if sr.status.value == "warn"
                else "fail"
                if sr.status.value == "fail"
                else "info"
            )
            text = sr.status.value.upper()
            if sr.notes:
                text = f"{sr.status.value.upper()} · {sr.notes}"
            self._set_status(stage, text, kind=kind)
            if sr.errors:
                self._log.appendPlainText(f"[{sr.stage_id}] errors: {sr.errors[:3]}")
            if sr.warnings:
                self._log.appendPlainText(f"[{sr.stage_id}] warnings: {sr.warnings[:3]}")
        self._log.appendPlainText(
            f"layout: {len(layout.roads)} roads · {len(layout.parcels)} parcels · "
            f"{len(layout.buildings)} buildings · {len(layout.landmarks)} landmarks · "
            f"{len(layout.scene_slots)} scene slots · {len(layout.guidance_cues)} cues"
        )
