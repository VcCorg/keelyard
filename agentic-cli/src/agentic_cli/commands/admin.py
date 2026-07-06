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


@admin_app.command("roles", help="List user → role assignments.")
def roles() -> None:
    from agentic_cli.auth import load_assignments

    data = load_assignments()
    if not data:
        console.print("[dim]No role assignments — roles come from the SSO proxy / dev default.[/dim]")
        return
    table = Table(show_header=True, header_style="bold magenta", title="Role assignments")
    table.add_column("User", style="cyan")
    table.add_column("Roles", style="green")
    for subject, r in sorted(data.items()):
        table.add_row(subject, ", ".join(r))
    console.print(table)


@admin_app.command("assign-role", help="Assign roles to a user (overrides SSO-derived roles).")
def assign_role(
    subject: Annotated[str, typer.Argument(help="User email / subject")],
    role: Annotated[List[str], typer.Argument(help="Roles: viewer/developer/maintainer/admin")],
) -> None:
    from agentic_cli.auth import VALID_ROLES, get_roles, set_roles

    unknown = [r for r in role if r not in VALID_ROLES]
    if unknown:
        console.print(f"[red]✗[/red] Unknown role(s): {', '.join(unknown)}. Valid: {', '.join(VALID_ROLES)}")
        raise typer.Exit(1)
    set_roles(subject, role)
    applied = get_roles(subject) or []
    _audit("assign_role", {"subject": subject, "roles": applied})
    console.print(f"[green]✓[/green] {subject} → [green]{', '.join(applied) or '(none)'}[/green]")


@admin_app.command("revoke-role", help="Remove a user's explicit role assignment.")
def revoke_role(
    subject: Annotated[str, typer.Argument(help="User email / subject")],
) -> None:
    from agentic_cli.auth import remove_assignment

    remove_assignment(subject)
    _audit("revoke_role", {"subject": subject})
    console.print(f"[green]✓[/green] Cleared role assignment for {subject}.")


@admin_app.command("reset", help="Reset platform data by scope (destructive).")
def reset(
    scope: Annotated[List[str], typer.Option("--scope", "-s",
        help="Scope(s): activity | catalog | sessions | settings | all")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be reset, change nothing")] = False,
) -> None:
    """Return the platform to a clean state for the chosen scopes.

    Individual deletes exist per item; this is the app-level reset. Destructive —
    requires confirmation (or --yes). Use --dry-run to preview counts.
    """
    from agentic_cli.admin import SCOPES, SCOPE_LABELS, normalize_scopes, reset_platform, reset_preview

    scopes = normalize_scopes(scope or [])
    if not scopes:
        console.print(f"[yellow]No valid scope. Choose from:[/yellow] {', '.join(SCOPES)}, all")
        raise typer.Exit(1)

    prev = reset_preview()
    table = Table(show_header=True, header_style="bold magenta", title="Platform reset — scope preview")
    table.add_column("Scope", style="cyan")
    table.add_column("What", style="dim")
    table.add_column("Items", justify="right")
    for s in scopes:
        table.add_row(s, SCOPE_LABELS[s], str(prev[s]["items"]))
    console.print(table)

    if dry_run:
        console.print("[dim]Dry-run — nothing changed.[/dim]")
        return

    if not yes:
        from rich.prompt import Confirm

        if not Confirm.ask(f"[red]Reset {', '.join(scopes)}? This cannot be undone.[/red]"):
            console.print("Aborted.")
            raise typer.Exit(1)

    summary = reset_platform(scopes)
    # Audit AFTER the reset so the record survives an activity clear.
    _audit("reset", {"scopes": scopes})
    console.print(f"[bold green]✓[/bold green] Reset complete: {', '.join(scopes)}")
    for s, detail in summary.items():
        console.print(f"  [cyan]{s}[/cyan]: {detail}")


def _audit(action: str, details: dict) -> None:
    try:
        from agentic_cli.tracker import record_action

        record_action("admin", action, entity_type="app_settings", entity_id="app",
                       source="cli", details=details)
    except Exception:  # noqa: BLE001 - never break on audit
        pass
