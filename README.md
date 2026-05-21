<div align="center">

# MapIR

**Structured IR and desktop toolchain for game worlds, scenes, interiors, validation, preview, and blockout export.**

*Worlds (cities, regions, ports, coastal areas) and Scenes (alleys, warehouses, yards, interiors) as
versionable JSON. Pydantic-validated, dark-themed PySide6 desktop UI, SVG preview,
OBJ + Blender blockout export, PyInstaller-packaged exe.*

[![Version](https://img.shields.io/badge/version-0.3.0-7c5cff.svg?style=flat-square)](pyproject.toml)
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
validate_examples.bat    :: structural + semantic checks on bundled examples
render_examples.bat      :: SVG previews into output\svg\
export_blockout_examples.bat :: OBJ + Blender scripts into output\
preflight.bat            :: scan the repo for regressions
build_exe.bat            :: package MapIR Studio.exe via PyInstaller
```

Single Python project. One CLI. One PySide6 window. One PyInstaller spec.
No web server, no cloud, no LLM, no engine plugin — those are tracked on the roadmap.

---

## Table of contents

- [Why MapIR](#why-mapir)
- [What's new in v0.3](#whats-new-in-v03)
- [Two modes: World and Scene](#two-modes-world-and-scene)
- [Quick start (Windows)](#quick-start-windows)
- [The desktop app](#the-desktop-app)
- [CLI reference](#cli-reference)
- [Architecture](#architecture)
- [Validation rules](#validation-rules)
- [Bundled examples](#bundled-examples)
- [Building the exe](#building-the-exe)
- [What MapIR is not yet](#what-mapir-is-not-yet)
- [Roadmap](#roadmap)
- [Development](#development)
- [License](#license)

---

## Why MapIR

Game-space tooling tends to fork into two extremes: opaque editor binaries on
one end, ad-hoc level scripts on the other. MapIR sits in between as a small,
typed, file-on-disk **Intermediate Representation** for spaces. You can:

- Describe a city, region, port, coastal area, or forest belt as a **WorldIR**.
- Describe an alley, yard, warehouse, club, blockpost, or interior as a **SceneIR**.
- Reserve **Scene Slots** inside a world that scenes can later be embedded into.
- Validate documents structurally (Pydantic) and semantically (rules engine).
- Preview them in 2D inside a real desktop app or as an exportable SVG.
- Export a clean blockout to OBJ or a Blender Python script for further work.

The format is text-first, diff-friendly, and engine-agnostic.

---

## What's new in v0.3

This is the **Desktop Reset** release.

- 🖥 **MapIR Studio** — full PySide6 desktop application with dark theme, sidebar
  navigation, dashboard, examples browser, World/Scene mode pages, JSON inspector,
  interactive zoomable preview, validation panel, and export panel.
- 📦 **PyInstaller build** — `build_exe.bat` produces a standalone
  `MapIR Studio.exe` in `dist\MapIR-Studio\` with examples and schemas bundled.
- 🧹 **Preflight scanner** — `python -m mapir.cli preflight` catches one-line
  corruption, broken Python files, invalid JSON, merged requirements lines,
  truncated workflow files, and missing README structure.
- 🎯 **Windows-first CI** — `windows-latest` runner with offscreen Qt, ruff +
  black + pytest gates, and example smoke tests.
- 🔧 **Tooling** — Ruff and Black configured, `.editorconfig` and `.gitattributes`
  added so cross-platform line endings don't silently corrupt files again.
- 🗑 The Tkinter UI from v0.2 has been removed. The `mapir ui` CLI command is
  kept as a deprecation alias that forwards to `mapir desktop`.

Core data model (WorldIR / SceneIR / Constraint / AssetRegistry) is **unchanged**
from v0.2 — existing JSON documents load as-is.

---

## Two modes: World and Scene

### World Mode

For larger spaces:

| District / region type            | Example                                  |
| --------------------------------- | ---------------------------------------- |
| compact open-world city           | `examples/worlds/world_jisso_city.json`  |
| coastal & forest region           | `examples/worlds/world_luga_region.json` |
| city district / port / industrial | within either of the above               |

A WorldIR contains districts, roads, water bodies, POIs, and **scene slots** —
named reservations inside the world where Scene Mode documents can be plugged in
later.

### Scene Mode

For smaller, gameplay-grade spaces (and interiors, which are a subtype):

| Scene type        | Example                                             |
| ----------------- | --------------------------------------------------- |
| urban alley       | `examples/scenes/scene_urban_alley.json`            |
| warehouse interior| `examples/scenes/scene_warehouse_interior.json`     |
| port yard         | `examples/scenes/scene_port_yard.json`              |

A SceneIR contains zones, entrances, paths, objects, gameplay markers, and
constraints. It can be standalone or reference a parent world + scene slot.

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
| **Dashboard**     | Status cards (document, IR type, validity, errors/warnings, last export), quick actions. |
| **Examples**      | Tree of bundled worlds / scenes / assets. Double-click to load.         |
| **World Mode**    | Read-only summary, districts table, scene-slots table.                  |
| **Scene Mode**    | Read-only summary, zones / entrances / objects / markers tables.        |
| **Inspector**     | Read-only monospaced JSON view + summary.                               |
| **Preview**       | `QGraphicsView` 2D rendering. Mouse wheel zoom, drag to pan, Fit / Refresh / Save SVG. |
| **Validation**    | Colour-coded errors / warnings / infos. F5 re-runs validation.          |
| **Export**        | One-click SVG / OBJ / Blender script. Recent export log. Open output folder. |
| **Settings/About**| Version, paths, Python/Qt info, scope notes.                            |

Menu bar:

- **File** → Open JSON (Ctrl+O), Close Document (Ctrl+W), Exit
- **Tools** → Validate (F5), Open Preview, Open Export
- **Help** → About MapIR Studio

---

## CLI reference

```text
mapir validate <path>
mapir inspect <path>
mapir render-svg <path> --out <out.svg>
mapir export-obj <path> --out <out.obj>
mapir export-blender <path> --out <out.py>
mapir desktop [--no-browser]
mapir preflight
mapir ui [--no-browser]    # deprecated alias for `desktop`
```

All commands also work via `python -m mapir.cli ...`.

---

## Architecture

```
mapir/
├── __init__.py              # __version__ = "0.3.0"
├── cli.py                   # Typer app — 7 commands
├── core/
│   ├── models.py            # Pydantic v2: WorldIR, SceneIR, AssetRegistry, Constraint, geometry
│   ├── enums.py             # IRType, Density, ZoneType, MarkerType, ConstraintType, ...
│   ├── geometry.py          # BBox2D, polygon/point bounds helpers
│   ├── validation.py        # ValidationReport, semantic rules engine
│   └── errors.py
├── render/
│   └── svg_renderer.py      # hand-rolled SVG for World + Scene
├── export/
│   ├── obj_exporter.py      # Wavefront OBJ blockouts
│   └── blender_exporter.py  # Blender bpy Python script
├── desktop/
│   ├── app.py               # QApplication entry + headless smoke
│   ├── main_window.py       # top bar + sidebar + stacked pages + menu
│   ├── state.py             # AppState (QObject) with signals
│   ├── theme.py             # palette + Qt stylesheet
│   ├── preview_scene.py     # QGraphicsScene builder mirroring the SVG renderer
│   └── widgets/             # 9 page widgets (dashboard, examples, world, scene, ...)
├── schemas/                 # reference JSON schemas
└── utils/
    ├── io.py                # load_json / load_ir / dump_text
    └── paths.py             # frozen-aware app paths

scripts/preflight.py         # repo health scanner (called by CLI `preflight`)

examples/                    # bundled worlds + scenes + asset registry
tests/                       # pytest suite
.github/workflows/ci.yml     # Windows CI: preflight + lint + tests + smoke commands
MapIR-Studio.spec            # PyInstaller spec
```

---

## Validation rules

Two layers:

1. **Structural** — Pydantic v2 enforces types, required fields, polygon vertex
   minimums, positive sizes, and `ir_type` discriminator on load.
2. **Semantic** — `mapir/core/validation.py` runs a `ValidationReport` of
   errors / warnings / infos:

| Check                                                        | Layer | Severity   |
| ------------------------------------------------------------ | ----- | ---------- |
| Unique IDs within each list                                  | both  | error      |
| World has ≥1 district and ≥1 scene slot                      | world | error      |
| Scene slot `district_id` references a real district          | world | error      |
| Polygon / point coordinates inside world / scene bounds      | both  | warning    |
| Scene has ≥1 zone and ≥1 entrance                            | scene | error      |
| Interior scene has at least one room / service / storage zone| scene | error      |
| Exterior scene has a path / combat / public / yard zone      | scene | error      |
| `MUST_HAVE_MIN_ENTRANCES` / `_ESCAPE_ROUTES` / `_COVER_MARKERS` | scene | configurable |
| `MUST_HAVE_SCENE_SLOT`                                       | world | configurable |
| `MUST_BE_INSIDE_BOUNDS`                                      | both  | configurable |
| `MUST_NOT_OVERLAP` (locked objects)                          | scene | configurable |
| Unsupported constraint types                                 | both  | warning    |

---

## Bundled examples

### Worlds

**`world_jisso_city.json`** — compact open-world city.
Districts: Kita Central, Sotonbori, Kurogane, KIU University, Aobadai,
Takamine, Seihama, Minato Bay Port, KIX Airport Island.
Scene slots: `sotonbori_club_back_alley`, `sotonbori_nightclub_interior`,
`kurogane_narrow_alley`, `minato_container_yard`, `minato_warehouse_interior`,
`kix_terminal_security_area`.

**`world_luga_region.json`** — coastal-forest region.
Districts: Coastal Shore, Port Edge, Small Village, Swamp Lowland, Forest Belt,
Observation Hill, Restricted Facility.
Scene slots: `forest_checkpoint`, `abandoned_house_interior`, `small_dock`,
`road_ambush_site`, `radio_tower`, `restricted_cabin_interior`.

### Scenes

- **`scene_urban_alley.json`** — Sotonbori backstreet alley (80×45×25).
  3 entrances, escape route, 5+ cover markers.
- **`scene_warehouse_interior.json`** — Minato bay warehouse (70×50×12).
  Loading zone, storage aisles, office corner, service corridor.
- **`scene_port_yard.json`** — Minato container yard (120×90×25).
  Container stacks, loading area, vehicle path, stealth route, spawns.

### Assets

- **`asset_registry_basic.json`** — 10 categorised entries (building, container,
  prop, vegetation, landmark, door, stairs).

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
- the `README.md`.

It excludes `tkinter`, `PyQt5`, `PyQt6`, and `PySide2` to keep the build small.

For first public releases you can zip up `dist\MapIR-Studio\` as
`MapIR-Studio-v0.3.0-windows.zip` and attach it to a GitHub Release.
An Inno Setup installer is planned for a later release — see
[`docs/release_plan.md`](docs/release_plan.md).

---

## What MapIR is not yet

Honest scope check — none of the following are claimed by v0.3:

- ❌ Not a final art generator.
- ❌ Not an AI / prompt-to-IR system.
- ❌ Not a UE5 or Unity exporter.
- ❌ Not a procedural city / scene layout generator.
- ❌ Not a marketplace asset importer.
- ❌ No game-ready optimisation pipeline.
- ❌ No editable canvas (read-only inspector for now).
- ❌ No installer yet (portable zip only).

If you're looking for any of the above today, MapIR is a foundation for it,
not the thing itself.

---

## Roadmap

**v0.3 (this release)** — Desktop reset; PyInstaller exe; preflight; stable
IR toolchain on Windows.

**v0.4** — Editable canvas (move / select objects); create new Scene from
preset; create new World from preset; project folder format; save / save-as;
asset registry viewer / editor; improved 2D preview controls.

**v0.5** — Prompt-to-IR draft (template-based, optional external provider);
asset kit indexing; embedding scenes into world slots; improved OBJ geometry.

**v0.6** — UE5 exporter prototype; road splines; data layers; gameplay
markers in-engine; Blender preview improvements.

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
endings** — `.gitattributes` and `.editorconfig` are configured to enforce this,
but if you edit on a system that ignores them, `preflight.bat` will catch the
damage before it lands in CI.

---

## License

License is not finalised yet — `pyproject.toml` currently declares the project
as **Proprietary**. If you intend to redistribute or modify MapIR outside this
repository, please open an issue first.

---

<div align="center">
<sub>Built with PySide6, Pydantic v2, Typer, Rich, and PyInstaller on Windows.</sub>
</div>
