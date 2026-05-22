from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
DEMOS = EXAMPLES / "demos"


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture(scope="session")
def demos_dir() -> Path:
    return DEMOS


def _filter_by_ir_type(files: list[Path], ir_type: str) -> list[Path]:
    import json

    out: list[Path] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("ir_type") == ir_type:
            out.append(f)
    return out


@pytest.fixture(scope="session")
def world_files(demos_dir: Path) -> list[Path]:
    """v0.5 demo worlds (generated from templates by scripts/build_demo_fixtures.py)."""
    files = sorted(demos_dir.glob("*.json"))
    return _filter_by_ir_type(files, "world")


@pytest.fixture(scope="session")
def scene_files(demos_dir: Path) -> list[Path]:
    """v0.5 demo scenes — exterior scenes plus interior scenes (SceneIR subtype)."""
    files = sorted(demos_dir.glob("*.json"))
    return _filter_by_ir_type(files, "scene")
