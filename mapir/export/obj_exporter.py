"""Minimal Wavefront OBJ exporter for blockout previews.

This is an MVP approximation: complex polygons (any non-rectangular district,
zone, or water body) are reduced to their axis-aligned bounding box. The
resulting OBJ is intended for visual blockout only, not for production geometry.

Axes convention:
    x = horizontal (JSON x)
    z = horizontal (JSON y; OBJ z grows into the screen)
    y = vertical (height)
"""

from __future__ import annotations

from io import StringIO

from ..core.models import (
    POI,
    Polygon2D,
    SceneIR,
    SceneSlot,
    WaterBody,
    WorldIR,
)


class _OBJBuilder:
    """Accumulates vertices/faces with a running index so groups stay correct."""

    def __init__(self) -> None:
        self.out = StringIO()
        self.vertex_count = 0

    def header(self, title: str, extra: str = "") -> None:
        self.out.write(f"# MapIR OBJ blockout — {title}\n")
        self.out.write("# MVP approximation: non-rectangular polygons collapse to bbox.\n")
        if extra:
            self.out.write(f"# {extra}\n")
        self.out.write("\n")

    def add_box(
        self,
        name: str,
        cx: float, cy: float, cz: float,
        size_x: float, size_y: float, size_z: float,
    ) -> None:
        """Adds an axis-aligned box centered at (cx, cy, cz). cy = height-center."""
        hx = size_x / 2.0
        hy = size_y / 2.0
        hz = size_z / 2.0
        verts = [
            (cx - hx, cy - hy, cz - hz),
            (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy - hy, cz + hz),
            (cx - hx, cy - hy, cz + hz),
            (cx - hx, cy + hy, cz - hz),
            (cx + hx, cy + hy, cz - hz),
            (cx + hx, cy + hy, cz + hz),
            (cx - hx, cy + hy, cz + hz),
        ]
        base = self.vertex_count
        self.out.write(f"o {_safe(name)}\n")
        for v in verts:
            self.out.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        self.vertex_count += 8
        # 6 quads (bottom, top, sides) — OBJ indices are 1-based
        b = base
        faces = [
            (b + 1, b + 2, b + 3, b + 4),  # bottom
            (b + 5, b + 8, b + 7, b + 6),  # top
            (b + 1, b + 5, b + 6, b + 2),  # -z
            (b + 2, b + 6, b + 7, b + 3),  # +x
            (b + 3, b + 7, b + 8, b + 4),  # +z
            (b + 4, b + 8, b + 5, b + 1),  # -x
        ]
        for q in faces:
            self.out.write(f"f {q[0]} {q[1]} {q[2]} {q[3]}\n")
        self.out.write("\n")

    def add_flat_polygon_approx(
        self,
        name: str,
        polygon: Polygon2D,
        z_base: float,
        thickness: float = 0.1,
    ) -> None:
        """Polygon → flat thin box using its bbox (MVP approximation)."""
        xs = [p.x for p in polygon.points]
        ys = [p.y for p in polygon.points]  # JSON y → OBJ z
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(ys), max(ys)
        cx = (min_x + max_x) / 2.0
        cz = (min_z + max_z) / 2.0
        size_x = max(0.01, max_x - min_x)
        size_z = max(0.01, max_z - min_z)
        self.add_box(name, cx, z_base + thickness / 2.0, cz, size_x, thickness, size_z)

    def add_marker_cube(self, name: str, x: float, z: float, y: float = 0.0, size: float = 1.0) -> None:
        self.add_box(name, x, y + size / 2.0, z, size, size, size)

    def text(self) -> str:
        return self.out.getvalue()


def _safe(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_")


# ============================================================
# Public API
# ============================================================

def export(ir: WorldIR | SceneIR) -> str:
    if isinstance(ir, WorldIR):
        return _export_world(ir)
    return _export_scene(ir)


# ============================================================
# World
# ============================================================

def _export_world(world: WorldIR) -> str:
    b = _OBJBuilder()
    b.header(f"World: {world.name}", extra=f"world_id={world.world_id}")

    # World ground plane
    b.add_box(
        "world_ground",
        cx=world.scale.width_m / 2.0,
        cy=-0.05,
        cz=world.scale.depth_m / 2.0,
        size_x=world.scale.width_m,
        size_y=0.1,
        size_z=world.scale.depth_m,
    )

    for d in world.districts:
        b.add_flat_polygon_approx(f"district_{d.id}", d.polygon, z_base=0.05, thickness=0.4)
    for w in world.water_bodies:
        _export_water(b, w)
    for r in world.roads:
        # Roads as thin strips along their bbox
        xs = [p.x for p in r.points]
        ys = [p.y for p in r.points]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(ys), max(ys)
        cx = (min_x + max_x) / 2.0
        cz = (min_z + max_z) / 2.0
        size_x = max(r.width_m, max_x - min_x)
        size_z = max(r.width_m, max_z - min_z)
        b.add_box(f"road_{r.id}", cx, 0.6, cz, size_x, 0.05, size_z)
    for p in world.pois:
        _export_poi(b, p)
    for s in world.scene_slots:
        _export_scene_slot(b, s)

    return b.text()


def _export_water(b: _OBJBuilder, w: WaterBody) -> None:
    xs = [p.x for p in w.polygon.points]
    ys = [p.y for p in w.polygon.points]
    cx = (min(xs) + max(xs)) / 2.0
    cz = (min(ys) + max(ys)) / 2.0
    size_x = max(0.5, max(xs) - min(xs))
    size_z = max(0.5, max(ys) - min(ys))
    b.add_box(f"water_{w.id}", cx, 0.1, cz, size_x, 0.05, size_z)


def _export_poi(b: _OBJBuilder, p: POI) -> None:
    b.add_marker_cube(f"poi_{p.id}", p.position.x, p.position.y, y=1.0, size=4.0)


def _export_scene_slot(b: _OBJBuilder, s: SceneSlot) -> None:
    b.add_box(
        f"slot_{s.id}",
        cx=s.position.x, cy=0.5, cz=s.position.y,
        size_x=s.size.width_m, size_y=0.3, size_z=s.size.depth_m,
    )


# ============================================================
# Scene
# ============================================================

def _export_scene(scene: SceneIR) -> str:
    b = _OBJBuilder()
    b.header(f"Scene: {scene.name}", extra=f"scene_id={scene.scene_id}")

    # Floor
    b.add_box(
        "scene_floor",
        cx=scene.bounds.width_m / 2.0,
        cy=-0.05,
        cz=scene.bounds.depth_m / 2.0,
        size_x=scene.bounds.width_m,
        size_y=0.1,
        size_z=scene.bounds.depth_m,
    )

    for z in scene.zones:
        b.add_flat_polygon_approx(f"zone_{z.id}", z.polygon, z_base=0.05, thickness=0.2)
    for obj in scene.objects:
        sx = obj.size.width_m * obj.transform.scale
        sy = obj.size.height_m * obj.transform.scale
        sz = obj.size.depth_m * obj.transform.scale
        b.add_box(
            f"obj_{obj.id}",
            cx=obj.transform.position.x,
            cy=obj.transform.position.z + sy / 2.0,
            cz=obj.transform.position.y,
            size_x=sx, size_y=sy, size_z=sz,
        )
    for e in scene.entrances:
        b.add_marker_cube(f"ent_{e.id}", e.position.x, e.position.y, y=0.2, size=1.2)
    for m in scene.gameplay_markers:
        b.add_marker_cube(f"mk_{m.id}", m.position.x, m.position.y, y=0.3, size=0.6)

    return b.text()
