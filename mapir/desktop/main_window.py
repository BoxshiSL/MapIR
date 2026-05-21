"""Main window — top bar, sidebar, stacked pages, menubar, statusbar."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from .state import AppState
from .widgets.dashboard import DashboardPage
from .widgets.examples_panel import ExamplesPage
from .widgets.export_panel import ExportPage
from .widgets.inspector_panel import InspectorPage
from .widgets.llm_draft_panel import LLMDraftPanel
from .widgets.preview_panel import PreviewPage
from .widgets.scene_panel import ScenePage
from .widgets.settings_panel import SettingsPage
from .widgets.sidebar import NAV_ITEMS, Sidebar
from .widgets.validation_panel import ValidationPage
from .widgets.world_panel import WorldPage

PAGE_INDEX = {key: i for i, (key, _label) in enumerate(NAV_ITEMS)}


class _TopBar(QFrame):
    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(46)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        self.title = QLabel("MapIR Studio")
        self.title.setObjectName("TopBarTitle")
        self.path = QLabel("— no document —")
        self.path.setObjectName("TopBarPath")
        self.badge = QLabel("READY")
        self.badge.setObjectName("BadgeNeutral")
        self.badge.setAlignment(Qt.AlignCenter)
        self.version = QLabel(f"v{__version__}")
        self.version.setObjectName("TopBarVersion")

        layout.addWidget(self.title)
        layout.addWidget(self.path, 1)
        layout.addWidget(self.badge)
        layout.addWidget(self.version)

        state.document_loaded.connect(lambda: self._refresh(state))
        state.validation_changed.connect(lambda: self._refresh(state))

    def _refresh(self, state: AppState) -> None:
        if state.current_document is None:
            self.path.setText("— no document —")
            self.badge.setObjectName("BadgeNeutral")
            self.badge.setText("READY")
        else:
            self.path.setText(str(state.current_path) if state.current_path else "(in-memory)")
            report = state.validation_report
            if report is None:
                self.badge.setObjectName("BadgeNeutral")
                self.badge.setText("LOADED")
            elif report.is_valid:
                self.badge.setObjectName("BadgeOK")
                self.badge.setText("VALID")
            elif report.warnings and not report.errors:
                self.badge.setObjectName("BadgeWarn")
                self.badge.setText("WARN")
            else:
                self.badge.setObjectName("BadgeError")
                self.badge.setText("INVALID")
        # Force stylesheet re-evaluation after object-name swap
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)


class MainWindow(QMainWindow):
    def __init__(self, state: AppState | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"MapIR Studio  v{__version__}")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        self.state = state or AppState(self)

        # Top bar
        self.top_bar = _TopBar(self.state)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_selected.connect(self._on_nav)

        # Pages
        self.stack = QStackedWidget()
        self.dashboard = DashboardPage(self.state)
        self.examples = ExamplesPage(self.state)
        self.world = WorldPage(self.state)
        self.scene_page = ScenePage(self.state)
        self.inspector = InspectorPage(self.state)
        self.preview = PreviewPage(self.state)
        self.validation = ValidationPage(self.state)
        self.export = ExportPage(self.state)
        self.llm_draft = LLMDraftPanel(self.state)
        self.settings = SettingsPage()

        for page in (
            self.dashboard,
            self.examples,
            self.world,
            self.scene_page,
            self.inspector,
            self.preview,
            self.validation,
            self.export,
            self.llm_draft,
            self.settings,
        ):
            self.stack.addWidget(page)

        # Wire dashboard quick actions
        self.dashboard.show_examples_requested.connect(lambda: self._select_page("examples"))
        self.dashboard.open_file_requested.connect(self._action_open)
        self.dashboard.validate_requested.connect(self._action_validate)
        self.dashboard.render_svg_requested.connect(lambda: self._select_page("preview"))
        self.dashboard.export_obj_requested.connect(lambda: self._select_page("export"))
        self.dashboard.export_blender_requested.connect(lambda: self._select_page("export"))

        self.world.render_requested.connect(lambda: self._select_page("preview"))
        self.world.export_obj_requested.connect(lambda: self._select_page("export"))
        self.scene_page.render_requested.connect(lambda: self._select_page("preview"))
        self.scene_page.export_obj_requested.connect(lambda: self._select_page("export"))
        self.validation.revalidate_requested.connect(self._action_validate)
        self.examples.error_signal.connect(self._show_load_error)

        # Central layout
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(self.sidebar)
        body_lay.addWidget(self.stack, 1)

        root = QWidget()
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        root_lay.addWidget(self.top_bar)
        root_lay.addWidget(body, 1)
        self.setCentralWidget(root)

        # Status bar
        bar = QStatusBar()
        bar.showMessage("Ready")
        self.setStatusBar(bar)
        self.state.status_message.connect(bar.showMessage)

        self._build_menu()
        self.sidebar.set_current(0)

    # ------------------------------------------------------------------
    # Menu / actions
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_act = QAction("&Open JSON…", self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self._action_open)
        file_menu.addAction(open_act)

        close_act = QAction("&Close Document", self)
        close_act.setShortcut("Ctrl+W")
        close_act.triggered.connect(self.state.clear)
        file_menu.addAction(close_act)

        file_menu.addSeparator()
        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        tools_menu = menu.addMenu("&Tools")
        validate_act = QAction("&Validate", self)
        validate_act.setShortcut("F5")
        validate_act.triggered.connect(self._action_validate)
        tools_menu.addAction(validate_act)

        preview_act = QAction("Open &Preview", self)
        preview_act.triggered.connect(lambda: self._select_page("preview"))
        tools_menu.addAction(preview_act)

        export_act = QAction("Open &Export", self)
        export_act.triggered.connect(lambda: self._select_page("export"))
        tools_menu.addAction(export_act)

        help_menu = menu.addMenu("&Help")
        about_act = QAction("&About MapIR Studio", self)
        about_act.triggered.connect(self._action_about)
        help_menu.addAction(about_act)

    def _on_nav(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _select_page(self, key: str) -> None:
        idx = PAGE_INDEX.get(key)
        if idx is not None:
            self.sidebar.set_current(idx)
            self.stack.setCurrentIndex(idx)

    def _action_open(self) -> None:
        start_dir = self.state.paths.last_open_dir or Path.cwd()
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Open MapIR JSON",
            str(start_dir),
            "MapIR JSON (*.json);;All files (*)",
        )
        if not chosen:
            return
        try:
            self.state.load_json_file(Path(chosen))
        except Exception as exc:  # noqa: BLE001
            self._show_load_error(chosen, str(exc))

    def _action_validate(self) -> None:
        self.state.validate_current()
        self._select_page("validation")

    def _action_about(self) -> None:
        QMessageBox.information(
            self,
            "About MapIR Studio",
            f"MapIR Studio v{__version__}\n\n"
            "Structured World & Scene IR Toolchain.\n"
            "Built with PySide6 / Qt.\n\n"
            "Source: https://github.com/BoxshiSL/MapIR",
        )

    def _show_load_error(self, path: str, msg: str) -> None:
        QMessageBox.critical(self, "Failed to load document", f"{path}\n\n{msg}")

    # ------------------------------------------------------------------
    # Test/headless helper
    # ------------------------------------------------------------------

    def select_first_example(self) -> Path | None:
        """Load the first available example, used by the headless smoke test."""
        from ..utils.paths import examples_dir

        for sub in ("scenes", "worlds"):
            folder = examples_dir() / sub
            if folder.is_dir():
                files = sorted(folder.glob("*.json"))
                if files:
                    try:
                        self.state.load_json_file(files[0])
                    except Exception:
                        return None
                    return files[0]
        return None
