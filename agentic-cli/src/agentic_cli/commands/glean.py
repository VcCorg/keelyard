"""Glean commands — inspect config and run enterprise-search queries."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
glean_app = typer.Typer(help="Glean enterprise search (config + query)")


@glean_app.command("status", help="Show Glean configuration + whether live search is available.")
def status() -> None:
    from agentic_cli.glean import GleanConfig

    cfg = GleanConfig.load()
    reason = cfg.unavailable_reason()
    console.print(Panel.fit(
        f"[bold]URL:[/bold] {cfg.api_url or '—'}\n"
        f"[bold]Auth mode:[/bold] {cfg.auth_mode}\n"
        f"[bold]Configured:[/bold] {cfg.is_configured()}\n"
        f"[bold]Live search:[/bold] " + ("[green]ready[/green]" if not reason else f"[yellow]{reason}[/yellow]"),
        title="Glean", border_style="cyan"))


@glean_app.command("search", help="Run a Glean search and print the context (token mode).")
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 5,
) -> None:
    from agentic_cli.glean import GleanError, search_text

    try:
        text = search_text(query, limit=limit)
    except GleanError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    if not text.strip():
        console.print("[yellow]No results.[/yellow]")
        return
    console.print(Panel(text, title=f"Glean · {query}", border_style="green"))
    try:
        from agentic_cli.tracker import record_action

        record_action("glean", "search", entity_type="query", entity_id=query,
                       source="cli", details={"limit": limit, "chars": len(text)})
    except Exception:  # noqa: BLE001
        pass
