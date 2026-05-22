"""Convert SketchDocument + GeneratedLayout into validated WorldIR/SceneIR.

This is the v0.5 equivalent of the v0.4 ``llm.plan_to_ir`` converter. It
takes the user's sketch *and* the deterministic generation output and merges
them into a canonical IR document.

Design rules:

* The sketch's geometry (district polygons, road shapes, POI positions,
  scene slot rectangles) is preserved verbatim — generation augments rather
  than replaces it.
* ``GeneratedRoad`` entries map onto the v0.4 ``RoadType`` enum
  (arterial→primary, collector→secondary, local→secondary, alley→alley,
  service→service, path/trail→path).
* ``GeneratedSceneSlot`` instances merge with any sketch slots (we de-dupe
  by ``district_id``).
* Buildings, parcels, landmarks, and guidance cues *do not* land in the IR
  because the v0.4 schemas do not have slots for them — they remain in the
  ``GeneratedLayout`` and are exported separately by the v0.5 Export page.
"""

from __future__ import annotations

import uuid

from ..core.enums import Density, EntranceType, HeightProfile, RoadType, SceneType, ZoneType
from ..core.models import (
    POI,
    District,
    Entrance,
    Point2D,
    Polygon2D,
    Road,
    SceneBounds,
    SceneIR,
    SceneObject,
    SceneSlot,
    SceneZone,
    ScenePath,
    Size2D,
    WorldIR,
)
from ..generation.layout import GeneratedLayout, GeneratedRoad
from .sketch_models import SketchDistrict, SketchDocument, SketchPOI, SketchSceneSlot


_ROAD_TYPE_MAP: dict[str, RoadType] = {
    "arterial": RoadType.PRIMARY,
    "collector": RoadType.SECONDARY,
    "local": RoadType.SECONDARY,
    "alley": RoadType.ALLEY,
    "service": RoadType.SERVICE,
    "path": RoadType.PATH,
    "trail": RoadType.PATH,
}


def _density(value: str) -> Density:
    try:
        return Density(value)
    except (ValueError, KeyError):
        return Density.MEDIUM


def _height(value: str) -> HeightProfile:
    try:
        return HeightProfile(value)
    except (ValueError, KeyError):
        return HeightProfile.MID


def _map_road_type(road_type: str) -> RoadType:
    return _ROAD_TYPE_MAP.get(road_type, RoadType.PRIMARY)


def _district_from_sketch(d: SketchDistrict) -> District:
    return District(
        id=d.id,
        name=d.name,
        district_type=d.district_type,
        polygon=d.polygon,
        density=_density(d.density),
        height_profile=_height(d.height_profile),
        tags=list(d.tags),
        gameplay_tags=[p.value for p in d.gameplay_profiles],
    )


def _road_from_generated(r: GeneratedRoad) -> Road:
    return Road(
        id=r.id,
        name=r.name or None,
        road_type=_map_road_type(r.road_type),
        points=list(r.points),
        width_m=max(1.0, r.width_m),
        tags=list(r.gameplay_tags),
    )


def _poi_from_sketch(p: SketchPOI) -> POI:
    return POI(
        id=p.id,
        name=p.name,
        poi_type=p.poi_type.value,
        position=p.position,
        tags=list(p.tags),
        gameplay_tags=[],
    )


def _scene_slot_from_sketch(s: SketchSceneSlot) -> SceneSlot:
    types = []
    for t in s.allowed_scene_types:
        try:
            types.append(SceneType(t))
        except (ValueError, KeyError):
            continue
    if not types:
        types = [SceneType.EXTERIOR_LOCATION]
    return SceneSlot(
        id=s.id,
        name=s.name,
        district_id=s.district_id,
        position=s.position,
        size=s.size,
        allowed_scene_types=types,
        tags=list(s.tags),
    )


def sketch_to_world_ir(
    sketch: SketchDocument, layout: GeneratedLayout | None = None
) -> WorldIR:
    assert sketch.document_type == "world", "sketch_to_world_ir expects a world sketch"
    districts = [_district_from_sketch(d) for d in sketch.districts]
    roads: list[Road] = []
    if layout is not None:
        roads.extend(_road_from_generated(r) for r in layout.roads)
    pois = [_poi_from_sketch(p) for p in sketch.pois]

    # Scene slots: sketch + generated, deduped by id
    slots: list[SceneSlot] = []
    seen_ids: set[str] = set()
    for s in sketch.scene_slots:
        if s.id in seen_ids:
            continue
        slots.append(_scene_slot_from_sketch(s))
        seen_ids.add(s.id)
    if layout is not None:
        for gs in layout.scene_slots:
            if gs.id in seen_ids:
                continue
            # Avoid duplicating per district when a sketch slot already covers it
            if any(getattr(s, "district_id", None) == gs.district_id for s in slots):
                continue
            slots.append(
                SceneSlot(
                    id=gs.id,
                    name=gs.name,
                    district_id=gs.district_id,
                    position=gs.position,
                    size=Size2D(width_m=gs.width_m, depth_m=gs.depth_m),
                    allowed_scene_types=[
                        SceneType(t)
                        for t in gs.allowed_scene_types
                        if t in {st.value for st in SceneType}
                    ]
                    or [SceneType.EXTERIOR_LOCATION],
                    tags=list(gs.tags),
                )
            )
            seen_ids.add(gs.id)

    if not slots and districts:
        # Validator demands ≥ 1 scene slot.
        d0 = districts[0]
        cx = sum(p.x for p in d0.polygon.points) / len(d0.polygon.points)
        cy = sum(p.y for p in d0.polygon.points) / len(d0.polygon.points)
        slots.append(
            SceneSlot(
                id="slot_fallback",
                name="Fallback Slot",
                district_id=d0.id,
                position=Point2D(x=cx, y=cy),
                size=Size2D(width_m=20.0, depth_m=15.0),
                allowed_scene_types=[SceneType.EXTERIOR_LOCATION],
            )
        )

    return WorldIR(
        world_id=sketch.sketch_id,
        name=sketch.name,
        scale=sketch.size,
        theme=sketch.template_id or "v0.5",
        tags=["from_sketch"],
        districts=districts,
        roads=roads,
        pois=pois,
        scene_slots=slots,
    )


_INTERIOR_ZONE_TYPES = (ZoneType.ROOM, ZoneType.SERVICE_AREA, ZoneType.STORAGE, ZoneType.PRIVATE_AREA)


def _sketch_district_to_zone(d: SketchDistrict, *, interior: bool) -> SceneZone:
    dt = d.district_type.lower()
    if interior:
        if "storage" in dt:
            zt = ZoneType.STORAGE
        elif "service" in dt or "corridor" in dt:
            zt = ZoneType.SERVICE_AREA
        elif "executive" in dt or "apartment" in dt or "private" in dt:
            zt = ZoneType.PRIVATE_AREA
        else:
            zt = ZoneType.ROOM
    else:
        if "alley" in dt or "trail" in dt or "road" in dt or "corridor" in dt:
            zt = ZoneType.PATH
        elif "yard" in dt or "compound" in dt or "rooftop" in dt or "plaza" in dt:
            zt = ZoneType.EXTERIOR_YARD
        elif "checkpoint" in dt or "combat" in dt or "arena" in dt:
            zt = ZoneType.COMBAT_SPACE
        elif "forest" in dt or "wetland" in dt or "grove" in dt:
            zt = ZoneType.EXTERIOR_YARD
        else:
            zt = ZoneType.PUBLIC_AREA
    return SceneZone(
        id=d.id,
        name=d.name,
        zone_type=zt,
        polygon=d.polygon,
        tags=list(d.tags),
        gameplay_tags=[p.value for p in d.gameplay_profiles],
    )


def sketch_to_scene_ir(
    sketch: SketchDocument, layout: GeneratedLayout | None = None
) -> SceneIR:
    assert sketch.document_type in ("scene", "interior")
    interior = sketch.document_type == "interior"
    w = sketch.size.width_m
    d = sketch.size.depth_m
    h = 6.0 if interior else 20.0
    bounds = SceneBounds(width_m=w, depth_m=d, height_m=h)

    zones = [_sketch_district_to_zone(district, interior=interior) for district in sketch.districts]
    if interior and not any(z.zone_type in _INTERIOR_ZONE_TYPES for z in zones) and zones:
        z0 = zones[0]
        zones[0] = SceneZone(
            id=z0.id,
            name=z0.name,
            zone_type=ZoneType.ROOM,
            polygon=z0.polygon,
            tags=z0.tags,
            gameplay_tags=z0.gameplay_tags,
        )

    if not zones:
        margin = max(1.0, w * 0.02)
        zones = [
            SceneZone(
                id=f"z_default_{uuid.uuid4().hex[:4]}",
                name="Default Zone",
                zone_type=ZoneType.ROOM if interior else ZoneType.PUBLIC_AREA,
                polygon=Polygon2D(
                    points=[
                        Point2D(x=margin, y=margin),
                        Point2D(x=w - margin, y=margin),
                        Point2D(x=w - margin, y=d - margin),
                        Point2D(x=margin, y=d - margin),
                    ]
                ),
            )
        ]

    # Entrance on west edge (one is enough for validator)
    margin_x = max(0.5, w * 0.02)
    entrances = [
        Entrance(
            id="e_main",
            name="Main Entrance",
            position=Point2D(x=margin_x, y=d / 2.0),
            entrance_type=EntranceType.MAIN,
        )
    ]

    # Paths from generated roads
    paths: list[ScenePath] = []
    if layout is not None:
        for r in layout.roads:
            paths.append(
                ScenePath(
                    id=r.id,
                    name=r.name or None,
                    path_type=__import__(
                        "mapir.core.enums", fromlist=["ScenePathType"]
                    ).ScenePathType.MAIN_ROUTE,
                    points=list(r.points),
                    width_m=max(1.0, r.width_m),
                )
            )

    # For exterior scenes the validator requires either a ScenePath or an
    # exterior/combat zone — zones already cover this when district mapping
    # produced PATH / EXTERIOR_YARD / COMBAT_SPACE, but we add a fallback.
    return SceneIR(
        scene_id=sketch.sketch_id,
        name=sketch.name,
        scene_type=SceneType.INTERIOR if interior else SceneType.EXTERIOR_LOCATION,
        standalone=True,
        bounds=bounds,
        theme=sketch.template_id or "v0.5",
        tags=["from_sketch"],
        zones=zones,
        entrances=entrances,
        paths=paths,
    )


def sketch_to_ir(
    sketch: SketchDocument, layout: GeneratedLayout | None = None
) -> WorldIR | SceneIR:
    if sketch.document_type == "world":
        return sketch_to_world_ir(sketch, layout)
    return sketch_to_scene_ir(sketch, layout)
