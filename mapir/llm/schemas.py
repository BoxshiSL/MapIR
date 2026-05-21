"""Plan schemas for LLM output.

The LLM produces high-level semantic Plans (no precise polygon coords);
plan_to_ir.py turns those into valid WorldIR/SceneIR. Plans are intentionally
forgiving (extra="ignore") so a model that adds an unknown field still parses.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _PlanBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ============================================================
# World plan
# ============================================================


class ScalePlan(_PlanBase):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)


class DistrictPlan(_PlanBase):
    id: str
    name: str
    district_type: str = "mixed"
    role: str | None = None
    density: str = "medium"
    height_profile: str = "mid"
    tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)
    adjacency_hints: list[str] = Field(default_factory=list)
    required_features: list[str] = Field(default_factory=list)


class RoadPlan(_PlanBase):
    id: str
    name: str | None = None
    road_type: str = "primary"
    connects: list[str] = Field(default_factory=list)
    role: str | None = None
    width_m: float = 8.0


class WaterPlan(_PlanBase):
    id: str
    name: str = "water"
    water_type: str = "sea"
    role: str | None = None


class POIPlan(_PlanBase):
    id: str
    name: str
    poi_type: str = "landmark"
    district_hint: str | None = None
    role: str | None = None


class SceneSlotPlan(_PlanBase):
    id: str
    name: str
    district_id: str | None = None
    allowed_scene_types: list[str] = Field(default_factory=lambda: ["exterior_location"])
    role: str | None = None
    width_m: float = 60.0
    depth_m: float = 40.0


class WorldPlan(_PlanBase):
    world_id: str
    name: str
    theme: str = "neutral"
    scale: ScalePlan
    tags: list[str] = Field(default_factory=list)
    districts: list[DistrictPlan] = Field(default_factory=list)
    roads: list[RoadPlan] = Field(default_factory=list)
    water_bodies: list[WaterPlan] = Field(default_factory=list)
    pois: list[POIPlan] = Field(default_factory=list)
    scene_slots: list[SceneSlotPlan] = Field(default_factory=list)


# ============================================================
# District profile (returned separately, not embedded in WorldPlan)
# ============================================================


class DistrictProfile(_PlanBase):
    district_id: str
    description: str = ""
    density: str = "medium"
    height_profile: str = "mid"
    street_pattern: str = "grid"
    landmark_types: list[str] = Field(default_factory=list)
    scene_slot_suggestions: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)
    forbidden_tags: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)


# ============================================================
# Scene plan
# ============================================================


class BoundsPlan(_PlanBase):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    height_m: float = Field(default=20.0, gt=0)


class ZonePlan(_PlanBase):
    id: str
    name: str
    zone_type: str = "path"
    role: str | None = None
    tags: list[str] = Field(default_factory=list)


class EntrancePlan(_PlanBase):
    id: str
    name: str
    entrance_type: str = "main"
    side: str | None = None  # "north"|"south"|"east"|"west" — used as a hint
    connects_to: str | None = None


class PathPlan(_PlanBase):
    id: str
    name: str | None = None
    path_type: str = "main_route"
    connects: list[str] = Field(default_factory=list)  # zone or entrance ids
    width_m: float = 3.0


class ObjectPlan(_PlanBase):
    id: str
    name: str
    object_type: str = "prop"
    role: str | None = None
    width_m: float = 1.5
    depth_m: float = 1.5
    height_m: float = 2.0


class MarkerPlan(_PlanBase):
    id: str
    marker_type: str = "cover"
    role: str | None = None
    radius_m: float | None = None


class ConstraintPlan(_PlanBase):
    id: str
    constraint_type: str
    target_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    severity: str = "error"


class ScenePlan(_PlanBase):
    scene_id: str
    name: str
    scene_type: str = "exterior_location"
    preset: str = "custom"
    bounds: BoundsPlan
    theme: str = "neutral"
    tags: list[str] = Field(default_factory=list)
    zones: list[ZonePlan] = Field(default_factory=list)
    entrances: list[EntrancePlan] = Field(default_factory=list)
    paths: list[PathPlan] = Field(default_factory=list)
    objects: list[ObjectPlan] = Field(default_factory=list)
    gameplay_markers: list[MarkerPlan] = Field(default_factory=list)
    constraints: list[ConstraintPlan] = Field(default_factory=list)


# ============================================================
# JSON schemas for Ollama structured output
# ============================================================
#
# These are intentionally compact: enough hint for the model to emit the right
# shape, but not so strict that a slightly-off response is rejected pre-parse.
# Pydantic does the real validation on the parsed dict.


def world_plan_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["world_id", "name", "scale", "districts", "scene_slots"],
        "properties": {
            "world_id": {"type": "string"},
            "name": {"type": "string"},
            "theme": {"type": "string"},
            "scale": {
                "type": "object",
                "required": ["width_m", "depth_m"],
                "properties": {
                    "width_m": {"type": "number"},
                    "depth_m": {"type": "number"},
                },
            },
            "tags": {"type": "array", "items": {"type": "string"}},
            "districts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "district_type": {"type": "string"},
                        "role": {"type": "string"},
                        "density": {"type": "string"},
                        "height_profile": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "gameplay_tags": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "roads": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "road_type": {"type": "string"},
                        "connects": {"type": "array", "items": {"type": "string"}},
                        "role": {"type": "string"},
                    },
                },
            },
            "water_bodies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "water_type": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
            },
            "pois": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "poi_type": {"type": "string"},
                        "district_hint": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
            },
            "scene_slots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "district_id": {"type": "string"},
                        "allowed_scene_types": {"type": "array", "items": {"type": "string"}},
                        "role": {"type": "string"},
                    },
                },
            },
        },
    }


def scene_plan_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["scene_id", "name", "bounds", "zones", "entrances"],
        "properties": {
            "scene_id": {"type": "string"},
            "name": {"type": "string"},
            "scene_type": {"type": "string"},
            "preset": {"type": "string"},
            "bounds": {
                "type": "object",
                "required": ["width_m", "depth_m"],
                "properties": {
                    "width_m": {"type": "number"},
                    "depth_m": {"type": "number"},
                    "height_m": {"type": "number"},
                },
            },
            "theme": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "zones": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "zone_type": {"type": "string"},
                        "role": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "entrances": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "entrance_type": {"type": "string"},
                        "side": {"type": "string"},
                        "connects_to": {"type": "string"},
                    },
                },
            },
            "paths": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "path_type": {"type": "string"},
                        "connects": {"type": "array", "items": {"type": "string"}},
                        "width_m": {"type": "number"},
                    },
                },
            },
            "objects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "object_type": {"type": "string"},
                        "role": {"type": "string"},
                        "width_m": {"type": "number"},
                        "depth_m": {"type": "number"},
                        "height_m": {"type": "number"},
                    },
                },
            },
            "gameplay_markers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "marker_type": {"type": "string"},
                        "role": {"type": "string"},
                        "radius_m": {"type": "number"},
                    },
                },
            },
        },
    }


def district_profile_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["district_id"],
        "properties": {
            "district_id": {"type": "string"},
            "description": {"type": "string"},
            "density": {"type": "string"},
            "height_profile": {"type": "string"},
            "street_pattern": {"type": "string"},
            "landmark_types": {"type": "array", "items": {"type": "string"}},
            "scene_slot_suggestions": {"type": "array", "items": {"type": "string"}},
            "gameplay_tags": {"type": "array", "items": {"type": "string"}},
            "forbidden_tags": {"type": "array", "items": {"type": "string"}},
            "validation_notes": {"type": "array", "items": {"type": "string"}},
        },
    }
