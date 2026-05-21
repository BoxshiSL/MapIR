"""Lightweight 2D geometry helpers used by validation and renderers."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Point2D, Polygon2D, Size2D, Size3D, Transform3D


@dataclass(frozen=True)
class BBox2D:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def depth(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> tuple[float, float]:
        return ((self.min_x + self.max_x) / 2.0, (self.min_y + self.max_y) / 2.0)


def polygon_bbox(poly: Polygon2D) -> BBox2D:
    xs = [p.x for p in poly.points]
    ys = [p.y for p in poly.points]
    return BBox2D(min(xs), min(ys), max(xs), max(ys))


def points_bbox(points: list[Point2D]) -> BBox2D:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return BBox2D(min(xs), min(ys), max(xs), max(ys))


def point_in_world(p: Point2D, scale: Size2D, slack: float = 0.0) -> bool:
    return (
        -slack <= p.x <= scale.width_m + slack
        and -slack <= p.y <= scale.depth_m + slack
    )


def point_in_scene(p: Point2D, width_m: float, depth_m: float, slack: float = 0.0) -> bool:
    return -slack <= p.x <= width_m + slack and -slack <= p.y <= depth_m + slack


def polygon_in_bounds(poly: Polygon2D, width_m: float, depth_m: float, slack: float = 0.0) -> bool:
    return all(point_in_scene(p, width_m, depth_m, slack) for p in poly.points)


def object_footprint_bbox(transform: Transform3D, size: Size3D) -> BBox2D:
    """Axis-aligned XY footprint ignoring rotation (MVP approximation)."""
    cx = transform.position.x
    cy = transform.position.y
    hw = (size.width_m * transform.scale) / 2.0
    hd = (size.depth_m * transform.scale) / 2.0
    return BBox2D(cx - hw, cy - hd, cx + hw, cy + hd)


def bbox_overlap(a: BBox2D, b: BBox2D, eps: float = 1e-6) -> bool:
    if a.max_x <= b.min_x + eps or b.max_x <= a.min_x + eps:
        return False
    if a.max_y <= b.min_y + eps or b.max_y <= a.min_y + eps:
        return False
    return True
