#!/usr/bin/env python3
"""Interactive Domain Onboarding Script.

Walks through onboarding a project and domain with superpowers skills,
KG context, Confluence docs, and repo linking.

Usage:
    python scripts/onboard_domain.py
    python scripts/onboard_domain.py --product CWOW --domain Facility --bb CGF --confluence MTT

Environment:
    Requires agentic-cli to be installed in the Python environment.
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
except ImportError:
    print("Missing 'rich' library. Install with: pip install rich")
    sys.exit(1)

console = Console()

# Detect CLI name (prefer dva alias if available)
import os
import shutil
if shutil.which("dva"):
    CLI_NAME = "dva"
else:
    CLI_NAME = os.getenv("AGENT_CLI_NAME", "agent-cli")
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_WORKSPACE = SCRIPT_DIR.parent


def run_cli(args: list[str], check: bool = False, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a CLI command and return the result."""
    cmd = [CLI_NAME] + args
    console.print(f"[dim]  $ {' '.join(cmd)}[/dim]")
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


def step_header(num: int, title: str) -> None:
    console.print()
    console.rule(f"[bold cyan]Step {num}: {title}[/bold cyan]")


def main():
    parser = argparse.ArgumentParser(description="Interactive Domain Onboarding")
    parser.add_argument("--product", help="Product name (e.g. CWOW)")
    parser.add_argument("--domain", help="Domain name (e.g. Facility)")
    parser.add_argument("--bb", help="Bitbucket project key (e.g. CGF)")
    parser.add_argument("--confluence", help="Confluence space key (e.g. MTT)")
    parser.add_argument("--jira", help="Jira project key (defaults to product)")
    parser.add_argument("--description", help="Domain description")
    parser.add_argument("--release-url", help="Confluence release page URL for KG ingestion")
    parser.add_argument("--git-remote", help="Git remote for domain-context repo")
    parser.add_argument("--workspace", help="Workspace directory", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--lightrag-url", help="LightRAG server URL", default="http://localhost:8001")
    parser.add_argument("--skip-kg", action="store_true", help="Skip KG ingestion")
    parser.add_argument("--skip-skills", action="store_true", help="Skip superpowers skill injection")
    parser.add_argument("--non-interactive", action="store_true", help="No prompts, fail if args missing")
    args = parser.parse_args()

    # ── Banner ──────────────────────────────────────────────
    console.print()
    console.print(Panel(
        "[bold]Domain Onboarding — Superpowers Skills Integration[/bold]\n\n"
        "This script will:\n"
        "  1. Register product & domain\n"
        "  2. Fetch & link repos from Bitbucket\n"
        "  3. Fetch & track Confluence docs\n"
        "  4. Ingest docs into Knowledge Graph\n"
        "  5. Initialize domain context repo with superpowers skills\n"
        "  6. Generate domain persona skills",
        border_style="cyan",
    ))

    # ── Step 1: Gather inputs ──────────────────────────────
    step_header(1, "Project & Domain Configuration")

    interactive = not args.non_interactive

    product = args.product or (Prompt.ask("  Product name", default="CWOW") if interactive else None)
    if not product:
        console.print("[red]✗ Product name is required[/red]")
        sys.exit(1)
    product = product.upper()

    domain = args.domain or (Prompt.ask("  Domain name", default="Facility") if interactive else None)
    if not domain:
        console.print("[red]✗ Domain name is required[/red]")
        sys.exit(1)

    bb_project = args.bb or (Prompt.ask("  Bitbucket project key") if interactive else None)
    if not bb_project:
        console.print("[red]✗ Bitbucket project key is required[/red]")
        sys.exit(1)
    bb_project = bb_project.upper()

    conf_space = args.confluence or (Prompt.ask("  Confluence space key") if interactive else None)
    if not conf_space:
        console.print("[red]✗ Confluence space key is required[/red]")
        sys.exit(1)
    conf_space = conf_space.upper()

    jira_project = args.jira or (Prompt.ask("  Jira project key", default=product) if interactive else product)
    jira_project = jira_project.upper()

    description = args.description or (Prompt.ask("  Domain description (optional)", default="") if interactive else "")

    release_url = args.release_url or (Prompt.ask("  Confluence release page URL (optional)", default="") if interactive else "")

    git_remote = args.git_remote or (Prompt.ask("  Git remote for domain-context repo (optional)", default="") if interactive else "")

    workspace = args.workspace
    lightrag_url = args.lightrag_url
    skip_kg = args.skip_kg
    skip_skills = args.skip_skills

    if interactive:
        skip_kg = skip_kg or Confirm.ask("  Skip KG ingestion?", default=False)
        skip_skills = skip_skills or Confirm.ask("  Skip superpowers skill injection?", default=False)

    # Derived
    domain_slug = f"{product.lower()}-{domain.lower().replace(' ', '-')}"

    # Summary
    console.print()
    table = Table(title="Configuration Summary", show_header=False, border_style="dim")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row("Product", product)
    table.add_row("Domain", domain)
    table.add_row("Domain Slug", domain_slug)
    table.add_row("Bitbucket", bb_project)
    table.add_row("Confluence", conf_space)
    table.add_row("Jira", jira_project)
    table.add_row("Workspace", workspace)
    table.add_row("LightRAG", lightrag_url)
    table.add_row("KG Ingestion", "Skipped" if skip_kg else "Enabled")
    table.add_row("Skills", "Skipped" if skip_skills else "Enabled")
    if release_url:
        table.add_row("Release Page", release_url)
    if git_remote:
        table.add_row("Git Remote", git_remote)
    console.print(table)

    if interactive and not Confirm.ask("\n  Proceed with this configuration?", default=True):
        console.print("Aborted.")
        sys.exit(0)

    errors = []

    # ── Step 2: Register product ───────────────────────────
    step_header(2, "Register Product")
    r = run_cli(["product", "show", product], capture=True)
    if r.returncode == 0:
        console.print(f"  [green]✓[/green] Product '{product}' already registered")
    else:
        console.print(f"  Registering product '{product}'...")
        r = run_cli(["product", "create", product])
        if r.returncode == 0:
            console.print(f"  [green]✓[/green] Product '{product}' registered")
        else:
            console.print(f"  [red]✗[/red] Failed to register product")
            errors.append("product registration")

    # ── Step 3: Register domain ────────────────────────────
    step_header(3, "Register Domain")
    domain_args = [
        "domain", "create", domain,
        "--product", product,
        "--bb", bb_project,
        "--confluence", conf_space,
        "--jira", jira_project,
    ]
    if description:
        domain_args.extend(["--description", description])

    r = run_cli(domain_args)
    if r.returncode == 0:
        console.print(f"  [green]✓[/green] Domain '{domain_slug}' registered")
    else:
        console.print(f"  [yellow]⚠[/yellow] Domain create returned non-zero (may already exist)")

    # ── Step 4: Fetch repos ────────────────────────────────
    step_header(4, "Fetch & Link Repositories")
    r = run_cli(["domain", "fetch-repos", domain_slug, "--all"], capture=True)
    if r.returncode == 0:
        console.print(f"  [green]✓[/green] Repos fetched and linked")
    else:
        console.print(f"  [yellow]⚠[/yellow] Could not fetch repos (Bitbucket MCP may not be running)")
        console.print(f"  [dim]Link manually: {CLI_NAME} domain link-repo {domain_slug} <repo-slug>[/dim]")

    # ── Step 5: Fetch Confluence docs ──────────────────────
    step_header(5, "Fetch & Track Confluence Docs")
    r = run_cli(["domain", "add-docs", domain_slug, "--all"], capture=True)
    if r.returncode == 0:
        console.print(f"  [green]✓[/green] Confluence docs tracked")
    else:
        console.print(f"  [yellow]⚠[/yellow] Could not fetch Confluence docs (Confluence MCP may not be running)")

    # ── Step 6: KG Ingestion ───────────────────────────────
    if not skip_kg:
        step_header(6, "Ingest into Knowledge Graph")

        r = run_cli([
            "kg", "ingest", "submit",
            "--domain", domain_slug,
            "--lightrag-url", lightrag_url,
        ], capture=True)
        if r.returncode == 0:
            console.print(f"  [green]✓[/green] Domain docs ingested into KG")
        else:
            console.print(f"  [yellow]⚠[/yellow] KG ingestion failed (LightRAG may not be running)")
            errors.append("KG ingestion")

        if release_url:
            r = run_cli([
                "kg", "ingest", "submit",
                "--source", release_url,
                "--format", "confluence",
                "--workspace", domain_slug,
                "--lightrag-url", lightrag_url,
            ], capture=True)
            if r.returncode == 0:
                console.print(f"  [green]✓[/green] Release page ingested")
            else:
                console.print(f"  [yellow]⚠[/yellow] Release page ingestion failed")
    else:
        step_header(6, "Ingest into Knowledge Graph (SKIPPED)")
        console.print(f"  [dim]Run later: {CLI_NAME} kg ingest submit --domain {domain_slug}[/dim]")

    # ── Step 7: Domain context repo ────────────────────────
    step_header(7, "Initialize Domain Context Repo")

    context_dir = str(Path(workspace) / f"{domain_slug}-domain-context")
    init_args = [
        "domain", "init-context", domain_slug,
        "--lightrag-url", lightrag_url,
        "--output", context_dir,
    ]
    if skip_skills:
        init_args.append("--no-bootstrap-skills")
    if git_remote:
        init_args.extend(["--git-remote", git_remote])

    r = run_cli(init_args)
    if r.returncode == 0:
        console.print(f"  [green]✓[/green] Domain context repo created at {context_dir}")
    else:
        console.print(f"  [red]✗[/red] Domain context initialization failed")
        errors.append("domain context init")

    # ── Step 8: Persona skills ─────────────────────────────
    step_header(8, "Generate Domain Persona Skills")
    r = run_cli(["domain", "gen-skills", domain_slug], capture=True)
    if r.returncode == 0:
        console.print(f"  [green]✓[/green] Domain persona skills generated")
    else:
        console.print(f"  [yellow]⚠[/yellow] Skill generation returned non-zero (may need KG context)")

    # ── Summary ────────────────────────────────────────────
    console.print()
    status = "with warnings" if errors else "successfully"
    color = "yellow" if errors else "green"
    console.print(Panel(
        f"[bold {color}]Onboarding completed {status}![/bold {color}]\n\n"
        f"[bold]Domain:[/bold]   {domain_slug}\n"
        f"[bold]Context:[/bold]  {context_dir}\n"
        f"[bold]Skills:[/bold]   {'Skipped' if skip_skills else 'Superpowers injected'}\n"
        f"[bold]KG:[/bold]       {'Skipped' if skip_kg else 'Ingested'}"
        + (f"\n\n[yellow]Warnings:[/yellow] {', '.join(errors)}" if errors else ""),
        title="Onboarding Summary",
        border_style=color,
    ))

    console.print("\n[bold]Next Steps:[/bold]\n")

    if git_remote:
        console.print(f"  1. Push context repo:")
        console.print(f"     [cyan]cd {context_dir} && git push -u origin main[/cyan]\n")

    console.print(f"  2. Onboard a repo with domain skills:")
    console.print(f"     [cyan]{CLI_NAME} code onboard --path ./<repo-name> \\")
    console.print(f"       --domain {domain_slug} \\")
    console.print(f"       --use-domain-skills \\")
    if git_remote:
        console.print(f"       --domain-context-repo {git_remote} \\")
    console.print(f"       --kg[/cyan]\n")

    console.print(f"  3. Validate skills:")
    console.print(f"     [cyan]{CLI_NAME} domain validate-skills {domain_slug} --list[/cyan]")
    console.print(f"     [cyan]{CLI_NAME} domain validate-skills {domain_slug} --skill <name> --feedback works[/cyan]\n")

    console.print(f"  4. Fork a skill for customization:")
    console.print(f"     [cyan]{CLI_NAME} domain fork-skill {domain_slug} --skill <name> --reason \"...\"[/cyan]\n")

    console.print(f"  5. View domain:")
    console.print(f"     [cyan]{CLI_NAME} domain show {domain_slug}[/cyan]")
    console.print(f"     [cyan]{CLI_NAME} domain list-skills {domain_slug}[/cyan]\n")


if __name__ == "__main__":
    main()
