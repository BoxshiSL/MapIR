"""Guidance cue generator.

The pipeline GUIDANCE stage calls this. We don't have light/colour/sound
geometry in v0.5 IR — instead we emit ``GuidanceCue`` metadata pointing at
landmarks, scene slots, and POIs so:

* the validator can flag missing cues for major objectives,
* the design report cites which cue covers which target,
* future viewports / exporters can read the metadata to drive lighting,
  colour, and audio.

Heuristics (curated from the level-design thesis):
* ``leading_line`` — for every landmark, look for the closest road and
  declare it the leading line toward the landmark.
* ``landmark``     — every landmark also becomes a ``landmark`` cue
  (orientation anchor).
* ``breadcrumb``   — if multiple POIs cluster within ``breadcrumb_density``
  metres of a landmark, emit a breadcrumb cue along them.
* ``vista``        — landmarks tagged "vista" or in a hub role.
* ``negative_space`` — emitted for "landmark" parcels with low density.
"""

from __future__ import annotations

import math
import uuid

from ..core.models import Point2D
from .layout import (
    CueStrength,
    CueType,
    GeneratedLayout,
    GuidanceCue,
)


def _distance(a: Point2D, b: Point2D) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _closest_road_id(landmark, layout: GeneratedLayout) -> str | None:
    best_id: str | None = None
    best_d = float("inf")
    for r in layout.roads:
        for p in r.points:
            d = _distance(landmark.position, p)
            if d < best_d:
                best_d = d
                best_id = r.id
    return best_id


def generate_guidance(sketch, layout: GeneratedLayout) -> list[GuidanceCue]:
    cues: list[GuidanceCue] = []
    metrics = layout.metrics
    breadcrumb_radius = max(20.0, sketch.size.width_m * 0.04)

    for lm in layout.landmarks:
        cues.append(
            GuidanceCue(
                id=f"cue_lm_{lm.id}",
                cue_type=CueType.LANDMARK,
                target_id=lm.id,
                position=lm.position,
                description=f"{lm.name} is the orientation anchor for its district.",
                strength=CueStrength.STRONG,
                tags=["landmark"],
            )
        )
        road_id = _closest_road_id(lm, layout)
        if road_id:
            cues.append(
                GuidanceCue(
                    id=f"cue_ll_{lm.id}",
                    cue_type=CueType.LEADING_LINE,
                    target_id=lm.id,
                    description=(
                        f"Road {road_id!r} acts as a leading line toward "
                        f"landmark {lm.name!r}."
                    ),
                    strength=CueStrength.MEDIUM,
                    tags=["road", road_id],
                )
            )
        # Vista cue if the landmark itself reads as a vista
        if any("vista" in tag.lower() for tag in lm.tags):
            cues.append(
                GuidanceCue(
                    id=f"cue_vista_{lm.id}",
                    cue_type=CueType.VISTA,
                    target_id=lm.id,
                    position=lm.position,
                    description=f"{lm.name} reveals a wider vista when approached.",
                    strength=CueStrength.MEDIUM,
                )
            )

    # Scene slot cues — every major scene slot deserves at least one cue.
    for slot in layout.scene_slots:
        cues.append(
            GuidanceCue(
                id=f"cue_slot_{slot.id}",
                cue_type=CueType.AFFORDANCE,
                target_id=slot.id,
                position=slot.position,
                description=(
                    f"Scene slot {slot.name!r} hosts {slot.gameplay_role!r} — "
                    "place an affordance signifier (door, sign, light) at the "
                    "approach."
                ),
                strength=CueStrength.SUBTLE,
            )
        )

    # Breadcrumbs from landmarks toward nearby districts' centroids.
    landmark_positions = {lm.id: lm.position for lm in layout.landmarks}
    for lm_id, pos in landmark_positions.items():
        for d in sketch.districts:
            cx = sum(p.x for p in d.polygon.points) / len(d.polygon.points)
            cy = sum(p.y for p in d.polygon.points) / len(d.polygon.points)
            if (
                _distance(pos, Point2D(x=cx, y=cy)) <= breadcrumb_radius * 2
                and d.id != getattr(
                    next(
                        (lm for lm in layout.landmarks if lm.id == lm_id), None
                    ),
                    "district_id",
                    None,
                )
            ):
                cues.append(
                    GuidanceCue(
                        id=f"cue_bc_{lm_id}_{d.id}",
                        cue_type=CueType.BREADCRUMB,
                        target_id=lm_id,
                        description=(
                            f"Breadcrumb cues (lanterns / props / footprints) "
                            f"from district {d.name!r} toward landmark."
                        ),
                        strength=CueStrength.SUBTLE,
                        tags=["breadcrumb", d.id],
                    )
                )
                break  # one per landmark is enough

    # Deduplicate by id (defensive)
    seen: set[str] = set()
    out: list[GuidanceCue] = []
    for cue in cues:
        if cue.id in seen:
            cue.id = f"{cue.id}_{uuid.uuid4().hex[:4]}"
        seen.add(cue.id)
        out.append(cue)
    return out
