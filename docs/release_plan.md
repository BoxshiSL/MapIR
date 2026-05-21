# MapIR — release plan

A short, honest map of where MapIR is going. Updated each release.

## v0.3.0 — Desktop Reset (this release)

**Goal:** turn MapIR from a CLI + Tkinter prototype into a standalone Windows
desktop application that can be packaged as an exe.

Shipped:

- PySide6 desktop UI (`mapir/desktop/`) with dark theme, sidebar, 9 pages.
- `MapIR Studio.exe` build via PyInstaller (`MapIR-Studio.spec`).
- Preflight scanner (`scripts/preflight.py`, CLI: `mapir preflight`).
- Ruff + Black configured. Windows-first CI on `windows-latest`.
- Tkinter UI removed (`mapir ui` kept as deprecation alias).
- README, `.editorconfig`, `.gitattributes` rewritten / added.

Distribution: portable zip of `dist\MapIR-Studio\` attached to the GitHub
Release. **No installer in this release.**

---

## v0.4.0 — Editable Canvas + Project Folders

**Goal:** turn MapIR from a viewer into a basic editor.

Planned:

- Editable canvas in the Preview page — move, select, snap objects.
- Wizards: *create new Scene from preset*, *create new World from preset*.
- Project folder format (`projects/<name>/`) with metadata, JSON documents,
  and per-project output directory.
- Save / Save As inside the desktop UI; explicit Apply/Validate in the
  Inspector page (no auto-save).
- Asset registry viewer + editor (matches the existing `AssetRegistry` model).
- Better 2D preview controls (zoom levels, ruler, snap-to-grid toggle).

Stretch: light/dark theme toggle.

---

## v0.5.0 — Prompt-to-IR Draft + Asset Indexing

**Goal:** assistive authoring without making MapIR depend on a specific LLM
vendor.

Planned:

- Local prompt templates that produce IR drafts deterministically (no AI).
- Optional external provider plugin (OpenAI / Anthropic / Ollama), strictly
  opt-in and runtime-checked. Disabled by default.
- Asset kit indexing — scan a folder of GLB/FBX assets and produce an
  `AssetRegistry` JSON.
- Embedding scenes into world slots (`parent_world_id` + `parent_scene_slot_id`
  flow in the UI).
- Improved OBJ exporter geometry (rotation, non-rectangular polygons).

---

## v0.6.0 — UE5 Exporter Prototype

**Goal:** first engine target.

Planned:

- UE5 exporter prototype (DataAsset + simple actor placement).
- Road splines as UE Spline components.
- Data Layers for districts.
- Gameplay markers as named actors.
- Blender preview improvements (camera setup, materials).

---

## Future (no firm version)

- Inno Setup Windows installer (vs portable zip).
- Unity exporter prototype.
- Marketplace asset import (Quixel, Sketchfab, FAB).
- Cloud sync for projects (still optional).

---

Each milestone ships when it's solid, not on a calendar. If something gets cut
or moved between versions, this file gets updated in the same commit.
