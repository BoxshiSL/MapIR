# Templates

v0.5 ships 13 neutral templates under `mapir/data/templates/`. Each one is a
JSON file matching the `TemplateDefinition` schema in
`mapir/generation/templates.py`.

| template_id | type | genre | size (m) | default profiles |
|---|---|---|---|---|
| `world_modern_island_city` | world | modern_open_world | 4000×4000 | driving, shooter, exploration |
| `world_medieval_magical_forest` | world | medieval_fantasy | 4000×4000 | exploration, stealth, shooter |
| `world_modern_rural_forest` | world | modern_rural | 3000×3000 | stealth, shooter, driving, exploration |
| `world_cyberpunk_dense_district` | world | cyberpunk | 1500×1500 | stealth, parkour, shooter, exploration |
| `scene_industrial_port` | scene | industrial | 200×150 | shooter, stealth, exploration |
| `scene_urban_alley` | scene | urban | 80×45 | stealth, shooter, parkour |
| `scene_forest_checkpoint` | scene | rural | 150×100 | stealth, shooter, exploration |
| `scene_rural_house_compound` | scene | rural | 180×140 | stealth, shooter, exploration |
| `scene_rooftop_encounter` | scene | urban | 120×90 | shooter, parkour, stealth |
| `interior_warehouse` | interior | industrial | 80×60 | shooter, stealth, exploration |
| `interior_nightclub` | interior | urban | 50×40 | stealth, shooter, exploration |
| `interior_office_floor` | interior | urban | 60×40 | stealth, shooter |
| `interior_apartment_block` | interior | urban | 50×30 | stealth, shooter |

## TemplateDefinition fields

```python
class TemplateDefinition(BaseModel):
    template_id: str
    name: str
    document_type: Literal["world", "scene", "interior"]
    genre: str
    description: str
    default_size: Size2D
    default_gameplay_profiles: list[GameplayProfile]
    default_districts: list[DistrictPreset]
    default_metrics: GameplayMetrics
    recommended_llm_brief: str = ""
    generation_recipe_id: str = "grid"
    thumbnail: str | None = None
```

## DistrictPreset

Each entry seeds one `SketchDistrict` when the template is instantiated:

```python
class DistrictPreset(BaseModel):
    name: str
    district_type: str
    role: str = ""
    theme: str = ""
    density: Density = Density.MEDIUM
    height_profile: HeightProfile = HeightProfile.MID
    building_style: BuildingStyle
    road_pattern: RoadPattern
    gameplay_profiles: list[GameplayProfile]
    bbox: [x_min, y_min, x_max, y_max]   # in world units
    tags: list[str]
```

## Adding a new template

1. Drop a `*.json` file into `mapir/data/templates/`.
2. The loader (`load_all_templates()`) discovers it on next launch.
3. The preflight check counts `≥ 13` templates and refuses duplicate ids.
4. Add a row to this table.

The wizard, the gallery page, the CLI `templates` command, and
`new-from-template` all read from the same loader — no separate
registration required.
