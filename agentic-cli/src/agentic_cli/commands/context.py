"""Context commands — project canonical context into a portable, engine-neutral bundle."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

console = Console()
context_app = typer.Typer(help="Portable, engine-neutral context bundles (any coding agent)")


@context_app.command("build", help="Render a portable context bundle from canonical knowledge.")
def build(
    prompt: Annotated[str, typer.Argument(help="Task prompt for the bundle")],
    title: Annotated[str, typer.Option("--title", "-t", help="Bundle title")] = "",
    jira: Annotated[str, typer.Option("--jira", "-j", help="Jira key")] = "",
    domain: Annotated[str, typer.Option("--domain", "-d", help="Domain slug")] = "",
    ref: Annotated[Optional[List[str]], typer.Option("--ref", help="Canonical context ref okf://<domain>/<concept> (repeatable)")] = None,
    tag: Annotated[Optional[List[str]], typer.Option("--tag", help="Tag (repeatable)")] = None,
    out: Annotated[Optional[Path], typer.Option("--out", help="Output directory (default ~/.keel/context/<id>)")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview CONTEXT.md without writing files")] = False,
) -> None:
    """Project the org's canonical context into a self-contained bundle.

    The bundle (CONTEXT.md + prompt.md + manifest.json) is engine-neutral: hand
    it to Claude Code, Codex, or any local agent — no vendor API, no lock-in.
    It is the same context the Devin engine would receive, rendered portably.
    """
    from agentic_cli.context import (
        PortableContextSpec, bundle_id_for, load_governance, render_context_markdown,
        resolve_refs, write_bundle,
    )

    items = resolve_refs(ref or [], default_domain=domain)
    spec = PortableContextSpec(
        prompt=prompt, title=title or (f"{jira}: {prompt}" if jira else prompt)[:120],
        jira=jira, domain=domain, tags=list(tag or []), items=items,
        governance=load_governance(domain),
    )
    bid = bundle_id_for(spec)

    if dry_run:
        console.print(Panel.fit(render_context_markdown(spec), title=f"CONTEXT.md · {bid} (dry-run)",
                                border_style="yellow"))
        return

    out_dir = Path(out) if out else None
    if out_dir is None:
        from agentic_cli.execution.local_adapter import CONTEXT_ROOT

        out_dir = CONTEXT_ROOT / bid
    bundle = write_bundle(spec, out_dir)

    table = Table(show_header=True, header_style="bold magenta", title=f"Portable bundle · {bundle.bundle_id}")
    table.add_column("File", style="cyan")
    for f in bundle.files:
        table.add_row(f)
    console.print(table)
    console.print(Panel.fit(
        f"[bold]Path:[/bold] {bundle.path}\n"
        f"[bold]Refs:[/bold] {bundle.resolved_count}/{bundle.item_count} resolved\n"
        f"[bold]Digest:[/bold] {bundle.digest}",
        border_style="green"))

    try:
        from agentic_cli.tracker import record_action

        record_action("context", "build", entity_type="context_bundle",
                      entity_id=jira or bundle.bundle_id, source="cli",
                      details={"domain": domain, "refs": bundle.item_count,
                               "resolved": bundle.resolved_count, "digest": bundle.digest})
    except Exception:  # noqa: BLE001 - never break on audit
        pass


@context_app.command(
    "trace",
    help="Show the context ledger for a session — what an agent actually read.",
)
def trace(
    session: Annotated[str, typer.Argument(help="Session / correlation id")],
    limit: Annotated[int, typer.Option("--limit", help="Max rows")] = 200,
) -> None:
    """Print every context read recorded under a session, oldest first.

    The read side of the KeelTrace sensors: retrieval that used to be invisible
    (MCP tool calls, and KG reads once they move behind the retriever seam) is
    recorded against the session's correlation id, so a run can be explained
    after the fact rather than guessed at.
    """
    import json as _json

    from agentic_cli import tracing

    rows = tracing.session_context(session, limit=limit)
    summary = tracing.session_summary(session, limit=limit)

    if not rows:
        console.print(
            f"[yellow]No context reads recorded for session [bold]{session}[/bold].[/yellow]"
        )
        console.print(
            "[dim]Either the session predates tracing, or its retrieval ran "
            "outside a session scope.[/dim]"
        )
        raise typer.Exit(0)

    table = Table(title=f"Context ledger — {session}", show_lines=False)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Source", style="cyan")
    table.add_column("Operation")
    table.add_column("Bytes", justify="right")
    table.add_column("ms", justify="right", style="dim")
    table.add_column("Status")

    for i, r in enumerate(rows, 1):
        details = r.get("details") or {}
        if isinstance(details, str):
            try:
                details = _json.loads(details)
            except (ValueError, TypeError):
                details = {}
        status = r.get("status") or ""
        ms = r.get("duration_ms")
        table.add_row(
            str(i),
            r.get("command") or "",
            r.get("subcommand") or "",
            f"{int(details.get('bytes') or 0):,}",
            "-" if ms is None else str(ms),   # 0 ms is a real value, not "unknown"
            "[green]ok[/green]" if status == "success" else f"[red]{status}[/red]",
        )

    console.print(table)

    parts = [
        f"[bold]{summary['reads']}[/bold] reads",
        f"[bold]{summary['bytes']:,}[/bold] bytes",
    ]
    if summary["errors"]:
        parts.append(f"[red]{summary['errors']} failed[/red]")
    by_source = ", ".join(
        f"{src} {v['reads']}×/{v['bytes']:,}B"
        for src, v in sorted(summary["by_source"].items())
    )
    console.print(Panel(
        "  ·  ".join(parts) + (f"\n[dim]{by_source}[/dim]" if by_source else ""),
        title="Context budget", expand=False,
    ))
