"""Local LLM provider abstraction.

A provider is anything that can take a structured JSON request and return a
JSON response. v0.4 ships two providers: OllamaProvider (real local model) and
MockProvider (deterministic fixtures for tests). The Protocol leaves room for
v0.5 to add llama.cpp / generic HTTP without changing call sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Raised by providers for unrecoverable setup errors.

    Per-call failures are returned via LLMJsonResponse.ok=False instead — this
    is reserved for cases like a totally absent runtime or invalid settings.
    """


@dataclass(frozen=True)
class LLMJsonRequest:
    task: str
    system_prompt: str
    user_prompt: str
    schema: dict[str, Any] | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    model: str | None = None


@dataclass(frozen=True)
class LLMJsonResponse:
    ok: bool
    raw_text: str
    json_data: dict[str, Any] | None
    error: str | None
    provider_name: str
    model_name: str | None
    elapsed_ms: int | None


@runtime_checkable
class LocalLLMProvider(Protocol):
    """Minimal contract every MapIR LLM provider implements."""

    name: str

    def is_available(self) -> bool: ...

    def list_models(self) -> list[str]: ...

    def generate_json(self, request: LLMJsonRequest) -> LLMJsonResponse: ...
