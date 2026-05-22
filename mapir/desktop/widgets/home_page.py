"""Home — the v0.5 landing page.

Replaces the v0.4 ``DashboardPage``. Creation-focused: big buttons to start a
new project from a World / Scene / Interior template, plus the usual
"open existing JSON" entry point. The old Dashboard module remains in the
repo for backwards compatibility but is no longer wired into the sidebar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState


class _ActionCard(QFrame):
    """A clickable card with a title, a short hint, and one or two buttons."""

    def __init__(
        self,
        title: str,
        hint: str,
        primary_label: str,
        secondary_label: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HomeCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(140)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        t = QLabel(title)
        t.setProperty("role", "cardTitle")
        t.setStyleSheet("font-weight: 600; font-size: 14px;")
        lay.addWidget(t)

        h = QLabel(hint)
        h.setWordWrap(True)
        h.setProperty("role", "muted")
        h.setStyleSheet("color: #aab4c0;")
        lay.addWidget(h, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.primary = QPushButton(primary_label)
        self.primary.setProperty("role", "primary")
        row.addWidget(self.primary)
        if secondary_label:
            self.secondary = QPushButton(secondary_label)
            row.addWidget(self.secondary)
        else:
            self.secondary = None
        row.addStretch(1)
        lay.addLayout(row)


class HomePage(QWidget):
    """Creation-focused entry point. Emits intents; MainWindow handles routing."""

    new_project_requested = Signal(str)  # initial document_type: "" or "world"/"scene"/"interior"
    open_file_requested = Signal()
    show_templates_requested = Signal()
    validate_requested = Signal()
    export_requested = Signal()

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("MapIR Studio")
        title.setProperty("role", "pageTitle")
        root.addWidget(title)
        subtitle = QLabel(
            "Design game worlds, scenes, and interiors with templates, a "
            "sketch canvas, and gameplay-aware generation. Start a new "
            "project or open an existing one."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(subtitle)

        # Status card — what's currently loaded.
        self._status = QLabel()
        self._status.setProperty("role", "muted")
        self._status.setWordWrap(True)
        self._refresh_status()
        root.addWidget(self._status)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.card_world = _ActionCard(
            "New World",
            "Pick a world template (modern island city, magical forest, "
            "rural compound, cyberpunk district). Set size, gameplay "
            "profiles, theme, and local LLM, then sketch on the canvas.",
            "Create World…",
        )
        self.card_scene = _ActionCard(
            "New Scene",
            "Pick a scene template (industrial port, urban alley, forest "
            "checkpoint, rural compound, rooftop). Designed for "
            "shooter / stealth / parkour encounters.",
            "Create Scene…",
        )
        self.card_interior = _ActionCard(
            "New Interior",
            "Pick an interior template (warehouse, nightclub, office floor, "
            "apartment block). Interiors are a SceneIR subtype.",
            "Create Interior…",
        )
        self.card_open = _ActionCard(
            "Open Existing",
            "Open a MapIR JSON file from disk (WorldIR / SceneIR / "
            "Interior). All v0.4 documents remain compatible.",
            "Open JSON…",
        )
        self.card_templates = _ActionCard(
            "Browse Templates",
            "13 neutral templates across World / Scene / Interior. "
            "Filter by genre, gameplay profile, or size.",
            "Open Gallery",
        )
        self.card_tools = _ActionCard(
            "Tools",
            "Validate the current document or jump straight to Export.",
            "Validate",
            secondary_label="Export…",
        )

        grid.addWidget(self.card_world, 0, 0)
        grid.addWidget(self.card_scene, 0, 1)
        grid.addWidget(self.card_interior, 0, 2)
        grid.addWidget(self.card_open, 1, 0)
        grid.addWidget(self.card_templates, 1, 1)
        grid.addWidget(self.card_tools, 1, 2)

        root.addLayout(grid)
        root.addStretch(1)

        # Wire signals
        self.card_world.primary.clicked.connect(lambda: self.new_project_requested.emit("world"))
        self.card_scene.primary.clicked.connect(lambda: self.new_project_requested.emit("scene"))
        self.card_interior.primary.clicked.connect(
            lambda: self.new_project_requested.emit("interior")
        )
        self.card_open.primary.clicked.connect(self.open_file_requested.emit)
        self.card_templates.primary.clicked.connect(self.show_templates_requested.emit)
        self.card_tools.primary.clicked.connect(self.validate_requested.emit)
        if self.card_tools.secondary is not None:
            self.card_tools.secondary.clicked.connect(self.export_requested.emit)

        state.document_loaded.connect(self._refresh_status)
        state.validation_changed.connect(self._refresh_status)

    def _refresh_status(self) -> None:
        doc = self._state.current_document
        if doc is None:
            self._status.setText("No document loaded.")
            return
        kind = self._state.doc_type().upper()
        name = self._state.doc_name()
        path = self._state.current_path
        path_part = f"  ·  {path}" if path else "  ·  (in-memory)"
        report = self._state.validation_report
        if report is None:
            badge = "LOADED"
        elif report.is_valid:
            badge = "VALID"
        elif report.warnings and not report.errors:
            badge = "WARN"
        else:
            badge = f"INVALID ({len(report.errors)} error(s))"
        tpl = self._state.current_template_id
        tpl_part = f"  ·  template={tpl}" if tpl else ""
        self._status.setText(f"Current: {kind} — {name} [{badge}]{path_part}{tpl_part}")
