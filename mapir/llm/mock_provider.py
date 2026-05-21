"""Deterministic Mock provider for tests and Ollama-less workflows.

Returns hand-crafted Plan JSON for each supported task. The plans are designed
to round-trip through plan_to_ir + validate() with zero errors.
"""

from __future__ import annotations

import json
import time

from .providers import LLMJsonRequest, LLMJsonResponse


class MockProvider:
    name = "mock"

    def is_available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["mock-small", "mock-large"]

    def generate_json(self, request: LLMJsonRequest) -> LLMJsonResponse:
        start = time.perf_counter()
        data = _FIXTURES.get(request.task)
        if data is None:
            elapsed = int((time.perf_counter() - start) * 1000)
            return LLMJsonResponse(
                ok=False,
                raw_text="",
                json_data=None,
                error=f"MockProvider has no fixture for task={request.task!r}",
                provider_name=self.name,
                model_name=request.model or "mock-small",
                elapsed_ms=elapsed,
            )
        raw = json.dumps(data, ensure_ascii=False, indent=2)
        elapsed = int((time.perf_counter() - start) * 1000)
        return LLMJsonResponse(
            ok=True,
            raw_text=raw,
            json_data=data,
            error=None,
            provider_name=self.name,
            model_name=request.model or "mock-small",
            elapsed_ms=elapsed,
        )


_MOCK_WORLD_PLAN: dict = {
    "world_id": "mock_world",
    "name": "Mock Coastal City",
    "theme": "neutral_urban",
    "scale": {"width_m": 3000.0, "depth_m": 2000.0},
    "tags": ["coastal", "compact", "mock"],
    "districts": [
        {
            "id": "old_town",
            "name": "Old Town",
            "district_type": "old_dense",
            "role": "rough dense district",
            "density": "high",
            "height_profile": "low",
            "tags": ["narrow", "historic"],
            "gameplay_tags": ["stealth", "alleys"],
            "adjacency_hints": ["business_core"],
            "required_features": ["narrow_alley"],
        },
        {
            "id": "business_core",
            "name": "Business Core",
            "district_type": "business",
            "role": "central business",
            "density": "very_high",
            "height_profile": "high",
            "tags": ["skyscrapers"],
            "gameplay_tags": ["vertical"],
            "adjacency_hints": ["old_town", "port_zone"],
            "required_features": [],
        },
        {
            "id": "port_zone",
            "name": "Port Zone",
            "district_type": "industrial",
            "role": "industrial port",
            "density": "high",
            "height_profile": "mid",
            "tags": ["port", "containers"],
            "gameplay_tags": ["industrial_combat"],
            "adjacency_hints": ["business_core"],
            "required_features": ["container_yard"],
        },
        {
            "id": "airport_island",
            "name": "Airport Island",
            "district_type": "airport",
            "role": "offshore airport",
            "density": "low",
            "height_profile": "low",
            "tags": ["offshore", "restricted"],
            "gameplay_tags": ["security_high"],
            "adjacency_hints": [],
            "required_features": [],
        },
    ],
    "roads": [
        {
            "id": "primary_loop",
            "name": "Primary Loop",
            "road_type": "primary",
            "connects": ["old_town", "business_core", "port_zone"],
            "role": "main artery",
        },
    ],
    "water_bodies": [
        {"id": "the_sea", "name": "Coastal Sea", "water_type": "sea", "role": "sea"},
        {
            "id": "port_harbor",
            "name": "Port Harbor",
            "water_type": "harbor",
            "role": "harbor",
        },
    ],
    "pois": [
        {
            "id": "old_town_shrine",
            "name": "Old Town Shrine",
            "poi_type": "landmark",
            "district_hint": "old_town",
            "role": "landmark",
        },
        {
            "id": "central_plaza",
            "name": "Central Plaza",
            "poi_type": "plaza",
            "district_hint": "business_core",
            "role": "gathering",
        },
    ],
    "scene_slots": [
        {
            "id": "old_town_alley_slot",
            "name": "Old Town Alley Slot",
            "district_id": "old_town",
            "allowed_scene_types": ["exterior_location"],
            "role": "narrow alley",
        },
        {
            "id": "port_warehouse_slot",
            "name": "Port Warehouse Slot",
            "district_id": "port_zone",
            "allowed_scene_types": ["interior"],
            "role": "warehouse interior",
        },
    ],
}


_MOCK_SCENE_PLAN: dict = {
    "scene_id": "mock_scene",
    "name": "Mock Night Alley",
    "scene_type": "exterior_location",
    "preset": "urban_alley",
    "bounds": {"width_m": 80.0, "depth_m": 45.0, "height_m": 25.0},
    "theme": "neon_urban_night",
    "tags": ["alley", "stealth", "mock"],
    "zones": [
        {"id": "main_alley", "name": "Main Alley", "zone_type": "path", "tags": ["main_path"]},
        {
            "id": "service_yard",
            "name": "Service Yard",
            "zone_type": "service_area",
            "tags": ["dumpsters"],
        },
        {
            "id": "combat_pocket",
            "name": "Combat Pocket",
            "zone_type": "combat_space",
            "tags": [],
        },
    ],
    "entrances": [
        {"id": "ent_main", "name": "Street Main", "entrance_type": "main", "side": "west"},
        {"id": "ent_side", "name": "Side Door", "entrance_type": "side", "side": "north"},
        {
            "id": "ent_service",
            "name": "Service Back",
            "entrance_type": "backdoor",
            "side": "east",
        },
    ],
    "paths": [
        {
            "id": "main_route",
            "name": "Main Route",
            "path_type": "main_route",
            "connects": ["ent_main", "ent_service"],
            "width_m": 3.0,
        },
        {
            "id": "escape_side",
            "name": "Escape via Side",
            "path_type": "escape_route",
            "connects": ["main_alley", "ent_side"],
            "width_m": 2.0,
        },
        {
            "id": "escape_service",
            "name": "Escape via Service",
            "path_type": "escape_route",
            "connects": ["main_alley", "ent_service"],
            "width_m": 2.0,
        },
    ],
    "objects": [
        {
            "id": "dumpster_1",
            "name": "Dumpster A",
            "object_type": "container",
            "width_m": 1.8,
            "depth_m": 1.2,
            "height_m": 1.4,
        },
        {
            "id": "dumpster_2",
            "name": "Dumpster B",
            "object_type": "container",
            "width_m": 1.8,
            "depth_m": 1.2,
            "height_m": 1.4,
        },
    ],
    "gameplay_markers": [
        {"id": "cover_a", "marker_type": "cover", "radius_m": 1.2},
        {"id": "cover_b", "marker_type": "cover", "radius_m": 1.2},
        {"id": "cover_c", "marker_type": "cover", "radius_m": 1.2},
        {"id": "cover_d", "marker_type": "cover", "radius_m": 1.2},
        {"id": "cover_e", "marker_type": "cover", "radius_m": 1.2},
        {"id": "ambush_1", "marker_type": "ambush"},
    ],
    "constraints": [
        {
            "id": "c_min_entrances",
            "constraint_type": "must_have_min_entrances",
            "target_id": None,
            "params": {"min": 3},
            "severity": "error",
        },
        {
            "id": "c_min_escape",
            "constraint_type": "must_have_min_escape_routes",
            "target_id": None,
            "params": {"min": 2},
            "severity": "error",
        },
        {
            "id": "c_min_cover",
            "constraint_type": "must_have_min_cover_markers",
            "target_id": None,
            "params": {"min": 5},
            "severity": "error",
        },
    ],
}


_MOCK_DISTRICT_PROFILE: dict = {
    "district_id": "old_town",
    "description": "Dense old-town district with narrow alleys and historic landmarks.",
    "density": "high",
    "height_profile": "low",
    "street_pattern": "irregular_grid",
    "landmark_types": ["shrine", "market"],
    "scene_slot_suggestions": ["narrow_alley", "rooftop_chase"],
    "gameplay_tags": ["stealth", "alleys", "verticality"],
    "forbidden_tags": ["wide_boulevard"],
    "validation_notes": ["Keep at least one scene_slot inside the district."],
}


_FIXTURES: dict[str, dict] = {
    "world_zoning": _MOCK_WORLD_PLAN,
    "scene_planning": _MOCK_SCENE_PLAN,
    "district_profile": _MOCK_DISTRICT_PROFILE,
    # For repair_ir we just echo a "fixed" world plan; the repair pipeline calls
    # the provider with task="repair_ir" — returning a known-good world plan is
    # sufficient for the deterministic round-trip tests.
    "repair_ir": _MOCK_WORLD_PLAN,
}
