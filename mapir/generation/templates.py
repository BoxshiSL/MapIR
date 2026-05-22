"""Template registry — 13 neutral templates loaded from ``mapir/data/templates``.

Each template is a ``TemplateDefinition`` JSON file. Loading is lazy and
cached. The Wizard, the Home page, and the CLI ``templates`` /
``new-from-template`` commands all read from here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..core.enums import Density, HeightProfile
from ..core.models import Size2D
from ..utils.paths import templates_dir
from .gameplay_metrics import (
    BuildingStyle,
    GameplayMetrics,
    GameplayProfile,
    RoadPattern,
)


DocumentType = Literal["world", "scene", "interior"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DistrictPreset(_Strict):
    """Initial district sketched into the canvas when instantiating a template."""

    name: str
    district_type: str
    role: str = ""
    theme: str = ""
    density: Density = Density.MEDIUM
    height_profile: HeightProfile = HeightProfile.MID
    building_style: BuildingStyle = BuildingStyle.MODERN_CITY
    road_pattern: RoadPattern = RoadPattern.GRID
    gameplay_profiles: list[GameplayProfile] = Field(default_factory=list)
    # Relative bbox inside the world's [0, size]; the loader does not clip,
    # generators do.
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="[x_min, y_min, x_max, y_max] in world units",
    )
    tags: list[str] = Field(default_factory=list)


class TemplateDefinition(_Strict):
    template_id: str
    name: str
    document_type: DocumentType
    genre: str
    description: str
    default_size: Size2D
    default_gameplay_profiles: list[GameplayProfile] = Field(default_factory=list)
    default_districts: list[DistrictPreset] = Field(default_factory=list)
    default_metrics: GameplayMetrics = Field(default_factory=GameplayMetrics)
    recommended_llm_brief: str = ""
    generation_recipe_id: str = "grid"
    thumbnail: str | None = None


class TemplateLoadError(RuntimeError):
    pass


_CACHE: dict[str, TemplateDefinition] | None = None


def _scan_dir() -> Path:
    path = templates_dir()
    if not path.is_dir():
        raise TemplateLoadError(
            f"Template directory not found: {path}. "
            "Did the PyInstaller spec bundle 'mapir/data/templates'?"
        )
    return path


def load_all_templates(*, force: bool = False) -> dict[str, TemplateDefinition]:
    """Read every ``*.json`` in the templates dir and validate it.

    Cached after the first successful read. Raises ``TemplateLoadError`` if any
    file fails to parse — templates are bundled assets and must be valid.
    """
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    out: dict[str, TemplateDefinition] = {}
    path = _scan_dir()
    for file in sorted(path.glob("*.json")):
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateLoadError(f"Invalid JSON in {file.name}: {exc}") from exc
        try:
            tpl = TemplateDefinition.model_validate(raw)
        except ValidationError as exc:
            raise TemplateLoadError(
                f"Template {file.name} failed validation:\n{exc}"
            ) from exc
        if tpl.template_id in out:
            raise TemplateLoadError(
                f"Duplicate template_id {tpl.template_id!r} in {file.name}"
            )
        out[tpl.template_id] = tpl

    _CACHE = out
    return out


def get_template(template_id: str) -> TemplateDefinition:
    templates = load_all_templates()
    if template_id not in templates:
        raise KeyError(
            f"Unknown template_id: {template_id!r}. "
            f"Available: {sorted(templates)}"
        )
    return templates[template_id]


def templates_by_type(document_type: DocumentType) -> list[TemplateDefinition]:
    return [
        tpl
        for tpl in load_all_templates().values()
        if tpl.document_type == document_type
    ]
