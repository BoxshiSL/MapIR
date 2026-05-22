"""Vertical sidebar navigation.

v0.5 reorganises the sidebar around the new guided creation workflow:
``Home → Templates → Canvas → Districts → Generation`` is the primary path.
``Preview``, ``Validation``, ``Export`` finish the loop. ``Inspector``, the
LLM Draft page, and the legacy ``World Mode`` / ``Scene Mode`` tables are
kept reachable but de-emphasised as advanced views.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

# Display order = stack index order. Keep in sync with MainWindow.
# ``flag`` is purely cosmetic — "primary" items get a brighter style hook so the
# new workflow is visually obvious.
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("home", "Home", "primary"),
    ("templates", "New / Templates", "primary"),
    ("canvas", "Canvas", "primary"),
    ("districts", "Districts", "primary"),
    ("generation", "Generation", "primary"),
    ("preview", "Preview", "primary"),
    ("validation", "Validation", "primary"),
    ("export", "Export", "primary"),
    ("inspector", "Inspector (Advanced)", "advanced"),
    ("llm_draft", "LLM Draft (Advanced)", "advanced"),
    ("world", "World Mode (Summary)", "advanced"),
    ("scene", "Scene Mode (Summary)", "advanced"),
    ("settings", "Settings / About", "advanced"),
]


class Sidebar(QFrame):
    page_selected = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(230)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        brand = QLabel("MapIR Studio")
        brand.setStyleSheet("font-weight: 700; padding: 4px 18px; font-size: 15px;")
        layout.addWidget(brand)

        subtitle = QLabel("Guided world & scene design")
        subtitle.setStyleSheet("color: #9aa4b2; padding: 0 18px 12px 18px; font-size: 11px;")
        layout.addWidget(subtitle)

        self.list = QListWidget()
        self.list.setObjectName("SidebarList")
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setIconSize(QSize(16, 16))
        for _key, label, flag in NAV_ITEMS:
            item = QListWidgetItem(label)
            if flag == "advanced":
                # Subtle italic for advanced/legacy pages so the workflow path
                # reads first.
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
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
