# Urban-playground production principles

Curated from the bundled "Building Urban Playgrounds for Video Games" guide
(`guides/Building Urban Playgrounds for Video Games.pdf`).

## Key rules (referenced by `design_rules.json`)

* **planning_blockout_first** — plan in 2D before building anything in 3D.
* **planning_gameplay_first** — identify gameplay locations first; roads and
  districts grow outward from them.
* **streets_road_hierarchy** — arterial → collector → local. One road type
  everywhere is a smell.
* **landmarks_one_per_district** — every major district has a landmark for
  orientation and reward.
* **landmarks_meaningful_payoff** — a landmark you can't interact with is a
  promise you didn't keep.
* **navigation_district_road_connection** — every district must touch the
  road graph (unless the design explicitly hides a discovery target).

## Side notes from the talk

* Modularity matters — grid-aligned blockouts are easier to iterate.
* Treat road splines and procedural prop recipes as future direction; v0.5
  doesn't ship them.
* Foundation planning is more important than early decoration.
