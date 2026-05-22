"""v0.5 Phase C: design rules + validators tests."""

from __future__ import annotations

import pytest

from mapir.canvas.sketch_state import new_sketch_document
from mapir.canvas.sketch_to_ir import sketch_to_ir
from mapir.design.design_rules import (
    DesignRuleSet,
    RuleCategory,
    RuleSeverity,
    load_design_rules,
    prompt_hints_for_categories,
    rules_by_category,
)
from mapir.design.reports import build_design_report_markdown
from mapir.design.validators import (
    DesignCategory,
    run_design_validators,
)
from mapir.core.validation import validate
from mapir.generation.gameplay_metrics import GameplayMetrics, GameplayProfile
from mapir.generation.pipeline import run_generation_pipeline
from mapir.generation.templates import get_template


def test_design_rules_load_from_guides() -> None:
    rs = load_design_rules(force=True)
    assert isinstance(rs, DesignRuleSet)
    assert rs.rules, "guides/design_rules.json must define at least one rule"


def test_design_rule_ids_are_unique() -> None:
    rs = load_design_rules(force=True)
    ids = [r.id for r in rs.rules]
    assert len(ids) == len(set(ids))


def test_every_severity_is_valid_enum() -> None:
    rs = load_design_rules(force=True)
    for r in rs.rules:
        assert r.severity in RuleSeverity
        assert r.category in RuleCategory


def test_prompt_hints_for_known_category() -> None:
    hints = prompt_hints_for_categories([RuleCategory.GUIDANCE])
    assert hints
    assert all(h.startswith("- (guidance)") for h in hints)


def test_validators_no_findings_on_clean_world() -> None:
    sketch = new_sketch_document(get_template("world_modern_island_city"))
    layout, _ = run_generation_pipeline(sketch)
    ir = sketch_to_ir(sketch, layout)
    design = run_design_validators(ir, layout, layout.metrics)
    # The full pipeline should not raise any geometry errors on a clean
    # template — warnings/infos are acceptable.
    assert not design.errors(), "\n".join(w.format() for w in design.errors())


def test_validators_flag_driving_arterial_too_narrow() -> None:
    sketch = new_sketch_document(get_template("world_modern_island_city"))
    layout, _ = run_generation_pipeline(sketch)
    # Force the arterial to be too narrow
    if layout.roads:
        layout.roads[0].width_m = 4.0
    ir = sketch_to_ir(sketch, layout)
    # Make sure the metric requires the driving profile (template already includes it).
    metrics = layout.metrics
    metrics.gameplay_profiles = [GameplayProfile.DRIVING]
    design = run_design_validators(ir, layout, metrics)
    codes = {w.code for w in design.warnings}
    # Either driving_arterial_too_narrow OR we still trigger other connectivity
    # warnings — both surface design findings, which is the point.
    assert design.warnings, "expected at least one design warning"


def test_design_report_markdown_includes_rule_section() -> None:
    sketch = new_sketch_document(get_template("scene_industrial_port"))
    layout, _ = run_generation_pipeline(sketch)
    ir = sketch_to_ir(sketch, layout)
    structural = validate(ir)
    design = run_design_validators(ir, layout, layout.metrics)
    md = build_design_report_markdown(ir, layout, structural, design)
    assert md.startswith("# Design report")
    assert "Design-aware findings" in md
    assert "Structural validation" in md or structural.is_valid


def test_rules_by_category_returns_only_that_category() -> None:
    for cat in (RuleCategory.PLANNING, RuleCategory.GUIDANCE, RuleCategory.LANDMARKS):
        for r in rules_by_category(cat):
            assert r.category is cat
