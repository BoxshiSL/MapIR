"""MapIR — guided desktop tool for designing game worlds, scenes, and interiors.

v0.5 introduces a guided creation workflow: a New Project Wizard with a neutral
template gallery, a sketch canvas (polygon / road / POI / scene slot), a
District Inspector with per-district gameplay profiles and local LLM briefs, a
deterministic generation pipeline (roads → parcels → buildings → landmarks →
scene slots → guidance), curated design rules, and gameplay-aware validators.

v0.4's local LLM drafting layer, structural validation, and PyInstaller desktop
build remain. The LLM is an assistant only; structural and design validation
remain the source of truth.
"""

__version__ = "0.5.0"
