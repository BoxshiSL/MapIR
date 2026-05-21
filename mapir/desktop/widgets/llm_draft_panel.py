"""LLM Draft panel — generate WorldIR/SceneIR drafts via a local LLM.

The panel collects provider/model/task settings, runs generation on a
background thread (so the UI doesn't freeze for 120s), shows the raw output,
plan JSON, IR JSON, and validation report, and lets the user load the draft
into the current document (only after explicit confirmation).
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.models import SceneIR, WorldIR
from ...core.validation import validate as run_validation
from ...llm.drafting import DraftResult
from ...llm.settings import LLMSettings, load_settings, save_settings
from ..llm_worker import make_worker_thread
from ..state import AppState
from ..theme import PALETTE

_TASK_LABELS = [
    ("world", "Draft World Zoning"),
    ("scene", "Draft Scene / Location"),
    ("district", "Draft District Profile"),
    ("repair", "Repair Current Document"),
]

_PLACEHOLDERS = {
    "world": (
        "Example:\n"
        "Create a compact Japanese-inspired crime city with a nightlife canal district, "
        "old rough dense district, business core, university district, hill edge, industrial "
        "port and offshore airport island. Include scene slots for club back alley, nightclub "
        "interior, narrow alley, container yard and warehouse interior."
    ),
    "scene": (
        "Example:\n"
        "Create an 80x45m night urban alley for stealth-combat gameplay. Include 3 entrances, "
        "2 escape routes, a service yard, side passage, roof stairs marker, ambush point and "
        "at least 5 cover markers."
    ),
    "district": (
        "Example:\n"
        "Old-town district between business core and port. Narrow alleys, low buildings, "
        "stealth-friendly. Include a market and a shrine. Forbid wide boulevards."
    ),
    "repair": "Repair uses the currently loaded document — type any extra instructions for the model here.",
}


_SEVERITY_COLORS = {
    "error": PALETTE["danger"],
    "warning": PALETTE["warning"],
    "info": PALETTE["accent_2"],
}


class LLMDraftPanel(QWidget):
    error_signal = Signal(str, str)

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state
        self._settings: LLMSettings = load_settings()
        self._last_result: DraftResult | None = None
        self._thread = None
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Local LLM Drafting")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Draft a WorldIR / SceneIR from a local model (Ollama by default), "
            "review the output, then load into the current document. "
            "Drafts are validated; invalid output is never silently accepted."
        )
        subtitle.setProperty("role", "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        # ---- Provider settings -----------------------------------------
        provider_group = QGroupBox("Provider")
        prov_form = QFormLayout(provider_group)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "mock"])
        self.provider_combo.setCurrentText(self._settings.provider)
        self.base_url_edit = QLineEdit(self._settings.base_url)
        self.model_edit = QLineEdit(self._settings.model)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.05)
        self.temperature_spin.setValue(self._settings.temperature)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 32768)
        self.max_tokens_spin.setValue(self._settings.max_tokens)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setValue(self._settings.timeout_seconds)

        prov_form.addRow("Provider:", self.provider_combo)
        prov_form.addRow("Base URL:", self.base_url_edit)
        prov_form.addRow("Model:", self.model_edit)
        prov_form.addRow("Temperature:", self.temperature_spin)
        prov_form.addRow("Max tokens:", self.max_tokens_spin)
        prov_form.addRow("Timeout (s):", self.timeout_spin)

        prov_actions = QHBoxLayout()
        self.btn_check = QPushButton("Check Provider")
        self.btn_list = QPushButton("List Models")
        self.btn_save_settings = QPushButton("Save Settings")
        prov_actions.addWidget(self.btn_check)
        prov_actions.addWidget(self.btn_list)
        prov_actions.addWidget(self.btn_save_settings)
        prov_actions.addStretch(1)
        prov_form.addRow(prov_actions)

        self.provider_status = QLabel("")
        self.provider_status.setProperty("role", "muted")
        self.provider_status.setWordWrap(True)
        prov_form.addRow(self.provider_status)

        root.addWidget(provider_group)

        # ---- Task + brief ----------------------------------------------
        task_group = QGroupBox("Task")
        task_layout = QVBoxLayout(task_group)
        task_row = QHBoxLayout()
        self.task_combo = QComboBox()
        for _key, label in _TASK_LABELS:
            self.task_combo.addItem(label)
        task_row.addWidget(QLabel("Task:"))
        task_row.addWidget(self.task_combo, 1)
        task_layout.addLayout(task_row)

        self.brief_edit = QPlainTextEdit()
        self.brief_edit.setPlaceholderText(_PLACEHOLDERS["world"])
        self.brief_edit.setMinimumHeight(120)
        task_layout.addWidget(self.brief_edit)

        run_row = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Draft")
        self.btn_generate.setProperty("role", "primary")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        run_row.addWidget(self.btn_generate)
        run_row.addWidget(self.progress, 1)
        task_layout.addLayout(run_row)

        root.addWidget(task_group)

        # ---- Results tabs ----------------------------------------------
        self.result_tabs = QTabWidget()
        self.raw_view = QPlainTextEdit()
        self.raw_view.setReadOnly(True)
        self.plan_view = QPlainTextEdit()
        self.plan_view.setReadOnly(True)
        self.ir_view = QPlainTextEdit()
        self.ir_view.setReadOnly(True)
        self.validation_table = QTableWidget(0, 4)
        self.validation_table.setHorizontalHeaderLabels(["Severity", "Code", "Message", "Path"])
        self.validation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.validation_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.validation_table.verticalHeader().setVisible(False)
        self.validation_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_tabs.addTab(self.raw_view, "Raw model output")
        self.result_tabs.addTab(self.plan_view, "Plan JSON")
        self.result_tabs.addTab(self.ir_view, "IR JSON")
        self.result_tabs.addTab(self.validation_table, "Validation")
        root.addWidget(self.result_tabs, 1)

        # ---- Actions row -----------------------------------------------
        actions = QFrame()
        actions_lay = QHBoxLayout(actions)
        actions_lay.setContentsMargins(0, 0, 0, 0)
        self.btn_load_current = QPushButton("Load Draft as Current Document")
        self.btn_load_current.setProperty("role", "primary")
        self.btn_save_as = QPushButton("Save Draft As…")
        actions_lay.addWidget(self.btn_load_current)
        actions_lay.addWidget(self.btn_save_as)
        actions_lay.addStretch(1)
        root.addWidget(actions)

        # ---- Wiring -----------------------------------------------------
        self.task_combo.currentIndexChanged.connect(self._on_task_changed)
        self.btn_check.clicked.connect(self._on_check_provider)
        self.btn_list.clicked.connect(self._on_list_models)
        self.btn_save_settings.clicked.connect(self._on_save_settings)
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_load_current.clicked.connect(self._on_load_into_current)
        self.btn_save_as.clicked.connect(self._on_save_draft_as)

        self._set_action_buttons_enabled(False)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _current_task_key(self) -> str:
        return _TASK_LABELS[self.task_combo.currentIndex()][0]

    def _on_task_changed(self, _idx: int) -> None:
        key = self._current_task_key()
        self.brief_edit.setPlaceholderText(_PLACEHOLDERS.get(key, ""))

    def _collect_settings(self) -> LLMSettings:
        s = LLMSettings(
            provider=self.provider_combo.currentText(),
            base_url=self.base_url_edit.text().strip() or self._settings.base_url,
            model=self.model_edit.text().strip() or self._settings.model,
            fallback_model=self._settings.fallback_model,
            temperature=float(self.temperature_spin.value()),
            max_tokens=int(self.max_tokens_spin.value()),
            timeout_seconds=int(self.timeout_spin.value()),
            enable_repair=self._settings.enable_repair,
            max_repair_attempts=self._settings.max_repair_attempts,
            structured_output=self._settings.structured_output,
        )
        return s

    def _make_provider(self, settings: LLMSettings):
        from ...llm import MockProvider, OllamaProvider

        if settings.provider == "mock":
            return MockProvider()
        return OllamaProvider(
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
            structured_output=settings.structured_output,
        )

    def _set_action_buttons_enabled(self, has_result: bool) -> None:
        self.btn_load_current.setEnabled(has_result)
        self.btn_save_as.setEnabled(has_result)

    # ------------------------------------------------------------------
    # Provider actions (synchronous — quick HTTP / no LLM call)
    # ------------------------------------------------------------------

    def _on_check_provider(self) -> None:
        settings = self._collect_settings()
        prov = self._make_provider(settings)
        if prov.is_available():
            self.provider_status.setText(f"OK · provider={prov.name} reachable")
            self.provider_status.setStyleSheet(f"color: {PALETTE['success']};")
        else:
            self.provider_status.setText(
                f"UNAVAILABLE · {prov.name}. If Ollama: start it locally, then "
                f"`ollama pull {settings.model}`."
            )
            self.provider_status.setStyleSheet(f"color: {PALETTE['danger']};")

    def _on_list_models(self) -> None:
        settings = self._collect_settings()
        prov = self._make_provider(settings)
        models = prov.list_models()
        if not models:
            self.provider_status.setText(
                f"{prov.name} returned no models. Pull one first, e.g. `ollama pull {settings.model}`."
            )
            self.provider_status.setStyleSheet(f"color: {PALETTE['warning']};")
            return
        self.provider_status.setText("Models: " + ", ".join(models))
        self.provider_status.setStyleSheet(f"color: {PALETTE['muted']};")

    def _on_save_settings(self) -> None:
        s = self._collect_settings()
        save_settings(s)
        self._settings = s
        self.provider_status.setText("Settings saved to settings/mapir_settings.json")
        self.provider_status.setStyleSheet(f"color: {PALETTE['success']};")

    # ------------------------------------------------------------------
    # Generate (async via QThread)
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        task = self._current_task_key()
        brief = self.brief_edit.toPlainText().strip()
        if not brief and task != "repair":
            QMessageBox.warning(self, "Brief required", "Type a brief before generating.")
            return

        if task == "repair":
            self._run_repair_task(brief)
            return

        settings = self._collect_settings()
        provider = self._make_provider(settings)

        district_id = ""
        world_summary = ""
        if task == "district":
            # Best-effort: pull world summary from current document, ask user for district id.
            if isinstance(self._state.current_document, WorldIR):
                world_summary = self._world_summary_text(self._state.current_document)
                district_id = self._prompt_for_district_id(self._state.current_document)
                if not district_id:
                    return
            else:
                QMessageBox.information(
                    self,
                    "Load a world first",
                    "District profile drafting needs a loaded WorldIR. "
                    "Open a world JSON via File → Open, then try again.",
                )
                return

        self._start_worker(task, brief, provider, settings, district_id, world_summary)

    def _world_summary_text(self, world: WorldIR) -> str:
        dnames = ", ".join(f"{d.id}:{d.name}" for d in world.districts) or "(none)"
        return (
            f"World id={world.world_id} name={world.name} theme={world.theme} "
            f"scale={world.scale.width_m}x{world.scale.depth_m}\nDistricts: {dnames}"
        )

    def _prompt_for_district_id(self, world: WorldIR) -> str:
        from PySide6.QtWidgets import QInputDialog

        ids = [d.id for d in world.districts]
        if not ids:
            QMessageBox.information(self, "No districts", "The loaded world has no districts.")
            return ""
        choice, ok = QInputDialog.getItem(
            self, "District id", "Pick a district to profile:", ids, 0, False
        )
        return choice if ok else ""

    def _start_worker(self, task, brief, provider, settings, district_id, world_summary):
        if self._thread is not None and self._thread.isRunning():
            return  # one job at a time

        thread, worker = make_worker_thread(self)
        worker.configure(
            task=task,
            brief=brief,
            provider=provider,
            settings=settings,
            district_id=district_id,
            world_summary=world_summary,
        )
        worker.finished.connect(self._on_worker_finished)
        # Drive the worker once the thread starts; clean up afterwards.
        thread.started.connect(worker.run_draft)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker

        self.progress.setVisible(True)
        self.btn_generate.setEnabled(False)
        self._state.status_message.emit(f"Generating {task} draft…")
        thread.start()

    def _on_worker_finished(self, result: DraftResult) -> None:
        self._thread = None
        self._worker = None
        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)
        self._render_result(result)
        self._last_result = result
        self._set_action_buttons_enabled(result.ir_json is not None)
        if result.ok:
            self._state.status_message.emit(f"Draft OK ({result.task})")
        else:
            self._state.status_message.emit(f"Draft FAILED ({result.task})")

    def _render_result(self, result: DraftResult) -> None:
        self.raw_view.setPlainText(result.raw_text or "")
        self.plan_view.setPlainText(
            json.dumps(result.plan_json, indent=2, ensure_ascii=False) if result.plan_json else ""
        )
        self.ir_view.setPlainText(
            json.dumps(result.ir_json, indent=2, ensure_ascii=False) if result.ir_json else ""
        )
        self._populate_validation_table(result)

    def _populate_validation_table(self, result: DraftResult) -> None:
        report = result.validation_report
        # Synthesize rows from errors[] when validator wasn't reached.
        if report is None:
            self.validation_table.setRowCount(len(result.errors))
            for r, msg in enumerate(result.errors):
                self.validation_table.setItem(r, 0, _sev_cell("error"))
                self.validation_table.setItem(r, 1, QTableWidgetItem("provider_or_parse"))
                self.validation_table.setItem(r, 2, QTableWidgetItem(msg))
                self.validation_table.setItem(r, 3, QTableWidgetItem(""))
            return
        issues = report.all()
        self.validation_table.setRowCount(len(issues))
        for r, issue in enumerate(issues):
            self.validation_table.setItem(r, 0, _sev_cell(issue.severity.value))
            self.validation_table.setItem(r, 1, QTableWidgetItem(issue.code))
            self.validation_table.setItem(r, 2, QTableWidgetItem(issue.message))
            self.validation_table.setItem(r, 3, QTableWidgetItem(issue.path))

    # ------------------------------------------------------------------
    # Repair (uses current document as input)
    # ------------------------------------------------------------------

    def _run_repair_task(self, _extra_brief: str) -> None:
        from ...llm.repair import repair_invalid_ir

        doc = self._state.current_document
        if doc is None or self._state.current_raw_json is None:
            QMessageBox.information(
                self,
                "No document",
                "Load a document via File → Open before running repair.",
            )
            return
        report = self._state.validation_report or run_validation(doc)
        if report.is_valid:
            QMessageBox.information(
                self, "Already valid", "Current document is already valid — nothing to repair."
            )
            return

        settings = self._collect_settings()
        provider = self._make_provider(settings)
        repaired = repair_invalid_ir(
            invalid_json=self._state.current_raw_json,
            validation_report=report,
            provider=provider,
            settings=settings,
            expected_type="world" if isinstance(doc, WorldIR) else "scene",
        )
        result = DraftResult(
            ok=False,
            task="repair",
            raw_text="" if repaired is None else json.dumps(repaired, indent=2),
            plan_json=None,
            ir_json=repaired,
            provider_name=provider.name,
            model_name=settings.model,
        )
        if repaired is not None:
            try:
                ir2 = (
                    WorldIR.model_validate(repaired)
                    if isinstance(doc, WorldIR)
                    else SceneIR.model_validate(repaired)
                )
                result.validation_report = run_validation(ir2)
                result.ok = result.validation_report.is_valid
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Repaired output failed structural validation: {exc}")
        else:
            result.errors.append("Repair failed: provider returned no usable JSON")
        self._render_result(result)
        self._last_result = result
        self._set_action_buttons_enabled(result.ir_json is not None)

    # ------------------------------------------------------------------
    # Load into current / save as
    # ------------------------------------------------------------------

    def _on_load_into_current(self) -> None:
        if self._last_result is None or self._last_result.ir_json is None:
            return
        if not self._last_result.ok:
            answer = QMessageBox.question(
                self,
                "Load invalid draft?",
                "This draft did not pass validation. Load it anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        ir_json = self._last_result.ir_json
        try:
            ir = (
                WorldIR.model_validate(ir_json)
                if ir_json.get("ir_type") == "world"
                else SceneIR.model_validate(ir_json)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Cannot load draft", str(exc))
            return
        self._state.current_document = ir
        self._state.current_raw_json = ir_json
        self._state.current_path = None
        self._state.document_loaded.emit()
        self._state.validation_report = run_validation(ir)
        self._state.validation_changed.emit()
        self._state.status_message.emit(f"Loaded draft into current document ({ir.ir_type.value})")

    def _on_save_draft_as(self) -> None:
        if self._last_result is None or self._last_result.ir_json is None:
            return
        start_dir = self._state.paths.last_export_dir or Path.cwd()
        chosen, _ = QFileDialog.getSaveFileName(
            self,
            "Save Draft IR JSON",
            str(start_dir / "draft.json"),
            "MapIR JSON (*.json);;All files (*)",
        )
        if not chosen:
            return
        path = Path(chosen)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._last_result.ir_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._state.paths.last_export_dir = path.parent
        self._state.status_message.emit(f"Draft saved to {path}")


def _sev_cell(severity: str) -> QTableWidgetItem:
    item = QTableWidgetItem(severity.upper())
    color = QColor(_SEVERITY_COLORS.get(severity, PALETTE["muted"]))
    item.setForeground(QBrush(color))
    font = item.font()
    font.setBold(True)
    item.setFont(font)
    item.setTextAlignment(Qt.AlignCenter)
    return item
