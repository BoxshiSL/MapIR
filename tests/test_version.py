from __future__ import annotations

import re
import tomllib
from pathlib import Path

import mapir

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_is_050() -> None:
    assert mapir.__version__ == "0.5.0"


def test_pyproject_version_matches_package() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == mapir.__version__


def test_readme_mentions_current_version() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert re.search(r"0\.5(?:\.0)?\b", readme), "README should mention v0.5 / 0.5.0"


def test_readme_mentions_local_llm() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Local LLM" in readme, "README must continue to document the local LLM layer"


def test_readme_mentions_v05_features() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    # v0.5 introduces these top-level concepts; the README must surface them.
    for keyword in ("template", "canvas", "district", "gameplay"):
        assert keyword in readme, f"README must mention v0.5 keyword: {keyword!r}"
