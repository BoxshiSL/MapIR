from __future__ import annotations

from pathlib import Path

from mapir.render.svg_renderer import render
from mapir.utils.io import load_ir


def test_scene_svg_is_valid_xml_with_expected_pieces(scene_files: list[Path]) -> None:
    # v0.5 demos: scene + interior live side by side under examples/demos/.
    assert scene_files, "no scene/interior demo files found"
    target = scene_files[0]
    ir = load_ir(target)
    svg = render(ir)
    assert svg.startswith("<svg")
    assert "viewBox=" in svg
    assert 'class="legend"' in svg
    # At least one zone name should appear as a label.
    assert any(z.name in svg for z in ir.zones)


def test_world_svg_contains_districts_and_legend(world_files: list[Path]) -> None:
    assert world_files, "no world demo files found"
    target = world_files[0]
    ir = load_ir(target)
    svg = render(ir)
    assert "<svg" in svg
    assert "viewBox=" in svg
    # At least one district name should appear as a label.
    assert any(d.name in svg for d in ir.districts)
    assert "Scene Slot" in svg  # legend entry


def test_label_scale_changes_font_sizes() -> None:
    """v0.5: render(label_scale=...) propagates into the CSS template."""
    from mapir.core.models import (
        District,
        Point2D,
        Polygon2D,
        SceneSlot,
        Size2D,
        WorldIR,
    )

    world = WorldIR(
        world_id="t",
        name="T",
        scale=Size2D(width_m=200.0, depth_m=200.0),
        theme="neutral",
        districts=[
            District(
                id="d1",
                name="D1",
                district_type="mixed",
                polygon=Polygon2D(
                    points=[
                        Point2D(x=0, y=0),
                        Point2D(x=100, y=0),
                        Point2D(x=100, y=100),
                        Point2D(x=0, y=100),
                    ]
                ),
            )
        ],
        scene_slots=[
            SceneSlot(
                id="s1",
                name="S1",
                position=Point2D(x=50, y=50),
                size=Size2D(width_m=10, depth_m=10),
            )
        ],
    )
    small = render(world, label_scale=0.5)
    large = render(world, label_scale=2.0)
    assert "font-size: 4.5px" in small
    assert "font-size: 18.0px" in large
