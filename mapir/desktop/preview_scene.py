"""Qt-native 2D renderer for the preview panel.

Builds a :class:`QGraphicsScene` from a :class:`WorldIR` or :class:`SceneIR`,
mirroring the layout rules used by the SVG renderer (same y-flip, same
fit-to-bounds, same element order) but with the dark-theme palette so the
preview looks good inside the studio window.

The SVG renderer remains canonical for export — this module is the *live*
view in the desktop app and exists so the user can zoom and pan without
re-rendering an SVG on every change.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene

from ..core.enums import MarkerType, ZoneType
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
from .theme import PALETTE

_LABEL_FONT = QFont("Segoe UI", 9)
_LABEL_FONT_BOLD = QFont("Segoe UI", 10, QFont.DemiBold)


def _c(key: str) -> QColor:
    return QColor(PALETTE[key])


def _fy(y: float, depth: float) -> float:
    return depth - y


def _qpoly(poly: Polygon2D, depth: float) -> QPolygonF:
    return QPolygonF([QPointF(p.x, _fy(p.y, depth)) for p in poly.points])


def _qpolyline(points: list[Point2D], depth: float) -> QPolygonF:
    return QPolygonF([QPointF(p.x, _fy(p.y, depth)) for p in points])


def _bbox_center(poly: Polygon2D) -> tuple[float, float]:
    xs = [p.x for p in poly.points]
    ys = [p.y for p in poly.points]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _add_label(
    scene: QGraphicsScene, x: float, y_flipped: float, text: str, *, bold: bool = False
) -> None:
    item = scene.addSimpleText(text, _LABEL_FONT_BOLD if bold else _LABEL_FONT)
    item.setBrush(QBrush(_c("prev_label")))
    br = item.boundingRect()
    item.setPos(x - br.width() / 2.0, y_flipped - br.height() / 2.0)
    item.setZValue(1000)


# ============================================================
# Public entry
# ============================================================


def build_scene(ir: WorldIR | SceneIR) -> QGraphicsScene:
    """Construct a fresh QGraphicsScene that contains the whole IR rendered."""
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(_c("prev_bg")))
    if isinstance(ir, WorldIR):
        _build_world(scene, ir)
    else:
        _build_scene_ir(scene, ir)
    return scene


# ============================================================
# World
# ============================================================


def _build_world(scene: QGraphicsScene, world: WorldIR) -> None:
    w, d = world.scale.width_m, world.scale.depth_m
    bounds_pen = QPen(_c("prev_bounds"))
    bounds_pen.setStyle(Qt.DashLine)
    bounds_pen.setWidthF(max(1.0, min(w, d) * 0.002))
    bounds_pen.setCosmetic(False)
    scene.addRect(QRectF(0, 0, w, d), bounds_pen, QBrush(_c("panel")))
    scene.setSceneRect(QRectF(0, 0, w, d))

    for district in world.districts:
        _draw_district(scene, district, d)
    for water in world.water_bodies:
        _draw_water(scene, water, d)
    for road in world.roads:
        _draw_road(scene, road, d)
    for poi in world.pois:
        _draw_poi(scene, poi, d)
    for slot in world.scene_slots:
        _draw_scene_slot(scene, slot, d)


def _draw_district(scene: QGraphicsScene, district, depth: float) -> None:
    pen = QPen(_c("border"))
    pen.setWidthF(0.6)
    pen.setCosmetic(True)
    brush = QBrush(_c("prev_district"))
    item = scene.addPolygon(_qpoly(district.polygon, depth), pen, brush)
    item.setOpacity(0.65)
    cx, cy = _bbox_center(district.polygon)
    _add_label(scene, cx, _fy(cy, depth), district.name, bold=True)


def _draw_water(scene: QGraphicsScene, water: WaterBody, depth: float) -> None:
    pen = QPen(_c("prev_water"))
    pen.setWidthF(0.5)
    pen.setCosmetic(True)
    brush = QBrush(_c("prev_water"))
    item = scene.addPolygon(_qpoly(water.polygon, depth), pen, brush)
    item.setOpacity(0.7)
    cx, cy = _bbox_center(water.polygon)
    _add_label(scene, cx, _fy(cy, depth), water.name)


def _draw_road(scene: QGraphicsScene, road: Road, depth: float) -> None:
    pen = QPen(_c("prev_road"))
    pen.setWidthF(max(1.5, road.width_m))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    if road.road_type.value == "alley":
        pen.setStyle(Qt.DashLine)
    pen.setCosmetic(False)
    points = [QPointF(p.x, _fy(p.y, depth)) for p in road.points]
    for a, b in zip(points, points[1:], strict=False):
        scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)


def _draw_poi(scene: QGraphicsScene, poi: POI, depth: float) -> None:
    r = 4.0
    pen = QPen(QColor("#6e2117"))
    pen.setWidthF(0.5)
    pen.setCosmetic(True)
    brush = QBrush(_c("prev_poi"))
    scene.addEllipse(poi.position.x - r, _fy(poi.position.y, depth) - r, r * 2, r * 2, pen, brush)
    _add_label(scene, poi.position.x, _fy(poi.position.y, depth) - 10.0, poi.name)


def _draw_scene_slot(scene: QGraphicsScene, slot: SceneSlot, depth: float) -> None:
    half_w = slot.size.width_m / 2.0
    half_d = slot.size.depth_m / 2.0
    x = slot.position.x - half_w
    y_top = _fy(slot.position.y + half_d, depth)
    pen = QPen(_c("prev_scene_slot"))
    pen.setStyle(Qt.DashLine)
    pen.setWidthF(1.2)
    pen.setCosmetic(True)
    scene.addRect(QRectF(x, y_top, slot.size.width_m, slot.size.depth_m), pen)
    _add_label(scene, slot.position.x, _fy(slot.position.y, depth), slot.name)


# ============================================================
# Scene
# ============================================================

_ZONE_KEY = {
    ZoneType.ROOM: "prev_zone_room",
    ZoneType.STORAGE: "prev_zone_storage",
    ZoneType.SERVICE_AREA: "prev_zone_service",
    ZoneType.COMBAT_SPACE: "prev_zone_combat",
    ZoneType.STEALTH_ROUTE: "prev_zone_stealth",
    ZoneType.DANGER_ZONE: "prev_zone_danger",
    ZoneType.SAFE_ZONE: "prev_zone_safe",
    ZoneType.PATH: "prev_zone_path",
    ZoneType.PUBLIC_AREA: "prev_zone",
    ZoneType.PRIVATE_AREA: "prev_zone_room",
    ZoneType.EXTERIOR_YARD: "prev_zone",
}

_PATH_KEY = {
    "main_route": "prev_path",
    "alternate_route": "prev_path",
    "stealth_route": "prev_path_stealth",
    "escape_route": "prev_path_escape",
    "patrol_route": "prev_path",
}

_MARKER_KEY = {
    MarkerType.COVER: "prev_marker_cover",
    MarkerType.AMBUSH: "prev_marker_ambush",
    MarkerType.OBJECTIVE: "prev_marker_objective",
    MarkerType.ENEMY_SPAWN: "prev_marker_enemy",
    MarkerType.PLAYER_SPAWN: "prev_marker_player",
    MarkerType.EXTRACTION: "prev_marker_extract",
}


def _build_scene_ir(scene: QGraphicsScene, scene_ir: SceneIR) -> None:
    w, d = scene_ir.bounds.width_m, scene_ir.bounds.depth_m
    bounds_pen = QPen(_c("prev_bounds"))
    bounds_pen.setStyle(Qt.DashLine)
    bounds_pen.setWidthF(max(0.6, min(w, d) * 0.004))
    scene.addRect(QRectF(0, 0, w, d), bounds_pen, QBrush(_c("panel")))
    scene.setSceneRect(QRectF(0, 0, w, d))

    for zone in scene_ir.zones:
        _draw_zone(scene, zone, d)
    for obj in scene_ir.objects:
        _draw_object(scene, obj, d)
    for path in scene_ir.paths:
        _draw_path(scene, path, d)
    for entrance in scene_ir.entrances:
        _draw_entrance(scene, entrance, d)
    for marker in scene_ir.gameplay_markers:
        _draw_marker(scene, marker, d)


def _draw_zone(scene: QGraphicsScene, zone: SceneZone, depth: float) -> None:
    color = _c(_ZONE_KEY.get(zone.zone_type, "prev_zone"))
    pen = QPen(_c("border"))
    pen.setWidthF(0.4)
    pen.setCosmetic(True)
    item = scene.addPolygon(_qpoly(zone.polygon, depth), pen, QBrush(color))
    item.setOpacity(0.65)
    cx, cy = _bbox_center(zone.polygon)
    _add_label(scene, cx, _fy(cy, depth), zone.name)


def _draw_object(scene: QGraphicsScene, obj: SceneObject, depth: float) -> None:
    w_m = obj.size.width_m * obj.transform.scale
    d_m = obj.size.depth_m * obj.transform.scale
    x = obj.transform.position.x - w_m / 2.0
    y_top = _fy(obj.transform.position.y + d_m / 2.0, depth)
    color_key = (
        "prev_object_cover"
        if obj.object_type.value == "cover"
        else ("prev_object_wall" if obj.object_type.value == "wall" else "prev_object")
    )
    pen = QPen(_c("border"))
    pen.setWidthF(0.3)
    pen.setCosmetic(True)
    brush = QBrush(_c(color_key))
    scene.addRect(QRectF(x, y_top, w_m, d_m), pen, brush)


def _draw_path(scene: QGraphicsScene, path: ScenePath, depth: float) -> None:
    color = _c(_PATH_KEY.get(path.path_type.value, "prev_path"))
    pen = QPen(color)
    pen.setWidthF(max(1.0, path.width_m * 0.7))
    pen.setCapStyle(Qt.RoundCap)
    if path.path_type.value in ("stealth_route", "escape_route", "alternate_route"):
        pen.setStyle(Qt.DashLine)
    points = [QPointF(p.x, _fy(p.y, depth)) for p in path.points]
    for a, b in zip(points, points[1:], strict=False):
        scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)


def _draw_entrance(scene: QGraphicsScene, ent: Entrance, depth: float) -> None:
    x, y = ent.position.x, _fy(ent.position.y, depth)
    r = 1.4
    triangle = QPolygonF(
        [
            QPointF(x, y - r),
            QPointF(x - r, y + r),
            QPointF(x + r, y + r),
        ]
    )
    pen = QPen(QColor("#6e5b00"))
    pen.setWidthF(0.4)
    pen.setCosmetic(True)
    scene.addPolygon(triangle, pen, QBrush(_c("prev_entrance")))


def _draw_marker(scene: QGraphicsScene, marker: GameplayMarker, depth: float) -> None:
    color = _c(_MARKER_KEY.get(marker.marker_type, "muted"))
    r = marker.radius_m if marker.radius_m else 1.0
    pen = QPen(color.darker(150))
    pen.setWidthF(0.4)
    pen.setCosmetic(True)
    scene.addEllipse(
        marker.position.x - r,
        _fy(marker.position.y, depth) - r,
        r * 2,
        r * 2,
        pen,
        QBrush(color),
    )
