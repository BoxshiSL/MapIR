"""v0.5: end-to-end mock workflow.

Template → Sketch → Pipeline → IR → Validate → Render SVG → Export OBJ.
Uses the Mock LLM provider implicitly (no Ollama). All deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mapir.canvas.sketch_state import new_sketch_document
from mapir.canvas.sketch_to_ir import sketch_to_ir
from mapir.core.validation import validate
from mapir.export import blender_exporter, obj_exporter
from mapir.generation.pipeline import run_generation_pipeline
from mapir.generation.templates import get_template
from mapir.render.svg_renderer import render


@pytest.mark.parametrize(
    "tpl_id",
    [
        "world_modern_island_city",
        "scene_industrial_port",
        "interior_warehouse",
    ],
)
def test_full_v05_workflow(tpl_id: str, tmp_path: Path) -> None:
    # 1. Pick template
    tpl = get_template(tpl_id)
    # 2. Sketch
    sketch = new_sketch_document(tpl)
    assert sketch.template_id == tpl_id
    # 3. Pipeline
    layout, _report = run_generation_pipeline(sketch)
    # 4. Convert
    ir = sketch_to_ir(sketch, layout)
    # 5. Validate
    report = validate(ir)
    assert report.is_valid, "\n".join(i.format() for i in report.errors)
    # 6. SVG
    svg = render(ir, label_scale=0.8)
    assert svg.startswith("<svg")
    (tmp_path / f"{tpl_id}.svg").write_text(svg, encoding="utf-8")
    # 7. OBJ
    obj = obj_exporter.export(ir)
    assert "v " in obj
    assert "f " in obj
    (tmp_path / f"{tpl_id}.obj").write_text(obj, encoding="utf-8")
    # 8. Blender Python script
    script = blender_exporter.export(ir)
    compile(script, "blender.py", "exec")
