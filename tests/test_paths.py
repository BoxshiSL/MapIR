"""Sanity tests for mapir.utils.paths."""

from __future__ import annotations

from pathlib import Path

from mapir.utils import paths as p


def test_app_root_contains_mapir_package() -> None:
    root = p.app_root()
    assert (
        root / "mapir" / "__init__.py"
    ).is_file(), f"app_root() {root} does not look like the repo root"


def test_examples_dir_resolves() -> None:
    examples = p.examples_dir()
    assert examples.name == "examples"
    assert examples.is_dir()


def test_schemas_dir_resolves() -> None:
    schemas = p.schemas_dir()
    assert schemas.is_dir()
    assert any(schemas.glob("*.json")), "no JSON schemas found"


def test_ensure_output_dirs_creates_subdirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(p, "output_dir", lambda: tmp_path / "out")
    base = p.ensure_output_dirs()
    for sub in ("svg", "obj", "blender", "desktop_exports"):
        assert (base / sub).is_dir()


def test_is_frozen_is_false_in_source_tree() -> None:
    # We're running tests from the source tree, so this must be False.
    assert p.is_frozen() is False
