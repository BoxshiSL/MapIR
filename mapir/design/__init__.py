"""Design rules + design-aware validators for MapIR v0.5.

The design rules are *curated* from the bundled level-design, urban-playground,
open-world scale, and worldbuilding guides under ``guides/``. No embeddings,
no live web access — the rules are a small JSON file plus matching Markdown
notes.

The design validators apply these rules to a ``GeneratedLayout`` + IR pair
and produce ``DesignWarning`` items grouped by category.
"""
