"""Inspector page — read-only monospaced JSON viewer + small summary."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState


class InspectorPage(QWidget):
    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Inspector")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Raw JSON of the loaded document. Read-only in v0.3 — editing will "
            "land in v0.4 with explicit Apply/Validate."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)

        # Left: summary
        left = QGroupBox("Summary")
        left_layout = QVBoxLayout(left)
        self.summary_label = QLabel("No document loaded.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.summary_label.setAlignment(Qt.AlignTop)
        left_layout.addWidget(self.summary_label, 1)

        # Right: JSON viewer
        right = QGroupBox("Raw JSON")
        right_layout = QVBoxLayout(right)
        self.json_view = QPlainTextEdit()
        self.json_view.setProperty("role", "mono")
        self.json_view.setReadOnly(True)
        font = QFont("Cascadia Mono")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.json_view.setFont(font)
        right_layout.addWidget(self.json_view)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        state.document_loaded.connect(self._refresh)
        state.validation_changed.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        doc = self._state.current_document
        if doc is None:
            self.summary_label.setText("No document loaded.")
            self.json_view.setPlainText("")
            return

        path = self._state.current_path
        kind = self._state.doc_type().upper()
        report = self._state.validation_report
        lines = [
            f"Path: {path}" if path else "Path: (in-memory)",
            f"IR type: {kind}",
            f"Name: {self._state.doc_name()}",
        ]
        if report is not None:
            lines.append(
                f"Validation: {'OK' if report.is_valid else 'FAIL'} "
                f"(errors={len(report.errors)}, warnings={len(report.warnings)})"
            )
        self.summary_label.setText("\n".join(lines))
        self.json_view.setPlainText(self._state.raw_json_pretty())
