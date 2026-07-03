"""History and tracking commands — view activity log, onboarded repos, and created projects."""

import json
from typing import Optional
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_cli.tracker import (
    get_activity,
    get_activity_summary,
    get_repos,
    get_projects,
    get_full_context,
    remove_repo,
)
from agentic_cli.config import CLI_NAME

console = Console()
history_app = typer.Typer(help="View activity history, onboarded repos, and tracked projects", rich_markup_mode=None)


@history_app.command("log")
def show_log(
    command: Annotated[
        Optional[str],
        typer.Option("--command", "-c", help="Filter by command group (e.g. kg, code, project)"),
    ] = None,
    subcommand: Annotated[
        Optional[str],
        typer.Option("--sub", "-s", help="Filter by subcommand (e.g. onboard, create, ingest)"),
    ] = None,
    status: Annotated[
        Optional[str],
        typer.Option("--status", help="Filter by status: success or error"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of entries to show"),
    ] = 30,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON (for agent consumption)"),
    ] = False,
) -> None:
    """
    Show the CLI activity log.

    Examples:
        {CLI_NAME} history log
        {CLI_NAME} history log --command kg --limit 10
        {CLI_NAME} history log --command code --sub onboard
        {CLI_NAME} history log --status error
        {CLI_NAME} history log --json
    """.format(CLI_NAME=CLI_NAME)
    entries = get_activity(command=command, subcommand=subcommand, status=status, limit=limit)

    if output_json:
        console.print(json.dumps(entries, indent=2))
        return

    if not entries:
        console.print("[dim]No activity recorded yet.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", title="Activity Log")
    table.add_column("Time", style="dim", max_width=20)
    table.add_column("Command", style="cyan")
    table.add_column("Sub", style="green")
    table.add_column("Status")
    table.add_column("Source", style="magenta")
    table.add_column("Duration")
    table.add_column("Path / Details", style="dim", max_width=40)

    for entry in entries:
        ts = entry["timestamp"][:19].replace("T", " ")
        cmd = entry["command"] or ""
        sub = entry["subcommand"] or ""
        st = "[green]✓[/green]" if entry["status"] == "success" else "[red]✗[/red]"
        src = entry.get("source") or "cli"
        dur = f"{entry['duration_ms']}ms" if entry.get("duration_ms") else "—"
        path = entry.get("repo_path") or ""
        if not path and entry.get("details"):
            try:
                details = json.loads(entry["details"]) if isinstance(entry["details"], str) else entry["details"]
                path = details.get("error", details.get("name", ""))[:40]
            except (json.JSONDecodeError, AttributeError):
                pass
        table.add_row(ts, cmd, sub, st, src, dur, path)

    console.print(table)
    console.print(f"\n[dim]Showing {len(entries)} of last entries. Use --limit to change.[/dim]")


@history_app.command("summary")
def show_summary(
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """
    Show summary statistics of all CLI activity.

    Examples:
        {CLI_NAME} history summary
        {CLI_NAME} history summary --json
    """.format(CLI_NAME=CLI_NAME)
    summary = get_activity_summary()

    if output_json:
        console.print(json.dumps(summary, indent=2))
        return

    if summary["total_actions"] == 0:
        console.print("[dim]No activity recorded yet.[/dim]")
        return

    lines = [
        f"[bold green]Activity Summary[/bold green]\n",
        f"[bold]Total Actions:[/bold] {summary['total_actions']}",
        f"[bold]Errors:[/bold] {summary['errors']}",
        f"[bold]Success Rate:[/bold] {summary['success_rate']}",
        f"[bold]Last Activity:[/bold] {summary['last_activity'][:19].replace('T', ' ') if summary['last_activity'] else 'None'}",
        "",
        "[bold]By Command:[/bold]",
    ]
    for cmd, cnt in sorted(summary["commands"].items(), key=lambda x: -x[1]):
        lines.append(f"  {cmd}: {cnt}")

    console.print(Panel.fit("\n".join(lines), border_style="cyan"))


@history_app.command("repos")
def list_repos(
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Filter repos by name"),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """
    List all onboarded repositories.

    Examples:
        {CLI_NAME} history repos
        {CLI_NAME} history repos --name cwow
        {CLI_NAME} history repos --json
    """.format(CLI_NAME=CLI_NAME)
    repos = get_repos(name=name)

    if output_json:
        console.print(json.dumps(repos, indent=2))
        return

    if not repos:
        console.print("[dim]No repos onboarded yet.[/dim]")
        console.print(f"[dim]Onboard one with: {CLI_NAME} code onboard --path ./my-repo[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", title="Onboarded Repositories")
    table.add_column("Name", style="cyan")
    table.add_column("Languages", style="green")
    table.add_column("Frameworks")
    table.add_column("Skills")
    table.add_column("Deps", justify="right")
    table.add_column("Onboarded", style="dim")
    table.add_column("Path", style="dim", max_width=35)

    for repo in repos:
        langs = ", ".join(repo.get("languages", []) or [])[:25]
        fws = ", ".join(repo.get("frameworks", []) or [])[:25]
        skills = len(repo.get("skills_installed", []) or [])
        deps = str(repo.get("dependencies", 0))
        onboarded = (repo.get("onboarded_at") or "")[:10]
        path = repo.get("path", "")
        # Shorten home dir
        path = path.replace(str(__import__("pathlib").Path.home()), "~")
        table.add_row(repo["name"], langs, fws, str(skills), deps, onboarded, path)

    console.print(table)
    console.print(f"\n[dim]Total: {len(repos)} repo(s)[/dim]")


@history_app.command("repos-remove")
def repos_remove(
    path: Annotated[
        str,
        typer.Argument(help="Path of the repo to remove from tracking"),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation"),
    ] = False,
) -> None:
    """
    Remove a repo from the central tracking registry.

    This does NOT delete the repo — only removes it from {CLI_NAME} tracking.
    """.format(CLI_NAME=CLI_NAME)
    from pathlib import Path as P
    resolved = str(P(path).resolve())

    if not yes:
        confirm = typer.confirm(f"Remove '{resolved}' from tracking?")
        if not confirm:
            raise typer.Exit(0)

    if remove_repo(resolved):
        console.print(f"[green]✓[/green] Removed '{resolved}' from tracking.")
    else:
        console.print(f"[yellow]Repo not found in tracking: {resolved}[/yellow]")


@history_app.command("projects")
def list_tracked_projects(
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """
    List all created agent projects.

    Examples:
        {CLI_NAME} history projects
        {CLI_NAME} history projects --json
    """.format(CLI_NAME=CLI_NAME)
    projects = get_projects()

    if output_json:
        console.print(json.dumps(projects, indent=2))
        return

    if not projects:
        console.print("[dim]No projects created yet.[/dim]")
        console.print(f"[dim]Create one with: {CLI_NAME} project create my-agent[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", title="Created Projects")
    table.add_column("Name", style="cyan")
    table.add_column("Framework", style="green")
    table.add_column("Use Case")
    table.add_column("Created", style="dim")
    table.add_column("Path", style="dim", max_width=40)

    for proj in projects:
        created = (proj.get("created_at") or "")[:10]
        path = proj.get("path", "").replace(str(__import__("pathlib").Path.home()), "~")
        table.add_row(
            proj["name"],
            proj.get("framework") or "—",
            proj.get("use_case") or "—",
            created,
            path,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(projects)} project(s)[/dim]")


@history_app.command("context")
def export_context(
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = True,
) -> None:
    """
    Export full tracked context as JSON for agent consumption.

    This provides agents with a complete snapshot of:
    - All onboarded repos with tech stacks
    - All created projects
    - Activity summary and recent history

    Examples:
        {CLI_NAME} history context
        {CLI_NAME} history context --json
    """.format(CLI_NAME=CLI_NAME)
    ctx = get_full_context()
    console.print(json.dumps(ctx, indent=2))
