"""Qt-native 2D renderer for the preview panel.

Builds a :class:`QGraphicsScene` from a :class:`WorldIR` or :class:`SceneIR`,
mirroring the layout rules used by the SVG renderer (same y-flip, same
fit-to-bounds, same element order) but with the dark-theme palette so the
preview looks good inside the studio window.

v0.5 adds:

* ``PreviewOptions.label_scale`` — global multiplier for label font size.
* ``PreviewOptions.layer_visibility`` — per-layer toggles (districts, roads,
  pois, scene slots, zones, paths, entrances, objects, markers, water).
* Greedy overlap suppression for labels — when bboxes collide, later labels
  drop out so the preview doesn't scream.
* Heuristic auto-scaling based on world / scene width.

The SVG renderer remains canonical for export. This module is the *live*
view in the desktop app; the user can change ``PreviewOptions`` without
re-rendering an SVG on every change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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


# ---------- layers ----------

WORLD_LAYERS: tuple[str, ...] = (
    "districts",
    "water",
    "roads",
    "pois",
    "scene_slots",
)
SCENE_LAYERS: tuple[str, ...] = (
    "zones",
    "objects",
    "paths",
    "entrances",
    "markers",
)
ALL_LAYERS: tuple[str, ...] = tuple(dict.fromkeys(WORLD_LAYERS + SCENE_LAYERS))


def default_layer_visibility() -> dict[str, bool]:
    return {layer: True for layer in ALL_LAYERS}


@dataclass
class PreviewOptions:
    """Knobs for :func:`build_scene`.

    * ``label_scale``: multiplier on top of the auto-computed font size.
      ``1.0`` keeps the v0.4 baseline of 9pt; ``0.5`` halves it; ``2.0``
      doubles it.
    * ``layer_visibility``: per-layer toggles. Unknown keys are ignored.
    * ``suppress_overlap``: when True, the renderer drops labels whose bbox
      collides with an already-placed label.
    * ``auto_scale``: when True, shrinks labels for large worlds so a
      4000m world doesn't render 9pt text the size of buildings.
    """

    label_scale: float = 1.0
    layer_visibility: dict[str, bool] = field(default_factory=default_layer_visibility)
    suppress_overlap: bool = True
    auto_scale: bool = True
    dropped_labels: int = 0  # populated by build_scene, useful for validators


def _is_visible(options: PreviewOptions, layer: str) -> bool:
    return options.layer_visibility.get(layer, True)


def _label_pointsize(options: PreviewOptions, world_width: float) -> int:
    base = 9.0
    if options.auto_scale and world_width > 0.0:
        # heuristic: scale down once the canvas exceeds ~1500m
        auto = min(1.0, 1500.0 / world_width) ** 0.5
        base = base * max(0.55, auto)
    pt = int(round(base * max(0.4, options.label_scale)))
    return max(5, pt)


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


def _bbox_overlap(a: QRectF, b: QRectF) -> bool:
    return a.intersects(b)


class _LabelTracker:
    """Greedy bbox-overlap suppressor."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.placed: list[QRectF] = []
        self.dropped = 0

    def place(self, rect: QRectF) -> bool:
        if not self.enabled:
            self.placed.append(rect)
            return True
        for existing in self.placed:
            if _bbox_overlap(rect, existing):
                self.dropped += 1
                return False
        self.placed.append(rect)
        return True


def _add_label(
    scene: QGraphicsScene,
    tracker: _LabelTracker,
    font: QFont,
    bold_font: QFont,
    x: float,
    y_flipped: float,
    text: str,
    *,
    bold: bool = False,
) -> None:
    if not text:
        return
    item = scene.addSimpleText(text, bold_font if bold else font)
    item.setBrush(QBrush(_c("prev_label")))
    br = item.boundingRect()
    rect = QRectF(x - br.width() / 2.0, y_flipped - br.height() / 2.0, br.width(), br.height())
    if not tracker.place(rect):
        scene.removeItem(item)
        return
    item.setPos(rect.x(), rect.y())
    item.setZValue(1000)


# ============================================================
# Public entry
# ============================================================


def build_scene(
    ir: WorldIR | SceneIR,
    options: PreviewOptions | None = None,
) -> QGraphicsScene:
    """Construct a fresh QGraphicsScene that contains the whole IR rendered.

    ``options`` may be ``None`` for backward compatibility — that path is
    equivalent to the v0.4 defaults: all layers on, label_scale=1.0, auto
    scaling on, overlap suppression on.
    """
    options = options or PreviewOptions()
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(_c("prev_bg")))
    if isinstance(ir, WorldIR):
        _build_world(scene, ir, options)
    else:
        _build_scene_ir(scene, ir, options)
    return scene


# ============================================================
# World
# ============================================================


def _build_world(scene: QGraphicsScene, world: WorldIR, options: PreviewOptions) -> None:
    w, d = world.scale.width_m, world.scale.depth_m
    bounds_pen = QPen(_c("prev_bounds"))
    bounds_pen.setStyle(Qt.DashLine)
    bounds_pen.setWidthF(max(1.0, min(w, d) * 0.002))
    bounds_pen.setCosmetic(False)
    scene.addRect(QRectF(0, 0, w, d), bounds_pen, QBrush(_c("panel")))
    scene.setSceneRect(QRectF(0, 0, w, d))

    pt = _label_pointsize(options, w)
    font = QFont("Segoe UI", pt)
    font_bold = QFont("Segoe UI", pt + 1, QFont.DemiBold)
    tracker = _LabelTracker(enabled=options.suppress_overlap)

    if _is_visible(options, "districts"):
        for district in world.districts:
            _draw_district(scene, district, d, font, font_bold, tracker)
    if _is_visible(options, "water"):
        for water in world.water_bodies:
            _draw_water(scene, water, d, font, font_bold, tracker)
    if _is_visible(options, "roads"):
        for road in world.roads:
            _draw_road(scene, road, d)
    if _is_visible(options, "pois"):
        for poi in world.pois:
            _draw_poi(scene, poi, d, font, font_bold, tracker)
    if _is_visible(options, "scene_slots"):
        for slot in world.scene_slots:
            _draw_scene_slot(scene, slot, d, font, font_bold, tracker)

    options.dropped_labels = tracker.dropped


def _draw_district(
    scene, district, depth, font, font_bold, tracker
) -> None:
    pen = QPen(_c("border"))
    pen.setWidthF(0.6)
    pen.setCosmetic(True)
    brush = QBrush(_c("prev_district"))
    item = scene.addPolygon(_qpoly(district.polygon, depth), pen, brush)
    item.setOpacity(0.65)
    cx, cy = _bbox_center(district.polygon)
    _add_label(scene, tracker, font, font_bold, cx, _fy(cy, depth), district.name, bold=True)


def _draw_water(scene, water: WaterBody, depth, font, font_bold, tracker) -> None:
    pen = QPen(_c("prev_water"))
    pen.setWidthF(0.5)
    pen.setCosmetic(True)
    brush = QBrush(_c("prev_water"))
    item = scene.addPolygon(_qpoly(water.polygon, depth), pen, brush)
    item.setOpacity(0.7)
    cx, cy = _bbox_center(water.polygon)
    _add_label(scene, tracker, font, font_bold, cx, _fy(cy, depth), water.name)


def _draw_road(scene, road: Road, depth) -> None:
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


def _draw_poi(scene, poi: POI, depth, font, font_bold, tracker) -> None:
    r = 4.0
    pen = QPen(QColor("#6e2117"))
    pen.setWidthF(0.5)
    pen.setCosmetic(True)
    brush = QBrush(_c("prev_poi"))
    scene.addEllipse(poi.position.x - r, _fy(poi.position.y, depth) - r, r * 2, r * 2, pen, brush)
    _add_label(scene, tracker, font, font_bold, poi.position.x, _fy(poi.position.y, depth) - 10.0, poi.name)


def _draw_scene_slot(scene, slot: SceneSlot, depth, font, font_bold, tracker) -> None:
    half_w = slot.size.width_m / 2.0
    half_d = slot.size.depth_m / 2.0
    x = slot.position.x - half_w
    y_top = _fy(slot.position.y + half_d, depth)
    pen = QPen(_c("prev_scene_slot"))
    pen.setStyle(Qt.DashLine)
    pen.setWidthF(1.2)
    pen.setCosmetic(True)
    scene.addRect(QRectF(x, y_top, slot.size.width_m, slot.size.depth_m), pen)
    _add_label(scene, tracker, font, font_bold, slot.position.x, _fy(slot.position.y, depth), slot.name)


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


def _build_scene_ir(scene: QGraphicsScene, scene_ir: SceneIR, options: PreviewOptions) -> None:
    w, d = scene_ir.bounds.width_m, scene_ir.bounds.depth_m
    bounds_pen = QPen(_c("prev_bounds"))
    bounds_pen.setStyle(Qt.DashLine)
    bounds_pen.setWidthF(max(0.6, min(w, d) * 0.004))
    scene.addRect(QRectF(0, 0, w, d), bounds_pen, QBrush(_c("panel")))
    scene.setSceneRect(QRectF(0, 0, w, d))

    pt = _label_pointsize(options, w)
    font = QFont("Segoe UI", pt)
    font_bold = QFont("Segoe UI", pt + 1, QFont.DemiBold)
    tracker = _LabelTracker(enabled=options.suppress_overlap)

    if _is_visible(options, "zones"):
        for zone in scene_ir.zones:
            _draw_zone(scene, zone, d, font, font_bold, tracker)
    if _is_visible(options, "objects"):
        for obj in scene_ir.objects:
            _draw_object(scene, obj, d)
    if _is_visible(options, "paths"):
        for path in scene_ir.paths:
            _draw_path(scene, path, d)
    if _is_visible(options, "entrances"):
        for entrance in scene_ir.entrances:
            _draw_entrance(scene, entrance, d)
    if _is_visible(options, "markers"):
        for marker in scene_ir.gameplay_markers:
            _draw_marker(scene, marker, d)

    options.dropped_labels = tracker.dropped


def _draw_zone(scene, zone: SceneZone, depth, font, font_bold, tracker) -> None:
    color = _c(_ZONE_KEY.get(zone.zone_type, "prev_zone"))
    pen = QPen(_c("border"))
    pen.setWidthF(0.4)
    pen.setCosmetic(True)
    item = scene.addPolygon(_qpoly(zone.polygon, depth), pen, QBrush(color))
    item.setOpacity(0.65)
    cx, cy = _bbox_center(zone.polygon)
    _add_label(scene, tracker, font, font_bold, cx, _fy(cy, depth), zone.name)


def _draw_object(scene, obj: SceneObject, depth) -> None:
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


def _draw_path(scene, path: ScenePath, depth) -> None:
    color = _c(_PATH_KEY.get(path.path_type.value, "prev_path"))
    pen = QPen(color)
    pen.setWidthF(max(1.0, path.width_m * 0.7))
    pen.setCapStyle(Qt.RoundCap)
    if path.path_type.value in ("stealth_route", "escape_route", "alternate_route"):
        pen.setStyle(Qt.DashLine)
    points = [QPointF(p.x, _fy(p.y, depth)) for p in path.points]
    for a, b in zip(points, points[1:], strict=False):
        scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)


def _draw_entrance(scene, ent: Entrance, depth) -> None:
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


def _draw_marker(scene, marker: GameplayMarker, depth) -> None:
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
