"""v0.5: template gallery sanity tests.

Every JSON file under ``mapir/data/templates/`` must validate as a
``TemplateDefinition``. IDs must be unique across the gallery, and the
gallery must cover all three document types (world / scene / interior).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mapir.generation.gameplay_metrics import GameplayProfile
from mapir.generation.template_instantiation import instantiate
from mapir.generation.templates import (
    DistrictPreset,
    TemplateDefinition,
    get_template,
    load_all_templates,
    templates_by_type,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "mapir" / "data" / "templates"


def test_templates_directory_exists() -> None:
    assert TEMPLATES_DIR.is_dir(), "mapir/data/templates/ must exist in v0.5"


def test_at_least_thirteen_templates_present() -> None:
    files = sorted(TEMPLATES_DIR.glob("*.json"))
    assert len(files) >= 13, f"expected ≥13 templates, found {len(files)}"


def test_all_templates_load_and_validate() -> None:
    templates = load_all_templates(force=True)
    assert len(templates) >= 13
    for tpl_id, tpl in templates.items():
        assert isinstance(tpl, TemplateDefinition)
        assert tpl.template_id == tpl_id
        assert tpl.name
        assert tpl.document_type in ("world", "scene", "interior")
        assert tpl.default_size.width_m > 0
        assert tpl.default_size.depth_m > 0


def test_template_ids_are_unique() -> None:
    files = sorted(TEMPLATES_DIR.glob("*.json"))
    seen: set[str] = set()
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        tpl_id = data["template_id"]
        assert tpl_id not in seen, f"duplicate template_id {tpl_id!r}"
        seen.add(tpl_id)


def test_gallery_covers_all_three_document_types() -> None:
    assert len(templates_by_type("world")) >= 1
    assert len(templates_by_type("scene")) >= 1
    assert len(templates_by_type("interior")) >= 1


def test_gameplay_profiles_use_valid_enum_values() -> None:
    valid = {p.value for p in GameplayProfile}
    for tpl in load_all_templates().values():
        for profile in tpl.default_gameplay_profiles:
            assert profile.value in valid


def test_get_template_raises_on_unknown_id() -> None:
    with pytest.raises(KeyError):
        get_template("does_not_exist")


def test_district_presets_have_valid_bboxes() -> None:
    for tpl in load_all_templates().values():
        for preset in tpl.default_districts:
            assert isinstance(preset, DistrictPreset)
            assert len(preset.bbox) == 4
            x0, y0, x1, y1 = preset.bbox
            assert x1 > x0, f"{tpl.template_id}/{preset.name}: bbox x1≤x0"
            assert y1 > y0, f"{tpl.template_id}/{preset.name}: bbox y1≤y0"


def test_every_template_instantiates_to_valid_ir() -> None:
    """Each template must produce an IR that passes structural + semantic
    validation when run through ``instantiate``."""
    from mapir.core.validation import validate

    for tpl in load_all_templates().values():
        ir = instantiate(tpl)
        report = validate(ir)
        assert report.is_valid, (
            f"template {tpl.template_id} instantiated to invalid IR:\n"
            + "\n".join(i.format() for i in report.errors)
        )
