"""Districts page + District Inspector — Phase A scaffold.

Phase A shows the list of districts in the current ``WorldIR`` (or zones in a
``SceneIR``) and a read-only inspector panel that previews the v0.5
inspector fields. Phase B wires this up to per-district settings, gameplay
profiles, local LLM brief, and the "Generate district" actions.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...core.models import SceneIR, WorldIR
from ..state import AppState


class _DistrictInspector(QFrame):
    """Read-only Phase-A preview of the v0.5 District Inspector."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        title = QLabel("District Inspector")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        lay.addWidget(title)
        hint = QLabel(
            "Phase A: read-only summary. Editable fields, gameplay-profile "
            "overrides, local LLM brief, and per-district generation actions "
            "land in Phase B."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        lay.addWidget(hint)

        self._form = QFormLayout()
        self._form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._id = QLabel("—")
        self._name = QLabel("—")
        self._type = QLabel("—")
        self._density = QLabel("—")
        self._height = QLabel("—")
        self._tags = QLabel("—")
        self._gameplay_tags = QLabel("—")
        self._form.addRow("id", self._id)
        self._form.addRow("name", self._name)
        self._form.addRow("type", self._type)
        self._form.addRow("density", self._density)
        self._form.addRow("height_profile", self._height)
        self._form.addRow("tags", self._tags)
        self._form.addRow("gameplay_tags", self._gameplay_tags)
        lay.addLayout(self._form)

        lay.addWidget(QLabel("Local LLM brief (Phase B):"))
        self._brief = QPlainTextEdit()
        self._brief.setReadOnly(True)
        self._brief.setPlaceholderText(
            "Per-district LLM brief — wired up in Phase B."
        )
        lay.addWidget(self._brief, 1)

        actions = QHBoxLayout()
        for label in (
            "Generate roads",
            "Generate parcels & buildings",
            "Generate landmarks & slots",
            "Validate district",
        ):
            btn = QPushButton(label)
            btn.setEnabled(False)
            actions.addWidget(btn)
        actions.addStretch(1)
        lay.addLayout(actions)

    def show(self, entry: dict[str, str]) -> None:
        self._id.setText(entry.get("id", "—"))
        self._name.setText(entry.get("name", "—"))
        self._type.setText(entry.get("type", "—"))
        self._density.setText(entry.get("density", "—"))
        self._height.setText(entry.get("height_profile", "—"))
        self._tags.setText(entry.get("tags", "—"))
        self._gameplay_tags.setText(entry.get("gameplay_tags", "—"))


class DistrictsPage(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Districts")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Per-district setup. Pick a district on the left to inspect its "
            "fields on the right. In Phase B you'll edit type, theme, "
            "density, road pattern, gameplay profile, and a local LLM brief, "
            "then trigger per-district generation."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self._list)
        self._inspector = _DistrictInspector()
        splitter.addWidget(self._inspector)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        state.document_loaded.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        doc = self._state.current_document
        if doc is None:
            return
        if isinstance(doc, WorldIR):
            for d in doc.districts:
                item = QListWidgetItem(f"{d.name}  ·  {d.district_type}")
                item.setData(
                    Qt.UserRole,
                    {
                        "id": d.id,
                        "name": d.name,
                        "type": d.district_type,
                        "density": d.density.value,
                        "height_profile": d.height_profile.value,
                        "tags": ", ".join(d.tags) or "—",
                        "gameplay_tags": ", ".join(d.gameplay_tags) or "—",
                    },
                )
                self._list.addItem(item)
        elif isinstance(doc, SceneIR):
            for z in doc.zones:
                item = QListWidgetItem(f"{z.name}  ·  {z.zone_type.value}")
                item.setData(
                    Qt.UserRole,
                    {
                        "id": z.id,
                        "name": z.name,
                        "type": z.zone_type.value,
                        "density": "—",
                        "height_profile": "—",
                        "tags": ", ".join(z.tags) or "—",
                        "gameplay_tags": ", ".join(z.gameplay_tags) or "—",
                    },
                )
                self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _on_select(self, current: QListWidgetItem | None) -> None:
        if current is None:
            return
        data = current.data(Qt.UserRole) or {}
        self._inspector.show(data)
