"""Build deterministic demo fixtures from the v0.5 template gallery.

Used by:

* tests (``examples/demos/*.json`` are validator-friendly fixtures);
* ``validate_examples.bat`` / ``render_examples.bat`` /
  ``export_blockout_examples.bat`` after the old Jissō / Luga examples were
  removed in v0.5.

This is a *minimal* runner that delegates the actual template-to-IR
conversion to :mod:`mapir.generation.template_instantiation`. The full v0.5
generation pipeline (parcels / buildings / landmarks / guidance) lives under
``mapir.generation`` and is wired in during Phase B.

Run from the repo root::

    .venv\\Scripts\\python.exe scripts\\build_demo_fixtures.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mapir.core.validation import validate
from mapir.generation.template_instantiation import instantiate
from mapir.generation.templates import get_template, load_all_templates

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "examples" / "demos"

# Demo selection: one per document_type. Other templates remain loadable via
# ``mapir templates`` and the Wizard.
DEMO_SELECTION = {
    "world": "world_modern_island_city",
    "scene": "scene_industrial_port",
    "interior": "interior_warehouse",
}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_all(out_dir: Path = DEMO_DIR) -> list[Path]:
    """Build all demo fixtures. Returns list of generated paths."""
    load_all_templates()  # validate the whole gallery first
    generated: list[Path] = []

    for kind, tpl_id in DEMO_SELECTION.items():
        tpl = get_template(tpl_id)
        ir = instantiate(tpl, name_override=f"[Demo] {tpl.name}")
        report = validate(ir)
        if not report.is_valid:
            raise SystemExit(
                f"{kind} demo from {tpl.template_id} fails validation:\n"
                + "\n".join(i.format() for i in report.errors)
            )
        path = out_dir / f"demo_{tpl.template_id}.json"
        _write_json(path, ir.model_dump(mode="json"))
        generated.append(path)

    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEMO_DIR,
        help="Output directory (default: examples/demos/).",
    )
    args = parser.parse_args()
    generated = build_all(args.out)
    for p in generated:
        rel = p.relative_to(ROOT) if p.is_absolute() else p
        print(f"wrote {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
