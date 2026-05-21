from __future__ import annotations

import re
import tomllib
from pathlib import Path

import mapir

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_is_020() -> None:
    assert mapir.__version__ == "0.2.0"


def test_pyproject_version_matches_package() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == mapir.__version__


def test_readme_mentions_current_version() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert re.search(r"0\.2(?:\.0)?\b", readme), \
        "README should mention v0.2 / 0.2.0"
