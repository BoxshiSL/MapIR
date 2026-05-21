from __future__ import annotations

from pathlib import Path

from mapir.render.svg_renderer import render
from mapir.utils.io import load_ir


def test_scene_svg_is_valid_xml_with_expected_pieces(scene_files: list[Path]) -> None:
    target = next(f for f in scene_files if "urban_alley" in f.name)
    svg = render(load_ir(target))
    assert svg.startswith("<svg")
    assert "viewBox=" in svg
    assert "Main Alley" in svg
    assert "Sotonbori" not in svg  # scene-only labels, no world name
    assert 'class="legend"' in svg


def test_world_svg_contains_districts_and_legend(world_files: list[Path]) -> None:
    target = next(f for f in world_files if "jisso" in f.name)
    svg = render(load_ir(target))
    assert "<svg" in svg
    assert "viewBox=" in svg
    assert "Sotonbori" in svg
    assert "Kita Central" in svg
    assert "Scene Slot" in svg  # legend entry
