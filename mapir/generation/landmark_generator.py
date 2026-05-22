"""Landmark generator.

For each district whose role / tags suggest an "anchor" we emit one
``Landmark``. The pool is keyed by genre / building style; the heuristic is
explicit and deterministic so two runs over the same sketch produce the same
landmarks.
"""

from __future__ import annotations

from ..core.models import Point2D, Polygon2D
from .gameplay_metrics import BuildingStyle, GameplayMetrics
from .layout import Landmark, LandmarkType


_STYLE_TO_LANDMARK: dict[BuildingStyle, list[LandmarkType]] = {
    BuildingStyle.MODERN_CITY: [
        LandmarkType.SKYSCRAPER,
        LandmarkType.RADIO_TOWER,
        LandmarkType.MONUMENT,
    ],
    BuildingStyle.MEDIEVAL: [
        LandmarkType.CASTLE,
        LandmarkType.TOWER,
        LandmarkType.RUINS,
        LandmarkType.GIANT_TREE,
    ],
    BuildingStyle.RURAL: [
        LandmarkType.RADIO_TOWER,
        LandmarkType.VISTA_POINT,
        LandmarkType.MOUNTAIN,
    ],
    BuildingStyle.CYBERPUNK: [
        LandmarkType.NEON_SIGN,
        LandmarkType.SKYSCRAPER,
        LandmarkType.RADIO_TOWER,
    ],
    BuildingStyle.INDUSTRIAL: [
        LandmarkType.FACTORY_STACK,
        LandmarkType.RADIO_TOWER,
        LandmarkType.AIRPORT_TOWER,
    ],
    BuildingStyle.GENERIC_INTERIOR: [
        LandmarkType.MONUMENT,
    ],
}


_LANDMARK_TAGS_MARKERS = ("landmark", "objective", "vista", "focal_point", "secret")


def _centroid(polygon: Polygon2D) -> Point2D:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return Point2D(x=sum(xs) / len(xs), y=sum(ys) / len(ys))


def _district_should_anchor(sketch_district) -> bool:
    tags = set(sketch_district.tags or [])
    if tags & set(_LANDMARK_TAGS_MARKERS):
        return True
    if sketch_district.role.lower() in (
        "focal_point",
        "landmark",
        "vista",
        "objective",
        "spine",
        "hub",
    ):
        return True
    return False


def generate_landmarks(
    sketch_districts: list,
    metrics: GameplayMetrics,
) -> list[Landmark]:
    h_max = metrics.building.building_height_max_m
    out: list[Landmark] = []
    for i, d in enumerate(sketch_districts):
        if not _district_should_anchor(d):
            continue
        choices = _STYLE_TO_LANDMARK.get(d.building_style, [LandmarkType.MONUMENT])
        lt = choices[i % len(choices)]
        out.append(
            Landmark(
                id=f"lm_{d.id}",
                name=f"{d.name} Landmark",
                landmark_type=lt,
                position=_centroid(d.polygon),
                height_m=max(8.0, h_max),
                district_id=d.id,
                tags=["from_template"],
                guidance_payoff=(
                    "Vista of the district; orientation anchor visible from "
                    "neighbouring zones."
                ),
            )
        )
    # Guarantee at least one landmark if the template wants exploration.
    if not out and sketch_districts:
        d0 = sketch_districts[0]
        out.append(
            Landmark(
                id=f"lm_default_{d0.id}",
                name=f"{d0.name} Anchor",
                landmark_type=LandmarkType.MONUMENT,
                position=_centroid(d0.polygon),
                height_m=max(8.0, h_max),
                district_id=d0.id,
                guidance_payoff="Default orientation anchor.",
            )
        )
    return out
