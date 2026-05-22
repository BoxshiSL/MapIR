"""Convert a :class:`TemplateDefinition` into a minimal validator-passing IR.

This is the v0.5 Phase-A scaffolding used by:

* the New Project Wizard, when the user clicks "Create",
* the ``scripts/build_demo_fixtures.py`` CLI runner that produces the
  ``examples/demos/*.json`` files committed to the repo,
* the CLI ``new-from-template`` command (added in Phase C).

It is *not* the full generation pipeline — that arrives in Phase B (under
``mapir.generation.pipeline``) and produces ``GeneratedLayout`` objects with
roads, parcels, buildings, landmarks, scene slots, and guidance cues. For
Phase A we only need a starting document the user can iterate on.
"""

from __future__ import annotations

from mapir.core.enums import (
    Density,
    EntranceType,
    MarkerType,
    RoadType,
    SceneObjectType,
    ScenePathType,
    SceneType,
    ZoneType,
)
from mapir.core.models import (
    POI,
    District,
    Entrance,
    GameplayMarker,
    Point2D,
    Point3D,
    Polygon2D,
    Road,
    SceneBounds,
    SceneIR,
    SceneObject,
    SceneSlot,
    SceneZone,
    ScenePath,
    Size2D,
    Size3D,
    Transform3D,
    WorldIR,
)

from .templates import DistrictPreset, TemplateDefinition

INTERIOR_ZONE_TYPES = (
    ZoneType.ROOM,
    ZoneType.SERVICE_AREA,
    ZoneType.STORAGE,
    ZoneType.PRIVATE_AREA,
)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _bbox_to_polygon(bbox: list[float], max_w: float, max_d: float) -> Polygon2D:
    x0, y0, x1, y1 = bbox
    x0 = _clamp(x0, 0.0, max_w)
    y0 = _clamp(y0, 0.0, max_d)
    x1 = _clamp(x1, x0 + 1.0, max_w)
    y1 = _clamp(y1, y0 + 1.0, max_d)
    return Polygon2D(
        points=[
            Point2D(x=x0, y=y0),
            Point2D(x=x1, y=y0),
            Point2D(x=x1, y=y1),
            Point2D(x=x0, y=y1),
        ]
    )


def _bbox_centroid(bbox: list[float]) -> Point2D:
    x0, y0, x1, y1 = bbox
    return Point2D(x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0)


def _slug(name: str) -> str:
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "_", "-"):
            out.append("_")
    s = "".join(out).strip("_")
    while "__" in s:
        s = s.replace("__", "_")
    return s or "x"


def _density(preset: DistrictPreset) -> Density:
    try:
        return Density(preset.density.value)
    except Exception:
        return Density.MEDIUM


def _scene_zone_type(preset: DistrictPreset, *, interior: bool) -> ZoneType:
    dt = preset.district_type.lower()
    if interior:
        if "storage" in dt:
            return ZoneType.STORAGE
        if "service" in dt or "corridor" in dt:
            return ZoneType.SERVICE_AREA
        if "executive" in dt or "apartment" in dt or "private" in dt:
            return ZoneType.PRIVATE_AREA
        return ZoneType.ROOM
    if "alley" in dt or "trail" in dt or "road" in dt:
        return ZoneType.PATH
    if "yard" in dt or "compound" in dt or "rooftop" in dt or "plaza" in dt:
        return ZoneType.EXTERIOR_YARD
    if "checkpoint" in dt or "combat" in dt or "arena" in dt:
        return ZoneType.COMBAT_SPACE
    if "forest" in dt or "wetland" in dt or "grove" in dt:
        return ZoneType.EXTERIOR_YARD
    if "alcove" in dt or "wall_facade" in dt:
        return ZoneType.SAFE_ZONE
    if "building" in dt or "outbuilding" in dt or "landmark" in dt or "dock" in dt:
        return ZoneType.PUBLIC_AREA
    return ZoneType.PUBLIC_AREA


# ============================================================
# World
# ============================================================


def instantiate_world(
    tpl: TemplateDefinition,
    *,
    include_cover_pois: bool = True,
    name_override: str | None = None,
) -> WorldIR:
    """Build a validator-passing WorldIR from a World template."""
    assert tpl.document_type == "world", f"Expected world template, got {tpl.document_type}"
    w = tpl.default_size.width_m
    d = tpl.default_size.depth_m

    districts: list[District] = []
    centroids: list[Point2D] = []
    for i, preset in enumerate(tpl.default_districts):
        district_id = f"d_{i:02d}_{_slug(preset.name)}"
        districts.append(
            District(
                id=district_id,
                name=preset.name,
                district_type=preset.district_type,
                polygon=_bbox_to_polygon(preset.bbox, w, d),
                density=_density(preset),
                tags=list(preset.tags),
                gameplay_tags=[p.value for p in preset.gameplay_profiles],
            )
        )
        centroids.append(_bbox_centroid(preset.bbox))

    if not districts:
        polygon = _bbox_to_polygon([w * 0.05, d * 0.05, w * 0.95, d * 0.95], w, d)
        districts = [
            District(
                id="d_default",
                name="Default District",
                district_type="mixed",
                polygon=polygon,
            )
        ]
        centroids = [Point2D(x=w / 2.0, y=d / 2.0)]

    roads: list[Road] = []
    if len(centroids) >= 2:
        roads.append(
            Road(
                id="r_arterial",
                name="Arterial",
                road_type=RoadType.PRIMARY,
                points=centroids[: min(len(centroids), 4)],
                width_m=12.0,
            )
        )

    pois: list[POI] = []
    if include_cover_pois:
        for i, (district, centroid) in enumerate(zip(districts, centroids, strict=False)):
            if i >= 2:
                break
            pois.append(
                POI(
                    id=f"poi_{district.id}_landmark",
                    name=f"{district.name} Landmark",
                    poi_type="landmark",
                    position=centroid,
                    tags=["from_template"],
                )
            )

    first = districts[0]
    first_centroid = centroids[0]
    scene_slots = [
        SceneSlot(
            id="slot_main",
            name=f"{first.name} Scene Slot",
            district_id=first.id,
            position=first_centroid,
            size=Size2D(width_m=60.0, depth_m=40.0),
            allowed_scene_types=[SceneType.EXTERIOR_LOCATION],
        )
    ]

    return WorldIR(
        world_id=f"from_{tpl.template_id}",
        name=name_override or tpl.name,
        description=tpl.description,
        scale=Size2D(width_m=w, depth_m=d),
        theme=tpl.genre,
        tags=["from_template", "v0.5", tpl.genre],
        districts=districts,
        roads=roads,
        pois=pois,
        scene_slots=scene_slots,
    )


# ============================================================
# Scene / Interior
# ============================================================


def instantiate_scene(
    tpl: TemplateDefinition,
    *,
    interior: bool | None = None,
    include_cover_objects: bool = True,
    name_override: str | None = None,
) -> SceneIR:
    """Build a validator-passing SceneIR from a scene or interior template.

    ``interior`` is auto-detected from ``tpl.document_type`` if not provided.
    """
    if interior is None:
        interior = tpl.document_type == "interior"
    assert tpl.document_type in ("scene", "interior"), tpl.document_type
    w = tpl.default_size.width_m
    d = tpl.default_size.depth_m
    bounds = SceneBounds(
        width_m=w,
        depth_m=d,
        height_m=6.0 if interior else 20.0,
    )

    zones: list[SceneZone] = []
    centroids: list[Point2D] = []
    for i, preset in enumerate(tpl.default_districts):
        zone_id = f"z_{i:02d}_{_slug(preset.name)}"
        zones.append(
            SceneZone(
                id=zone_id,
                name=preset.name,
                zone_type=_scene_zone_type(preset, interior=interior),
                polygon=_bbox_to_polygon(preset.bbox, w, d),
                tags=list(preset.tags),
                gameplay_tags=[p.value for p in preset.gameplay_profiles],
            )
        )
        centroids.append(_bbox_centroid(preset.bbox))

    if not zones:
        margin = 1.0
        zones = [
            SceneZone(
                id="z_default",
                name="Default Zone",
                zone_type=ZoneType.ROOM if interior else ZoneType.PUBLIC_AREA,
                polygon=_bbox_to_polygon([margin, margin, w - margin, d - margin], w, d),
            )
        ]
        centroids = [Point2D(x=w / 2.0, y=d / 2.0)]

    if interior and not any(z.zone_type in INTERIOR_ZONE_TYPES for z in zones):
        z0 = zones[0]
        zones[0] = SceneZone(
            id=z0.id,
            name=z0.name,
            zone_type=ZoneType.ROOM,
            polygon=z0.polygon,
            tags=z0.tags,
            gameplay_tags=z0.gameplay_tags,
        )

    margin_x = max(0.5, w * 0.02)
    entrances = [
        Entrance(
            id="e_main",
            name="Main Entrance",
            position=Point2D(x=margin_x, y=d / 2.0),
            entrance_type=EntranceType.MAIN,
        )
    ]

    paths: list[ScenePath] = []
    if not interior and len(centroids) >= 2:
        paths.append(
            ScenePath(
                id="p_main_route",
                name="Main Route",
                path_type=ScenePathType.MAIN_ROUTE,
                points=centroids[: min(len(centroids), 4)],
                width_m=3.0,
            )
        )

    objects: list[SceneObject] = []
    markers: list[GameplayMarker] = []
    if include_cover_objects:
        for i, c in enumerate(centroids[:3]):
            objects.append(
                SceneObject(
                    id=f"obj_cover_{i:02d}",
                    name=f"Cover {i + 1}",
                    object_type=SceneObjectType.COVER,
                    transform=Transform3D(position=Point3D(x=c.x, y=c.y, z=0.0)),
                    size=Size3D(width_m=1.2, depth_m=1.2, height_m=1.1),
                    gameplay_tags=["cover"],
                )
            )
            markers.append(
                GameplayMarker(
                    id=f"mk_cover_{i:02d}",
                    marker_type=MarkerType.COVER,
                    position=c,
                    radius_m=0.8,
                )
            )

    return SceneIR(
        scene_id=f"from_{tpl.template_id}",
        name=name_override or tpl.name,
        description=tpl.description,
        scene_type=SceneType.INTERIOR if interior else SceneType.EXTERIOR_LOCATION,
        standalone=True,
        bounds=bounds,
        theme=tpl.genre,
        tags=["from_template", "v0.5", tpl.genre],
        zones=zones,
        entrances=entrances,
        paths=paths,
        objects=objects,
        gameplay_markers=markers,
    )


def instantiate(tpl: TemplateDefinition, **kwargs) -> WorldIR | SceneIR:
    """Dispatch by ``document_type``."""
    if tpl.document_type == "world":
        return instantiate_world(tpl, **kwargs)
    return instantiate_scene(tpl, **kwargs)
