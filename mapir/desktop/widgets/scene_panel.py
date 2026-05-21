"""Scene Mode page — read-only scene summary and entity tables."""

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

from ...core.models import SceneIR
from ..state import AppState


class ScenePage(QWidget):
    render_requested = Signal()
    export_obj_requested = Signal()

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Scene Mode")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Read-only view of a SceneIR document. Full procedural scene "
            "generation is not implemented yet."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.warning = QLabel()
        self.warning.setProperty("role", "muted")
        self.warning.setWordWrap(True)
        root.addWidget(self.warning)

        summary_box = QGroupBox("Summary")
        self.summary = QGridLayout(summary_box)
        self.summary.setHorizontalSpacing(20)
        self.summary.setVerticalSpacing(4)
        root.addWidget(summary_box)
        self._summary_rows: list[tuple[QLabel, QLabel]] = []

        # Two side-by-side tables: zones + entrances
        upper = QHBoxLayout()
        upper.setSpacing(12)

        z_group = QGroupBox("Zones")
        z_layout = QVBoxLayout(z_group)
        self.zones_table = QTableWidget(0, 3)
        self.zones_table.setHorizontalHeaderLabels(["ID", "Name", "Type"])
        self.zones_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.zones_table.verticalHeader().setVisible(False)
        z_layout.addWidget(self.zones_table)
        upper.addWidget(z_group)

        e_group = QGroupBox("Entrances")
        e_layout = QVBoxLayout(e_group)
        self.entrances_table = QTableWidget(0, 3)
        self.entrances_table.setHorizontalHeaderLabels(["ID", "Name", "Type"])
        self.entrances_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.entrances_table.verticalHeader().setVisible(False)
        e_layout.addWidget(self.entrances_table)
        upper.addWidget(e_group)
        root.addLayout(upper)

        # Lower: objects + markers
        lower = QHBoxLayout()
        lower.setSpacing(12)

        o_group = QGroupBox("Objects")
        o_layout = QVBoxLayout(o_group)
        self.objects_table = QTableWidget(0, 4)
        self.objects_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Size"])
        self.objects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.objects_table.verticalHeader().setVisible(False)
        o_layout.addWidget(self.objects_table)
        lower.addWidget(o_group)

        m_group = QGroupBox("Gameplay markers")
        m_layout = QVBoxLayout(m_group)
        self.markers_table = QTableWidget(0, 3)
        self.markers_table.setHorizontalHeaderLabels(["ID", "Type", "Position"])
        self.markers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.markers_table.verticalHeader().setVisible(False)
        m_layout.addWidget(self.markers_table)
        lower.addWidget(m_group)
        root.addLayout(lower)

        actions = QHBoxLayout()
        self.btn_render = QPushButton("Render Scene Preview")
        self.btn_render.setProperty("role", "primary")
        self.btn_export = QPushButton("Export Scene OBJ")
        self.btn_render.clicked.connect(self.render_requested.emit)
        self.btn_export.clicked.connect(self.export_obj_requested.emit)
        actions.addWidget(self.btn_render)
        actions.addWidget(self.btn_export)
        actions.addStretch(1)
        root.addLayout(actions)

        state.document_loaded.connect(self._refresh)
        self._refresh()

    def _set_summary(self, items: list[tuple[str, str]]) -> None:
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
        if not isinstance(doc, SceneIR):
            self.warning.setText(
                "The current document is not a SceneIR. Load a scene example "
                "or switch to World Mode."
            )
            self._set_summary([])
            for t in (
                self.zones_table,
                self.entrances_table,
                self.objects_table,
                self.markers_table,
            ):
                t.setRowCount(0)
            self.btn_render.setEnabled(False)
            self.btn_export.setEnabled(False)
            return

        self.warning.setText("")
        self.btn_render.setEnabled(True)
        self.btn_export.setEnabled(True)
        self._set_summary(
            [
                ("Scene ID", doc.scene_id),
                ("Name", doc.name),
                ("Type", doc.scene_type.value),
                ("Preset", doc.preset.value),
                ("Standalone", "yes" if doc.standalone else "no"),
                (
                    "Bounds",
                    f"{doc.bounds.width_m:.0f} × {doc.bounds.depth_m:.0f} × {doc.bounds.height_m:.0f} m",
                ),
                ("Theme", doc.theme),
                ("Zones", str(len(doc.zones))),
                ("Entrances", str(len(doc.entrances))),
                ("Paths", str(len(doc.paths))),
                ("Objects", str(len(doc.objects))),
                ("Markers", str(len(doc.gameplay_markers))),
                ("Constraints", str(len(doc.constraints))),
            ]
        )

        self.zones_table.setRowCount(len(doc.zones))
        for r, z in enumerate(doc.zones):
            self.zones_table.setItem(r, 0, QTableWidgetItem(z.id))
            self.zones_table.setItem(r, 1, QTableWidgetItem(z.name))
            self.zones_table.setItem(r, 2, QTableWidgetItem(z.zone_type.value))

        self.entrances_table.setRowCount(len(doc.entrances))
        for r, e in enumerate(doc.entrances):
            self.entrances_table.setItem(r, 0, QTableWidgetItem(e.id))
            self.entrances_table.setItem(r, 1, QTableWidgetItem(e.name))
            self.entrances_table.setItem(r, 2, QTableWidgetItem(e.entrance_type.value))

        self.objects_table.setRowCount(len(doc.objects))
        for r, o in enumerate(doc.objects):
            self.objects_table.setItem(r, 0, QTableWidgetItem(o.id))
            self.objects_table.setItem(r, 1, QTableWidgetItem(o.name))
            self.objects_table.setItem(r, 2, QTableWidgetItem(o.object_type.value))
            self.objects_table.setItem(
                r,
                3,
                QTableWidgetItem(
                    f"{o.size.width_m:.1f}×{o.size.depth_m:.1f}×{o.size.height_m:.1f}"
                ),
            )

        self.markers_table.setRowCount(len(doc.gameplay_markers))
        for r, m in enumerate(doc.gameplay_markers):
            self.markers_table.setItem(r, 0, QTableWidgetItem(m.id))
            self.markers_table.setItem(r, 1, QTableWidgetItem(m.marker_type.value))
            self.markers_table.setItem(
                r, 2, QTableWidgetItem(f"({m.position.x:.1f}, {m.position.y:.1f})")
            )
