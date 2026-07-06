"""Auth commands — inspect the resolved identity and the RBAC model."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli import auth as A

console = Console()
auth_app = typer.Typer(help="Enterprise auth: identity provider + RBAC (forward-auth ready)")


@auth_app.command("whoami", help="Show the identity the configured provider resolves.")
def whoami() -> None:
    provider = A.resolve_provider()
    p = provider.identity()  # CLI has no request headers → provider env/dev identity
    console.print(Panel.fit(
        f"[bold]Subject:[/bold] {p.subject}\n"
        f"[bold]Name:[/bold] {p.display_name or '—'}\n"
        f"[bold]Provider:[/bold] {p.provider}\n"
        f"[bold]Authenticated:[/bold] {p.authenticated}\n"
        f"[bold]Roles:[/bold] {', '.join(p.roles) or 'none'}\n"
        f"[bold]Permissions:[/bold] {', '.join(sorted(p.permissions)) or 'none'}",
        title="whoami", border_style="cyan"))
    console.print("[dim]Set KEEL_AUTH_MODE=forward-auth behind an SSO proxy; "
                  "dev mode defaults to an admin principal.[/dim]")


@auth_app.command("roles", help="List roles and the permissions each grants.")
def roles() -> None:
    table = Table(show_header=True, header_style="bold magenta", title="RBAC roles")
    table.add_column("Role", style="cyan")
    table.add_column("Permissions", style="green")
    for r in A.ROLE_ORDER:
        perms = sorted(A.ROLE_PERMISSIONS.get(r, set())) or ["(read-only)"]
        table.add_row(r, ", ".join(perms))
    console.print(table)


@auth_app.command("check", help="Check whether the current identity has a permission.")
def check(
    permission: Annotated[str, typer.Argument(help="Permission, e.g. knowledge:project")],
) -> None:
    p = A.current_principal()
    if p.has(permission):
        console.print(f"[green]✓[/green] {p.subject} has [cyan]{permission}[/cyan]")
        raise typer.Exit(0)
    console.print(f"[red]✗[/red] {p.subject} (roles: {', '.join(p.roles) or 'none'}) "
                  f"lacks [cyan]{permission}[/cyan]")
    raise typer.Exit(1)
