"""MockProvider should produce deterministic, validation-passing drafts."""

from __future__ import annotations

from mapir.core.models import SceneIR, WorldIR
from mapir.core.validation import validate as run_validation
from mapir.llm import (
    LLMJsonRequest,
    LLMSettings,
    MockProvider,
    draft_district_profile,
    draft_scene_from_brief,
    draft_world_from_brief,
)


def test_mock_provider_is_available() -> None:
    p = MockProvider()
    assert p.is_available() is True
    assert p.list_models()  # not empty


def test_mock_provider_world_zoning_returns_json() -> None:
    p = MockProvider()
    resp = p.generate_json(
        LLMJsonRequest(
            task="world_zoning",
            system_prompt="",
            user_prompt="",
        )
    )
    assert resp.ok is True
    assert isinstance(resp.json_data, dict)
    assert resp.json_data["world_id"] == "mock_world"


def test_mock_provider_unknown_task_fails() -> None:
    p = MockProvider()
    resp = p.generate_json(LLMJsonRequest(task="does_not_exist", system_prompt="", user_prompt=""))
    assert resp.ok is False
    assert resp.error and "does_not_exist" in resp.error


def test_draft_world_from_brief_returns_valid_world() -> None:
    settings = LLMSettings()
    result = draft_world_from_brief("Test world brief", MockProvider(), settings)
    assert result.ok is True, result.errors
    assert result.ir_json is not None
    ir = WorldIR.model_validate(result.ir_json)
    report = run_validation(ir)
    assert report.is_valid, [i.format() for i in report.errors]


def test_draft_scene_from_brief_returns_valid_scene() -> None:
    settings = LLMSettings()
    result = draft_scene_from_brief("Test scene brief", MockProvider(), settings)
    assert result.ok is True, result.errors
    assert result.ir_json is not None
    ir = SceneIR.model_validate(result.ir_json)
    report = run_validation(ir)
    assert report.is_valid, [i.format() for i in report.errors]


def test_draft_district_profile_returns_ok() -> None:
    settings = LLMSettings()
    result = draft_district_profile(
        "World summary text",
        district_id="old_town",
        brief="Profile this district",
        provider=MockProvider(),
        settings=settings,
    )
    assert result.ok is True, result.errors
    assert result.plan_json is not None
    assert result.plan_json["district_id"] == "old_town"
