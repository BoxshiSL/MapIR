"""JSON IO and IR discriminator dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.errors import IRLoadError, IRTypeError
from ..core.models import SceneIR, WorldIR


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise IRLoadError(f"cannot read {p}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IRLoadError(f"{p} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise IRLoadError(f"{p} top-level must be an object")
    return data


def load_ir(path: str | Path) -> WorldIR | SceneIR:
    """Read a JSON file and parse it as the right IR based on `ir_type`."""
    data = load_json(path)
    ir_type = data.get("ir_type")
    if ir_type == "world":
        return WorldIR.model_validate(data)
    if ir_type == "scene":
        return SceneIR.model_validate(data)
    raise IRTypeError(f"unknown or missing ir_type={ir_type!r}; expected 'world' or 'scene'")


def dump_text(path: str | Path, content: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
