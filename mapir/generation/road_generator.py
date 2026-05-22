"""Deterministic road generator for v0.5.

Inputs:
    * ``SketchDocument`` (provides district polygons and any user-drawn roads),
    * ``GameplayMetrics`` (road widths, intersection spacing),
    * ``RoadPattern`` (grid / organic / radial / coastal / rural / medieval /
      industrial / dense_urban).

Output: a list of ``GeneratedRoad`` instances. The seed is the sketch_id, so
the same sketch always produces the same road graph.
"""

from __future__ import annotations

import math
import random
import uuid

from ..core.models import Point2D, Polygon2D
from .gameplay_metrics import GameplayMetrics, RoadPattern
from .layout import GeneratedRoad


def _bbox_of(polygon: Polygon2D) -> tuple[float, float, float, float]:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return min(xs), min(ys), max(xs), max(ys)


def _centroid(polygon: Polygon2D) -> Point2D:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return Point2D(x=sum(xs) / len(xs), y=sum(ys) / len(ys))


def generate_roads(
    sketch_districts: list,
    metrics: GameplayMetrics,
    pattern: RoadPattern,
    *,
    seed: str = "",
) -> list[GeneratedRoad]:
    """Generate a road graph for a list of SketchDistricts.

    The strategy depends on ``pattern``:

    * ``grid`` / ``dense_urban`` / ``industrial``: arterial perimeter +
      local grid inside each district.
    * ``organic`` / ``medieval``: arterial perimeter + jittered connectors
      between district centroids.
    * ``radial``: collector roads from each district centroid to the global
      centroid.
    * ``coastal``: arterial that visits district centroids in x-order.
    * ``rural``: a single arterial across district centroids + sparse local
      stubs.
    """
    rng = random.Random(seed or "v0.5")
    out: list[GeneratedRoad] = []
    if not sketch_districts:
        return out

    centroids = {d.id: _centroid(d.polygon) for d in sketch_districts}
    bboxes = {d.id: _bbox_of(d.polygon) for d in sketch_districts}

    # ---- arterial network connecting centroids ------------------------
    arterial = _arterial(centroids, pattern, metrics)
    out.extend(arterial)

    # ---- inner roads per district -------------------------------------
    for d in sketch_districts:
        out.extend(_inner_roads(d, bboxes[d.id], metrics, pattern, rng))

    return out


def _arterial(
    centroids: dict[str, Point2D],
    pattern: RoadPattern,
    metrics: GameplayMetrics,
) -> list[GeneratedRoad]:
    ids = list(centroids.keys())
    if len(ids) < 2:
        return []
    # Pattern-specific routing
    if pattern is RoadPattern.RADIAL:
        # Star from the global centroid.
        cx = sum(centroids[i].x for i in ids) / len(ids)
        cy = sum(centroids[i].y for i in ids) / len(ids)
        hub = Point2D(x=cx, y=cy)
        roads: list[GeneratedRoad] = []
        for i in ids:
            roads.append(
                GeneratedRoad(
                    id=f"r_radial_{i}",
                    name=f"Radial → {i}",
                    road_type="arterial",
                    points=[hub, centroids[i]],
                    width_m=metrics.road.arterial_width_m,
                    district_id=i,
                    gameplay_tags=["arterial"],
                )
            )
        return roads
    if pattern is RoadPattern.COASTAL:
        ordered = sorted(ids, key=lambda i: centroids[i].x)
    elif pattern is RoadPattern.RURAL:
        ordered = sorted(ids, key=lambda i: centroids[i].x)
    else:
        # grid / organic / medieval / industrial / dense_urban: order by
        # angle around the global centroid for a closed loop.
        cx = sum(centroids[i].x for i in ids) / len(ids)
        cy = sum(centroids[i].y for i in ids) / len(ids)
        ordered = sorted(
            ids,
            key=lambda i: math.atan2(centroids[i].y - cy, centroids[i].x - cx),
        )
    points = [centroids[i] for i in ordered]
    if pattern in (RoadPattern.GRID, RoadPattern.DENSE_URBAN, RoadPattern.MEDIEVAL):
        # Close the loop
        points = [*points, points[0]]
    return [
        GeneratedRoad(
            id="r_arterial_main",
            name="Arterial Loop",
            road_type="arterial",
            points=points,
            width_m=metrics.road.arterial_width_m,
            gameplay_tags=["arterial", pattern.value],
        )
    ]


def _inner_roads(
    sketch_district,
    bbox: tuple[float, float, float, float],
    metrics: GameplayMetrics,
    pattern: RoadPattern,
    rng: random.Random,
) -> list[GeneratedRoad]:
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    depth = y1 - y0
    out: list[GeneratedRoad] = []

    if pattern in (RoadPattern.RURAL, RoadPattern.COASTAL):
        # Single collector through the district centre
        cy = (y0 + y1) / 2.0
        out.append(
            GeneratedRoad(
                id=f"r_{sketch_district.id}_collector",
                name=f"{sketch_district.name} Collector",
                road_type="collector",
                points=[Point2D(x=x0, y=cy), Point2D(x=x1, y=cy)],
                width_m=metrics.road.collector_width_m,
                district_id=sketch_district.id,
                gameplay_tags=["collector"],
            )
        )
        return out

    # Otherwise, a grid sized by intersection spacing.
    spacing = max(metrics.road.intersection_spacing_m, 10.0)
    n_cols = max(1, int(width // spacing))
    n_rows = max(1, int(depth // spacing))
    # Horizontal local streets
    for r in range(1, n_rows):
        y = y0 + r * (depth / n_rows)
        out.append(
            GeneratedRoad(
                id=f"r_{sketch_district.id}_h{r:02d}",
                name="",
                road_type="local",
                points=[Point2D(x=x0, y=y), Point2D(x=x1, y=y)],
                width_m=metrics.road.local_width_m,
                district_id=sketch_district.id,
                gameplay_tags=["local"],
            )
        )
    # Vertical local streets
    for c in range(1, n_cols):
        x = x0 + c * (width / n_cols)
        out.append(
            GeneratedRoad(
                id=f"r_{sketch_district.id}_v{c:02d}",
                name="",
                road_type="local",
                points=[Point2D(x=x, y=y0), Point2D(x=x, y=y1)],
                width_m=metrics.road.local_width_m,
                district_id=sketch_district.id,
                gameplay_tags=["local"],
            )
        )

    # Dense_urban gets alley fills, industrial gets service roads
    extra_type = None
    if pattern is RoadPattern.DENSE_URBAN:
        extra_type = ("alley", metrics.road.alley_width_m)
    elif pattern is RoadPattern.INDUSTRIAL:
        extra_type = ("service", metrics.road.alley_width_m)
    if extra_type and (n_cols >= 2 or n_rows >= 2):
        kind, w_m = extra_type
        # one jittered alley near the middle
        jx = (x0 + x1) / 2.0 + (rng.random() - 0.5) * (width / max(n_cols + 1, 3))
        out.append(
            GeneratedRoad(
                id=f"r_{sketch_district.id}_{kind}_01",
                name="",
                road_type=kind,
                points=[Point2D(x=jx, y=y0), Point2D(x=jx, y=y1)],
                width_m=w_m,
                district_id=sketch_district.id,
                gameplay_tags=[kind],
            )
        )

    return out
