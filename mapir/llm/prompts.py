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


# ============================================================
# v0.5 prompts — template-aware, gameplay-metrics-aware, design-rule-aware
# ============================================================


_TEMPLATE_BRIEF_SYSTEM = (
    "You are a senior creative director planning a game world at the "
    "template / vision level. Given a neutral template and a user brief, "
    "produce a concise WorldPlan JSON that respects the template's genre "
    "and gameplay profiles. Geometry is created later by deterministic "
    "code; do NOT invent coordinates."
)


_DISTRICT_GEN_SYSTEM = (
    "You are a senior level designer working on a specific district. Given "
    "the district's profile (type, role, gameplay tags, metrics, local "
    "brief) and curated design rules, propose a DistrictPlan JSON: street "
    "pattern hints, landmark types, scene-slot suggestions, and gameplay "
    "tags. Stay terse; geometry is generated deterministically."
)


_ROAD_NETWORK_SYSTEM = (
    "You are a senior open-world layout planner. Given a district's bbox, "
    "gameplay metrics, and a desired road pattern, propose a RoadIntentPlan "
    "JSON: arterial / collector / local / alley intent (counts + style), "
    "without coordinates. Match driving profiles to wider arterials and "
    "stealth profiles to denser alleys."
)


_BUILDING_STYLE_SYSTEM = (
    "You are a senior environment-art director. Given a district's style, "
    "density, and parcel count, propose a BuildingStylePlan JSON: building "
    "types per parcel category, height_profile, and silhouette notes. "
    "Treat the existing GeneratedLayout as authoritative geometry."
)


_GUIDANCE_SYSTEM = (
    "You are a senior level designer focusing on player guidance. Given "
    "the generated landmarks, scene slots, and roads, plus curated "
    "guidance design rules, propose a GuidancePlan JSON: leading lines, "
    "breadcrumbs, light/contrast cues, sound cues, negative-space hints. "
    "Cite the rule id from the provided design rules block where useful."
)


_REPAIR_LAYOUT_SYSTEM = (
    "You are a strict JSON repair tool for MapIR v0.5 GeneratedLayouts. "
    "Given an invalid layout (or the IR derived from it) and a list of "
    "validation errors (structural + design-aware), return a corrected "
    "JSON document that fixes every listed error. STRICT JSON ONLY."
)


def build_template_world_brief_prompt(
    template_name: str,
    genre: str,
    user_brief: str,
    gameplay_profiles: list[str],
    design_hints: list[str] | None = None,
) -> tuple[str, str]:
    """v0.5: prompt for drafting a WorldPlan from a neutral template + user brief."""
    profiles = ", ".join(gameplay_profiles) or "(none specified)"
    hints_block = (
        "\nCurated design hints:\n" + "\n".join(design_hints)
        if design_hints
        else ""
    )
    user = (
        f"Template name: {template_name}\n"
        f"Genre: {genre}\n"
        f"Gameplay profiles: {profiles}\n\n"
        f"User brief:\n{user_brief.strip()}\n"
        f"{hints_block}\n\n"
        "Produce a WorldPlan with: world_id, name, theme, tags[], scale "
        "{width_m, depth_m}, districts[], roads[], pois[], scene_slots[].\n"
        "Reference template defaults when not overridden by the brief.\n\n"
        f"{_JSON_RULES}"
    )
    return _TEMPLATE_BRIEF_SYSTEM, user


def build_district_generation_prompt(
    district_id: str,
    district_summary: str,
    metrics_summary: str,
    local_brief: str,
    design_hints: list[str] | None = None,
) -> tuple[str, str]:
    """v0.5: prompt for a per-district plan with metrics + design rules baked in."""
    hints_block = (
        "\nCurated design hints:\n" + "\n".join(design_hints)
        if design_hints
        else ""
    )
    user = (
        f"District id: {district_id}\n\n"
        f"District summary:\n{district_summary}\n\n"
        f"Gameplay metrics summary:\n{metrics_summary}\n\n"
        f"Local LLM brief:\n{local_brief.strip() or '(none)'}\n"
        f"{hints_block}\n\n"
        "Produce a DistrictPlan with: district_id, name, district_type, role, "
        "theme, density, height_profile, street_pattern, landmark_types[], "
        "scene_slot_suggestions[], gameplay_tags[], forbidden_tags[], "
        "validation_notes[].\n\n"
        f"{_JSON_RULES}"
    )
    return _DISTRICT_GEN_SYSTEM, user


def build_road_network_prompt(
    district_id: str,
    bbox_summary: str,
    metrics_summary: str,
    pattern: str,
) -> tuple[str, str]:
    user = (
        f"District id: {district_id}\n"
        f"BBox summary: {bbox_summary}\n"
        f"Pattern: {pattern}\n\n"
        f"Gameplay metrics summary:\n{metrics_summary}\n\n"
        "Produce a RoadIntentPlan with: district_id, pattern, arterial_intent "
        "(count, style notes), collector_intent, local_intent, alley_intent, "
        "service_intent.\n"
        "Do NOT supply coordinates. Stay terse.\n\n"
        f"{_JSON_RULES}"
    )
    return _ROAD_NETWORK_SYSTEM, user


def build_building_style_prompt(
    district_id: str,
    district_style: str,
    parcel_count: int,
    parcel_type_breakdown: str,
) -> tuple[str, str]:
    user = (
        f"District id: {district_id}\n"
        f"District style: {district_style}\n"
        f"Parcel count: {parcel_count}\n"
        f"Parcel type breakdown:\n{parcel_type_breakdown}\n\n"
        "Produce a BuildingStylePlan with: district_id, primary_style, "
        "building_types[] (one entry per parcel category — residential, "
        "commercial, industrial, civic, landmark, mixed_use, rural, "
        "forest_clearing), height_profile, silhouette_notes.\n\n"
        f"{_JSON_RULES}"
    )
    return _BUILDING_STYLE_SYSTEM, user


def build_guidance_cues_prompt(
    landmark_summary: str,
    scene_slot_summary: str,
    road_summary: str,
    design_hints: list[str] | None = None,
) -> tuple[str, str]:
    hints_block = (
        "\nCurated guidance design rules:\n" + "\n".join(design_hints)
        if design_hints
        else ""
    )
    user = (
        f"Landmarks:\n{landmark_summary}\n\n"
        f"Scene slots:\n{scene_slot_summary}\n\n"
        f"Roads:\n{road_summary}\n"
        f"{hints_block}\n\n"
        "Produce a GuidancePlan with: cues[] entries each having "
        "{id, cue_type (landmark | breadcrumb | leading_line | "
        "light_contrast | color_signifier | sound_cue | negative_space | "
        "affordance | vista), target_id, description, strength "
        "(subtle | medium | strong), rule_id (optional, cite from design hints)}.\n\n"
        f"{_JSON_RULES}"
    )
    return _GUIDANCE_SYSTEM, user


def build_repair_generated_layout_prompt(
    invalid_json: dict,
    errors: list[str],
) -> tuple[str, str]:
    import json as _json

    pretty = _json.dumps(invalid_json, indent=2, ensure_ascii=False)
    err_block = "\n".join(f"- {e}" for e in errors) or "- (no specific errors provided)"
    user = (
        f"Validation errors to fix:\n{err_block}\n\n"
        f"Invalid layout / IR:\n{pretty}\n\n"
        "Return the corrected JSON document. Preserve ids, names, and intent. "
        "Fix every listed error.\n\n"
        f"{_JSON_RULES}"
    )
    return _REPAIR_LAYOUT_SYSTEM, user


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
