"""``{CLI_NAME} skill upstream`` — push domain-authored skills to the registry.

The inverse of a skill trial: instead of pulling a registry skill into a domain,
this finds skills a domain *authored* and promotes them into the shared registry
so every other domain (and every future scaffold) gets them.

Promotion stages the skill on a dedicated branch in the registry working tree.
Pushing is opt-in (``--push``) because the registry is a reviewed, shared
artifact.
"""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli import skills_upstream as up
from agentic_cli.config import CLI_NAME

upstream_app = typer.Typer(
    help="Promote domain-authored skills into the shared skills registry",
    rich_markup_mode=None,
)
console = Console()

_ORIGIN_STYLE = {
    up.DOMAIN_AUTHORED: "green",
    up.DOMAIN_CUSTOMIZED: "cyan",
    up.UPSTREAM_BASELINE: "dim",
    up.PLATFORM_GENERATED: "dim",
    up.REGISTRY_SOURCED: "dim",
}
_KIND_STYLE = {up.NEW: "green", up.UPDATE: "yellow", up.IDENTICAL: "dim"}


def _registry() -> Path:
    """The configured skills registry (cloning it if that's how it's set up)."""
    from agentic_cli.commands.code import _ensure_registry

    return _ensure_registry()


def _discover(domain: str, repo: Optional[str]):
    registry = _registry()
    try:
        if repo:
            path = Path(repo).expanduser().resolve()
            if not path.is_dir():
                console.print(f"[red]✗[/red] Not a directory: {path}")
                raise typer.Exit(1)
            return path, up.discover_domain_skills(path, registry=registry), registry
        domain_repo, candidates = up.discover_for_domain(domain, registry=registry)
        return domain_repo, candidates, registry
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@upstream_app.command("list")
def list_candidates(
    domain: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-apoc)")],
    repo: Annotated[str, typer.Option("--repo", help="Path to the domain context-meta repo (defaults to the workspace location)")] = None,
    all_skills: Annotated[bool, typer.Option("--all", help="Also list skills that are not promotable, with the reason")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the raw candidate list as JSON")] = False,
) -> None:
    """List a domain's skills, showing which can be promoted upstream.

    Read-only. Skills are classified by origin: only domain-authored and
    domain-customized skills are offered — injected superpowers baselines,
    platform-generated context/role skills, and registry-installed skills are
    excluded (use ``--all`` to see them with the reason).
    """
    domain_repo, candidates, registry = _discover(domain, repo)

    if as_json:
        console.print_json(_json.dumps({
            "domain": domain,
            "domain_repo": str(domain_repo),
            "registry": str(registry),
            "candidates": [c.to_dict() for c in candidates],
        }))
        return

    promotable = [c for c in candidates if c.promotable]
    console.print(Panel(
        f"Domain repo: {domain_repo}\n"
        f"Registry:    {registry}\n"
        f"Skills:      {len(candidates)} found, "
        f"[bold]{len(promotable)}[/bold] promotable",
        title=f"Skill upstream — {domain}",
        border_style="green" if promotable else "yellow",
    ))

    shown = candidates if all_skills else promotable
    if not shown:
        console.print(
            "[yellow]No promotable skills.[/yellow] Every skill here is an "
            "injected baseline, a platform-generated render, or already in the "
            f"registry. Run with --all to see why.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Skill")
    table.add_column("Origin")
    table.add_column("Change")
    table.add_column("Location", style="dim")
    table.add_column("Why not / description")
    for c in shown:
        origin_style = _ORIGIN_STYLE.get(c.origin, "white")
        kind_style = _KIND_STYLE.get(c.kind, "white")
        note = c.reason or (c.description[:60] if c.description else "")
        table.add_row(
            f"[bold]{c.name}[/bold]" if c.promotable else c.name,
            f"[{origin_style}]{c.origin}[/{origin_style}]",
            f"[{kind_style}]{c.kind}[/{kind_style}]",
            c.location,
            note,
        )
    console.print(table)

    if promotable:
        console.print(Panel(
            f"{CLI_NAME} skill upstream promote {domain} --skill "
            f"{promotable[0].name}\n"
            f"[dim]Add --dry-run to preview, --push to publish the branch.[/dim]",
            title="Promote", border_style="cyan"))


@upstream_app.command("promote")
def promote(
    domain: Annotated[str, typer.Argument(help="Domain name (slug, e.g. cwow-apoc)")],
    skill: Annotated[list[str], typer.Option("--skill", "-s", help="Skill name to promote (repeatable)")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Path to the domain context-meta repo (defaults to the workspace location)")] = None,
    all_promotable: Annotated[bool, typer.Option("--all", help="Promote every promotable skill in the domain")] = False,
    push: Annotated[bool, typer.Option("--push", help="Push the promotion branch to origin (otherwise commit locally only)")] = False,
    no_commit: Annotated[bool, typer.Option("--no-commit", help="Write files without creating a branch/commit")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Run the gate and report what would happen, writing nothing")] = False,
) -> None:
    """Promote domain-authored skill(s) into the shared skills registry.

    Each skill passes a gate (SKILL.md structure + security scan) before
    anything is written. Files land in the registry working tree on a
    ``skill-promote/<domain>/<skill>`` branch; publishing is opt-in via
    ``--push``.
    """
    if not skill and not all_promotable:
        console.print("[red]✗[/red] Provide --skill <name> or --all")
        raise typer.Exit(1)

    domain_repo, candidates, registry = _discover(domain, repo)
    by_name = {c.name: c for c in candidates}

    if all_promotable:
        selected = [c for c in candidates if c.promotable]
        if not selected:
            console.print("[yellow]Nothing promotable in this domain.[/yellow]")
            raise typer.Exit(0)
    else:
        selected = []
        for name in list(skill or []):
            candidate = by_name.get(name)
            if candidate is None:
                console.print(
                    f"[red]✗[/red] Skill '{name}' not found in {domain_repo}. "
                    f"Run: {CLI_NAME} skill upstream list {domain} --all")
                raise typer.Exit(1)
            selected.append(candidate)

    results, failures = [], []
    for candidate in selected:
        try:
            result = up.promote_to_registry(
                candidate, domain, registry,
                domain_repo=domain_repo,
                commit=not no_commit,
                push=push,
                dry_run=dry_run,
            )
            results.append(result)
        except up.PromotionError as e:
            failures.append((candidate.name, str(e)))

    for r in results:
        state = ("would promote" if dry_run else
                 ("pushed" if r.pushed else
                  ("committed" if r.committed else "written")))
        lines = [
            f"Skill:    {r.skill}  ({r.kind})",
            f"Registry: {r.dest}",
            f"Files:    {r.files}",
            f"Gate:     {'; '.join(r.gate)}",
            f"State:    [bold]{state}[/bold]",
        ]
        if r.branch:
            lines.append(f"Branch:   {r.branch}"
                         + (f" @ {r.commit}" if r.commit else ""))
        if r.push_hint and not r.pushed:
            lines.append(f"\n[dim]Publish with:[/dim] {r.push_hint}")
        console.print(Panel("\n".join(lines),
                            title=f"{'Dry run' if dry_run else 'Promoted'} — {r.skill}",
                            border_style="cyan" if dry_run else "green"))

    for name, error in failures:
        console.print(Panel(error, title=f"Blocked — {name}", border_style="red"))

    try:
        from agentic_cli.tracker import record_activity

        record_activity(
            command="skill", subcommand="upstream-promote",
            status="error" if failures and not results else "success",
            entity_type="domain", entity_id=domain,
            args={"domain": domain, "skills": [c.name for c in selected],
                  "push": push, "dry_run": dry_run},
            details={"promoted": [r.skill for r in results],
                     "blocked": {n: e for n, e in failures}},
        )
    except Exception:  # noqa: BLE001
        pass

    if failures and not results:
        raise typer.Exit(1)
