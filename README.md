# MapIR

**MapIR** is a tool for generating, describing, validating, and exporting game spaces.

It works in two modes:

- **World Mode** — large worlds, cities, regions, islands. A WorldIR holds
  districts, roads, water bodies, points of interest, and *scene slots*:
  pre-marked spots where smaller scenes can later be embedded.
- **Scene Mode** — small locations or interiors: alleys, yards, warehouses,
  offices, apartments. A SceneIR can stand on its own *or* fill a scene slot
  from a WorldIR.

This repository is the **MVP foundation**. It is intentionally not a generator.
It builds the underlying data, validation, preview, and blockout export layers
so the later AI / procedural / asset / engine layers have something to talk to.

---

## What the MVP can do

- Read and validate `WorldIR` and `SceneIR` JSON files.
  - Structural validation via pydantic v2.
  - Semantic validation: unique IDs, bounds containment, role checks,
    interior/exterior consistency, scene-slot district references, etc.
  - A small constraints engine that enforces:
    - `must_have_min_entrances`
    - `must_have_min_escape_routes`
    - `must_have_min_cover_markers`
    - `must_have_scene_slot`
    - `must_be_inside_bounds`
    - `must_not_overlap` (axis-aligned bbox; ignores rotation)
  - Unsupported constraints are reported as warnings, not errors.
- Render a 2D SVG preview of a world or scene (browser-viewable, no deps).
- Export a simple 3D blockout as either:
  - a Wavefront `.obj` file, or
  - a Blender `.py` script that builds the same blockout with `bpy`.
- Inspect a file from the command line (counts, names, validation summary).
- Run all of the above on the bundled examples.

## What the MVP does NOT do (yet)

- No UI, no web app.
- No LLM, prompt parsing, or sketch parsing.
- No marketplace asset import or real asset placement.
- No UE5 / Unity exporter.
- No procedural generation, no World Partition, no PCG hooks.
- No mission generator, no final-art pass.

Polygons that are not axis-aligned rectangles are **collapsed to their bounding
box** during blockout export. The OBJ/Blender output is for visual orientation
only — not production geometry.

---

## Architecture

```
+----------------+        +---------------+        +----------------+
|   *.json IR    |  --->  |   pydantic    |  --->  |  semantic +    |
|  world / scene |        |    models     |        |  constraint    |
+----------------+        +---------------+        |  validation    |
                                                   +----------------+
                                                          |
                              +---------------------------+--------------------+
                              v                           v                    v
                       SVG renderer            OBJ exporter         Blender script
                       (output/svg/*.svg)      (output/obj/*.obj)   (output/blender/*.py)
```

- `mapir/core/models.py` — single source of truth for all data shapes.
- `mapir/core/enums.py` — string enums for clean JSON round-trip.
- `mapir/core/validation.py` — structural + semantic + constraint checks.
- `mapir/core/geometry.py` — bbox / containment / overlap helpers.
- `mapir/utils/io.py` — `load_ir(path)` reads JSON and dispatches by `ir_type`.
- `mapir/render/svg_renderer.py` — hand-rolled SVG for World and Scene.
- `mapir/export/obj_exporter.py` — minimal OBJ blockout.
- `mapir/export/blender_exporter.py` — self-contained Blender Python script.
- `mapir/cli.py` — `typer`-based command line; `python -m mapir.cli ...`.
- `mapir/schemas/*.schema.json` — human-readable JSON-Schema reference docs.
- `examples/` — worlds, scenes, and a small asset registry.

The IR model files are the source of truth; the JSON schemas are written for
humans (IDE / editor autocomplete) and are not used at runtime.

---

## Quick start (Windows)

Requires Python 3.11 or newer on `PATH`.

```bat
cd /d "H:\BLUME PROJECTS\MapIR"
install.bat
validate_examples.bat
render_examples.bat
export_blockout_examples.bat
```

`install.bat` creates `.venv`, installs the dependencies, and editable-installs
the package. The other three drive the CLI over every example file and write
their results into `output\`.

To run the test suite:

```bat
.venv\Scripts\python.exe -m pytest -q
```

---

## CLI reference

All commands work with either `WorldIR` or `SceneIR` files; the type is
inferred from the JSON `ir_type` field.

```text
python -m mapir.cli validate        <path-to-ir.json>
python -m mapir.cli render-svg      <path-to-ir.json> --out output\svg\<name>.svg
python -m mapir.cli export-obj      <path-to-ir.json> --out output\obj\<name>.obj
python -m mapir.cli export-blender  <path-to-ir.json> --out output\blender\<name>.py
python -m mapir.cli inspect         <path-to-ir.json>
```

Examples:

```bat
python -m mapir.cli inspect       examples\worlds\world_jisso_city.json
python -m mapir.cli validate      examples\scenes\scene_urban_alley.json
python -m mapir.cli render-svg    examples\scenes\scene_urban_alley.json --out output\svg\scene_urban_alley.svg
python -m mapir.cli export-obj    examples\scenes\scene_urban_alley.json --out output\obj\scene_urban_alley.obj
python -m mapir.cli export-blender examples\scenes\scene_warehouse_interior.json --out output\blender\scene_warehouse_interior.py
```

Open the SVG in any browser, the OBJ in any 3D viewer (Blender, Windows 3D
Viewer, etc.), and run the Blender script from Blender's *Scripting* workspace
(Open → Run Script).

---

## Examples shipped with the project

Worlds:

- `examples/worlds/world_jisso_city.json` — Jisso City. Compact open-world city
  with the districts KIU, Sotonbori, Kita Central, Kurogane, Aobadai, Seihama,
  Takamine, Minato Bay Port, and the offshore KIX Airport Island. Includes
  canal water, harbor, sea, a KIX bridge, and six scene slots.
- `examples/worlds/world_luga_region.json` — coastal-forest region with a
  village, port edge, swamp, forest belt, observation hill, and a restricted
  facility.

Scenes:

- `examples/scenes/scene_urban_alley.json` — exterior Sotonbori backstreet:
  3 entrances, 2 escape routes, 5+ cover markers.
- `examples/scenes/scene_warehouse_interior.json` — interior Minato Bay
  warehouse: storage aisles, office corner, vault, emergency exit.
- `examples/scenes/scene_port_yard.json` — exterior container yard with
  stealth route through the stacks and a crane landmark.

Assets:

- `examples/assets/asset_registry_basic.json` — ~10 representative entries
  spanning buildings, props, walls, containers, doors, stairs, vegetation,
  and landmarks. (Read-only in this MVP; not yet referenced from scenes.)

---

## Roadmap (post-MVP)

- Prompt-to-IR (LLM-driven authoring).
- Sketch-to-IR (image → polygons).
- Procedural generation for districts and interior room graphs.
- Asset registry UI and real asset placement.
- UE5 exporter (Levels / PCG-friendly).
- World → Scene embedding (place a SceneIR into a scene slot, in-engine).
- Gameplay-aware layout validation (line-of-sight, cover graphs).
- Mission integration.

---

## Limitations of this MVP (read before complaining)

- **Blockout only.** OBJ and Blender exports are for orientation. Non-rect
  polygons collapse to their bounding box.
- **No art pass.** No textures, no real materials, no lighting design.
- **No AI layer.** No LLM, no prompt parsing, no auto-generation.
- **No real asset placement.** The asset registry parses but is not yet wired
  into scenes.
- **Geometry math is 2D-axis-aligned.** Object rotation is stored but ignored
  by overlap and bounds checks.
- **Scene-slot ↔ Scene embedding is a marker, not a transform.** The scene
  slot references its parent in the scene JSON; the world doesn't pull the
  scene in yet.

These are all on the roadmap. The point of this version is to make the data
and tooling solid enough that the next layer has nothing to argue with.
