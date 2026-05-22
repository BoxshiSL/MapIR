"""Building footprint generator.

Each parcel produces one building footprint set back by
``GameplayMetrics.building.building_setback_m``. Height is drawn from the
metrics range and modulated by the district density. Building type is
derived from the parcel type, with gameplay tags forwarded.

For v0.5 we keep the strategy deliberately simple — production-quality
parcel/building generation needs polygon clipping and frontage logic; that
arrives in v0.6.
"""

from __future__ import annotations

import random

from ..core.models import Point2D, Polygon2D
from .gameplay_metrics import GameplayMetrics, GameplayProfile
from .layout import BuildingFootprint, BuildingType, Parcel, ParcelType


_PARCEL_TO_BUILDING: dict[ParcelType, BuildingType] = {
    ParcelType.RESIDENTIAL: BuildingType.HOUSE,
    ParcelType.COMMERCIAL: BuildingType.RETAIL,
    ParcelType.INDUSTRIAL: BuildingType.INDUSTRIAL,
    ParcelType.CIVIC: BuildingType.OFFICE,
    ParcelType.LANDMARK: BuildingType.LANDMARK,
    ParcelType.MIXED_USE: BuildingType.GENERIC,
    ParcelType.RURAL: BuildingType.HOUSE,
    ParcelType.FOREST_CLEARING: BuildingType.SHED,
}


def _bbox(polygon: Polygon2D) -> tuple[float, float, float, float]:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return min(xs), min(ys), max(xs), max(ys)


def _rect(x0: float, y0: float, x1: float, y1: float) -> Polygon2D:
    return Polygon2D(
        points=[
            Point2D(x=x0, y=y0),
            Point2D(x=x1, y=y0),
            Point2D(x=x1, y=y1),
            Point2D(x=x0, y=y1),
        ]
    )


def _district_lookup(sketch_districts) -> dict[str, object]:
    return {d.id: d for d in sketch_districts}


def generate_buildings(
    parcels: list[Parcel],
    sketch_districts: list,
    metrics: GameplayMetrics,
    *,
    seed: str = "",
) -> list[BuildingFootprint]:
    rng = random.Random(seed or "v0.5_buildings")
    setback = metrics.building.building_setback_m
    h_min = metrics.building.building_height_min_m
    h_max = metrics.building.building_height_max_m
    density = max(0.05, min(1.0, metrics.building.building_density))
    has_shooter = GameplayProfile.SHOOTER in metrics.gameplay_profiles
    has_parkour = GameplayProfile.PARKOUR in metrics.gameplay_profiles

    out: list[BuildingFootprint] = []
    by_district = _district_lookup(sketch_districts)
    for parcel in parcels:
        # density skip: drop parcels stochastically below the density
        if rng.random() > density:
            continue
        x0, y0, x1, y1 = _bbox(parcel.polygon)
        bx0 = x0 + setback
        by0 = y0 + setback
        bx1 = x1 - setback
        by1 = y1 - setback
        if bx1 - bx0 < 1.0 or by1 - by0 < 1.0:
            continue
        # Height jitter modulated by parcel type
        if parcel.parcel_type is ParcelType.LANDMARK:
            height = h_max
        elif parcel.parcel_type is ParcelType.INDUSTRIAL:
            height = max(h_min, min(h_max, h_min + (h_max - h_min) * 0.4))
        else:
            height = h_min + (h_max - h_min) * rng.random()
        # Gameplay tags
        tags: list[str] = []
        if has_shooter:
            tags.append("cover")
        if has_parkour and height >= h_min + (h_max - h_min) * 0.4:
            tags.append("climbable")
        if parcel.parcel_type is ParcelType.LANDMARK:
            tags.append("landmark")
        out.append(
            BuildingFootprint(
                id=f"b_{parcel.id}",
                parcel_id=parcel.id,
                district_id=parcel.district_id,
                polygon=_rect(bx0, by0, bx1, by1),
                height_m=round(height, 1),
                building_type=_PARCEL_TO_BUILDING.get(
                    parcel.parcel_type, BuildingType.GENERIC
                ),
                style_tags=[
                    by_district[parcel.district_id].building_style.value
                    if parcel.district_id in by_district
                    else "modern_city"
                ],
                gameplay_tags=tags,
            )
        )
    return out
