# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for MapIR Studio.

Builds a one-folder distribution at ``dist/MapIR-Studio/`` with
``MapIR Studio.exe`` at its root. Examples, JSON schemas, the v0.5 template
gallery, guides, and docs are bundled so the application works without any
external files.
"""

from pathlib import Path

block_cipher = None

repo_root = Path(SPECPATH).resolve()
entry_script = str(repo_root / "mapir_studio.py")

# Bundle data so the desktop app can find it via mapir.utils.paths helpers
# inside the frozen exe.
datas = [
    (str(repo_root / "examples"),           "examples"),
    (str(repo_root / "mapir" / "schemas"),  "mapir/schemas"),
    (str(repo_root / "mapir" / "data"),     "mapir/data"),     # v0.5 templates
    (str(repo_root / "guides"),             "guides"),         # v0.5 design rules
    (str(repo_root / "docs"),               "docs"),
    (str(repo_root / "README.md"),          "."),
]

hiddenimports = [
    "mapir",
    "mapir.cli",
    "mapir.core",
    "mapir.core.models",
    "mapir.core.validation",
    "mapir.core.enums",
    "mapir.core.geometry",
    "mapir.core.errors",
    "mapir.render",
    "mapir.render.svg_renderer",
    "mapir.export",
    "mapir.export.obj_exporter",
    "mapir.export.blender_exporter",
    "mapir.utils",
    "mapir.utils.io",
    "mapir.utils.paths",
    # v0.5 generation layer
    "mapir.generation",
    "mapir.generation.templates",
    "mapir.generation.gameplay_metrics",
    "mapir.generation.template_instantiation",
    # Desktop
    "mapir.desktop",
    "mapir.desktop.app",
    "mapir.desktop.main_window",
    "mapir.desktop.state",
    "mapir.desktop.theme",
    "mapir.desktop.preview_scene",
    "mapir.desktop.dialogs.new_project_wizard",
    "mapir.desktop.widgets.home_page",
    "mapir.desktop.widgets.templates_gallery",
    "mapir.desktop.widgets.canvas_page",
    "mapir.desktop.widgets.districts_page",
    "mapir.desktop.widgets.generation_page",
    "mapir.desktop.widgets.preview_panel",
    "mapir.desktop.widgets.validation_panel",
    "mapir.desktop.widgets.export_panel",
    "mapir.desktop.widgets.inspector_panel",
    "mapir.desktop.widgets.llm_draft_panel",
    "mapir.desktop.widgets.world_panel",
    "mapir.desktop.widgets.scene_panel",
    "mapir.desktop.widgets.settings_panel",
    "mapir.desktop.widgets.sidebar",
    # Legacy v0.4 widgets kept available
    "mapir.desktop.widgets.dashboard",
    "mapir.desktop.widgets.examples_panel",
]

a = Analysis(
    [entry_script],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MapIR Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MapIR-Studio",
)
