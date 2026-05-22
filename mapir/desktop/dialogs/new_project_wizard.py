"""New Project Wizard — the v0.5 first-launch flow.

Steps:

1. Choose document type (World / Scene / Interior).
2. Choose template (filtered to the chosen type).
3. Size & scale (read-only for now; uses the template default).
4. Gameplay profiles (checkboxes; pre-checked from template defaults).
5. Theme / worldbuilding (short text fields).
6. Local LLM (provider + model + temperature — defaults come from
   :class:`LLMSettings`).
7. Create — the wizard returns the chosen template_id and metadata; the
   caller (MainWindow) asks :meth:`AppState.load_from_template` to
   instantiate it.

Phase B will wire steps 3-6 into ``SketchDocument`` / ``GameplayMetrics``
overrides; for Phase A the wizard captures intent but only the
``template_id`` is consumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from ...generation.gameplay_metrics import GameplayProfile
from ...generation.templates import TemplateDefinition, load_all_templates
from ...llm.settings import load_settings


@dataclass
class WizardResult:
    template_id: str
    document_type: str
    gameplay_profiles: list[str] = field(default_factory=list)
    theme: str = ""
    worldbuilding_brief: str = ""
    llm_provider: str = "mock"
    llm_model: str = ""
    llm_temperature: float = 0.4


# ============================================================
# Pages
# ============================================================


class _TypePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Step 1 · Document type")
        self.setSubTitle("What are you designing?")
        lay = QVBoxLayout(self)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QRadioButton] = {}
        for key, label, desc in (
            ("world", "World", "Open-world city, region, forest, or compound."),
            ("scene", "Scene", "Gameplay-grade space (port, alley, checkpoint, …)."),
            (
                "interior",
                "Interior",
                "Building interior (warehouse, club, office, apartment). A subtype of Scene.",
            ),
        ):
            b = QRadioButton(label)
            b.setObjectName(key)
            d = QLabel(desc)
            d.setProperty("role", "muted")
            d.setStyleSheet("color: #aab4c0; padding-left: 24px;")
            self._group.addButton(b)
            self._buttons[key] = b
            lay.addWidget(b)
            lay.addWidget(d)
        self._buttons["world"].setChecked(True)
        lay.addStretch(1)
        # Non-mandatory: there's always a default radio selected, so QWizard's
        # asterisk completeness check would block ``next()`` until something
        # changed even though we already have a valid value.
        self.registerField("document_type", self, "documentType")

    # Qt property exposed for registerField
    def get_document_type(self) -> str:
        for key, b in self._buttons.items():
            if b.isChecked():
                return key
        return "world"

    def set_document_type(self, value: str) -> None:
        if value in self._buttons:
            self._buttons[value].setChecked(True)

    documentType = property(get_document_type, set_document_type)


class _TemplatePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Step 2 · Template")
        self.setSubTitle("Pick a neutral starting template.")
        lay = QVBoxLayout(self)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self.completeChanged.emit)
        lay.addWidget(self._list, 1)
        self._description = QLabel()
        self._description.setWordWrap(True)
        self._description.setProperty("role", "muted")
        lay.addWidget(self._description)

        self._list.currentItemChanged.connect(self._on_select)
        self._templates: dict[str, TemplateDefinition] = {}

    def initializePage(self) -> None:
        self._list.clear()
        doc_type = self.field("document_type")
        templates = load_all_templates()
        for tpl in sorted(templates.values(), key=lambda t: t.template_id):
            if tpl.document_type != doc_type:
                continue
            item = QListWidgetItem(f"{tpl.name} — {tpl.genre}")
            item.setData(Qt.UserRole, tpl.template_id)
            self._list.addItem(item)
            self._templates[tpl.template_id] = tpl
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _on_select(self, current: QListWidgetItem | None) -> None:
        if current is None:
            self._description.setText("")
            return
        tpl = self._templates[current.data(Qt.UserRole)]
        self._description.setText(tpl.description)

    def selected_template_id(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def isComplete(self) -> bool:
        return self._list.currentItem() is not None


class _SizePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Step 3 · Size & gameplay profiles")
        self.setSubTitle("Defaults come from the template. Override here.")
        root = QVBoxLayout(self)

        form = QFormLayout()
        self._width = QDoubleSpinBox()
        self._width.setRange(20.0, 10000.0)
        self._width.setSuffix(" m")
        self._depth = QDoubleSpinBox()
        self._depth.setRange(20.0, 10000.0)
        self._depth.setSuffix(" m")
        form.addRow("Width", self._width)
        form.addRow("Depth", self._depth)
        root.addLayout(form)

        root.addWidget(QLabel("Gameplay profiles:"))
        self._profile_boxes: dict[str, QCheckBox] = {}
        chips = QHBoxLayout()
        for profile in GameplayProfile:
            cb = QCheckBox(profile.value)
            self._profile_boxes[profile.value] = cb
            chips.addWidget(cb)
        chips.addStretch(1)
        root.addLayout(chips)
        root.addStretch(1)

    def initializePage(self) -> None:
        tpl_id = self.wizard().property("template_id")
        if not tpl_id:
            return
        tpl = load_all_templates().get(str(tpl_id))
        if tpl is None:
            return
        self._width.setValue(tpl.default_size.width_m)
        self._depth.setValue(tpl.default_size.depth_m)
        selected = {p.value for p in tpl.default_gameplay_profiles}
        for key, cb in self._profile_boxes.items():
            cb.setChecked(key in selected)

    def selected_profiles(self) -> list[str]:
        return [k for k, cb in self._profile_boxes.items() if cb.isChecked()]


class _ThemePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Step 4 · Theme & worldbuilding")
        self.setSubTitle("Short brief; informs the LLM and prompts later.")
        root = QVBoxLayout(self)

        root.addWidget(QLabel("Theme / mood (one line):"))
        self._theme = QPlainTextEdit()
        self._theme.setFixedHeight(50)
        root.addWidget(self._theme)

        root.addWidget(QLabel("Worldbuilding brief (factions, conflict, geography):"))
        self._brief = QPlainTextEdit()
        root.addWidget(self._brief, 1)

    def initializePage(self) -> None:
        tpl_id = self.wizard().property("template_id")
        if not tpl_id:
            return
        tpl = load_all_templates().get(str(tpl_id))
        if tpl is None:
            return
        self._theme.setPlainText(tpl.genre)
        self._brief.setPlainText(tpl.recommended_llm_brief)

    @property
    def theme(self) -> str:
        return self._theme.toPlainText().strip()

    @property
    def brief(self) -> str:
        return self._brief.toPlainText().strip()


class _LLMPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Step 5 · Local LLM (optional)")
        self.setSubTitle("Mock is always available. Ollama needs a local model.")
        form = QFormLayout(self)

        self._provider = QComboBox()
        self._provider.addItems(["mock", "ollama"])
        form.addRow("Provider", self._provider)

        self._model = QComboBox()
        self._model.setEditable(True)
        self._model.addItems(["", "qwen3:8b", "deepseek-r1:7b", "llama3.1:8b"])
        form.addRow("Model", self._model)

        self._temperature = QDoubleSpinBox()
        self._temperature.setRange(0.0, 2.0)
        self._temperature.setSingleStep(0.1)
        form.addRow("Temperature", self._temperature)

    def initializePage(self) -> None:
        settings = load_settings()
        # default to mock so first-run users don't get blocked on Ollama
        self._provider.setCurrentText("mock")
        self._model.setCurrentText(getattr(settings, "model", "") or "")
        self._temperature.setValue(float(getattr(settings, "temperature", 0.4)))

    @property
    def provider(self) -> str:
        return self._provider.currentText()

    @property
    def model(self) -> str:
        return self._model.currentText()

    @property
    def temperature(self) -> float:
        return float(self._temperature.value())


# ============================================================
# Wizard
# ============================================================


class NewProjectWizard(QWizard):
    """The first-run / Home → New flow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New MapIR Project")
        self.setMinimumSize(720, 540)
        self.setWizardStyle(QWizard.ModernStyle)

        self._type_page = _TypePage()
        self._template_page = _TemplatePage()
        self._size_page = _SizePage()
        self._theme_page = _ThemePage()
        self._llm_page = _LLMPage()
        self.addPage(self._type_page)
        self.addPage(self._template_page)
        self.addPage(self._size_page)
        self.addPage(self._theme_page)
        self.addPage(self._llm_page)

        self.currentIdChanged.connect(self._on_page_change)

    def set_initial_document_type(self, doc_type: str) -> None:
        if doc_type:
            self._type_page.documentType = doc_type

    def _on_page_change(self, idx: int) -> None:
        if idx >= 2:
            tpl_id = self._template_page.selected_template_id()
            if tpl_id is not None:
                self.setProperty("template_id", tpl_id)

    def result_payload(self) -> WizardResult | None:
        tpl_id = self._template_page.selected_template_id()
        if tpl_id is None:
            return None
        return WizardResult(
            template_id=tpl_id,
            document_type=self._type_page.documentType,
            gameplay_profiles=self._size_page.selected_profiles(),
            theme=self._theme_page.theme,
            worldbuilding_brief=self._theme_page.brief,
            llm_provider=self._llm_page.provider,
            llm_model=self._llm_page.model,
            llm_temperature=self._llm_page.temperature,
        )
