"""MapIR command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core.errors import MapIRError
from .core.models import SceneIR, WorldIR
from .core.validation import ValidationReport
from .core.validation import validate as run_validation
from .export import blender_exporter, obj_exporter
from .render import svg_renderer
from .utils.io import dump_text, load_ir

app = typer.Typer(
    name="mapir",
    help="MapIR - generate, describe, validate and export game spaces.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# ============================================================
# Loading helper (turns exceptions into nice exits)
# ============================================================


def _load_or_exit(path: Path) -> WorldIR | SceneIR:
    try:
        return load_ir(path)
    except ValidationError as exc:
        err_console.print(
            Panel.fit(
                _format_pydantic_error(exc),
                title=f"[red]Invalid IR structure[/red] - {path}",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc
    except MapIRError as exc:
        err_console.print(f"[red]ERROR[/red] {exc}")
        raise typer.Exit(code=1) from exc


def _format_pydantic_error(exc: ValidationError) -> str:
    lines: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"[yellow]{loc}[/yellow]: {err['msg']} ({err['type']})")
    return "\n".join(lines) or str(exc)


def _print_report(report: ValidationReport, *, title: str) -> None:
    if not report.all():
        console.print(Panel.fit(f"[green]OK[/green]  {title}\n" "no issues.", border_style="green"))
        return
    table = Table(title=title, show_lines=False, header_style="bold")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Message")
    table.add_column("Path", style="dim")
    color = {"error": "red", "warning": "yellow", "info": "cyan"}
    for issue in report.all():
        sev = issue.severity.value
        table.add_row(
            f"[{color.get(sev, 'white')}]{sev.upper()}[/]", issue.code, issue.message, issue.path
        )
    console.print(table)


# ============================================================
# Commands
# ============================================================


@app.command()
def validate(path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True)) -> None:
    """Validate a WorldIR or SceneIR JSON file (structural + semantic)."""
    ir = _load_or_exit(path)
    report = run_validation(ir)
    label = f"{ir.ir_type.value.upper()} - {getattr(ir, 'name', '?')}"
    _print_report(report, title=label)
    if not report.is_valid:
        raise typer.Exit(code=1)


@app.command(name="render-svg")
def render_svg(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out", "-o", help="Output .svg path"),
) -> None:
    """Render a WorldIR or SceneIR as a 2D SVG preview."""
    ir = _load_or_exit(path)
    report = run_validation(ir)
    if not report.is_valid:
        err_console.print("[red]Cannot render: input has validation errors.[/red]")
        _print_report(report, title=f"{ir.ir_type.value} validation")
        raise typer.Exit(code=1)
    svg = svg_renderer.render(ir)
    dump_text(out, svg)
    console.print(f"[green]wrote[/green] {out}  ({len(svg):,} bytes)")


@app.command(name="export-obj")
def export_obj(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out", "-o", help="Output .obj path"),
) -> None:
    """Export a simple blockout OBJ from a WorldIR or SceneIR."""
    ir = _load_or_exit(path)
    text = obj_exporter.export(ir)
    dump_text(out, text)
    console.print(f"[green]wrote[/green] {out}  ({len(text):,} bytes)")


@app.command(name="export-blender")
def export_blender(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out", "-o", help="Output .py path"),
) -> None:
    """Export a Blender Python script that builds a blockout."""
    ir = _load_or_exit(path)
    script = blender_exporter.export(ir)
    dump_text(out, script)
    console.print(f"[green]wrote[/green] {out}  ({len(script):,} bytes)")


@app.command()
def desktop(
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Headless smoke mode: build the window, then exit without showing it.",
    ),
) -> None:
    """Launch MapIR Studio — the PySide6 desktop application."""
    from .desktop.app import run  # lazy import keeps CLI startup fast

    code = run(headless=no_browser)
    if code != 0:
        raise typer.Exit(code=code)


@app.command()
def ui(
    no_browser: bool = typer.Option(False, "--no-browser", help="Headless smoke mode."),
) -> None:
    """[Deprecated] Alias for ``desktop`` — kept for backwards compatibility."""
    err_console.print(
        "[yellow]deprecation[/yellow] "
        "[dim]`mapir ui` is deprecated; use `mapir desktop` instead.[/dim]"
    )
    from .desktop.app import run

    code = run(headless=no_browser)
    if code != 0:
        raise typer.Exit(code=code)


@app.command()
def preflight() -> None:
    """Scan the repository for the kind of damage that has bitten this project.

    Checks for one-line-corruption, broken Python files, invalid TOML/JSON,
    missing README structure, and merged requirements lines. Read-only.
    """
    from scripts.preflight import main as preflight_main  # local import

    code = preflight_main()
    if code != 0:
        raise typer.Exit(code=code)


# ============================================================
# Local LLM drafting
# ============================================================


def _make_provider(provider_name: str, base_url: str | None, settings):
    """Build a LocalLLMProvider from the user's provider choice."""
    from .llm import MockProvider, OllamaProvider

    name = (provider_name or "ollama").lower()
    if name == "mock":
        return MockProvider()
    if name == "ollama":
        return OllamaProvider(
            base_url=base_url or settings.base_url,
            timeout_seconds=settings.timeout_seconds,
            structured_output=settings.structured_output,
        )
    raise typer.BadParameter(f"unknown provider {provider_name!r} (expected 'ollama' or 'mock')")


def _read_brief(brief: str | None, brief_file: Path | None) -> str:
    if brief and brief_file:
        raise typer.BadParameter("pass only one of --brief or --brief-file")
    if brief_file:
        return brief_file.read_text(encoding="utf-8").strip()
    if brief:
        return brief.strip()
    raise typer.BadParameter("either --brief or --brief-file is required")


def _print_draft_result(result, *, output_path: Path | None = None) -> None:
    color = "green" if result.ok else "red"
    title = (
        f"[{color}]{result.task}[/{color}] "
        f"provider={result.provider_name} model={result.model_name or '—'}"
    )
    console.print(Panel.fit(title, border_style=color))
    if result.validation_report is not None:
        _print_report(result.validation_report, title="Validation")
    if result.errors:
        err_console.print("[red]Errors:[/red]")
        for e in result.errors[:10]:
            err_console.print(f"  - {e}")
    if output_path is not None and result.ok:
        console.print(f"[green]wrote[/green] {output_path}")


@app.command(name="llm-check")
def llm_check(
    provider: str = typer.Option("ollama", help="Provider: 'ollama' or 'mock'"),
    model: str | None = typer.Option(None, help="Model name (e.g. 'qwen3:8b')"),
    base_url: str | None = typer.Option(None, help="Override Ollama base URL"),
    list_models: bool = typer.Option(False, "--list-models", help="Print available models"),
) -> None:
    """Check that the local LLM provider is available and (optionally) list models."""
    from .llm import load_settings

    settings = load_settings()
    if model:
        settings.model = model

    prov = _make_provider(provider, base_url, settings)
    available = prov.is_available()
    if available:
        console.print(
            Panel.fit(f"[green]OK[/green] provider={prov.name} reachable", border_style="green")
        )
    else:
        console.print(
            Panel.fit(
                f"[red]UNAVAILABLE[/red] provider={prov.name}\n"
                f"If using Ollama, start it locally (default http://127.0.0.1:11434)\n"
                f"and pull a model, e.g.:  ollama pull {settings.model}",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if list_models:
        models = prov.list_models()
        if models:
            console.print("[bold]Available models:[/bold]")
            for m in models:
                console.print(f"  - {m}")
        else:
            console.print("[yellow]No models reported by the provider.[/yellow]")


def _write_ir_json(out: Path, ir_json: dict) -> None:
    import json

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ir_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@app.command(name="llm-draft-world")
def llm_draft_world(
    out: Path = typer.Option(..., "--out", "-o", help="Output IR JSON path"),
    brief: str | None = typer.Option(None, help="User brief text"),
    brief_file: Path | None = typer.Option(None, help="Path to a file containing the brief"),
    provider: str = typer.Option("ollama"),
    model: str | None = typer.Option(None),
    base_url: str | None = typer.Option(None),
    temperature: float | None = typer.Option(None),
    no_repair: bool = typer.Option(False, "--no-repair", help="Disable validation-driven repair"),
) -> None:
    """Draft a WorldIR JSON from a user brief using a local LLM."""
    from .llm import draft_world_from_brief, load_settings

    settings = load_settings()
    if model:
        settings.model = model
    if temperature is not None:
        settings.temperature = temperature
    if no_repair:
        settings.enable_repair = False

    prov = _make_provider(provider, base_url, settings)
    text = _read_brief(brief, brief_file)
    result = draft_world_from_brief(text, prov, settings)

    if result.ir_json is not None:
        _write_ir_json(out, result.ir_json)
    _print_draft_result(result, output_path=out if result.ir_json is not None else None)

    if not result.ok:
        raise typer.Exit(code=1)


@app.command(name="llm-draft-scene")
def llm_draft_scene(
    out: Path = typer.Option(..., "--out", "-o", help="Output IR JSON path"),
    brief: str | None = typer.Option(None, help="User brief text"),
    brief_file: Path | None = typer.Option(None, help="Path to a file containing the brief"),
    provider: str = typer.Option("ollama"),
    model: str | None = typer.Option(None),
    base_url: str | None = typer.Option(None),
    temperature: float | None = typer.Option(None),
    no_repair: bool = typer.Option(False, "--no-repair", help="Disable validation-driven repair"),
) -> None:
    """Draft a SceneIR JSON from a user brief using a local LLM."""
    from .llm import draft_scene_from_brief, load_settings

    settings = load_settings()
    if model:
        settings.model = model
    if temperature is not None:
        settings.temperature = temperature
    if no_repair:
        settings.enable_repair = False

    prov = _make_provider(provider, base_url, settings)
    text = _read_brief(brief, brief_file)
    result = draft_scene_from_brief(text, prov, settings)

    if result.ir_json is not None:
        _write_ir_json(out, result.ir_json)
    _print_draft_result(result, output_path=out if result.ir_json is not None else None)

    if not result.ok:
        raise typer.Exit(code=1)


@app.command(name="llm-repair")
def llm_repair(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out", "-o", help="Output repaired IR JSON path"),
    provider: str = typer.Option("ollama"),
    model: str | None = typer.Option(None),
    base_url: str | None = typer.Option(None),
) -> None:
    """Repair an invalid WorldIR/SceneIR JSON via local LLM, then re-validate."""
    import json as _json

    from .llm import load_settings
    from .llm.repair import repair_invalid_ir
    from .utils.io import load_json

    settings = load_settings()
    if model:
        settings.model = model
    prov = _make_provider(provider, base_url, settings)

    raw = load_json(input_path)
    ir_type = raw.get("ir_type")
    if ir_type not in {"world", "scene"}:
        err_console.print(f"[red]Cannot repair: missing or unknown ir_type={ir_type!r}[/red]")
        raise typer.Exit(code=1)

    # Parse + validate to produce a ValidationReport we can hand to the model.
    try:
        ir = load_ir(input_path)
        report = run_validation(ir)
    except (ValidationError, MapIRError):
        # Synthesise a single-issue report when the IR doesn't even parse.
        from .core.validation import ValidationIssue, ValidationReport

        report = ValidationReport()
        report.add(
            ValidationIssue(
                "structural_parse_failure",
                "Input did not parse as IR; pydantic/structural error",
            )
        )

    if report.is_valid:
        console.print("[green]Input is already valid — nothing to repair.[/green]")
        _write_ir_json(out, raw)
        return

    repaired = repair_invalid_ir(
        invalid_json=raw,
        validation_report=report,
        provider=prov,
        settings=settings,
        expected_type=ir_type,  # type: ignore[arg-type]
    )
    if repaired is None:
        err_console.print("[red]Repair failed — provider returned no usable JSON.[/red]")
        raise typer.Exit(code=1)

    # Validate the repaired output before writing.
    try:
        ir2 = (
            WorldIR.model_validate(repaired)
            if ir_type == "world"
            else SceneIR.model_validate(repaired)
        )
    except ValidationError as exc:
        err_console.print(
            "[red]Repair produced a document that still fails structural validation:[/red]"
        )
        err_console.print(_format_pydantic_error(exc))
        # Still write it out so the user can inspect.
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_json.dumps(repaired, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        raise typer.Exit(code=1) from exc
    report2 = run_validation(ir2)
    _print_report(report2, title=f"Repaired {ir_type} validation")
    _write_ir_json(out, repaired)
    if not report2.is_valid:
        raise typer.Exit(code=1)


@app.command()
def inspect(path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True)) -> None:
    """Print a quick summary of an IR file."""
    ir = _load_or_exit(path)
    report = run_validation(ir)

    table = Table(show_header=False, box=None)
    table.add_row("[bold]Type[/bold]", ir.ir_type.value)
    if isinstance(ir, WorldIR):
        table.add_row("[bold]ID[/bold]", ir.world_id)
        table.add_row("[bold]Name[/bold]", ir.name)
        table.add_row("[bold]Theme[/bold]", ir.theme)
        table.add_row("[bold]Scale[/bold]", f"{ir.scale.width_m} x {ir.scale.depth_m} m")
        table.add_row("Districts", str(len(ir.districts)))
        table.add_row("Roads", str(len(ir.roads)))
        table.add_row("Water bodies", str(len(ir.water_bodies)))
        table.add_row("POIs", str(len(ir.pois)))
        table.add_row("Scene slots", str(len(ir.scene_slots)))
        table.add_row("Constraints", str(len(ir.constraints)))
    else:
        scene: SceneIR = ir
        table.add_row("[bold]ID[/bold]", scene.scene_id)
        table.add_row("[bold]Name[/bold]", scene.name)
        table.add_row("[bold]Theme[/bold]", scene.theme)
        table.add_row("[bold]Scene type[/bold]", scene.scene_type.value)
        table.add_row("[bold]Preset[/bold]", scene.preset.value)
        table.add_row(
            "Bounds", f"{scene.bounds.width_m} x {scene.bounds.depth_m} x {scene.bounds.height_m} m"
        )
        table.add_row("Standalone", str(scene.standalone))
        table.add_row("Zones", str(len(scene.zones)))
        table.add_row("Entrances", str(len(scene.entrances)))
        table.add_row("Paths", str(len(scene.paths)))
        table.add_row("Objects", str(len(scene.objects)))
        table.add_row("Gameplay markers", str(len(scene.gameplay_markers)))
        table.add_row("Constraints", str(len(scene.constraints)))

    table.add_row(
        "Validation",
        ("[green]ok[/green]" if report.is_valid else f"[red]{len(report.errors)} error(s)[/red]"),
    )
    table.add_row("Warnings", str(len(report.warnings)))
    console.print(Panel(table, title=f"MapIR - inspect {path.name}", border_style="cyan"))

    if report.errors or report.warnings:
        _print_report(report, title="Issues")


# ============================================================
# v0.5 commands — templates, sketch-from-template, deterministic layout,
# design validation, design report.
# ============================================================


@app.command("templates")
def cmd_templates() -> None:
    """List the bundled v0.5 template gallery."""
    from .generation.templates import load_all_templates

    templates = load_all_templates()
    table = Table(title="MapIR v0.5 templates", show_lines=False, header_style="bold")
    table.add_column("template_id")
    table.add_column("type")
    table.add_column("genre")
    table.add_column("size")
    table.add_column("profiles")
    table.add_column("name")
    for tpl in sorted(templates.values(), key=lambda t: (t.document_type, t.template_id)):
        size = f"{int(tpl.default_size.width_m)}x{int(tpl.default_size.depth_m)}"
        profiles = ",".join(p.value for p in tpl.default_gameplay_profiles)
        table.add_row(
            tpl.template_id,
            tpl.document_type,
            tpl.genre,
            size,
            profiles,
            tpl.name,
        )
    console.print(table)


@app.command("new-from-template")
def cmd_new_from_template(
    template_id: str = typer.Argument(..., help="Template id from `mapir templates`."),
    out: Path = typer.Option(..., "--out", help="Output JSON path for the SketchDocument."),
) -> None:
    """Create a fresh SketchDocument from a template and write it to disk."""
    from .canvas.sketch_state import new_sketch_document
    from .generation.templates import get_template

    try:
        tpl = get_template(template_id)
    except KeyError as exc:
        err_console.print(f"[red]ERROR[/red] {exc}")
        raise typer.Exit(code=1) from exc
    sketch = new_sketch_document(tpl)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_text(out, sketch.model_dump_json(indent=2) + "\n")
    console.print(
        Panel.fit(
            f"[green]OK[/green]  wrote SketchDocument for [bold]{tpl.name}[/bold]\n"
            f"path: {out}",
            border_style="green",
        )
    )


@app.command("generate-layout")
def cmd_generate_layout(
    sketch: Path = typer.Argument(..., exists=True, dir_okay=False, help="SketchDocument JSON."),
    out: Path = typer.Option(..., "--out", help="Output JSON path for the GeneratedLayout."),
) -> None:
    """Run the deterministic generation pipeline on a SketchDocument JSON."""
    from .canvas.sketch_models import SketchDocument
    from .generation.pipeline import run_generation_pipeline

    data = sketch.read_text(encoding="utf-8")
    try:
        document = SketchDocument.model_validate_json(data)
    except ValidationError as exc:
        err_console.print(
            Panel.fit(
                _format_pydantic_error(exc),
                title=f"[red]Invalid SketchDocument[/red] - {sketch}",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    layout, report = run_generation_pipeline(document)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_text(out, layout.model_dump_json(indent=2) + "\n")
    n_err = len(report.errors) if report else 0
    panel = (
        f"[green]OK[/green]  GeneratedLayout written to {out}\n"
        f"roads={len(layout.roads)} parcels={len(layout.parcels)} "
        f"buildings={len(layout.buildings)} landmarks={len(layout.landmarks)} "
        f"scene_slots={len(layout.scene_slots)} guidance={len(layout.guidance_cues)}\n"
        f"validation errors={n_err}"
    )
    console.print(Panel.fit(panel, border_style="green" if n_err == 0 else "yellow"))


@app.command("validate-design")
def cmd_validate_design(
    target: Path = typer.Argument(..., exists=True, dir_okay=False, help="WorldIR/SceneIR JSON."),
    layout_path: Path | None = typer.Option(
        None, "--layout", help="Optional GeneratedLayout JSON for richer checks."
    ),
) -> None:
    """Run the v0.5 design-aware validators on an IR (optionally with a layout)."""
    from .design.validators import run_design_validators
    from .generation.gameplay_metrics import GameplayMetrics
    from .generation.layout import GeneratedLayout

    ir = _load_or_exit(target)
    layout: GeneratedLayout | None = None
    if layout_path is not None:
        if not layout_path.exists():
            err_console.print(f"[red]ERROR[/red] layout file {layout_path} not found")
            raise typer.Exit(code=1)
        try:
            layout = GeneratedLayout.model_validate_json(
                layout_path.read_text(encoding="utf-8")
            )
        except ValidationError as exc:
            err_console.print(
                Panel.fit(
                    _format_pydantic_error(exc),
                    title=f"[red]Invalid layout[/red] - {layout_path}",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc
    metrics = layout.metrics if layout is not None else GameplayMetrics()

    design = run_design_validators(ir, layout, metrics)
    if not design.warnings:
        console.print(
            Panel.fit(
                f"[green]OK[/green]  design rules: no findings on {target.name}.",
                border_style="green",
            )
        )
        return
    table = Table(title=f"Design findings - {target.name}", header_style="bold")
    table.add_column("severity")
    table.add_column("category")
    table.add_column("code")
    table.add_column("message")
    table.add_column("rule")
    color = {"error": "red", "warning": "yellow", "info": "cyan"}
    for w in design.warnings:
        sev = w.severity.value
        table.add_row(
            f"[{color.get(sev, 'white')}]{sev.upper()}[/]",
            w.category.value,
            w.code,
            w.message,
            w.rule_id or "",
        )
    console.print(table)
    if design.errors():
        raise typer.Exit(code=1)


@app.command("export-design-report")
def cmd_export_design_report(
    target: Path = typer.Argument(..., exists=True, dir_okay=False, help="WorldIR/SceneIR JSON."),
    out: Path = typer.Option(..., "--out", help="Output Markdown path."),
    layout_path: Path | None = typer.Option(
        None, "--layout", help="Optional GeneratedLayout JSON."
    ),
) -> None:
    """Write a Markdown design report bundling structural + design findings."""
    from .design.reports import build_design_report_markdown
    from .design.validators import run_design_validators
    from .generation.gameplay_metrics import GameplayMetrics
    from .generation.layout import GeneratedLayout

    ir = _load_or_exit(target)
    layout: GeneratedLayout | None = None
    if layout_path is not None and layout_path.exists():
        layout = GeneratedLayout.model_validate_json(
            layout_path.read_text(encoding="utf-8")
        )
    metrics = layout.metrics if layout is not None else GameplayMetrics()
    structural = run_validation(ir)
    design = run_design_validators(ir, layout, metrics)
    md = build_design_report_markdown(ir, layout, structural, design)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_text(out, md)
    console.print(
        Panel.fit(
            f"[green]OK[/green]  design report written to {out}",
            border_style="green",
        )
    )


if __name__ == "__main__":  # pragma: no cover
    app()
