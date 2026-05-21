"""Dashboard page — status cards and quick actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core.models import SceneIR, WorldIR
from ..state import AppState


class _Card(QFrame):
    def __init__(self, title: str, value: str = "—", hint: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.title = QLabel(title)
        self.title.setProperty("role", "cardTitle")
        layout.addWidget(self.title)

        self.value = QLabel(value)
        self.value.setProperty("role", "cardValue")
        layout.addWidget(self.value)

        self.hint = QLabel(hint)
        self.hint.setProperty("role", "cardHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addStretch(1)

    def update_value(self, value: str, hint: str = "") -> None:
        self.value.setText(value)
        if hint:
            self.hint.setText(hint)


class DashboardPage(QWidget):
    open_file_requested = Signal()
    open_example_requested = Signal()
    validate_requested = Signal()
    render_svg_requested = Signal()
    export_obj_requested = Signal()
    export_blender_requested = Signal()
    show_examples_requested = Signal()

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("MapIR Studio")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel("Structured World & Scene IR Toolchain — v0.3.0")
        subtitle.setProperty("role", "pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        # Status cards
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)

        self.card_doc = _Card("Document", "none", "Open a JSON file or pick an example.")
        self.card_type = _Card("IR type", "—", "Detected from ir_type field.")
        self.card_valid = _Card("Validation", "—", "Structural and semantic checks.")
        self.card_errors = _Card("Errors", "0", "Issues that block rendering.")
        self.card_warnings = _Card("Warnings", "0", "Heuristic findings.")
        self.card_exports = _Card("Last export", "—", "Files written from the Export page.")

        for col, card in enumerate((self.card_doc, self.card_type, self.card_valid)):
            cards_grid.addWidget(card, 0, col)
        for col, card in enumerate((self.card_errors, self.card_warnings, self.card_exports)):
            cards_grid.addWidget(card, 1, col)
        for c in range(3):
            cards_grid.setColumnStretch(c, 1)
        root.addLayout(cards_grid)

        # Quick actions
        actions_title = QLabel("Quick actions")
        actions_title.setProperty("role", "cardTitle")
        root.addWidget(actions_title)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_open_example = QPushButton("Open Example")
        self.btn_open_example.setProperty("role", "primary")
        self.btn_open_file = QPushButton("Open JSON…")
        self.btn_validate = QPushButton("Validate (F5)")
        self.btn_render = QPushButton("Render SVG")
        self.btn_export_obj = QPushButton("Export OBJ")
        self.btn_export_blender = QPushButton("Export Blender")

        for b in (
            self.btn_open_example,
            self.btn_open_file,
            self.btn_validate,
            self.btn_render,
            self.btn_export_obj,
            self.btn_export_blender,
        ):
            b.setMinimumHeight(34)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            actions.addWidget(b)
        root.addLayout(actions)

        self.btn_open_example.clicked.connect(self.show_examples_requested.emit)
        self.btn_open_file.clicked.connect(self.open_file_requested.emit)
        self.btn_validate.clicked.connect(self.validate_requested.emit)
        self.btn_render.clicked.connect(self.render_svg_requested.emit)
        self.btn_export_obj.clicked.connect(self.export_obj_requested.emit)
        self.btn_export_blender.clicked.connect(self.export_blender_requested.emit)

        # Intro text
        hint = QLabel(
            "MapIR Studio is a Windows-first desktop tool for working with structured "
            "game space descriptions: cities, regions, scenes, interiors, and the "
            "scene slots that connect them.\n\n"
            "Use the sidebar to browse examples, inspect raw IR, preview layouts, and "
            "export blockouts."
        )
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignTop)
        root.addWidget(hint)
        root.addStretch(1)

        state.document_loaded.connect(self._refresh)
        state.validation_changed.connect(self._refresh)
        state.export_completed.connect(self._on_export)
        self._refresh()

    def _refresh(self) -> None:
        state = self._state
        if state.current_document is None:
            self.card_doc.update_value("none", "Open a JSON file or pick an example.")
            self.card_type.update_value("—", "Detected from ir_type field.")
            self.card_valid.update_value("—", "Structural and semantic checks.")
            self.card_errors.update_value("0", "—")
            self.card_warnings.update_value("0", "—")
            for b in (
                self.btn_validate,
                self.btn_render,
                self.btn_export_obj,
                self.btn_export_blender,
            ):
                b.setEnabled(False)
            return

        path = state.current_path
        self.card_doc.update_value(
            path.name if path else "unsaved",
            str(path) if path else "in-memory document",
        )
        if isinstance(state.current_document, WorldIR):
            self.card_type.update_value("World", state.current_document.theme)
        elif isinstance(state.current_document, SceneIR):
            self.card_type.update_value(
                "Scene",
                f"{state.current_document.scene_type.value} / {state.current_document.preset.value}",
            )

        report = state.validation_report
        if report is None:
            self.card_valid.update_value("—", "Press Validate to run checks.")
        elif report.is_valid:
            self.card_valid.update_value("OK", "All required checks pass.")
        else:
            self.card_valid.update_value("FAIL", "See Validation page for details.")
        self.card_errors.update_value(str(len(report.errors)) if report else "?")
        self.card_warnings.update_value(str(len(report.warnings)) if report else "?")

        for b in (self.btn_validate, self.btn_render, self.btn_export_obj, self.btn_export_blender):
            b.setEnabled(True)

    def _on_export(self, kind: str, path_str: str) -> None:
        from pathlib import Path

        self.card_exports.update_value(kind.upper(), Path(path_str).name)
