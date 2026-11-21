"""Command-line interface for the AI Automation MCP servers and skills.

Mirrors the series CLI style (Typer + Rich tables). ``run`` starts one
server on stdio for a real MCP client — that is what the command is
for. ``demo`` runs every server in-process on fake backends instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ai_automation_mcp import __version__
from ai_automation_mcp.config import get_settings
from ai_automation_mcp.demo import run_full_demo
from ai_automation_mcp.servers import SERVERS, SERVERS_BY_NAME, create_live_server
from ai_automation_mcp.skills import validate_skill

app = typer.Typer(
    no_args_is_help=True,
    help="Run MCP servers that give AI agents hands — and validate the skills that teach them jobs.",
)
console = Console()


@app.command("servers")
def list_servers() -> None:
    """List the six servers in build order."""
    table = Table(title="AI Automation MCP — servers in build order")
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Server", style="cyan")
    table.add_column("What it does")
    table.add_column("Tools")
    table.add_column("Backend")
    table.add_column("Sends anything?")
    for spec in SERVERS:
        table.add_row(
            f"{spec.number:02d}",
            spec.name,
            spec.description,
            spec.tools,
            spec.backend,
            spec.sends,
        )
    console.print(table)


@app.command("run")
def run_server(
    name: Annotated[str, typer.Argument(help="Server name, e.g. lead-tools.")],
    notes_dir: Annotated[
        Path | None, typer.Option("--notes-dir", help="notes-files sandbox directory.")
    ] = None,
    crm_path: Annotated[
        Path | None, typer.Option("--crm-path", help="mini-crm JSON store path.")
    ] = None,
    allow_domain: Annotated[
        list[str] | None,
        typer.Option("--allow-domain", help="web-fetch allowlist domain (repeatable)."),
    ] = None,
) -> None:
    """Start one server on stdio for an MCP client."""
    if name not in SERVERS_BY_NAME:
        choices = ", ".join(sorted(SERVERS_BY_NAME))
        raise typer.BadParameter(f"Unknown server {name!r}. Available: {choices}")
    server = create_live_server(
        name,
        get_settings(),
        notes_dir=notes_dir,
        crm_path=crm_path,
        allowlist=allow_domain,
    )
    server.serve_stdio()


@app.command("demo")
def demo() -> None:
    """Boot all six servers on fakes and call their headline tools."""
    # markup=False: tool output contains characters Rich would treat as tags.
    console.print(run_full_demo(), markup=False)


@app.command("validate-skill")
def validate_skill_command(
    path: Annotated[Path, typer.Argument(help="Skill folder (or its SKILL.md).")],
) -> None:
    """Validate a SKILL.md folder against the Agent Skills rules."""
    report = validate_skill(path)
    if report.ok:
        console.print(f"OK — skill {report.name!r} at {report.path} is valid.")
        return
    console.print(f"INVALID — {report.path}:", style="red")
    for problem in report.problems:
        console.print(f"  - {problem}")
    raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the installed ai-automation-mcp version."""
    console.print(__version__)
