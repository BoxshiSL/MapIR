"""SketchLayer models — what the user draws on the Canvas.

These are *separate* from validated IR. The Canvas page, the District
Inspector, and the generation pipeline read/write ``SketchDocument``; only
the pipeline and ``sketch_to_ir`` convert it into ``WorldIR`` / ``SceneIR``.

Schema decisions:
* Polygons / roads use the same ``Point2D`` / ``Polygon2D`` primitives as the
  core IR — no parallel geometry hierarchy.
* Enums are mostly free-form strings (``district_type`` etc.) like
  ``core.models.District`` to stay flexible while we iterate.
* Road types include the v0.5 superset (``arterial``, ``collector``,
  ``local``, ``alley``, ``path``, ``trail``, ``service``); the
  ``sketch_to_ir`` converter maps these onto the v0.4 ``RoadType`` enum.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..core.models import Point2D, Polygon2D, Size2D
from ..generation.gameplay_metrics import (
    BuildingStyle,
    GameplayMetrics,
    GameplayProfile,
    RoadPattern,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- enums ----


class SketchRoadType(str, Enum):
    ARTERIAL = "arterial"
    COLLECTOR = "collector"
    LOCAL = "local"
    ALLEY = "alley"
    PATH = "path"
    TRAIL = "trail"
    SERVICE = "service"


class SketchPOIType(str, Enum):
    LANDMARK = "landmark"
    OBJECTIVE = "objective"
    SHOP = "shop"
    SAFE_ZONE = "safe_zone"
    ENEMY_AREA = "enemy_area"
    RESOURCE = "resource"
    VISTA = "vista"
    DUNGEON = "dungeon"
    CHECKPOINT = "checkpoint"
    CUSTOM = "custom"


class GuidanceRole(str, Enum):
    LANDMARK = "landmark"
    BREADCRUMB = "breadcrumb"
    LEADING_LINE = "leading_line"
    LIGHT_CONTRAST = "light_contrast"
    COLOR_SIGNIFIER = "color_signifier"
    SOUND_CUE = "sound_cue"
    NEGATIVE_SPACE = "negative_space"
    AFFORDANCE = "affordance"
    VISTA = "vista"
    NONE = "none"


# ---- per-task LLM override (used by District Inspector and Generation page) ----


class LLMSettingsOverride(_Strict):
    """Per-task overrides on top of the global :class:`LLMSettings` defaults."""

    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


# ---- sketch items ----


class SketchDistrict(_Strict):
    id: str
    name: str
    polygon: Polygon2D
    district_type: str = "mixed"
    role: str = ""
    theme: str = ""
    density: str = "medium"
    height_profile: str = "mid"
    building_style: BuildingStyle = BuildingStyle.MODERN_CITY
    road_pattern: RoadPattern = RoadPattern.GRID
    gameplay_profiles: list[GameplayProfile] = Field(default_factory=list)
    llm_brief: str = ""
    generation_settings: LLMSettingsOverride = Field(default_factory=LLMSettingsOverride)
    metrics_override: GameplayMetrics | None = None
    tags: list[str] = Field(default_factory=list)


class SketchRoad(_Strict):
    id: str
    name: str = ""
    road_type: SketchRoadType = SketchRoadType.LOCAL
    points: list[Point2D]
    width_m: float = Field(default=4.0, gt=0)
    gameplay_tags: list[str] = Field(default_factory=list)

    @classmethod
    def _validate_min_points(cls, points: list[Point2D]) -> list[Point2D]:
        if len(points) < 2:
            raise ValueError("SketchRoad requires at least 2 points")
        return points


class SketchPOI(_Strict):
    id: str
    name: str
    poi_type: SketchPOIType = SketchPOIType.LANDMARK
    position: Point2D
    tags: list[str] = Field(default_factory=list)
    guidance_role: GuidanceRole = GuidanceRole.NONE


class SketchSceneSlot(_Strict):
    id: str
    name: str
    position: Point2D
    size: Size2D
    district_id: str | None = None
    allowed_scene_types: list[str] = Field(default_factory=lambda: ["exterior_location"])
    gameplay_role: str = ""
    tags: list[str] = Field(default_factory=list)


class SketchNote(_Strict):
    """Free-form annotation pinned at a point. Cosmetic, never validates."""

    id: str
    position: Point2D
    text: str


class SketchDocument(_Strict):
    sketch_id: str
    name: str
    document_type: Literal["world", "scene", "interior"]
    template_id: str | None = None
    size: Size2D
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    districts: list[SketchDistrict] = Field(default_factory=list)
    roads: list[SketchRoad] = Field(default_factory=list)
    pois: list[SketchPOI] = Field(default_factory=list)
    scene_slots: list[SketchSceneSlot] = Field(default_factory=list)
    notes: list[SketchNote] = Field(default_factory=list)

    # Document-wide metrics; districts can override individually via
    # ``SketchDistrict.metrics_override``.
    metrics: GameplayMetrics = Field(default_factory=GameplayMetrics)
    # Author-level LLM brief — informs prompts when no district-level brief
    # is set.
    llm_brief: str = ""
