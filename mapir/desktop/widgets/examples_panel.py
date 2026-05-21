"""Examples browser — lists bundled worlds and scenes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...utils.paths import examples_dir
from ..state import AppState


class ExamplesPage(QWidget):
    error_signal = Signal(str, str)

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Bundled Examples")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Double-click a file to load it. The document will be validated automatically."
        )
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Size"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setColumnWidth(0, 360)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.tree, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.btn_load = QPushButton("Load selected")
        self.btn_load.setProperty("role", "primary")
        self.btn_load.clicked.connect(self._load_selected)
        bottom.addWidget(self.btn_load)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        bottom.addWidget(self.btn_refresh)
        bottom.addStretch(1)
        self.path_hint = QLabel()
        self.path_hint.setProperty("role", "muted")
        bottom.addWidget(self.path_hint)
        root.addLayout(bottom)

        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        base = examples_dir()
        self.path_hint.setText(str(base))
        groups = [
            ("Worlds", base / "worlds"),
            ("Scenes", base / "scenes"),
            ("Assets", base / "assets"),
        ]
        for label, folder in groups:
            parent = QTreeWidgetItem([label, ""])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            self.tree.addTopLevelItem(parent)
            parent.setExpanded(True)
            if folder.is_dir():
                for path in sorted(folder.glob("*.json")):
                    size_kb = max(1, path.stat().st_size // 1024)
                    child = QTreeWidgetItem([path.name, f"{size_kb} KB"])
                    child.setData(0, Qt.UserRole, str(path))
                    parent.addChild(child)
            if parent.childCount() == 0:
                parent.addChild(QTreeWidgetItem(["(empty)", ""]))

    def _on_double_click(self, item: QTreeWidgetItem, _col: int) -> None:
        path_str = item.data(0, Qt.UserRole)
        if path_str:
            self._load(Path(path_str))

    def _load_selected(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        path_str = item.data(0, Qt.UserRole)
        if path_str:
            self._load(Path(path_str))

    def _load(self, path: Path) -> None:
        try:
            self._state.load_json_file(path)
        except Exception as exc:  # surface error, don't crash
            self.error_signal.emit(str(path), str(exc))
