"""CLI smoke tests using the Mock provider — no Ollama required."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mapir.cli import app

runner = CliRunner()


def test_cli_llm_check_mock_succeeds() -> None:
    result = runner.invoke(app, ["llm-check", "--provider", "mock"])
    assert result.exit_code == 0, result.output
    assert "mock" in result.output


def test_cli_llm_draft_world_mock_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "world.json"
    result = runner.invoke(
        app,
        [
            "llm-draft-world",
            "--provider",
            "mock",
            "--brief",
            "Test compact coastal city",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ir_type"] == "world"

    # Independently re-validate via the CLI's validate command.
    val = runner.invoke(app, ["validate", str(out)])
    assert val.exit_code == 0, val.output


def test_cli_llm_draft_scene_mock_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "scene.json"
    result = runner.invoke(
        app,
        [
            "llm-draft-scene",
            "--provider",
            "mock",
            "--brief",
            "Night alley with 3 entrances",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ir_type"] == "scene"
    val = runner.invoke(app, ["validate", str(out)])
    assert val.exit_code == 0, val.output


def test_cli_llm_draft_world_supports_brief_file(tmp_path: Path) -> None:
    brief_file = tmp_path / "brief.txt"
    brief_file.write_text("Brief from file", encoding="utf-8")
    out = tmp_path / "world_from_file.json"
    result = runner.invoke(
        app,
        [
            "llm-draft-world",
            "--provider",
            "mock",
            "--brief-file",
            str(brief_file),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_llm_draft_rejects_both_brief_sources(tmp_path: Path) -> None:
    brief_file = tmp_path / "b.txt"
    brief_file.write_text("x", encoding="utf-8")
    out = tmp_path / "x.json"
    result = runner.invoke(
        app,
        [
            "llm-draft-world",
            "--provider",
            "mock",
            "--brief",
            "y",
            "--brief-file",
            str(brief_file),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code != 0
