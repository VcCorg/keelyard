"""Product management commands for agentic-cli.

A product is the top-level grouping (e.g. CWOW, IMTO) that contains
one or more domains. Products must be registered before domains can
reference them.

Hierarchy:
    Product (e.g. CWOW)
      └── Domain (e.g. Facility)  ← created via {CLI_NAME} domain create
"""

from pathlib import Path

from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_cli.config import CLI_NAME
from agentic_cli.tracker import (
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
# {CLI_NAME} product create
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
        {CLI_NAME} product create CWOW --description "CWOW Healthcare Platform" --tags "healthcare,gcp"
        {CLI_NAME} product create IMTO --description "Imaging & Technology Operations"
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

    console.print(f"\n[dim]Next: Create a domain:[/dim]  {CLI_NAME} domain create <DOMAIN> --product {name_upper}")

    record_activity(
        command="product", subcommand="create",
        args={"name": name_upper},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} product list
# ---------------------------------------------------------------------------

@product_app.command("list")
def list_products() -> None:
    """
    List all registered products.

    Examples:
        {CLI_NAME} product list
    """
    products = get_products()

    if not products:
        console.print("[yellow]No products registered.[/yellow]")
        console.print(f"[dim]Register one with: {CLI_NAME} product create <NAME>[/dim]")
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
# {CLI_NAME} product show
# ---------------------------------------------------------------------------

@product_app.command()
def show(
    name: Annotated[str, typer.Argument(help="Product name")],
) -> None:
    """
    Show detailed information about a product and its domains.

    Examples:
        {CLI_NAME} product show CWOW
    """
    p = get_product(name)
    if not p:
        console.print(f"[red]✗ Product '{name.upper()}' not found.[/red]")
        console.print(f"[dim]Use '{CLI_NAME} product list' to see available products.[/dim]")
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
        console.print(f"[dim]No domains yet. Create one with: {CLI_NAME} domain create <DOMAIN> --product {p['name']}[/dim]")


# ---------------------------------------------------------------------------
# {CLI_NAME} product update
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
        {CLI_NAME} product update CWOW --description "Updated description"
        {CLI_NAME} product update CWOW --tags "healthcare,gcp,spanner"
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
# {CLI_NAME} product remove
# ---------------------------------------------------------------------------

@product_app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Product name")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """
    Remove a product. Fails if domains still reference it.

    Examples:
        {CLI_NAME} product remove IMTO --yes
    """
    p = get_product(name)
    if not p:
        console.print(f"[red]✗ Product '{name.upper()}' not found.[/red]")
        raise typer.Exit(1)

    domains = get_domains(product=p["name"])
    if domains:
        console.print(f"[red]✗ Cannot remove product '{p['name']}' — it has {len(domains)} domain(s).[/red]")
        console.print(f"[dim]Remove domains first with: {CLI_NAME} domain remove <domain-name>[/dim]")
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


# ---------------------------------------------------------------------------
# {CLI_NAME} product init-meta
# ---------------------------------------------------------------------------

@product_app.command("init-meta")
def init_meta(
    name: Annotated[str, typer.Argument(help="Product name (e.g. ABC, CWOW)")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory for the product meta-repo")
    ] = None,
    org_methodology: Annotated[
        str,
        typer.Option(
            "--org-methodology",
            help="Git URL of the org-wide methodology (inner loop) to pin as a submodule",
        ),
    ] = "https://github.com/venkatchinta/superpowers.git",
    git_init: Annotated[
        bool, typer.Option("--git-init/--no-git-init", help="Initialize as a git repo")
    ] = True,
) -> None:
    """
    Initialize a product meta-repo (top-level outer-loop tier).

    Creates `product-<name>-meta` holding the shared outer-loop governance for
    all domains under the product, the inner↔outer crosswalk, and the
    exceptions ledger. Pins the org-wide methodology (inner loop) as a submodule.

    The product must be registered first via `{CLI_NAME} product create`.

    Examples:
        {CLI_NAME} product init-meta ABC
        {CLI_NAME} product init-meta ABC --org-methodology https://github.com/acme/methodology.git
        {CLI_NAME} product init-meta ABC --output ./abc-meta
    """
    from pathlib import Path

    from agentic_cli.meta_repo import scaffold_product_meta_repo
    from agentic_cli.commands.domain import _get_code_workspace

    name_upper = name.upper()
    p = get_product(name_upper)
    if not p:
        console.print(f"[red]✗ Product '{name_upper}' not found.[/red]")
        console.print(f"[dim]Register it first: {CLI_NAME} product create {name_upper}[/dim]")
        raise typer.Exit(1)

    if output:
        out_dir = Path(output).resolve()
    else:
        workspace = _get_code_workspace()
        out_dir = workspace / name_upper.lower()
        out_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Initializing product meta-repo for '{name_upper}'...[/cyan]")
    try:
        created = scaffold_product_meta_repo(
            output_dir=out_dir,
            product=name_upper,
            description=p.get("description", ""),
            owner=p.get("owner", ""),
            org_methodology_url=org_methodology,
            git_init=git_init,
        )
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to scaffold product meta-repo: {e}[/red]")
        raise typer.Exit(1)

    meta_path = created["root"]
    console.print(f"[green]✓ Product meta-repo created:[/green] {meta_path}")
    for label, path in created.items():
        if label != "root":
            console.print(f"  [green]✓[/green] {path.relative_to(meta_path)}")

    console.print()
    console.print(Panel(
        f"[cyan]Product:[/cyan] {name_upper}\n"
        f"[cyan]Location:[/cyan] {meta_path}\n"
        f"[cyan]Inner loop:[/cyan] {org_methodology}\n"
        f"[cyan]Git:[/cyan] {'initialized' if git_init else 'skipped'}",
        title="Product Meta-Repo",
        border_style="green",
    ))
    console.print(f"\n[dim]Next: link domains to this product meta:[/dim]")
    console.print(
        f"[dim]  {CLI_NAME} domain init-meta <slug> --product-meta {meta_path}[/dim]"
    )

    record_activity(
        command="product", subcommand="init-meta",
        args={"name": name_upper, "output": str(meta_path), "org_methodology": org_methodology},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} product exceptions
# ---------------------------------------------------------------------------

exceptions_app = typer.Typer(
    help="Manage the product governance exceptions ledger (override-with-justification)",
    rich_markup_mode=None,
)
product_app.add_typer(exceptions_app, name="exceptions")


def _resolve_product_meta(name_upper: str, meta: str = None):
    """Resolve the product meta-repo path. Uses --meta if given, else workspace."""
    from pathlib import Path
    from agentic_cli.commands.domain import _get_code_workspace

    if meta:
        return Path(meta).resolve()
    workspace = _get_code_workspace()
    return workspace / name_upper.lower() / f"product-{name_upper.lower()}-meta"


@exceptions_app.command("add")
def exceptions_add(
    name: Annotated[str, typer.Argument(help="Product name")],
    rule: Annotated[str, typer.Option("--rule", help="Rule being relaxed (e.g. tdd, spec-first)")],
    reason: Annotated[str, typer.Option("--reason", help="Justification for the waiver")],
    scope: Annotated[str, typer.Option("--scope", help="Scope, e.g. domain:<slug> or repo:<slug>")],
    owner: Annotated[str, typer.Option("--owner", help="Owner email")],
    expires: Annotated[str, typer.Option("--expires", help="Expiry date (ISO, e.g. 2026-07-27)")] = "",
    meta: Annotated[str, typer.Option("--meta", help="Path to product meta-repo (override)")] = None,
) -> None:
    """Record a governance waiver in the product exceptions ledger.

    Examples:
        {CLI_NAME} product exceptions add ABC --rule tdd --reason "spike" \\
            --scope domain:abc-a1 --owner you@example.com --expires 2026-07-27
    """
    from agentic_cli.meta_repo import add_exception

    name_upper = name.upper()
    meta_path = _resolve_product_meta(name_upper, meta)
    if not meta_path.exists():
        console.print(f"[red]✗ Product meta-repo not found at {meta_path}[/red]")
        console.print(f"[dim]Create it first: {CLI_NAME} product init-meta {name_upper}[/dim]")
        raise typer.Exit(1)

    try:
        entry = add_exception(
            meta_repo_path=meta_path, rule=rule, reason=reason,
            scope=scope, owner=owner, expires_at=expires,
        )
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold green]✓[/bold green] Exception [cyan]{entry.id}[/cyan] recorded.")
    console.print(Panel(
        f"[cyan]Rule:[/cyan] {entry.rule}\n"
        f"[cyan]Reason:[/cyan] {entry.reason}\n"
        f"[cyan]Scope:[/cyan] {entry.scope}\n"
        f"[cyan]Owner:[/cyan] {entry.owner}\n"
        f"[cyan]Expires:[/cyan] {entry.expires_at or '(none — discouraged)'}",
        title=f"Exception {entry.id}",
    ))
    if not expires:
        console.print("[yellow]⚠ No expiry set — waivers without an expiry are discouraged.[/yellow]")

    record_activity(
        command="product", subcommand="exceptions-add",
        args={"name": name_upper, "rule": rule, "scope": scope, "id": entry.id},
    )


@exceptions_app.command("list")
def exceptions_list(
    name: Annotated[str, typer.Argument(help="Product name")],
    meta: Annotated[str, typer.Option("--meta", help="Path to product meta-repo (override)")] = None,
) -> None:
    """List all waivers in the product exceptions ledger.

    Examples:
        {CLI_NAME} product exceptions list ABC
    """
    from agentic_cli.meta_repo import list_exceptions

    name_upper = name.upper()
    meta_path = _resolve_product_meta(name_upper, meta)
    if not meta_path.exists():
        console.print(f"[red]✗ Product meta-repo not found at {meta_path}[/red]")
        raise typer.Exit(1)

    entries = list_exceptions(meta_path)
    if not entries:
        console.print("[dim]No exceptions recorded.[/dim]")
        return

    table = Table(title=f"{name_upper} — Exceptions Ledger")
    table.add_column("ID", style="cyan")
    table.add_column("Rule")
    table.add_column("Scope")
    table.add_column("Owner")
    table.add_column("Expires")
    table.add_column("Status")
    for e in entries:
        effective = e.is_effective()
        status = e.status if effective else (e.status if e.status != "active" else "expired")
        style = "green" if effective else "red"
        table.add_row(
            e.id, e.rule, e.scope, e.owner, e.expires_at or "—",
            f"[{style}]{status}[/{style}]",
        )
    console.print(table)
