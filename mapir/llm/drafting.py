"""High-level drafting pipeline: brief → plan → IR → validation.

This module never raises on LLM failure or invalid output — every failure mode
is carried in the DraftResult so the caller (CLI or desktop panel) can show
something useful to the user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ..core.models import SceneIR, WorldIR
from ..core.validation import ValidationReport
from ..core.validation import validate as run_validation
from . import prompts
from .plan_to_ir import scene_plan_to_scene_ir, world_plan_to_world_ir
from .providers import LLMJsonRequest, LocalLLMProvider
from .schemas import (
    DistrictProfile,
    ScenePlan,
    WorldPlan,
    district_profile_schema,
    scene_plan_schema,
    world_plan_schema,
)
from .settings import LLMSettings


@dataclass
class DraftResult:
    ok: bool
    task: str
    raw_text: str = ""
    plan_json: dict[str, Any] | None = None
    ir_json: dict[str, Any] | None = None
    validation_report: ValidationReport | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider_name: str = ""
    model_name: str | None = None


def _validation_errors(report: ValidationReport | None) -> list[str]:
    if report is None:
        return []
    return [f"{i.code}: {i.message}" + (f" [{i.path}]" if i.path else "") for i in report.errors]


def _ir_to_json(ir: WorldIR | SceneIR) -> dict:
    return ir.model_dump(mode="json")


# ============================================================
# World drafting
# ============================================================


def draft_world_from_brief(
    brief: str,
    provider: LocalLLMProvider,
    settings: LLMSettings,
) -> DraftResult:
    task = "world_zoning"
    system, user = prompts.build_world_zoning_prompt(brief)
    request = LLMJsonRequest(
        task=task,
        system_prompt=system,
        user_prompt=user,
        schema=world_plan_schema() if settings.structured_output else None,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        model=settings.model,
    )
    response = provider.generate_json(request)
    result = DraftResult(
        ok=False,
        task=task,
        raw_text=response.raw_text,
        provider_name=response.provider_name,
        model_name=response.model_name,
    )

    if not response.ok or response.json_data is None:
        result.errors.append(response.error or "Provider failed")
        return result

    plan_dict = response.json_data
    result.plan_json = plan_dict

    plan, plan_errs = _parse_world_plan(plan_dict)
    if plan is None and settings.enable_repair:
        repaired = _repair_plan(
            invalid_json=plan_dict,
            errors=plan_errs,
            provider=provider,
            settings=settings,
            schema=world_plan_schema() if settings.structured_output else None,
            expected_type="WorldPlan",
        )
        if repaired is not None:
            result.plan_json = repaired
            plan, plan_errs = _parse_world_plan(repaired)
    if plan is None:
        result.errors.extend(plan_errs)
        return result

    try:
        ir = world_plan_to_world_ir(plan)
    except (ValidationError, ValueError) as exc:
        result.errors.append(f"plan_to_ir failure: {exc}")
        return result

    result.ir_json = _ir_to_json(ir)
    report = run_validation(ir)
    result.validation_report = report

    if not report.is_valid and settings.enable_repair:
        ir, report = _repair_ir_loop(
            ir=ir,
            report=report,
            provider=provider,
            settings=settings,
            expected_type="world",
        )
        result.ir_json = _ir_to_json(ir) if ir is not None else result.ir_json
        result.validation_report = report

    if report is not None and report.is_valid:
        result.ok = True
    else:
        result.errors.extend(_validation_errors(report))
    return result


# ============================================================
# Scene drafting
# ============================================================


def draft_scene_from_brief(
    brief: str,
    provider: LocalLLMProvider,
    settings: LLMSettings,
) -> DraftResult:
    task = "scene_planning"
    system, user = prompts.build_scene_planning_prompt(brief)
    request = LLMJsonRequest(
        task=task,
        system_prompt=system,
        user_prompt=user,
        schema=scene_plan_schema() if settings.structured_output else None,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        model=settings.model,
    )
    response = provider.generate_json(request)
    result = DraftResult(
        ok=False,
        task=task,
        raw_text=response.raw_text,
        provider_name=response.provider_name,
        model_name=response.model_name,
    )

    if not response.ok or response.json_data is None:
        result.errors.append(response.error or "Provider failed")
        return result

    plan_dict = response.json_data
    result.plan_json = plan_dict

    plan, plan_errs = _parse_scene_plan(plan_dict)
    if plan is None and settings.enable_repair:
        repaired = _repair_plan(
            invalid_json=plan_dict,
            errors=plan_errs,
            provider=provider,
            settings=settings,
            schema=scene_plan_schema() if settings.structured_output else None,
            expected_type="ScenePlan",
        )
        if repaired is not None:
            result.plan_json = repaired
            plan, plan_errs = _parse_scene_plan(repaired)
    if plan is None:
        result.errors.extend(plan_errs)
        return result

    try:
        ir = scene_plan_to_scene_ir(plan)
    except (ValidationError, ValueError) as exc:
        result.errors.append(f"plan_to_ir failure: {exc}")
        return result

    result.ir_json = _ir_to_json(ir)
    report = run_validation(ir)
    result.validation_report = report

    if not report.is_valid and settings.enable_repair:
        ir, report = _repair_ir_loop(
            ir=ir,
            report=report,
            provider=provider,
            settings=settings,
            expected_type="scene",
        )
        result.ir_json = _ir_to_json(ir) if ir is not None else result.ir_json
        result.validation_report = report

    if report is not None and report.is_valid:
        result.ok = True
    else:
        result.errors.extend(_validation_errors(report))
    return result


# ============================================================
# District profile drafting
# ============================================================


def draft_district_profile(
    world_summary: str,
    district_id: str,
    brief: str,
    provider: LocalLLMProvider,
    settings: LLMSettings,
) -> DraftResult:
    task = "district_profile"
    system, user = prompts.build_district_profile_prompt(world_summary, district_id, brief)
    request = LLMJsonRequest(
        task=task,
        system_prompt=system,
        user_prompt=user,
        schema=district_profile_schema() if settings.structured_output else None,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        model=settings.model,
    )
    response = provider.generate_json(request)
    result = DraftResult(
        ok=False,
        task=task,
        raw_text=response.raw_text,
        provider_name=response.provider_name,
        model_name=response.model_name,
    )

    if not response.ok or response.json_data is None:
        result.errors.append(response.error or "Provider failed")
        return result

    result.plan_json = response.json_data
    try:
        DistrictProfile.model_validate(response.json_data)
    except ValidationError as exc:
        result.errors.append(f"DistrictProfile parse failure: {exc.errors()[:3]}")
        return result

    result.ok = True
    return result


# ============================================================
# Internal helpers
# ============================================================


def _parse_world_plan(data: dict) -> tuple[WorldPlan | None, list[str]]:
    try:
        return WorldPlan.model_validate(data), []
    except ValidationError as exc:
        errs = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return None, errs


def _parse_scene_plan(data: dict) -> tuple[ScenePlan | None, list[str]]:
    try:
        return ScenePlan.model_validate(data), []
    except ValidationError as exc:
        errs = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return None, errs


def _repair_plan(
    invalid_json: dict,
    errors: list[str],
    provider: LocalLLMProvider,
    settings: LLMSettings,
    schema: dict | None,
    expected_type: str,
) -> dict | None:
    attempts = max(1, settings.max_repair_attempts)
    current = invalid_json
    current_errs = errors
    for _ in range(attempts):
        system, user = prompts.build_repair_prompt(
            invalid_json=current,
            errors=current_errs,
            expected_type=expected_type,
        )
        request = LLMJsonRequest(
            task="repair_ir",
            system_prompt=system,
            user_prompt=user,
            schema=schema,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            model=settings.model,
        )
        resp = provider.generate_json(request)
        if not resp.ok or not isinstance(resp.json_data, dict):
            return None
        current = resp.json_data
        # Stop as soon as we have something usable (caller validates again).
        return current
    return None


def _repair_ir_loop(
    ir: WorldIR | SceneIR | None,
    report: ValidationReport,
    provider: LocalLLMProvider,
    settings: LLMSettings,
    expected_type: str,
) -> tuple[WorldIR | SceneIR | None, ValidationReport | None]:
    """Try to repair an invalid IR by asking the model to fix the plan.

    The model gets the IR errors and the current IR JSON; whatever it returns
    is re-parsed as Plan, re-converted, re-validated. Bounded by
    settings.max_repair_attempts.
    """
    from .repair import repair_invalid_ir  # local to avoid cycle at import time

    if ir is None:
        return ir, report
    repaired_json = repair_invalid_ir(
        invalid_json=_ir_to_json(ir),
        validation_report=report,
        provider=provider,
        settings=settings,
        expected_type=expected_type,
    )
    if repaired_json is None:
        return ir, report
    # Try to parse repaired output back as the corresponding Plan; if that fails,
    # try to parse as IR directly (the model may have returned a fully-formed IR).
    if expected_type == "world":
        plan, _ = _parse_world_plan(repaired_json)
        if plan is None:
            try:
                ir2 = WorldIR.model_validate(repaired_json)
            except ValidationError:
                return ir, report
        else:
            try:
                ir2 = world_plan_to_world_ir(plan)
            except (ValidationError, ValueError):
                return ir, report
    else:
        plan, _ = _parse_scene_plan(repaired_json)
        if plan is None:
            try:
                ir2 = SceneIR.model_validate(repaired_json)
            except ValidationError:
                return ir, report
        else:
            try:
                ir2 = scene_plan_to_scene_ir(plan)
            except (ValidationError, ValueError):
                return ir, report
    report2 = run_validation(ir2)
    return ir2, report2
