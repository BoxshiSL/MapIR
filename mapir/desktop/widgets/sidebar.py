"""Vertical sidebar navigation."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

# Display order = stack index order. Keep in sync with MainWindow.
NAV_ITEMS: list[tuple[str, str]] = [
    ("dashboard", "Dashboard"),
    ("examples", "Examples"),
    ("world", "World Mode"),
    ("scene", "Scene Mode"),
    ("inspector", "Inspector"),
    ("preview", "Preview"),
    ("validation", "Validation"),
    ("export", "Export"),
    ("llm_draft", "LLM Draft"),
    ("settings", "Settings / About"),
]


class Sidebar(QFrame):
    page_selected = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        brand = QLabel("MapIR Studio")
        brand.setStyleSheet("font-weight: 700; padding: 4px 18px; font-size: 15px;")
        layout.addWidget(brand)

        subtitle = QLabel("Structured world & scene IR")
        subtitle.setStyleSheet("color: #9aa4b2; padding: 0 18px 12px 18px; font-size: 11px;")
        layout.addWidget(subtitle)

        self.list = QListWidget()
        self.list.setObjectName("SidebarList")
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setIconSize(QSize(16, 16))
        for _key, label in NAV_ITEMS:
            item = QListWidgetItem(label)
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        self.list.currentRowChanged.connect(self.page_selected.emit)
        layout.addWidget(self.list, 1)

        from ... import __version__

        footer = QLabel(f"v{__version__} · Desktop")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(footer)

    def set_current(self, index: int) -> None:
        self.list.setCurrentRow(index)
