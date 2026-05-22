"""SVG renderer for WorldIR and SceneIR.

Hand-rolled XML, no external dependencies. JSON y-axis points up; SVG y points
down, so all coordinates are flipped via `_fy(y, depth)`. Each element class
has a CSS rule defined in the inline `<style>` block.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

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

# ---------- shared CSS ----------
#
# v0.5: the label font sizes are templated so the caller can pass
# ``label_scale`` to :func:`render` and rescale ``.label-sm`` / ``.label-md``
# without touching the rest of the stylesheet.

_STYLE_TEMPLATE = """
.bg            {{ fill: #ffffff; stroke: #222; stroke-width: 0.3%; }}
.world-bounds  {{ fill: #fafafa; stroke: #444; stroke-width: 0.25%; stroke-dasharray: 4 2; }}
.scene-bounds  {{ fill: #fbfbf6; stroke: #444; stroke-width: 0.25%; stroke-dasharray: 4 2; }}
.district      {{ fill: #f0e6d2; stroke: #b48a3b; stroke-width: 0.2%; fill-opacity: 0.65; }}
.water         {{ fill: #b3d9ff; stroke: #4a7ab2; stroke-width: 0.15%; fill-opacity: 0.7; }}
.road          {{ fill: none; stroke: #555; stroke-linecap: round; stroke-linejoin: round; }}
.alley         {{ stroke: #888; stroke-dasharray: 4 2; }}
.poi           {{ fill: #c0392b; stroke: #6e2117; stroke-width: 0.1%; }}
.scene-slot    {{ fill: none; stroke: #2e8b57; stroke-width: 0.25%; stroke-dasharray: 3 2; }}
.zone          {{ fill: #e8eef5; stroke: #4a6178; stroke-width: 0.2%; fill-opacity: 0.55; }}
.zone-room     {{ fill: #fff1c2; }}
.zone-storage  {{ fill: #f4dcb8; }}
.zone-service  {{ fill: #d6e7ff; }}
.zone-combat   {{ fill: #ffd6d6; }}
.zone-stealth  {{ fill: #d5e7d2; }}
.zone-danger   {{ fill: #ffc1b3; }}
.zone-safe     {{ fill: #d2f0d2; }}
.zone-path     {{ fill: #e0e0e0; }}
.path-main     {{ fill: none; stroke: #d35400; stroke-width: 1.5; stroke-linecap: round; }}
.path-stealth  {{ fill: none; stroke: #16a085; stroke-width: 1.2; stroke-dasharray: 3 2; }}
.path-escape   {{ fill: none; stroke: #c0392b; stroke-width: 1.5; stroke-dasharray: 5 2; }}
.path-alt      {{ fill: none; stroke: #f39c12; stroke-width: 1.2; stroke-dasharray: 2 2; }}
.path-patrol   {{ fill: none; stroke: #7d3c98; stroke-width: 1.0; stroke-dasharray: 1 2; }}
.object        {{ fill: #cccccc; stroke: #555; stroke-width: 0.15%; }}
.entrance      {{ fill: #f1c40f; stroke: #6e5b00; stroke-width: 0.1%; }}
.marker-cover     {{ fill: #2980b9; }}
.marker-ambush    {{ fill: #c0392b; }}
.marker-objective {{ fill: #f1c40f; stroke: #7d6608; stroke-width: 0.15%; }}
.marker-enemy     {{ fill: #8e44ad; }}
.marker-player    {{ fill: #27ae60; }}
.marker-extract   {{ fill: #1abc9c; }}
.marker-other     {{ fill: #95a5a6; }}
.label         {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                  fill: #222; pointer-events: none; }}
.label-sm      {{ font-size: {label_sm:.1f}px; }}
.label-md      {{ font-size: {label_md:.1f}px; }}
.legend-box    {{ fill: #ffffff; stroke: #999; stroke-width: 0.5; opacity: 0.9; }}
.legend-text   {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 10px; fill: #222; }}
""".strip()


def _style(label_scale: float) -> str:
    scale = max(0.4, float(label_scale))
    return _STYLE_TEMPLATE.format(label_sm=9.0 * scale, label_md=11.0 * scale)


# ============================================================
# Public API
# ============================================================


def render(ir: WorldIR | SceneIR, *, label_scale: float = 1.0) -> str:
    """Render IR to SVG XML.

    ``label_scale`` (v0.5) scales the ``.label-sm`` / ``.label-md`` font sizes
    relative to the v0.4 baseline (9px / 11px). The geometry is otherwise
    unchanged, so the rendered file remains valid SVG.
    """
    if isinstance(ir, WorldIR):
        return _render_world(ir, label_scale=label_scale)
    return _render_scene(ir, label_scale=label_scale)


# ============================================================
# Helpers
# ============================================================


def _fy(y: float, depth: float) -> float:
    """Flip y so JSON-up matches SVG-down."""
    return depth - y


def _polygon_points(poly: Polygon2D, depth: float) -> str:
    return " ".join(f"{p.x:.2f},{_fy(p.y, depth):.2f}" for p in poly.points)


def _polyline_points(pts: list[Point2D], depth: float) -> str:
    return " ".join(f"{p.x:.2f},{_fy(p.y, depth):.2f}" for p in pts)


def _bbox_center(poly: Polygon2D) -> tuple[float, float]:
    xs = [p.x for p in poly.points]
    ys = [p.y for p in poly.points]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _label(x: float, y: float, depth: float, text: str, cls: str = "label label-sm") -> str:
    safe = escape(text)
    return (
        f'<text class="{cls}" x="{x:.2f}" y="{_fy(y, depth):.2f}" '
        f'text-anchor="middle" dominant-baseline="middle">{safe}</text>'
    )


def _svg_open(width: float, depth: float, label_scale: float = 1.0) -> str:
    # Pixel size capped so previews are usable in a browser
    px_w = min(1600, max(600, width))
    px_h = px_w * (depth / max(width, 1.0))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.2f} {depth:.2f}" '
        f'width="{px_w:.0f}" height="{px_h:.0f}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f"<style>{_style(label_scale)}</style>"
    )


def _svg_close() -> str:
    return "</svg>"


def _legend(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    line_h = 14
    box_w = 170
    box_h = 10 + line_h * len(items) + 4
    parts = [
        '<g class="legend" transform="translate(8,8)">',
        f'<rect class="legend-box" x="0" y="0" width="{box_w}" height="{box_h}" rx="4"/>',
    ]
    for i, (swatch_cls, text) in enumerate(items):
        y = 14 + i * line_h
        parts.append(f'<rect class="{swatch_cls}" x="8" y="{y - 9:.0f}" width="14" height="10"/>')
        parts.append(f'<text class="legend-text" x="28" y="{y:.0f}">{escape(text)}</text>')
    parts.append("</g>")
    return "".join(parts)


# ============================================================
# World rendering
# ============================================================


def _render_world(world: WorldIR, *, label_scale: float = 1.0) -> str:
    w, d = world.scale.width_m, world.scale.depth_m
    parts: list[str] = [_svg_open(w, d, label_scale)]

    parts.append(f'<rect class="world-bounds" x="0" y="0" width="{w:.2f}" height="{d:.2f}"/>')

    for district in world.districts:
        parts.append(_render_district(district, d))
    for water in world.water_bodies:
        parts.append(_render_water(water, d))
    for road in world.roads:
        parts.append(_render_road(road, d))
    for poi in world.pois:
        parts.append(_render_poi(poi, d))
    for slot in world.scene_slots:
        parts.append(_render_scene_slot(slot, d))

    legend = [
        ("district", "District"),
        ("water", "Water"),
        ("road", "Road"),
        ("poi", "POI"),
        ("scene-slot", "Scene Slot"),
    ]
    parts.append(_legend(legend))
    parts.append(_svg_close())
    return "".join(parts)


def _render_district(dist, depth: float) -> str:
    pts = _polygon_points(dist.polygon, depth)
    cx, cy = _bbox_center(dist.polygon)
    return f'<polygon class="district" points="{pts}"/>' + _label(
        cx, cy, depth, dist.name, cls="label label-md"
    )


def _render_water(water: WaterBody, depth: float) -> str:
    pts = _polygon_points(water.polygon, depth)
    cx, cy = _bbox_center(water.polygon)
    return f'<polygon class="water" points="{pts}"/>' + _label(cx, cy, depth, water.name)


def _render_road(road: Road, depth: float) -> str:
    pts = _polyline_points(road.points, depth)
    cls = "road alley" if road.road_type.value == "alley" else "road"
    return (
        f'<polyline class="{cls}" points="{pts}" ' f'stroke-width="{max(1.0, road.width_m):.2f}"/>'
    )


def _render_poi(poi: POI, depth: float) -> str:
    return (
        f'<circle class="poi" cx="{poi.position.x:.2f}" cy="{_fy(poi.position.y, depth):.2f}" r="6"/>'
        + _label(poi.position.x, poi.position.y - 10, depth, poi.name)
    )


def _render_scene_slot(slot: SceneSlot, depth: float) -> str:
    half_w = slot.size.width_m / 2.0
    half_d = slot.size.depth_m / 2.0
    x = slot.position.x - half_w
    y_top = _fy(slot.position.y + half_d, depth)
    return (
        f'<rect class="scene-slot" x="{x:.2f}" y="{y_top:.2f}" '
        f'width="{slot.size.width_m:.2f}" height="{slot.size.depth_m:.2f}"/>'
        + _label(slot.position.x, slot.position.y, depth, slot.name)
    )


# ============================================================
# Scene rendering
# ============================================================

_ZONE_CLASS = {
    ZoneType.ROOM: "zone zone-room",
    ZoneType.STORAGE: "zone zone-storage",
    ZoneType.SERVICE_AREA: "zone zone-service",
    ZoneType.COMBAT_SPACE: "zone zone-combat",
    ZoneType.STEALTH_ROUTE: "zone zone-stealth",
    ZoneType.DANGER_ZONE: "zone zone-danger",
    ZoneType.SAFE_ZONE: "zone zone-safe",
    ZoneType.PATH: "zone zone-path",
    ZoneType.PUBLIC_AREA: "zone",
    ZoneType.PRIVATE_AREA: "zone zone-room",
    ZoneType.EXTERIOR_YARD: "zone",
}

_PATH_CLASS = {
    "main_route": "path-main",
    "alternate_route": "path-alt",
    "stealth_route": "path-stealth",
    "escape_route": "path-escape",
    "patrol_route": "path-patrol",
}

_MARKER_CLASS = {
    MarkerType.COVER: "marker-cover",
    MarkerType.AMBUSH: "marker-ambush",
    MarkerType.OBJECTIVE: "marker-objective",
    MarkerType.ENEMY_SPAWN: "marker-enemy",
    MarkerType.PLAYER_SPAWN: "marker-player",
    MarkerType.EXTRACTION: "marker-extract",
}


def _render_scene(scene: SceneIR, *, label_scale: float = 1.0) -> str:
    w, d = scene.bounds.width_m, scene.bounds.depth_m
    parts: list[str] = [_svg_open(w, d, label_scale)]
    parts.append(f'<rect class="scene-bounds" x="0" y="0" width="{w:.2f}" height="{d:.2f}"/>')

    for zone in scene.zones:
        parts.append(_render_zone(zone, d))
    for obj in scene.objects:
        parts.append(_render_object(obj, d))
    for path in scene.paths:
        parts.append(_render_path(path, d))
    for entrance in scene.entrances:
        parts.append(_render_entrance(entrance, d))
    for marker in scene.gameplay_markers:
        parts.append(_render_marker(marker, d))

    parts.append(
        _legend(
            [
                ("zone", "Zone"),
                ("object", "Object"),
                ("entrance", "Entrance"),
                ("path-main", "Main route"),
                ("path-escape", "Escape route"),
                ("path-stealth", "Stealth route"),
                ("marker-cover", "Cover marker"),
                ("marker-enemy", "Enemy spawn"),
                ("marker-player", "Player spawn"),
            ]
        )
    )
    parts.append(_svg_close())
    return "".join(parts)


def _render_zone(zone: SceneZone, depth: float) -> str:
    cls = _ZONE_CLASS.get(zone.zone_type, "zone")
    pts = _polygon_points(zone.polygon, depth)
    cx, cy = _bbox_center(zone.polygon)
    return f'<polygon class="{cls}" points="{pts}"/>' + _label(cx, cy, depth, zone.name)


def _render_object(obj: SceneObject, depth: float) -> str:
    half_w = (obj.size.width_m * obj.transform.scale) / 2.0
    half_d = (obj.size.depth_m * obj.transform.scale) / 2.0
    x = obj.transform.position.x - half_w
    y_top = _fy(obj.transform.position.y + half_d, depth)
    return (
        f'<rect class="object" x="{x:.2f}" y="{y_top:.2f}" '
        f'width="{obj.size.width_m * obj.transform.scale:.2f}" '
        f'height="{obj.size.depth_m * obj.transform.scale:.2f}"/>'
    )


def _render_path(path: ScenePath, depth: float) -> str:
    cls = _PATH_CLASS.get(path.path_type.value, "path-main")
    pts = _polyline_points(path.points, depth)
    return f'<polyline class="{cls}" points="{pts}" stroke-width="{max(1.0, path.width_m):.2f}"/>'


def _render_entrance(ent: Entrance, depth: float) -> str:
    x, y = ent.position.x, _fy(ent.position.y, depth)
    r = 1.4
    triangle = f"{x:.2f},{y - r:.2f} {x - r:.2f},{y + r:.2f} {x + r:.2f},{y + r:.2f}"
    return f'<polygon class="entrance" points="{triangle}"/>' + _label(
        ent.position.x + 2.0, ent.position.y, depth, ent.name
    )


def _render_marker(marker: GameplayMarker, depth: float) -> str:
    cls = _MARKER_CLASS.get(marker.marker_type, "marker-other")
    r = marker.radius_m if marker.radius_m else 1.0
    return (
        f'<circle class="{cls}" '
        f'cx="{marker.position.x:.2f}" cy="{_fy(marker.position.y, depth):.2f}" '
        f'r="{r:.2f}"/>'
    )
