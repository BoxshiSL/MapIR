from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture(scope="session")
def world_files(examples_dir: Path) -> list[Path]:
    return sorted((examples_dir / "worlds").glob("*.json"))


@pytest.fixture(scope="session")
def scene_files(examples_dir: Path) -> list[Path]:
    return sorted((examples_dir / "scenes").glob("*.json"))
