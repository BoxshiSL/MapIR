"""Dark theme palette and stylesheet for MapIR Studio.

Single source for both the Qt stylesheet and the QGraphicsScene preview, so
visual changes only need to happen here.
"""

from __future__ import annotations

PALETTE: dict[str, str] = {
    # base surfaces
    "bg": "#0f1117",
    "panel": "#151924",
    "panel_alt": "#1b2030",
    "border": "#2a3142",
    # text
    "text": "#e6e9ef",
    "muted": "#9aa4b2",
    "dim": "#6b7280",
    # accents
    "accent": "#7c5cff",
    "accent_2": "#00d4ff",
    "success": "#3ddc97",
    "warning": "#ffcc66",
    "danger": "#ff5c7a",
    # preview palette (used by preview_scene)
    "prev_bg": "#0f1117",
    "prev_grid": "#1b2030",
    "prev_bounds": "#2a3142",
    "prev_district": "#3a4566",
    "prev_water": "#1f3a5f",
    "prev_road": "#a0a4ad",
    "prev_poi": "#ff5c7a",
    "prev_scene_slot": "#3ddc97",
    "prev_zone": "#2a3a52",
    "prev_zone_room": "#3b4d6e",
    "prev_zone_storage": "#3e4452",
    "prev_zone_service": "#3a3a4a",
    "prev_zone_combat": "#5c2a3a",
    "prev_zone_stealth": "#2a3a3a",
    "prev_zone_danger": "#7a2a2a",
    "prev_zone_safe": "#2a5a3a",
    "prev_zone_path": "#404a5e",
    "prev_object": "#9aa4b2",
    "prev_object_cover": "#ffcc66",
    "prev_object_wall": "#5a6478",
    "prev_path": "#7c5cff",
    "prev_path_stealth": "#00d4ff",
    "prev_path_escape": "#3ddc97",
    "prev_entrance": "#ffcc66",
    "prev_marker_cover": "#ffcc66",
    "prev_marker_ambush": "#ff5c7a",
    "prev_marker_objective": "#00d4ff",
    "prev_marker_enemy": "#ff5c7a",
    "prev_marker_player": "#3ddc97",
    "prev_marker_extract": "#7c5cff",
    "prev_label": "#e6e9ef",
}


def stylesheet() -> str:
    """Build the Qt stylesheet from the palette."""
    p = PALETTE
    return f"""
    QWidget {{
        background-color: {p["bg"]};
        color: {p["text"]};
        font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }}
    QMainWindow {{
        background-color: {p["bg"]};
    }}
    QMenuBar {{
        background-color: {p["panel"]};
        color: {p["text"]};
        border-bottom: 1px solid {p["border"]};
        padding: 2px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
    }}
    QMenuBar::item:selected {{
        background: {p["panel_alt"]};
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {p["panel"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        padding: 4px 0;
    }}
    QMenu::item {{
        padding: 6px 22px;
    }}
    QMenu::item:selected {{
        background: {p["panel_alt"]};
    }}
    QStatusBar {{
        background: {p["panel"]};
        color: {p["muted"]};
        border-top: 1px solid {p["border"]};
    }}

    /* ----- Top bar ----- */
    #TopBar {{
        background: {p["panel"]};
        border-bottom: 1px solid {p["border"]};
    }}
    #TopBarTitle {{
        font-size: 16px;
        font-weight: 700;
        color: {p["text"]};
    }}
    #TopBarPath {{
        color: {p["muted"]};
    }}
    #TopBarVersion {{
        color: {p["dim"]};
    }}
    #BadgeOK {{
        background: {p["success"]};
        color: #0a1f15;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 10px;
    }}
    #BadgeWarn {{
        background: {p["warning"]};
        color: #2b1d05;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 10px;
    }}
    #BadgeError {{
        background: {p["danger"]};
        color: #240a13;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 10px;
    }}
    #BadgeNeutral {{
        background: {p["panel_alt"]};
        color: {p["muted"]};
        padding: 3px 10px;
        border-radius: 10px;
        border: 1px solid {p["border"]};
    }}

    /* ----- Sidebar ----- */
    #Sidebar {{
        background: {p["panel"]};
        border-right: 1px solid {p["border"]};
    }}
    QListWidget#SidebarList {{
        background: {p["panel"]};
        border: none;
        padding: 8px 4px;
        outline: 0;
    }}
    QListWidget#SidebarList::item {{
        color: {p["muted"]};
        padding: 9px 14px;
        border-radius: 6px;
        margin: 2px 6px;
    }}
    QListWidget#SidebarList::item:selected {{
        background: {p["panel_alt"]};
        color: {p["text"]};
        border-left: 3px solid {p["accent"]};
        padding-left: 11px;
    }}
    QListWidget#SidebarList::item:hover {{
        background: {p["panel_alt"]};
        color: {p["text"]};
    }}

    /* ----- Cards & panels ----- */
    QFrame[card="true"] {{
        background: {p["panel"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        padding: 12px;
    }}
    QLabel[role="cardTitle"] {{
        font-weight: 700;
        font-size: 14px;
        color: {p["text"]};
    }}
    QLabel[role="cardValue"] {{
        font-size: 22px;
        font-weight: 700;
        color: {p["accent_2"]};
    }}
    QLabel[role="cardHint"] {{
        color: {p["muted"]};
    }}
    QLabel[role="pageTitle"] {{
        font-size: 20px;
        font-weight: 700;
        color: {p["text"]};
    }}
    QLabel[role="pageSubtitle"] {{
        color: {p["muted"]};
    }}
    QLabel[role="muted"] {{
        color: {p["muted"]};
    }}

    /* ----- Inputs ----- */
    QPushButton {{
        background: {p["panel_alt"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        padding: 7px 14px;
    }}
    QPushButton:hover {{
        background: #232b3e;
        border-color: #3a4565;
    }}
    QPushButton:pressed {{
        background: {p["panel"]};
    }}
    QPushButton:disabled {{
        color: {p["dim"]};
        background: {p["panel"]};
        border-color: {p["border"]};
    }}
    QPushButton[role="primary"] {{
        background: {p["accent"]};
        color: #ffffff;
        border: 1px solid {p["accent"]};
        font-weight: 600;
    }}
    QPushButton[role="primary"]:hover {{
        background: #8e72ff;
    }}
    QLineEdit, QPlainTextEdit, QTextEdit {{
        background: {p["panel_alt"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        selection-background-color: {p["accent"]};
        selection-color: #ffffff;
        padding: 6px 8px;
    }}
    QPlainTextEdit[role="mono"], QTextEdit[role="mono"] {{
        font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
        font-size: 12px;
    }}

    /* ----- Lists / tables ----- */
    QListWidget, QTreeWidget, QTableWidget {{
        background: {p["panel"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        gridline-color: {p["border"]};
        alternate-background-color: {p["panel_alt"]};
    }}
    QHeaderView::section {{
        background: {p["panel_alt"]};
        color: {p["muted"]};
        border: none;
        border-right: 1px solid {p["border"]};
        border-bottom: 1px solid {p["border"]};
        padding: 6px 8px;
    }}
    QTableWidget::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {p["accent"]};
        color: #ffffff;
    }}

    /* ----- Scrollbars ----- */
    QScrollBar:vertical {{
        background: {p["bg"]};
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p["panel_alt"]};
        border-radius: 6px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #2c3550;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {p["bg"]};
        height: 12px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p["panel_alt"]};
        border-radius: 6px;
        min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ----- Graphics view ----- */
    QGraphicsView {{
        background: {p["prev_bg"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
    }}

    /* ----- Group box ----- */
    QGroupBox {{
        background: {p["panel"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        margin-top: 14px;
        padding: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {p["muted"]};
    }}
    """


def apply_theme(app) -> None:
    """Apply the dark theme to a QApplication."""
    from PySide6.QtGui import QColor, QPalette

    app.setStyle("Fusion")
    pal = QPalette()
    p = PALETTE
    pal.setColor(QPalette.Window, QColor(p["bg"]))
    pal.setColor(QPalette.WindowText, QColor(p["text"]))
    pal.setColor(QPalette.Base, QColor(p["panel"]))
    pal.setColor(QPalette.AlternateBase, QColor(p["panel_alt"]))
    pal.setColor(QPalette.Text, QColor(p["text"]))
    pal.setColor(QPalette.Button, QColor(p["panel_alt"]))
    pal.setColor(QPalette.ButtonText, QColor(p["text"]))
    pal.setColor(QPalette.Highlight, QColor(p["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ToolTipBase, QColor(p["panel"]))
    pal.setColor(QPalette.ToolTipText, QColor(p["text"]))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet())
