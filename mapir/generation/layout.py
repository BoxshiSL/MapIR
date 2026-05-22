"""GeneratedLayout — the deterministic v0.5 generation output.

A ``GeneratedLayout`` is the validated procedural artefact produced from a
``SketchDocument`` plus per-district / per-task ``GameplayMetrics``. It lives
alongside the existing ``WorldIR`` / ``SceneIR`` (the canonical IR) — the
existing schemas are *not* extended.

Conversion to IR happens via ``mapir.canvas.sketch_to_ir`` which combines
the SketchDocument with the GeneratedLayout into a WorldIR or SceneIR.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ..core.models import Point2D, Polygon2D
from .gameplay_metrics import GameplayMetrics


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParcelType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    CIVIC = "civic"
    LANDMARK = "landmark"
    MIXED_USE = "mixed_use"
    RURAL = "rural"
    FOREST_CLEARING = "forest_clearing"


class BuildingType(str, Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    WAREHOUSE = "warehouse"
    TOWER = "tower"
    SHED = "shed"
    LANDMARK = "landmark"
    GENERIC = "generic"


class LandmarkType(str, Enum):
    TOWER = "tower"
    CASTLE = "castle"
    SKYSCRAPER = "skyscraper"
    RADIO_TOWER = "radio_tower"
    TEMPLE = "temple"
    BRIDGE = "bridge"
    MOUNTAIN = "mountain"
    GIANT_TREE = "giant_tree"
    RUINS = "ruins"
    FACTORY_STACK = "factory_stack"
    AIRPORT_TOWER = "airport_tower"
    NEON_SIGN = "neon_sign"
    MONUMENT = "monument"
    VISTA_POINT = "vista_point"


class CueType(str, Enum):
    LANDMARK = "landmark"
    BREADCRUMB = "breadcrumb"
    LEADING_LINE = "leading_line"
    LIGHT_CONTRAST = "light_contrast"
    COLOR_SIGNIFIER = "color_signifier"
    SOUND_CUE = "sound_cue"
    NEGATIVE_SPACE = "negative_space"
    AFFORDANCE = "affordance"
    VISTA = "vista"


class CueStrength(str, Enum):
    SUBTLE = "subtle"
    MEDIUM = "medium"
    STRONG = "strong"


# ---- per-layer models ----


class GeneratedRoad(_Strict):
    id: str
    name: str = ""
    road_type: str  # arterial / collector / local / alley / path / trail / service
    points: list[Point2D]
    width_m: float
    sketch_road_id: str | None = None  # back-reference if derived from sketch
    district_id: str | None = None  # primary district for which this road was generated
    gameplay_tags: list[str] = Field(default_factory=list)


class Parcel(_Strict):
    id: str
    district_id: str
    polygon: Polygon2D
    parcel_type: ParcelType = ParcelType.MIXED_USE
    frontage_road_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class BuildingFootprint(_Strict):
    id: str
    parcel_id: str
    district_id: str
    polygon: Polygon2D
    height_m: float
    building_type: BuildingType = BuildingType.GENERIC
    style_tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)


class Landmark(_Strict):
    id: str
    name: str
    landmark_type: LandmarkType
    position: Point2D
    height_m: float
    district_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    guidance_payoff: str = ""  # what the landmark "rewards" the player with


class GeneratedSceneSlot(_Strict):
    id: str
    name: str
    district_id: str | None
    position: Point2D
    width_m: float
    depth_m: float
    allowed_scene_types: list[str] = Field(default_factory=list)
    gameplay_role: str = ""
    reason: str = ""
    tags: list[str] = Field(default_factory=list)


class GuidanceCue(_Strict):
    id: str
    cue_type: CueType
    target_id: str
    position: Point2D | None = None
    description: str = ""
    strength: CueStrength = CueStrength.MEDIUM
    tags: list[str] = Field(default_factory=list)


class StageStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


class StageResult(_Strict):
    stage_id: str
    status: StageStatus = StageStatus.IDLE
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    notes: str = ""


class GeneratedLayout(_Strict):
    layout_id: str
    world_id: str | None = None
    scene_id: str | None = None
    document_type: str  # mirrors SketchDocument.document_type
    metrics: GameplayMetrics

    roads: list[GeneratedRoad] = Field(default_factory=list)
    parcels: list[Parcel] = Field(default_factory=list)
    buildings: list[BuildingFootprint] = Field(default_factory=list)
    landmarks: list[Landmark] = Field(default_factory=list)
    scene_slots: list[GeneratedSceneSlot] = Field(default_factory=list)
    guidance_cues: list[GuidanceCue] = Field(default_factory=list)

    stage_results: list[StageResult] = Field(default_factory=list)
