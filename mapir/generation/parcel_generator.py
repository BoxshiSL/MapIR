"""Parcel generator — subdivide a district bbox into a grid of parcels.

v0.5 strategy is intentionally naive (no shapely): we use the district's
axis-aligned bounding box, divide it by ``GameplayMetrics.building.parcel_*``,
and emit rectangular ``Parcel`` polygons. Future versions can clip to the
true polygon and align to road frontages.
"""

from __future__ import annotations

from ..core.models import Point2D, Polygon2D
from .gameplay_metrics import GameplayMetrics
from .layout import Parcel, ParcelType


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


_DISTRICT_TYPE_TO_PARCEL: dict[str, ParcelType] = {
    "downtown": ParcelType.COMMERCIAL,
    "historic": ParcelType.MIXED_USE,
    "port": ParcelType.INDUSTRIAL,
    "airport": ParcelType.INDUSTRIAL,
    "residential": ParcelType.RESIDENTIAL,
    "industrial": ParcelType.INDUSTRIAL,
    "highway_strip": ParcelType.COMMERCIAL,
    "compound": ParcelType.RURAL,
    "forest": ParcelType.FOREST_CLEARING,
    "wetland": ParcelType.FOREST_CLEARING,
    "village": ParcelType.RURAL,
    "ruins": ParcelType.LANDMARK,
    "landmark": ParcelType.LANDMARK,
    "grove": ParcelType.FOREST_CLEARING,
    "alley_block": ParcelType.MIXED_USE,
    "plaza": ParcelType.CIVIC,
    "rooftop_network": ParcelType.MIXED_USE,
    "yard": ParcelType.INDUSTRIAL,
    "dock": ParcelType.INDUSTRIAL,
    "building": ParcelType.CIVIC,
    "trail": ParcelType.RURAL,
    "trailhead": ParcelType.RURAL,
    "outbuilding": ParcelType.RURAL,
    "checkpoint": ParcelType.MIXED_USE,
}


def _parcel_type_for(district_type: str) -> ParcelType:
    return _DISTRICT_TYPE_TO_PARCEL.get(district_type, ParcelType.MIXED_USE)


def generate_parcels(
    sketch_districts: list, metrics: GameplayMetrics
) -> list[Parcel]:
    parcels: list[Parcel] = []
    pw_min = metrics.building.parcel_min_width_m
    pw_max = metrics.building.parcel_max_width_m
    pd_m = metrics.building.parcel_depth_m
    parcel_w = max(pw_min, min(pw_max, (pw_min + pw_max) / 2.0))
    parcel_d = pd_m

    for d in sketch_districts:
        x0, y0, x1, y1 = _bbox(d.polygon)
        width = x1 - x0
        depth = y1 - y0
        if width < parcel_w or depth < parcel_d:
            continue
        # Margin so parcels don't kiss the district boundary
        margin_x = min(width * 0.05, parcel_w * 0.5)
        margin_y = min(depth * 0.05, parcel_d * 0.5)
        usable_w = width - 2 * margin_x
        usable_d = depth - 2 * margin_y
        n_cols = max(1, int(usable_w // parcel_w))
        n_rows = max(1, int(usable_d // parcel_d))
        ptype = _parcel_type_for(d.district_type)
        gap_x = (usable_w - n_cols * parcel_w) / max(n_cols + 1, 2)
        gap_y = (usable_d - n_rows * parcel_d) / max(n_rows + 1, 2)
        for r in range(n_rows):
            for c in range(n_cols):
                px0 = x0 + margin_x + gap_x + c * (parcel_w + gap_x)
                py0 = y0 + margin_y + gap_y + r * (parcel_d + gap_y)
                px1 = px0 + parcel_w
                py1 = py0 + parcel_d
                parcel = Parcel(
                    id=f"p_{d.id}_r{r:02d}c{c:02d}",
                    district_id=d.id,
                    polygon=_rect(px0, py0, px1, py1),
                    parcel_type=ptype,
                    tags=["from_template"],
                )
                parcels.append(parcel)

    return parcels
