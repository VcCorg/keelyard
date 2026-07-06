"""Standalone ``devin`` command group — Knowledge + Sessions.

Reuses the self-contained ``agentic_cli.devin`` package so the whole Devin
integration is one reusable unit, decoupled from the KG/OKF commands.

    keel devin init                         configure defaults (key via $DEVIN_API_KEY)
    keel devin kg list|delete|move          manage Devin Knowledge entries
    keel devin sessions create|list|status|message
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

devin_app = typer.Typer(help="Devin Cloud integration — Knowledge & Sessions", rich_markup_mode=None)
console = Console()

kg_app = typer.Typer(help="Manage Devin Cloud Knowledge entries", rich_markup_mode=None)
sessions_app = typer.Typer(help="Create and follow Devin sessions", rich_markup_mode=None)
snapshots_app = typer.Typer(help="List per-domain snapshots and verify meta-repo drift", rich_markup_mode=None)
devin_app.add_typer(kg_app, name="kg")
devin_app.add_typer(sessions_app, name="sessions")
devin_app.add_typer(snapshots_app, name="snapshots")


def _require_key(api_key: str | None) -> None:
    from agentic_cli.devin.config import has_api_key, DEVIN_API_KEY_ENV

    if not has_api_key(api_key):
        console.print(f"[red]\u2717[/red] No Devin API key. Set [cyan]${DEVIN_API_KEY_ENV}[/cyan] "
                      f"or pass [cyan]--api-key[/cyan].")
        raise typer.Exit(1)


# ── init ─────────────────────────────────────────────────────────────────────

def configure_devin(
    base_url: str | None = None,
    max_acu: int | None = None,
    domain: str | None = None,
    snapshot_id: str | None = None,
    playbook_id: str | None = None,
    knowledge_folder: str | None = None,
) -> None:
    """Persist Devin defaults to the shared CLI config and print a summary.

    Single source of truth shared by ``keel devin init`` and ``keel init devin``.
    The API key is NEVER stored — it is read from ``$DEVIN_API_KEY`` at call time.
    """
    from agentic_cli.devin.config import DevinConfig, has_api_key, DEVIN_API_KEY_ENV

    cfg = DevinConfig.load()
    if base_url:
        cfg.base_url = base_url
    if max_acu is not None:
        cfg.default_max_acu = max_acu
    if domain:
        cfg.set_domain(domain, snapshot_id=snapshot_id, playbook_id=playbook_id,
                       knowledge_folder=knowledge_folder)
    cfg.save()

    console.print("[bold green]\u2713[/bold green] Saved Devin config")
    console.print(f"  base_url        = [cyan]{cfg.base_url}[/cyan]")
    console.print(f"  default_max_acu = [cyan]{cfg.default_max_acu}[/cyan]")
    if domain:
        console.print(f"  domain '{domain}': [cyan]{cfg.domain(domain)}[/cyan]")
    state = "present" if has_api_key() else "[yellow]missing[/yellow]"
    console.print(f"  ${DEVIN_API_KEY_ENV}: {state}")


@devin_app.command("init")
def devin_init(
    base_url: Annotated[str | None, typer.Option("--base-url", help="Devin API base URL")] = None,
    max_acu: Annotated[int | None, typer.Option("--max-acu", help="Default per-session ACU ceiling")] = None,
    domain: Annotated[str | None, typer.Option("--domain", help="Configure per-domain defaults for this slug")] = None,
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id", help="Machine snapshot id for the domain")] = None,
    playbook_id: Annotated[str | None, typer.Option("--playbook-id", help="Playbook id for the domain")] = None,
    knowledge_folder: Annotated[str | None, typer.Option("--knowledge-folder", help="Devin folder name for the domain")] = None,
) -> None:
    """Configure Devin defaults. The API key is NEVER stored — set $DEVIN_API_KEY."""
    configure_devin(base_url=base_url, max_acu=max_acu, domain=domain,
                    snapshot_id=snapshot_id, playbook_id=playbook_id,
                    knowledge_folder=knowledge_folder)


# ── kg: knowledge management ─────────────────────────────────────────────────

@kg_app.command("list")
def kg_list(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    folder: Annotated[str | None, typer.Option("--folder", help="Filter to a folder name")] = None,
) -> None:
    """List all Devin Knowledge entries and folders."""
    from agentic_cli.devin import list_entries, DevinError

    _require_key(api_key)
    try:
        data = list_entries(api_key=api_key)
    except (DevinError, Exception) as exc:  # noqa: BLE001
        console.print(f"[red]\u2717[/red] {exc}")
        raise typer.Exit(1)
    folders = data.get("folders", [])
    knowledge = data.get("knowledge", [])
    by_id = {f.get("id"): f.get("name") for f in folders}
    fid = next((f.get("id") for f in folders if f.get("name") == folder), None) if folder else None

    console.print(f"[bold]Folders[/bold] ({len(folders)}): " +
                  (", ".join(f.get("name", "?") for f in folders) or "(none)"))
    table = Table(title="Devin Knowledge")
    table.add_column("Name", style="cyan", max_width=50)
    table.add_column("Folder", style="green")
    table.add_column("Repo", style="magenta")
    table.add_column("ID", style="dim")
    n = 0
    for k in knowledge:
        if fid and k.get("parent_folder_id") != fid:
            continue
        table.add_row(k.get("name", "?"), by_id.get(k.get("parent_folder_id"), "-"),
                      k.get("pinned_repo") or "-", k.get("id", "?"))
        n += 1
    console.print(table)
    console.print(f"  {n} entr{'y' if n == 1 else 'ies'}.")


@kg_app.command("delete")
def kg_delete(
    ids: Annotated[list[str], typer.Argument(help="Knowledge entry id(s) to delete")],
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
) -> None:
    """Delete one or more Devin Knowledge entries by id."""
    from agentic_cli.devin import delete_entries

    _require_key(api_key)
    deleted, failed = delete_entries(ids, api_key=api_key)
    console.print(f"[green]\u2713[/green] deleted={len(deleted)} failed={len(failed)}")
    for fid, err in failed:
        console.print(f"  [red]{fid}[/red]: {err}")
    if failed:
        raise typer.Exit(1)


@kg_app.command("move")
def kg_move(
    note_id: Annotated[str, typer.Argument(help="Knowledge entry id")],
    folder_id: Annotated[str | None, typer.Option("--folder-id", help="Target folder id (omit for root)")] = None,
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
) -> None:
    """Move a Knowledge entry to a folder (or root)."""
    from agentic_cli.devin import move_entry

    _require_key(api_key)
    move_entry(note_id, folder_id, api_key=api_key)
    console.print(f"[green]\u2713[/green] moved {note_id} -> {folder_id or 'root'}")


# ── sessions ─────────────────────────────────────────────────────────────────

def _knowledge_ids_from_sync(bundle: Path | None, feature: str = "") -> list[str]:
    """Read concept->knowledge id mappings from a bundle's ``.devin-sync.json``."""
    if not bundle:
        return []
    from agentic_cli.kg.okf.devin import load_sync

    sync = load_sync(bundle)
    ids: list[str] = []
    for cid, rec in sync.items():
        if feature and f"/{feature}/" not in f"/{cid}/":
            continue
        kid = rec.get("id")
        if kid:
            ids.append(kid)
    return ids


@sessions_app.command("create")
def sessions_create(
    prompt: Annotated[str | None, typer.Option("--prompt", help="Task prompt for Devin")] = None,
    title: Annotated[str, typer.Option("--title")] = "",
    domain: Annotated[str | None, typer.Option("--domain", help="Apply per-domain defaults (snapshot/playbook/folder)")] = None,
    jira: Annotated[str, typer.Option("--jira", help="Jira key for provenance/tagging")] = "",
    bundle: Annotated[Path | None, typer.Option("--bundle", help="OKF bundle dir for --knowledge-from-sync")] = None,
    knowledge_from_sync: Annotated[bool, typer.Option("--knowledge-from-sync", help="Attach knowledge_ids from <bundle>/.devin-sync.json")] = False,
    knowledge_id: Annotated[list[str] | None, typer.Option("--knowledge-id", help="Explicit knowledge id(s) to attach")] = None,
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    playbook_id: Annotated[str | None, typer.Option("--playbook-id")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Extra tag(s)")] = None,
    max_acu: Annotated[int | None, typer.Option("--max-acu", help="ACU ceiling (defaults from config)")] = None,
    idempotent: Annotated[bool, typer.Option("--idempotent", help="Reuse a tracked live session with the same prompt")] = False,
    unlisted: Annotated[bool, typer.Option("--unlisted")] = False,
    watch: Annotated[bool, typer.Option("--watch", help="Poll until the session reaches a terminal state")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print the payload without calling the API")] = False,
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
) -> None:
    """Create (trigger) a Devin session, optionally grounded in OKF knowledge."""
    from agentic_cli.devin import SessionSpec, create_session, DevinError
    from agentic_cli.devin.config import DevinConfig

    if not prompt:
        console.print("[red]\u2717[/red] --prompt is required.")
        raise typer.Exit(1)

    cfg = DevinConfig.load()
    dconf = cfg.domain(domain) if domain else {}

    kids: list[str] = list(knowledge_id or [])
    if knowledge_from_sync:
        kids += _knowledge_ids_from_sync(bundle)
    tags = ["keel"] + ([domain] if domain else []) + ([jira] if jira else []) + list(tag or [])

    spec = SessionSpec(
        prompt=prompt,
        title=title or (f"{domain or 'devin'} \u00b7 {jira}".strip(" \u00b7")),
        snapshot_id=snapshot_id or dconf.get("snapshot_id"),
        playbook_id=playbook_id or dconf.get("playbook_id"),
        knowledge_ids=sorted(set(kids)),
        tags=sorted(set(tags)),
        idempotent=idempotent,
        max_acu_limit=max_acu if max_acu is not None else cfg.default_max_acu,
        unlisted=unlisted,
        domain=domain or "",
        jira=jira,
    )

    if dry_run:
        console.print("[bold]Devin session payload (dry-run)[/bold]:")
        console.print_json(json.dumps(spec.to_payload()))
        return

    _require_key(api_key)
    try:
        res = create_session(spec, api_key=api_key, base_url=cfg.base_url)
    except (DevinError, Exception) as exc:  # noqa: BLE001
        console.print(f"[red]\u2717[/red] {exc}")
        raise typer.Exit(1)

    tag_note = " [yellow](reused tracked session)[/yellow]" if res.reused_local else ""
    console.print(f"[bold green]\u2713[/bold green] session [cyan]{res.session_id}[/cyan]{tag_note}")
    if res.url:
        console.print(f"  {res.url}")
    if spec.knowledge_ids:
        n = len(spec.knowledge_ids)
        console.print(f"  attached {n} knowledge entr{'y' if n == 1 else 'ies'}")

    if watch and res.session_id:
        _watch(res.session_id, api_key, cfg.base_url)


def _watch(session_id: str, api_key: str | None, base_url: str) -> None:
    from agentic_cli.devin import poll_session

    console.print("  [dim]watching\u2026 (Ctrl-C to stop)[/dim]")

    def on_update(status: str | None) -> None:
        console.print(f"  status: [cyan]{status or '?'}[/cyan]")

    try:
        final = poll_session(session_id, api_key=api_key, base_url=base_url, on_update=on_update)
    except KeyboardInterrupt:
        console.print("  [yellow]stopped watching[/yellow]")
        return
    console.print(f"[bold green]\u2713[/bold green] terminal status: [cyan]{final.status}[/cyan]")
    if final.structured_output:
        console.print_json(json.dumps(final.structured_output))


@sessions_app.command("list")
def sessions_list(
    local: Annotated[bool, typer.Option("--local", help="Show only locally-tracked sessions (no API call)")] = False,
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
) -> None:
    """List Devin sessions (locally-tracked, or live from the API)."""
    from agentic_cli.devin import list_local, list_sessions, DevinError

    table = Table(title="Devin sessions")
    table.add_column("Session", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Title/Domain", style="green")
    table.add_column("URL", style="dim")

    if local:
        rows = list_local()
        for r in rows:
            table.add_row(r.get("session_id", "?"), r.get("last_status") or "-",
                          r.get("title") or r.get("domain") or "-", r.get("url") or "-")
        console.print(table)
        console.print(f"  {len(rows)} tracked session(s).")
        return

    _require_key(api_key)
    try:
        data = list_sessions(api_key=api_key)
    except (DevinError, Exception) as exc:  # noqa: BLE001
        console.print(f"[red]\u2717[/red] {exc}")
        raise typer.Exit(1)
    items = data.get("sessions", data if isinstance(data, list) else [])
    for s in items:
        table.add_row(s.get("session_id") or s.get("id", "?"),
                      s.get("status_enum") or s.get("status") or "-",
                      s.get("title") or "-", s.get("url") or "-")
    console.print(table)
    console.print(f"  {len(items)} session(s).")


@sessions_app.command("status")
def sessions_status(
    session_id: Annotated[str, typer.Argument(help="Devin session id")],
    watch: Annotated[bool, typer.Option("--watch")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Print raw JSON")] = False,
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
) -> None:
    """Show a session's current status and structured output."""
    from agentic_cli.devin import get_session, DevinError
    from agentic_cli.devin.config import DevinConfig

    _require_key(api_key)
    cfg = DevinConfig.load()
    if watch:
        _watch(session_id, api_key, cfg.base_url)
        return
    try:
        res = get_session(session_id, api_key=api_key, base_url=cfg.base_url)
    except (DevinError, Exception) as exc:  # noqa: BLE001
        console.print(f"[red]\u2717[/red] {exc}")
        raise typer.Exit(1)
    if json_out:
        console.print_json(json.dumps(res.payload))
        return
    console.print(f"[bold]{session_id}[/bold]  status: [cyan]{res.status}[/cyan]")
    if res.url:
        console.print(f"  {res.url}")
    if res.structured_output:
        console.print("  [bold]structured_output[/bold]:")
        console.print_json(json.dumps(res.structured_output))


@sessions_app.command("message")
def sessions_message(
    session_id: Annotated[str, typer.Argument(help="Devin session id")],
    message: Annotated[str, typer.Argument(help="Message to send")],
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
) -> None:
    """Send a follow-up message to a running session."""
    from agentic_cli.devin import send_message, DevinError
    from agentic_cli.devin.config import DevinConfig

    _require_key(api_key)
    cfg = DevinConfig.load()
    try:
        send_message(session_id, message, api_key=api_key, base_url=cfg.base_url)
    except (DevinError, Exception) as exc:  # noqa: BLE001
        console.print(f"[red]\u2717[/red] {exc}")
        raise typer.Exit(1)
    console.print(f"[green]\u2713[/green] sent message to {session_id}")


# ── snapshots ────────────────────────────────────────────────────────────────

_STATE_STYLE = {
    "ok": "green",
    "drift": "yellow",
    "no-snapshot": "dim",
    "meta-missing": "red",
    "unverifiable": "dim",
}


def _state_label(state: str) -> str:
    return f"[{_STATE_STYLE.get(state, 'white')}]{state}[/]"


@snapshots_app.command("list")
def snapshots_list(
    json_out: Annotated[bool, typer.Option("--json", help="Print raw JSON")] = False,
) -> None:
    """List locally-registered per-domain Devin snapshots and their drift state.

    Reads the shared CLI config (no network). For each domain that has a
    ``snapshot_id`` it also checks whether the meta-repo has changed since the
    snapshot was built (see ``snapshots verify`` for details).
    """
    from agentic_cli.devin.snapshots import list_snapshots

    statuses = list_snapshots()
    if json_out:
        console.print_json(json.dumps([s.__dict__ for s in statuses]))
        return
    if not statuses:
        console.print("[dim]No domains configured. Build one: keel domain build-snapshot <slug>[/dim]")
        return

    table = Table(title="Devin snapshots (per domain)")
    table.add_column("Domain", style="cyan")
    table.add_column("Snapshot ID", style="green")
    table.add_column("State")
    table.add_column("Meta-repo commit", style="dim")
    table.add_column("Built at", style="dim")
    table.add_column("Knowledge folder", style="magenta")

    n_snap = 0
    for s in statuses:
        if s.snapshot_id:
            n_snap += 1
        if s.state == "drift" and s.recorded_sha:
            commit = f"{s.recorded_sha} → {s.current_sha or '?'}"
        else:
            commit = s.recorded_sha or "-"
        table.add_row(
            s.domain,
            s.snapshot_id or "-",
            _state_label(s.state),
            commit,
            (s.built_at or "-")[:19],
            s.knowledge_folder or "-",
        )
    console.print(table)
    console.print(f"  {n_snap} snapshot(s) across {len(statuses)} domain(s).")
    stale = [s.domain for s in statuses if s.state in ("drift", "meta-missing")]
    if stale:
        console.print(f"  [yellow]⚠ needs attention:[/yellow] {', '.join(stale)} "
                      f"([dim]keel devin snapshots verify <domain>[/dim])")


@snapshots_app.command("verify")
def snapshots_verify(
    domain: Annotated[str | None, typer.Argument(help="Domain slug (omit to verify all)")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Print raw JSON")] = False,
) -> None:
    """Verify snapshot(s) against their meta-repo and report drift.

    Exits non-zero if any snapshot is stale (meta-repo changed since build) or
    its meta-repo/blueprint is missing — handy for CI and pre-session checks.
    """
    from agentic_cli.devin.snapshots import (
        verify_snapshot, list_snapshots, STATE_DRIFT, STATE_META_MISSING,
    )

    statuses = [verify_snapshot(domain)] if domain else list_snapshots()
    if json_out:
        console.print_json(json.dumps([s.__dict__ for s in statuses]))
    else:
        if not statuses:
            console.print("[dim]No domains configured.[/dim]")
            return
        for s in statuses:
            console.print(f"{_state_label(s.state)} [cyan]{s.domain}[/cyan] "
                          f"{('· ' + s.snapshot_id) if s.snapshot_id else ''}")
            console.print(f"    {s.detail}")

    bad = [s for s in statuses if s.state in (STATE_DRIFT, STATE_META_MISSING)]
    if bad:
        raise typer.Exit(1)
