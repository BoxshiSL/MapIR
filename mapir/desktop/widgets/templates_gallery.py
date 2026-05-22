"""Template Gallery page — replaces the v0.4 Examples panel.

Lists every ``TemplateDefinition`` in ``mapir/data/templates`` as a card.
Cards expose template name, type (world/scene/interior), genre, gameplay
profiles, size, description, and a "Create" button that asks the
:class:`AppState` to instantiate the template into the current document.

Phase B will replace the in-memory document with a richer
``SketchDocument``; Phase A only needs to drop the user into a working IR
they can then preview / validate / export.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...generation.templates import TemplateDefinition, load_all_templates
from ..state import AppState


_TYPE_FILTER_LABELS = {"all": "All", "world": "World", "scene": "Scene", "interior": "Interior"}


class _TemplateCard(QFrame):
    create_clicked = Signal(str)  # template_id

    def __init__(self, tpl: TemplateDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tpl_id = tpl.template_id
        self.setObjectName("TemplateCard")
        self.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        title = QLabel(tpl.name)
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        lay.addWidget(title)

        meta_parts: list[str] = []
        meta_parts.append(tpl.document_type.upper())
        if tpl.genre:
            meta_parts.append(tpl.genre)
        size = tpl.default_size
        meta_parts.append(f"{int(size.width_m)}×{int(size.depth_m)} m")
        meta = QLabel("  ·  ".join(meta_parts))
        meta.setProperty("role", "muted")
        meta.setStyleSheet("color: #aab4c0; font-size: 11px;")
        lay.addWidget(meta)

        if tpl.default_gameplay_profiles:
            chips_text = "  ".join(
                f"[{p.value}]" for p in tpl.default_gameplay_profiles
            )
            chips = QLabel(chips_text)
            chips.setStyleSheet("color: #7fb3ff; font-size: 11px;")
            lay.addWidget(chips)

        desc = QLabel(tpl.description)
        desc.setWordWrap(True)
        lay.addWidget(desc, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_create = QPushButton("Create")
        self.btn_create.setProperty("role", "primary")
        row.addWidget(self.btn_create)
        row.addStretch(1)
        lay.addLayout(row)

        self.btn_create.clicked.connect(lambda: self.create_clicked.emit(self._tpl_id))

    @property
    def template_id(self) -> str:
        return self._tpl_id


class TemplatesGalleryPage(QWidget):
    template_selected = Signal(str)  # template_id — fired when "Create" is clicked

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._cards: list[_TemplateCard] = []
        self._type_filter: str = "all"
        self._genre_filter: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("New / Templates")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "13 neutral templates across World / Scene / Interior. Pick "
            "one to create a starting document, then iterate on the "
            "Canvas, Districts, and Generation pages."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        filter_row.addWidget(QLabel("Type:"))
        self._type_group = QButtonGroup(self)
        self._type_group.setExclusive(True)
        for key, label in _TYPE_FILTER_LABELS.items():
            b = QPushButton(label)
            b.setCheckable(True)
            b.setProperty("filter_key", key)
            if key == "all":
                b.setChecked(True)
            b.clicked.connect(lambda _checked, k=key: self._set_type_filter(k))
            self._type_group.addButton(b)
            filter_row.addWidget(b)

        filter_row.addSpacing(16)
        filter_row.addWidget(QLabel("Genre:"))
        self._genre_combo = QComboBox()
        self._genre_combo.addItem("All", "")
        self._genre_combo.currentIndexChanged.connect(self._on_genre_change)
        filter_row.addWidget(self._genre_combo)

        filter_row.addStretch(1)
        self._count_label = QLabel()
        self._count_label.setProperty("role", "muted")
        filter_row.addWidget(self._count_label)
        root.addLayout(filter_row)

        # Cards container
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(0, 0, 0, 0)
        scroller.setWidget(container)
        root.addWidget(scroller, 1)

        self._build_cards()
        self._populate_grid()

    def _build_cards(self) -> None:
        templates = load_all_templates()
        sorted_templates = sorted(
            templates.values(),
            key=lambda t: (t.document_type, t.template_id),
        )
        genres = sorted({t.genre for t in sorted_templates if t.genre})
        for g in genres:
            self._genre_combo.addItem(g, g)

        for tpl in sorted_templates:
            card = _TemplateCard(tpl)
            card.create_clicked.connect(self.template_selected.emit)
            self._cards.append(card)

    def _populate_grid(self) -> None:
        # Clear current layout
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        visible = [
            card
            for card in self._cards
            if self._card_matches_filters(card)
        ]
        cols = 3
        for i, card in enumerate(visible):
            row, col = divmod(i, cols)
            self._grid.addWidget(card, row, col)

        self._count_label.setText(
            f"{len(visible)} template(s) shown · {len(self._cards)} total"
        )

    def _card_matches_filters(self, card: _TemplateCard) -> bool:
        tpl = load_all_templates()[card.template_id]
        if self._type_filter != "all" and tpl.document_type != self._type_filter:
            return False
        if self._genre_filter and tpl.genre != self._genre_filter:
            return False
        return True

    def _set_type_filter(self, key: str) -> None:
        self._type_filter = key
        self._populate_grid()

    def _on_genre_change(self) -> None:
        self._genre_filter = self._genre_combo.currentData() or ""
        self._populate_grid()
