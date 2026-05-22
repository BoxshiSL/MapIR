"""Design-aware validators — supplement the structural rules with v0.5
gameplay / readability / district-identity / connectivity / geometry checks.

These run *in addition to* the structural validators in
``mapir.core.validation``. They consume:

* the converted ``WorldIR`` / ``SceneIR`` (geometry source of truth),
* the source ``GeneratedLayout`` (parcels, buildings, landmarks, scene
  slots, guidance cues),
* the ``GameplayMetrics`` bundle (so the validator knows e.g. how wide
  arterials are required to be for a driving profile).

Each check produces ``DesignWarning`` items with a category and severity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..core.enums import RoadType
from ..core.models import SceneIR, WorldIR
from ..generation.gameplay_metrics import GameplayMetrics, GameplayProfile
from ..generation.layout import GeneratedLayout
from .design_rules import RuleSeverity


class DesignCategory(str, Enum):
    CONNECTIVITY = "connectivity"
    GAMEPLAY_METRICS = "gameplay_metrics"
    READABILITY = "readability"
    DISTRICT_IDENTITY = "district_identity"
    GEOMETRY = "geometry"


@dataclass
class DesignWarning:
    code: str
    category: DesignCategory
    severity: RuleSeverity
    message: str
    target_id: str | None = None
    rule_id: str | None = None

    def format(self) -> str:
        loc = f" [{self.target_id}]" if self.target_id else ""
        rule = f" (rule={self.rule_id})" if self.rule_id else ""
        return (
            f"{self.severity.value.upper()} {self.code}: {self.message}{loc}{rule}"
        )


@dataclass
class DesignReport:
    warnings: list[DesignWarning] = field(default_factory=list)

    def add(self, w: DesignWarning) -> None:
        self.warnings.append(w)

    def errors(self) -> list[DesignWarning]:
        return [w for w in self.warnings if w.severity is RuleSeverity.ERROR]

    def infos(self) -> list[DesignWarning]:
        return [w for w in self.warnings if w.severity is RuleSeverity.INFO]

    def warnings_only(self) -> list[DesignWarning]:
        return [w for w in self.warnings if w.severity is RuleSeverity.WARNING]

    def by_category(self) -> dict[DesignCategory, list[DesignWarning]]:
        out: dict[DesignCategory, list[DesignWarning]] = {}
        for w in self.warnings:
            out.setdefault(w.category, []).append(w)
        return out


# ============================================================
# Entry point
# ============================================================


def run_design_validators(
    ir: WorldIR | SceneIR,
    layout: GeneratedLayout | None,
    metrics: GameplayMetrics,
) -> DesignReport:
    report = DesignReport()
    if isinstance(ir, WorldIR):
        _validate_world(ir, layout, metrics, report)
    else:
        _validate_scene(ir, layout, metrics, report)
    return report


# ============================================================
# World
# ============================================================


def _validate_world(
    world: WorldIR,
    layout: GeneratedLayout | None,
    metrics: GameplayMetrics,
    report: DesignReport,
) -> None:
    if not world.districts:
        return

    # ---- connectivity --------------------------------------------------
    road_district_ids = (
        {r.district_id for r in layout.roads if r.district_id} if layout else set()
    )
    for d in world.districts:
        in_road_district = d.id in road_district_ids
        # OR a sketch road has at least one point inside the district bbox
        bbox_has_road = _district_bbox_touches_road(d, world.roads)
        if not (in_road_district or bbox_has_road):
            report.add(
                DesignWarning(
                    code="district_no_road",
                    category=DesignCategory.CONNECTIVITY,
                    severity=RuleSeverity.WARNING,
                    message=f"district {d.name!r} has no road touching its bbox",
                    target_id=d.id,
                    rule_id="navigation_district_road_connection",
                )
            )

    # ---- gameplay metrics: driving arterial widths ---------------------
    if GameplayProfile.DRIVING in metrics.gameplay_profiles:
        min_arterial = metrics.road.arterial_width_m
        for r in world.roads:
            if r.road_type is RoadType.PRIMARY and r.width_m < min_arterial - 0.1:
                report.add(
                    DesignWarning(
                        code="driving_arterial_too_narrow",
                        category=DesignCategory.GAMEPLAY_METRICS,
                        severity=RuleSeverity.WARNING,
                        message=(
                            f"arterial road {r.id!r} is {r.width_m:.1f}m wide; "
                            f"driving profile expects ≥ {min_arterial:.1f}m"
                        ),
                        target_id=r.id,
                        rule_id="gameplay_metrics_driving_widths",
                    )
                )

    # ---- landmarks per major district ----------------------------------
    landmark_districts = (
        {lm.district_id for lm in layout.landmarks if lm.district_id} if layout else set()
    )
    for d in world.districts:
        if _district_is_major(d) and d.id not in landmark_districts:
            report.add(
                DesignWarning(
                    code="major_district_no_landmark",
                    category=DesignCategory.READABILITY,
                    severity=RuleSeverity.WARNING,
                    message=(
                        f"major district {d.name!r} has no landmark — players will "
                        "struggle to orient"
                    ),
                    target_id=d.id,
                    rule_id="landmarks_one_per_district",
                )
            )

    # ---- district identity ---------------------------------------------
    for d in world.districts:
        differentiating = bool(d.tags) or bool(d.gameplay_tags) or (
            d.district_type and d.district_type != "mixed"
        )
        if not differentiating:
            report.add(
                DesignWarning(
                    code="district_no_identity",
                    category=DesignCategory.DISTRICT_IDENTITY,
                    severity=RuleSeverity.WARNING,
                    message=(
                        f"district {d.name!r} has no theme/tags/distinct type"
                    ),
                    target_id=d.id,
                    rule_id="district_identity_differentiator",
                )
            )

    # ---- geometry: buildings inside parcels (layout only) --------------
    if layout is not None:
        _validate_buildings_inside_parcels(layout, report)


def _district_bbox_touches_road(district, roads) -> bool:
    xs = [p.x for p in district.polygon.points]
    ys = [p.y for p in district.polygon.points]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    for r in roads:
        for p in r.points:
            if x0 <= p.x <= x1 and y0 <= p.y <= y1:
                return True
    return False


def _district_is_major(d) -> bool:
    """Major districts are everything except pure ambience / forest belts."""
    minor_types = {"forest", "wetland", "grove", "trail", "highway_strip"}
    return d.district_type not in minor_types


# ============================================================
# Scene
# ============================================================


def _validate_scene(
    scene: SceneIR,
    layout: GeneratedLayout | None,
    metrics: GameplayMetrics,
    report: DesignReport,
) -> None:
    # ---- shooter: cover marker count ----------------------------------
    if GameplayProfile.SHOOTER in metrics.gameplay_profiles:
        n_cover = sum(
            1 for m in scene.gameplay_markers if m.marker_type.value == "cover"
        ) + sum(1 for o in scene.objects if o.object_type.value == "cover")
        # heuristic: ≥ 1 cover per (cover_interval ** 2) m²
        area = scene.bounds.width_m * scene.bounds.depth_m
        ci = max(1.0, metrics.shooter.cover_interval_m)
        expected = max(1, int(area / (ci * ci)))
        if n_cover < expected // 4:  # generous floor (a quarter of ideal)
            report.add(
                DesignWarning(
                    code="shooter_cover_sparse",
                    category=DesignCategory.GAMEPLAY_METRICS,
                    severity=RuleSeverity.WARNING,
                    message=(
                        f"shooter profile: {n_cover} cover marker(s) for a "
                        f"{int(area)} m² area — looks sparse"
                    ),
                    rule_id="gameplay_metrics_shooter_cover",
                )
            )

    # ---- stealth: alternate routes ------------------------------------
    if GameplayProfile.STEALTH in metrics.gameplay_profiles:
        from ..core.enums import ScenePathType

        alt = sum(
            1
            for p in scene.paths
            if p.path_type
            in (ScenePathType.ALTERNATE_ROUTE, ScenePathType.STEALTH_ROUTE)
        )
        if alt < metrics.stealth.alternate_route_count_min:
            report.add(
                DesignWarning(
                    code="stealth_alternate_routes_missing",
                    category=DesignCategory.CONNECTIVITY,
                    severity=RuleSeverity.WARNING,
                    message=(
                        f"stealth profile expects ≥ "
                        f"{metrics.stealth.alternate_route_count_min} alternate/"
                        f"stealth routes; found {alt}"
                    ),
                    rule_id="navigation_multiple_routes",
                )
            )

    # ---- entrances ----------------------------------------------------
    if len(scene.entrances) < 2:
        report.add(
            DesignWarning(
                code="scene_few_entrances",
                category=DesignCategory.CONNECTIVITY,
                severity=RuleSeverity.INFO,
                message=(
                    f"scene has {len(scene.entrances)} entrance(s); two or "
                    "more usually read better"
                ),
            )
        )

    # ---- geometry -----------------------------------------------------
    if layout is not None:
        _validate_buildings_inside_parcels(layout, report)


# ============================================================
# Shared
# ============================================================


def _bbox(polygon) -> tuple[float, float, float, float]:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return min(xs), min(ys), max(xs), max(ys)


def _validate_buildings_inside_parcels(
    layout: GeneratedLayout, report: DesignReport
) -> None:
    parcels_by_id = {p.id: p for p in layout.parcels}
    for b in layout.buildings:
        parcel = parcels_by_id.get(b.parcel_id)
        if parcel is None:
            report.add(
                DesignWarning(
                    code="building_orphan",
                    category=DesignCategory.GEOMETRY,
                    severity=RuleSeverity.ERROR,
                    message=f"building {b.id!r} references unknown parcel {b.parcel_id!r}",
                    target_id=b.id,
                    rule_id="geometry_buildings_inside_parcels",
                )
            )
            continue
        bx0, by0, bx1, by1 = _bbox(b.polygon)
        px0, py0, px1, py1 = _bbox(parcel.polygon)
        tol = 0.5  # 0.5m forgiveness — set-back tolerance
        if bx0 + tol < px0 or by0 + tol < py0 or bx1 - tol > px1 or by1 - tol > py1:
            report.add(
                DesignWarning(
                    code="building_outside_parcel",
                    category=DesignCategory.GEOMETRY,
                    severity=RuleSeverity.ERROR,
                    message=(
                        f"building {b.id!r} bbox extends outside parcel "
                        f"{parcel.id!r}"
                    ),
                    target_id=b.id,
                    rule_id="geometry_buildings_inside_parcels",
                )
            )
