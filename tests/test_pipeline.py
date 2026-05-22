"""v0.5 Phase B: generation pipeline + sketch→IR converter."""

from __future__ import annotations

import pytest

from mapir.canvas.sketch_state import new_sketch_document
from mapir.canvas.sketch_to_ir import sketch_to_ir
from mapir.core.models import SceneIR, WorldIR
from mapir.core.validation import validate
from mapir.generation.layout import GeneratedLayout
from mapir.generation.pipeline import PipelineStage, run_generation_pipeline
from mapir.generation.templates import get_template, load_all_templates


@pytest.mark.parametrize(
    "tpl_id",
    [
        "world_modern_island_city",
        "world_medieval_magical_forest",
        "world_cyberpunk_dense_district",
        "scene_industrial_port",
        "scene_urban_alley",
        "interior_warehouse",
        "interior_office_floor",
    ],
)
def test_pipeline_runs_end_to_end(tpl_id: str) -> None:
    sketch = new_sketch_document(get_template(tpl_id))
    layout, report = run_generation_pipeline(sketch)
    assert isinstance(layout, GeneratedLayout)
    assert layout.roads, f"{tpl_id}: expected at least one road"
    assert layout.parcels, f"{tpl_id}: expected at least one parcel"
    assert layout.buildings, f"{tpl_id}: expected at least one building"
    assert layout.landmarks, f"{tpl_id}: expected at least one landmark"
    assert report is not None
    assert report.is_valid, f"{tpl_id}: generated IR fails validation"


def test_pipeline_subset_skips_disabled_stages() -> None:
    sketch = new_sketch_document(get_template("scene_industrial_port"))
    layout, _ = run_generation_pipeline(
        sketch,
        stages=[PipelineStage.ROADS, PipelineStage.LANDMARKS, PipelineStage.CONVERT_TO_IR],
    )
    assert layout.roads
    assert layout.landmarks
    assert not layout.parcels  # parcels stage was disabled
    assert not layout.buildings


def test_sketch_to_ir_world_preserves_district_count() -> None:
    sketch = new_sketch_document(get_template("world_modern_island_city"))
    layout, _ = run_generation_pipeline(sketch)
    ir = sketch_to_ir(sketch, layout)
    assert isinstance(ir, WorldIR)
    assert len(ir.districts) == len(sketch.districts)
    assert validate(ir).is_valid


def test_sketch_to_ir_interior_marks_room() -> None:
    sketch = new_sketch_document(get_template("interior_warehouse"))
    layout, _ = run_generation_pipeline(sketch)
    ir = sketch_to_ir(sketch, layout)
    assert isinstance(ir, SceneIR)
    assert ir.scene_type.value == "interior"
    # At least one interior-type zone present
    interior_set = {"room", "service_area", "storage", "private_area"}
    assert any(z.zone_type.value in interior_set for z in ir.zones)


def test_every_template_pipeline_produces_valid_ir() -> None:
    for tpl_id, tpl in load_all_templates().items():
        sketch = new_sketch_document(tpl)
        layout, report = run_generation_pipeline(sketch)
        assert report is not None
        assert report.is_valid, (
            f"{tpl_id}: pipeline IR invalid:\n"
            + "\n".join(i.format() for i in report.errors)
        )
        # All buildings reference a real parcel
        parcel_ids = {p.id for p in layout.parcels}
        for b in layout.buildings:
            assert b.parcel_id in parcel_ids
