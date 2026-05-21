from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from mapir.core.models import SceneIR, WorldIR
from mapir.core.validation import validate
from mapir.utils.io import load_ir


def _ids(report) -> set[str]:
    return {iss.code for iss in report.all()}


def test_all_world_examples_validate(world_files: list[Path]) -> None:
    assert world_files, "no world example files found"
    for f in world_files:
        ir = load_ir(f)
        assert isinstance(ir, WorldIR)
        report = validate(ir)
        assert report.is_valid, (
            f"{f.name} had errors: " + ", ".join(i.format() for i in report.errors)
        )


def test_all_scene_examples_validate(scene_files: list[Path]) -> None:
    assert scene_files, "no scene example files found"
    for f in scene_files:
        ir = load_ir(f)
        assert isinstance(ir, SceneIR)
        report = validate(ir)
        assert report.is_valid, (
            f"{f.name} had errors: " + ", ".join(i.format() for i in report.errors)
        )


def test_polygon_requires_at_least_three_points() -> None:
    with pytest.raises(ValidationError):
        WorldIR.model_validate({
            "ir_type": "world",
            "world_id": "w1", "name": "w", "theme": "x",
            "scale": {"width_m": 100, "depth_m": 100},
            "districts": [{
                "id": "d1", "name": "d1", "district_type": "x",
                "polygon": {"points": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]},
            }],
            "scene_slots": [{
                "id": "s1", "name": "s1",
                "position": {"x": 1, "y": 1},
                "size": {"width_m": 1, "depth_m": 1},
            }],
        })


def test_scene_slot_unknown_district_reference_is_error() -> None:
    world = WorldIR.model_validate({
        "ir_type": "world",
        "world_id": "w1", "name": "w", "theme": "x",
        "scale": {"width_m": 100, "depth_m": 100},
        "districts": [{
            "id": "d1", "name": "d1", "district_type": "x",
            "polygon": {"points": [
                {"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}
            ]},
        }],
        "scene_slots": [{
            "id": "s1", "name": "s1",
            "district_id": "DOES_NOT_EXIST",
            "position": {"x": 5, "y": 5},
            "size": {"width_m": 4, "depth_m": 4},
        }],
    })
    report = validate(world)
    assert not report.is_valid
    assert "scene_slot_unknown_district" in _ids(report)


def test_min_entrances_constraint_triggers() -> None:
    scene = SceneIR.model_validate({
        "ir_type": "scene",
        "scene_id": "s1", "name": "s", "theme": "x",
        "scene_type": "exterior_location",
        "bounds": {"width_m": 50, "depth_m": 50, "height_m": 10},
        "zones": [{
            "id": "z1", "name": "z1", "zone_type": "combat_space",
            "polygon": {"points": [
                {"x": 1, "y": 1}, {"x": 10, "y": 1}, {"x": 10, "y": 10}, {"x": 1, "y": 10}
            ]},
        }],
        "entrances": [{
            "id": "e1", "name": "e1", "position": {"x": 1, "y": 1},
            "entrance_type": "main",
        }],
        "constraints": [{
            "id": "c1", "constraint_type": "must_have_min_entrances",
            "params": {"min": 3},
        }],
    })
    report = validate(scene)
    assert not report.is_valid
    assert "min_entrances_unmet" in _ids(report)


def test_unsupported_constraint_is_warning_not_error() -> None:
    scene = SceneIR.model_validate({
        "ir_type": "scene",
        "scene_id": "s1", "name": "s", "theme": "x",
        "scene_type": "exterior_location",
        "bounds": {"width_m": 50, "depth_m": 50, "height_m": 10},
        "zones": [{
            "id": "z1", "name": "z1", "zone_type": "combat_space",
            "polygon": {"points": [
                {"x": 1, "y": 1}, {"x": 10, "y": 1}, {"x": 10, "y": 10}, {"x": 1, "y": 10}
            ]},
        }],
        "entrances": [{
            "id": "e1", "name": "e1", "position": {"x": 1, "y": 1},
            "entrance_type": "main",
        }],
        "constraints": [{
            "id": "c1", "constraint_type": "must_connect_to_road",
        }],
    })
    report = validate(scene)
    assert report.is_valid  # warning only
    assert "unsupported_constraint" in {iss.code for iss in report.warnings}
