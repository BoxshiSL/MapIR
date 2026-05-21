"""Blender Python script exporter.

The generated script uses only `bpy` primitives (cube + scale). Run it from
Blender's Scripting workspace. Materials are colored via the principled BSDF
base color so the blockout is visually parseable.

Coordinate convention (Blender):
    x = JSON x
    y = JSON y   (Blender Y is depth/forward)
    z = height
"""

from __future__ import annotations

import json

from ..core.enums import ZoneType
from ..core.models import (
    Polygon2D,
    SceneIR,
    WorldIR,
)

_SCENE_COLORS = {
    "floor": (0.85, 0.85, 0.83, 1.0),
    "zone_default": (0.78, 0.82, 0.88, 1.0),
    "zone_room": (1.00, 0.95, 0.76, 1.0),
    "zone_storage": (0.96, 0.86, 0.72, 1.0),
    "zone_service": (0.84, 0.91, 1.00, 1.0),
    "zone_combat": (1.00, 0.75, 0.75, 1.0),
    "zone_stealth": (0.83, 0.91, 0.82, 1.0),
    "zone_path": (0.88, 0.88, 0.88, 1.0),
    "zone_danger": (1.00, 0.62, 0.55, 1.0),
    "zone_safe": (0.78, 0.93, 0.78, 1.0),
    "object": (0.70, 0.70, 0.70, 1.0),
    "entrance": (1.00, 0.84, 0.18, 1.0),
    "marker": (0.18, 0.55, 0.79, 1.0),
}

_WORLD_COLORS = {
    "ground": (0.93, 0.92, 0.86, 1.0),
    "district": (0.92, 0.88, 0.80, 1.0),
    "water": (0.55, 0.78, 0.95, 1.0),
    "road": (0.30, 0.30, 0.30, 1.0),
    "poi": (0.78, 0.22, 0.16, 1.0),
    "scene_slot": (0.17, 0.60, 0.36, 1.0),
}

_ZONE_COLOR_KEY = {
    ZoneType.ROOM: "zone_room",
    ZoneType.STORAGE: "zone_storage",
    ZoneType.SERVICE_AREA: "zone_service",
    ZoneType.COMBAT_SPACE: "zone_combat",
    ZoneType.STEALTH_ROUTE: "zone_stealth",
    ZoneType.PATH: "zone_path",
    ZoneType.DANGER_ZONE: "zone_danger",
    ZoneType.SAFE_ZONE: "zone_safe",
    ZoneType.PRIVATE_AREA: "zone_room",
    ZoneType.PUBLIC_AREA: "zone_default",
    ZoneType.EXTERIOR_YARD: "zone_default",
}


# ============================================================
# Public API
# ============================================================


def export(ir: WorldIR | SceneIR) -> str:
    items: list[dict] = []
    if isinstance(ir, WorldIR):
        items, palette, title = _world_items(ir)
    else:
        items, palette, title = _scene_items(ir)
    return _render_script(title=title, palette=palette, items=items)


# ============================================================
# Item generators
# ============================================================


def _world_items(world: WorldIR) -> tuple[list[dict], dict, str]:
    items: list[dict] = []

    items.append(
        _box(
            name="world_ground",
            cx=world.scale.width_m / 2.0,
            cy=world.scale.depth_m / 2.0,
            cz=-0.05,
            sx=world.scale.width_m,
            sy=world.scale.depth_m,
            sz=0.1,
            material="ground",
        )
    )

    for d in world.districts:
        items.append(
            _box_from_polygon(
                f"district_{d.id}", d.polygon, height=0.4, z_base=0.05, material="district"
            )
        )
    for w in world.water_bodies:
        items.append(
            _box_from_polygon(f"water_{w.id}", w.polygon, height=0.1, z_base=0.05, material="water")
        )
    for r in world.roads:
        xs = [p.x for p in r.points]
        ys = [p.y for p in r.points]
        items.append(
            _box(
                name=f"road_{r.id}",
                cx=(min(xs) + max(xs)) / 2.0,
                cy=(min(ys) + max(ys)) / 2.0,
                cz=0.5,
                sx=max(r.width_m, max(xs) - min(xs)),
                sy=max(r.width_m, max(ys) - min(ys)),
                sz=0.05,
                material="road",
            )
        )
    for p in world.pois:
        items.append(
            _box(
                name=f"poi_{p.id}",
                cx=p.position.x,
                cy=p.position.y,
                cz=2.0,
                sx=5.0,
                sy=5.0,
                sz=4.0,
                material="poi",
            )
        )
    for s in world.scene_slots:
        items.append(
            _box(
                name=f"slot_{s.id}",
                cx=s.position.x,
                cy=s.position.y,
                cz=0.4,
                sx=s.size.width_m,
                sy=s.size.depth_m,
                sz=0.3,
                material="scene_slot",
            )
        )

    return items, _WORLD_COLORS, f"World: {world.name}"


def _scene_items(scene: SceneIR) -> tuple[list[dict], dict, str]:
    items: list[dict] = []

    items.append(
        _box(
            name="scene_floor",
            cx=scene.bounds.width_m / 2.0,
            cy=scene.bounds.depth_m / 2.0,
            cz=-0.05,
            sx=scene.bounds.width_m,
            sy=scene.bounds.depth_m,
            sz=0.1,
            material="floor",
        )
    )

    for z in scene.zones:
        items.append(
            _box_from_polygon(
                f"zone_{z.id}",
                z.polygon,
                height=0.15,
                z_base=0.05,
                material=_ZONE_COLOR_KEY.get(z.zone_type, "zone_default"),
            )
        )
    for obj in scene.objects:
        sx = obj.size.width_m * obj.transform.scale
        sy = obj.size.depth_m * obj.transform.scale
        sz = obj.size.height_m * obj.transform.scale
        items.append(
            _box(
                name=f"obj_{obj.id}",
                cx=obj.transform.position.x,
                cy=obj.transform.position.y,
                cz=obj.transform.position.z + sz / 2.0,
                sx=sx,
                sy=sy,
                sz=sz,
                material="object",
            )
        )
    for e in scene.entrances:
        items.append(
            _box(
                name=f"ent_{e.id}",
                cx=e.position.x,
                cy=e.position.y,
                cz=0.6,
                sx=1.2,
                sy=1.2,
                sz=1.2,
                material="entrance",
            )
        )
    for m in scene.gameplay_markers:
        items.append(
            _box(
                name=f"mk_{m.id}",
                cx=m.position.x,
                cy=m.position.y,
                cz=0.4,
                sx=0.6,
                sy=0.6,
                sz=0.6,
                material="marker",
            )
        )

    return items, _SCENE_COLORS, f"Scene: {scene.name}"


def _box_from_polygon(
    name: str,
    polygon: Polygon2D,
    height: float,
    z_base: float,
    material: str,
) -> dict:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    sx = max(0.01, max(xs) - min(xs))
    sy = max(0.01, max(ys) - min(ys))
    return _box(
        name=name,
        cx=cx,
        cy=cy,
        cz=z_base + height / 2.0,
        sx=sx,
        sy=sy,
        sz=height,
        material=material,
    )


def _box(
    *, name: str, cx: float, cy: float, cz: float, sx: float, sy: float, sz: float, material: str
) -> dict:
    return {
        "name": _safe(name),
        "center": [cx, cy, cz],
        "size": [sx, sy, sz],
        "material": material,
    }


def _safe(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_")


# ============================================================
# Script template
# ============================================================

_TEMPLATE = '''"""Auto-generated by MapIR. Run inside Blender (Scripting workspace).

Title: {title}
"""

import bpy

PALETTE = {palette!s}
ITEMS = {items!s}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection_attr in ("meshes", "materials", "cameras", "lights"):
        coll = getattr(bpy.data, collection_attr)
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


_material_cache = {{}}


def get_material(key):
    if key in _material_cache:
        return _material_cache[key]
    color = PALETTE.get(key, (0.5, 0.5, 0.5, 1.0))
    mat = bpy.data.materials.new(name="mat_" + key)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
    _material_cache[key] = mat
    return mat


def add_box(name, center, size, material_key):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(get_material(material_key))


def main():
    clear_scene()
    for item in ITEMS:
        add_box(item["name"], tuple(item["center"]), tuple(item["size"]), item["material"])
    # Frame the result
    bpy.ops.object.select_all(action="SELECT")
    try:
        bpy.ops.view3d.camera_to_view_selected()
    except RuntimeError:
        pass


if __name__ == "__main__":
    main()
'''


def _render_script(title: str, palette: dict, items: list[dict]) -> str:
    # json.dumps gives a Python-literal-compatible representation for our simple data
    return _TEMPLATE.format(
        title=title,
        palette=_format_palette(palette),
        items=json.dumps(items, ensure_ascii=False),
    )


def _format_palette(palette: dict) -> str:
    # Build a literal Python dict mapping string -> tuple
    parts = ["{"]
    for k, v in palette.items():
        parts.append(f'    "{k}": ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}, {v[3]:.4f}),')
    parts.append("}")
    return "\n".join(parts)
