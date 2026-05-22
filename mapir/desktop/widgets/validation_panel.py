"""Validation page — colour-coded issue list.

v0.5: in addition to the structural validators from ``mapir.core.validation``,
the page now also runs the design-aware validators from
``mapir.design.validators`` when a ``GeneratedLayout`` is available.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...design.validators import run_design_validators
from ...generation.gameplay_metrics import GameplayMetrics
from ..state import AppState
from ..theme import PALETTE

_SEVERITY_COLORS = {
    "error": PALETTE["danger"],
    "warning": PALETTE["warning"],
    "info": PALETTE["accent_2"],
}


class ValidationPage(QWidget):
    revalidate_requested = Signal()

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Validation")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Structural validation comes from Pydantic on load; semantic "
            "validation is the rules engine in mapir/core/validation.py."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.status_label = QLabel()
        self.status_label.setProperty("role", "cardTitle")
        header.addWidget(self.status_label)
        header.addStretch(1)
        self.counts_label = QLabel()
        self.counts_label.setProperty("role", "muted")
        header.addWidget(self.counts_label)
        self.btn_revalidate = QPushButton("Validate Current (F5)")
        self.btn_revalidate.setProperty("role", "primary")
        self.btn_revalidate.clicked.connect(self.revalidate_requested.emit)
        header.addWidget(self.btn_revalidate)
        root.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Severity", "Category", "Code", "Message", "Path / Rule"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        root.addWidget(self.table, 1)

        state.validation_changed.connect(self._refresh)
        state.document_loaded.connect(self._refresh)
        state.layout_changed.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        report = self._state.validation_report
        if report is None:
            self.status_label.setText("No document")
            self.counts_label.setText("")
            self.table.setRowCount(0)
            self.btn_revalidate.setEnabled(False)
            return
        self.btn_revalidate.setEnabled(True)
        if report.is_valid:
            self.status_label.setText("✔ VALID")
            self.status_label.setStyleSheet(f"color: {PALETTE['success']}; font-weight: 700;")
        else:
            self.status_label.setText("✘ INVALID")
            self.status_label.setStyleSheet(f"color: {PALETTE['danger']}; font-weight: 700;")

        # v0.5 — also run the design validators when a layout is available.
        design_report = None
        try:
            doc = self._state.current_document
            layout = getattr(self._state, "current_layout", None)
            if doc is not None:
                metrics = (
                    layout.metrics if layout is not None else GameplayMetrics()
                )
                design_report = run_design_validators(doc, layout, metrics)
        except Exception:  # noqa: BLE001 — design validation should never crash the UI
            design_report = None

        n_design = len(design_report.warnings) if design_report else 0
        self.counts_label.setText(
            f"structural: errors={len(report.errors)}  "
            f"warnings={len(report.warnings)}  infos={len(report.infos)}    "
            f"design: {n_design}"
        )

        rows: list[tuple[str, str, str, str, str]] = []
        for issue in report.all():
            rows.append(
                (
                    issue.severity.value,
                    "structural",
                    issue.code,
                    issue.message,
                    issue.path,
                )
            )
        if design_report is not None:
            for w in design_report.warnings:
                rows.append(
                    (
                        w.severity.value,
                        w.category.value,
                        w.code,
                        w.message,
                        w.rule_id or w.target_id or "",
                    )
                )

        self.table.setRowCount(len(rows))
        for r, (sev, category, code, message, path) in enumerate(rows):
            sev_item = QTableWidgetItem(sev.upper())
            color = QColor(_SEVERITY_COLORS.get(sev, PALETTE["muted"]))
            sev_item.setForeground(QBrush(color))
            font = sev_item.font()
            font.setBold(True)
            sev_item.setFont(font)
            sev_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, sev_item)
            self.table.setItem(r, 1, QTableWidgetItem(category))
            self.table.setItem(r, 2, QTableWidgetItem(code))
            self.table.setItem(r, 3, QTableWidgetItem(message))
            self.table.setItem(r, 4, QTableWidgetItem(path))
