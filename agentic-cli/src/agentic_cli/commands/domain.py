"""Domain management commands for agentic-cli.

A domain is a scoped area within a product that ties together a Jira project,
Bitbucket project, Confluence space, and selected repositories.

Products must be registered first via ``{CLI_NAME} product create``.

Hierarchy:
    Product (e.g. CWOW)   ← {CLI_NAME} product create CWOW
      └── Domain (e.g. Facility)  ← {CLI_NAME} domain create Facility --product CWOW
            ├── jira_project: CWOW
            ├── bitbucket_project: CGF
            ├── confluence_space: MTT
            └── repos: [cwow-facility-service, ...]
"""

import json
from typing import Optional

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
    remove_domain_doc,
    mark_domain_repo_onboarded,
    register_workspace,
)
from agentic_cli import persona_workspace as pw
from agentic_cli.meta_repo.detector import detect_domain_meta_repo
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

# Configuration directory and file
AGENT_CONFIG_DIR = Path.home() / ".agent-cli-agentic"
AGENT_CONFIG_FILE = AGENT_CONFIG_DIR / "config.json"


def _load_config() -> dict:
    """Load configuration from file."""
    if AGENT_CONFIG_FILE.exists():
        return json.loads(AGENT_CONFIG_FILE.read_text())
    return {}


def _get_code_workspace() -> Path:
    """Get the configured code workspace directory."""
    config = _load_config()
    workspace = config.get("code_workspace")
    if workspace:
        return Path(workspace).expanduser().resolve()
    # Default to ~/keel-code-workspace
    return Path.home() / "keel-code-workspace"


def _slugify(product: str, domain: str) -> str:
    """Generate a domain slug from product + domain name."""
    return f"{product.lower()}-{domain.lower().replace(' ', '-')}"


# ---------------------------------------------------------------------------
# {CLI_NAME} domain create
# ---------------------------------------------------------------------------

@domain_app.command()
def create(
    domain: Annotated[str, typer.Argument(help="Domain name (e.g. Facility, Patient)")],
    product: Annotated[str, typer.Option("--product", "-p", help="Product this domain belongs to (required)")] = ...,
    description: Annotated[str, typer.Option("--description", "-d", help="Description of this domain")] = None,
    jira_project: Annotated[str, typer.Option("--jira", help="Jira project key")] = None,
    bitbucket_project: Annotated[str, typer.Option("--bb", help="Bitbucket project key")] = None,
    bitbucket_url: Annotated[str, typer.Option("--bb-url", help="Bitbucket project/repo URL")] = None,
    confluence_space: Annotated[str, typer.Option("--confluence", help="Source Confluence space key")] = None,
    jira_dashboard: Annotated[str, typer.Option("--jira-dashboard", help="Jira dashboard URL")] = None,
    jira_board: Annotated[str, typer.Option("--jira-board", help="Jira board name/ID")] = None,
    confluence_url: Annotated[str, typer.Option("--confluence-url", help="Confluence page/space URL")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Comma-separated extra tags")] = None,
) -> None:
    """
    Register a new domain under a product.

    The --product flag is mandatory. The product must already be registered
    via f'{CLI_NAME} product create'. The domain slug is auto-generated as
    <product>-<domain> (lowercase).

    Examples:
        {CLI_NAME} domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT
        {CLI_NAME} domain create Patient --product CWOW --jira CWOW --bb CGP --tags "spanner,healthcare"
        {CLI_NAME} domain create Imaging --product IMTO --jira IMTO --bb IMTO
    """
    product_upper = product.upper()

    # Validate product exists
    prod = get_product(product_upper)
    if not prod:
        console.print(f"[red]✗ Product '{product_upper}' not found.[/red]")
        console.print(f"[dim]Register it first: {CLI_NAME} product create {product_upper}[/dim]")
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
        jira_board=jira_board,
        bitbucket_project=bitbucket_project,
        bitbucket_url=bitbucket_url,
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
    if bitbucket_url:
        panel_lines.append(f"[cyan]Bitbucket URL:[/cyan] {bitbucket_url}")
    if confluence_space:
        panel_lines.append(f"[cyan]Confluence Space:[/cyan] {confluence_space}")
    if jira_dashboard:
        panel_lines.append(f"[cyan]Jira Dashboard:[/cyan] {jira_dashboard}")
    if jira_board:
        panel_lines.append(f"[cyan]Jira Board:[/cyan] {jira_board}")
    if confluence_url:
        panel_lines.append(f"[cyan]Confluence URL:[/cyan] {confluence_url}")
    if tag_list:
        panel_lines.append(f"[cyan]Tags:[/cyan] {', '.join(tag_list)}")

    console.print(Panel("\n".join(panel_lines), title="Domain Details"))

    # Hints
    if bitbucket_project:
        console.print(f"\n[dim]Next: Link repos with:[/dim]  {CLI_NAME} domain link-repo {name} <repo-slug>")
    else:
        console.print(f"\n[dim]Tip: Add a Bitbucket project:[/dim]  {CLI_NAME} domain update {name} --bb <PROJECT_KEY>")

    record_activity(
        command="domain", subcommand="create",
        args={"name": name, "product": product_upper, "domain": domain},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} domain list
# ---------------------------------------------------------------------------

@domain_app.command("list")
def list_domains(
    product: Annotated[str, typer.Option("--product", "-p", help="Filter by product")] = None,
) -> None:
    """
    List all registered domains.

    Examples:
        {CLI_NAME} domain list
        {CLI_NAME} domain list --product CWOW
    """
    domains = get_domains(product=product.upper() if product else None)

    if not domains:
        filter_msg = f" for product '{product.upper()}'" if product else ""
        console.print(f"[yellow]No domains registered{filter_msg}.[/yellow]")
        console.print(f"[dim]Register one with: {CLI_NAME} domain create <PRODUCT> <DOMAIN>[/dim]")
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
# {CLI_NAME} domain show
# ---------------------------------------------------------------------------

@domain_app.command()
def show(
    name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
) -> None:
    """
    Show detailed information about a domain.

    Examples:
        {CLI_NAME} domain show cwow-facility
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
    if d.get("jira_board"):
        lines.append(f"[cyan]Jira Board:[/cyan] {d['jira_board']}")
    if d.get("confluence_url"):
        lines.append(f"[cyan]Confluence URL:[/cyan] {d['confluence_url']}")
    kg_ingested = d.get("kg_ingested", 0)
    kg_status = "[green]✓[/green]" if kg_ingested else "[dim]—[/dim]"
    lines.append(f"[cyan]KG Ingested:[/cyan] {kg_status}")
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
# {CLI_NAME} domain update
# ---------------------------------------------------------------------------

@domain_app.command()
def update(
    name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    product: Annotated[str, typer.Option("--product", help="Update product name")] = None,
    domain_name: Annotated[str, typer.Option("--domain", help="Update domain label")] = None,
    description: Annotated[str, typer.Option("--description", "-d", help="Update description")] = None,
    jira_project: Annotated[str, typer.Option("--jira", help="Update Jira project key")] = None,
    bitbucket_project: Annotated[str, typer.Option("--bb", help="Update Bitbucket project key")] = None,
    bitbucket_url: Annotated[str, typer.Option("--bb-url", help="Update Bitbucket project/repo URL")] = None,
    confluence_space: Annotated[str, typer.Option("--confluence", help="Update Confluence space key")] = None,
    jira_dashboard: Annotated[str, typer.Option("--jira-dashboard", help="Jira dashboard URL")] = None,
    jira_board: Annotated[str, typer.Option("--jira-board", help="Jira board name/ID")] = None,
    confluence_url: Annotated[str, typer.Option("--confluence-url", help="Confluence page/space URL")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Replace tags (comma-separated)")] = None,
) -> None:
    """
    Update an existing domain's fields.

    Examples:
        {CLI_NAME} domain update cwow-facility --jira CWOW --bb CGF
        {CLI_NAME} domain update cwow-facility --jira-dashboard https://jira.example.com/...
        {CLI_NAME} domain update cwow-facility --confluence-url https://confluence.example.com/...
        {CLI_NAME} domain update cwow-facility --tags "spanner,healthcare,gcp"
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
    if bitbucket_url:
        fields["bitbucket_url"] = bitbucket_url
    if confluence_space:
        fields["confluence_space"] = confluence_space
    if jira_dashboard:
        fields["jira_dashboard"] = jira_dashboard
    if jira_board:
        fields["jira_board"] = jira_board
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
# {CLI_NAME} domain remove
# ---------------------------------------------------------------------------

@domain_app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """
    Remove a domain and all its linked repos and docs.

    Examples:
        {CLI_NAME} domain remove cwow-facility
        {CLI_NAME} domain remove cwow-facility --yes
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
# {CLI_NAME} domain link-repo
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
        {CLI_NAME} domain link-repo cwow-facility cwow-facility-service
        {CLI_NAME} domain link-repo cwow-facility cwow-facility-service --clone-url https://bitbucket.example.com/scm/cgf/cwow-facility-service.git
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
# {CLI_NAME} domain unlink-repo
# ---------------------------------------------------------------------------

@domain_app.command("reset-repos")
def fix_repo_urls(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
) -> None:
    """
    Reset/remove all linked repos from a domain.
    
    Removes all repos so you can link them again with correct URLs.
    
    Examples:
        {CLI_NAME} domain reset-repos cwow-facility
    """
    from agentic_cli.tracker import get_domain_repos, unlink_repo_from_domain
    
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)
    
    repos = get_domain_repos(domain_name)
    if not repos:
        console.print(f"[yellow]No repos linked to domain '{domain_name}'.[/yellow]")
        return
    
    console.print(f"[cyan]Removing all repos from domain '{domain_name}'...[/cyan]")
    
    removed_count = 0
    for repo in repos:
        removed = unlink_repo_from_domain(domain_name, repo["repo_slug"])
        if removed:
            console.print(f"  [green]✓[/green] Removed: {repo['repo_slug']}")
            removed_count += 1
    
    if removed_count > 0:
        console.print(f"\n[bold green]✓[/bold green] Removed {removed_count} repo(s).")
        console.print(f"[dim]You can now link repos again using '{CLI_NAME} domain link-repo'[/dim]")
        record_activity(
            command="domain", subcommand="reset-repos",
            args={"domain": domain_name, "removed": removed_count},
        )
    else:
        console.print(f"\n[dim]No repos were removed.[/dim]")


@domain_app.command("unlink-repo")
def unlink_repo(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    repo_slug: Annotated[str, typer.Argument(help="Repository slug to unlink")],
) -> None:
    """
    Unlink a repository from a domain.

    Examples:
        {CLI_NAME} domain unlink-repo cwow-facility cwow-facility-service
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
# {CLI_NAME} domain repos
# ---------------------------------------------------------------------------

@domain_app.command("repos")
def list_repos(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
) -> None:
    """
    List repositories linked to a domain.

    Examples:
        {CLI_NAME} domain repos cwow-facility
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    repos = get_domain_repos(domain_name)
    if not repos:
        console.print(f"[yellow]No repos linked to '{domain_name}'.[/yellow]")
        console.print(f"[dim]Link repos with: {CLI_NAME} domain link-repo {domain_name} <repo-slug>[/dim]")
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
# {CLI_NAME} domain fetch-repos
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
        {CLI_NAME} domain fetch-repos cwow-facility
        {CLI_NAME} domain fetch-repos cwow-facility --filter cwow
        {CLI_NAME} domain fetch-repos cwow-facility --all
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
        console.print(f"[dim]Set one with: {CLI_NAME} domain update {domain_name} --bb <PROJECT_KEY>[/dim]")
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

    # Filter out deprecated repos
    repos = [r for r in repos if "deprecated" not in r.get("slug", "").lower() and "deprecated" not in r.get("name", "").lower()]
    if not repos:
        console.print(f"[yellow]No non-deprecated repos found in project '{bb_project}'.[/yellow]")
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
        console.print(f"[dim]View linked repos: {CLI_NAME} domain repos {domain_name}[/dim]")

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
# {CLI_NAME} domain add-docs
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
    The domain must have a Confluence space key (set via --confluence on create/update)
    or a Confluence URL (set via --confluence-url on create/update).

    When using a page URL, all descendant pages (children of children) are fetched recursively.
    When using a space key, only pages in that space are fetched (not recursive).

    Examples:
        {CLI_NAME} domain add-docs cwow-facility
        {CLI_NAME} domain add-docs cwow-facility --filter architecture
        {CLI_NAME} domain add-docs cwow-facility --all
    """
    from agentic_cli.mcp_tool_client import (
        MCPToolError, confluence_get_space_pages, confluence_get_page_children,
        confluence_get_all_descendants, parse_space_key, parse_confluence_url,
    )

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    # Try confluence_url first, then confluence_space
    space_key = ""
    page_id = ""
    
    # Try parsing confluence_url first
    confluence_url = d.get("confluence_url") or ""
    if confluence_url:
        space_key, page_id = parse_confluence_url(confluence_url)
    
    # If no URL or URL didn't yield space/page, try confluence_space
    if not space_key and not page_id:
        space_key = parse_space_key(d.get("confluence_space") or "")
    
    if not space_key and not page_id:
        console.print(f"[red]✗ Domain '{domain_name}' has no Confluence space key or URL.[/red]")
        console.print(f"[dim]Set one with: {CLI_NAME} domain update {domain_name} --confluence <SPACE_KEY>[/dim]")
        console.print(f"[dim]Or: {CLI_NAME} domain update {domain_name} --confluence-url <URL>[/dim]")
        raise typer.Exit(1)

    # Fetch pages based on what we have
    if page_id:
        console.print(f"Fetching all descendant pages from Confluence page [cyan]{page_id}[/cyan] via MCP...")
        try:
            pages = confluence_get_all_descendants(page_id)
        except MCPToolError as e:
            console.print(f"[red]✗ {e}[/red]")
            if e.is_connection_error:
                console.print("[dim]Is the Confluence MCP server running? (docker compose up confluence-mcp)[/dim]")
            raise typer.Exit(1)
    else:
        console.print(f"Fetching pages from Confluence space [cyan]{space_key}[/cyan] via MCP...")
        try:
            pages = confluence_get_space_pages(space_key, limit=limit)
        except MCPToolError as e:
            console.print(f"[red]✗ {e}[/red]")
            if e.is_connection_error:
                console.print("[dim]Is the Confluence MCP server running? (docker compose up confluence-mcp)[/dim]")
            raise typer.Exit(1)

    if not pages:
        source_desc = f"page {page_id}" if page_id else f"space '{space_key}'"
        console.print(f"[yellow]No pages found in {source_desc}.[/yellow]")
        return

    if filter_text:
        pages = [p for p in pages if filter_text.lower() in (p.get("title") or "").lower()]
        if not pages:
            source_desc = f"page {page_id}" if page_id else f"space '{space_key}'"
            console.print(f"[yellow]No pages matching '{filter_text}' in {source_desc}.[/yellow]")
            return

    # Auto-discover cross-space release pages.
    #
    # This is the dominant network cost of add-docs: one body fetch per page,
    # plus a CQL search per cross-space link. Run the per-page work in a bounded
    # thread pool so N sequential round-trips become ~N/workers — the MCP calls
    # are independent HTTP requests, so this is safe to parallelize.
    console.print("[dim]Scanning for cross-space release page links...[/dim]")
    import concurrent.futures
    import json
    import re

    from agentic_cli.mcp_tool_client import (
        confluence_get_page, call_mcp_tool, _get_confluence_url, MCPToolError
    )

    def _scan_page(p: dict) -> list[dict]:
        """Fetch a page body and resolve any cross-space links it references."""
        found: list[dict] = []
        try:
            page = confluence_get_page(str(p["id"]), include_body=True)
        except MCPToolError:
            return found
        body_html = page.get("body_html", "")
        # Pattern: <ri:page ri:space-key="CWOV" ri:content-title="Release 27: Patients" />
        page_links = re.findall(
            r'<ri:page ri:space-key="([^"]+)" ri:content-title="([^"]+)"', body_html
        )
        for link_space, link_title in page_links:
            if link_space == space_key:
                continue  # same-space link — not cross-space
            try:
                cql = f'space="{link_space}" AND title="{link_title}" AND type=page'
                search_results = call_mcp_tool(
                    _get_confluence_url(), "search_confluence_cql",
                    {"cql": cql, "limit": 1},
                )
                if not search_results or search_results == "0":
                    continue
                results = json.loads(search_results) if isinstance(search_results, str) else search_results
                linked_id = None
                if isinstance(results, list) and results:
                    linked_id = results[0].get("id")
                elif isinstance(results, dict):
                    if results.get("results"):
                        linked_id = results["results"][0].get("id")
                    elif "id" in results:
                        linked_id = results.get("id")
                if linked_id:
                    found.append({
                        "id": linked_id,
                        "title": link_title,
                        "space": link_space,
                        "version": 0,
                        "_cross_space": True,
                    })
            except (MCPToolError, json.JSONDecodeError, KeyError):
                continue
        return found

    cross_space_pages: list[dict] = []
    seen_ids: set[str] = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for batch in ex.map(_scan_page, pages):
            for cp in batch:
                if cp["id"] in seen_ids:
                    continue
                seen_ids.add(cp["id"])
                cross_space_pages.append(cp)
                console.print(
                    f"  [dim]→ Found cross-space page: {cp['title']} ({cp['space']})[/dim]"
                )

    if cross_space_pages:
        console.print(f"[dim]Found [bold]{len(cross_space_pages)}[/bold] cross-space pages to add.[/dim]")
        pages.extend(cross_space_pages)

    source_desc = f"page {page_id}" if page_id else f"space '{space_key}'"
    console.print(f"Found [bold]{len(pages)}[/bold] pages in {source_desc}.")

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
        # Use the page's actual space key for cross-space pages
        page_space_key = p.get("space", space_key) if p.get("_cross_space") else space_key
        
        added = add_domain_doc(
            domain_name,
            source_page_id=str(p["id"]),
            source_space_key=page_space_key,
            title=p.get("title"),
            source_version=p.get("version", 0),
        )
        if added:
            tracked_count += 1
            space_label = f" [{page_space_key}]" if p.get("_cross_space") else ""
            console.print(f"  [green]✓[/green] {p['title'] or p['id']}{space_label}")

    console.print(
        f"\n[bold green]✓[/bold green] Tracked [bold]{tracked_count}[/bold] docs for [cyan]{domain_name}[/cyan]."
    )
    if tracked_count > 0:
        console.print(f"[dim]View docs: {CLI_NAME} domain docs {domain_name}[/dim]")

    record_activity(
        command="domain", subcommand="add-docs",
        args={"domain": domain_name, "space": space_key, "tracked": tracked_count},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} domain docs
# ---------------------------------------------------------------------------

@domain_app.command("docs")
def list_docs(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
) -> None:
    """
    List tracked Confluence docs for a domain.

    Examples:
        {CLI_NAME} domain docs cwow-facility
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    docs = get_domain_docs(domain_name)
    if not docs:
        console.print(f"[yellow]No docs tracked for '{domain_name}'.[/yellow]")
        console.print(f"[dim]Add docs with: {CLI_NAME} domain add-docs {domain_name}[/dim]")
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


@domain_app.command("remove-docs")
def remove_docs(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    page_ids: Annotated[str, typer.Option("--page-ids", "-p", help="Comma-separated Confluence page IDs to remove (e.g., 1170473595,1170488862)")] = "",
    all: Annotated[bool, typer.Option("--all", help="Remove all tracked docs from the domain")] = False,
) -> None:
    """
    Remove tracked Confluence docs from a domain.

    Examples:
        {CLI_NAME} domain remove-docs cwow-facility --page-ids 1170473595,1170488862
        {CLI_NAME} domain remove-docs cwow-facility --all
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    if not page_ids and not all:
        console.print(f"[red]✗ Either --page-ids or --all is required.[/red]")
        console.print(f"[dim]View docs with: {CLI_NAME} domain docs {domain_name}[/dim]")
        raise typer.Exit(1)

    if all:
        # Remove all docs
        docs = get_domain_docs(domain_name)
        if not docs:
            console.print(f"[yellow]No docs tracked for '{domain_name}'.[/yellow]")
            raise typer.Exit(0)
        
        removed_count = 0
        for doc in docs:
            if remove_domain_doc(domain_name, doc["source_page_id"]):
                removed_count += 1
        
        console.print(f"[green]✓[/green] Removed {removed_count} doc(s) from '{domain_name}'")
        record_activity("domain_remove_docs_all", {"domain": domain_name, "count": removed_count})
    else:
        # Parse comma-separated page IDs
        page_id_list = [pid.strip() for pid in page_ids.split(",") if pid.strip()]
        
        # Remove specific page IDs
        removed_count = 0
        for page_id in page_id_list:
            if remove_domain_doc(domain_name, page_id):
                console.print(f"[green]✓[/green] Removed page {page_id}")
                removed_count += 1
            else:
                console.print(f"[yellow]⚠ Page {page_id} not found in '{domain_name}'[/yellow]")
        
        if removed_count > 0:
            record_activity("domain_remove_docs", {"domain": domain_name, "page_ids": page_id_list, "count": removed_count})
        
        console.print(f"[dim]Removed {removed_count}/{len(page_id_list)} page(s)[/dim]")


# ---------------------------------------------------------------------------
# {CLI_NAME} domain sync-docs
# ---------------------------------------------------------------------------

@domain_app.command("sync-docs")
def sync_docs(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug)")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without making changes")] = False,
) -> None:
    """
    Sync tracked docs to the domain's managed Confluence space.

    Creates a managed space (KEEL-<SLUG>) if it doesn't exist, then copies
    or updates each tracked doc into the managed space.

    Calls the Confluence MCP server (credentials managed there).

    Examples:
        {CLI_NAME} domain sync-docs cwow-facility
        {CLI_NAME} domain sync-docs cwow-facility --dry-run
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

    managed_key = d.get("managed_confluence_space") or f"KEEL-{domain_name.upper().replace('-', '')}"

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
                space_name = f"KEEL Managed — {d.get('product', '')} {d.get('domain', '')}"
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
# {CLI_NAME} domain gen-skills
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
        {CLI_NAME} domain gen-skills cwow-facility
        {CLI_NAME} domain gen-skills cwow-facility --role dev
        {CLI_NAME} domain gen-skills cwow-facility --role sm
        {CLI_NAME} domain gen-skills cwow-facility --output /tmp/skills
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


@domain_app.command("regen-personas")
def regen_personas(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    persona: Annotated[list[str], typer.Option("--persona", "-p", help="Only regenerate these persona ids (repeatable)")] = None,
    product_meta: Annotated[str, typer.Option("--product-meta", help="Path/URL of the product meta-repo (to read personas.yaml)")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Meta-repo path (default: workspace/<domain>/domain-<domain>-meta)")] = None,
    enrich: Annotated[bool, typer.Option("--enrich/--no-enrich", help="AI-enrich custom personas marked ai_enrich")] = False,
) -> None:
    """
    (Re)generate persona skills into an existing domain meta-repo.

    Resolves the effective persona catalog (built-in defaults + product-specific
    personas from the product meta-repo's personas.yaml) and renders each into
    <meta-repo>/.agents/skills/personas/<id>/SKILL.md. Safe to re-run; existing
    persona files are overwritten.

    Examples:
        {CLI_NAME} domain regen-personas cwow-facility
        {CLI_NAME} domain regen-personas cwow-facility --persona tech-lead
        {CLI_NAME} domain regen-personas cwow-facility --enrich
    """
    from agentic_cli.persona_catalog import resolve_personas
    from agentic_cli.skill_generator import generate_personas

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    # Locate the domain meta-repo.
    if output:
        meta_repo_path = Path(output).resolve()
    else:
        workspace = _get_code_workspace()
        meta_repo_path = workspace / domain_name / f"domain-{domain_name}-meta"
    if not meta_repo_path.exists():
        console.print(f"[red]✗ Domain meta-repo not found at {meta_repo_path}[/red]")
        console.print(f"[dim]Create it first: {CLI_NAME} domain init-meta {domain_name}[/dim]")
        raise typer.Exit(1)

    # Resolve the product meta path to read the persona catalog.
    product = d.get("product", "")
    product_meta_path = None
    if product_meta and Path(product_meta).exists():
        product_meta_path = Path(product_meta)
    elif product:
        slug = product.lower()
        product_meta_path = _get_code_workspace() / slug / f"product-{slug}-meta"

    personas = resolve_personas(product_meta_path)
    if persona:
        wanted = set(persona)
        personas = [p for p in personas if p.id in wanted]
        if not personas:
            console.print(f"[red]✗ No matching personas for: {', '.join(persona)}[/red]")
            raise typer.Exit(1)

    repos = get_domain_repos(domain_name)
    docs = get_domain_docs(domain_name)
    ctx = gather_domain_context(d, repos, docs)

    personas_dir = meta_repo_path / ".agents" / "skills" / "personas"
    console.print(f"Regenerating personas for [cyan]{domain_name}[/cyan]...")
    written = generate_personas(personas, ctx, personas_dir, enrich=enrich)

    lines = []
    for spec in personas:
        path = written.get(spec.id)
        if path:
            lines.append(f"[green]✓[/green] {spec.label:<22s} → {path.relative_to(meta_repo_path)}")
    lines.append(f"\n[dim]Output: {personas_dir}[/dim]")
    console.print(Panel("\n".join(lines), title=f"Personas — {domain_name}", border_style="green"))

    record_activity(
        command="domain", subcommand="regen-personas",
        args={"domain": domain_name, "personas": [p.id for p in personas], "enrich": enrich},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} domain init-context
# ---------------------------------------------------------------------------

def _resolve_context_meta_path(domain_name: str, output: Optional[str] = None) -> Path:
    """Resolve the unified context-meta repo path.

    Default: ``<workspace>/<domain>/<domain>-context-meta``.
    """
    if output:
        return Path(output).resolve()
    workspace = _get_code_workspace()
    return workspace / domain_name / f"{domain_name}-context-meta"


@domain_app.command("init")
def init_domain(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output directory for the unified context-meta repo")] = None,
    git_init: Annotated[bool, typer.Option("--git-init/--no-git-init", help="Initialize as a git repo (registers repo submodules)")] = True,
    git_remote: Annotated[str, typer.Option("--git-remote", help="Git remote URL to set as origin")] = None,
    bootstrap_skills: Annotated[bool, typer.Option("--bootstrap-skills/--no-bootstrap-skills", help="Inject superpowers skills as baseline")] = True,
    superpowers_url: Annotated[str, typer.Option("--superpowers-url", help="Git URL for superpowers skills repo")] = "https://github.com/venkatchinta/superpowers.git",
    code_assist_tool: Annotated[str, typer.Option("--code-assist-tool", help="Code assist tool (auto, windsurf, cursor, devin, generic). 'auto' detects the IDE.")] = "auto",
    product_meta_url: Annotated[str, typer.Option("--product-meta", help="Git URL/path of the product meta-repo to reference as a submodule (outer-loop shared tier)")] = None,
    clone_repos: Annotated[bool, typer.Option("--clone-repos/--no-clone-repos", help="Clone submodule working trees now (default: register + fetch lazily via `make init`)")] = False,
    no_kg: Annotated[bool, typer.Option("--no-kg", help="Skip the Knowledge Graph query (fastest; uses placeholder content)")] = False,
    kg_timeout: Annotated[int, typer.Option("--kg-timeout", help="Max seconds to wait for the KG query before falling back to placeholder content")] = 20,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite an existing repo without prompting (required in non-interactive contexts such as the dashboard)")] = False,
) -> None:
    """
    Initialize a unified domain **context-meta** repository (context + meta in one).

    This single command replaces the previous two-step ``init-context`` +
    ``init-meta`` flow. It creates ``<workspace>/<domain>/<domain>-context-meta``
    containing BOTH:
      - Context: ``.domain/`` (KG business context, metadata, architecture),
        ``.skills/`` (superpowers + project-context), README.
      - Meta: ``.platform/config`` (governance), ``.agents/skills/personas``,
        ``repos/`` submodules, ``docs/``, ``Makefile``, ``.devin`` DRS blueprint.

    Skills are bridged into the code assist tool automatically (for Windsurf,
    symlinked into ~/.codeium/windsurf/skills so Cascade loads them immediately).

    Examples:
        {CLI_NAME} domain init cwow-facility
        {CLI_NAME} domain init cwow-facility --code-assist-tool windsurf
        {CLI_NAME} domain init cwow-facility --product-meta ../product-cwow-meta
    """
    import subprocess

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        console.print(f"[dim]Register it first: {CLI_NAME} domain create <DOMAIN> --product <PRODUCT>[/dim]")
        raise typer.Exit(1)

    if code_assist_tool == "auto":
        from agentic_cli.commands.code import detect_code_assist_tool

        code_assist_tool = detect_code_assist_tool()
        console.print(f"[dim]Code assist tool (auto-detected): {code_assist_tool}[/dim]")

    out_dir = _resolve_context_meta_path(domain_name, output)
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    if out_dir.exists() and any(out_dir.iterdir()):
        import sys

        if force:
            _robust_rmtree(out_dir)
            console.print(f"[yellow]Removed existing repo (--force): {out_dir}[/yellow]")
        elif sys.stdin.isatty():
            if not typer.confirm(f"Directory {out_dir} is not empty. Overwrite?", default=False):
                raise typer.Exit(0)
            _robust_rmtree(out_dir)
        else:
            console.print(f"[red]✗ Repo already exists and is not empty: {out_dir}[/red]")
            console.print("[dim]Re-run with --force to overwrite, or delete the directory first.[/dim]")
            raise typer.Exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]Initializing unified context-meta repo for '{domain_name}'...[/cyan]")

    repos = get_domain_repos(domain_name)
    docs = get_domain_docs(domain_name)

    # ── Context: query KG (time-boxed/skippable) + scaffold context files ──
    from agentic_cli.kg.domain_context import scaffold_domain_context_repo

    kg_context: dict = {}
    if no_kg:
        console.print("[dim]Skipping Knowledge Graph query (--no-kg) — using placeholder content.[/dim]")
    else:
        console.print(f"[dim]Querying Knowledge Graph for domain context (timeout {kg_timeout}s)...[/dim]")
        try:
            import concurrent.futures

            from agentic_cli.kg.domain_context import query_domain_kg

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(query_domain_kg, domain_name)
                try:
                    kg_context = fut.result(timeout=kg_timeout) or {}
                except concurrent.futures.TimeoutError:
                    console.print(
                        f"[yellow]⚠ KG query exceeded {kg_timeout}s — continuing with "
                        f"placeholder content.[/yellow]"
                    )
                    kg_context = {}
            if any(kg_context.values()):
                console.print(
                    f"[green]✓ KG domain context retrieved "
                    f"({sum(1 for v in kg_context.values() if v)}/6 aspects)[/green]"
                )
            else:
                console.print("[yellow]⚠ No domain context found in KG — using placeholder content.[/yellow]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[yellow]⚠ KG query failed: {e}[/yellow]")
            kg_context = {}

    try:
        created = scaffold_domain_context_repo(
            output_dir=out_dir, domain=domain_name, domain_data=d,
            kg_context=kg_context, repos=repos, code_assist_tool=code_assist_tool,
        )
        for name, path in created.items():
            console.print(f"  [green]✓[/green] context/{name}")
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ Failed to scaffold context files: {e}[/red]")
        raise typer.Exit(1)

    # ── Skills injection ──────────────────────────────────────────────────
    skills_result = None
    if bootstrap_skills:
        console.print("\n[cyan]Injecting superpowers skills as baseline...[/cyan]")
        try:
            from agentic_cli.kg.domain_skills import bootstrap_domain_skills

            skills_result = bootstrap_domain_skills(
                domain_context_dir=out_dir, domain=domain_name,
                superpowers_url=superpowers_url, use_submodule=False,
                code_assist_tool=code_assist_tool,
            )
            console.print(f"[green]✓ {skills_result['skill_count']} superpowers skills injected[/green]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[yellow]⚠ Skill injection failed: {e}[/yellow]")

    # ── project-context skill ─────────────────────────────────────────────
    try:
        from agentic_cli.commands.code import _generate_project_context_skill
        from agentic_cli.analyzer.detector import ProjectAnalysis

        analysis = ProjectAnalysis()
        analysis.languages = ["markdown"]
        analysis.frameworks = ["domain-context"]
        _generate_project_context_skill(
            project_path=out_dir, analysis=analysis, code_assist_tool=code_assist_tool,
            domain=domain_name, product=d.get("product"),
        )
        console.print("[green]✓ project-context skill generated[/green]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]⚠ project-context skill generation failed: {e}[/yellow]")

    # ── Meta: governance, personas, submodules, Devin blueprint ───────────
    console.print("\n[cyan]Scaffolding meta layer (governance, personas, submodules)...[/cyan]")
    try:
        from agentic_cli.meta_repo import scaffold_domain_meta_repo
        from agentic_cli.meta_repo.git_utils import detect_git_host
        from agentic_cli.persona_catalog import resolve_personas

        repos_config = [
            {
                "slug": r["repo_slug"], "clone_url": r["clone_url"],
                "description": r.get("description", ""), "languages": r.get("languages", []),
                "frameworks": r.get("frameworks", []),
                "host": detect_git_host(r.get("clone_url", "")), "branch": r.get("branch"),
            }
            for r in repos
        ]

        product = d.get("product", "")
        product_meta_path = None
        if product_meta_url and Path(product_meta_url).exists():
            product_meta_path = Path(product_meta_url)
        elif product:
            slug = product.lower()
            product_meta_path = _get_code_workspace() / slug / f"product-{slug}-meta"

        personas = resolve_personas(product_meta_path)
        persona_context = gather_domain_context(d, repos, docs)

        meta_created = scaffold_domain_meta_repo(
            output_dir=out_dir.parent, domain=domain_name, product=product,
            description=d.get("description", ""), owner=d.get("owner", ""),
            product_meta_url=product_meta_url, repos=repos_config,
            git_init=git_init, code_assist_tool=code_assist_tool,
            personas=personas, persona_context=persona_context,
            clone_repos=clone_repos, repo_name=out_dir.name, allow_existing=True,
        )
        for name, path in meta_created.items():
            if name != "root":
                console.print(f"  [green]✓[/green] meta/{name}")
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ Failed to scaffold meta layer: {e}[/red]")
        raise typer.Exit(1)

    # ── Bridge skills into the code assist tool ───────────────────────────
    if code_assist_tool == "windsurf":
        console.print("\n[cyan]Registering skills with Windsurf/Cascade...[/cyan]")
        try:
            from agentic_cli.kg.domain_skills import (
                install_skills_to_windsurf, get_windsurf_skills_root,
            )

            bridged = install_skills_to_windsurf(out_dir / ".skills", domain_name)
            console.print(
                f"[green]✓ {len(bridged)} skills registered[/green] "
                f"[dim]in {get_windsurf_skills_root()}[/dim]"
            )
            console.print("[dim]Reload the Cascade window to load them.[/dim]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[yellow]⚠ Windsurf skill registration failed: {e}[/yellow]")

    # ── Git remote ────────────────────────────────────────────────────────
    # The meta scaffold's _init_git_repo already made the initial commit,
    # which includes the context files + skills (written BEFORE the meta
    # scaffold) AND the submodule gitlinks (product-meta + linked repos).
    # We must NOT run `git add .` here: with submodules registered but not
    # cloned (clone_repos=False), `git add .` sees the empty submodule paths
    # as deletions and would clobber the gitlinks — dropping every submodule.
    if git_init and git_remote:
        try:
            subprocess.run(
                ["git", "remote", "add", "origin", git_remote],
                cwd=str(out_dir), capture_output=True, check=True,
            )
            console.print(f"[green]✓ Git remote set:[/green] {git_remote}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            console.print(f"[yellow]⚠ Git remote add failed: {stderr}[/yellow]")

    skills_count = skills_result["skill_count"] if skills_result else 0
    console.print()
    console.print(Panel(
        f"[bold]Domain:[/bold] {d.get('domain', domain_name)} ({d.get('product', '')})\n"
        f"[bold]Location:[/bold] {out_dir}\n"
        f"[bold]KG Context:[/bold] {'Yes' if any((kg_context or {}).values()) else 'Placeholder'}\n"
        f"[bold]Skills:[/bold] {skills_count} injected"
        + (f"\n[bold]Remote:[/bold] {git_remote}" if git_remote else ""),
        title=f"Domain Context-Meta Repo — {domain_name}", border_style="green",
    ))

    record_activity(
        command="domain", subcommand="init",
        args={"domain": domain_name, "output": str(out_dir),
              "skills_injected": skills_count, "tool": code_assist_tool},
    )


@domain_app.command("init-context", hidden=True, deprecated=True)
def init_context(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output directory for domain context repo")] = None,
    git_init: Annotated[bool, typer.Option("--git-init/--no-git-init", help="Initialize as a git repo")] = True,
    git_remote: Annotated[str, typer.Option("--git-remote", help="Git remote URL to set as origin")] = None,
    bootstrap_skills: Annotated[bool, typer.Option("--bootstrap-skills/--no-bootstrap-skills", help="Inject superpowers skills as baseline")] = True,
    superpowers_url: Annotated[str, typer.Option("--superpowers-url", help="Git URL for superpowers skills repo")] = "https://github.com/venkatchinta/superpowers.git",
    code_assist_tool: Annotated[str, typer.Option("--code-assist-tool", help="Code assist tool (auto, windsurf, cursor, devin, or generic). 'auto' detects the IDE. Determines where skills are installed and whether they're bridged into the tool's skill dir.")] = "auto",
    no_kg: Annotated[bool, typer.Option("--no-kg", help="Skip the Knowledge Graph query (fastest; uses placeholder content)")] = False,
    kg_timeout: Annotated[int, typer.Option("--kg-timeout", help="Max seconds to wait for the KG query before falling back to placeholder content")] = 20,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite an existing context repo without prompting (required in non-interactive contexts such as the dashboard)")] = False,
) -> None:
    """
    Initialize a central domain context repository.

    Creates a domain-context repo structure with shared business context
    from the Knowledge Graph, shared skills, and metadata. This repo is
    referenced by individual repos via git submodules.

    The KG provider is determined dynamically from KGConfig (supports Neo4j, LightRAG, etc.).

    By default, the context repo is created in the configured code workspace
    under a domain folder: <workspace>/<domain>/<domain>-domain-context.
    All linked repos for the domain can be cloned into the same domain folder.
    Use --output to specify a custom location.

    By default, injects superpowers skills as a baseline. Use --no-bootstrap-skills
    to skip skill injection.

    The --code-assist-tool determines where skills are installed:
    - auto: Detect the active IDE (default) and use its convention.
    - windsurf: Skills stored as .skills/*/SKILL.md AND symlinked into the
      per-user dir Cascade scans (~/.codeium/windsurf/skills/<domain>__*) so
      they load immediately. (Skills are NOT .windsurf/workflows — that is the
      slash-command feature and is never loaded as a skill.)
    - cursor: Skills installed under .cursorrules (Cursor rules format)
    - devin: Skills installed as .devin/skills/*/SKILL.md
    - generic: Skills installed as .skills/*/SKILL.md (portable format)

    Examples:
        {CLI_NAME} domain init-context cwow-facility
        {CLI_NAME} domain init-context cwow-facility --code-assist-tool windsurf
        {CLI_NAME} domain init-context cwow-facility --output ./facility-domain-context
        {CLI_NAME} domain init-context cwow-facility --git-remote https://github.com/company/facility-domain-context.git
        {CLI_NAME} domain init-context cwow-facility --no-bootstrap-skills
    """
    import subprocess

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        console.print(f"[dim]Register it first: {CLI_NAME} domain create <DOMAIN> --product <PRODUCT>[/dim]")
        raise typer.Exit(1)

    # Resolve 'auto' to the active IDE so skills land where the tool loads them.
    if code_assist_tool == "auto":
        from agentic_cli.commands.code import detect_code_assist_tool

        code_assist_tool = detect_code_assist_tool()
        console.print(f"[dim]Code assist tool (auto-detected): {code_assist_tool}[/dim]")

    # Determine output directory
    if output:
        out_dir = Path(output).resolve()
    else:
        # Use code workspace as default location
        workspace = _get_code_workspace()
        # Create domain folder structure: workspace/domain-name/domain-context
        domain_folder = workspace / domain_name
        out_dir = domain_folder / f"{domain_name}-domain-context"
        # Ensure workspace and domain folder exist
        if not workspace.exists():
            console.print(f"[yellow]Workspace directory does not exist: {workspace}[/yellow]")
            console.print(f"[dim]Creating workspace directory...[/dim]")
            try:
                workspace.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓[/green] Created: {workspace}")
            except Exception as e:
                console.print(f"[red]✗ Failed to create workspace: {e}[/red]")
                console.print(f"[dim]Falling back to current directory[/dim]")
                out_dir = Path.cwd() / domain_name / f"{domain_name}-domain-context"
        else:
            # Ensure domain folder exists
            if not domain_folder.exists():
                try:
                    domain_folder.mkdir(parents=True, exist_ok=True)
                    console.print(f"[green]✓[/green] Created domain folder: {domain_folder}")
                except Exception as e:
                    console.print(f"[red]✗ Failed to create domain folder: {e}[/red]")
                    console.print(f"[dim]Falling back to workspace root[/dim]")
                    out_dir = workspace / f"{domain_name}-domain-context"

    if out_dir.exists() and any(out_dir.iterdir()):
        import sys

        if force:
            _robust_rmtree(out_dir)
            console.print(f"[yellow]Removed existing context repo (--force): {out_dir}[/yellow]")
        elif sys.stdin.isatty():
            overwrite = typer.confirm(f"Directory {out_dir} is not empty. Overwrite?", default=False)
            if not overwrite:
                raise typer.Exit(0)
            _robust_rmtree(out_dir)
        else:
            # Non-interactive (e.g. dashboard): never block on a prompt.
            console.print(f"[red]✗ Context repo already exists and is not empty: {out_dir}[/red]")
            console.print("[dim]Re-run with --force to overwrite, or delete the directory first.[/dim]")
            raise typer.Exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]Initializing domain context repo for '{domain_name}'...[/cyan]")

    # Initialize git repo FIRST (before skill injection, needed for git submodule)
    if git_init:
        try:
            subprocess.run(["git", "init"], cwd=str(out_dir), capture_output=True, check=True)
            console.print("[dim]Git repo initialized[/dim]")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            console.print(f"[yellow]⚠ Git init failed: {stderr}[/yellow]")
            console.print("[yellow]⚠ Skill injection may fail without git initialization[/yellow]")
            git_init = False

    # Gather domain data
    repos = get_domain_repos(domain_name)
    docs = get_domain_docs(domain_name)

    from agentic_cli.kg.domain_context import scaffold_domain_context_repo

    # Query KG for domain business context (skippable + time-boxed so a slow or
    # unreachable KG provider never stalls onboarding).
    kg_context: dict = {}
    if no_kg:
        console.print("[dim]Skipping Knowledge Graph query (--no-kg) — using placeholder content.[/dim]")
    else:
        console.print(
            f"[dim]Querying Knowledge Graph for domain context (timeout {kg_timeout}s)...[/dim]"
        )
        try:
            import concurrent.futures

            from agentic_cli.kg.domain_context import query_domain_kg

            # query_domain_kg automatically determines provider from KGConfig.
            # Run it off-thread so we can enforce a hard wall-clock timeout.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(query_domain_kg, domain_name)
                try:
                    kg_context = fut.result(timeout=kg_timeout) or {}
                except concurrent.futures.TimeoutError:
                    console.print(
                        f"[yellow]⚠ KG query exceeded {kg_timeout}s — continuing with "
                        f"placeholder content (raise with --kg-timeout, or skip with --no-kg).[/yellow]"
                    )
                    kg_context = {}

            has_kg = any(kg_context.values())
            if has_kg:
                console.print(
                    f"[green]✓ KG domain context retrieved "
                    f"({sum(1 for v in kg_context.values() if v)}/6 aspects)[/green]"
                )
            else:
                try:
                    from agentic_cli.kg.config import KGConfig
                    provider = KGConfig.load().provider
                    console.print(f"[yellow]⚠ No domain context found in KG ({provider} may not be running or domain not ingested)[/yellow]")
                except Exception:
                    console.print("[yellow]⚠ No domain context found in KG (provider may not be running or domain not ingested)[/yellow]")
                console.print("[dim]The repo structure will be created with placeholder content.[/dim]")

        except Exception as e:
            console.print(f"[yellow]⚠ KG query failed: {e}[/yellow]")
            console.print("[dim]Creating repo structure with placeholder content.[/dim]")
            kg_context = {}

    # Scaffold the repo
    try:
        created = scaffold_domain_context_repo(
            output_dir=out_dir,
            domain=domain_name,
            domain_data=d,
            kg_context=kg_context,
            repos=repos,
            code_assist_tool=code_assist_tool,
        )

        for name, path in created.items():
            console.print(f"  [green]✓[/green] {name}: {path.relative_to(out_dir)}")

    except Exception as e:
        console.print(f"[red]✗ Failed to scaffold domain context repo: {e}[/red]")
        raise typer.Exit(1)

    # Inject superpowers skills
    skills_result = None
    if bootstrap_skills:
        console.print("\n[cyan]Injecting superpowers skills as baseline...[/cyan]")
        try:
            from agentic_cli.kg.domain_skills import bootstrap_domain_skills

            skills_result = bootstrap_domain_skills(
                domain_context_dir=out_dir,
                domain=domain_name,
                superpowers_url=superpowers_url,
                use_submodule=git_init,  # submodule needs git
                code_assist_tool=code_assist_tool,
            )

            for sname in skills_result["injected_skills"]:
                console.print(f"  [green]✓[/green] {sname}")

            console.print(
                f"[green]✓ {skills_result['skill_count']} superpowers skills injected[/green]"
            )
            console.print(f"  Manifest: {skills_result['manifest_path'].relative_to(out_dir)}")
            console.print(f"  Readme: {skills_result['manifest_md_path'].relative_to(out_dir)}")

        except Exception as e:
            console.print(f"[yellow]⚠ Skill injection failed: {e}[/yellow]")
            console.print("[dim]Domain context repo created without superpowers skills.[/dim]")

    # Generate project-context skill (for consistency with code onboard)
    console.print("\n[cyan]Generating project-context skill...[/cyan]")
    try:
        from agentic_cli.commands.code import _generate_project_context_skill
        from agentic_cli.analyzer.detector import ProjectAnalysis

        # Create minimal analysis for domain context repo
        analysis = ProjectAnalysis()
        analysis.languages = ["markdown"]
        analysis.frameworks = ["domain-context"]
        analysis.project_files = {
            "kg-context.md": True,
            "domain-metadata.json": True,
            "architecture.md": True,
        }

        _generate_project_context_skill(
            project_path=out_dir,
            analysis=analysis,
            code_assist_tool=code_assist_tool,
            domain=domain_name,
            product=d.get("product"),
        )
        console.print("[green]✓ project-context skill generated[/green]")

    except Exception as e:
        console.print(f"[yellow]⚠ project-context skill generation failed: {e}[/yellow]")
        console.print("[dim]Domain context repo created without project-context skill.[/dim]")

    # Bridge all repo-local skills into the per-user dir Cascade scans, so
    # Windsurf loads them immediately (covers superpowers + project-context).
    if code_assist_tool == "windsurf":
        console.print("\n[cyan]Registering skills with Windsurf/Cascade...[/cyan]")
        try:
            from agentic_cli.kg.domain_skills import (
                install_skills_to_windsurf, get_windsurf_skills_root,
            )

            bridged = install_skills_to_windsurf(out_dir / ".skills", domain_name)
            for b in bridged:
                console.print(f"  [green]✓[/green] {b['global_name']} [dim]({b['mode']})[/dim]")
            console.print(
                f"[green]✓ {len(bridged)} skills registered[/green] "
                f"[dim]in {get_windsurf_skills_root()}[/dim]"
            )
            console.print("[dim]Reload the Cascade window (or restart Windsurf) to load them.[/dim]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[yellow]⚠ Windsurf skill registration failed: {e}[/yellow]")

    # Commit files to git (repo already initialized earlier)
    if git_init:
        try:
            subprocess.run(["git", "add", "."], cwd=str(out_dir), capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Initial domain context for {domain_name}"],
                cwd=str(out_dir), capture_output=True, check=True,
            )
            console.print("[green]✓ Git repo committed[/green]")

            if git_remote:
                subprocess.run(
                    ["git", "remote", "add", "origin", git_remote],
                    cwd=str(out_dir), capture_output=True, check=True,
                )
                console.print(f"[green]✓ Git remote set:[/green] {git_remote}")
                console.print(f"[dim]Push with: cd {out_dir} && git push -u origin main[/dim]")

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            console.print(f"[yellow]⚠ Git commit failed: {stderr}[/yellow]")

    # Summary
    domain_label = d.get("domain", domain_name)
    product = d.get("product", "")
    skills_count = skills_result["skill_count"] if skills_result else 0

    console.print()
    console.print(Panel(
        f"[bold]Domain:[/bold] {domain_label} ({product})\n"
        f"[bold]Location:[/bold] {out_dir}\n"
        f"[bold]Files:[/bold] {len(created)}\n"
        f"[bold]KG Context:[/bold] {'Yes' if any((kg_context or {}).values()) else 'Placeholder'}\n"
        f"[bold]Skills:[/bold] {skills_count} superpowers skills injected\n"
        f"[bold]Git Initialized:[/bold] {'Yes' if git_init else 'No'}"
        + (f"\n[bold]Remote:[/bold] {git_remote}" if git_remote else ""),
        title=f"Domain Context Repo — {domain_name}",
        border_style="green",
    ))

    # Next steps
    console.print(f"\n[dim]Next steps:[/dim]")
    if git_remote:
        console.print(f"[dim]  1. Push: cd {out_dir} && git push -u origin main[/dim]")
        console.print(f"[dim]  2. Link to repos: {CLI_NAME} code onboard --path <repo> --domain {domain_name} --domain-context-repo {git_remote}[/dim]")
    else:
        console.print(f"[dim]  1. Create remote repo and push[/dim]")
        console.print(f"[dim]  2. Link to repos: {CLI_NAME} code onboard --path <repo> --domain {domain_name} --domain-context-repo <git-url>[/dim]")

    record_activity(
        command="domain", subcommand="init-context",
        args={
            "domain": domain_name,
            "output": str(out_dir),
            "git_init": git_init,
            "git_remote": git_remote,
            "kg_aspects_found": sum(1 for v in (kg_context or {}).values() if v),
            "skills_injected": skills_result["skill_count"] if skills_result else 0,
        },
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} domain reinstall-skills
# ---------------------------------------------------------------------------

@domain_app.command("reinstall-skills")
def reinstall_skills(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-apoc)")],
    code_assist_tool: Annotated[str, typer.Option("--code-assist-tool", help="Code assist tool (auto, windsurf, cursor, devin, generic). 'auto' detects the IDE.")] = "auto",
    context_repo: Annotated[str, typer.Option("--context-repo", help="Path to the domain-context repo (defaults to the workspace location)")] = None,
    copy: Annotated[bool, typer.Option("--copy", help="Copy skill folders instead of symlinking (robust, but updates need re-running this)")] = False,
) -> None:
    """Re-register an already-injected domain's skills with the code assist tool.

    Backfills existing domains (whose skills were injected before the install
    step existed) without re-cloning superpowers or re-scaffolding the repo.
    For Windsurf/Cascade this symlinks the repo's ``.skills`` folders into
    ``~/.codeium/windsurf/skills/<domain>__*`` so Cascade discovers them.

    Examples:
        {CLI_NAME} domain reinstall-skills cwow-apoc
        {CLI_NAME} domain reinstall-skills cwow-apoc --code-assist-tool windsurf
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    if code_assist_tool == "auto":
        from agentic_cli.commands.code import detect_code_assist_tool

        code_assist_tool = detect_code_assist_tool()
        console.print(f"[dim]Code assist tool (auto-detected): {code_assist_tool}[/dim]")

    # Resolve the unified context-meta repo path (falls back to legacy
    # split-context repo for domains created before the cutover).
    if context_repo:
        ctx_dir = Path(context_repo).resolve()
    else:
        ctx_dir = _resolve_context_meta_path(domain_name)
        if not (ctx_dir / ".skills").is_dir():
            legacy = _get_code_workspace() / domain_name / f"{domain_name}-domain-context"
            if (legacy / ".skills").is_dir():
                ctx_dir = legacy

    skills_dir = ctx_dir / ".skills"
    if not skills_dir.is_dir():
        console.print(f"[red]✗ No .skills found at {skills_dir}[/red]")
        console.print(
            f"[dim]Create the repo first: {CLI_NAME} domain init {domain_name} "
            f"--code-assist-tool {code_assist_tool}[/dim]"
        )
        raise typer.Exit(1)

    if code_assist_tool != "windsurf":
        console.print(
            f"[yellow]Skills for '{code_assist_tool}' are loaded from the repo directly "
            f"({skills_dir}); no global registration needed.[/yellow]"
        )
        raise typer.Exit(0)

    from agentic_cli.kg.domain_skills import (
        install_skills_to_windsurf, get_windsurf_skills_root,
    )

    console.print(f"[cyan]Registering '{domain_name}' skills with Windsurf/Cascade...[/cyan]")
    bridged = install_skills_to_windsurf(skills_dir, domain_name, use_symlink=not copy)
    if not bridged:
        console.print(f"[yellow]No skills (SKILL.md folders) found under {skills_dir}.[/yellow]")
        raise typer.Exit(0)

    for b in bridged:
        console.print(f"  [green]✓[/green] {b['global_name']} [dim]({b['mode']})[/dim]")
    console.print(
        f"\n[bold green]✓[/bold green] Registered [bold]{len(bridged)}[/bold] skills "
        f"[dim]in {get_windsurf_skills_root()}[/dim]"
    )
    console.print("[dim]Reload the Cascade window (or restart Windsurf) to load them.[/dim]")

    record_activity(
        command="domain", subcommand="reinstall-skills",
        args={"domain": domain_name, "tool": code_assist_tool, "count": len(bridged)},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} domain init-meta
# ---------------------------------------------------------------------------

def _robust_rmtree(path: Path, attempts: int = 5) -> None:
    """Remove a directory tree, retrying on transient ``ENOTEMPTY`` races.

    On macOS, Finder/Spotlight can recreate ``.DS_Store`` files mid-deletion,
    causing ``shutil.rmtree`` to fail with ``[Errno 66] Directory not empty``.
    Retrying with ``ignore_errors`` clears these transient leftovers.
    """
    import shutil
    import time

    for i in range(attempts):
        shutil.rmtree(path, ignore_errors=(i < attempts - 1))
        if not path.exists():
            return
        time.sleep(0.1)


@domain_app.command("init-meta", hidden=True, deprecated=True)
def init_meta(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for meta-repo (default: workspace/domain-name)"),
    ] = None,
    context_repo_url: Annotated[
        str,
        typer.Option("--context-repo", help="Git URL of domain-context-repo to add as submodule"),
    ] = None,
    product_meta_url: Annotated[
        str,
        typer.Option("--product-meta", help="Git URL/path of the product meta-repo to reference as submodule (outer-loop shared tier)"),
    ] = None,
    git_init: Annotated[
        bool,
        typer.Option("--git-init/--no-git-init", help="Initialize as git repo with submodules"),
    ] = True,
    clone_repos: Annotated[
        bool,
        typer.Option(
            "--clone-repos/--no-clone-repos",
            help="Clone submodule working trees now (shallow+parallel). By default "
            "submodules are only registered and fetched lazily via `make init`.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force", "-f",
            help="Overwrite an existing meta-repo without prompting (required in "
            "non-interactive contexts such as the dashboard).",
        ),
    ] = False,
) -> None:
    """
    Initialize a domain meta-repo following meta-repo standards.

    Creates a new git repository with:
    - .platform/config/ — Domain configuration (domain.yaml, repos.yaml, governance.yaml, skills.yaml)
    - .agents/ — Domain-specific agents and skills
    - repos/ — Git submodules for linked domain repositories
    - docs/ — Documentation (README, ONBOARDING, GOVERNANCE, ARCHITECTURE)
    - Makefile — Automation targets (init, update, validate)

    The domain must be registered first via `{CLI_NAME} domain create`.

    By default, the meta-repo is created in the configured code workspace
    under a domain folder: <workspace>/<domain>/domain-<domain>-meta.
    Use --output to specify a custom location.

    Examples:
        {CLI_NAME} domain init-meta cwow-facility
        {CLI_NAME} domain init-meta cwow-facility --context-repo https://github.com/company/facility-domain-context.git
        {CLI_NAME} domain init-meta cwow-facility --output ./facility-meta
    """.format(CLI_NAME=CLI_NAME)

    from agentic_cli.meta_repo import scaffold_domain_meta_repo

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        console.print(f"[dim]Register it first: {CLI_NAME} domain create <DOMAIN> --product <PRODUCT>[/dim]")
        raise typer.Exit(1)

    # Determine output directory
    if output:
        out_dir = output.resolve()
        meta_repo_path = out_dir
    else:
        # Use code workspace as default location
        workspace = _get_code_workspace()
        domain_folder = workspace / domain_name
        meta_repo_path = domain_folder / f"domain-{domain_name}-meta"
        out_dir = domain_folder

        # Ensure workspace and domain folder exist
        if not workspace.exists():
            console.print(f"[yellow]Workspace directory does not exist: {workspace}[/yellow]")
            console.print(f"[dim]Creating workspace directory...[/dim]")
            try:
                workspace.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓[/green] Created: {workspace}")
            except Exception as e:
                console.print(f"[red]✗ Failed to create workspace: {e}[/red]")
                raise typer.Exit(1)

        if not domain_folder.exists():
            try:
                domain_folder.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓[/green] Created domain folder: {domain_folder}")
            except Exception as e:
                console.print(f"[red]✗ Failed to create domain folder: {e}[/red]")
                raise typer.Exit(1)

    if meta_repo_path.exists() and any(meta_repo_path.iterdir()):
        import sys

        if force:
            _robust_rmtree(meta_repo_path)
            console.print(
                f"[yellow]Removed existing meta-repo (--force): {meta_repo_path}[/yellow]"
            )
        elif sys.stdin.isatty():
            overwrite = typer.confirm(
                f"Directory {meta_repo_path} is not empty. Overwrite?", default=False
            )
            if not overwrite:
                raise typer.Exit(0)
            _robust_rmtree(meta_repo_path)
        else:
            # Non-interactive (e.g. dashboard): never block on a prompt.
            console.print(
                f"[red]✗ Meta-repo already exists and is not empty: {meta_repo_path}[/red]"
            )
            console.print(
                "[dim]Re-run with --force to overwrite, or delete the directory first.[/dim]"
            )
            raise typer.Exit(1)

    console.print(f"[cyan]Initializing domain meta-repo for '{domain_name}'...[/cyan]")

    # Get linked repos for the domain. Tag each with its git host
    # (bitbucket/gitlab/github) so repos.yaml records provenance; the
    # submodule branch is auto-detected per host at scaffold time.
    from agentic_cli.meta_repo.git_utils import detect_git_host

    repos = get_domain_repos(domain_name)
    repos_config = [
        {
            "slug": r["repo_slug"],
            "clone_url": r["clone_url"],
            "description": r.get("description", ""),
            "languages": r.get("languages", []),
            "frameworks": r.get("frameworks", []),
            "host": detect_git_host(r.get("clone_url", "")),
            "branch": r.get("branch"),
        }
        for r in repos
    ]

    # Resolve the effective persona catalog (built-in defaults + product-specific
    # personas from the product meta-repo) and build the rendering context so the
    # scaffolder can generate persona skills into .agents/skills/personas/.
    from agentic_cli.persona_catalog import resolve_personas

    product = d.get("product", "")
    product_meta_path = None
    if product_meta_url and Path(product_meta_url).exists():
        product_meta_path = Path(product_meta_url)
    elif product:
        slug = product.lower()
        product_meta_path = _get_code_workspace() / slug / f"product-{slug}-meta"

    personas = resolve_personas(product_meta_path)
    docs = get_domain_docs(domain_name)
    persona_context = gather_domain_context(d, repos, docs)

    # Scaffold the meta-repo
    try:
        created = scaffold_domain_meta_repo(
            output_dir=out_dir,
            domain=domain_name,
            product=product,
            description=d.get("description", ""),
            owner=d.get("owner", ""),
            context_repo_url=context_repo_url,
            product_meta_url=product_meta_url,
            repos=repos_config,
            git_init=git_init,
            personas=personas,
            persona_context=persona_context,
            clone_repos=clone_repos,
        )

        console.print(f"[green]✓ Domain meta-repo created:[/green] {meta_repo_path}")
        console.print()
        console.print("[cyan]Created directories:[/cyan]")
        for name, path in created.items():
            if name != "root":
                console.print(f"  [green]✓[/green] {path.relative_to(meta_repo_path)}")

        console.print()
        console.print("[cyan]Next steps:[/cyan]")
        console.print(f"  1. cd {meta_repo_path}")
        console.print(f"  2. make init          # Initialize submodules")
        console.print(f"  3. make validate      # Validate repo state")
        console.print(
            f"  4. {CLI_NAME} domain build-snapshot {domain_name}   "
            f"# Build the Devin snapshot for consistent sessions"
        )
        console.print()
        if created.get("devin_blueprint"):
            console.print(
                f"[dim]Devin blueprint: {created['devin_blueprint'].relative_to(meta_repo_path)} "
                f"(edit, then build a snapshot so every {domain_name} session is governance-consistent)[/dim]"
            )
        console.print()
        console.print("[dim]Documentation:[/dim]")
        console.print(f"  - README.md: {meta_repo_path / 'docs' / 'README.md'}")
        console.print(f"  - ONBOARDING.md: {meta_repo_path / 'docs' / 'ONBOARDING.md'}")
        console.print(f"  - GOVERNANCE.md: {meta_repo_path / 'docs' / 'GOVERNANCE.md'}")

    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except RuntimeError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to scaffold domain meta-repo: {e}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# {CLI_NAME} domain build-snapshot / gen-blueprint (Devin DRS)
# ---------------------------------------------------------------------------

def _resolve_domain_meta_path(domain_name: str, meta: Optional[str] = None) -> Path:
    """Resolve a domain's meta-repo path.

    Post-cutover this is the unified context-meta repo
    (``<workspace>/<domain>/<domain>-context-meta``), which now holds the
    ``.devin`` DRS blueprint, ``.platform`` governance, and ``repos/`` submodules.
    """
    if meta:
        return Path(meta).resolve()
    return _resolve_context_meta_path(domain_name)


@domain_app.command("gen-blueprint")
def gen_blueprint(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    meta: Annotated[str, typer.Option("--meta", help="Path to the domain meta-repo (defaults to the workspace location)")] = None,
) -> None:
    """(Re)generate the Devin DRS blueprint (.devin/environment.yaml + setup.sh).

    The blueprint is normally written by `domain init-meta`; use this to refresh
    it (e.g. after MCP servers change) without re-scaffolding the meta-repo.
    """
    from agentic_cli.devin.blueprint import load_workspace_mcp_servers, write_domain_blueprint

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    meta_repo_path = _resolve_domain_meta_path(domain_name, meta)
    if not meta_repo_path.exists():
        console.print(f"[red]✗ Meta-repo not found: {meta_repo_path}[/red]")
        console.print(f"[dim]Create it first: {CLI_NAME} domain init-meta {domain_name}[/dim]")
        raise typer.Exit(1)

    bp = write_domain_blueprint(
        meta_repo_path,
        domain_name,
        d.get("product", ""),
        mcp_servers=load_workspace_mcp_servers(),
    )
    console.print(f"[green]✓[/green] Blueprint written:")
    for name, path in bp.items():
        console.print(f"  [green]✓[/green] {path.relative_to(meta_repo_path)}")
    console.print(
        f"\n[dim]Next: {CLI_NAME} domain build-snapshot {domain_name}[/dim]"
    )


def _git_remote_slug(repo_path: Path) -> Optional[str]:
    """Best-effort `owner/repo` slug from a repo's `origin` remote URL."""
    import re
    import subprocess

    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(repo_path), capture_output=True, text=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return None
    if not url:
        return None
    # git@host:owner/repo.git  |  https://host/owner/repo.git
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


@domain_app.command("build-snapshot")
def build_snapshot(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    meta: Annotated[str, typer.Option("--meta", help="Path to the domain meta-repo (defaults to the workspace location)")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Scope the blueprint to a repo (owner/repo); defaults to the meta-repo's origin remote")] = None,
    blueprint_id: Annotated[str, typer.Option("--blueprint-id", help="Update an existing blueprint instead of creating a new one")] = None,
    snapshot_id: Annotated[str, typer.Option("--snapshot-id", help="Register a pre-built snapshot id and skip the DRS build entirely")] = None,
    env_file: Annotated[str, typer.Option("--env-file", help="Override the environment.yaml path (defaults to the meta-repo's .devin/environment.yaml)")] = None,
    no_build: Annotated[bool, typer.Option("--no-build", help="Create/update the blueprint but do not trigger a build")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print the DRS commands without running them")] = False,
) -> None:
    """Build (or register) the per-domain Devin snapshot via DRS and persist its id.

    Blueprint-now, build-later: `domain init-meta` already committed the DRS
    blueprint (`.devin/environment.yaml`). This:

      1. `devin cloud drs blueprint-create --repo <owner/repo> --from-file <yaml>`
         (or `blueprint-write --blueprint-id <id>` when --blueprint-id is given)
      2. `devin cloud drs build` (builds all current blueprints and waits)

    then stores the resulting snapshot id per-domain so
    `{CLI_NAME} devin sessions create --domain {domain_name}` reuses the SAME
    environment for every session.

    If you built it elsewhere (e.g. the Devin UI), skip DRS entirely and just
    register the id: `--snapshot-id <id>`.
    """
    import shutil
    import subprocess

    from agentic_cli.devin.blueprint import (
        BLUEPRINT_DIR,
        ENVIRONMENT_FILE,
        blueprint_create_command,
        blueprint_write_command,
        build_command,
        parse_blueprint_id,
        parse_snapshot_id,
    )
    from agentic_cli.devin.config import DevinConfig

    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    def _persist(*, snapshot: str = None, blueprint: str = None,
                 meta_path: Path = None) -> None:
        from agentic_cli.devin.snapshots import capture_provenance

        cfg = DevinConfig.load()
        kwargs: dict = {}
        if snapshot:
            kwargs["snapshot_id"] = snapshot
        if blueprint:
            kwargs["blueprint_id"] = blueprint
        if meta_path is not None:
            kwargs["meta_repo_path"] = str(meta_path.resolve())
            # Record the meta-repo commit + blueprint hash the snapshot was
            # built from, so `devin snapshots verify` can detect drift.
            if snapshot:
                kwargs.update(capture_provenance(meta_path))
        if kwargs:
            cfg.set_domain(domain_name, **{k: v for k, v in kwargs.items() if v is not None})
        cfg.save()
        if snapshot:
            console.print(f"[bold green]✓[/bold green] Stored snapshot for [cyan]{domain_name}[/cyan]: {snapshot}")
            console.print(
                f"[dim]Sessions now reuse it: {CLI_NAME} devin sessions create "
                f"--domain {domain_name} --prompt \"...\"[/dim]"
            )
            console.print(f"[dim]List/verify: {CLI_NAME} devin snapshots list · {CLI_NAME} devin snapshots verify {domain_name}[/dim]")
        if blueprint:
            console.print(f"[dim]Blueprint id: {blueprint}[/dim]")

    # Manual path: register an already-built snapshot id (no DRS needed).
    if snapshot_id:
        mp = _resolve_domain_meta_path(domain_name, meta)
        _persist(snapshot=snapshot_id, meta_path=mp if mp.exists() else None)
        return

    meta_repo_path = _resolve_domain_meta_path(domain_name, meta)
    blueprint_path = Path(env_file).resolve() if env_file else meta_repo_path / BLUEPRINT_DIR / ENVIRONMENT_FILE
    if not blueprint_path.exists():
        console.print(f"[red]✗ Blueprint not found: {blueprint_path}[/red]")
        console.print(
            f"[dim]Generate it first: {CLI_NAME} domain gen-blueprint {domain_name} "
            f"(or re-run {CLI_NAME} domain init-meta {domain_name})[/dim]"
        )
        raise typer.Exit(1)

    repo_slug = repo or _git_remote_slug(meta_repo_path)

    # Step 1: create or update the blueprint from the environment.yaml.
    if blueprint_id:
        bp_cmd = blueprint_write_command(blueprint_id, blueprint_path)
    else:
        bp_cmd = blueprint_create_command(blueprint_path, repo_slug)
    build_cmd = build_command()

    if dry_run:
        console.print("[bold]DRS commands (dry-run):[/bold]")
        console.print(f"  1. {' '.join(bp_cmd)}")
        if not no_build:
            console.print(f"  2. {' '.join(build_cmd)}")
        console.print(f"[dim]Blueprint file: {blueprint_path}[/dim]")
        if not repo_slug and not blueprint_id:
            console.print("[yellow]⚠ No --repo and no origin remote — blueprint will be org-wide.[/yellow]")
        return

    if shutil.which("devin") is None:
        console.print("[red]✗ 'devin' CLI not found on PATH.[/red]")
        console.print(
            "[dim]Install + authenticate the Devin CLI (devin auth login), or build in "
            f"the UI and register: {CLI_NAME} domain build-snapshot {domain_name} --snapshot-id <id>[/dim]"
        )
        raise typer.Exit(1)

    def _run(cmd: list[str]) -> tuple[int, str]:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        proc = subprocess.run(cmd, cwd=str(meta_repo_path), capture_output=True, text=True)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.stdout:
            console.print(proc.stdout.strip())
        if proc.returncode != 0 and proc.stderr:
            console.print(f"[dim]{proc.stderr.strip()[:500]}[/dim]")
        return proc.returncode, out

    console.print(f"[cyan]Registering blueprint for '{domain_name}'...[/cyan]")
    rc, out = _run(bp_cmd)
    if rc != 0:
        console.print(f"[red]✗ blueprint step failed (exit {rc}).[/red]")
        raise typer.Exit(1)
    bp_id = blueprint_id or parse_blueprint_id(out)

    if no_build:
        console.print("[green]✓[/green] Blueprint registered (build skipped via --no-build).")
        _persist(blueprint=bp_id, meta_path=meta_repo_path)
        return

    console.print(f"[cyan]Building Devin environment snapshot...[/cyan]")
    rc, out = _run(build_cmd)
    if rc != 0:
        console.print(f"[red]✗ DRS build failed (exit {rc}).[/red]")
        raise typer.Exit(1)

    sid = parse_snapshot_id(out)
    if not sid:
        console.print(
            "[yellow]⚠ Build succeeded but no snapshot id was detected in the output.[/yellow]"
        )
        console.print(
            f"[dim]Register it manually once you have it: {CLI_NAME} domain build-snapshot "
            f"{domain_name} --snapshot-id <id>[/dim]"
        )
        _persist(blueprint=bp_id, meta_path=meta_repo_path)
        raise typer.Exit(1)

    _persist(snapshot=sid, blueprint=bp_id, meta_path=meta_repo_path)
    record_activity(
        command="domain", subcommand="build-snapshot",
        args={"domain": domain_name, "snapshot_id": sid, "blueprint_id": bp_id},
    )


# ---------------------------------------------------------------------------
# {CLI_NAME} domain validate-skills
# ---------------------------------------------------------------------------

@domain_app.command("validate-skills")
def validate_skills(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    skill: Annotated[str, typer.Option("--skill", "-s", help="Skill name to validate")] = None,
    feedback: Annotated[str, typer.Option("--feedback", "-f", help="Feedback: works, needs-tuning, broken")] = None,
    task: Annotated[str, typer.Option("--task", "-t", help="Task description that skill was tested on")] = None,
    notes: Annotated[str, typer.Option("--notes", "-n", help="Feedback notes")] = None,
    list_skills: Annotated[bool, typer.Option("--list", "-l", help="List skill validation status")] = False,
    report: Annotated[bool, typer.Option("--report", help="Generate validation report")] = False,
    context_dir: Annotated[str, typer.Option("--context-dir", help="Domain context repo directory")] = None,
) -> None:
    """
    Validate and track skill usage against real development tasks.

    Record validation feedback for injected skills, list status, or generate
    a report of which skills have been validated.

    Examples:
        {CLI_NAME} domain validate-skills cwow-facility --list
        {CLI_NAME} domain validate-skills cwow-facility --skill requesting-code-review --feedback works --task "Review PR #123"
        {CLI_NAME} domain validate-skills cwow-facility --report
    """.format(CLI_NAME=CLI_NAME)
    from agentic_cli.kg.domain_skills import (
        load_skills_manifest,
        update_skill_status,
        log_skill_event,
    )

    # Resolve domain context dir
    ctx_dir = _resolve_domain_context_dir(domain_name, context_dir)
    if not ctx_dir:
        return

    manifest = load_skills_manifest(ctx_dir)
    if not manifest or not manifest.get("skills"):
        console.print(f"[red]✗ No skills manifest found in {ctx_dir}[/red]")
        console.print(f"[dim]Run: {CLI_NAME} domain init-context {domain_name}[/dim]")
        raise typer.Exit(1)

    # List mode
    if list_skills:
        table = Table(title=f"Skills Status — {domain_name}")
        table.add_column("Skill", style="cyan")
        table.add_column("Source", style="dim")
        table.add_column("Status", style="yellow")
        table.add_column("Validated", style="green")
        table.add_column("Notes", style="dim")

        for sname, sinfo in sorted(manifest["skills"].items()):
            validated = "✓" if sinfo.get("validated") else "—"
            table.add_row(
                sname,
                sinfo.get("source", "—"),
                sinfo.get("status", "—"),
                validated,
                (sinfo.get("notes") or "")[:40],
            )
        console.print(table)
        return

    # Report mode
    if report:
        skills_data = manifest.get("skills", {})
        total = len(skills_data)
        validated = sum(1 for s in skills_data.values() if s.get("validated"))
        forked = sum(1 for s in skills_data.values() if s.get("customized"))
        broken = sum(1 for s in skills_data.values() if s.get("status") == "broken")

        console.print(Panel(
            f"[bold]Domain:[/bold] {domain_name}\n"
            f"[bold]Total Skills:[/bold] {total}\n"
            f"[bold]Validated:[/bold] {validated}/{total}\n"
            f"[bold]Forked:[/bold] {forked}\n"
            f"[bold]Broken:[/bold] {broken}\n"
            f"[bold]Pending:[/bold] {total - validated}",
            title="Skill Validation Report",
            border_style="cyan",
        ))
        return

    # Validate a specific skill
    if not skill:
        console.print("[red]Provide --skill or use --list / --report[/red]")
        raise typer.Exit(1)

    if skill not in manifest.get("skills", {}):
        console.print(f"[red]✗ Skill '{skill}' not found in manifest[/red]")
        console.print(f"[dim]Use --list to see available skills[/dim]")
        raise typer.Exit(1)

    if not feedback:
        console.print("[red]Provide --feedback (works, needs-tuning, broken)[/red]")
        raise typer.Exit(1)

    if feedback not in ("works", "needs-tuning", "broken"):
        console.print(f"[red]Invalid feedback: {feedback} (use: works, needs-tuning, broken)[/red]")
        raise typer.Exit(1)

    # Record validation
    is_validated = feedback == "works"
    status = "validated" if is_validated else feedback
    combined_notes = ""
    if task:
        combined_notes += f"Task: {task}. "
    if notes:
        combined_notes += notes

    update_skill_status(ctx_dir, skill, status, validated=is_validated, notes=combined_notes)
    log_skill_event(ctx_dir, skill, "validated", {
        "feedback": feedback,
        "task": task or "",
        "notes": notes or "",
    })

    emoji = "✓" if is_validated else "⚠" if feedback == "needs-tuning" else "✗"
    color = "green" if is_validated else "yellow" if feedback == "needs-tuning" else "red"
    console.print(f"[{color}]{emoji} Skill '{skill}' marked as: {status}[/{color}]")
    if combined_notes:
        console.print(f"[dim]Notes: {combined_notes}[/dim]")


# ---------------------------------------------------------------------------
# {CLI_NAME} domain fork-skill
# ---------------------------------------------------------------------------

@domain_app.command("fork-skill")
def fork_skill_cmd(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    skill: Annotated[str, typer.Option("--skill", "-s", help="Skill name to fork")] = ...,
    reason: Annotated[str, typer.Option("--reason", "-r", help="Reason for forking")] = "",
    context_dir: Annotated[str, typer.Option("--context-dir", help="Domain context repo directory")] = None,
) -> None:
    """
    Fork a superpowers skill for domain-specific customization.

    Copies the skill to a domain-specific directory, updates the manifest,
    and creates a CUSTOMIZATION_NOTES.md for tracking changes.

    Examples:
        {CLI_NAME} domain fork-skill cwow-facility --skill requesting-code-review --reason "Add domain review rules"
    """.format(CLI_NAME=CLI_NAME)
    from agentic_cli.kg.domain_skills import fork_skill

    ctx_dir = _resolve_domain_context_dir(domain_name, context_dir)
    if not ctx_dir:
        return

    result = fork_skill(ctx_dir, skill, domain_name, reason)
    if result:
        console.print(f"[green]✓ Skill forked:[/green] {result.relative_to(ctx_dir)}")
        console.print(f"[dim]Customize files in {result}[/dim]")
        console.print(f"[dim]Document changes in {result / 'CUSTOMIZATION_NOTES.md'}[/dim]")
    else:
        console.print(f"[red]✗ Failed to fork skill '{skill}'[/red]")
        console.print(f"[dim]Check that the skill exists in the domain context repo[/dim]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# {CLI_NAME} domain list-skills
# ---------------------------------------------------------------------------

@domain_app.command("list-skills")
def list_skills(
    domain_name: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-facility)")],
    context_dir: Annotated[str, typer.Option("--context-dir", help="Domain context repo directory")] = None,
) -> None:
    """
    List all skills available for a domain (from manifest).

    Examples:
        {CLI_NAME} domain list-skills cwow-facility
    """.format(CLI_NAME=CLI_NAME)
    from agentic_cli.kg.domain_skills import load_skills_manifest

    ctx_dir = _resolve_domain_context_dir(domain_name, context_dir)
    if not ctx_dir:
        return

    manifest = load_skills_manifest(ctx_dir)
    if not manifest or not manifest.get("skills"):
        console.print(f"[red]✗ No skills manifest found[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Domain Skills — {domain_name}")
    table.add_column("Skill", style="cyan")
    table.add_column("Description")
    table.add_column("Source", style="dim")
    table.add_column("Status", style="yellow")
    table.add_column("Validated", style="green")
    table.add_column("Customized", style="magenta")

    for sname, sinfo in sorted(manifest["skills"].items()):
        table.add_row(
            sname,
            (sinfo.get("description", "") or "")[:50],
            sinfo.get("source", "—"),
            sinfo.get("status", "—"),
            "✓" if sinfo.get("validated") else "—",
            "✓" if sinfo.get("customized") else "—",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(manifest['skills'])} skills[/dim]")


# ---------------------------------------------------------------------------
# Helper: resolve domain context directory
# ---------------------------------------------------------------------------

def _resolve_domain_context_dir(domain_name: str, context_dir: str = None) -> Path | None:
    """Find the domain context repo directory."""
    if context_dir:
        p = Path(context_dir).resolve()
        if p.exists():
            return p
        console.print(f"[red]✗ Directory not found: {p}[/red]")
        raise typer.Exit(1)

    # Try standard naming convention in CWD parent
    candidates = [
        Path.cwd() / f"{domain_name}-domain-context",
        Path.cwd().parent / f"{domain_name}-domain-context",
        Path.cwd() / ".domain-context",
    ]
    for c in candidates:
        if c.exists() and (c / ".domain").exists():
            return c

    console.print(f"[red]✗ Cannot find domain context repo for '{domain_name}'[/red]")
    console.print(f"[dim]Use --context-dir to specify the path, or run from the workspace root[/dim]")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# {CLI_NAME} domain sync  (tech-lead / domain-tier workspace)
# ---------------------------------------------------------------------------

@domain_app.command("sync")
def sync_domain(
    domain_name: Annotated[str, typer.Argument(help="Domain slug (e.g. cwow-facility)")],
    persona: Annotated[str, typer.Option("--persona", help="Domain-tier persona (default: tech-lead)")] = "tech-lead",
    graphify: Annotated[bool, typer.Option("--graphify/--no-graphify", help="Run graphify update per repo to refresh code graphs")] = True,
    code_assist_tool: Annotated[str, typer.Option("--code-assist-tool", help="devin | windsurf | cursor | generic (where the persona skill is written)")] = "windsurf",
) -> None:
    """Assemble the tech-lead (domain-tier) workspace.

    Ensures a canonical store clone for every linked repo, refreshes each repo's
    graphify graph, writes a federated reference manifest
    (``<domain-meta>/.graph/graph-refs.json``) — no code copied into the meta-repo —
    and installs the tech-lead persona skill. Registers the workspace.
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    product = d.get("product")
    domain_label = d.get("domain", domain_name)

    repos = get_domain_repos(domain_name)
    if not repos:
        console.print(f"[yellow]⚠ No repos linked to '{domain_name}'. Use 'keel domain link-repo' first.[/yellow]")
        raise typer.Exit(0)

    meta = detect_domain_meta_repo(domain_name)
    if not meta:
        console.print(f"[red]✗ Domain meta-repo not found for '{domain_name}'.[/red]")
        console.print(f"[dim]Run: {CLI_NAME} domain init-meta {domain_name} --product-meta <url>[/dim]")
        raise typer.Exit(1)

    if graphify and not pw.graphify_available():
        console.print("[yellow]⚠ graphify CLI not found; writing graph references without graphs.[/yellow]")
        console.print("[dim]Install with: pip install graphifyy[/dim]")

    console.print(f"[cyan]Syncing {len(repos)} repo(s) into the store for '{domain_name}'...[/cyan]")

    from agentic_cli.kg.okf.locking import DomainLockBusy, domain_lock

    # Serialize per-domain: refreshing shared store graphs must not interleave
    # with a concurrent `kg okf enrich/export` (which reads those graphs) or
    # another developer's sync of the same domain.
    try:
        with domain_lock(domain_name, scope="okf"):
            manifest = pw.build_graph_refs(domain_name, product, repos, run_graphify=graphify)
    except DomainLockBusy as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        console.print(f"[dim]Another enrich/export/sync for '{domain_name}' is in progress. Try again shortly.[/dim]")
        raise typer.Exit(1)

    for entry in manifest["repos"]:
        if entry["status"] == "ready":
            graph = "graph ✓" if entry["graph"].get("has_graph") else "graph ✗"
            console.print(f"  [green]✓[/green] {entry['slug']} ({graph})")
        else:
            console.print(f"  [red]✗[/red] {entry['slug']}: {entry.get('error', 'failed')}")

    refs_path = pw.write_graph_refs(meta, manifest)
    console.print(f"[green]✓[/green] Federated manifest: {refs_path}")

    # Install the tech-lead persona skill into the domain meta-repo.
    skill = pw.assemble_persona_skill(
        meta, persona,
        pw.render_tech_lead_skill({
            "domain": domain_name, "domain_label": domain_label,
            "product": product, "repos": manifest["repos"],
        }),
        code_assist_tool,
    )
    console.print(f"[green]✓[/green] Persona skill: {skill}")

    ready = sum(1 for e in manifest["repos"] if e["status"] == "ready")
    graphs = sum(1 for e in manifest["repos"] if e["graph"].get("has_graph"))
    register_workspace(
        tier="domain", persona=persona, root_path=str(meta),
        product=product, domain=domain_name, store_path=str(pw.get_store_base()),
        repos=[
            {"slug": e["slug"], "mode": "graph-ref", "path": e.get("store_path")}
            for e in manifest["repos"]
        ],
    )
    record_activity(
        command="domain", subcommand="sync",
        args={"domain": domain_name, "persona": persona, "repos": len(repos)},
    )

    console.print(Panel.fit(
        f"[bold green]✓ Tech-lead workspace ready[/bold green]\n\n"
        f"[bold]Persona:[/bold] {persona} (domain tier)\n"
        f"[bold]Open in IDE:[/bold] {meta}\n"
        f"[bold]Repos:[/bold] {ready}/{len(repos)} in store, {graphs} graph(s) ready\n\n"
        f"[dim]Federated cross-repo reasoning via .graph/graph-refs.json — no code checkout.[/dim]",
        border_style="green",
    ))
