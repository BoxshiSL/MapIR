"""v0.5: preview label scaling + per-layer visibility tests.

These run with ``QT_QPA_PLATFORM=offscreen`` so they don't need a display.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="PySide6 not installed")

from mapir.core.models import (  # noqa: E402  — must be after env var
    District,
    Point2D,
    Polygon2D,
    Road,
    SceneSlot,
    Size2D,
    WorldIR,
)
from mapir.core.enums import RoadType  # noqa: E402
from mapir.desktop.preview_scene import (  # noqa: E402
    PreviewOptions,
    build_scene,
    default_layer_visibility,
)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def small_world() -> WorldIR:
    return WorldIR(
        world_id="lab",
        name="Lab World",
        scale=Size2D(width_m=200.0, depth_m=200.0),
        theme="neutral",
        districts=[
            District(
                id=f"d{i}",
                name=f"District {i}",
                district_type="mixed",
                polygon=Polygon2D(
                    points=[
                        Point2D(x=10.0 + i * 30, y=10.0),
                        Point2D(x=30.0 + i * 30, y=10.0),
                        Point2D(x=30.0 + i * 30, y=30.0),
                        Point2D(x=10.0 + i * 30, y=30.0),
                    ]
                ),
            )
            for i in range(3)
        ],
        roads=[
            Road(
                id="r1",
                name="A1",
                road_type=RoadType.PRIMARY,
                points=[Point2D(x=10, y=20), Point2D(x=100, y=20)],
                width_m=4.0,
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


def test_build_scene_accepts_no_options(qapp, small_world: WorldIR) -> None:
    """v0.4 compatibility: calling without options still works."""
    scene = build_scene(small_world)
    assert scene.items(), "scene should contain at least the bounds rect"


def test_label_scale_applies(qapp, small_world: WorldIR) -> None:
    small = build_scene(
        small_world,
        PreviewOptions(label_scale=0.5, suppress_overlap=False, auto_scale=False),
    )
    large = build_scene(
        small_world,
        PreviewOptions(label_scale=2.0, suppress_overlap=False, auto_scale=False),
    )
    # In Qt graphics scenes labels are QGraphicsSimpleTextItems; the
    # easiest robust check is to compare bounding rect totals — bigger scale
    # ⇒ bigger total label area.
    from PySide6.QtWidgets import QGraphicsSimpleTextItem

    def label_area(scene) -> float:
        return sum(
            i.boundingRect().width() * i.boundingRect().height()
            for i in scene.items()
            if isinstance(i, QGraphicsSimpleTextItem)
        )

    assert label_area(large) > label_area(small)


def test_visibility_off_drops_layer(qapp, small_world: WorldIR) -> None:
    visibility = default_layer_visibility()
    visibility["roads"] = False
    options = PreviewOptions(layer_visibility=visibility, suppress_overlap=False)
    scene = build_scene(small_world, options)

    # Without roads, no QGraphicsLineItem should remain (lines are produced
    # only by ``_draw_road``).
    from PySide6.QtWidgets import QGraphicsLineItem

    lines = [i for i in scene.items() if isinstance(i, QGraphicsLineItem)]
    assert lines == []


def test_overlap_suppression_drops_labels(qapp) -> None:
    """Three overlapping districts at the same centroid produce label drops."""
    world = WorldIR(
        world_id="overlap",
        name="Overlap",
        scale=Size2D(width_m=100, depth_m=100),
        theme="neutral",
        districts=[
            District(
                id=f"d{i}",
                name=f"District With A Really Long Name {i}",
                district_type="mixed",
                polygon=Polygon2D(
                    points=[
                        Point2D(x=10, y=10),
                        Point2D(x=90, y=10),
                        Point2D(x=90, y=90),
                        Point2D(x=10, y=90),
                    ]
                ),
            )
            for i in range(3)
        ],
        scene_slots=[
            SceneSlot(
                id="s1",
                name="S1",
                position=Point2D(x=50, y=50),
                size=Size2D(width_m=5, depth_m=5),
            )
        ],
    )
    options = PreviewOptions(suppress_overlap=True, auto_scale=False)
    build_scene(world, options)
    assert options.dropped_labels >= 1
