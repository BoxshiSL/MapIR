"""Local LLM settings, persisted as plain JSON.

Loaded from settings/mapir_settings.json under the repo root. No secrets are
serialised — there are no API keys in the local-LLM workflow.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_FALLBACK_MODEL: str | None = "deepseek-r1:7b"


@dataclass
class LLMSettings:
    provider: str = "ollama"
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    fallback_model: str | None = DEFAULT_FALLBACK_MODEL
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout_seconds: int = 120
    enable_repair: bool = True
    max_repair_attempts: int = 1
    structured_output: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> LLMSettings:
        allowed = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)


def _repo_root_from_here() -> Path:
    # mapir/llm/settings.py → mapir/llm → mapir → repo root
    return Path(__file__).resolve().parents[2]


def default_settings_path() -> Path:
    return _repo_root_from_here() / "settings" / "mapir_settings.json"


def load_settings(path: Path | str | None = None) -> LLMSettings:
    p = Path(path) if path else default_settings_path()
    if not p.exists():
        return LLMSettings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return LLMSettings()
    if not isinstance(data, dict):
        return LLMSettings()
    return LLMSettings.from_dict(data)


def save_settings(settings: LLMSettings, path: Path | str | None = None) -> Path:
    p = Path(path) if path else default_settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(settings.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return p
