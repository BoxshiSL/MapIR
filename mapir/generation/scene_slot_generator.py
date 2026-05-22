"""Scene slot generator.

Strategy: every district with a "major" role gets at least one scene slot.
The gameplay role of the slot is derived from the district's primary
gameplay profile.
"""

from __future__ import annotations

from ..core.models import Point2D, Polygon2D
from .gameplay_metrics import GameplayMetrics, GameplayProfile
from .layout import GeneratedSceneSlot


def _centroid(polygon: Polygon2D) -> Point2D:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return Point2D(x=sum(xs) / len(xs), y=sum(ys) / len(ys))


def _gameplay_role(profiles: list[GameplayProfile]) -> str:
    if not profiles:
        return "encounter"
    primary = profiles[0]
    return {
        GameplayProfile.DRIVING: "vehicle_event",
        GameplayProfile.STEALTH: "stealth_objective",
        GameplayProfile.SHOOTER: "combat_arena",
        GameplayProfile.PARKOUR: "rooftop_traversal",
        GameplayProfile.EXPLORATION: "vista_or_secret",
    }.get(primary, "encounter")


def generate_scene_slots(
    sketch_districts: list,
    metrics: GameplayMetrics,
    *,
    existing_slots: list | None = None,
) -> list[GeneratedSceneSlot]:
    existing_slots = existing_slots or []
    have_for: set[str] = {
        getattr(s, "district_id", None)
        for s in existing_slots
        if getattr(s, "district_id", None)
    }
    out: list[GeneratedSceneSlot] = []
    for d in sketch_districts:
        if d.id in have_for:
            continue
        role = _gameplay_role(d.gameplay_profiles or metrics.gameplay_profiles)
        c = _centroid(d.polygon)
        # size is relative but capped: a reasonable default that fits inside
        # most district bboxes
        width_m = 20.0
        depth_m = 15.0
        out.append(
            GeneratedSceneSlot(
                id=f"gs_{d.id}",
                name=f"{d.name} Encounter",
                district_id=d.id,
                position=c,
                width_m=width_m,
                depth_m=depth_m,
                allowed_scene_types=["exterior_location"],
                gameplay_role=role,
                reason=f"Auto-placed because district has profile {role}.",
                tags=["from_generator"],
            )
        )
    return out
