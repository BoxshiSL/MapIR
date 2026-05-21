"""MapIR local LLM drafting layer.

Provides a small provider abstraction so MapIR can ask a local model (default:
Ollama) to draft a high-level WorldPlan or ScenePlan from a user brief.
Deterministic helpers then convert the plan into validator-friendly IR.

The LLM is an assistant — Pydantic + semantic validators remain the source of
truth. Invalid drafts are never silently accepted.
"""

from __future__ import annotations

from .drafting import (
    DraftResult,
    draft_district_profile,
    draft_scene_from_brief,
    draft_world_from_brief,
)
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .providers import LLMJsonRequest, LLMJsonResponse, LocalLLMProvider, ProviderError
from .settings import LLMSettings, default_settings_path, load_settings, save_settings

__all__ = [
    "DraftResult",
    "LLMJsonRequest",
    "LLMJsonResponse",
    "LLMSettings",
    "LocalLLMProvider",
    "MockProvider",
    "OllamaProvider",
    "ProviderError",
    "default_settings_path",
    "draft_district_profile",
    "draft_scene_from_brief",
    "draft_world_from_brief",
    "load_settings",
    "save_settings",
]
