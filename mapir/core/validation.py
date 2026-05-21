"""Semantic validation and a small constraints engine for MapIR.

Structural validation is handled by pydantic when the model is built; this
module performs ID-uniqueness, bounds, role, and constraint checks.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .enums import (
    ConstraintType,
    MarkerType,
    ScenePathType,
    SceneType,
    Severity,
    ZoneType,
)
from .geometry import (
    bbox_overlap,
    object_footprint_bbox,
    point_in_scene,
    point_in_world,
    polygon_bbox,
    polygon_in_bounds,
)
from .models import Constraint, SceneIR, WorldIR

INTERIOR_ZONE_TYPES: frozenset[ZoneType] = frozenset(
    {ZoneType.ROOM, ZoneType.SERVICE_AREA, ZoneType.STORAGE, ZoneType.PRIVATE_AREA}
)

EXTERIOR_ZONE_TYPES: frozenset[ZoneType] = frozenset(
    {ZoneType.EXTERIOR_YARD, ZoneType.COMBAT_SPACE, ZoneType.PUBLIC_AREA, ZoneType.PATH}
)


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    path: str = ""

    def format(self) -> str:
        loc = f" [{self.path}]" if self.path else ""
        return f"{self.severity.value.upper()} {self.code}: {self.message}{loc}"


@dataclass
class ValidationReport:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    infos: list[ValidationIssue] = field(default_factory=list)

    def add(self, issue: ValidationIssue) -> None:
        if issue.severity is Severity.ERROR:
            self.errors.append(issue)
        elif issue.severity is Severity.WARNING:
            self.warnings.append(issue)
        else:
            self.infos.append(issue)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def all(self) -> list[ValidationIssue]:
        return [*self.errors, *self.warnings, *self.infos]


# ============================================================
# Dispatcher
# ============================================================

def validate(ir: WorldIR | SceneIR) -> ValidationReport:
    report = ValidationReport()
    if isinstance(ir, WorldIR):
        validate_world(ir, report)
    else:
        validate_scene(ir, report)
    return report


# ============================================================
# World validation
# ============================================================

def validate_world(world: WorldIR, report: ValidationReport) -> None:
    _check_unique_ids(
        report,
        groups={
            "districts": [d.id for d in world.districts],
            "roads": [r.id for r in world.roads],
            "water_bodies": [w.id for w in world.water_bodies],
            "pois": [p.id for p in world.pois],
            "scene_slots": [s.id for s in world.scene_slots],
            "constraints": [c.id for c in world.constraints],
        },
    )

    if not world.districts:
        report.add(ValidationIssue("world_no_districts", "WorldIR must have at least one district"))
    if not world.scene_slots:
        report.add(ValidationIssue("world_no_scene_slots", "WorldIR must have at least one scene_slot"))

    # Bounds checks (a generous slack so coastal/island geometry can hang slightly outside)
    slack = max(world.scale.width_m, world.scale.depth_m) * 0.05
    for i, d in enumerate(world.districts):
        if not polygon_in_bounds(d.polygon, world.scale.width_m, world.scale.depth_m, slack):
            report.add(ValidationIssue(
                "district_out_of_bounds",
                f"district {d.id!r} polygon extends beyond world bounds",
                Severity.WARNING,
                f"districts[{i}]",
            ))
    for i, r in enumerate(world.roads):
        for j, p in enumerate(r.points):
            if not point_in_world(p, world.scale, slack):
                report.add(ValidationIssue(
                    "road_point_out_of_bounds",
                    f"road {r.id!r} point {j} is outside world bounds",
                    Severity.WARNING,
                    f"roads[{i}].points[{j}]",
                ))
                break
    for i, p in enumerate(world.pois):
        if not point_in_world(p.position, world.scale, slack):
            report.add(ValidationIssue(
                "poi_out_of_bounds",
                f"poi {p.id!r} is outside world bounds",
                Severity.WARNING,
                f"pois[{i}]",
            ))
    for i, s in enumerate(world.scene_slots):
        if not point_in_world(s.position, world.scale, slack):
            report.add(ValidationIssue(
                "scene_slot_out_of_bounds",
                f"scene_slot {s.id!r} is outside world bounds",
                Severity.WARNING,
                f"scene_slots[{i}]",
            ))

    # Scene slot district references
    district_ids = {d.id for d in world.districts}
    for i, s in enumerate(world.scene_slots):
        if s.district_id is not None and s.district_id not in district_ids:
            report.add(ValidationIssue(
                "scene_slot_unknown_district",
                f"scene_slot {s.id!r} references unknown district_id={s.district_id!r}",
                path=f"scene_slots[{i}].district_id",
            ))

    # Constraints
    for i, c in enumerate(world.constraints):
        _evaluate_constraint(world, c, report, path=f"constraints[{i}]")


# ============================================================
# Scene validation
# ============================================================

def validate_scene(scene: SceneIR, report: ValidationReport) -> None:
    _check_unique_ids(
        report,
        groups={
            "zones": [z.id for z in scene.zones],
            "entrances": [e.id for e in scene.entrances],
            "paths": [p.id for p in scene.paths],
            "objects": [o.id for o in scene.objects],
            "gameplay_markers": [m.id for m in scene.gameplay_markers],
            "constraints": [c.id for c in scene.constraints],
        },
    )

    if not scene.entrances:
        report.add(ValidationIssue("scene_no_entrances", "SceneIR must have at least one entrance"))
    if not scene.zones:
        report.add(ValidationIssue("scene_no_zones", "SceneIR must have at least one zone"))

    if scene.scene_type is SceneType.INTERIOR:
        has_interior_zone = any(z.zone_type in INTERIOR_ZONE_TYPES for z in scene.zones)
        if not has_interior_zone:
            report.add(ValidationIssue(
                "interior_missing_room",
                "Interior scenes need at least one room/service_area/storage/private_area zone",
            ))
    else:
        has_path = bool(scene.paths)
        has_exterior_zone = any(z.zone_type in EXTERIOR_ZONE_TYPES for z in scene.zones)
        if not (has_path or has_exterior_zone):
            report.add(ValidationIssue(
                "exterior_missing_paths_or_zones",
                "Exterior scenes need at least one ScenePath or an exterior/combat zone",
            ))

    if not scene.standalone and not scene.parent_world_id:
        report.add(ValidationIssue(
            "embedded_scene_missing_parent",
            "Non-standalone scenes should reference a parent_world_id",
            Severity.WARNING,
        ))

    # Bounds checks (small slack so polygons touching the boundary are accepted)
    w, d = scene.bounds.width_m, scene.bounds.depth_m
    slack = max(w, d) * 0.05
    for i, z in enumerate(scene.zones):
        if not polygon_in_bounds(z.polygon, w, d, slack):
            report.add(ValidationIssue(
                "zone_out_of_bounds",
                f"zone {z.id!r} polygon extends beyond scene bounds",
                Severity.WARNING,
                f"zones[{i}]",
            ))
    for i, e in enumerate(scene.entrances):
        if not point_in_scene(e.position, w, d, slack):
            report.add(ValidationIssue(
                "entrance_out_of_bounds",
                f"entrance {e.id!r} is outside scene bounds",
                Severity.WARNING,
                f"entrances[{i}]",
            ))
    for i, p in enumerate(scene.paths):
        for j, pt in enumerate(p.points):
            if not point_in_scene(pt, w, d, slack):
                report.add(ValidationIssue(
                    "path_point_out_of_bounds",
                    f"path {p.id!r} point {j} is outside scene bounds",
                    Severity.WARNING,
                    f"paths[{i}].points[{j}]",
                ))
                break
    for i, m in enumerate(scene.gameplay_markers):
        if not point_in_scene(m.position, w, d, slack):
            report.add(ValidationIssue(
                "marker_out_of_bounds",
                f"marker {m.id!r} is outside scene bounds",
                Severity.WARNING,
                f"gameplay_markers[{i}]",
            ))

    # Constraints
    for i, c in enumerate(scene.constraints):
        _evaluate_constraint(scene, c, report, path=f"constraints[{i}]")


# ============================================================
# Helpers
# ============================================================

def _check_unique_ids(report: ValidationReport, groups: dict[str, list[str]]) -> None:
    for group, ids in groups.items():
        counts = Counter(ids)
        for ident, n in counts.items():
            if n > 1:
                report.add(ValidationIssue(
                    "duplicate_id",
                    f"id {ident!r} appears {n} times within {group}",
                    path=group,
                ))


def _evaluate_constraint(
    ir: WorldIR | SceneIR,
    c: Constraint,
    report: ValidationReport,
    path: str,
) -> None:
    handler = _CONSTRAINT_HANDLERS.get(c.constraint_type)
    if handler is None:
        report.add(ValidationIssue(
            "unsupported_constraint",
            f"constraint {c.id!r} of type {c.constraint_type.value!r} is not yet supported",
            Severity.WARNING,
            path,
        ))
        return
    handler(ir, c, report, path)


# ---- constraint handlers --------------------------------------------------

def _h_min_entrances(ir, c: Constraint, report: ValidationReport, path: str) -> None:
    if not isinstance(ir, SceneIR):
        report.add(ValidationIssue(
            "constraint_wrong_ir",
            f"{c.constraint_type.value} only applies to SceneIR",
            c.severity, path,
        ))
        return
    minimum = int(c.params.get("min", 1))
    n = len(ir.entrances)
    if n < minimum:
        report.add(ValidationIssue(
            "min_entrances_unmet",
            f"need at least {minimum} entrances, found {n}",
            c.severity, path,
        ))


def _h_min_escape_routes(ir, c: Constraint, report: ValidationReport, path: str) -> None:
    if not isinstance(ir, SceneIR):
        report.add(ValidationIssue(
            "constraint_wrong_ir",
            f"{c.constraint_type.value} only applies to SceneIR",
            c.severity, path,
        ))
        return
    minimum = int(c.params.get("min", 1))
    n = sum(1 for p in ir.paths if p.path_type is ScenePathType.ESCAPE_ROUTE)
    if n < minimum:
        report.add(ValidationIssue(
            "min_escape_routes_unmet",
            f"need at least {minimum} escape_route paths, found {n}",
            c.severity, path,
        ))


def _h_min_cover_markers(ir, c: Constraint, report: ValidationReport, path: str) -> None:
    if not isinstance(ir, SceneIR):
        report.add(ValidationIssue(
            "constraint_wrong_ir",
            f"{c.constraint_type.value} only applies to SceneIR",
            c.severity, path,
        ))
        return
    minimum = int(c.params.get("min", 1))
    n = sum(1 for m in ir.gameplay_markers if m.marker_type is MarkerType.COVER)
    if n < minimum:
        report.add(ValidationIssue(
            "min_cover_markers_unmet",
            f"need at least {minimum} cover markers, found {n}",
            c.severity, path,
        ))


def _h_must_have_scene_slot(ir, c: Constraint, report: ValidationReport, path: str) -> None:
    if not isinstance(ir, WorldIR):
        report.add(ValidationIssue(
            "constraint_wrong_ir",
            f"{c.constraint_type.value} only applies to WorldIR",
            c.severity, path,
        ))
        return
    minimum = int(c.params.get("min", 1))
    if len(ir.scene_slots) < minimum:
        report.add(ValidationIssue(
            "must_have_scene_slot_unmet",
            f"need at least {minimum} scene_slots, found {len(ir.scene_slots)}",
            c.severity, path,
        ))


def _h_inside_bounds(ir, c: Constraint, report: ValidationReport, path: str) -> None:
    if isinstance(ir, SceneIR):
        w, d = ir.bounds.width_m, ir.bounds.depth_m
        ok = True
        for obj in ir.objects:
            bb = object_footprint_bbox(obj.transform, obj.size)
            if not (0 <= bb.min_x and 0 <= bb.min_y and bb.max_x <= w and bb.max_y <= d):
                ok = False
                break
        if not ok:
            report.add(ValidationIssue(
                "must_be_inside_bounds_unmet",
                "at least one scene object footprint extends outside scene bounds",
                c.severity, path,
            ))
    elif isinstance(ir, WorldIR):
        w, d = ir.scale.width_m, ir.scale.depth_m
        for district in ir.districts:
            bb = polygon_bbox(district.polygon)
            if not (0 <= bb.min_x and 0 <= bb.min_y and bb.max_x <= w and bb.max_y <= d):
                report.add(ValidationIssue(
                    "must_be_inside_bounds_unmet",
                    f"district {district.id!r} extends outside world bounds",
                    c.severity, path,
                ))
                return


def _h_must_not_overlap(ir, c: Constraint, report: ValidationReport, path: str) -> None:
    if not isinstance(ir, SceneIR):
        report.add(ValidationIssue(
            "constraint_wrong_ir",
            f"{c.constraint_type.value} only applies to SceneIR",
            c.severity, path,
        ))
        return
    only_locked = bool(c.params.get("only_locked", False))
    objects = [o for o in ir.objects if (not only_locked) or o.locked]
    bboxes = [(o.id, object_footprint_bbox(o.transform, o.size)) for o in objects]
    overlaps: list[tuple[str, str]] = []
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            if bbox_overlap(bboxes[i][1], bboxes[j][1]):
                overlaps.append((bboxes[i][0], bboxes[j][0]))
    if overlaps:
        sample = ", ".join(f"{a}<>{b}" for a, b in overlaps[:5])
        more = f" (+{len(overlaps) - 5} more)" if len(overlaps) > 5 else ""
        report.add(ValidationIssue(
            "must_not_overlap_unmet",
            f"{len(overlaps)} bbox overlap(s): {sample}{more}",
            c.severity, path,
        ))


_CONSTRAINT_HANDLERS = {
    ConstraintType.MUST_HAVE_MIN_ENTRANCES: _h_min_entrances,
    ConstraintType.MUST_HAVE_MIN_ESCAPE_ROUTES: _h_min_escape_routes,
    ConstraintType.MUST_HAVE_MIN_COVER_MARKERS: _h_min_cover_markers,
    ConstraintType.MUST_HAVE_SCENE_SLOT: _h_must_have_scene_slot,
    ConstraintType.MUST_BE_INSIDE_BOUNDS: _h_inside_bounds,
    ConstraintType.MUST_NOT_OVERLAP: _h_must_not_overlap,
}
