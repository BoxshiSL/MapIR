"""v0.5: smoke-test the New Project Wizard offscreen.

The wizard is a thin orchestrator over template selection; we verify it can
be constructed, can list templates of the selected type, and that
``AppState.load_from_template`` produces a valid document.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="PySide6 not installed")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_wizard_constructs_with_five_pages(qapp) -> None:
    from mapir.desktop.dialogs.new_project_wizard import NewProjectWizard

    wizard = NewProjectWizard()
    wizard.set_initial_document_type("world")
    # 5 steps: type → template → size → theme → llm
    assert len(wizard.pageIds()) == 5
    # Result before selection: no template_id yet.
    assert wizard.result_payload() is None
    wizard.deleteLater()


def test_load_from_template_produces_valid_scene(qapp) -> None:
    """Phase A safety net: every template_id usable via the gallery yields a
    validator-passing IR (the wizard relies on this contract)."""
    from mapir.core.validation import validate
    from mapir.desktop.state import AppState
    from mapir.generation.templates import load_all_templates

    state = AppState()
    for tpl_id in load_all_templates():
        state.load_from_template(tpl_id)
        assert state.current_document is not None
        report = validate(state.current_document)
        assert report.is_valid, f"{tpl_id} produced invalid IR"
        state.clear()


def test_load_from_template_produces_valid_world(qapp) -> None:
    from mapir.desktop.state import AppState

    state = AppState()
    state.load_from_template("world_modern_island_city")
    assert state.current_document is not None
    assert state.current_document.ir_type.value == "world"
    assert state.validation_report is not None
    assert state.validation_report.is_valid
    assert state.current_template_id == "world_modern_island_city"


def test_load_from_template_produces_valid_interior(qapp) -> None:
    from mapir.desktop.state import AppState

    state = AppState()
    state.load_from_template("interior_warehouse")
    assert state.current_document is not None
    assert state.current_document.ir_type.value == "scene"
    assert state.current_document.scene_type.value == "interior"
    assert state.validation_report is not None
    assert state.validation_report.is_valid
