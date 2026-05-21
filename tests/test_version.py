from __future__ import annotations

import re
import tomllib
from pathlib import Path

import mapir

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_is_040() -> None:
    assert mapir.__version__ == "0.4.0"


def test_pyproject_version_matches_package() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == mapir.__version__


def test_readme_mentions_current_version() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert re.search(r"0\.4(?:\.0)?\b", readme), "README should mention v0.4 / 0.4.0"


def test_readme_mentions_local_llm() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Local LLM" in readme, "README must document the v0.4 local LLM layer"
