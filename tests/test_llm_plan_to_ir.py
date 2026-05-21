"""Deterministic Plan → IR conversion must always produce validator-friendly IR."""

from __future__ import annotations

from mapir.core.enums import EntranceType, MarkerType, RoadType, SceneType, ZoneType
from mapir.core.geometry import polygon_bbox
from mapir.core.validation import validate as run_validation
from mapir.llm.plan_to_ir import scene_plan_to_scene_ir, world_plan_to_world_ir
from mapir.llm.schemas import (
    BoundsPlan,
    DistrictPlan,
    EntrancePlan,
    MarkerPlan,
    ObjectPlan,
    PathPlan,
    POIPlan,
    RoadPlan,
    ScalePlan,
    ScenePlan,
    SceneSlotPlan,
    WaterPlan,
    WorldPlan,
    ZonePlan,
)


def _basic_world_plan() -> WorldPlan:
    return WorldPlan(
        world_id="test_world",
        name="Test City",
        theme="test",
        scale=ScalePlan(width_m=3000.0, depth_m=2000.0),
        tags=["test"],
        districts=[
            DistrictPlan(id="d_north", name="North", district_type="business"),
            DistrictPlan(id="d_south", name="South", district_type="industrial"),
            DistrictPlan(id="d_east", name="East", district_type="residential"),
        ],
        roads=[RoadPlan(id="r_main", road_type="primary", connects=["d_north", "d_south"])],
        water_bodies=[WaterPlan(id="w_bay", name="Bay", water_type="sea", role="sea")],
        pois=[POIPlan(id="poi_shrine", name="Shrine", poi_type="landmark", district_hint="d_east")],
        scene_slots=[
            SceneSlotPlan(id="slot_a", name="Slot A", district_id="d_north"),
            SceneSlotPlan(id="slot_b", name="Slot B", district_id="d_south"),
        ],
    )


def _basic_scene_plan(scene_type: str = "exterior_location") -> ScenePlan:
    return ScenePlan(
        scene_id="test_scene",
        name="Test Alley",
        scene_type=scene_type,
        preset="urban_alley",
        bounds=BoundsPlan(width_m=80.0, depth_m=45.0, height_m=25.0),
        theme="urban_night",
        tags=["test"],
        zones=[
            ZonePlan(id="z_main", name="Main", zone_type="path"),
            ZonePlan(id="z_combat", name="Combat", zone_type="combat_space"),
            ZonePlan(id="z_service", name="Service", zone_type="service_area"),
        ],
        entrances=[
            EntrancePlan(id="e_main", name="Main", entrance_type="main", side="west"),
            EntrancePlan(id="e_side", name="Side", entrance_type="side", side="north"),
            EntrancePlan(id="e_back", name="Back", entrance_type="backdoor", side="east"),
        ],
        paths=[
            PathPlan(
                id="p_main", path_type="main_route", connects=["e_main", "e_back"], width_m=3.0
            ),
            PathPlan(
                id="p_esc", path_type="escape_route", connects=["z_main", "e_side"], width_m=2.0
            ),
        ],
        objects=[
            ObjectPlan(id="o_1", name="Dumpster A", object_type="container"),
            ObjectPlan(id="o_2", name="Dumpster B", object_type="container"),
        ],
        gameplay_markers=[MarkerPlan(id=f"m_cover_{i}", marker_type="cover") for i in range(5)],
    )


def test_world_plan_converts_to_valid_world_ir() -> None:
    plan = _basic_world_plan()
    world = world_plan_to_world_ir(plan)
    report = run_validation(world)
    assert report.is_valid, [i.format() for i in report.errors]
    assert len(world.districts) == 3
    assert len(world.scene_slots) == 2


def test_world_district_polygons_inside_scale() -> None:
    plan = _basic_world_plan()
    world = world_plan_to_world_ir(plan)
    width, depth = world.scale.width_m, world.scale.depth_m
    for d in world.districts:
        bb = polygon_bbox(d.polygon)
        assert bb.min_x >= 0.0
        assert bb.min_y >= 0.0
        assert bb.max_x <= width
        assert bb.max_y <= depth


def test_world_roads_have_valid_widths_and_points() -> None:
    plan = _basic_world_plan()
    world = world_plan_to_world_ir(plan)
    assert world.roads, "expected at least one road"
    for r in world.roads:
        assert r.width_m > 0
        assert len(r.points) >= 2
        assert r.road_type is RoadType.PRIMARY


def test_scene_plan_converts_to_valid_scene_ir() -> None:
    plan = _basic_scene_plan()
    scene = scene_plan_to_scene_ir(plan)
    report = run_validation(scene)
    assert report.is_valid, [i.format() for i in report.errors]
    assert scene.scene_type is SceneType.EXTERIOR_LOCATION
    assert len(scene.entrances) == 3
    assert len(scene.zones) == 3


def test_scene_markers_and_entrances_inside_bounds() -> None:
    plan = _basic_scene_plan()
    scene = scene_plan_to_scene_ir(plan)
    w, d = scene.bounds.width_m, scene.bounds.depth_m
    for e in scene.entrances:
        assert 0.0 <= e.position.x <= w
        assert 0.0 <= e.position.y <= d
    for m in scene.gameplay_markers:
        assert 0.0 <= m.position.x <= w
        assert 0.0 <= m.position.y <= d
    for p in scene.paths:
        for pt in p.points:
            assert 0.0 <= pt.x <= w
            assert 0.0 <= pt.y <= d


def test_interior_scene_gets_room_zone_when_missing() -> None:
    # Interior plan that only declares a 'path' zone — converter must promote one
    # to a room/storage/service/private_area to satisfy the validator.
    plan = ScenePlan(
        scene_id="interior_only",
        name="Bare Interior",
        scene_type="interior",
        preset="warehouse_interior",
        bounds=BoundsPlan(width_m=30.0, depth_m=20.0, height_m=6.0),
        theme="industrial",
        zones=[ZonePlan(id="z_open", name="Open", zone_type="path")],
        entrances=[EntrancePlan(id="e_main", name="Main", entrance_type="main", side="west")],
    )
    scene = scene_plan_to_scene_ir(plan)
    report = run_validation(scene)
    assert report.is_valid, [i.format() for i in report.errors]
    assert any(
        z.zone_type
        in {ZoneType.ROOM, ZoneType.SERVICE_AREA, ZoneType.STORAGE, ZoneType.PRIVATE_AREA}
        for z in scene.zones
    )


def test_exterior_scene_without_paths_gets_default_route() -> None:
    plan = ScenePlan(
        scene_id="ext_no_paths",
        name="Bare Exterior",
        scene_type="exterior_location",
        preset="custom",
        bounds=BoundsPlan(width_m=50.0, depth_m=40.0, height_m=20.0),
        theme="urban",
        zones=[ZonePlan(id="z_room_like", name="Inside", zone_type="room")],
        entrances=[EntrancePlan(id="e_main", name="Main", entrance_type="main", side="west")],
    )
    scene = scene_plan_to_scene_ir(plan)
    report = run_validation(scene)
    assert report.is_valid, [i.format() for i in report.errors]
    assert scene.paths, "default route should have been injected for exterior scene"


def test_entrance_type_coercion_falls_back_to_main() -> None:
    plan = ScenePlan(
        scene_id="ent_test",
        name="ent_test",
        scene_type="exterior_location",
        preset="custom",
        bounds=BoundsPlan(width_m=40.0, depth_m=30.0, height_m=10.0),
        theme="t",
        zones=[ZonePlan(id="z1", name="z1", zone_type="combat_space")],
        entrances=[EntrancePlan(id="e_x", name="x", entrance_type="not_a_real_type", side="west")],
    )
    scene = scene_plan_to_scene_ir(plan)
    assert scene.entrances[0].entrance_type is EntranceType.MAIN


def test_marker_default_type_when_unknown() -> None:
    plan = _basic_scene_plan()
    # Replace markers with one of an unknown type.
    plan.gameplay_markers = [MarkerPlan(id="m_x", marker_type="not_real")]
    scene = scene_plan_to_scene_ir(plan)
    assert scene.gameplay_markers[0].marker_type is MarkerType.COVER
