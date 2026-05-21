"""Repair loop should be invoked when validation fails."""

from __future__ import annotations

from mapir.core.validation import ValidationIssue, ValidationReport
from mapir.llm import LLMSettings, MockProvider
from mapir.llm.repair import repair_invalid_ir


def test_repair_returns_json_when_provider_has_fixture() -> None:
    bad_world = {
        "ir_type": "world",
        "world_id": "broken",
        "scale": {"width_m": 100, "depth_m": 100},
    }
    report = ValidationReport()
    report.add(ValidationIssue("world_no_districts", "needs districts"))
    repaired = repair_invalid_ir(
        invalid_json=bad_world,
        validation_report=report,
        provider=MockProvider(),
        settings=LLMSettings(),
        expected_type="world",
    )
    assert repaired is not None
    # MockProvider repair fixture is the canonical world plan; the key
    # property we want is that *something usable* came back.
    assert isinstance(repaired, dict)
    assert "world_id" in repaired or "ir_type" in repaired


def test_repair_disabled_returns_none() -> None:
    report = ValidationReport()
    report.add(ValidationIssue("x", "y"))
    settings = LLMSettings(enable_repair=False)
    repaired = repair_invalid_ir(
        invalid_json={},
        validation_report=report,
        provider=MockProvider(),
        settings=settings,
        expected_type="world",
    )
    assert repaired is None


def test_repair_skipped_when_no_errors() -> None:
    report = ValidationReport()  # empty
    repaired = repair_invalid_ir(
        invalid_json={"any": "thing"},
        validation_report=report,
        provider=MockProvider(),
        settings=LLMSettings(),
        expected_type="world",
    )
    assert repaired is None
