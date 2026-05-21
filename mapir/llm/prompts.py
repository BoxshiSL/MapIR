"""Prompt templates for the local LLM drafting layer.

All prompts demand strict JSON only — no Markdown fences, no commentary, no
trailing text. The Plan models accept extra fields gracefully so a slightly
chatty model still parses; but explicit instructions keep clean models clean.
"""

from __future__ import annotations

_JSON_RULES = """\
Output rules — these are non-negotiable:
- Return STRICT JSON only.
- Do NOT wrap output in Markdown code fences.
- Do NOT add commentary, explanation, or text before/after the JSON object.
- Do NOT invent fields outside the schema.
- All ids use snake_case ASCII.
- Preserve user intent. Do not silently drop required features.
"""

_WORLD_SYSTEM = (
    "You are a senior game-world layout planner. Given a user brief, produce a "
    "compact WorldPlan as JSON. Geometry is created later by deterministic code, "
    "so DO NOT invent polygon coordinates. Focus on names, types, roles, and "
    "relationships between districts, roads, water bodies, POIs, and scene slots."
)

_SCENE_SYSTEM = (
    "You are a senior level designer. Given a user brief, produce a compact "
    "ScenePlan as JSON. Geometry is created later by deterministic code; you "
    "DO NOT supply coordinates. Focus on zones, entrances, paths, objects, "
    "markers, and constraints that capture gameplay intent."
)

_DISTRICT_SYSTEM = (
    "You are a senior urban planner. Given a world context and a district id, "
    "produce a DistrictProfile JSON describing density, street pattern, "
    "landmark types, scene-slot suggestions, and gameplay tags."
)

_REPAIR_SYSTEM = (
    "You are a strict JSON repair tool. Given an invalid Plan or IR document "
    "and the list of validation errors, return a corrected JSON document that "
    "preserves user intent while fixing every listed error. STRICT JSON ONLY."
)


def build_world_zoning_prompt(brief: str) -> tuple[str, str]:
    user = (
        f"User brief:\n{brief.strip()}\n\n"
        "Required output: a WorldPlan object with these top-level fields:\n"
        "  world_id (snake_case), name, theme, tags,\n"
        "  scale {width_m, depth_m},\n"
        "  districts[] {id, name, district_type, role, density, height_profile, "
        "tags, gameplay_tags, adjacency_hints, required_features},\n"
        "  roads[] {id, name, road_type, connects[], role},\n"
        "  water_bodies[] {id, name, water_type, role},\n"
        "  pois[] {id, name, poi_type, district_hint, role},\n"
        "  scene_slots[] {id, name, district_id, allowed_scene_types[], role}.\n"
        "Include at least one district AND at least one scene_slot. "
        "Use district ids from districts[] when referencing district_id/district_hint.\n\n"
        f"{_JSON_RULES}"
    )
    return _WORLD_SYSTEM, user


def build_scene_planning_prompt(brief: str) -> tuple[str, str]:
    user = (
        f"User brief:\n{brief.strip()}\n\n"
        "Required output: a ScenePlan object with these top-level fields:\n"
        "  scene_id (snake_case), name, scene_type "
        "('exterior_location' or 'interior'), preset, theme, tags,\n"
        "  bounds {width_m, depth_m, height_m},\n"
        "  zones[] {id, name, zone_type, role, tags},\n"
        "  entrances[] {id, name, entrance_type, side ('north'|'south'|'east'|'west'), "
        "connects_to},\n"
        "  paths[] {id, name, path_type, connects[], width_m},\n"
        "  objects[] {id, name, object_type, role, width_m, depth_m, height_m},\n"
        "  gameplay_markers[] {id, marker_type, role, radius_m},\n"
        "  constraints[] {id, constraint_type, target_id, params, severity}.\n"
        "Include at least one zone AND at least one entrance. "
        "For interior scenes, include at least one room/service_area/storage/private_area zone. "
        "For exterior scenes, include at least one path OR an exterior_yard/combat_space zone.\n\n"
        f"{_JSON_RULES}"
    )
    return _SCENE_SYSTEM, user


def build_district_profile_prompt(
    world_summary: str, district_id: str, brief: str
) -> tuple[str, str]:
    user = (
        f"World context:\n{world_summary.strip()}\n\n"
        f"Target district id: {district_id}\n\n"
        f"User brief:\n{brief.strip()}\n\n"
        "Required output: a DistrictProfile object with fields:\n"
        "  district_id, description, density, height_profile, street_pattern,\n"
        "  landmark_types[], scene_slot_suggestions[], gameplay_tags[],\n"
        "  forbidden_tags[], validation_notes[].\n\n"
        f"{_JSON_RULES}"
    )
    return _DISTRICT_SYSTEM, user


def build_repair_prompt(
    invalid_json: dict,
    errors: list[str],
    expected_type: str,
    schema_summary: str = "",
) -> tuple[str, str]:
    import json as _json

    pretty = _json.dumps(invalid_json, indent=2, ensure_ascii=False)
    err_block = "\n".join(f"- {e}" for e in errors) or "- (no specific errors provided)"
    schema_hint = f"\nExpected schema summary:\n{schema_summary}\n" if schema_summary else ""
    user = (
        f"Expected document type: {expected_type}\n\n"
        f"Validation errors to fix:\n{err_block}\n"
        f"{schema_hint}\n"
        f"Invalid document:\n{pretty}\n\n"
        "Return the corrected JSON document. Preserve original ids, names, and "
        "user intent. Fix every error listed above.\n\n"
        f"{_JSON_RULES}"
    )
    return _REPAIR_SYSTEM, user
