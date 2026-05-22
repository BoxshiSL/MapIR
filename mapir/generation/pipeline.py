"""Generation pipeline — run stages over a ``SketchDocument``.

Stages (enum ``PipelineStage``):

* ``ZONING``         — no-op in v0.5 (districts come from the sketch).
* ``ROADS``          — :func:`road_generator.generate_roads`.
* ``PARCELS``        — :func:`parcel_generator.generate_parcels`.
* ``BUILDINGS``      — :func:`building_generator.generate_buildings`.
* ``LANDMARKS``      — :func:`landmark_generator.generate_landmarks`.
* ``SCENE_SLOTS``    — :func:`scene_slot_generator.generate_scene_slots`.
* ``GUIDANCE``       — :func:`guidance_generator.generate_guidance` (Phase C
  stub: returns an empty list in Phase B; the stage is wired in now so the
  Generation page can show progress).
* ``CONVERT_TO_IR``  — :func:`mapir.canvas.sketch_to_ir.sketch_to_ir`.
* ``VALIDATE``       — :func:`mapir.core.validation.validate`.

Each stage records a ``StageResult`` on the ``GeneratedLayout``.
"""

from __future__ import annotations

from enum import Enum

from ..core.validation import ValidationReport, validate
from .building_generator import generate_buildings
from .gameplay_metrics import RoadPattern
from .landmark_generator import generate_landmarks
from .layout import GeneratedLayout, StageResult, StageStatus
from .parcel_generator import generate_parcels
from .road_generator import generate_roads
from .scene_slot_generator import generate_scene_slots


class PipelineStage(str, Enum):
    ZONING = "zoning"
    ROADS = "roads"
    PARCELS = "parcels"
    BUILDINGS = "buildings"
    LANDMARKS = "landmarks"
    SCENE_SLOTS = "scene_slots"
    GUIDANCE = "guidance"
    CONVERT_TO_IR = "convert_to_ir"
    VALIDATE = "validate"


_ALL_STAGES: tuple[PipelineStage, ...] = tuple(PipelineStage)


def run_generation_pipeline(
    sketch,
    *,
    stages: list[PipelineStage] | None = None,
    pattern: RoadPattern | None = None,
) -> tuple[GeneratedLayout, ValidationReport | None]:
    """Run the requested stages over a SketchDocument.

    Returns ``(layout, validation_report_or_None)``. The layout is always
    returned even when validation fails — caller decides what to do with it.
    """
    enabled = set(stages or _ALL_STAGES)

    layout = GeneratedLayout(
        layout_id=f"layout_{sketch.sketch_id}",
        world_id=sketch.sketch_id if sketch.document_type == "world" else None,
        scene_id=sketch.sketch_id if sketch.document_type != "world" else None,
        document_type=sketch.document_type,
        metrics=sketch.metrics,
    )

    use_pattern = pattern or _infer_pattern(sketch)

    # Stage: ZONING (no-op; sketches already contain districts).
    if PipelineStage.ZONING in enabled:
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.ZONING.value,
                status=StageStatus.OK,
                notes="Districts taken from sketch (no auto-zoning in v0.5).",
            )
        )

    # Stage: ROADS
    if PipelineStage.ROADS in enabled:
        roads = generate_roads(
            sketch.districts, sketch.metrics, use_pattern, seed=sketch.sketch_id
        )
        layout.roads.extend(roads)
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.ROADS.value,
                status=StageStatus.OK,
                notes=f"Generated {len(roads)} road(s) using {use_pattern.value} pattern.",
            )
        )

    # Stage: PARCELS
    if PipelineStage.PARCELS in enabled:
        parcels = generate_parcels(sketch.districts, sketch.metrics)
        layout.parcels.extend(parcels)
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.PARCELS.value,
                status=StageStatus.OK,
                notes=f"Generated {len(parcels)} parcel(s).",
            )
        )

    # Stage: BUILDINGS
    if PipelineStage.BUILDINGS in enabled:
        buildings = generate_buildings(
            layout.parcels, sketch.districts, sketch.metrics, seed=sketch.sketch_id
        )
        layout.buildings.extend(buildings)
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.BUILDINGS.value,
                status=StageStatus.OK,
                notes=f"Generated {len(buildings)} building footprint(s).",
            )
        )

    # Stage: LANDMARKS
    if PipelineStage.LANDMARKS in enabled:
        landmarks = generate_landmarks(sketch.districts, sketch.metrics)
        layout.landmarks.extend(landmarks)
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.LANDMARKS.value,
                status=StageStatus.OK,
                notes=f"Generated {len(landmarks)} landmark(s).",
            )
        )

    # Stage: SCENE_SLOTS
    if PipelineStage.SCENE_SLOTS in enabled:
        gs = generate_scene_slots(
            sketch.districts, sketch.metrics, existing_slots=list(sketch.scene_slots)
        )
        layout.scene_slots.extend(gs)
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.SCENE_SLOTS.value,
                status=StageStatus.OK,
                notes=f"Generated {len(gs)} scene slot(s) (existing: {len(sketch.scene_slots)}).",
            )
        )

    # Stage: GUIDANCE (Phase C — empty list in Phase B)
    if PipelineStage.GUIDANCE in enabled:
        try:
            from .guidance_generator import generate_guidance  # type: ignore

            cues = generate_guidance(sketch, layout)
        except ImportError:
            cues = []
        layout.guidance_cues.extend(cues)
        layout.stage_results.append(
            StageResult(
                stage_id=PipelineStage.GUIDANCE.value,
                status=StageStatus.OK,
                notes=f"Generated {len(cues)} guidance cue(s).",
            )
        )

    # Stage: CONVERT_TO_IR + VALIDATE
    report: ValidationReport | None = None
    if PipelineStage.CONVERT_TO_IR in enabled or PipelineStage.VALIDATE in enabled:
        from ..canvas.sketch_to_ir import sketch_to_ir

        ir = sketch_to_ir(sketch, layout)
        if PipelineStage.CONVERT_TO_IR in enabled:
            layout.stage_results.append(
                StageResult(
                    stage_id=PipelineStage.CONVERT_TO_IR.value,
                    status=StageStatus.OK,
                    notes=f"Converted SketchDocument to {sketch.document_type.upper()}.",
                )
            )

        if PipelineStage.VALIDATE in enabled:
            report = validate(ir)
            stage_status = StageStatus.OK if report.is_valid else (
                StageStatus.WARN if not report.errors else StageStatus.FAIL
            )
            layout.stage_results.append(
                StageResult(
                    stage_id=PipelineStage.VALIDATE.value,
                    status=stage_status,
                    errors=[i.format() for i in report.errors],
                    warnings=[i.format() for i in report.warnings],
                )
            )

    return layout, report


def _infer_pattern(sketch) -> RoadPattern:
    """Pick a sensible default pattern when the caller doesn't specify one."""
    if not sketch.districts:
        return RoadPattern.GRID
    first = sketch.districts[0]
    return first.road_pattern or RoadPattern.GRID
