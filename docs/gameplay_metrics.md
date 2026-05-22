# Gameplay metrics

`mapir.generation.gameplay_metrics.GameplayMetrics` is a bundle of knobs that
the deterministic generators read for sizing and that the design validators
read for "is this big enough / dense enough / connected enough" checks.

It is not a physics or AI simulation — it is a small Pydantic model that
templates ship with sensible defaults and that districts can override per
inspector.

## Top-level shape

```python
class GameplayMetrics(BaseModel):
    gameplay_profiles: list[GameplayProfile] = []
    road: RoadMetrics
    building: BuildingMetrics
    shooter: ShooterMetrics
    stealth: StealthMetrics
    parkour: ParkourMetrics
    exploration: ExplorationMetrics
```

`GameplayProfile` is the small enum `driving / stealth / shooter / parkour /
exploration`.

## Road metrics

```
arterial_width_m       default 14
collector_width_m      default 9
local_width_m          default 6
alley_width_m          default 3
trail_width_m          default 1.5
intersection_spacing_m default 80
shortcut_density       default 0.20  (0..1)
dead_end_ratio_max     default 0.15  (0..1)
```

Generators use `intersection_spacing_m` to set the grid cell size for inner
roads. The validators flag arterial roads under `arterial_width_m` for
driving profiles.

## Building metrics

```
parcel_min_width_m / parcel_max_width_m / parcel_depth_m
building_setback_m
building_height_min_m / building_height_max_m
building_density  (0..1; probability that a parcel gets a building)
```

The parcel generator slices each district's bbox along these numbers. The
building generator skips parcels probabilistically below the density to keep
sprawl in check.

## Shooter / stealth / parkour / exploration

```
shooter:      cover_interval_m, cover_width_min_m, cover_height_min_m,
              max_open_sightline_m, combat_arena_size_m
stealth:      alternate_route_count_min, concealment_density,
              restricted_area_count, patrol_route_hint_count
parkour:      climbable_edge_interval_m, rooftop_connection_density,
              verticality_score
exploration:  landmark_count_min, vista_count_min, secret_path_count_min,
              breadcrumb_density
```

`default_metrics_for_profiles([...])` returns a metrics bundle pre-tuned for
the supplied profiles — used by the wizard when the user picks profiles but
doesn't yet override individual fields.

## Where they're consumed

* `mapir.generation.road_generator` — widths, spacing, dead-end ratio.
* `mapir.generation.parcel_generator` — parcel dimensions.
* `mapir.generation.building_generator` — heights, density, setback.
* `mapir.generation.landmark_generator` — landmark count target.
* `mapir.design.validators` — emits warnings when the IR + layout don't
  satisfy the metrics for the chosen profiles.

## Recommended defaults

The templates ship per-genre tunings — see [`templates.md`](templates.md).
GTA-like city: wider arterials (18m), shooter cover_interval=6m. Medieval
forest: trails replace arterials. Cyberpunk: dense alleys, parkour
verticality 0.75. Far Cry-like rural: forest concealment density 0.55.
