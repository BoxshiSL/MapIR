"""World Mode page — read-only world summary, districts, scene slots."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models import WorldIR
from ..state import AppState


class WorldPage(QWidget):
    render_requested = Signal()
    export_obj_requested = Signal()

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("World Mode")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Read-only view of a WorldIR document. Procedural generation is not "
            "implemented yet — content comes from the loaded JSON."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.warning = QLabel()
        self.warning.setProperty("role", "muted")
        self.warning.setWordWrap(True)
        root.addWidget(self.warning)

        # Summary grid
        self.summary = QGridLayout()
        self.summary.setHorizontalSpacing(20)
        self.summary.setVerticalSpacing(4)
        summary_box = QGroupBox("Summary")
        summary_box.setLayout(self.summary)
        root.addWidget(summary_box)
        self._summary_rows: list[tuple[QLabel, QLabel]] = []

        # Districts table
        d_group = QGroupBox("Districts")
        d_layout = QVBoxLayout(d_group)
        self.districts_table = QTableWidget(0, 4)
        self.districts_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Density"])
        self.districts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.districts_table.verticalHeader().setVisible(False)
        d_layout.addWidget(self.districts_table)
        root.addWidget(d_group)

        # Scene slots table
        s_group = QGroupBox("Scene slots")
        s_layout = QVBoxLayout(s_group)
        self.slots_table = QTableWidget(0, 5)
        self.slots_table.setHorizontalHeaderLabels(
            ["ID", "Name", "District", "Size (m)", "Allowed scene types"]
        )
        self.slots_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.slots_table.verticalHeader().setVisible(False)
        s_layout.addWidget(self.slots_table)
        root.addWidget(s_group)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_render = QPushButton("Render World Preview")
        self.btn_render.setProperty("role", "primary")
        self.btn_export = QPushButton("Export World OBJ")
        self.btn_render.clicked.connect(self.render_requested.emit)
        self.btn_export.clicked.connect(self.export_obj_requested.emit)
        actions.addWidget(self.btn_render)
        actions.addWidget(self.btn_export)
        actions.addStretch(1)
        root.addLayout(actions)

        state.document_loaded.connect(self._refresh)
        self._refresh()

    def _set_summary(self, items: list[tuple[str, str]]) -> None:
        # rebuild grid
        for lbl, val in self._summary_rows:
            self.summary.removeWidget(lbl)
            lbl.deleteLater()
            self.summary.removeWidget(val)
            val.deleteLater()
        self._summary_rows = []
        for r, (k, v) in enumerate(items):
            row = r // 2
            col = (r % 2) * 2
            lbl = QLabel(f"{k}:")
            lbl.setProperty("role", "muted")
            val = QLabel(v)
            self.summary.addWidget(lbl, row, col)
            self.summary.addWidget(val, row, col + 1)
            self._summary_rows.append((lbl, val))

    def _refresh(self) -> None:
        doc = self._state.current_document
        if not isinstance(doc, WorldIR):
            self.warning.setText(
                "The current document is not a WorldIR. Switch to Scene Mode "
                "or load a world example to use this page."
            )
            self._set_summary([])
            self.districts_table.setRowCount(0)
            self.slots_table.setRowCount(0)
            self.btn_render.setEnabled(False)
            self.btn_export.setEnabled(False)
            return

        self.warning.setText(
            "Procedural world generation is not implemented yet. "
            "Use the Preview page for interactive 2D view, or Export for blockout outputs."
        )
        self.btn_render.setEnabled(True)
        self.btn_export.setEnabled(True)
        self._set_summary(
            [
                ("World ID", doc.world_id),
                ("Name", doc.name),
                ("Theme", doc.theme),
                ("Size", f"{doc.scale.width_m:.0f} × {doc.scale.depth_m:.0f} m"),
                ("Districts", str(len(doc.districts))),
                ("Roads", str(len(doc.roads))),
                ("Water bodies", str(len(doc.water_bodies))),
                ("POIs", str(len(doc.pois))),
                ("Scene slots", str(len(doc.scene_slots))),
                ("Constraints", str(len(doc.constraints))),
            ]
        )

        self.districts_table.setRowCount(len(doc.districts))
        for r, d in enumerate(doc.districts):
            self.districts_table.setItem(r, 0, QTableWidgetItem(d.id))
            self.districts_table.setItem(r, 1, QTableWidgetItem(d.name))
            self.districts_table.setItem(r, 2, QTableWidgetItem(d.district_type))
            self.districts_table.setItem(r, 3, QTableWidgetItem(d.density.value))

        self.slots_table.setRowCount(len(doc.scene_slots))
        for r, s in enumerate(doc.scene_slots):
            self.slots_table.setItem(r, 0, QTableWidgetItem(s.id))
            self.slots_table.setItem(r, 1, QTableWidgetItem(s.name))
            self.slots_table.setItem(r, 2, QTableWidgetItem(s.district_id or ""))
            self.slots_table.setItem(
                r, 3, QTableWidgetItem(f"{s.size.width_m:.0f}×{s.size.depth_m:.0f}")
            )
            allowed = ", ".join(t.value for t in (s.allowed_scene_types or [])) or "—"
            self.slots_table.setItem(r, 4, QTableWidgetItem(allowed))
