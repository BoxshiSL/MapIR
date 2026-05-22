"""Curated design rules loader.

Reads ``guides/design_rules.json``, validates it as a Pydantic model, and
exposes lookup helpers used by the validators and the LLM prompts.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..utils.paths import guides_dir


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleCategory(str, Enum):
    PLANNING = "planning"
    GAMEPLAY_METRICS = "gameplay_metrics"
    NAVIGATION = "navigation"
    READABILITY = "readability"
    LANDMARKS = "landmarks"
    STREETS = "streets"
    BUILDINGS = "buildings"
    WORLDBUILDING = "worldbuilding"
    GUIDANCE = "guidance"
    AFFORDANCE = "affordance"
    COMPOSITION = "composition"
    SCALE_ILLUSION = "scale_illusion"
    ITERATION = "iteration"
    DISTRICTS = "districts"
    GEOMETRY = "geometry"


class RuleSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DesignRule(_Strict):
    id: str
    category: RuleCategory
    name: str
    description: str
    applies_to: list[str] = Field(default_factory=list)
    severity: RuleSeverity = RuleSeverity.INFO
    validator_hint: str = ""
    prompt_hint: str = ""
    source_note: str = ""


class DesignRuleSet(_Strict):
    version: str = "0.5.0"
    rules: list[DesignRule] = Field(default_factory=list)


class DesignRulesLoadError(RuntimeError):
    pass


_CACHE: DesignRuleSet | None = None


def design_rules_path() -> Path:
    return guides_dir() / "design_rules.json"


def load_design_rules(*, force: bool = False) -> DesignRuleSet:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    path = design_rules_path()
    if not path.exists():
        raise DesignRulesLoadError(
            f"design_rules.json not found at {path}. "
            "v0.5 ships this file under guides/."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DesignRulesLoadError(f"invalid JSON in {path}: {exc}") from exc
    try:
        ruleset = DesignRuleSet.model_validate(data)
    except ValidationError as exc:
        raise DesignRulesLoadError(f"design_rules.json failed validation:\n{exc}") from exc
    ids = [r.id for r in ruleset.rules]
    duplicates = {x for x in ids if ids.count(x) > 1}
    if duplicates:
        raise DesignRulesLoadError(f"duplicate rule ids in design_rules.json: {duplicates}")
    _CACHE = ruleset
    return ruleset


def rules_by_category(category: RuleCategory) -> list[DesignRule]:
    return [r for r in load_design_rules().rules if r.category is category]


def prompt_hints_for_categories(categories: list[RuleCategory]) -> list[str]:
    """Return prompt-friendly one-liner hints for the given categories.

    Used by the LLM prompts to inject curated design wisdom without dumping
    the whole rule registry into every prompt.
    """
    rules = load_design_rules().rules
    out: list[str] = []
    seen: set[str] = set()
    for r in rules:
        if r.category not in categories:
            continue
        if r.id in seen or not r.prompt_hint:
            continue
        out.append(f"- ({r.category.value}) {r.prompt_hint}")
        seen.add(r.id)
    return out
