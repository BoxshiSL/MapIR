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
from .core.validation import ValidationReport, validate as run_validation
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
        err_console.print(Panel.fit(_format_pydantic_error(exc),
                                    title=f"[red]Invalid IR structure[/red] - {path}",
                                    border_style="red"))
        raise typer.Exit(code=1)
    except MapIRError as exc:
        err_console.print(f"[red]ERROR[/red] {exc}")
        raise typer.Exit(code=1)


def _format_pydantic_error(exc: ValidationError) -> str:
    lines: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"[yellow]{loc}[/yellow]: {err['msg']} ({err['type']})")
    return "\n".join(lines) or str(exc)


def _print_report(report: ValidationReport, *, title: str) -> None:
    if not report.all():
        console.print(Panel.fit(f"[green]OK[/green]  {title}\n"
                                "no issues.", border_style="green"))
        return
    table = Table(title=title, show_lines=False, header_style="bold")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Message")
    table.add_column("Path", style="dim")
    color = {"error": "red", "warning": "yellow", "info": "cyan"}
    for issue in report.all():
        sev = issue.severity.value
        table.add_row(f"[{color.get(sev, 'white')}]{sev.upper()}[/]",
                      issue.code, issue.message, issue.path)
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
        table.add_row("Bounds",
                      f"{scene.bounds.width_m} x {scene.bounds.depth_m} x {scene.bounds.height_m} m")
        table.add_row("Standalone", str(scene.standalone))
        table.add_row("Zones", str(len(scene.zones)))
        table.add_row("Entrances", str(len(scene.entrances)))
        table.add_row("Paths", str(len(scene.paths)))
        table.add_row("Objects", str(len(scene.objects)))
        table.add_row("Gameplay markers", str(len(scene.gameplay_markers)))
        table.add_row("Constraints", str(len(scene.constraints)))

    table.add_row("Validation",
                  ("[green]ok[/green]"
                   if report.is_valid
                   else f"[red]{len(report.errors)} error(s)[/red]"))
    table.add_row("Warnings", str(len(report.warnings)))
    console.print(Panel(table, title=f"MapIR - inspect {path.name}", border_style="cyan"))

    if report.errors or report.warnings:
        _print_report(report, title="Issues")


if __name__ == "__main__":  # pragma: no cover
    app()
