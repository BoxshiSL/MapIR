# MapIR design guides

This folder holds reference material curated into machine-readable design
rules. v0.5 ships:

* `design_rules.json` — the rule registry consumed by
  `mapir.design.design_rules.load_design_rules()`.
* `design_rules/*.md` — human-readable notes that group the same rules by
  topic.
* The bundled PDF guides (not authored by MapIR; left as references for the
  team to consult while iterating on rules).

## Rule categories

| Category            | What it covers                                                |
|---------------------|---------------------------------------------------------------|
| `planning`          | research → 2D plan → blockout → gameplay → detail             |
| `gameplay_metrics`  | road widths, cover intervals, sightlines, climbable intervals |
| `navigation`        | road connectivity, dead ends, multiple routes                 |
| `readability`       | label clutter, landmark visibility, hidden vs frustrating     |
| `landmarks`         | unique silhouettes, meaningful payoff, skyline composition    |
| `streets`           | road hierarchy, alley density, traffic flow                   |
| `buildings`         | density, parcels, set-backs, top-down footprints              |
| `worldbuilding`     | values, conflict, factions, arena boundaries                  |
| `guidance`          | leading lines, breadcrumbs, light/colour contrast, sound      |
| `affordance`        | signifiers, climbable surfaces, doors, openings               |
| `composition`       | foreground/midground/background, negative space               |
| `scale_illusion`    | partial visibility, distant goals, fog of war                 |
| `iteration`         | playtesting, blockout-first, expect to throw work away        |

## How rules are applied

* **Validators** (`mapir.design.validators`) scan the WorldIR / SceneIR +
  GeneratedLayout for violations and produce ``DesignWarning`` items grouped
  by severity (``info`` / ``warning`` / ``error``).
* **Prompts** (`mapir.llm.prompts`) — the v0.5 LLM prompts include the rule
  text for the relevant category so the model is steered toward
  level-design-aware suggestions.
* **Reports** (`mapir.design.reports`) — Markdown design reports cite the
  rule id and category that triggered each note.

## Adding a rule

1. Append a record to `design_rules.json` with:
   ```json
   {
     "id": "navigation_no_dead_ends",
     "category": "navigation",
     "name": "Avoid dead-end-only districts",
     "description": "...",
     "applies_to": ["world", "district"],
     "severity": "warning",
     "validator_hint": "districts must have ≥1 through-road",
     "prompt_hint": "Avoid placing the whole district behind a single dead-end road.",
     "source_note": "Open-world city production talk (urban playgrounds)"
   }
   ```
2. Match the new rule in the corresponding `design_rules/*.md` file so the
   team can read the rationale.
3. Add a unit test in `tests/test_design_validators.py` if the rule has a
   validator counterpart.

Curated, not RAG. Reproducible, no embeddings.
