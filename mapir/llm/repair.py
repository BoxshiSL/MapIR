"""Repair loop for invalid LLM-drafted JSON.

Asks the provider to fix a document given its validation errors. Bounded by
LLMSettings.max_repair_attempts. Never silently accepts the repaired output —
the caller MUST re-parse and re-validate.
"""

from __future__ import annotations

from typing import Literal

from ..core.validation import ValidationReport
from . import prompts
from .providers import LLMJsonRequest, LocalLLMProvider
from .settings import LLMSettings


def _report_errors(report: ValidationReport) -> list[str]:
    msgs: list[str] = []
    for i in report.errors:
        path = f" [{i.path}]" if i.path else ""
        msgs.append(f"{i.code}: {i.message}{path}")
    return msgs


def repair_invalid_ir(
    invalid_json: dict,
    validation_report: ValidationReport,
    provider: LocalLLMProvider,
    settings: LLMSettings,
    expected_type: Literal["world", "scene"],
) -> dict | None:
    """Ask the provider to fix the listed errors. Returns repaired dict or None."""
    if not settings.enable_repair:
        return None
    attempts = max(1, settings.max_repair_attempts)
    errors = _report_errors(validation_report)
    if not errors:
        return None

    current = invalid_json
    for _ in range(attempts):
        system, user = prompts.build_repair_prompt(
            invalid_json=current,
            errors=errors,
            expected_type=expected_type,
        )
        request = LLMJsonRequest(
            task="repair_ir",
            system_prompt=system,
            user_prompt=user,
            schema=None,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            model=settings.model,
        )
        response = provider.generate_json(request)
        if not response.ok or not isinstance(response.json_data, dict):
            return None
        # Return the first usable JSON object — the caller re-validates.
        return response.json_data
    return None
