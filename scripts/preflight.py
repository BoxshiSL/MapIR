"""MapIR repository preflight scanner.

Catches the kind of damage that has bitten this project before:

  * source files collapsed into a single line (lost newlines);
  * Python files that no longer compile;
  * pyproject.toml that fails to parse;
  * requirements.txt with several packages glued on one line;
  * JSON examples / schemas that are not valid JSON;
  * CI workflow files reduced to a single line;
  * batch files collapsed to one line;
  * README.md emptied of its top-level heading or shrunk to a stub.

The scanner is **read-only**. It exits 0 on success and 1 when any error is
found. Warnings never fail the scan but are surfaced in the report.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT_ENV = "MAPIR_REPO_ROOT"

# A file is "suspiciously single-line" if it has > MIN_BYTES_FOR_LINE_CHECK
# bytes but < MIN_LINES_REQUIRED lines. Tuned to match the spec.
MIN_BYTES_FOR_LINE_CHECK = 500
MIN_LINES_REQUIRED = 3

LINE_CHECK_EXTENSIONS = {".py", ".toml", ".yml", ".yaml", ".bat", ".md"}

# Files allowed to be tiny stubs even if they exist (e.g. package markers).
ALLOWED_TINY_FILES = {
    Path("scripts/__init__.py"),
    Path("mapir/__init__.py"),  # only ~7 lines; spec section 23 still passes.
    Path("mapir/core/__init__.py"),
    Path("mapir/export/__init__.py"),
    Path("mapir/render/__init__.py"),
    Path("mapir/utils/__init__.py"),
    Path("mapir/desktop/__init__.py"),
    Path("mapir/desktop/widgets/__init__.py"),
    Path("tests/__init__.py"),
}


@dataclass
class PreflightIssue:
    severity: str  # "error" | "warning"
    code: str
    path: str
    message: str


@dataclass
class PreflightReport:
    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, path: Path | str, message: str) -> None:
        self.issues.append(PreflightIssue("error", code, str(path), message))

    def warn(self, code: str, path: Path | str, message: str) -> None:
        self.issues.append(PreflightIssue("warning", code, str(path), message))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _iter_files(root: Path, pattern: str, *, skip_dirs: Iterable[str] = ()) -> Iterable[Path]:
    skip = {Path(s) for s in skip_dirs}
    for p in root.rglob(pattern):
        if any(
            part
            in {
                ".venv",
                ".git",
                ".pytest_cache",
                "build",
                "dist",
                "__pycache__",
                "mapir.egg-info",
                "output",
                ".claude",
            }
            for part in p.parts
        ):
            continue
        rel = p.relative_to(root)
        if any(rel.is_relative_to(s) for s in skip):  # type: ignore[arg-type]
            continue
        yield p


def _check_one_line_corruption(root: Path, report: PreflightReport) -> None:
    """Flag files that are large but have basically no newlines."""
    targets: list[Path] = []
    for ext in LINE_CHECK_EXTENSIONS:
        targets.extend(_iter_files(root, f"*{ext}"))

    for path in targets:
        rel = path.relative_to(root)
        if rel in ALLOWED_TINY_FILES:
            continue
        try:
            size = path.stat().st_size
        except OSError as exc:
            report.error("preflight_io", rel, f"cannot stat: {exc}")
            continue
        if size <= MIN_BYTES_FOR_LINE_CHECK:
            continue
        text = _read_text(path)
        if text is None:
            report.error("preflight_io", rel, "cannot read as UTF-8")
            continue
        line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
        if line_count < MIN_LINES_REQUIRED:
            report.error(
                "one_line_corruption",
                rel,
                f"{size} bytes but only {line_count} line(s) "
                "— suspected one-line/lost-newlines corruption",
            )


def _check_python(root: Path, report: PreflightReport) -> None:
    for path in _iter_files(root, "*.py"):
        rel = path.relative_to(root)
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            report.error("py_compile", rel, f"compile failed: {exc.msg.strip()}")


def _check_pyproject(root: Path, report: PreflightReport) -> None:
    path = root / "pyproject.toml"
    if not path.exists():
        report.error("pyproject_missing", path.relative_to(root), "pyproject.toml not found")
        return
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        report.error("pyproject_parse", path.relative_to(root), f"TOML parse failed: {exc}")
        return
    if "project" not in data:
        report.error("pyproject_shape", path.relative_to(root), "missing [project] table")


def _check_requirements(root: Path, report: PreflightReport) -> None:
    for name in ("requirements.txt", "requirements-dev.txt"):
        path = root / name
        if not path.exists():
            continue
        text = _read_text(path) or ""
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-r "):
                continue
            # A legitimate requirement line has only one specifier, no spaces
            # outside of version markers like ; python_version<"3.12".
            head = line.split(";", 1)[0]
            if re.search(r"[a-zA-Z0-9_\-]+(==|>=|<=|>|<|~=|!=|\s)+\S+\s+[a-zA-Z]", head):
                # Heuristic: bare word followed by another bare word usually
                # means two packages glued on one line.
                report.warn(
                    "requirements_merged",
                    f"{path.relative_to(root)}:{lineno}",
                    f"line looks like multiple packages: {raw!r}",
                )


def _check_json(root: Path, report: PreflightReport) -> None:
    candidates: list[Path] = []
    for subdir in ("examples", "mapir/schemas"):
        sd = root / subdir
        if sd.is_dir():
            candidates.extend(sd.rglob("*.json"))
    for path in candidates:
        rel = path.relative_to(root)
        text = _read_text(path)
        if text is None:
            report.error("json_io", rel, "cannot read as UTF-8")
            continue
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            report.error("json_parse", rel, f"invalid JSON: {exc}")


def _check_workflows(root: Path, report: PreflightReport) -> None:
    wfdir = root / ".github" / "workflows"
    if not wfdir.is_dir():
        return
    for path in sorted([*wfdir.glob("*.yml"), *wfdir.glob("*.yaml")]):
        rel = path.relative_to(root)
        text = _read_text(path)
        if text is None:
            report.error("workflow_io", rel, "cannot read as UTF-8")
            continue
        # We don't require PyYAML — a workflow that has lost its newlines is the
        # symptom we're catching here. Structural validation is the job of the
        # one-line check above plus actionlint in CI (out of scope for v0.3).
        lines = text.splitlines()
        non_blank = [ln for ln in lines if ln.strip()]
        if len(non_blank) < 5:
            report.error(
                "workflow_too_short",
                rel,
                f"only {len(non_blank)} non-blank lines — workflow likely broken",
            )


def _check_bat_files(root: Path, report: PreflightReport) -> None:
    for path in _iter_files(root, "*.bat"):
        rel = path.relative_to(root)
        text = _read_text(path)
        if text is None:
            report.error("bat_io", rel, "cannot read as UTF-8")
            continue
        non_blank = [ln for ln in text.splitlines() if ln.strip()]
        if len(non_blank) < 3:
            report.error(
                "bat_too_short",
                rel,
                f"only {len(non_blank)} non-blank lines — batch file likely broken",
            )


def _check_readme(root: Path, report: PreflightReport) -> None:
    path = root / "README.md"
    if not path.exists():
        report.error("readme_missing", "README.md", "README.md not found")
        return
    text = _read_text(path) or ""
    if "# MapIR" not in text:
        report.error("readme_heading", "README.md", "top-level '# MapIR' heading missing")
    line_count = len(text.splitlines())
    if line_count < 50:
        report.warn(
            "readme_short", "README.md", f"only {line_count} lines — README looks like a stub"
        )


def scan_repo(root: Path | str | None = None) -> PreflightReport:
    """Run every check and return the aggregated report.

    Accepts an explicit root for tests; otherwise reads the env var
    ``MAPIR_REPO_ROOT`` and falls back to walking up from this file.
    """
    if root is None:
        env = os.environ.get(REPO_ROOT_ENV)
        # Fall back to walking up from this file (scripts/preflight.py → repo root).
        root_path = Path(env) if env else Path(__file__).resolve().parents[1]
    else:
        root_path = Path(root)

    report = PreflightReport()
    _check_one_line_corruption(root_path, report)
    _check_python(root_path, report)
    _check_pyproject(root_path, report)
    _check_requirements(root_path, report)
    _check_json(root_path, report)
    _check_workflows(root_path, report)
    _check_bat_files(root_path, report)
    _check_readme(root_path, report)
    return report


def _print_report(report: PreflightReport) -> None:
    """Print using rich if available, otherwise plain text."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        if not report.issues:
            console.print("[green]OK preflight: no issues[/green]")
            return
        table = Table(title="MapIR preflight", show_lines=False, header_style="bold")
        table.add_column("Severity")
        table.add_column("Code")
        table.add_column("Path", style="dim")
        table.add_column("Message")
        for issue in report.issues:
            color = "red" if issue.severity == "error" else "yellow"
            table.add_row(
                f"[{color}]{issue.severity.upper()}[/{color}]",
                issue.code,
                issue.path,
                issue.message,
            )
        console.print(table)
        if report.ok:
            console.print(
                "[green]OK preflight: errors=0[/green] "
                f"[yellow]warnings={len(report.warnings)}[/yellow]"
            )
        else:
            console.print(
                f"[red]FAIL preflight: {len(report.errors)} error(s)[/red] "
                f"[yellow]warnings={len(report.warnings)}[/yellow]"
            )
    except ImportError:
        for issue in report.issues:
            print(f"[{issue.severity.upper()}] {issue.code} {issue.path}: {issue.message}")
        if report.ok:
            print(f"preflight: OK (warnings={len(report.warnings)})")
        else:
            print(
                f"preflight: FAIL ({len(report.errors)} error(s), "
                f"{len(report.warnings)} warning(s))"
            )


def main(argv: list[str] | None = None) -> int:
    _ = argv
    report = scan_repo()
    _print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
