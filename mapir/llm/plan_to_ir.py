"""Deterministic Plan → IR conversion.

The LLM produces a high-level Plan with semantic intent only. This module
generates safe blockout geometry from those plans:

    WorldPlan → WorldIR   (districts as a grid, roads connecting centroids,
                           water bodies on the south edge, scene slots and
                           POIs inside their owning district)

    ScenePlan → SceneIR   (zones tiled inside bounds, entrances on edges,
                           paths connecting referenced features, objects
                           positioned on a small grid, markers as points)

Geometry is intentionally simple: clipped to bounds, deterministic, validator-
friendly. v0.5 may add richer layout heuristics.
"""

from __future__ import annotations

import math
from typing import TypeVar

from ..core.enums import (
    ConstraintType,
    Density,
    EntranceType,
    HeightProfile,
    MarkerType,
    RoadType,
    SceneObjectType,
    ScenePathType,
    ScenePreset,
    SceneType,
    Severity,
    WaterType,
    ZoneType,
)
from ..core.models import (
    POI,
    Constraint,
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
    ScenePath,
    SceneSlot,
    SceneZone,
    Size2D,
    Size3D,
    Transform3D,
    WaterBody,
    WorldIR,
)
from .schemas import ScenePlan, WorldPlan

E = TypeVar("E")


def _coerce_enum(value: str | None, enum_cls: type[E], default: E) -> E:
    """Best-effort enum coercion: match by value, then case-insensitive name."""
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    try:
        return enum_cls(s)  # type: ignore[call-arg]
    except (ValueError, KeyError):
        pass
    upper = s.upper().replace("-", "_").replace(" ", "_")
    members = getattr(enum_cls, "__members__", {})
    if upper in members:
        return members[upper]
    lower = s.lower()
    for member in members.values():
        if getattr(member, "value", None) == lower:
            return member
    return default


def _rect(x0: float, y0: float, x1: float, y1: float) -> Polygon2D:
    return Polygon2D(
        points=[
            Point2D(x=x0, y=y0),
            Point2D(x=x1, y=y0),
            Point2D(x=x1, y=y1),
            Point2D(x=x0, y=y1),
        ]
    )


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ============================================================
# WorldPlan → WorldIR
# ============================================================


def world_plan_to_world_ir(plan: WorldPlan) -> WorldIR:
    width = plan.scale.width_m
    depth = plan.scale.depth_m

    n_districts = max(1, len(plan.districts))
    cols = max(1, math.ceil(math.sqrt(n_districts)))
    rows = max(1, math.ceil(n_districts / cols))
    cell_w = width / cols
    cell_d = depth / rows
    inner_margin_x = cell_w * 0.05
    inner_margin_y = cell_d * 0.05

    district_centroids: dict[str, Point2D] = {}
    districts: list[District] = []
    for i, dp in enumerate(plan.districts):
        col = i % cols
        row = i // cols
        x0 = col * cell_w + inner_margin_x
        y0 = row * cell_d + inner_margin_y
        x1 = (col + 1) * cell_w - inner_margin_x
        y1 = (row + 1) * cell_d - inner_margin_y
        # Clamp to world bounds with a tiny safety margin.
        x0 = _clamp(x0, 0.0, width)
        y0 = _clamp(y0, 0.0, depth)
        x1 = _clamp(x1, x0 + 1.0, width)
        y1 = _clamp(y1, y0 + 1.0, depth)
        polygon = _rect(x0, y0, x1, y1)
        centroid = Point2D(x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0)
        district_centroids[dp.id] = centroid

        districts.append(
            District(
                id=dp.id,
                name=dp.name,
                district_type=dp.district_type or "mixed",
                polygon=polygon,
                density=_coerce_enum(dp.density, Density, Density.MEDIUM),
                height_profile=_coerce_enum(dp.height_profile, HeightProfile, HeightProfile.MID),
                tags=list(dp.tags),
                gameplay_tags=list(dp.gameplay_tags),
            )
        )

    if not districts:
        # Validator requires ≥ 1 district; synthesise a single full-world block.
        polygon = _rect(width * 0.05, depth * 0.05, width * 0.95, depth * 0.95)
        districts.append(
            District(
                id="d_default",
                name="Default District",
                district_type="mixed",
                polygon=polygon,
            )
        )
        district_centroids["d_default"] = Point2D(x=width / 2.0, y=depth / 2.0)

    # Roads — connect listed district centroids; fall back to ordered centroids.
    roads: list[Road] = []
    for rp in plan.roads:
        points: list[Point2D] = []
        for did in rp.connects:
            c = district_centroids.get(did)
            if c is not None:
                points.append(c)
        if len(points) < 2:
            ordered = list(district_centroids.values())[:2]
            if len(ordered) < 2:
                continue
            points = ordered
        roads.append(
            Road(
                id=rp.id,
                name=rp.name,
                road_type=_coerce_enum(rp.road_type, RoadType, RoadType.PRIMARY),
                points=points,
                width_m=max(1.0, float(rp.width_m)),
            )
        )

    # Water bodies — south-edge strip; each gets a slice of the world width.
    water_bodies: list[WaterBody] = []
    water_plans = list(plan.water_bodies)
    if water_plans:
        strip_depth = max(20.0, depth * 0.06)
        slice_w = width / len(water_plans)
        for i, wp in enumerate(water_plans):
            x0 = i * slice_w + width * 0.005
            x1 = (i + 1) * slice_w - width * 0.005
            y0 = -strip_depth * 0.4  # slight overhang into the slack region
            y1 = strip_depth * 0.6
            # Keep polygon within slack tolerance (5% of max dim).
            slack = max(width, depth) * 0.04
            y0 = _clamp(y0, -slack, depth)
            y1 = _clamp(y1, y0 + 1.0, depth)
            water_bodies.append(
                WaterBody(
                    id=wp.id,
                    name=wp.name,
                    water_type=_coerce_enum(wp.water_type, WaterType, WaterType.SEA),
                    polygon=_rect(x0, y0, x1, y1),
                )
            )

    # POIs — district centroid if hinted, else world centroid + deterministic offset.
    pois: list[POI] = []
    for pp in plan.pois:
        anchor = district_centroids.get(pp.district_hint or "")
        if anchor is None:
            anchor = Point2D(x=width / 2.0, y=depth / 2.0)
        # Deterministic offset based on id hash, kept small so it stays inside.
        hx = (hash(("poi", pp.id)) % 21 - 10) * (width * 0.005)
        hy = (hash(("poi", pp.id, "y")) % 21 - 10) * (depth * 0.005)
        pos = Point2D(
            x=_clamp(anchor.x + hx, 0.0, width),
            y=_clamp(anchor.y + hy, 0.0, depth),
        )
        pois.append(
            POI(
                id=pp.id,
                name=pp.name,
                poi_type=pp.poi_type or "landmark",
                position=pos,
                tags=[pp.role] if pp.role else [],
            )
        )

    # Scene slots — at district centroid when known, else world centroid.
    known_district_ids = {d.id for d in districts}
    scene_slots: list[SceneSlot] = []
    for i, sp in enumerate(plan.scene_slots):
        district_id = sp.district_id if sp.district_id in known_district_ids else None
        if district_id and district_id in district_centroids:
            anchor = district_centroids[district_id]
        else:
            anchor = Point2D(x=width / 2.0, y=depth / 2.0)
        # Small deterministic offset per slot.
        ox = (i % 3 - 1) * (width * 0.02)
        oy = (i // 3 - 1) * (depth * 0.02)
        pos = Point2D(
            x=_clamp(anchor.x + ox, 0.0, width),
            y=_clamp(anchor.y + oy, 0.0, depth),
        )
        allowed_types = [
            _coerce_enum(t, SceneType, SceneType.EXTERIOR_LOCATION) for t in sp.allowed_scene_types
        ] or [SceneType.EXTERIOR_LOCATION]
        scene_slots.append(
            SceneSlot(
                id=sp.id,
                name=sp.name,
                district_id=district_id,
                position=pos,
                size=Size2D(
                    width_m=max(5.0, float(sp.width_m)), depth_m=max(5.0, float(sp.depth_m))
                ),
                allowed_scene_types=allowed_types,
            )
        )

    if not scene_slots:
        # Validator requires ≥ 1 scene_slot; synthesise a default one in district 0.
        anchor = districts[0]
        center = _polygon_centroid(anchor.polygon)
        scene_slots.append(
            SceneSlot(
                id="slot_default",
                name="Default Slot",
                district_id=anchor.id,
                position=center,
                size=Size2D(width_m=60.0, depth_m=40.0),
                allowed_scene_types=[SceneType.EXTERIOR_LOCATION],
            )
        )

    return WorldIR(
        world_id=plan.world_id,
        name=plan.name,
        description=None,
        scale=Size2D(width_m=width, depth_m=depth),
        theme=plan.theme or "neutral",
        tags=list(plan.tags),
        districts=districts,
        roads=roads,
        water_bodies=water_bodies,
        pois=pois,
        scene_slots=scene_slots,
        constraints=[],
    )


def _polygon_centroid(poly: Polygon2D) -> Point2D:
    n = len(poly.points)
    sx = sum(p.x for p in poly.points) / n
    sy = sum(p.y for p in poly.points) / n
    return Point2D(x=sx, y=sy)


# ============================================================
# ScenePlan → SceneIR
# ============================================================


def scene_plan_to_scene_ir(plan: ScenePlan) -> SceneIR:
    width = plan.bounds.width_m
    depth = plan.bounds.depth_m
    height = plan.bounds.height_m
    scene_type = _coerce_enum(plan.scene_type, SceneType, SceneType.EXTERIOR_LOCATION)
    preset = _coerce_enum(plan.preset, ScenePreset, ScenePreset.CUSTOM)

    # ---- Zones ---------------------------------------------------------
    zone_centroids: dict[str, Point2D] = {}
    zones: list[SceneZone] = []
    zone_plans = list(plan.zones)
    margin_x = max(0.5, width * 0.02)
    margin_y = max(0.5, depth * 0.02)
    if zone_plans:
        n = len(zone_plans)
        cols = max(1, math.ceil(math.sqrt(n)))
        rows = max(1, math.ceil(n / cols))
        cell_w = (width - 2 * margin_x) / cols
        cell_d = (depth - 2 * margin_y) / rows
        for i, zp in enumerate(zone_plans):
            col = i % cols
            row = i // cols
            gap_x = cell_w * 0.08
            gap_y = cell_d * 0.08
            x0 = margin_x + col * cell_w + gap_x
            y0 = margin_y + row * cell_d + gap_y
            x1 = margin_x + (col + 1) * cell_w - gap_x
            y1 = margin_y + (row + 1) * cell_d - gap_y
            x0 = _clamp(x0, 0.0, width)
            y0 = _clamp(y0, 0.0, depth)
            x1 = _clamp(x1, x0 + 0.5, width)
            y1 = _clamp(y1, y0 + 0.5, depth)
            polygon = _rect(x0, y0, x1, y1)
            zone_centroids[zp.id] = Point2D(x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0)
            default_zone = ZoneType.ROOM if scene_type is SceneType.INTERIOR else ZoneType.PATH
            zones.append(
                SceneZone(
                    id=zp.id,
                    name=zp.name,
                    zone_type=_coerce_enum(zp.zone_type, ZoneType, default_zone),
                    polygon=polygon,
                    tags=list(zp.tags),
                )
            )
    else:
        # Ensure ≥ 1 zone. Use full-bounds zone with a type appropriate to scene_type.
        polygon = _rect(margin_x, margin_y, width - margin_x, depth - margin_y)
        default_zone = ZoneType.ROOM if scene_type is SceneType.INTERIOR else ZoneType.PATH
        zones.append(
            SceneZone(
                id="z_default",
                name="Default Zone",
                zone_type=default_zone,
                polygon=polygon,
            )
        )
        zone_centroids["z_default"] = Point2D(x=width / 2.0, y=depth / 2.0)

    # Interior scenes require at least one room/service_area/storage/private_area.
    if scene_type is SceneType.INTERIOR:
        interior_set = {
            ZoneType.ROOM,
            ZoneType.SERVICE_AREA,
            ZoneType.STORAGE,
            ZoneType.PRIVATE_AREA,
        }
        if not any(z.zone_type in interior_set for z in zones):
            # Promote the first zone to ROOM to satisfy validator.
            z0 = zones[0]
            zones[0] = SceneZone(
                id=z0.id,
                name=z0.name,
                zone_type=ZoneType.ROOM,
                polygon=z0.polygon,
                height_m=z0.height_m,
                tags=z0.tags,
                gameplay_tags=z0.gameplay_tags,
            )

    # ---- Entrances -----------------------------------------------------
    entrance_positions: dict[str, Point2D] = {}
    entrances: list[Entrance] = []
    entrance_plans = list(plan.entrances)
    edge_order = ["west", "east", "north", "south"]
    for i, ep in enumerate(entrance_plans):
        side = (ep.side or edge_order[i % 4]).lower()
        if side == "west":
            pos = Point2D(x=margin_x, y=depth * ((i + 1) / (len(entrance_plans) + 1)))
        elif side == "east":
            pos = Point2D(x=width - margin_x, y=depth * ((i + 1) / (len(entrance_plans) + 1)))
        elif side == "south":
            pos = Point2D(x=width * ((i + 1) / (len(entrance_plans) + 1)), y=margin_y)
        else:  # north (default)
            pos = Point2D(x=width * ((i + 1) / (len(entrance_plans) + 1)), y=depth - margin_y)
        pos = Point2D(x=_clamp(pos.x, 0.0, width), y=_clamp(pos.y, 0.0, depth))
        entrance_positions[ep.id] = pos
        entrances.append(
            Entrance(
                id=ep.id,
                name=ep.name,
                position=pos,
                entrance_type=_coerce_enum(ep.entrance_type, EntranceType, EntranceType.MAIN),
                connects_to=ep.connects_to,
            )
        )

    if not entrances:
        # Validator requires ≥ 1 entrance.
        pos = Point2D(x=margin_x, y=depth / 2.0)
        entrance_positions["ent_default"] = pos
        entrances.append(
            Entrance(
                id="ent_default",
                name="Main Entrance",
                position=pos,
                entrance_type=EntranceType.MAIN,
            )
        )

    # ---- Paths ---------------------------------------------------------
    paths: list[ScenePath] = []
    for pp in plan.paths:
        points: list[Point2D] = []
        for ref in pp.connects:
            p = zone_centroids.get(ref) or entrance_positions.get(ref)
            if p is not None:
                points.append(p)
        if len(points) < 2:
            # Fall back to a straight line west→east through the middle.
            points = [
                Point2D(x=margin_x, y=depth / 2.0),
                Point2D(x=width - margin_x, y=depth / 2.0),
            ]
        # Clip every path point inside bounds.
        clipped = [Point2D(x=_clamp(pt.x, 0.0, width), y=_clamp(pt.y, 0.0, depth)) for pt in points]
        paths.append(
            ScenePath(
                id=pp.id,
                name=pp.name,
                path_type=_coerce_enum(pp.path_type, ScenePathType, ScenePathType.MAIN_ROUTE),
                points=clipped,
                width_m=max(0.5, float(pp.width_m)),
            )
        )

    # Exterior scenes need either ≥ 1 ScenePath OR an exterior/combat zone.
    if scene_type is SceneType.EXTERIOR_LOCATION:
        exterior_set = {
            ZoneType.EXTERIOR_YARD,
            ZoneType.COMBAT_SPACE,
            ZoneType.PUBLIC_AREA,
            ZoneType.PATH,
        }
        if not paths and not any(z.zone_type in exterior_set for z in zones):
            paths.append(
                ScenePath(
                    id="path_default_route",
                    name="Default Route",
                    path_type=ScenePathType.MAIN_ROUTE,
                    points=[
                        Point2D(x=margin_x, y=depth / 2.0),
                        Point2D(x=width - margin_x, y=depth / 2.0),
                    ],
                    width_m=3.0,
                )
            )

    # ---- Objects -------------------------------------------------------
    objects: list[SceneObject] = []
    obj_plans = list(plan.objects)
    if obj_plans:
        cols = max(1, math.ceil(math.sqrt(len(obj_plans))))
        rows = max(1, math.ceil(len(obj_plans) / cols))
        spacing_x = (width - 2 * margin_x) / max(cols + 1, 2)
        spacing_y = (depth - 2 * margin_y) / max(rows + 1, 2)
        for i, op in enumerate(obj_plans):
            col = i % cols
            row = i // cols
            ow = max(0.2, float(op.width_m))
            od = max(0.2, float(op.depth_m))
            oh = max(0.2, float(op.height_m))
            half_w = ow / 2.0
            half_d = od / 2.0
            cx = margin_x + (col + 1) * spacing_x
            cy = margin_y + (row + 1) * spacing_y
            cx = _clamp(cx, half_w, width - half_w)
            cy = _clamp(cy, half_d, depth - half_d)
            objects.append(
                SceneObject(
                    id=op.id,
                    name=op.name,
                    object_type=_coerce_enum(op.object_type, SceneObjectType, SceneObjectType.PROP),
                    transform=Transform3D(position=Point3D(x=cx, y=cy, z=0.0)),
                    size=Size3D(width_m=ow, depth_m=od, height_m=oh),
                )
            )

    # ---- Markers -------------------------------------------------------
    markers: list[GameplayMarker] = []
    marker_plans = list(plan.gameplay_markers)
    if marker_plans:
        cols = max(1, math.ceil(math.sqrt(len(marker_plans))))
        rows = max(1, math.ceil(len(marker_plans) / cols))
        spacing_x = (width - 2 * margin_x) / max(cols + 1, 2)
        spacing_y = (depth - 2 * margin_y) / max(rows + 1, 2)
        for i, mp in enumerate(marker_plans):
            col = i % cols
            row = i // cols
            cx = margin_x + (col + 1) * spacing_x + ((i % 5) - 2) * 0.4
            cy = margin_y + (row + 1) * spacing_y + ((i % 7) - 3) * 0.3
            cx = _clamp(cx, margin_x, width - margin_x)
            cy = _clamp(cy, margin_y, depth - margin_y)
            markers.append(
                GameplayMarker(
                    id=mp.id,
                    marker_type=_coerce_enum(mp.marker_type, MarkerType, MarkerType.COVER),
                    position=Point2D(x=cx, y=cy),
                    radius_m=mp.radius_m,
                )
            )

    # ---- Constraints ---------------------------------------------------
    constraints: list[Constraint] = []
    for cp in plan.constraints:
        ct = _coerce_enum(cp.constraint_type, ConstraintType, ConstraintType.CUSTOM)
        sev = _coerce_enum(cp.severity, Severity, Severity.ERROR)
        constraints.append(
            Constraint(
                id=cp.id,
                constraint_type=ct,
                target_id=cp.target_id,
                params=dict(cp.params),
                severity=sev,
            )
        )

    return SceneIR(
        scene_id=plan.scene_id,
        name=plan.name,
        scene_type=scene_type,
        preset=preset,
        standalone=True,
        bounds=SceneBounds(width_m=width, depth_m=depth, height_m=height),
        theme=plan.theme or "neutral",
        tags=list(plan.tags),
        zones=zones,
        entrances=entrances,
        paths=paths,
        objects=objects,
        gameplay_markers=markers,
        constraints=constraints,
    )
