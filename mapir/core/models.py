"""Pydantic v2 models for WorldIR, SceneIR, AssetRegistry, and Constraints.

This module is the single source of truth for MapIR's data shapes.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    AssetCategory,
    Collision,
    ConstraintType,
    Density,
    EntranceType,
    HeightProfile,
    IRType,
    MarkerType,
    RoadType,
    SceneObjectType,
    ScenePathType,
    ScenePreset,
    SceneType,
    Severity,
    WaterType,
    ZoneType,
)


# ============================================================
# Geometry primitives
# ============================================================

class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point2D(_Frozen):
    x: float
    y: float


class Point3D(_Frozen):
    x: float
    y: float
    z: float


class Size2D(_Frozen):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)


class Size3D(_Frozen):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    height_m: float = Field(gt=0)


class Polygon2D(_Frozen):
    points: list[Point2D]

    @field_validator("points")
    @classmethod
    def _at_least_three(cls, v: list[Point2D]) -> list[Point2D]:
        if len(v) < 3:
            raise ValueError("Polygon2D requires at least 3 points")
        return v


class Transform2D(_Frozen):
    position: Point2D
    rotation_deg: float = 0.0
    scale: float = 1.0


class Transform3D(_Frozen):
    position: Point3D
    rotation_deg: float = 0.0
    scale: float = 1.0


# ============================================================
# Constraints
# ============================================================

class Constraint(_Frozen):
    id: str
    constraint_type: ConstraintType
    target_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.ERROR


# ============================================================
# World IR
# ============================================================

class District(_Frozen):
    id: str
    name: str
    district_type: str
    polygon: Polygon2D
    density: Density = Density.MEDIUM
    height_profile: HeightProfile = HeightProfile.MID
    tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)


class Road(_Frozen):
    id: str
    name: str | None = None
    road_type: RoadType
    points: list[Point2D]
    width_m: float = Field(gt=0)
    tags: list[str] = Field(default_factory=list)

    @field_validator("points")
    @classmethod
    def _at_least_two(cls, v: list[Point2D]) -> list[Point2D]:
        if len(v) < 2:
            raise ValueError("Road requires at least 2 points")
        return v


class WaterBody(_Frozen):
    id: str
    name: str
    water_type: WaterType
    polygon: Polygon2D
    tags: list[str] = Field(default_factory=list)


class POI(_Frozen):
    id: str
    name: str
    poi_type: str
    position: Point2D
    tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)


class SceneSlot(_Frozen):
    id: str
    name: str
    district_id: str | None = None
    position: Point2D
    rotation_deg: float = 0.0
    size: Size2D
    allowed_scene_types: list[SceneType] = Field(default_factory=list)
    connection_rules: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class WorldIR(_Frozen):
    ir_type: Literal[IRType.WORLD] = IRType.WORLD
    version: str = "0.1"
    world_id: str
    name: str
    description: str | None = None
    scale: Size2D
    theme: str
    tags: list[str] = Field(default_factory=list)

    districts: list[District] = Field(default_factory=list)
    roads: list[Road] = Field(default_factory=list)
    water_bodies: list[WaterBody] = Field(default_factory=list)
    pois: list[POI] = Field(default_factory=list)
    scene_slots: list[SceneSlot] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)


# ============================================================
# Scene IR
# ============================================================

class SceneZone(_Frozen):
    id: str
    name: str
    zone_type: ZoneType
    polygon: Polygon2D
    height_m: float | None = None
    tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)


class Entrance(_Frozen):
    id: str
    name: str
    position: Point2D
    entrance_type: EntranceType
    connects_to: str | None = None
    tags: list[str] = Field(default_factory=list)


class ScenePath(_Frozen):
    id: str
    name: str | None = None
    path_type: ScenePathType
    points: list[Point2D]
    width_m: float = Field(gt=0)
    tags: list[str] = Field(default_factory=list)

    @field_validator("points")
    @classmethod
    def _at_least_two(cls, v: list[Point2D]) -> list[Point2D]:
        if len(v) < 2:
            raise ValueError("ScenePath requires at least 2 points")
        return v


class SceneObject(_Frozen):
    id: str
    name: str
    object_type: SceneObjectType
    transform: Transform3D
    size: Size3D
    asset_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)
    locked: bool = False


class GameplayMarker(_Frozen):
    id: str
    marker_type: MarkerType
    position: Point2D
    radius_m: float | None = None
    tags: list[str] = Field(default_factory=list)


class SceneBounds(_Frozen):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    height_m: float = Field(gt=0)


class SceneIR(_Frozen):
    ir_type: Literal[IRType.SCENE] = IRType.SCENE
    version: str = "0.1"
    scene_id: str
    name: str
    description: str | None = None
    scene_type: SceneType
    preset: ScenePreset = ScenePreset.CUSTOM
    standalone: bool = True
    parent_world_id: str | None = None
    parent_scene_slot_id: str | None = None
    bounds: SceneBounds
    theme: str
    tags: list[str] = Field(default_factory=list)

    zones: list[SceneZone] = Field(default_factory=list)
    entrances: list[Entrance] = Field(default_factory=list)
    paths: list[ScenePath] = Field(default_factory=list)
    objects: list[SceneObject] = Field(default_factory=list)
    gameplay_markers: list[GameplayMarker] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)


# ============================================================
# Asset Registry
# ============================================================

class AssetFootprint(_Frozen):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    height_m: float = Field(gt=0)


class AssetTechnical(_Frozen):
    collision: Collision = Collision.SIMPLE
    lod: bool = False
    nanite: bool | None = None
    unit: str = "meter"


class AssetEntry(_Frozen):
    asset_id: str
    name: str
    category: AssetCategory
    source_path: str | None = None
    preview_path: str | None = None
    footprint: AssetFootprint
    tags: list[str] = Field(default_factory=list)
    allowed_scene_types: list[SceneType] = Field(default_factory=list)
    allowed_district_types: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)
    technical: AssetTechnical = Field(default_factory=AssetTechnical)


class AssetRegistry(_Frozen):
    version: str = "0.1"
    name: str = "asset_registry"
    assets: list[AssetEntry] = Field(default_factory=list)


# ============================================================
# Discriminated union for loading
# ============================================================

AnyIR = Annotated[WorldIR | SceneIR, Field(discriminator="ir_type")]
