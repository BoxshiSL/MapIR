"""LLMSettings load/save round-trip."""

from __future__ import annotations

from pathlib import Path

from mapir.llm.settings import LLMSettings, load_settings, save_settings


def test_load_settings_returns_defaults_when_missing(tmp_path: Path) -> None:
    s = load_settings(tmp_path / "does_not_exist.json")
    assert isinstance(s, LLMSettings)
    assert s.provider == "ollama"
    assert s.base_url.startswith("http://")
    assert s.model  # non-empty
    assert s.timeout_seconds >= 30
    assert s.enable_repair is True


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    custom = LLMSettings(
        provider="ollama",
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:7b-instruct",
        fallback_model=None,
        temperature=0.35,
        max_tokens=2048,
        timeout_seconds=60,
        enable_repair=False,
        max_repair_attempts=2,
        structured_output=False,
    )
    target = tmp_path / "settings.json"
    written_path = save_settings(custom, target)
    assert written_path.exists()

    reloaded = load_settings(target)
    assert reloaded.model == "qwen2.5:7b-instruct"
    assert reloaded.temperature == 0.35
    assert reloaded.max_tokens == 2048
    assert reloaded.enable_repair is False
    assert reloaded.max_repair_attempts == 2
    assert reloaded.fallback_model is None


def test_load_settings_ignores_unknown_fields(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        '{"provider": "mock", "future_field": "ignored", "temperature": 0.7}',
        encoding="utf-8",
    )
    s = load_settings(target)
    assert s.provider == "mock"
    assert s.temperature == 0.7


def test_load_settings_handles_corrupt_file(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text("this is not json", encoding="utf-8")
    s = load_settings(target)
    # Falls back to defaults without raising.
    assert s.provider == "ollama"
