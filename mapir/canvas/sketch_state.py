"""SketchDocument helpers — construct an empty sketch from a template.

This is the v0.5 alternative to v0.4's "go from JSON straight to IR" flow.
The user creates a ``SketchDocument`` (seeded from a template), iterates on
it in the Canvas / District Inspector, and only generates IR when ready.
"""

from __future__ import annotations

import uuid

from ..core.models import Point2D, Polygon2D, Size2D
from ..generation.gameplay_metrics import GameplayMetrics
from ..generation.templates import DistrictPreset, TemplateDefinition
from .sketch_models import (
    LLMSettingsOverride,
    SketchDistrict,
    SketchDocument,
    SketchPOI,
    SketchPOIType,
    SketchRoad,
    SketchRoadType,
    SketchSceneSlot,
)


def _slug(name: str) -> str:
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("_")
    s = "".join(out).strip("_")
    while "__" in s:
        s = s.replace("__", "_")
    return s or "x"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _bbox_to_polygon(bbox: list[float], w: float, d: float) -> Polygon2D:
    x0, y0, x1, y1 = bbox
    x0 = _clamp(x0, 0.0, w)
    y0 = _clamp(y0, 0.0, d)
    x1 = _clamp(x1, x0 + 1.0, w)
    y1 = _clamp(y1, y0 + 1.0, d)
    return Polygon2D(
        points=[
            Point2D(x=x0, y=y0),
            Point2D(x=x1, y=y0),
            Point2D(x=x1, y=y1),
            Point2D(x=x0, y=y1),
        ]
    )


def new_sketch_document(
    template: TemplateDefinition,
    *,
    name: str | None = None,
    sketch_id: str | None = None,
    metrics_override: GameplayMetrics | None = None,
) -> SketchDocument:
    """Seed a ``SketchDocument`` from a template's defaults."""
    w = template.default_size.width_m
    d = template.default_size.depth_m
    sid = sketch_id or f"sketch_{uuid.uuid4().hex[:10]}"

    districts: list[SketchDistrict] = []
    for i, preset in enumerate(template.default_districts):
        districts.append(_district_from_preset(preset, i, w, d))

    # One scene slot at the first district centroid so the sketch is
    # non-empty in the Canvas right away.
    scene_slots: list[SketchSceneSlot] = []
    if districts:
        first = districts[0]
        cx = sum(p.x for p in first.polygon.points) / len(first.polygon.points)
        cy = sum(p.y for p in first.polygon.points) / len(first.polygon.points)
        scene_slots.append(
            SketchSceneSlot(
                id="slot_initial",
                name=f"{first.name} Scene Slot",
                position=Point2D(x=cx, y=cy),
                size=Size2D(width_m=min(60.0, w * 0.1), depth_m=min(40.0, d * 0.1)),
                district_id=first.id,
                gameplay_role="initial",
            )
        )

    return SketchDocument(
        sketch_id=sid,
        name=name or template.name,
        document_type=template.document_type,
        template_id=template.template_id,
        size=Size2D(width_m=w, depth_m=d),
        districts=districts,
        roads=[],
        pois=[],
        scene_slots=scene_slots,
        notes=[],
        metrics=metrics_override or template.default_metrics,
        llm_brief=template.recommended_llm_brief,
    )


def _district_from_preset(
    preset: DistrictPreset, idx: int, w: float, d: float
) -> SketchDistrict:
    return SketchDistrict(
        id=f"d_{idx:02d}_{_slug(preset.name)}",
        name=preset.name,
        polygon=_bbox_to_polygon(preset.bbox, w, d),
        district_type=preset.district_type,
        role=preset.role,
        theme=preset.theme,
        density=preset.density.value,
        height_profile=preset.height_profile.value,
        building_style=preset.building_style,
        road_pattern=preset.road_pattern,
        gameplay_profiles=list(preset.gameplay_profiles),
        tags=list(preset.tags),
        generation_settings=LLMSettingsOverride(),
    )


# ---- mutation helpers used by the Canvas tool controller ---------------


def add_district(
    sketch: SketchDocument,
    polygon: Polygon2D,
    *,
    name: str = "New District",
    district_type: str = "mixed",
) -> SketchDistrict:
    idx = len(sketch.districts)
    district = SketchDistrict(
        id=f"d_{idx:02d}_{_slug(name)}_{uuid.uuid4().hex[:4]}",
        name=name,
        polygon=polygon,
        district_type=district_type,
    )
    sketch.districts.append(district)
    return district


def add_road(
    sketch: SketchDocument,
    points: list[Point2D],
    *,
    name: str = "",
    road_type: SketchRoadType = SketchRoadType.LOCAL,
    width_m: float = 4.0,
) -> SketchRoad:
    if len(points) < 2:
        raise ValueError("road needs at least 2 points")
    idx = len(sketch.roads)
    road = SketchRoad(
        id=f"r_{idx:03d}_{uuid.uuid4().hex[:4]}",
        name=name,
        road_type=road_type,
        points=points,
        width_m=width_m,
    )
    sketch.roads.append(road)
    return road


def add_poi(
    sketch: SketchDocument,
    position: Point2D,
    *,
    name: str = "New POI",
    poi_type: SketchPOIType = SketchPOIType.LANDMARK,
) -> SketchPOI:
    idx = len(sketch.pois)
    poi = SketchPOI(
        id=f"poi_{idx:03d}_{uuid.uuid4().hex[:4]}",
        name=name,
        poi_type=poi_type,
        position=position,
    )
    sketch.pois.append(poi)
    return poi


def add_scene_slot(
    sketch: SketchDocument,
    position: Point2D,
    *,
    name: str = "New Scene Slot",
    size: Size2D | None = None,
    district_id: str | None = None,
) -> SketchSceneSlot:
    idx = len(sketch.scene_slots)
    slot = SketchSceneSlot(
        id=f"slot_{idx:03d}_{uuid.uuid4().hex[:4]}",
        name=name,
        position=position,
        size=size or Size2D(width_m=20.0, depth_m=15.0),
        district_id=district_id,
    )
    sketch.scene_slots.append(slot)
    return slot


def delete_by_id(sketch: SketchDocument, target_id: str) -> bool:
    """Remove the first item with the matching id from any layer."""
    for collection_name in ("districts", "roads", "pois", "scene_slots", "notes"):
        collection = getattr(sketch, collection_name)
        for i, item in enumerate(collection):
            if item.id == target_id:
                collection.pop(i)
                return True
    return False
