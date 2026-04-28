"""Domain management commands for agentic-cli.

A domain is a scoped area within a product that ties together a Jira project,
Bitbucket project, Confluence space, and selected repositories.

Products must be registered first via ``dva product create``.

Hierarchy:
    Product (e.g. CWOW)   ← dva product create CWOW
      └── Domain (e.g. Facility)  ← dva domain create Facility --product CWOW
            ├── jira_project: CWOW
            ├── bitbucket_project: CGF
            ├── confluence_space: MTT
            └── repos: [cwow-facility-service, ...]
"""

from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pathlib import Path

from agentic_cli.config import CLI_NAME
from agentic_cli.tracker import (
    record_activity,
    get_product,
    register_domain,
    get_domain,
    get_domains,
    remove_domain,
    update_domain,
    link_repo_to_domain,
    unlink_repo_from_domain,
    get_domain_repos,
    get_domain_docs,
    add_domain_doc,
    mark_domain_repo_onboarded,
)
from agentic_cli.skill_generator import (
    ROLES,
    ROLE_LABELS,
    gather_domain_context,
    generate_skill_files,
)

domain_app = typer.Typer(
    help="Domain management — register domains within a product with Jira, Bitbucket, and Confluence links",
    rich_markup_mode=None,
)
console = Console()


def _slugify(product: str, domain: str) -> str:
    """Generate a domain slug from product + domain name."""
    return f"{product.lower()}-{domain.lower().replace(' ', '-')}"


# ---------------------------------------------------------------------------
# dva domain create
# ---------------------------------------------------------------------------

@domain_app.command()
def create(
    domain: Annotated[str, typer.Argument(help="Domain name (e.g. Facility, Patient)")],
    product: Annotated[str, typer.Option("--product", "-p", help="Product this domain belongs to (required)")] = ...,
    description: Annotated[str, typer.Option("--description", "-d", help="Description of this domain")] = None,
    jira_project: Annotated[str, typer.Option("--jira", help="Jira project key")] = None,
    bitbucket_project: Annotated[str, typer.Option("--bb", help="Bitbucket project key")] = None,
    confluence_space: Annotated[str, typer.Option("--confluence", help="Source Confluence space key")] = None,
    jira_dashboard: Annotated[str, typer.Option("--jira-dashboard", help="Jira dashboard URL")] = None,
    confluence_url: Annotated[str, typer.Option("--confluence-url", help="Confluence page/space URL")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Comma-separated extra tags")] = None,
) -> None:
    """
    Register a new domain under a product.

    The --product flag is mandatory. The product must already be registered
    via f'{CLI_NAME} product create'. The domain slug is auto-generated as
    <product>-<domain> (lowercase).

    Examples:
        dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT
        dva domain create Patient --product CWOW --jira CWOW --bb CGP --tags "spanner,healthcare"
        dva domain create Imaging --product IMTO --jira IMTO --bb IMTO
    """
    product_upper = product.upper()

    # Validate product exists
    prod = get_product(product_upper)
    if not prod:
        console.print(f"[red]✗ Product '{product_upper}' not found.[/red]")
        console.print(f"[dim]Register it first: dva product create {product_upper}[/dim]")
        raise typer.Exit(1)

    name = _slugify(product_upper, domain)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Check if already exists
    existing = get_domain(name)
    if existing:
        console.print(f"[yellow]⚠ Domain '{name}' already exists. Updating...[/yellow]")

    register_domain(
        name=name,
        product=product_upper,
        domain=domain,
        description=description,
        jira_project=jira_project,
        bitbucket_project=bitbucket_project,
        confluence_space=confluence_space,
        jira_dashboard=jira_dashboard,
        confluence_url=confluence_url,
        tags=tag_list,
    )

    console.print(f"[bold green]✓[/bold green] Domain registered: [cyan]{name}[/cyan]")

    # Show summary
    panel_lines = [
        f"[cyan]Name:[/cyan] {name}",
        f"[cyan]Product:[/cyan] {product_upper}",
        f"[cyan]Domain:[/cyan] {domain}",
    ]
    if description:
        panel_lines.append(f"[cyan]Description:[/cyan] {description}")
    if jira_project:
        panel_lines.append(f"[cyan]Jira Project:[/cyan] {jira_project}")
    if bitbucket_project:
        panel_lines.append(f"[cyan]Bitbucket Project:[/cyan] {bitbucket_project}")
    if confluence_space:
        panel_lines.append(f"[cyan]Confluence Space:[/cyan] {confluence_space}")
    if jira_dashboard:
        panel_lines.append(f"[cyan]Jira Dashboard:[/cyan] {jira_dashboard}")
    if confluence_url:
        panel_lines.append(f"[cyan]Confluence URL:[/cyan] {confluence_url}")
    if tag_list:
        panel_lines.append(f"[cyan]Tags:[/cyan] {', '.join(tag_list)}")

    console.print(Panel("\n".join(panel_lines), title="Domain Details"))

    # Hints
    if bitbucket_project:
        console.print(f"\n[dim]Next: Link repos with:[/dim]  dva domain link-repo {name} <repo-slug>")
    else:
        console.print(f"\n[dim]Tip: Add a Bitbucket project:[/dim]  dva domain update {name} --bb <PROJECT_KEY>")

    record_activity(
        command="domain", subcommand="create",
        args={"name": name, "product": product_upper, "domain": domain},
    )


# ---------------------------------------------------------------------------
# dva domain list
# ---------------------------------------------------------------------------

@domain_app.command("list")
def list_domains(
    product: Annotated[str, typer.Option("--product", "-p", help="Filter by product")] = None,
) -> None:
    """
    List all registered domains.

    Examples:
        dva domain list
        dva domain list --product CWOW
    """
    domains = get_domains(product=product.upper() if product else None)

    if not domains:
        filter_msg = f" for product '{product.upper()}'" if product else ""
        console.print(f"[yellow]No domains registered{filter_msg}.[/yellow]")
        console.print("[dim]Register one with: dva domain create <PRODUCT> <DOMAIN>[/dim]")
        return

    table = Table(title=f"Registered Domains ({len(domains)})")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Product", style="bold")
    table.add_column("Domain", style="bold")
    table.add_column("Jira", style="dim")
    table.add_column("BB", style="dim")
    table.add_column("Confluence", style="dim")
    table.add_column("Repos", justify="right")
    table.add_column("Tags", style="dim")

    for d in domains:
        repos = get_domain_repos(d["name"])
        tag_str = ", ".join(d.get("tags", []) or [])
        table.add_row(
            d["name"],
            d["product"],
            d["domain"],
            d.get("jira_project") or "—",
            d.get("bitbucket_project") or "—",
            d.get("confluence_space") or "—",
            str(len(repos)),
            tag_str or "—",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# dva domain show
# ---------------------------------------------------------------------------

@domain_app.command()
def show(
    name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
) -> None:
    """
    Show detailed information about a domain.

    Examples:
        dva domain show cwow-facility
    """
    d = get_domain(name)
    if not d:
        console.print(f"[red]✗ Domain '{name}' not found.[/red]")
        console.print("[dim]Use f'{CLI_NAME} domain list' to see available domains.[/dim]")
        raise typer.Exit(1)

    # Domain info
    lines = [
        f"[cyan]Name:[/cyan] {d['name']}",
        f"[cyan]Product:[/cyan] {d['product']}",
        f"[cyan]Domain:[/cyan] {d['domain']}",
    ]
    if d.get("description"):
        lines.append(f"[cyan]Description:[/cyan] {d['description']}")
    if d.get("jira_project"):
        lines.append(f"[cyan]Jira Project:[/cyan] {d['jira_project']}")
    if d.get("bitbucket_project"):
        lines.append(f"[cyan]Bitbucket Project:[/cyan] {d['bitbucket_project']}")
    if d.get("confluence_space"):
        lines.append(f"[cyan]Confluence Space:[/cyan] {d['confluence_space']}")
    if d.get("managed_confluence_space"):
        lines.append(f"[cyan]Managed Space:[/cyan] {d['managed_confluence_space']}")
    if d.get("jira_dashboard"):
        lines.append(f"[cyan]Jira Dashboard:[/cyan] {d['jira_dashboard']}")
    if d.get("confluence_url"):
        lines.append(f"[cyan]Confluence URL:[/cyan] {d['confluence_url']}")
    tags = d.get("tags") or []
    if tags:
        lines.append(f"[cyan]Tags:[/cyan] {', '.join(tags)}")
    lines.append(f"[cyan]Created:[/cyan] {d['created_at']}")
    lines.append(f"[cyan]Updated:[/cyan] {d['updated_at']}")

    console.print(Panel("\n".join(lines), title=f"Domain: {d['name']}"))

    # Repos
    repos = get_domain_repos(name)
    if repos:
        repo_table = Table(title="Linked Repositories")
        repo_table.add_column("Slug", style="cyan")
        repo_table.add_column("Name", style="dim")
        repo_table.add_column("Onboarded", style="bold")
        repo_table.add_column("Clone URL", style="dim")

        for r in repos:
            onboarded = "[green]✓[/green]" if r.get("onboarded") else "[dim]—[/dim]"
            repo_table.add_row(
                r["repo_slug"],
                r.get("repo_name") or "—",
                onboarded,
                (r.get("clone_url") or "—")[:60],
            )
        console.print(repo_table)
    else:
        console.print("[dim]No repos linked. Use f'{CLI_NAME} domain link-repo' to add repos.[/dim]")

    # Docs
    docs = get_domain_docs(name)
    if docs:
        doc_table = Table(title="Tracked Documents")
        doc_table.add_column("Title", style="cyan")
        doc_table.add_column("Space", style="dim")
        doc_table.add_column("Page ID", style="dim")
        doc_table.add_column("Version", justify="right")
        doc_table.add_column("Synced", style="dim")

        for doc in docs:
            doc_table.add_row(
                doc.get("title") or "—",
                doc.get("source_space_key") or "—",
                doc["source_page_id"],
                str(doc.get("source_version", 0)),
                doc.get("synced_at", "—")[:19] if doc.get("synced_at") else "—",
            )
        console.print(doc_table)


# ---------------------------------------------------------------------------
# dva domain update
# ---------------------------------------------------------------------------

@domain_app.command()
def update(
    name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    product: Annotated[str, typer.Option("--product", help="Update product name")] = None,
    domain_name: Annotated[str, typer.Option("--domain", help="Update domain label")] = None,
    description: Annotated[str, typer.Option("--description", "-d", help="Update description")] = None,
    jira_project: Annotated[str, typer.Option("--jira", help="Update Jira project key")] = None,
    bitbucket_project: Annotated[str, typer.Option("--bb", help="Update Bitbucket project key")] = None,
    confluence_space: Annotated[str, typer.Option("--confluence", help="Update Confluence space key")] = None,
    jira_dashboard: Annotated[str, typer.Option("--jira-dashboard", help="Jira dashboard URL")] = None,
    confluence_url: Annotated[str, typer.Option("--confluence-url", help="Confluence page/space URL")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Replace tags (comma-separated)")] = None,
) -> None:
    """
    Update an existing domain's fields.

    Examples:
        dva domain update cwow-facility --jira CWOW --bb CGF
        dva domain update cwow-facility --jira-dashboard https://jira.example.com/...
        dva domain update cwow-facility --confluence-url https://confluence.example.com/...
        dva domain update cwow-facility --tags "spanner,healthcare,gcp"
    """
    d = get_domain(name)
    if not d:
        console.print(f"[red]✗ Domain '{name}' not found.[/red]")
        raise typer.Exit(1)

    fields = {}
    if product:
        fields["product"] = product.upper()
    if domain_name:
        fields["domain"] = domain_name
    if description:
        fields["description"] = description
    if jira_project:
        fields["jira_project"] = jira_project
    if bitbucket_project:
        fields["bitbucket_project"] = bitbucket_project
    if confluence_space:
        fields["confluence_space"] = confluence_space
    if jira_dashboard:
        fields["jira_dashboard"] = jira_dashboard
    if confluence_url:
        fields["confluence_url"] = confluence_url
    if tags:
        fields["tags"] = [t.strip() for t in tags.split(",")]

    if not fields:
        console.print("[yellow]No fields to update. Use --help to see options.[/yellow]")
        raise typer.Exit(1)

    updated = update_domain(name, **fields)
    if updated:
        console.print(f"[bold green]✓[/bold green] Domain '{name}' updated.")
        for k, v in fields.items():
            display_v = ", ".join(v) if isinstance(v, list) else v
            console.print(f"  [cyan]{k}:[/cyan] {display_v}")
        record_activity(command="domain", subcommand="update", args={"name": name, **fields})
    else:
        console.print(f"[yellow]No changes applied to '{name}'.[/yellow]")


# ---------------------------------------------------------------------------
# dva domain remove
# ---------------------------------------------------------------------------

@domain_app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """
    Remove a domain and all its linked repos and docs.

    Examples:
        dva domain remove cwow-facility
        dva domain remove cwow-facility --yes
    """
    d = get_domain(name)
    if not d:
        console.print(f"[red]✗ Domain '{name}' not found.[/red]")
        raise typer.Exit(1)

    repos = get_domain_repos(name)
    docs = get_domain_docs(name)

    if not yes:
        console.print(f"[bold]About to remove domain:[/bold] {name}")
        console.print(f"  Product: {d['product']}, Domain: {d['domain']}")
        console.print(f"  Linked repos: {len(repos)}, Tracked docs: {len(docs)}")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    removed = remove_domain(name)
    if removed:
        console.print(f"[bold green]✓[/bold green] Domain '{name}' removed (including {len(repos)} repos, {len(docs)} docs).")
        record_activity(command="domain", subcommand="remove", args={"name": name})
    else:
        console.print(f"[red]✗ Failed to remove '{name}'.[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# dva domain link-repo
# ---------------------------------------------------------------------------

@domain_app.command("link-repo")
def link_repo(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    repo_slug: Annotated[str, typer.Argument(help="Bitbucket repository slug")],
    repo_display: Annotated[str, typer.Option("--name", help="Display name for the repo")] = None,
    clone_url: Annotated[str, typer.Option("--clone-url", help="Clone URL")] = None,
) -> None:
    """
    Link a repository to a domain.

    Examples:
        dva domain link-repo cwow-facility cwow-facility-service
        dva domain link-repo cwow-facility cwow-facility-service --clone-url https://bitbucket.example.com/scm/cgf/cwow-facility-service.git
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    added = link_repo_to_domain(domain_name, repo_slug, repo_name=repo_display, clone_url=clone_url)
    if added:
        console.print(f"[bold green]✓[/bold green] Repo '{repo_slug}' linked to domain '{domain_name}'.")
        record_activity(
            command="domain", subcommand="link-repo",
            args={"domain": domain_name, "repo": repo_slug},
        )
    else:
        console.print(f"[yellow]⚠ Repo '{repo_slug}' is already linked to '{domain_name}'.[/yellow]")


# ---------------------------------------------------------------------------
# dva domain unlink-repo
# ---------------------------------------------------------------------------

@domain_app.command("unlink-repo")
def unlink_repo(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    repo_slug: Annotated[str, typer.Argument(help="Repository slug to unlink")],
) -> None:
    """
    Unlink a repository from a domain.

    Examples:
        dva domain unlink-repo cwow-facility cwow-facility-service
    """
    removed = unlink_repo_from_domain(domain_name, repo_slug)
    if removed:
        console.print(f"[bold green]✓[/bold green] Repo '{repo_slug}' unlinked from '{domain_name}'.")
        record_activity(
            command="domain", subcommand="unlink-repo",
            args={"domain": domain_name, "repo": repo_slug},
        )
    else:
        console.print(f"[red]✗ Repo '{repo_slug}' not found in domain '{domain_name}'.[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# dva domain repos
# ---------------------------------------------------------------------------

@domain_app.command("repos")
def list_repos(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
) -> None:
    """
    List repositories linked to a domain.

    Examples:
        dva domain repos cwow-facility
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    repos = get_domain_repos(domain_name)
    if not repos:
        console.print(f"[yellow]No repos linked to '{domain_name}'.[/yellow]")
        console.print(f"[dim]Link repos with: dva domain link-repo {domain_name} <repo-slug>[/dim]")
        return

    table = Table(title=f"Repos in {domain_name} ({len(repos)})")
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="dim")
    table.add_column("Onboarded", style="bold")
    table.add_column("Onboarded At", style="dim")

    for r in repos:
        onboarded = "[green]✓[/green]" if r.get("onboarded") else "[dim]—[/dim]"
        table.add_row(
            r["repo_slug"],
            r.get("repo_name") or "—",
            onboarded,
            (r.get("onboarded_at") or "—")[:19],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# dva domain fetch-repos
# ---------------------------------------------------------------------------

def _interactive_repo_picker(repos: list[dict], already_linked: set[str]) -> list[dict]:
    """Present an interactive picker for selecting repos.

    Returns the list of selected repo dicts.
    Uses Rich + simple numbered input for broad terminal compatibility.
    """
    # Show numbered list
    console.print()
    table = Table(title=f"Available Repositories ({len(repos)})", show_lines=False)
    table.add_column("#", style="bold", justify="right", width=4)
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="dim")
    table.add_column("Status", style="bold")

    for i, r in enumerate(repos, 1):
        status = "[green]✓ linked[/green]" if r["slug"] in already_linked else "[dim]—[/dim]"
        table.add_row(str(i), r["slug"], r["name"] or "—", status)
    console.print(table)

    console.print(
        "\n[bold]Select repos to link.[/bold]  "
        "Enter numbers separated by commas, ranges (e.g. 1-5), or 'all'."
    )
    console.print("[dim]Already-linked repos will be skipped.  Press Enter with no input to cancel.[/dim]")

    raw = input("\n→ Selection: ").strip()
    if not raw:
        return []

    selected_indices: set[int] = set()
    if raw.lower() == "all":
        selected_indices = set(range(1, len(repos) + 1))
    else:
        for part in raw.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    lo, hi = part.split("-", 1)
                    for n in range(int(lo), int(hi) + 1):
                        selected_indices.add(n)
                except ValueError:
                    console.print(f"[yellow]Skipping invalid range: {part}[/yellow]")
            else:
                try:
                    selected_indices.add(int(part))
                except ValueError:
                    console.print(f"[yellow]Skipping invalid input: {part}[/yellow]")

    # Filter to valid, non-already-linked repos
    selected = []
    for idx in sorted(selected_indices):
        if 1 <= idx <= len(repos):
            r = repos[idx - 1]
            if r["slug"] not in already_linked:
                selected.append(r)

    return selected


@domain_app.command("fetch-repos")
def fetch_repos(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max repos to fetch")] = 500,
    auto_link: Annotated[bool, typer.Option("--all", help="Link all repos without prompting")] = False,
    filter_text: Annotated[str, typer.Option("--filter", "-f", help="Filter repo slugs containing this text")] = None,
) -> None:
    """
    Fetch repos from the domain's Bitbucket project and interactively select which to link.

    Calls the Bitbucket MCP server (credentials managed there).
    The domain must have a Bitbucket project key (set via --bb on create/update).

    Examples:
        dva domain fetch-repos cwow-facility
        dva domain fetch-repos cwow-facility --filter cwow
        dva domain fetch-repos cwow-facility --all
    """
    from agentic_cli.mcp_tool_client import (
        MCPToolError, bb_list_project_repos, parse_project_key,
    )

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    bb_project = parse_project_key(d.get("bitbucket_project") or "")
    if not bb_project:
        console.print(f"[red]✗ Domain '{domain_name}' has no Bitbucket project key.[/red]")
        console.print(f"[dim]Set one with: dva domain update {domain_name} --bb <PROJECT_KEY>[/dim]")
        raise typer.Exit(1)

    # Fetch repos via Bitbucket MCP
    console.print(f"Fetching repos from Bitbucket project [cyan]{bb_project}[/cyan] via MCP...")
    try:
        repos = bb_list_project_repos(bb_project, limit=limit)
    except MCPToolError as e:
        console.print(f"[red]✗ {e}[/red]")
        if e.is_connection_error:
            console.print("[dim]Is the Bitbucket MCP server running? (docker compose up bitbucket-mcp)[/dim]")
        raise typer.Exit(1)

    if not repos:
        console.print(f"[yellow]No repos found in project '{bb_project}'.[/yellow]")
        return

    # Apply text filter
    if filter_text:
        repos = [r for r in repos if filter_text.lower() in r.get("slug", r.get("name", "")).lower()]
        if not repos:
            console.print(f"[yellow]No repos matching '{filter_text}' in project '{bb_project}'.[/yellow]")
            return

    console.print(f"Found [bold]{len(repos)}[/bold] repos in project [cyan]{bb_project}[/cyan].")

    # Get already-linked repos
    existing = get_domain_repos(domain_name)
    already_linked = {r["repo_slug"] for r in existing}

    if auto_link:
        selected = [r for r in repos if r.get("slug", r.get("name", "")) not in already_linked]
    else:
        selected = _interactive_repo_picker(repos, already_linked)

    if not selected:
        console.print("[dim]No new repos selected.[/dim]")
        return

    # Batch link
    linked_count = 0
    for r in selected:
        slug = r.get("slug", r.get("name", ""))
        added = link_repo_to_domain(
            domain_name,
            slug,
            repo_name=r.get("name", slug),
            clone_url=r.get("clone_url_https") or r.get("clone_url_ssh") or r.get("clone_url", ""),
        )
        if added:
            linked_count += 1
            console.print(f"  [green]✓[/green] {slug}")

    console.print(
        f"\n[bold green]✓[/bold green] Linked [bold]{linked_count}[/bold] repos to [cyan]{domain_name}[/cyan]."
    )

    if linked_count > 0:
        console.print(f"[dim]View linked repos: dva domain repos {domain_name}[/dim]")

    record_activity(
        command="domain", subcommand="fetch-repos",
        args={
            "domain": domain_name,
            "bb_project": bb_project,
            "fetched": len(repos),
            "linked": linked_count,
        },
    )


# ---------------------------------------------------------------------------
# dva domain add-docs
# ---------------------------------------------------------------------------

def _interactive_doc_picker(pages: list[dict], already_tracked: set[str]) -> list[dict]:
    """Present an interactive picker for selecting Confluence pages."""
    console.print()
    table = Table(title=f"Available Pages ({len(pages)})", show_lines=False)
    table.add_column("#", style="bold", justify="right", width=4)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Title", style="cyan")
    table.add_column("Version", justify="right", width=8)
    table.add_column("Status", style="bold")

    for i, p in enumerate(pages, 1):
        status = "[green]✓ tracked[/green]" if p["id"] in already_tracked else "[dim]—[/dim]"
        table.add_row(str(i), str(p["id"]), p["title"] or "—", str(p.get("version", 0)), status)
    console.print(table)

    console.print(
        "\n[bold]Select pages to track.[/bold]  "
        "Enter numbers separated by commas, ranges (e.g. 1-5), or 'all'."
    )
    console.print("[dim]Already-tracked pages will be skipped.  Press Enter to cancel.[/dim]")

    raw = input("\n→ Selection: ").strip()
    if not raw:
        return []

    selected_indices: set[int] = set()
    if raw.lower() == "all":
        selected_indices = set(range(1, len(pages) + 1))
    else:
        for part in raw.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    lo, hi = part.split("-", 1)
                    for n in range(int(lo), int(hi) + 1):
                        selected_indices.add(n)
                except ValueError:
                    console.print(f"[yellow]Skipping invalid range: {part}[/yellow]")
            else:
                try:
                    selected_indices.add(int(part))
                except ValueError:
                    console.print(f"[yellow]Skipping invalid input: {part}[/yellow]")

    selected = []
    for idx in sorted(selected_indices):
        if 1 <= idx <= len(pages):
            p = pages[idx - 1]
            if p["id"] not in already_tracked:
                selected.append(p)
    return selected


@domain_app.command("add-docs")
def add_docs(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max pages to fetch")] = 200,
    auto_add: Annotated[bool, typer.Option("--all", help="Track all pages without prompting")] = False,
    filter_text: Annotated[str, typer.Option("--filter", "-f", help="Filter page titles containing this text")] = None,
) -> None:
    """
    Fetch pages from the domain's Confluence space and select which to track.

    Calls the Confluence MCP server (credentials managed there).
    The domain must have a Confluence space key (set via --confluence on create/update).

    Examples:
        dva domain add-docs cwow-facility
        dva domain add-docs cwow-facility --filter architecture
        dva domain add-docs cwow-facility --all
    """
    from agentic_cli.mcp_tool_client import (
        MCPToolError, confluence_get_space_pages, parse_space_key,
    )

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    space_key = parse_space_key(d.get("confluence_space") or "")
    if not space_key:
        console.print(f"[red]✗ Domain '{domain_name}' has no Confluence space key.[/red]")
        console.print(f"[dim]Set one with: dva domain update {domain_name} --confluence <SPACE_KEY>[/dim]")
        raise typer.Exit(1)

    console.print(f"Fetching pages from Confluence space [cyan]{space_key}[/cyan] via MCP...")
    try:
        pages = confluence_get_space_pages(space_key, limit=limit)
    except MCPToolError as e:
        console.print(f"[red]✗ {e}[/red]")
        if e.is_connection_error:
            console.print("[dim]Is the Confluence MCP server running? (docker compose up confluence-mcp)[/dim]")
        raise typer.Exit(1)

    if not pages:
        console.print(f"[yellow]No pages found in space '{space_key}'.[/yellow]")
        return

    if filter_text:
        pages = [p for p in pages if filter_text.lower() in (p.get("title") or "").lower()]
        if not pages:
            console.print(f"[yellow]No pages matching '{filter_text}' in space '{space_key}'.[/yellow]")
            return

    console.print(f"Found [bold]{len(pages)}[/bold] pages in space [cyan]{space_key}[/cyan].")

    existing = get_domain_docs(domain_name)
    already_tracked = {dd["source_page_id"] for dd in existing}

    if auto_add:
        selected = [p for p in pages if str(p["id"]) not in already_tracked]
    else:
        selected = _interactive_doc_picker(pages, already_tracked)

    if not selected:
        console.print("[dim]No new pages selected.[/dim]")
        return

    tracked_count = 0
    for p in selected:
        added = add_domain_doc(
            domain_name,
            source_page_id=str(p["id"]),
            source_space_key=space_key,
            title=p.get("title"),
            source_version=p.get("version", 0),
        )
        if added:
            tracked_count += 1
            console.print(f"  [green]✓[/green] {p['title'] or p['id']}")

    console.print(
        f"\n[bold green]✓[/bold green] Tracked [bold]{tracked_count}[/bold] docs for [cyan]{domain_name}[/cyan]."
    )
    if tracked_count > 0:
        console.print(f"[dim]View docs: dva domain docs {domain_name}[/dim]")

    record_activity(
        command="domain", subcommand="add-docs",
        args={"domain": domain_name, "space": space_key, "tracked": tracked_count},
    )


# ---------------------------------------------------------------------------
# dva domain docs
# ---------------------------------------------------------------------------

@domain_app.command("docs")
def list_docs(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
) -> None:
    """
    List tracked Confluence docs for a domain.

    Examples:
        dva domain docs cwow-facility
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    docs = get_domain_docs(domain_name)
    if not docs:
        console.print(f"[yellow]No docs tracked for '{domain_name}'.[/yellow]")
        console.print(f"[dim]Add docs with: dva domain add-docs {domain_name}[/dim]")
        return

    table = Table(title=f"Tracked Docs — {domain_name} ({len(docs)})")
    table.add_column("Page ID", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Space", style="dim")
    table.add_column("Src Ver", justify="right")
    table.add_column("Managed ID", style="dim")
    table.add_column("Synced", style="dim")

    for doc in docs:
        table.add_row(
            doc["source_page_id"],
            doc.get("title") or "—",
            doc.get("source_space_key") or "—",
            str(doc.get("source_version", 0)),
            doc.get("managed_page_id") or "—",
            (doc.get("synced_at") or "—")[:19],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# dva domain sync-docs
# ---------------------------------------------------------------------------

@domain_app.command("sync-docs")
def sync_docs(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without making changes")] = False,
) -> None:
    """
    Sync tracked docs to the domain's managed Confluence space.

    Creates a managed space (DVA-<SLUG>) if it doesn't exist, then copies
    or updates each tracked doc into the managed space.

    Calls the Confluence MCP server (credentials managed there).

    Examples:
        dva domain sync-docs cwow-facility
        dva domain sync-docs cwow-facility --dry-run
    """
    from agentic_cli.mcp_tool_client import (
        MCPToolError,
        confluence_get_space,
        confluence_create_space,
        confluence_get_page,
        confluence_create_page,
        confluence_update_page,
    )

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    docs = get_domain_docs(domain_name)
    if not docs:
        console.print(f"[yellow]No docs tracked for '{domain_name}'. fRun '{CLI_NAME} domain add-docs' first.[/yellow]")
        raise typer.Exit(1)

    managed_key = d.get("managed_confluence_space") or f"DVA-{domain_name.upper().replace('-', '')}"

    console.print(f"Syncing [bold]{len(docs)}[/bold] docs to managed space [cyan]{managed_key}[/cyan] via MCP...")

    if dry_run:
        console.print("[dim](Dry run — no changes will be made)[/dim]\n")
        for doc in docs:
            action = "update" if doc.get("managed_page_id") else "create"
            console.print(f"  [yellow]→[/yellow] Would {action}: {doc.get('title') or doc['source_page_id']}")
        console.print(f"\n[dim]{len(docs)} docs would be synced.[/dim]")
        return

    try:
        # Ensure managed space exists
        try:
            space_info = confluence_get_space(managed_key)
            console.print(f"  Using existing managed space: [cyan]{managed_key}[/cyan]")
        except MCPToolError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                space_name = f"DVA Managed — {d.get('product', '')} {d.get('domain', '')}"
                space_info = confluence_create_space(
                    managed_key,
                    space_name,
                    description=f"Managed docs for domain {domain_name}",
                )
                console.print(f"  [green]✓[/green] Created managed space: [cyan]{managed_key}[/cyan]")
                update_domain(domain_name, managed_confluence_space=managed_key)
            else:
                raise

        synced = 0
        for doc in docs:
            source_id = doc["source_page_id"]
            title = doc.get("title") or f"Page {source_id}"

            # Fetch source page content
            try:
                source_page = confluence_get_page(source_id, include_body=True)
            except MCPToolError:
                console.print(f"  [red]✗[/red] Could not read source page {source_id}")
                continue

            body_html = source_page.get("body_html", source_page.get("body", ""))
            source_version = source_page.get("version", 0)

            if doc.get("managed_page_id"):
                # Update existing managed page
                try:
                    managed_page = confluence_get_page(doc["managed_page_id"])
                    updated = confluence_update_page(
                        doc["managed_page_id"],
                        title,
                        body_html,
                        managed_page["version"],
                    )
                    console.print(f"  [green]✓[/green] Updated: {title} (v{updated.get('version', '?')})")
                except MCPToolError:
                    console.print(f"  [red]✗[/red] Failed to update managed page for: {title}")
                    continue
            else:
                # Create new page in managed space
                created = confluence_create_page(managed_key, title, body_html)
                console.print(f"  [green]✓[/green] Created: {title} (id={created.get('id', '?')})")
                add_domain_doc(
                    domain_name,
                    source_page_id=source_id,
                    source_space_key=doc.get("source_space_key"),
                    title=title,
                    managed_page_id=str(created.get("id", "")),
                    source_version=source_version,
                )

            # Update source version tracking
            managed_id = doc.get("managed_page_id") or str(created.get("id", "")) if not doc.get("managed_page_id") else doc["managed_page_id"]
            add_domain_doc(
                domain_name,
                source_page_id=source_id,
                source_space_key=doc.get("source_space_key"),
                title=title,
                managed_page_id=managed_id,
                source_version=source_version,
            )
            synced += 1

    except MCPToolError as e:
        console.print(f"[red]✗ {e}[/red]")
        if e.is_connection_error:
            console.print("[dim]Is the Confluence MCP server running? (docker compose up confluence-mcp)[/dim]")
        raise typer.Exit(1)

    console.print(
        f"\n[bold green]✓[/bold green] Synced [bold]{synced}[/bold]/{len(docs)} docs to [cyan]{managed_key}[/cyan]."
    )

    record_activity(
        command="domain", subcommand="sync-docs",
        args={"domain": domain_name, "managed_space": managed_key, "synced": synced},
    )


# ---------------------------------------------------------------------------
# dva domain gen-skills
# ---------------------------------------------------------------------------

# Default output: skills/domains/<slug>/ next to agentic-cli
_DEFAULT_SKILLS_BASE = Path(__file__).resolve().parents[4] / "skills" / "domains"


@domain_app.command("gen-skills")
def gen_skills(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    role: Annotated[str, typer.Option("--role", "-r", help="Generate only this role (domain, dev, qa, sm, ba)")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Output directory (default: skills/domains/<slug>)")] = None,
) -> None:
    """
    Generate role-based persona skill files for a domain.

    Creates structured Markdown skill files that AI code assistants can
    consume to understand a domain from different perspectives.

    Roles:
        domain  — Overview: repos, docs, tech stack, links
        dev     — Developer: code patterns, PR conventions, build/deploy
        qa      — QA: test strategy, frameworks, coverage targets
        sm      — Scrum Master: Jira workflow, sprint cadence, ceremonies
        ba      — Business Analyst: domain glossary, AC templates, docs

    Examples:
        dva domain gen-skills cwow-facility
        dva domain gen-skills cwow-facility --role dev
        dva domain gen-skills cwow-facility --role sm
        dva domain gen-skills cwow-facility --output /tmp/skills
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    # Validate role
    roles_to_gen = list(ROLES)
    if role:
        role = role.lower()
        if role not in ROLES:
            console.print(f"[red]✗ Unknown role '{role}'. Choose from: {', '.join(ROLES)}[/red]")
            raise typer.Exit(1)
        roles_to_gen = [role]

    # Gather context
    repos = get_domain_repos(domain_name)
    docs = get_domain_docs(domain_name)
    ctx = gather_domain_context(d, repos, docs)

    # Determine output directory
    if output:
        out_dir = Path(output)
    else:
        out_dir = _DEFAULT_SKILLS_BASE / domain_name

    # Generate
    console.print(f"Generating persona skills for [cyan]{domain_name}[/cyan]...")
    written = generate_skill_files(ctx, out_dir, roles_to_gen)

    if not written:
        console.print("[yellow]No files generated.[/yellow]")
        raise typer.Exit(1)

    # Summary
    lines = []
    for r, path in written.items():
        label = ROLE_LABELS.get(r, r)
        lines.append(f"[green]✓[/green] {label:<20s} → {path}")
    lines.append(f"\n[dim]Output: {out_dir}[/dim]")

    console.print(Panel(
        "\n".join(lines),
        title=f"Generated Skills — {domain_name}",
        border_style="green",
    ))

    record_activity(
        command="domain", subcommand="gen-skills",
        args={"domain": domain_name, "roles": roles_to_gen, "output": str(out_dir)},
    )
