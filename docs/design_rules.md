# Design rules

v0.5 ships curated design rules drawn from the bundled level-design,
urban-playground, scale-illusion, and worldbuilding guides under `guides/`.
There is no embeddings / RAG layer in v0.5 — the registry is a small JSON
file (`guides/design_rules.json`) plus matching Markdown notes.

## Where the rules live

* `guides/design_rules.json` — machine-readable registry.
* `guides/design_rules/*.md` — per-topic notes:
  * `urban_playgrounds.md`
  * `open_world_scale.md`
  * `level_design_guidance.md`
  * `worldbuilding_structure.md`

The Pydantic schema is `mapir.design.design_rules.DesignRule`:

```python
class DesignRule(BaseModel):
    id: str
    category: RuleCategory   # planning / gameplay_metrics / navigation /
                             # readability / landmarks / streets / buildings /
                             # worldbuilding / guidance / affordance /
                             # composition / scale_illusion / iteration /
                             # districts / geometry
    name: str
    description: str
    applies_to: list[str]    # world / scene / interior / district / road / ...
    severity: "info" | "warning" | "error"
    validator_hint: str = ""
    prompt_hint: str = ""
    source_note: str = ""
```

`load_design_rules()` validates the whole registry and caches it.

## How they're applied

### Validators (`mapir.design.validators`)

`run_design_validators(ir, layout, metrics)` returns a `DesignReport` with
warnings grouped by `DesignCategory`:

* `connectivity` — districts have road touchpoints; stealth scenes have
  alternate routes; scenes have ≥ 2 entrances.
* `gameplay_metrics` — driving arterial widths; shooter cover density.
* `readability` — major district has a landmark; preview label clutter.
* `district_identity` — every district has a differentiating tag / theme.
* `geometry` — buildings inside parcels (set-back tolerance).

Findings cite the rule id from the registry.

### Prompts (`mapir.llm.prompts`)

The v0.5 prompt functions accept an optional `design_hints` list. The
`prompt_hints_for_categories([...])` helper feeds curated one-liners drawn
from the registry into the prompt without dumping the full registry every
time.

```python
hints = prompt_hints_for_categories([RuleCategory.GUIDANCE, RuleCategory.LANDMARKS])
system, user = build_district_generation_prompt(
    district_id="d_01_downtown",
    district_summary="Downtown core, dense, modern_city style.",
    metrics_summary="arterial 18m, cover_interval 6m.",
    local_brief="Show neon skyline pointing toward the harbour.",
    design_hints=hints,
)
```

### Reports (`mapir.design.reports`)

`build_design_report_markdown(ir, layout, structural, design)` produces a
Markdown report bundling structural and design findings, citing rule ids
inline.

## Adding a rule

1. Append a record to `guides/design_rules.json` (see `guides/README.md`
   for a template).
2. Update the matching Markdown note in `guides/design_rules/*.md`.
3. If the rule has a validator counterpart, add it to
   `mapir.design.validators` and test it in `tests/test_design_rules.py`.

## Not in v0.5

* No embeddings / vector search.
* No live web access.
* No automatic rule discovery from text guides — the curated registry is
  intentional.

These can land in v0.6 once the rule set is stable.
