"""Gameplay metrics — generator constraints and validation rules.

These are not a physics simulation. They are knobs that:

* the generators read to size roads, parcels, buildings, cover intervals,
* the design validators read to flag profile-specific problems
  (e.g. driving roads too narrow, shooter zones with no cover).

Templates ship sensible defaults; districts can override via the District
Inspector.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GameplayProfile(str, Enum):
    DRIVING = "driving"
    STEALTH = "stealth"
    SHOOTER = "shooter"
    PARKOUR = "parkour"
    EXPLORATION = "exploration"


class RoadPattern(str, Enum):
    GRID = "grid"
    ORGANIC = "organic"
    RADIAL = "radial"
    COASTAL = "coastal"
    RURAL = "rural"
    MEDIEVAL = "medieval"
    INDUSTRIAL = "industrial"
    DENSE_URBAN = "dense_urban"


class BuildingStyle(str, Enum):
    MODERN_CITY = "modern_city"
    MEDIEVAL = "medieval"
    RURAL = "rural"
    CYBERPUNK = "cyberpunk"
    INDUSTRIAL = "industrial"
    GENERIC_INTERIOR = "generic_interior"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoadMetrics(_Strict):
    arterial_width_m: float = Field(default=14.0, gt=0)
    collector_width_m: float = Field(default=9.0, gt=0)
    local_width_m: float = Field(default=6.0, gt=0)
    alley_width_m: float = Field(default=3.0, gt=0)
    trail_width_m: float = Field(default=1.5, gt=0)
    intersection_spacing_m: float = Field(default=80.0, gt=0)
    shortcut_density: float = Field(default=0.2, ge=0.0, le=1.0)
    dead_end_ratio_max: float = Field(default=0.15, ge=0.0, le=1.0)


class BuildingMetrics(_Strict):
    parcel_min_width_m: float = Field(default=8.0, gt=0)
    parcel_max_width_m: float = Field(default=24.0, gt=0)
    parcel_depth_m: float = Field(default=16.0, gt=0)
    building_setback_m: float = Field(default=1.5, ge=0)
    building_height_min_m: float = Field(default=4.0, gt=0)
    building_height_max_m: float = Field(default=24.0, gt=0)
    building_density: float = Field(default=0.6, ge=0.0, le=1.0)


class ShooterMetrics(_Strict):
    cover_interval_m: float = Field(default=6.0, gt=0)
    cover_width_min_m: float = Field(default=1.0, gt=0)
    cover_height_min_m: float = Field(default=1.0, gt=0)
    max_open_sightline_m: float = Field(default=40.0, gt=0)
    combat_arena_size_m: float = Field(default=30.0, gt=0)


class StealthMetrics(_Strict):
    alternate_route_count_min: int = Field(default=2, ge=0)
    concealment_density: float = Field(default=0.3, ge=0.0, le=1.0)
    restricted_area_count: int = Field(default=1, ge=0)
    patrol_route_hint_count: int = Field(default=1, ge=0)


class ParkourMetrics(_Strict):
    climbable_edge_interval_m: float = Field(default=8.0, gt=0)
    rooftop_connection_density: float = Field(default=0.25, ge=0.0, le=1.0)
    verticality_score: float = Field(default=0.3, ge=0.0, le=1.0)


class ExplorationMetrics(_Strict):
    landmark_count_min: int = Field(default=2, ge=0)
    vista_count_min: int = Field(default=1, ge=0)
    secret_path_count_min: int = Field(default=0, ge=0)
    breadcrumb_density: float = Field(default=0.2, ge=0.0, le=1.0)


class GameplayMetrics(_Strict):
    """Bundle of per-category metrics for a template or district."""

    gameplay_profiles: list[GameplayProfile] = Field(default_factory=list)
    road: RoadMetrics = Field(default_factory=RoadMetrics)
    building: BuildingMetrics = Field(default_factory=BuildingMetrics)
    shooter: ShooterMetrics = Field(default_factory=ShooterMetrics)
    stealth: StealthMetrics = Field(default_factory=StealthMetrics)
    parkour: ParkourMetrics = Field(default_factory=ParkourMetrics)
    exploration: ExplorationMetrics = Field(default_factory=ExplorationMetrics)


def default_metrics_for_profiles(
    profiles: list[GameplayProfile],
) -> GameplayMetrics:
    """Return a metrics bundle tuned to the given profile mix.

    The tuning is intentionally light: enough to make per-profile validators
    fire on obvious violations without being so opinionated that templates
    can't override.
    """

    metrics = GameplayMetrics(gameplay_profiles=list(profiles))

    if GameplayProfile.DRIVING in profiles:
        metrics.road.arterial_width_m = max(metrics.road.arterial_width_m, 16.0)
        metrics.road.collector_width_m = max(metrics.road.collector_width_m, 10.0)
        metrics.road.local_width_m = max(metrics.road.local_width_m, 7.0)

    if GameplayProfile.SHOOTER in profiles:
        metrics.shooter.cover_interval_m = min(metrics.shooter.cover_interval_m, 6.0)
        metrics.shooter.max_open_sightline_m = min(
            metrics.shooter.max_open_sightline_m, 40.0
        )

    if GameplayProfile.STEALTH in profiles:
        metrics.stealth.alternate_route_count_min = max(
            metrics.stealth.alternate_route_count_min, 2
        )
        metrics.stealth.concealment_density = max(
            metrics.stealth.concealment_density, 0.35
        )

    if GameplayProfile.PARKOUR in profiles:
        metrics.parkour.verticality_score = max(metrics.parkour.verticality_score, 0.5)
        metrics.parkour.rooftop_connection_density = max(
            metrics.parkour.rooftop_connection_density, 0.4
        )

    if GameplayProfile.EXPLORATION in profiles:
        metrics.exploration.landmark_count_min = max(
            metrics.exploration.landmark_count_min, 3
        )
        metrics.exploration.vista_count_min = max(metrics.exploration.vista_count_min, 2)

    return metrics
