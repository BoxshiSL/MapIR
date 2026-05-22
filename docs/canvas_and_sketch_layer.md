# Canvas + SketchLayer

The Canvas page in v0.5 is where the user iterates on a `SketchDocument`
before generating a `GeneratedLayout` and a canonical IR.

## SketchDocument

```python
class SketchDocument(BaseModel):
    sketch_id: str
    name: str
    document_type: "world" | "scene" | "interior"
    template_id: str | None
    size: Size2D
    created_at: datetime
    updated_at: datetime
    districts: list[SketchDistrict]
    roads:     list[SketchRoad]
    pois:      list[SketchPOI]
    scene_slots: list[SketchSceneSlot]
    notes: list[SketchNote]
    metrics: GameplayMetrics
    llm_brief: str = ""
```

`SketchRoad.road_type` covers the v0.5 superset:
`arterial / collector / local / alley / path / trail / service`. The
`sketch_to_ir` converter maps these onto the v0.4 `RoadType` enum.

`SketchPOI.poi_type` covers
`landmark / objective / shop / safe_zone / enemy_area / resource / vista /
dungeon / checkpoint / custom`.

`SketchSceneSlot` mirrors `SceneSlot` from v0.4 with an added
`gameplay_role` annotation.

## SketchDistrict

```python
class SketchDistrict(BaseModel):
    id: str
    name: str
    polygon: Polygon2D
    district_type: str
    role: str
    theme: str
    density: str
    height_profile: str
    building_style: BuildingStyle
    road_pattern: RoadPattern
    gameplay_profiles: list[GameplayProfile]
    llm_brief: str = ""
    generation_settings: LLMSettingsOverride
    metrics_override: GameplayMetrics | None = None
    tags: list[str]
```

## Helper API

`mapir.canvas.sketch_state` provides:

* `new_sketch_document(template, *, name=None, sketch_id=None,
  metrics_override=None)` — seeds a fresh sketch from a template's defaults.
* `add_district(sketch, polygon, *, name, district_type)`.
* `add_road(sketch, points, *, name, road_type, width_m)`.
* `add_poi(sketch, position, *, name, poi_type)`.
* `add_scene_slot(sketch, position, *, name, size, district_id)`.
* `delete_by_id(sketch, target_id)`.

These are imported by the Canvas controllers, the CLI
`new-from-template` command, and the demo-fixture script.

## Sketch → IR

`mapir.canvas.sketch_to_ir`:

* `sketch_to_world_ir(sketch, layout=None) -> WorldIR`
* `sketch_to_scene_ir(sketch, layout=None) -> SceneIR`
* `sketch_to_ir(sketch, layout=None) -> WorldIR | SceneIR`

The converter:

* preserves the sketch's polygons / road shapes / POI positions verbatim;
* uses the `GeneratedLayout.roads` as the primary road source;
* merges sketch + generated scene slots, de-duped by `district_id`;
* maps `SketchRoadType` → v0.4 `RoadType`;
* falls back to a synthetic scene slot when the sketch has none so the
  v0.4 validator (which requires ≥ 1 slot) stays happy.

## Phase A scaffold vs. Phase B targets

* **Phase A (now)**: the Canvas page renders the SketchDocument read-only.
  The toolbar is disabled. Use the wizard, the Templates Gallery, and the
  Generation page to iterate.
* **Phase B (later in v0.5.1)**: interactive draw tools — polygon, road,
  POI, scene slot, delete, select-and-move. Editable District Inspector.
* **Phase C / v0.6**: undo/redo, polygon clipping for proper parcels,
  freehand stroke recognition, road snapping.

The data model and converter are stable today, so a Phase B canvas patch
won't need to touch the schema.
