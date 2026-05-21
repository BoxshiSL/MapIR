<div align="center">

# MapIR

**A typed intermediate representation for game spaces — author once, validate, preview, export.**

*Worlds (cities, regions, islands) and Scenes (alleys, warehouses, yards) as
versionable JSON. Pydantic-validated, SVG-previewed, blockout-exportable, and
browsable from a small desktop UI.*

[![Version](https://img.shields.io/badge/version-0.2.0-1f6feb.svg?style=flat-square)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-17%20passing-3fb950.svg?style=flat-square)](tests/)
[![Pydantic](https://img.shields.io/badge/pydantic-v2-e92063.svg?style=flat-square)](https://docs.pydantic.dev/)
[![CLI](https://img.shields.io/badge/cli-typer-009485.svg?style=flat-square)](https://typer.tiangolo.com/)
[![UI](https://img.shields.io/badge/ui-tkinter-6e6e6e.svg?style=flat-square)](https://docs.python.org/3/library/tkinter.html)
[![License](https://img.shields.io/badge/license-Proprietary-c0392b.svg?style=flat-square)](pyproject.toml)

</div>

---

## TL;DR

```bat
install.bat              :: one-time setup
validate_examples.bat    :: structural + semantic checks
render_examples.bat      :: SVG previews into output\svg\
export_blockout_examples.bat   :: OBJ + Blender blockouts
run_ui.bat               :: open the desktop browser
```

Five batch files, one CLI, one window. No cloud, no LLM, no engine plugin —
that's later. This is the **data + tooling foundation** everything else stands on.

---

## Table of contents

- [Why MapIR](#why-mapir)
- [What's new in v0.2](#whats-new-in-v02)
- [Two modes: World and Scene](#two-modes-world-and-scene)
- [Quick start](#quick-start)
- [The desktop UI](#the-desktop-ui)
- [CLI reference](#cli-reference)
- [Architecture](#architecture)
- [Validation rules](#validation-rules)
- [Bundled examples](#bundled-examples)
- [What v0.2 does NOT do](#what-v02-does-not-do)
- [Roadmap](#roadmap)
- [Development](#development)
- [License](#license)

---

## Why MapIR

Game-space tooling tends to fork into two extremes: opaque editor binaries on
one end, ad-hoc level scripts on the other. MapIR sits in between as a small,
typed, file-on-disk **Intermediate Representation** for spaces. You can:

- **Author** worlds and scenes as JSON (or generate them — that's the v0.3+
  story);
- **Validate** them structurally (pydantic v2) and semantically (unique IDs,
  bounds containment, role consistency, constraint engine);
- **Preview** them as 2D SVG or in a local desktop window;
- **Export** them as a 3D blockout for orientation in Blender or any OBJ
  viewer;
- **Diff and version** them with plain `git`, because they're text.

The point of v0.2 is to be solid enough that the AI / procedural / asset /
engine layers have something stable to talk to.

---

## What's new in v0.2

| Area | Change |
| --- | --- |
| **Desktop UI** | Standalone Tkinter window: example tree, 2D preview, summary, validation, one-click exports. Zero new dependencies. |
| **CI** | GitHub Actions runs `pytest` and validates every bundled example on every push and PR. |
| **Version safety net** | A test asserts `pyproject.toml`, `mapir.__version__` and `README.md` agree on the current version. |
| **CLI** | New `mapir.cli ui [--no-browser]` subcommand. `--no-browser` is a headless smoke mode for CI. |

---

## Two modes: World and Scene

|  | **WorldIR** | **SceneIR** |
| --- | --- | --- |
| **Scale** | Cities, regions, islands | Alleys, yards, warehouses, rooms |
| **Holds** | Districts · Roads · Water bodies · POIs · Scene slots | Zones · Entrances · Paths · Objects · Gameplay markers |
| **Bounds** | `Size2D` (`width_m × depth_m`) | `SceneBounds` (`w × d × h`) |
| **Standalone?** | Yes | Yes — *or* fills a `scene_slot` from a World |
| **Discriminator** | `"ir_type": "world"` | `"ir_type": "scene"` |

A **scene slot** in a World is a labelled spot ("here will live an alley")
that a future SceneIR can be embedded into. v0.2 stores the link as a marker;
the actual transform-in-engine embedding is on the roadmap.

---

## Quick start

> **Requires:** Python **3.11+** on `PATH`. Windows is the primary target;
> macOS / Linux work with the CLI and tests — the `.bat` launchers are
> Windows-only, but the equivalent commands are obvious.

### Windows

```bat
cd /d "H:\BLUME PROJECTS\MapIR"
install.bat
```

That's it for setup. Then any of:

```bat
validate_examples.bat            :: validates every example JSON
render_examples.bat              :: writes output\svg\*.svg
export_blockout_examples.bat     :: writes output\obj\*.obj + output\blender\*.py
run_ui.bat                       :: opens the desktop UI
```

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m mapir.cli render-svg examples/scenes/scene_urban_alley.json \
    --out output/svg/scene_urban_alley.svg
python -m mapir.cli ui                  # needs python3-tk on Linux
```

### Run the test suite

```bash
.venv\Scripts\python.exe -m pytest -q   # Windows
python -m pytest -q                     # *nix
```

---

## The desktop UI

```
+--------------------------------------------------------------+
| MapIR  v0.2  — local preview of WorldIR / SceneIR examples   |
+-----------------+--------------------------------------------+
| Examples        |                                            |
|  Worlds         |                                            |
|   jisso_city    |          [ 2D Canvas preview ]             |
|   luga_region   |                                            |
|  Scenes         |                                            |
|   urban_alley   +--------------------------------------------+
|   warehouse     | Summary               | Validation         |
|   port_yard     | Type: scene           | OK — no issues     |
|                 | Zones: 5              |                    |
|                 | Entrances: 3          |                    |
|                 +--------------------------------------------+
|                 | [Save SVG] [Export OBJ] [Export Blender]   |
+-----------------+--------------------------------------------+
```

- Built with **stdlib tkinter only** — no Flask, no Electron, no pywebview.
- Palette and element ordering **mirror the SVG renderer**, so the desktop
  view reads the same as the exported `.svg`.
- The UI is **read-only**. Editing JSON in the UI is a v0.3 candidate.
- `mapir.cli ui --no-browser` builds the window, renders once, exits with
  code 0 — used by the CI smoke test and on display-less machines.

---

## CLI reference

All commands infer the IR type from the JSON `ir_type` field.

| Command | Purpose |
| --- | --- |
| `mapir.cli validate <ir.json>` | Structural + semantic + constraint validation. Exits non-zero on errors. |
| `mapir.cli inspect <ir.json>` | Quick summary table (type, counts, validation status). |
| `mapir.cli render-svg <ir.json> --out file.svg` | 2D preview as standalone SVG (browser-viewable, no deps). |
| `mapir.cli export-obj <ir.json> --out file.obj` | Wavefront OBJ blockout. |
| `mapir.cli export-blender <ir.json> --out file.py` | Self-contained `bpy` script. Run from Blender → Scripting → Run Script. |
| `mapir.cli ui [--no-browser]` | Launch the desktop UI. `--no-browser` is a headless smoke mode. |

<details>
<summary><b>Example invocations</b></summary>

```bat
python -m mapir.cli inspect        examples\worlds\world_jisso_city.json
python -m mapir.cli validate       examples\scenes\scene_urban_alley.json
python -m mapir.cli render-svg     examples\scenes\scene_urban_alley.json     --out output\svg\scene_urban_alley.svg
python -m mapir.cli export-obj     examples\scenes\scene_urban_alley.json     --out output\obj\scene_urban_alley.obj
python -m mapir.cli export-blender examples\scenes\scene_warehouse_interior.json --out output\blender\scene_warehouse_interior.py
```
</details>

---

## Architecture

```
                +--------------------+
                |   *.json IR file   |
                | world  /  scene    |
                +---------+----------+
                          |
                          v
              +-----------------------+
              |  pydantic v2 models   |   <- mapir/core/models.py
              |  (structural check)   |
              +-----------+-----------+
                          |
                          v
       +------------------+-------------------+
       |     semantic + constraint engine     |   <- mapir/core/validation.py
       +------------------+-------------------+
                          |
   +----------------------+-------------------+--------------------+
   |                      |                                        |
   v                      v                                        v
+---------+        +----------+        +-----------------+  +-----------------+
|  SVG    |        |   OBJ    |        | Blender script  |  |   Desktop UI    |
| (2D)    |        | blockout |        |    (.py / bpy)  |  |  (tkinter)      |
+---------+        +----------+        +-----------------+  +-----------------+
output/svg/*.svg   output/obj/*.obj    output/blender/*.py     mapir.cli ui
```

**File map:**

| Path | Role |
| --- | --- |
| [`mapir/core/models.py`](mapir/core/models.py) | Single source of truth — all data shapes (pydantic v2). |
| [`mapir/core/enums.py`](mapir/core/enums.py) | String-valued enums; JSON round-trips cleanly. |
| [`mapir/core/validation.py`](mapir/core/validation.py) | Semantic checks + constraint engine. |
| [`mapir/core/geometry.py`](mapir/core/geometry.py) | bbox / containment / overlap helpers. |
| [`mapir/utils/io.py`](mapir/utils/io.py) | `load_ir(path)` — reads JSON and dispatches by `ir_type`. |
| [`mapir/render/svg_renderer.py`](mapir/render/svg_renderer.py) | Hand-rolled SVG for World and Scene. |
| [`mapir/export/obj_exporter.py`](mapir/export/obj_exporter.py) | Minimal OBJ blockout. |
| [`mapir/export/blender_exporter.py`](mapir/export/blender_exporter.py) | Self-contained Blender Python script. |
| [`mapir/cli.py`](mapir/cli.py) | `typer`-based command line. |
| [`mapir/ui/`](mapir/ui/) | Tkinter UI — `app.py`, `canvas_renderer.py`, `widgets.py`. |
| [`mapir/schemas/`](mapir/schemas/) | Human-readable JSON-Schema reference docs. |
| [`examples/`](examples/) | Worlds, scenes, asset registry. |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions: pytest + example validation. |

The pydantic models are the source of truth; the JSON schemas are written for
humans (IDE / editor autocomplete) and are not used at runtime.

---

## Validation rules

### Structural

Done by pydantic v2 when the model is constructed: required fields, types,
positive sizes, polygons with ≥3 points, paths/roads with ≥2 points, frozen
schemas (`extra="forbid"`).

### Semantic

- Unique IDs across the file (districts, roads, water bodies, POIs, scene
  slots; or zones, entrances, paths, objects, markers).
- Bounds containment — every polygon / point sits inside its parent bounds.
- Interior vs exterior consistency between `scene_type` and `zone_type`.
- Scene-slot district references resolve (when set).
- Object footprints are inside scene bounds.

### Constraint engine

| Constraint | Behaviour |
| --- | --- |
| `must_have_min_entrances` | Scene has ≥ `params.min` entrances. |
| `must_have_min_escape_routes` | Scene has ≥ `params.min` paths of type `escape_route`. |
| `must_have_min_cover_markers` | Scene has ≥ `params.min` markers of type `cover`. |
| `must_have_scene_slot` | World has ≥ `params.min` scene slots (optionally of a given type). |
| `must_be_inside_bounds` | Targeted entity sits inside world / scene bounds. |
| `must_not_overlap` | Two entities' axis-aligned bboxes do not overlap. *(Rotation is stored but ignored — see [limitations](#what-v02-does-not-do).)* |
| *unsupported* | Reported as a `warning`, never a hard `error`. |

---

## Bundled examples

### Worlds

| File | Scope |
| --- | --- |
| [`examples/worlds/world_jisso_city.json`](examples/worlds/world_jisso_city.json) | **Jisso City.** Compact open-world city — districts KIU, Sotonbori, Kita Central, Kurogane, Aobadai, Seihama, Takamine, Minato Bay Port, and offshore KIX Airport Island. Canals, harbour, sea, KIX bridge, six scene slots. |
| [`examples/worlds/world_luga_region.json`](examples/worlds/world_luga_region.json) | **Luga region.** Coastal-forest area with a village, port edge, swamp, forest belt, observation hill, and a restricted facility. |

### Scenes

| File | What it shows |
| --- | --- |
| [`examples/scenes/scene_urban_alley.json`](examples/scenes/scene_urban_alley.json) | Exterior Sotonbori backstreet — 3 entrances, 2 escape routes, 5+ cover markers. |
| [`examples/scenes/scene_warehouse_interior.json`](examples/scenes/scene_warehouse_interior.json) | Interior Minato Bay warehouse — storage aisles, office corner, vault, emergency exit. |
| [`examples/scenes/scene_port_yard.json`](examples/scenes/scene_port_yard.json) | Exterior container yard — stealth route through the stacks and a crane landmark. |

### Assets

| File | Purpose |
| --- | --- |
| [`examples/assets/asset_registry_basic.json`](examples/assets/asset_registry_basic.json) | ~10 representative entries spanning buildings, props, walls, containers, doors, stairs, vegetation, landmarks. Parses today; **not yet referenced from scenes** (v0.3+). |

> After `render_examples.bat`, open `output/svg/*.svg` in any browser to see
> these examples drawn out.

---

## What v0.2 does NOT do

| Feature | Status |
| --- | --- |
| LLM / prompt-to-IR | not yet |
| Sketch-to-IR (image → polygons) | not yet |
| Procedural generation (PCG, World Partition) | not yet |
| Marketplace asset import or real asset placement | not yet |
| UE5 exporter (Levels) / Unity exporter | not yet |
| Mission generator / gameplay AI / final-art pass | not yet |
| Editing JSON inside the UI | not yet (read-only by design) |
| Rotation-aware overlap checks | not yet (bboxes are axis-aligned) |
| Scene-slot → embedded transform (in-engine) | marker only |
| Authentication / backend / cloud sync | **explicitly out of scope** |

> [!IMPORTANT]
> **Blockout only.** OBJ and Blender exports are for **visual orientation**.
> Polygons that are not axis-aligned rectangles **collapse to their bounding
> box** during blockout export. Do not ship this geometry to players.

---

## Roadmap

### v0.3 — make the UI useful

- [ ] Drag-and-drop a JSON file onto the window.
- [ ] Open recent files / file picker.
- [ ] Light editing: rename, toggle constraints, add markers, move objects.
- [ ] PyInstaller `.exe` so the UI runs without a Python install.
- [ ] 3D preview of the blockout inside the canvas (OpenGL or rasterised OBJ).
- [ ] Asset registry browser tab.

### Later

- [ ] Prompt-to-IR (LLM-driven authoring).
- [ ] Sketch-to-IR (raster sketch → polygons).
- [ ] Procedural generation for districts and interior room graphs.
- [ ] Real asset placement (asset registry wired into scenes).
- [ ] UE5 exporter (Levels / PCG-friendly).
- [ ] World → Scene embedding with a real transform.
- [ ] Gameplay-aware layout validation (LOS, cover graphs, patrol coverage).
- [ ] Mission integration.

---

## Development

### Running tests

```bash
.venv\Scripts\python.exe -m pytest -q
```

```text
17 passed in 0.6s
```

### Continuous integration

Every push and pull request to `main` runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

1. Install Python 3.11 + `python3-tk`.
2. `pip install -e ".[dev]"`.
3. `pytest -q`.
4. `mapir.cli validate` over every bundled example.

### Project layout

```
MapIR/
├── mapir/                 # the package
│   ├── core/              # models, enums, validation, geometry
│   ├── render/            # SVG renderer
│   ├── export/            # OBJ + Blender exporters
│   ├── ui/                # Tkinter desktop UI (v0.2)
│   ├── utils/             # io helpers
│   ├── schemas/           # JSON-Schema reference docs
│   └── cli.py             # typer CLI entry point
├── examples/              # worlds, scenes, assets
├── tests/                 # pytest suite
├── output/                # rendered SVG / OBJ / Blender artefacts
├── .github/workflows/     # CI
├── pyproject.toml
├── requirements.txt
├── install.bat
├── validate_examples.bat
├── render_examples.bat
├── export_blockout_examples.bat
└── run_ui.bat
```

### Contributing

This is currently an internal foundation, not an open-contribution project.
If you do open a PR:

- Keep the IR models the single source of truth.
- Add or update a test for every new validator or exporter rule.
- Do not introduce a new runtime dependency without a strong reason.
  v0.2's UI is stdlib-only on purpose.

---

## License

Proprietary — see [`pyproject.toml`](pyproject.toml). Internal BLUME project.
