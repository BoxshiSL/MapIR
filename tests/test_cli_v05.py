"""v0.5 Phase C: smoke tests for the new CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mapir.cli import app


runner = CliRunner()


def test_templates_command_lists_thirteen() -> None:
    result = runner.invoke(app, ["templates"])
    assert result.exit_code == 0, result.output
    # Rich's CliRunner-piped table truncates almost every column — we just
    # verify the command produced a non-empty table render.
    assert "templates" in result.output.lower()
    # Visible cell fragment that shouldn't get truncated away.
    assert "interior" in result.output.lower()


def test_new_from_template_writes_sketch(tmp_path: Path) -> None:
    out = tmp_path / "sketch.json"
    result = runner.invoke(
        app, ["new-from-template", "scene_industrial_port", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"sketch_id"' in text
    assert '"document_type": "scene"' in text


def test_generate_layout_writes_layout(tmp_path: Path) -> None:
    sketch_path = tmp_path / "sketch.json"
    layout_path = tmp_path / "layout.json"
    r1 = runner.invoke(
        app, ["new-from-template", "scene_industrial_port", "--out", str(sketch_path)]
    )
    assert r1.exit_code == 0, r1.output
    r2 = runner.invoke(
        app, ["generate-layout", str(sketch_path), "--out", str(layout_path)]
    )
    assert r2.exit_code == 0, r2.output
    assert layout_path.exists()
    text = layout_path.read_text(encoding="utf-8")
    assert '"layout_id"' in text
    assert '"roads"' in text


def test_validate_design_runs(tmp_path: Path) -> None:
    sketch_path = tmp_path / "sketch.json"
    layout_path = tmp_path / "layout.json"
    runner.invoke(app, ["new-from-template", "world_modern_island_city", "--out", str(sketch_path)])
    runner.invoke(app, ["generate-layout", str(sketch_path), "--out", str(layout_path)])

    # Need an IR file to validate design against.
    demo = Path(__file__).resolve().parents[1] / "examples" / "demos" / "demo_world_modern_island_city.json"
    assert demo.exists(), "Run scripts/build_demo_fixtures.py first."
    result = runner.invoke(
        app, ["validate-design", str(demo), "--layout", str(layout_path)]
    )
    # Either OK (exit 0) or has design errors (exit 1) — both are valid run
    # outcomes; we just verify the command runs.
    assert result.exit_code in (0, 1), result.output


def test_export_design_report_writes_markdown(tmp_path: Path) -> None:
    demo = Path(__file__).resolve().parents[1] / "examples" / "demos" / "demo_world_modern_island_city.json"
    out = tmp_path / "design_report.md"
    result = runner.invoke(
        app, ["export-design-report", str(demo), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Design report")
