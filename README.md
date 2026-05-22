<div align="center">

# MapIR

**Guided desktop tool for designing game worlds, scenes, and interiors —
templates, sketch canvas, gameplay-aware generation, local LLM, validation,
2D preview, and blockout export.**

*Worlds (modern cities, magical forests, rural compounds, dense urban districts)
and Scenes (ports, alleys, checkpoints, rooftops) and Interiors (warehouses,
clubs, offices, apartments) — sketched on a canvas, generated deterministically,
validated structurally and against gameplay-aware design rules, exported to
SVG / OBJ / Blender.*

[![Version](https://img.shields.io/badge/version-0.5.0-7c5cff.svg?style=flat-square)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078d6.svg?style=flat-square&logo=windows&logoColor=white)](#)
[![UI](https://img.shields.io/badge/UI-PySide6-41cd52.svg?style=flat-square&logo=qt&logoColor=white)](https://wiki.qt.io/Qt_for_Python)
[![CLI](https://img.shields.io/badge/CLI-typer-009485.svg?style=flat-square)](https://typer.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/pydantic-v2-e92063.svg?style=flat-square)](https://docs.pydantic.dev/)
[![Build](https://img.shields.io/badge/build-PyInstaller-fbb040.svg?style=flat-square)](https://pyinstaller.org/)
[![Status](https://img.shields.io/badge/status-MVP-success.svg?style=flat-square)](#what-mapir-is-not-yet)

</div>

---

## TL;DR

```bat
install.bat              :: one-time setup (creates .venv, installs everything)
run_desktop.bat          :: launch MapIR Studio (PySide6 window)
validate_examples.bat    :: structural + design checks on bundled demos
render_examples.bat      :: SVG previews into output\svg\
export_blockout_examples.bat :: OBJ + Blender scripts into output\
preflight.bat            :: scan the repo for regressions
build_exe.bat            :: package MapIR Studio.exe via PyInstaller
```

Single Python project. One CLI. One PySide6 window. One PyInstaller spec.
v0.5 turns MapIR into a **guided creation tool**: New Project Wizard with a
neutral template gallery, sketch canvas, District Inspector with per-district
gameplay profiles and local LLM briefs, deterministic generation pipeline
(roads → parcels → buildings → landmarks → scene slots → guidance), curated
design rules, and gameplay-aware validators. Local LLM stays local — no
cloud APIs, no API keys, no auto-downloads.

---

## Table of contents

- [Why MapIR](#why-mapir)
- [What's new in v0.5](#whats-new-in-v05)
- [The v0.5 workflow](#the-v05-workflow)
- [Three document modes: World, Scene, Interior](#three-document-modes-world-scene-interior)
- [Quick start (Windows)](#quick-start-windows)
- [The desktop app](#the-desktop-app)
- [CLI reference](#cli-reference)
- [Architecture](#architecture)
- [Templates](#templates)
- [Gameplay metrics and design rules](#gameplay-metrics-and-design-rules)
- [Validation](#validation)
- [Local LLM drafting](#local-llm-drafting)
- [Building the exe](#building-the-exe)
- [What MapIR is not yet](#what-mapir-is-not-yet)
- [Roadmap](#roadmap)
- [Development](#development)
- [License](#license)

---

## Why MapIR

Game-space tooling tends to fork into two extremes: opaque editor binaries on
one end, ad-hoc level scripts on the other. MapIR sits in between as a small,
typed, file-on-disk **Intermediate Representation** for spaces, wrapped in a
guided desktop tool.

In v0.5 you:

- Pick a **neutral template** (GTA-like island city, medieval magical forest,
  rural compound, dense cyberpunk district, industrial port, urban alley,
  warehouse interior, …).
- Sketch districts, roads, POIs, and scene slots on a **canvas**.
- Configure each district in the **District Inspector** — district type,
  density, height profile, road pattern, gameplay profile (driving, stealth,
  shooter/cover, parkour/climbing, exploration), local LLM brief.
- Run the **generation pipeline**: deterministic generators turn the sketch
  into roads, parcels, building footprints, landmarks, scene slots, and
  guidance cues. The local LLM produces semantic plans, never raw geometry.
- **Validate** with structural rules (the v0.4 engine) plus new
  design-aware rules (connectivity, gameplay metrics, readability, district
  identity, geometry).
- **Export** SVG, OBJ, Blender Python, the SketchLayer JSON, the
  GeneratedLayout JSON, and a Markdown design report.

The format is still text-first, diff-friendly, and engine-agnostic.

---

## What's new in v0.5

This is the **UX + Canvas + Gameplay-Aware Zoning** release.

- 🧭 **New Project Wizard + Template Gallery** — 13 neutral templates spanning
  World / Scene / Interior modes. No more project-specific examples on the
  default path. The wizard walks through type → template → size → gameplay
  profiles → theme → local LLM, then drops you into the canvas.
- 🖍 **Sketch Canvas** — polygon, road, POI, and scene-slot tools backed by a
  `SketchDocument` model. Sketch lives separately from generated IR; you
  can iterate freely before generating.
- 🏙 **District Inspector** — per-district district type, theme, density,
  height profile, building style, road pattern, gameplay profile, metrics,
  and local LLM brief. Generation can be triggered for the whole sketch or
  one district at a time.
- 🛣 **Deterministic generation pipeline** — `roads → parcels → buildings →
  landmarks → scene slots → guidance → convert → validate`. Each stage is
  individually toggleable and reports status. Geometry is computed by pure
  Python; the LLM is reserved for semantic plans.
- 🎯 **Gameplay metrics** — per-profile road widths, intersection spacing,
  cover intervals, sightlines, parcel sizes, building heights, landmark
  counts. Templates ship sensible defaults; districts can override.
- 📐 **Design rules + design-aware validators** — curated rules drawn from
  urban-playground, scale-illusion, level-design, and worldbuilding guides.
  New validation categories: connectivity, gameplay metrics, readability,
  district identity, geometry.
- 🪧 **Guidance cues** — landmarks, breadcrumbs, leading lines, light/contrast
  hints, colour signifiers, sound cues, negative space, affordances, level
  narrative — modelled as first-class objects and surfaced in validation.
- 🔎 **Better preview readability** — label-scale slider, per-layer visibility
  toggles, automatic font shrinking for large worlds, greedy overlap
  suppression. The preview no longer screams.
- 🤖 **Local LLM, now in the workflow** — global defaults plus per-generation
  overrides (model, temperature). District Inspector accepts a local LLM
  brief. The v0.4 Ollama / Mock providers, repair loop, and CLI commands all
  carry over.
- 📤 **Export upgrades** — SketchLayer JSON, GeneratedLayout JSON, and a
  Markdown design report alongside the existing SVG / OBJ / Blender exports.

No cloud APIs are introduced. No API keys are required. Existing v0.4 CLI
commands (`validate`, `render-svg`, `export-obj`, `export-blender`,
`preflight`, `llm-check`, `llm-draft-world`, `llm-draft-scene`, `llm-repair`)
still work; v0.5 adds `templates`, `new-from-template`, `generate-layout`,
`validate-design`, `export-design-report`.

---

## The v0.5 workflow

1. **Open MapIR Studio.** On first launch, the New Project Wizard appears.
2. **Choose a document type** — World, Scene, or Interior (Interior is a
   subtype of SceneIR internally).
3. **Pick a template** from the neutral gallery.
4. **Set size, gameplay profiles, theme, and local LLM** (provider, model,
   temperature). The Mock provider is always available.
5. **Sketch.** Draw district polygons, roads, POIs, scene slots on the canvas.
6. **Configure each district** in the District Inspector — district type,
   profile, density, road pattern, local brief.
7. **Generate.** Pick the pipeline stages you want, or Run All. Output is a
   `GeneratedLayout` (roads, parcels, buildings, landmarks, scene slots,
   guidance cues) bound to your sketch and converted into WorldIR / SceneIR.
8. **Validate.** Structural rules + design rules run together; warnings are
   grouped by category and clickable.
9. **Preview.** Toggle layers, scale labels, inspect what was generated.
10. **Export.** SVG, OBJ, Blender Python, SketchLayer JSON, GeneratedLayout
    JSON, design-report Markdown.

JSON / raw IR remains available in the **Inspector** page for advanced users
but is no longer the default landing experience.

---

## Three document modes: World, Scene, Interior

### World

Larger spaces. Districts, roads, water, POIs, scene slots. Examples: GTA-like
modern island city, medieval RPG magical forest, modern rural forest / Far
Cry-like compound, dense cyberpunk urban district.

### Scene

Smaller gameplay-grade spaces. Zones, entrances, paths, objects, gameplay
markers. Examples: industrial port, urban alley, forest checkpoint, rural
house compound, rooftop encounter.

### Interior

A subtype of SceneIR with interior-room zones. Examples: warehouse interior,
nightclub, office floor, apartment block.

Bundled demo files in `examples/demos/` exercise one template per mode.

---

## Quick start (Windows)

Requires **Python 3.11+** on `PATH`.

```bat
git clone https://github.com/BoxshiSL/MapIR.git
cd MapIR
install.bat
run_desktop.bat
```

Other useful one-shots:

```bat
validate_examples.bat
render_examples.bat
export_blockout_examples.bat
preflight.bat
test.bat
```

Build a portable exe:

```bat
build_exe.bat
```

Result: `dist\MapIR-Studio\MapIR Studio.exe`.

---

## The desktop app

`MapIR Studio` opens at 1440×900 (min 1280×800) with a dark theme and a left
sidebar:

| Page              | What it does                                                            |
| ----------------- | ----------------------------------------------------------------------- |
| **Home**          | Creation-focused entry: New World / Scene / Interior, Open Project, recent docs, template highlights. |
| **New / Templates** | Template gallery with 13 neutral cards. Filter by type, genre, gameplay profile. |
| **Canvas**        | Sketch tools: Select, Draw District Polygon, Draw Road, Add POI, Add Scene Slot, Delete. |
| **Districts**     | District list + District Inspector (type, profile, metrics, local LLM brief, generate actions). |
| **Generation**    | Pipeline stages with enable/disable and Run / Run All. Status log. |
| **Preview**       | `QGraphicsView` 2D rendering. Label-scale slider, per-layer visibility, zoom/pan/fit. |
| **Validation**    | Structural + design warnings grouped by category, colour-coded, clickable. |
| **Inspector**     | Advanced. Raw JSON tabs: WorldIR/SceneIR, SketchLayer, GeneratedLayout, Validation Report. |
| **Export**        | SVG / OBJ / Blender script + SketchLayer JSON + GeneratedLayout JSON + Design Report (Markdown). |
| **LLM Draft (Advanced)** | The v0.4 brief-driven drafting page, kept for power users. |
| **Settings/About**| Version, paths, Python/Qt info, scope notes.                            |

---

## CLI reference

```text
mapir validate <path>
mapir render-svg <path> --out <out.svg>
mapir export-obj <path> --out <out.obj>
mapir export-blender <path> --out <out.py>
mapir desktop [--no-browser]
mapir preflight
mapir ui [--no-browser]                       # deprecated alias for `desktop`
mapir llm-check --provider {mock,ollama}
mapir llm-draft-world --provider ... --brief ... --out ...
mapir llm-draft-scene --provider ... --brief ... --out ...
mapir llm-repair <path> --provider ... --out ...
mapir templates                                # v0.5
mapir new-from-template <template_id> --out <sketch.json>  # v0.5
mapir generate-layout <sketch.json> --out <layout.json>    # v0.5
mapir validate-design <layout.json>            # v0.5
mapir export-design-report <layout.json> --out <md>        # v0.5
```

All commands also work via `python -m mapir.cli ...`.

---

## Architecture

```
mapir/
├── __init__.py              # __version__ = "0.5.0"
├── cli.py                   # Typer app
├── core/                    # Pydantic v2: WorldIR, SceneIR, AssetRegistry, geometry, validation
├── render/svg_renderer.py   # Hand-rolled SVG (now label-scale aware)
├── export/                  # OBJ + Blender script exporters
├── desktop/                 # PySide6 desktop app
│   ├── main_window.py
│   ├── state.py             # AppState with current_document / current_sketch / current_layout
│   ├── preview_scene.py     # Label scaling + per-layer visibility
│   ├── widgets/             # Home, Templates, Canvas, Districts, Generation, Preview, Validation, Inspector, Export, LLM Draft, Settings
│   └── dialogs/new_project_wizard.py
├── canvas/                  # SketchLayer models, canvas tools, sketch→IR
├── generation/              # Templates loader, gameplay metrics, GeneratedLayout, road/parcel/building/landmark/scene-slot/guidance generators, pipeline
├── design/                  # DesignRule loader, design validators, design report
├── llm/                     # Providers (mock, ollama), prompts, schemas, drafting, plan→IR, repair, settings
├── data/templates/*.json    # 13 neutral templates (World/Scene/Interior)
├── schemas/                 # Reference JSON schemas
└── utils/                   # paths (frozen-aware) + io

guides/                      # Reference PDFs + curated design rules
├── README.md
├── design_rules.json
└── design_rules/*.md

docs/                        # v0_5_workflow, canvas_and_sketch_layer, gameplay_metrics, design_rules, templates, local_llm, release_plan

scripts/                     # preflight.py + build_demo_fixtures.py

examples/                    # asset_registry + demos/ (auto-generated from templates)
tests/                       # pytest suite (mock-only LLM, no real Ollama in CI)
.github/workflows/ci.yml     # Windows CI: preflight + lint + tests + smoke
MapIR-Studio.spec            # PyInstaller spec (now bundles mapir/data, guides, docs)
```

---

## Templates

13 neutral templates ship in `mapir/data/templates/`:

| Template | Type | Genre |
|---|---|---|
| `world_modern_island_city` | World | GTA-like modern city island |
| `world_medieval_magical_forest` | World | Medieval RPG / magical forest |
| `world_modern_rural_forest` | World | Far Cry-like rural forest compound |
| `world_cyberpunk_dense_district` | World | Dense vertical cyberpunk |
| `scene_industrial_port` | Scene | Industrial port |
| `scene_urban_alley` | Scene | Urban alley |
| `scene_forest_checkpoint` | Scene | Forest checkpoint |
| `scene_rural_house_compound` | Scene | Rural compound |
| `scene_rooftop_encounter` | Scene | Rooftop combat |
| `interior_warehouse` | Interior | Warehouse |
| `interior_nightclub` | Interior | Nightclub |
| `interior_office_floor` | Interior | Office floor |
| `interior_apartment_block` | Interior | Apartment block |

Each template carries default size, default gameplay profiles, default
districts, default metrics, and a recommended local LLM brief. See
[`docs/templates.md`](docs/templates.md).

---

## Gameplay metrics and design rules

Templates and districts carry a `GameplayMetrics` object with:

- Road widths (arterial / collector / local / alley / trail), intersection
  spacing, shortcut density, dead-end ratio.
- Parcel/block dimensions, building setbacks, height min/max, density.
- Shooter/cover: cover interval, cover width/height, max open sightline,
  combat arena size.
- Stealth: alternate-route count, concealment density, restricted areas,
  patrol hints.
- Parkour: climbable-edge interval, rooftop-connection density, verticality.
- Exploration: landmark count, vista count, secret paths, breadcrumb density.

Design rules live in `guides/design_rules.json` and human-readable Markdown
under `guides/design_rules/`. They are curated from the bundled level-design
and worldbuilding guides — no embeddings, no RAG. See
[`docs/gameplay_metrics.md`](docs/gameplay_metrics.md) and
[`docs/design_rules.md`](docs/design_rules.md).

---

## Validation

Three layers:

1. **Structural** — Pydantic v2 enforces types, required fields, polygon
   vertex minimums, positive sizes, `ir_type` discriminator.
2. **Semantic** — the v0.4 rules engine in `mapir/core/validation.py`
   (unique IDs, world has districts and scene slots, polygons inside bounds,
   scene has zones and entrances, configurable MUST_HAVE_* constraints).
3. **Design-aware (v0.5)** — `mapir/design/validators.py`:

| Category | Examples |
|---|---|
| connectivity | district has at least one road; road graph is connected for city templates |
| gameplay_metrics | road width meets driving profile; cover interval meets shooter profile |
| readability | each major district has a landmark; objectives have guidance cues |
| district_identity | district has type/theme/tags; differentiating feature exists |
| geometry | parcels inside districts; buildings inside parcels; scene slots inside districts |

---

## Local LLM drafting

MapIR v0.5 keeps the v0.4 local LLM stack and weaves it into the workflow:
the Wizard offers provider/model defaults, the District Inspector accepts a
**per-district brief**, and each generation stage can have its own
`LLMSettingsOverride` (model, temperature, max tokens).

You still install and pull models yourself — MapIR never downloads them
automatically.

### Quick start

1. Install and start Ollama.
2. Pull a model with structured-JSON support, e.g.:

```bat
ollama pull qwen3:8b
ollama pull deepseek-r1:7b
```

3. From MapIR:

```bat
:: Sanity-check the provider
python -m mapir.cli llm-check --provider ollama --model qwen3:8b

:: Draft a world from a brief (v0.4-style)
python -m mapir.cli llm-draft-world ^
  --provider ollama --model qwen3:8b ^
  --brief "Create a modern island city with driving, shooter and exploration profiles." ^
  --out output\llm\world_draft.json
```

For demos / tests that can't rely on a local model, swap `--provider ollama`
for `--provider mock`. See [`docs/local_llm.md`](docs/local_llm.md) for setup
notes and per-district briefs.

> Local LLM output is always validated before use. Invalid drafts are not
> silently accepted.

---

## Building the exe

```bat
install.bat
build_exe.bat
```

`build_exe.bat` runs preflight first, then invokes
`pyinstaller MapIR-Studio.spec` to produce a one-folder distribution at
`dist\MapIR-Studio\`. The exe is `dist\MapIR-Studio\MapIR Studio.exe`.

The spec bundles:

- the `mapir` package and all desktop sub-modules,
- the `examples/` directory,
- the JSON schemas under `mapir/schemas/`,
- the templates under `mapir/data/templates/`,
- the `guides/` and `docs/` directories,
- the `README.md`.

It excludes `tkinter`, `PyQt5`, `PyQt6`, and `PySide2` to keep the build small.
An Inno Setup installer is still planned for a later release —
[`docs/release_plan.md`](docs/release_plan.md) tracks it.

---

## What MapIR is not yet

Honest scope check — none of the following are claimed by v0.5:

- ❌ Not a final art generator.
- ❌ Not a UE5 or Unity exporter (UE5 prototype is on the v0.6 roadmap).
- ❌ Not a marketplace GLB/FBX asset importer.
- ❌ Not a full 3D viewport (the canvas and preview are 2D).
- ❌ Not a freehand sketch recognizer — drawing means explicit polygons,
  polylines, and markers.
- ❌ No installer yet (portable zip only).
- ❌ The local LLM layer is **assistive only** — the source of truth remains
  MapIR's schemas, structural validation, and design rules.

If you're looking for any of the above today, MapIR is a foundation for it,
not the thing itself.

---

## Roadmap

**v0.3** — Desktop reset; PyInstaller exe; preflight; stable IR toolchain.

**v0.4** — Local LLM drafting layer: Ollama provider, Mock provider,
deterministic Plan → IR conversion, repair loop, LLM Draft desktop page, CLI
commands.

**v0.5 (this release)** — UX + Canvas + Gameplay-Aware Zoning: New Project
Wizard, template gallery, sketch canvas, District Inspector, deterministic
generation pipeline, gameplay metrics, design rules, design-aware validators,
guidance cues, better preview readability, expanded exports.

**v0.6** — Editable object properties on the canvas; better road snapping
and parcel subdivision; building edge recipes; optional generic HTTP /
llama.cpp LLM provider; few-shot prompt examples; world ↔ scene embedding
workflow; asset-registry-assisted drafting; Blender preview improvements;
UE5 exporter prototype.

---

## Development

```bat
install.bat       :: creates .venv + installs dev deps
test.bat          :: pytest -q with QT_QPA_PLATFORM=offscreen
lint.bat          :: black --check + ruff check (no edits)
format.bat        :: black + ruff --fix (rewrites files)
preflight.bat     :: scan for one-line corruption, invalid JSON, etc.
```

The CI workflow at `.github/workflows/ci.yml` runs all of the above on
`windows-latest` for every push and PR to `main`.

When editing JSON, Python, or YAML files **always commit with normalised line
endings** — `.gitattributes` and `.editorconfig` are configured to enforce
this; `preflight.bat` will catch damage before it lands in CI.

---

## License

License is not finalised yet — `pyproject.toml` currently declares the
project as **Proprietary**. If you intend to redistribute or modify MapIR
outside this repository, please open an issue first.

---

<div align="center">
<sub>Built with PySide6, Pydantic v2, Typer, Rich, and PyInstaller on Windows.</sub>
</div>
