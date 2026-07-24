"""Persona-scoped, tier-aware workspace commands.

Three tiers, three personas:

- ``keel workspace open <domain> <repo> --persona dev``  → developer worktree (repo tier)
- ``keel domain sync <domain>``                          → tech-lead domain workspace (domain tier)
- ``keel workspace status --product <P>``                → solutions-architect view (product tier)
- ``keel workspace list``                                → all tracked workspaces
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli import persona_workspace as pw
from agentic_cli.meta_repo.detector import detect_domain_meta_repo
from agentic_cli.tracker import (
    record_activity,
    register_workspace,
    get_workspaces,
    remove_workspace,
    get_domain,
    get_domain_repos,
    get_domains,
)

console = Console()
workspace_app = typer.Typer(
    help="Persona-scoped, tier-aware development workspaces (dev / tech-lead / solutions-architect)",
    rich_markup_mode=None,
)


def _find_domain_repo(domain_name: str, repo_slug: str) -> Optional[dict]:
    for r in get_domain_repos(domain_name):
        if r["repo_slug"] == repo_slug:
            return r
    return None


@workspace_app.command("open")
def open_workspace(
    domain_name: Annotated[str, typer.Argument(help="Domain slug (e.g. cwow-facility)")],
    repo_slug: Annotated[str, typer.Argument(help="Repo slug linked to the domain")],
    persona: Annotated[str, typer.Option("--persona", help="Persona (default: dev)")] = "dev",
    branch: Annotated[Optional[str], typer.Option("--branch", help="Worktree branch name (default: ws/<persona>/<slug>)")] = None,
    graphify: Annotated[bool, typer.Option("--graphify/--no-graphify", help="Generate the repo graph in the worktree now (default: off; run 'graphify update .' on demand)")] = False,
    code_assist_tool: Annotated[str, typer.Option("--code-assist-tool", help="auto (detect) | devin | cursor | generic | windsurf (deprecated) — where the persona skill is written")] = "auto",
) -> None:
    """Open a developer (repo-tier) workspace as an editable git worktree.

    Materializes a worktree from the canonical store (no duplicate clone),
    installs the dev persona skill, and registers the workspace.
    """
    d = get_domain(domain_name)
    if not d:
        console.print(f"[red]✗ Domain '{domain_name}' not found.[/red]")
        raise typer.Exit(1)

    repo = _find_domain_repo(domain_name, repo_slug)
    if not repo or not repo.get("clone_url"):
        console.print(f"[red]✗ Repo '{repo_slug}' not linked to '{domain_name}' (or missing clone URL).[/red]")
        raise typer.Exit(1)

    product = d.get("product")
    domain_label = d.get("domain", domain_name)

    # Ensure the canonical store clone exists (so dev can worktree from it).
    console.print(f"[cyan]Ensuring store clone for {repo_slug}...[/cyan]")
    try:
        store_path, newly = pw.ensure_store_clone(repo_slug, repo["clone_url"], repo.get("branch"))
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] Store: {store_path}{' (cloned)' if newly else ''}")

    # Worktree destination: <workspace>/<domain>/repos/<slug>
    dest = pw.get_workspace_base() / domain_name / "repos" / repo_slug
    wt_branch = branch or f"ws/{persona}/{repo_slug}"
    console.print(f"[cyan]Creating worktree on branch '{wt_branch}'...[/cyan]")
    try:
        pw.add_worktree(repo_slug, dest, wt_branch)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] Worktree: {dest}")

    # Refresh this repo's graph for navigation (best-effort, opt-in).
    if graphify:
        console.print("[cyan]Generating repo graph (graphify update)...[/cyan]")
        pw.run_graphify_update(dest)

    # Install dev persona skill.
    skill = pw.assemble_persona_skill(
        dest, persona,
        pw.render_dev_skill({
            "domain": domain_name, "domain_label": domain_label,
            "product": product, "repo_slug": repo_slug,
        }),
        code_assist_tool,
    )
    console.print(f"[green]✓[/green] Persona skill: {skill}")

    register_workspace(
        tier="repo", persona=persona, root_path=str(dest),
        product=product, domain=domain_name, store_path=str(pw.get_store_base()),
        repos=[{"slug": repo_slug, "mode": "code", "branch": wt_branch, "path": str(dest)}],
    )
    record_activity(
        command="workspace", subcommand="open",
        args={"domain": domain_name, "repo": repo_slug, "persona": persona},
    )

    console.print(Panel.fit(
        f"[bold green]✓ Dev workspace ready[/bold green]\n\n"
        f"[bold]Persona:[/bold] {persona} (repo tier)\n"
        f"[bold]Open in IDE:[/bold] {dest}\n"
        f"[bold]Branch:[/bold] {wt_branch}\n\n"
        f"[dim]Single-repo coding with graphify navigation.[/dim]",
        border_style="green",
    ))


@workspace_app.command("list")
def list_workspaces(
    tier: Annotated[Optional[str], typer.Option("--tier", help="Filter by tier: repo | domain | product")] = None,
) -> None:
    """List all tracked persona workspaces across tiers."""
    rows = get_workspaces(tier=tier)
    if not rows:
        console.print("[dim]No workspaces registered yet.[/dim]")
        console.print(f"[dim]Create one: {CLI_NAME} domain sync <domain>  or  {CLI_NAME} workspace open <domain> <repo>[/dim]")
        return

    table = Table(title="Persona Workspaces", show_lines=False)
    table.add_column("Tier", style="cyan")
    table.add_column("Persona", style="magenta")
    table.add_column("Product")
    table.add_column("Domain")
    table.add_column("Repos")
    table.add_column("Root path", style="dim")
    for w in rows:
        repos = w.get("repos", [])
        repo_summary = ", ".join(
            f"{r.get('slug')}[{r.get('mode', '?')}]" for r in repos
        ) if repos else "—"
        table.add_row(
            w["tier"], w["persona"], w.get("product") or "—",
            w.get("domain") or "—", repo_summary, w["root_path"],
        )
    console.print(table)


@workspace_app.command("status")
def workspace_status(
    product: Annotated[Optional[str], typer.Option("--product", help="Product name for the solutions-architect view")] = None,
    domain_name: Annotated[Optional[str], typer.Option("--domain", help="Single domain slug to inspect")] = None,
    assemble: Annotated[bool, typer.Option("--assemble/--no-assemble", help="Write the solutions-architect persona skill into the product meta-repo")] = False,
    product_meta: Annotated[Optional[Path], typer.Option("--product-meta", help="Explicit product meta-repo path (for --assemble)")] = None,
    code_assist_tool: Annotated[str, typer.Option("--code-assist-tool", help="auto (detect) | devin | cursor | generic | windsurf (deprecated) — where the persona skill is written")] = "auto",
) -> None:
    """Solutions-architect (product tier) view: cross-domain map from the tracker.

    Tracker-only — clones nothing. Optionally assembles the SA persona skill
    into the product meta-repo.
    """
    # Resolve the set of domains to display.
    if domain_name:
        domains = [get_domain(domain_name)] if get_domain(domain_name) else []
    elif product:
        domains = [d for d in get_domains() if d.get("product") == product]
    else:
        domains = get_domains()

    if not domains:
        console.print("[yellow]No matching domains found.[/yellow]")
        raise typer.Exit(0)

    summary = []
    table = Table(title=f"Product View{f' — {product}' if product else ''}", show_lines=False)
    table.add_column("Domain", style="cyan")
    table.add_column("Repos", justify="right")
    table.add_column("Graphs ready", justify="right")
    table.add_column("Domain meta-repo", style="dim")

    for d in domains:
        slug = d["name"]
        repos = get_domain_repos(slug)
        repo_count = len(repos)
        # Read the tech-lead manifest for graph availability, if present.
        graphs_ready = 0
        meta = detect_domain_meta_repo(slug)
        if meta:
            refs = meta / pw.GRAPH_DIR_NAME / pw.GRAPH_REFS_FILENAME
            if refs.exists():
                try:
                    data = json.loads(refs.read_text())
                    graphs_ready = sum(
                        1 for r in data.get("repos", [])
                        if r.get("graph", {}).get("has_graph")
                    )
                except (json.JSONDecodeError, OSError):
                    pass
        table.add_row(slug, str(repo_count), f"{graphs_ready}/{repo_count}",
                      str(meta) if meta else "—")
        summary.append({"domain": slug, "repo_count": repo_count, "graphs_ready": graphs_ready})

    console.print(table)

    # Register the product-tier (tracker-only) workspace.
    if product:
        register_workspace(
            tier="product", persona="solutions-architect",
            root_path=str(product_meta or pw.find_product_meta(product) or f"product:{product}"),
            product=product, domain=None, store_path=None,
            repos=[{"slug": s["domain"], "mode": "graph-ref"} for s in summary],
        )

    if assemble:
        if not product:
            console.print("[red]--assemble requires --product[/red]")
            raise typer.Exit(1)
        meta_path = pw.find_product_meta(product, product_meta)
        if not meta_path:
            console.print(f"[yellow]⚠ Product meta-repo for '{product}' not found; skipping skill assembly.[/yellow]")
        else:
            skill = pw.assemble_persona_skill(
                meta_path, "solutions-architect",
                pw.render_sa_skill({"product": product, "domains": summary}),
                code_assist_tool,
            )
            console.print(f"[green]✓[/green] Solutions-architect skill: {skill}")

    record_activity(
        command="workspace", subcommand="status",
        args={"product": product, "domain": domain_name, "assemble": assemble},
    )
