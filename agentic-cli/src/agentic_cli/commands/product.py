"""Product management commands for agentic-cli.

A product is the top-level grouping (e.g. CWOW, IMTO) that contains
one or more domains. Products must be registered before domains can
reference them.

Hierarchy:
    Product (e.g. CWOW)
      └── Domain (e.g. Facility)  ← created via dva domain create
"""

from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_cli.tracker import (
from agentic_cli.config import CLI_NAME
    record_activity,
    register_product,
    get_product,
    get_products,
    remove_product,
    update_product,
    get_domains,
)

product_app = typer.Typer(
    help="Product management — register top-level product groupings (e.g. CWOW, IMTO)",
    rich_markup_mode=None,
)
console = Console()


# ---------------------------------------------------------------------------
# dva product create
# ---------------------------------------------------------------------------

@product_app.command()
def create(
    name: Annotated[str, typer.Argument(help="Product name (e.g. CWOW, IMTO)")],
    description: Annotated[str, typer.Option("--description", "-d", help="Product description")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Comma-separated tags")] = None,
) -> None:
    """
    Register a new product.

    Products are top-level groupings that contain domains.
    Product names are stored uppercase.

    Examples:
        dva product create CWOW --description "CWOW Healthcare Platform" --tags "healthcare,gcp"
        dva product create IMTO --description "Imaging & Technology Operations"
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    name_upper = name.upper()

    existing = get_product(name_upper)
    if existing:
        console.print(f"[yellow]⚠ Product '{name_upper}' already exists. Updating...[/yellow]")

    register_product(name=name_upper, description=description, tags=tag_list)

    console.print(f"[bold green]✓[/bold green] Product registered: [cyan]{name_upper}[/cyan]")

    lines = [f"[cyan]Name:[/cyan] {name_upper}"]
    if description:
        lines.append(f"[cyan]Description:[/cyan] {description}")
    if tag_list:
        lines.append(f"[cyan]Tags:[/cyan] {', '.join(tag_list)}")
    console.print(Panel("\n".join(lines), title="Product Details"))

    console.print(f"\n[dim]Next: Create a domain:[/dim]  dva domain create <DOMAIN> --product {name_upper}")

    record_activity(
        command="product", subcommand="create",
        args={"name": name_upper},
    )


# ---------------------------------------------------------------------------
# dva product list
# ---------------------------------------------------------------------------

@product_app.command("list")
def list_products() -> None:
    """
    List all registered products.

    Examples:
        dva product list
    """
    products = get_products()

    if not products:
        console.print("[yellow]No products registered.[/yellow]")
        console.print("[dim]Register one with: dva product create <NAME>[/dim]")
        return

    table = Table(title=f"Registered Products ({len(products)})")
    table.add_column("Name", style="cyan bold", no_wrap=True)
    table.add_column("Description", style="dim")
    table.add_column("Domains", justify="right")
    table.add_column("Tags", style="dim")
    table.add_column("Created", style="dim")

    for p in products:
        domains = get_domains(product=p["name"])
        tag_str = ", ".join(p.get("tags", []) or [])
        table.add_row(
            p["name"],
            p.get("description") or "—",
            str(len(domains)),
            tag_str or "—",
            p["created_at"][:10],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# dva product show
# ---------------------------------------------------------------------------

@product_app.command()
def show(
    name: Annotated[str, typer.Argument(help="Product name")],
) -> None:
    """
    Show detailed information about a product and its domains.

    Examples:
        dva product show CWOW
    """
    p = get_product(name)
    if not p:
        console.print(f"[red]✗ Product '{name.upper()}' not found.[/red]")
        console.print("[dim]Use f'{CLI_NAME} product list' to see available products.[/dim]")
        raise typer.Exit(1)

    lines = [f"[cyan]Name:[/cyan] {p['name']}"]
    if p.get("description"):
        lines.append(f"[cyan]Description:[/cyan] {p['description']}")
    tags = p.get("tags") or []
    if tags:
        lines.append(f"[cyan]Tags:[/cyan] {', '.join(tags)}")
    lines.append(f"[cyan]Created:[/cyan] {p['created_at']}")
    lines.append(f"[cyan]Updated:[/cyan] {p['updated_at']}")

    console.print(Panel("\n".join(lines), title=f"Product: {p['name']}"))

    # Show domains under this product
    domains = get_domains(product=p["name"])
    if domains:
        dtable = Table(title=f"Domains under {p['name']} ({len(domains)})")
        dtable.add_column("Name", style="cyan")
        dtable.add_column("Domain", style="bold")
        dtable.add_column("Jira", style="dim")
        dtable.add_column("BB", style="dim")
        dtable.add_column("Confluence", style="dim")

        for d in domains:
            dtable.add_row(
                d["name"],
                d["domain"],
                d.get("jira_project") or "—",
                d.get("bitbucket_project") or "—",
                d.get("confluence_space") or "—",
            )
        console.print(dtable)
    else:
        console.print(f"[dim]No domains yet. Create one with: dva domain create <DOMAIN> --product {p['name']}[/dim]")


# ---------------------------------------------------------------------------
# dva product update
# ---------------------------------------------------------------------------

@product_app.command()
def update(
    name: Annotated[str, typer.Argument(help="Product name")],
    description: Annotated[str, typer.Option("--description", "-d", help="Update description")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Replace tags (comma-separated)")] = None,
) -> None:
    """
    Update a product's description or tags.

    Examples:
        dva product update CWOW --description "Updated description"
        dva product update CWOW --tags "healthcare,gcp,spanner"
    """
    p = get_product(name)
    if not p:
        console.print(f"[red]✗ Product '{name.upper()}' not found.[/red]")
        raise typer.Exit(1)

    fields = {}
    if description:
        fields["description"] = description
    if tags:
        fields["tags"] = [t.strip() for t in tags.split(",")]

    if not fields:
        console.print("[yellow]No fields to update. Use --help to see options.[/yellow]")
        raise typer.Exit(1)

    updated = update_product(name, **fields)
    if updated:
        console.print(f"[bold green]✓[/bold green] Product '{name.upper()}' updated.")
        for k, v in fields.items():
            display_v = ", ".join(v) if isinstance(v, list) else v
            console.print(f"  [cyan]{k}:[/cyan] {display_v}")
        record_activity(command="product", subcommand="update", args={"name": name.upper(), **fields})
    else:
        console.print(f"[yellow]No changes applied to '{name.upper()}'.[/yellow]")


# ---------------------------------------------------------------------------
# dva product remove
# ---------------------------------------------------------------------------

@product_app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Product name")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """
    Remove a product. Fails if domains still reference it.

    Examples:
        dva product remove IMTO --yes
    """
    p = get_product(name)
    if not p:
        console.print(f"[red]✗ Product '{name.upper()}' not found.[/red]")
        raise typer.Exit(1)

    domains = get_domains(product=p["name"])
    if domains:
        console.print(f"[red]✗ Cannot remove product '{p['name']}' — it has {len(domains)} domain(s).[/red]")
        console.print("[dim]Remove domains first with: dva domain remove <domain-name>[/dim]")
        raise typer.Exit(1)

    if not yes:
        console.print(f"[bold]About to remove product:[/bold] {p['name']}")
        if p.get("description"):
            console.print(f"  Description: {p['description']}")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    removed = remove_product(name)
    if removed:
        console.print(f"[bold green]✓[/bold green] Product '{p['name']}' removed.")
        record_activity(command="product", subcommand="remove", args={"name": p["name"]})
    else:
        console.print(f"[red]✗ Failed to remove '{p['name']}'.[/red]")
        raise typer.Exit(1)
