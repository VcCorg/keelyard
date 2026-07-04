"""Execution commands — inspect and drive swappable coding engines."""

from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli import execution as ex

console = Console()
execution_app = typer.Typer(help="Vendor-neutral execution engines (Devin today; swappable)")


@execution_app.command("list", help="List available execution engines and their status.")
def list_engines() -> None:
    infos = ex.list_engines()
    if not infos:
        console.print("[yellow]No execution engines registered.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta", title="Execution engines")
    table.add_column("Engine", style="cyan")
    table.add_column("Kind")
    table.add_column("Available")
    table.add_column("Detail", style="dim")
    for i in infos:
        table.add_row(
            i.name, i.kind,
            "[green]yes[/green]" if i.available else "[red]no[/red]",
            i.detail or i.description,
        )
    console.print(table)
    console.print("[dim]Default engine: set DVA_EXECUTION_ENGINE (defaults to 'devin').[/dim]")


@execution_app.command("create", help="Launch a session on an execution engine (dry-run by default).")
def create(
    prompt: Annotated[str, typer.Argument(help="Task prompt for the session")],
    title: Annotated[str, typer.Option("--title", "-t", help="Session title")] = "",
    jira: Annotated[str, typer.Option("--jira", "-j", help="Jira key to link the session to")] = "",
    domain: Annotated[str, typer.Option("--domain", "-d", help="Domain slug")] = "",
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", help="Engine (default: devin)")] = None,
    tag: Annotated[Optional[List[str]], typer.Option("--tag", help="Tag (repeatable)")] = None,
    run: Annotated[bool, typer.Option("--run/--dry-run", help="Actually create the session (default: dry-run)")] = False,
) -> None:
    spec = ex.ExecutionSpec(
        prompt=prompt, title=title or (f"{jira}: {prompt}" if jira else prompt)[:120],
        jira=jira, domain=domain, tags=list(tag or []), dry_run=not run,
    )
    try:
        result = ex.create_session(spec, engine=engine)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ Failed to launch session: {e}[/red]")
        raise typer.Exit(1)

    mode = "DRY-RUN" if result.dry_run else "CREATED"
    console.print(Panel.fit(
        f"[bold]{mode}[/bold] · engine [cyan]{result.engine}[/cyan]\n"
        f"[bold]Session:[/bold] {result.session_id or '—'}\n"
        f"[bold]URL:[/bold] {result.url or '—'}\n"
        f"[bold]Jira:[/bold] {jira or '—'}",
        border_style="green" if not result.dry_run else "yellow",
    ))
