"""Admin commands — branding + navigation visibility (org-controlled)."""

from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli import admin as A

console = Console()
admin_app = typer.Typer(help="Admin-controlled app settings (branding + nav visibility)")


@admin_app.command("show", help="Show current admin settings (branding + nav overrides).")
def show() -> None:
    s = A.load_settings()
    console.print(Panel.fit(
        f"[bold]App title:[/bold] {s.branding.app_title}\n"
        f"[bold]App name:[/bold]  {s.branding.app_name}",
        title="Branding", border_style="cyan"))
    if s.nav_visibility:
        table = Table(show_header=True, header_style="bold magenta", title="Nav visibility overrides")
        table.add_column("Nav id", style="cyan")
        table.add_column("Allowed roles", style="green")
        for nav_id, roles in sorted(s.nav_visibility.items()):
            table.add_row(nav_id, ", ".join(roles))
        console.print(table)
    else:
        console.print("[dim]No nav overrides — frontend defaults (minRole) apply.[/dim]")


@admin_app.command("set-branding", help="Set the app title/name shown top-left.")
def set_branding(
    title: Annotated[Optional[str], typer.Option("--title", help="App title (heading)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", help="App name (subtitle)")] = None,
) -> None:
    if title is None and name is None:
        console.print("[yellow]Nothing to change (pass --title and/or --name).[/yellow]")
        raise typer.Exit(1)
    s = A.set_branding(app_title=title, app_name=name)
    _audit("set_branding", {"app_title": s.branding.app_title, "app_name": s.branding.app_name})
    console.print(f"[green]✓[/green] Branding: [cyan]{s.branding.app_title}[/cyan] · {s.branding.app_name}")


@admin_app.command("set-nav", help="Set which roles can see a nav entry.")
def set_nav(
    nav_id: Annotated[str, typer.Argument(help="Nav id, e.g. group:Knowledge or item:/kg/okf")],
    roles: Annotated[List[str], typer.Argument(help="Allowed roles (member/lead/admin)")],
) -> None:
    s = A.set_nav_visibility(nav_id, roles)
    applied = s.nav_visibility.get(nav_id, [])
    _audit("set_nav", {"nav_id": nav_id, "roles": applied})
    console.print(f"[green]✓[/green] {nav_id} → [green]{', '.join(applied)}[/green]")


@admin_app.command("clear-nav", help="Remove a nav override (revert to default).")
def clear_nav(
    nav_id: Annotated[str, typer.Argument(help="Nav id to reset")],
) -> None:
    A.clear_nav_override(nav_id)
    _audit("clear_nav", {"nav_id": nav_id})
    console.print(f"[green]✓[/green] Cleared override for {nav_id} (default applies).")


def _audit(action: str, details: dict) -> None:
    try:
        from agentic_cli.tracker import record_action

        record_action("admin", action, entity_type="app_settings", entity_id="app",
                       source="cli", details=details)
    except Exception:  # noqa: BLE001 - never break on audit
        pass
