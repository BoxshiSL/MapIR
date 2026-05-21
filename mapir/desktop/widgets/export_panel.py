"""Export page — buttons for SVG / OBJ / Blender script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.paths import ensure_output_dirs, output_dir
from ..state import AppState


class ExportPage(QWidget):
    open_output_requested = Signal()

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Export")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Write the current document out as SVG (2D preview), "
            "OBJ (blockout for any DCC), or a Blender Python script."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        out_box = QGroupBox("Output directory")
        out_layout = QHBoxLayout(out_box)
        self.out_path_label = QLabel(str(output_dir() / "desktop_exports"))
        self.out_path_label.setProperty("role", "muted")
        out_layout.addWidget(self.out_path_label, 1)
        self.btn_open_folder = QPushButton("Open in Explorer")
        self.btn_open_folder.clicked.connect(self._open_folder)
        out_layout.addWidget(self.btn_open_folder)
        root.addWidget(out_box)

        # Action buttons
        actions = QGridLayout()
        actions.setHorizontalSpacing(12)
        actions.setVerticalSpacing(12)

        self.btn_svg = QPushButton("Export SVG (2D preview)")
        self.btn_svg.setProperty("role", "primary")
        self.btn_obj = QPushButton("Export OBJ (blockout)")
        self.btn_blender = QPushButton("Export Blender Python script")

        for col, b in enumerate((self.btn_svg, self.btn_obj, self.btn_blender)):
            b.setMinimumHeight(40)
            actions.addWidget(b, 0, col)
        root.addLayout(actions)

        self.btn_svg.clicked.connect(self._export_svg)
        self.btn_obj.clicked.connect(self._export_obj)
        self.btn_blender.clicked.connect(self._export_blender)

        # Recent exports log
        log_box = QGroupBox("Recent exports")
        log_layout = QVBoxLayout(log_box)
        self.log_label = QLabel("(no exports yet in this session)")
        self.log_label.setProperty("role", "muted")
        self.log_label.setWordWrap(True)
        log_layout.addWidget(self.log_label)
        root.addWidget(log_box)
        root.addStretch(1)

        state.document_loaded.connect(self._refresh)
        state.export_completed.connect(self._on_export_completed)
        self._refresh()

    def _refresh(self) -> None:
        has_doc = self._state.current_document is not None
        for b in (self.btn_svg, self.btn_obj, self.btn_blender):
            b.setEnabled(has_doc)

    def _on_export_completed(self, kind: str, path_str: str) -> None:
        prev = self.log_label.text()
        if prev.startswith("(no exports"):
            prev = ""
        line = f"{kind.upper()}: {path_str}"
        self.log_label.setText((prev + "\n" + line).strip())

    def _pick(self, kind: str, suffix: str) -> Path | None:
        ensure_output_dirs()
        default = self._state.default_export_path(kind)
        chosen, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {kind.upper()}",
            str(default),
            f"{kind.upper()} (*.{suffix});;All files (*)",
        )
        return Path(chosen) if chosen else None

    def _export_svg(self) -> None:
        path = self._pick("svg", "svg")
        if path is None:
            return
        try:
            self._state.export_svg(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export SVG failed", str(exc))

    def _export_obj(self) -> None:
        path = self._pick("obj", "obj")
        if path is None:
            return
        try:
            self._state.export_obj(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export OBJ failed", str(exc))

    def _export_blender(self) -> None:
        path = self._pick("blender", "py")
        if path is None:
            return
        try:
            self._state.export_blender(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export Blender script failed", str(exc))

    def _open_folder(self) -> None:
        ensure_output_dirs()
        folder = output_dir() / "desktop_exports"
        if not folder.exists():
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(folder)])  # noqa: S603,S607
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(folder)])  # noqa: S603,S607
        except OSError as exc:
            QMessageBox.warning(self, "Open folder failed", str(exc))
