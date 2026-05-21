# projects/

User-created MapIR documents live here. In **v0.3.0** the format is just JSON
files following the WorldIR / SceneIR schemas — exactly like the bundled
`examples/`. Drop your own `.json` files in any sub-folder and they will work
with all CLI commands and the desktop app.

Recommended layout (suggestion, not enforced):

```
projects/
└── my-game/
    ├── worlds/
    │   └── my_city.json
    ├── scenes/
    │   ├── back_alley.json
    │   └── warehouse.json
    └── assets/
        └── my_asset_registry.json
```

In **v0.4** this directory becomes the home of a structured project format
(`.mapir` package or folder-with-metadata) and the desktop app will gain
**File → New Project** / **File → Open Project** flows. Until then,
`File → Open JSON` in MapIR Studio works directly against any JSON in here.

`.gitignore` does **not** exclude this directory — your projects are tracked
unless you add a per-project `.gitignore`.
