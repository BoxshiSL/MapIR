"""Render WorldIR / SceneIR onto a tkinter.Canvas.

Mirrors the visual language of :mod:`mapir.render.svg_renderer` (palette, flipped
y-axis, element ordering) so the desktop preview reads the same as the SVG. No
external deps — only tkinter primitives.
"""

from __future__ import annotations

import tkinter as tk
from typing import Iterable

from ..core.enums import MarkerType, RoadType, ScenePathType, ZoneType
from ..core.models import (
    POI,
    Entrance,
    GameplayMarker,
    Point2D,
    Polygon2D,
    Road,
    SceneIR,
    SceneObject,
    ScenePath,
    SceneSlot,
    SceneZone,
    WaterBody,
    WorldIR,
)

_MARGIN_PX = 16


# Palette aligned with svg_renderer's _STYLE block.
_C = {
    "bg": "#ffffff",
    "world_bounds_fill": "#fafafa",
    "world_bounds_stroke": "#444444",
    "scene_bounds_fill": "#fbfbf6",
    "scene_bounds_stroke": "#444444",
    "district_fill": "#f0e6d2",
    "district_stroke": "#b48a3b",
    "water_fill": "#b3d9ff",
    "water_stroke": "#4a7ab2",
    "road_stroke": "#555555",
    "alley_stroke": "#888888",
    "poi_fill": "#c0392b",
    "poi_stroke": "#6e2117",
    "scene_slot_stroke": "#2e8b57",
    "zone_default": "#e8eef5",
    "zone_room": "#fff1c2",
    "zone_storage": "#f4dcb8",
    "zone_service": "#d6e7ff",
    "zone_combat": "#ffd6d6",
    "zone_stealth": "#d5e7d2",
    "zone_danger": "#ffc1b3",
    "zone_safe": "#d2f0d2",
    "zone_path": "#e0e0e0",
    "zone_stroke": "#4a6178",
    "object_fill": "#cccccc",
    "object_stroke": "#555555",
    "entrance_fill": "#f1c40f",
    "entrance_stroke": "#6e5b00",
    "path_main": "#d35400",
    "path_stealth": "#16a085",
    "path_escape": "#c0392b",
    "path_alt": "#f39c12",
    "path_patrol": "#7d3c98",
    "marker_cover": "#2980b9",
    "marker_ambush": "#c0392b",
    "marker_objective": "#f1c40f",
    "marker_enemy": "#8e44ad",
    "marker_player": "#27ae60",
    "marker_extract": "#1abc9c",
    "marker_other": "#95a5a6",
    "label": "#222222",
}

_ZONE_FILL = {
    ZoneType.ROOM: _C["zone_room"],
    ZoneType.STORAGE: _C["zone_storage"],
    ZoneType.SERVICE_AREA: _C["zone_service"],
    ZoneType.COMBAT_SPACE: _C["zone_combat"],
    ZoneType.STEALTH_ROUTE: _C["zone_stealth"],
    ZoneType.DANGER_ZONE: _C["zone_danger"],
    ZoneType.SAFE_ZONE: _C["zone_safe"],
    ZoneType.PATH: _C["zone_path"],
    ZoneType.PUBLIC_AREA: _C["zone_default"],
    ZoneType.PRIVATE_AREA: _C["zone_room"],
    ZoneType.EXTERIOR_YARD: _C["zone_default"],
}

_PATH_COLOR = {
    ScenePathType.MAIN_ROUTE: _C["path_main"],
    ScenePathType.ALTERNATE_ROUTE: _C["path_alt"],
    ScenePathType.STEALTH_ROUTE: _C["path_stealth"],
    ScenePathType.ESCAPE_ROUTE: _C["path_escape"],
    ScenePathType.PATROL_ROUTE: _C["path_patrol"],
}

_PATH_DASH = {
    ScenePathType.STEALTH_ROUTE: (3, 2),
    ScenePathType.ESCAPE_ROUTE: (5, 2),
    ScenePathType.ALTERNATE_ROUTE: (2, 2),
    ScenePathType.PATROL_ROUTE: (1, 2),
}

_MARKER_COLOR = {
    MarkerType.COVER: _C["marker_cover"],
    MarkerType.AMBUSH: _C["marker_ambush"],
    MarkerType.OBJECTIVE: _C["marker_objective"],
    MarkerType.ENEMY_SPAWN: _C["marker_enemy"],
    MarkerType.PLAYER_SPAWN: _C["marker_player"],
    MarkerType.EXTRACTION: _C["marker_extract"],
}


class _Viewport:
    """Map world coordinates (origin bottom-left) into canvas pixels (origin top-left)."""

    def __init__(self, canvas_w: int, canvas_h: int, world_w: float, world_d: float) -> None:
        usable_w = max(1, canvas_w - 2 * _MARGIN_PX)
        usable_h = max(1, canvas_h - 2 * _MARGIN_PX)
        scale_x = usable_w / max(world_w, 1e-6)
        scale_y = usable_h / max(world_d, 1e-6)
        self.scale = min(scale_x, scale_y)
        self.world_d = world_d
        # Centre the drawing in the canvas.
        drawn_w = world_w * self.scale
        drawn_h = world_d * self.scale
        self.off_x = (canvas_w - drawn_w) / 2.0
        self.off_y = (canvas_h - drawn_h) / 2.0

    def px(self, x: float, y: float) -> tuple[float, float]:
        return (self.off_x + x * self.scale,
                self.off_y + (self.world_d - y) * self.scale)

    def length(self, meters: float) -> float:
        return max(1.0, meters * self.scale)


# ============================================================
# Public API
# ============================================================

def render(canvas: tk.Canvas, ir: WorldIR | SceneIR) -> None:
    """Clear ``canvas`` and draw ``ir`` filling the current widget size."""
    canvas.delete("all")
    canvas.update_idletasks()
    cw = max(int(canvas.winfo_width()), 1)
    ch = max(int(canvas.winfo_height()), 1)
    if isinstance(ir, WorldIR):
        _draw_world(canvas, ir, cw, ch)
    else:
        _draw_scene(canvas, ir, cw, ch)


# ============================================================
# World
# ============================================================

def _draw_world(canvas: tk.Canvas, world: WorldIR, cw: int, ch: int) -> None:
    w, d = world.scale.width_m, world.scale.depth_m
    vp = _Viewport(cw, ch, w, d)

    # World bounds rectangle.
    x0, y0 = vp.px(0.0, d)
    x1, y1 = vp.px(w, 0.0)
    canvas.create_rectangle(
        x0, y0, x1, y1,
        fill=_C["world_bounds_fill"], outline=_C["world_bounds_stroke"], dash=(4, 2),
    )

    for district in world.districts:
        _poly(canvas, vp, district.polygon, _C["district_fill"], _C["district_stroke"])
        _label_centre(canvas, vp, district.polygon, district.name, size=10)

    for water in world.water_bodies:
        _poly(canvas, vp, water.polygon, _C["water_fill"], _C["water_stroke"])
        _label_centre(canvas, vp, water.polygon, water.name, size=9)

    for road in world.roads:
        _road(canvas, vp, road)

    for poi in world.pois:
        _poi(canvas, vp, poi)

    for slot in world.scene_slots:
        _scene_slot(canvas, vp, slot)


def _road(canvas: tk.Canvas, vp: _Viewport, road: Road) -> None:
    coords = _polyline(vp, road.points)
    if not coords:
        return
    dash = (4, 2) if road.road_type == RoadType.ALLEY else None
    color = _C["alley_stroke"] if road.road_type == RoadType.ALLEY else _C["road_stroke"]
    kwargs: dict[str, object] = {"fill": color, "width": vp.length(road.width_m),
                                 "capstyle": "round", "joinstyle": "round"}
    if dash:
        kwargs["dash"] = dash
    canvas.create_line(*coords, **kwargs)


def _poi(canvas: tk.Canvas, vp: _Viewport, poi: POI) -> None:
    cx, cy = vp.px(poi.position.x, poi.position.y)
    r = 5
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                       fill=_C["poi_fill"], outline=_C["poi_stroke"])
    canvas.create_text(cx, cy - 10, text=poi.name, fill=_C["label"], font=("Segoe UI", 8))


def _scene_slot(canvas: tk.Canvas, vp: _Viewport, slot: SceneSlot) -> None:
    half_w = slot.size.width_m / 2.0
    half_d = slot.size.depth_m / 2.0
    x0, y0 = vp.px(slot.position.x - half_w, slot.position.y + half_d)
    x1, y1 = vp.px(slot.position.x + half_w, slot.position.y - half_d)
    canvas.create_rectangle(x0, y0, x1, y1, outline=_C["scene_slot_stroke"],
                            dash=(3, 2), width=2)
    cx, cy = vp.px(slot.position.x, slot.position.y)
    canvas.create_text(cx, cy, text=slot.name, fill=_C["label"], font=("Segoe UI", 8))


# ============================================================
# Scene
# ============================================================

def _draw_scene(canvas: tk.Canvas, scene: SceneIR, cw: int, ch: int) -> None:
    w, d = scene.bounds.width_m, scene.bounds.depth_m
    vp = _Viewport(cw, ch, w, d)

    x0, y0 = vp.px(0.0, d)
    x1, y1 = vp.px(w, 0.0)
    canvas.create_rectangle(
        x0, y0, x1, y1,
        fill=_C["scene_bounds_fill"], outline=_C["scene_bounds_stroke"], dash=(4, 2),
    )

    for zone in scene.zones:
        _zone(canvas, vp, zone)
    for obj in scene.objects:
        _scene_object(canvas, vp, obj)
    for path in scene.paths:
        _scene_path(canvas, vp, path)
    for entrance in scene.entrances:
        _entrance(canvas, vp, entrance)
    for marker in scene.gameplay_markers:
        _marker(canvas, vp, marker)


def _zone(canvas: tk.Canvas, vp: _Viewport, zone: SceneZone) -> None:
    fill = _ZONE_FILL.get(zone.zone_type, _C["zone_default"])
    _poly(canvas, vp, zone.polygon, fill, _C["zone_stroke"])
    _label_centre(canvas, vp, zone.polygon, zone.name, size=9)


def _scene_object(canvas: tk.Canvas, vp: _Viewport, obj: SceneObject) -> None:
    sx = obj.size.width_m * obj.transform.scale
    sy = obj.size.depth_m * obj.transform.scale
    half_w, half_d = sx / 2.0, sy / 2.0
    x0, y0 = vp.px(obj.transform.position.x - half_w, obj.transform.position.y + half_d)
    x1, y1 = vp.px(obj.transform.position.x + half_w, obj.transform.position.y - half_d)
    canvas.create_rectangle(x0, y0, x1, y1,
                            fill=_C["object_fill"], outline=_C["object_stroke"])


def _scene_path(canvas: tk.Canvas, vp: _Viewport, path: ScenePath) -> None:
    coords = _polyline(vp, path.points)
    if not coords:
        return
    color = _PATH_COLOR.get(path.path_type, _C["path_main"])
    dash = _PATH_DASH.get(path.path_type)
    kwargs: dict[str, object] = {"fill": color, "width": vp.length(path.width_m),
                                 "capstyle": "round"}
    if dash:
        kwargs["dash"] = dash
    canvas.create_line(*coords, **kwargs)


def _entrance(canvas: tk.Canvas, vp: _Viewport, ent: Entrance) -> None:
    cx, cy = vp.px(ent.position.x, ent.position.y)
    r = 6
    canvas.create_polygon(
        cx, cy - r, cx - r, cy + r, cx + r, cy + r,
        fill=_C["entrance_fill"], outline=_C["entrance_stroke"],
    )
    canvas.create_text(cx + 8, cy, text=ent.name, anchor="w",
                       fill=_C["label"], font=("Segoe UI", 8))


def _marker(canvas: tk.Canvas, vp: _Viewport, marker: GameplayMarker) -> None:
    color = _MARKER_COLOR.get(marker.marker_type, _C["marker_other"])
    cx, cy = vp.px(marker.position.x, marker.position.y)
    r = max(3.0, vp.length(marker.radius_m or 1.0))
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")


# ============================================================
# Geometry helpers
# ============================================================

def _poly(canvas: tk.Canvas, vp: _Viewport, polygon: Polygon2D,
          fill: str, outline: str) -> None:
    coords = _flatten(vp, polygon.points)
    if len(coords) < 6:
        return
    canvas.create_polygon(*coords, fill=fill, outline=outline)


def _polyline(vp: _Viewport, pts: Iterable[Point2D]) -> list[float]:
    return _flatten(vp, list(pts))


def _flatten(vp: _Viewport, pts: list[Point2D]) -> list[float]:
    out: list[float] = []
    for p in pts:
        x, y = vp.px(p.x, p.y)
        out.append(x)
        out.append(y)
    return out


def _label_centre(canvas: tk.Canvas, vp: _Viewport, polygon: Polygon2D,
                  text: str, *, size: int) -> None:
    if not polygon.points:
        return
    cx = sum(p.x for p in polygon.points) / len(polygon.points)
    cy = sum(p.y for p in polygon.points) / len(polygon.points)
    px, py = vp.px(cx, cy)
    canvas.create_text(px, py, text=text, fill=_C["label"], font=("Segoe UI", size))
