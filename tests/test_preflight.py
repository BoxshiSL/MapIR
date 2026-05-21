"""Tests for the preflight scanner.

The repo itself should pass preflight at all times — this test is the
guardrail. We also build a corrupted scratch repo to confirm the scanner
flags the kinds of damage it's meant to catch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.preflight import (
    PreflightReport,
    scan_repo,
)

ROOT = Path(__file__).resolve().parents[1]


def test_repo_passes_preflight() -> None:
    report: PreflightReport = scan_repo(ROOT)
    if not report.ok:
        msg = "\n".join(f"{i.code} {i.path}: {i.message}" for i in report.errors)
        pytest.fail(f"Preflight should be clean, but found:\n{msg}")


def test_detects_one_line_corruption(tmp_path: Path) -> None:
    # A "Python file" of 600 bytes glued onto a single line should be flagged.
    big_payload = ("x = 1; " * 100).rstrip()
    (tmp_path / "bad.py").write_text(big_payload, encoding="utf-8")
    # And a healthy file as a control.
    (tmp_path / "good.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    # Minimal anchors so README/pyproject checks emit predictable findings
    # but don't blow up the scan.
    (tmp_path / "README.md").write_text(
        "# MapIR\n" + "\n".join(f"line {i}" for i in range(60)),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\n', encoding="utf-8"
    )

    report = scan_repo(tmp_path)
    codes = {i.code for i in report.errors}
    paths = {i.path for i in report.errors}
    assert "one_line_corruption" in codes, codes
    assert any("bad.py" in p for p in paths), paths


def test_detects_invalid_json(tmp_path: Path) -> None:
    examples = tmp_path / "examples" / "worlds"
    examples.mkdir(parents=True)
    (examples / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# MapIR\n" + "\n".join(f"line {i}" for i in range(60)),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\n', encoding="utf-8"
    )

    report = scan_repo(tmp_path)
    assert any(i.code == "json_parse" for i in report.errors)


def test_detects_missing_readme_heading(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("no heading here\n" * 60, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\n', encoding="utf-8"
    )
    report = scan_repo(tmp_path)
    assert any(i.code == "readme_heading" for i in report.errors)


def test_examples_are_json_valid() -> None:
    """Belt-and-braces — every bundled example must still parse."""
    examples = ROOT / "examples"
    for path in (*examples.rglob("*.json"),):
        with path.open(encoding="utf-8") as f:
            json.load(f)
