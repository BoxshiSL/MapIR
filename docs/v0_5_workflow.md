# MapIR v0.5 workflow

v0.5 replaces the v0.4 "open a JSON, read tables, export" loop with a guided
**Template → Sketch → Generate → Validate → Export** workflow.

```
+----------+    +----------+    +----------+    +-----------+    +--------+
| Template | -> |  Sketch  | -> | Generate | -> | Validate  | -> | Export |
+----------+    +----------+    +----------+    +-----------+    +--------+
       \           |  ^           |   ^           |
        \          |  |           |   |           |
         +---------+  +-----------+   +-----------+
              (iterate — the Sketch is the source of truth)
```

## 1. Template

`MapIR Studio` opens at **Home** with three big creation cards:

* **New World** — full template gallery filtered to World templates.
* **New Scene** — Scene templates.
* **New Interior** — Interior templates (SceneIR subtype).

Clicking any of these (or **New / Templates** in the sidebar) launches the
**New Project Wizard**:

1. Document type (World / Scene / Interior).
2. Template choice (13 neutral templates, filterable by genre + gameplay
   profile).
3. Size & gameplay profiles (defaults from the template).
4. Theme & worldbuilding brief.
5. Local LLM (provider / model / temperature; Mock is always available).

`Create` produces a fresh `SketchDocument` and a starter IR snapshot.

## 2. Sketch

The **Canvas** page (Phase A: read-only preview of the seeded sketch; Phase
B will ship interactive sketch tools) and the **Districts** page give you a
view of:

* district polygons,
* roads, POIs, scene slots,
* per-district fields (type, role, density, height profile, gameplay
  profile, local LLM brief — read-only in Phase A, editable in Phase B).

The sketch lives separately from validated IR — editing the sketch does
*not* mutate IR until you regenerate.

## 3. Generate

The **Generation** page runs the deterministic v0.5 pipeline:

| Stage          | Output                                                |
|----------------|-------------------------------------------------------|
| `zoning`       | districts from sketch                                 |
| `roads`        | arterial / collector / local / alley / service / path |
| `parcels`      | rectangular parcels inside districts                  |
| `buildings`    | building footprints inside parcels                    |
| `landmarks`    | one anchor per major district                         |
| `scene_slots`  | ≥ 1 slot per major district                            |
| `guidance`     | leading lines, breadcrumbs, vista cues                |
| `convert_to_ir`| materialises WorldIR / SceneIR                        |
| `validate`     | structural + design-aware                             |

Each stage is toggleable; `Run All` runs every enabled stage. The pipeline
is fully deterministic — same sketch ⇒ same output.

## 4. Validate

The **Validation** page surfaces:

* the v0.4 structural validators (Pydantic + semantic rules in
  `mapir/core/validation.py`),
* the v0.5 design validators
  (`mapir/design/validators.run_design_validators`) — connectivity,
  gameplay metrics, readability, district identity, geometry.

Each finding cites a rule id from `guides/design_rules.json`.

## 5. Export

The **Export** page now offers:

* SVG, OBJ, and Blender Python script (as in v0.4),
* **SketchLayer JSON** (the `SketchDocument`),
* **GeneratedLayout JSON** (parcels, buildings, landmarks, guidance cues),
* **Design Report (Markdown)** — bundles structural + design findings,
  cites rule ids.

No UE5 / Unity / GLB / FBX in v0.5.

## CLI mirror

```bat
python -m mapir.cli templates
python -m mapir.cli new-from-template world_modern_island_city --out sketch.json
python -m mapir.cli generate-layout sketch.json --out layout.json
python -m mapir.cli validate examples\demos\demo_world_modern_island_city.json
python -m mapir.cli validate-design examples\demos\demo_world_modern_island_city.json --layout layout.json
python -m mapir.cli export-design-report examples\demos\demo_world_modern_island_city.json --out report.md --layout layout.json
python -m mapir.cli render-svg examples\demos\demo_world_modern_island_city.json --out preview.svg
```

## Known gaps in v0.5

* Interactive sketch tools (polygon, road, POI, scene slot) on the Canvas
  page are scaffolded but not yet hooked up — the Canvas page renders the
  current sketch read-only.
* District Inspector fields are read-only in Phase A; editing arrives in
  Phase B.
* No real polygon clipping (rect-only).
* No UE5 / Unity / asset import.
* Local LLM is still optional and Mock-only on CI.
