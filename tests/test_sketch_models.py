"""v0.5 Phase B: SketchDocument + sketch_state tests."""

from __future__ import annotations

import pytest

from mapir.canvas.sketch_models import (
    SketchDistrict,
    SketchDocument,
    SketchPOI,
    SketchPOIType,
    SketchRoad,
    SketchRoadType,
    SketchSceneSlot,
)
from mapir.canvas.sketch_state import (
    add_district,
    add_poi,
    add_road,
    add_scene_slot,
    delete_by_id,
    new_sketch_document,
)
from mapir.core.models import Point2D, Polygon2D, Size2D
from mapir.generation.templates import get_template


def test_sketch_document_roundtrip() -> None:
    tpl = get_template("world_modern_island_city")
    sketch = new_sketch_document(tpl)
    blob = sketch.model_dump_json()
    restored = SketchDocument.model_validate_json(blob)
    assert restored.sketch_id == sketch.sketch_id
    assert restored.document_type == sketch.document_type
    assert len(restored.districts) == len(sketch.districts)
    assert len(restored.scene_slots) == len(sketch.scene_slots)


def test_sketch_road_types_cover_v05_taxonomy() -> None:
    expected = {"arterial", "collector", "local", "alley", "path", "trail", "service"}
    actual = {t.value for t in SketchRoadType}
    assert expected == actual


def test_new_sketch_from_template_world() -> None:
    tpl = get_template("world_modern_island_city")
    sketch = new_sketch_document(tpl)
    assert sketch.document_type == "world"
    assert sketch.template_id == tpl.template_id
    assert len(sketch.districts) == len(tpl.default_districts)
    assert sketch.scene_slots, "expected initial scene slot"
    assert sketch.llm_brief  # template recommends one


def test_new_sketch_from_template_interior() -> None:
    tpl = get_template("interior_warehouse")
    sketch = new_sketch_document(tpl)
    assert sketch.document_type == "interior"
    assert len(sketch.districts) == len(tpl.default_districts)


def test_add_and_delete_helpers() -> None:
    tpl = get_template("scene_industrial_port")
    sketch = new_sketch_document(tpl)
    initial_roads = len(sketch.roads)

    road = add_road(
        sketch,
        [Point2D(x=10, y=10), Point2D(x=50, y=10)],
        name="Demo",
        road_type=SketchRoadType.LOCAL,
        width_m=5.0,
    )
    assert len(sketch.roads) == initial_roads + 1
    assert isinstance(road, SketchRoad)

    poi = add_poi(sketch, Point2D(x=30, y=30), name="Watchtower")
    assert isinstance(poi, SketchPOI)
    assert poi.poi_type == SketchPOIType.LANDMARK

    slot = add_scene_slot(sketch, Point2D(x=20, y=20))
    assert isinstance(slot, SketchSceneSlot)

    # delete each via helper
    assert delete_by_id(sketch, road.id) is True
    assert delete_by_id(sketch, poi.id) is True
    assert delete_by_id(sketch, slot.id) is True
    assert delete_by_id(sketch, "does_not_exist") is False


def test_add_road_rejects_single_point() -> None:
    tpl = get_template("scene_industrial_port")
    sketch = new_sketch_document(tpl)
    with pytest.raises(ValueError):
        add_road(sketch, [Point2D(x=1, y=1)])


def test_add_district_appends_polygon() -> None:
    tpl = get_template("scene_industrial_port")
    sketch = new_sketch_document(tpl)
    polygon = Polygon2D(
        points=[
            Point2D(x=0, y=0),
            Point2D(x=10, y=0),
            Point2D(x=10, y=10),
            Point2D(x=0, y=10),
        ]
    )
    d = add_district(sketch, polygon, name="Hand-drawn", district_type="custom")
    assert isinstance(d, SketchDistrict)
    assert sketch.districts[-1] is d
    assert d.district_type == "custom"
