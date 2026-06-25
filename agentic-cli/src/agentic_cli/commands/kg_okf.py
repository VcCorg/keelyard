"""`dva kg okf` — Open Knowledge Format bundle commands.

The OKF bundle is a directory of Markdown concept files governed by an
okf.schema.yaml contract. It is the source of truth for the KG; Neo4j/LightRAG
are optional derived projections.

Commands:
  init      scaffold a new bundle (canonical schema + index)
  export    build a bundle from an already-ingested Neo4j domain (no reindex)
  validate  check conformance against the schema
  trace     show FREQ dev/QA traceability (+ coverage gaps)
  push-devin push bundle concepts to Devin Cloud Knowledge (idempotent)
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

okf_app = typer.Typer(help="Open Knowledge Format (OKF) bundle commands", rich_markup_mode=None)
console = Console()

# Default bundle location for a domain slug.
def _default_bundle_dir(domain: str) -> Path:
    from agentic_cli.config import CLI_NAME  # noqa: F401
    base = Path.cwd()
    # Prefer the conventional skills/domains/<slug>/knowledge path if present.
    candidate = base / "skills" / "domains" / domain / "knowledge"
    return candidate


@okf_app.command()
def init(
    domain: Annotated[str, typer.Option("--domain", help="Domain slug, e.g. cwow-facility")],
    product: Annotated[str, typer.Option("--product", help="Product name")] = "",
    out: Annotated[Path | None, typer.Option("--out", help="Output bundle directory")] = None,
) -> None:
    """Scaffold a new OKF bundle with the canonical schema."""
    from agentic_cli.kg.okf.schema import OKFSchema

    out_dir = out or _default_bundle_dir(domain)
    out_dir = Path(out_dir)
    schema_path = out_dir / "okf.schema.yaml"
    if schema_path.exists():
        console.print(f"[yellow]Bundle already exists at[/yellow] {out_dir}")
        raise typer.Exit(1)
    (out_dir / "features").mkdir(parents=True, exist_ok=True)
    OKFSchema.canonical(domain=domain, product=product).dump(schema_path)
    # OKF §6/§9: index.md is a directory listing with NO frontmatter; the bundle
    # root MAY carry only `okf_version`. Concept IDs derive from file paths (§2).
    (out_dir / "index.md").write_text(
        f"---\nokf_version: '0.1'\n---\n\n# {domain} — OKF Knowledge Bundle\n\n"
        f"Product: {product or domain}.\n\n# Sections\n\n"
        "* [features/](features/) - feature-grouped concept directories\n",
        encoding="utf-8",
    )
    console.print(f"[bold green]✓[/bold green] Initialized OKF bundle at [cyan]{out_dir}[/cyan]")
    console.print(f"  schema:  {schema_path}")
    console.print("  next:    add concepts, then run [cyan]dva kg okf validate[/cyan]")


@okf_app.command()
def export(
    domain: Annotated[str, typer.Option("--domain", help="Domain slug to export from Neo4j")],
    out: Annotated[Path | None, typer.Option("--out", help="Output bundle directory")] = None,
    product: Annotated[str, typer.Option("--product", help="Product name")] = "",
    mint_freqs: Annotated[bool, typer.Option("--mint-freqs/--no-mint-freqs",
                          help="Mint FREQ concepts from CWOW-NNNNNN in requirement content")] = True,
    validate_after: Annotated[bool, typer.Option("--validate/--no-validate",
                              help="Validate the bundle after export")] = True,
) -> None:
    """Build an OKF bundle from an already-ingested Neo4j domain (no re-indexing).

    Reads the existing domain subgraph and maps it onto the canonical OKF schema
    (hybrid: unknown labels/rels are quarantined under review). Does NOT touch or
    re-ingest the graph.
    """
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.okf.exporter import export_domain

    config = KGConfig.load()
    if not config.is_neo4j_configured():
        console.print("[red]✗[/red] Neo4j is not configured. Run [cyan]dva kg init[/cyan] first.")
        raise typer.Exit(1)

    out_dir = Path(out or _default_bundle_dir(domain))
    console.print(f"[bold]Exporting domain[/bold] [cyan]{domain}[/cyan] -> {out_dir}")
    try:
        result = export_domain(
            domain=domain, out_dir=out_dir, product=product,
            mint_freqs=mint_freqs, config=config,
        )
    except Exception as e:  # surface connection/query errors cleanly
        console.print(f"[red]✗ Export failed:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title=f"OKF export — {domain}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Concepts", str(result.concepts))
    table.add_row("Typed edges", str(result.edges_typed))
    table.add_row("Minted FREQs", str(result.minted_freqs))
    table.add_row("Unmapped labels", str(len(result.unmapped_labels)))
    table.add_row("Unmapped rel types", str(len(result.unmapped_rels)))
    table.add_row("Quarantined triples", str(len(result.quarantined_triples)))
    table.add_row("Skipped edges", str(result.skipped_edges))
    console.print(table)
    console.print(f"  bundle: [cyan]{out_dir}[/cyan]")
    console.print(f"  report: [cyan]{out_dir / 'nonconforming-report.md'}[/cyan]")

    if validate_after:
        console.print("\n[bold]Validating exported bundle...[/bold]")
        _run_validate(out_dir)


@okf_app.command()
def enrich(
    domain: Annotated[str, typer.Option("--domain", help="Domain slug; resolves all paths from registered domain data")],
    source: Annotated[str, typer.Option("--source", help="Source: code, confluence, both")] = "both",
    model: Annotated[str | None, typer.Option("--model", help="Vertex AI model (default: gemini-2.5-flash-lite)")] = None,
    no_confluence: Annotated[bool, typer.Option("--no-confluence", help="Skip the Confluence enrichment pass")] = False,
    concept: Annotated[list[str] | None, typer.Option("--concept", help="Enrich only this concept id (repeatable)")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show planned concepts/pages without writing or calling the model")] = False,
    validate_after: Annotated[bool, typer.Option("--validate/--no-validate", help="Validate the bundle after enrichment")] = True,
) -> None:
    """Enrich (or generate) an OKF bundle using the LLM enrichment agent.

    Two passes, following the GCP OKF enrichment agent:
      1. structural — one OKF doc per concept advertised by the source
      2. enrichment — augment docs from tracked Confluence pages (never shrinking
         structured sections)

    ALL inputs are resolved from registered domain data (repos, docs, confluence,
    product) — there are no manual path flags. Register them first with
    `dva domain create`, `dva domain link-repo`, and `dva domain add-docs`.
    """
    from agentic_cli.kg.okf.enrichment.domain_paths import resolve_domain_enrichment_context
    from agentic_cli.kg.okf.enrichment.runner import EnrichmentRunner
    from agentic_cli.kg.okf.enrichment.sources.code import CodebaseSource
    from agentic_cli.kg.okf.enrichment.sources.confluence import ConfluenceSource
    from agentic_cli.tracker import record_activity

    source = source.lower().strip()
    if source not in ("code", "confluence", "both"):
        console.print(f"[red]✗[/red] Unknown --source '{source}'. Use code, confluence, or both.")
        raise typer.Exit(1)

    try:
        ctx = resolve_domain_enrichment_context(domain)
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    bundle_dir = ctx.bundle_dir
    console.print(f"[bold]OKF enrich[/bold] [cyan]{domain}[/cyan] -> {bundle_dir}")
    console.print(
        f"  resolved from domain: "
        f"{len(ctx.codebase_paths)} repo path(s), "
        f"{len(ctx.confluence_page_ids)} confluence doc(s), "
        f"product={ctx.product or '—'}"
    )
    if ctx.unresolved_repos:
        console.print(
            f"  [yellow]![/yellow] {len(ctx.unresolved_repos)} linked repo(s) not onboarded/"
            f"found on disk and skipped: {', '.join(ctx.unresolved_repos)}"
        )

    # Build the structural source.
    code_src = None
    if source in ("code", "both"):
        if not ctx.codebase_paths:
            if source == "code":
                console.print("[red]✗[/red] No onboarded repo paths for this domain. Onboard a repo first.")
                raise typer.Exit(1)
        else:
            # Enrich from the first resolved repo (primary). Multi-repo handled per-call.
            code_src = CodebaseSource(ctx.codebase_paths[0])

    confluence_src = None
    if source in ("confluence", "both") and not no_confluence:
        if ctx.confluence_docs:
            confluence_src = ConfluenceSource.from_domain_docs(ctx.confluence_docs)
        elif source == "confluence":
            console.print("[red]✗[/red] No tracked Confluence docs for this domain. Run `dva domain add-docs` first.")
            raise typer.Exit(1)

    if code_src is None and confluence_src is None:
        console.print("[red]✗[/red] Nothing to enrich — no code source and no Confluence docs resolved.")
        raise typer.Exit(1)

    # Ensure the bundle has a canonical schema (enrich may generate from scratch).
    if not dry_run:
        from agentic_cli.kg.okf.schema import OKFSchema
        schema_path = bundle_dir / "okf.schema.yaml"
        if not schema_path.exists():
            bundle_dir.mkdir(parents=True, exist_ok=True)
            OKFSchema.canonical(domain=domain, product=ctx.product).dump(schema_path)
            console.print(f"  scaffolded schema: [cyan]{schema_path}[/cyan]")

    # If a code source exists, it is the structural pass and Confluence is the
    # enrichment pass. If there is no code source, Confluence becomes the
    # structural pass and there is no separate enrichment pass.
    if code_src is not None:
        structural_source = code_src
        enrichment_confluence = confluence_src
    else:
        structural_source = confluence_src
        enrichment_confluence = None

    runner = EnrichmentRunner(
        source=structural_source,
        bundle_root=bundle_dir,
        model_name=model,
        confluence_source=enrichment_confluence,
        dry_run=dry_run,
    )

    only = [tuple(c.strip().strip("/").split("/")) for c in concept] if concept else None

    try:
        result = runner.enrich_all(only=only)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ Enrichment failed:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title=f"OKF enrich — {domain}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Concepts written", str(result.concepts_written))
    table.add_row("Concepts enriched", str(result.concepts_enriched))
    table.add_row("Confluence pages", str(result.pages_processed))
    table.add_row("Skipped pages", str(result.skipped))
    table.add_row("Guard blocks", str(result.guard_blocks))
    table.add_row("Errors", str(len(result.errors)))
    console.print(table)

    if dry_run:
        console.print("\n[dim](dry run — planned work)[/dim]")
        for item in result.planned[:100]:
            console.print(f"  [yellow]→[/yellow] {item}")
        return

    for err in result.errors[:50]:
        console.print(f"  [red]x[/red] {err}")

    console.print(f"  bundle: [cyan]{bundle_dir}[/cyan]")

    record_activity(
        command="kg", subcommand="okf-enrich",
        args={"domain": domain, "source": source, "model": model},
        details={
            "written": result.concepts_written,
            "enriched": result.concepts_enriched,
            "pages": result.pages_processed,
        },
    )

    if validate_after and not dry_run:
        console.print("\n[bold]Validating enriched bundle...[/bold]")
        _run_validate(bundle_dir)


@okf_app.command()
def visualize(
    domain: Annotated[str | None, typer.Option("--domain", help="Domain slug (resolves bundle from domain data)")] = None,
    bundle: Annotated[Path | None, typer.Option("--bundle", help="Bundle directory (overrides --domain)")] = None,
    out: Annotated[Path | None, typer.Option("--out", help="Output HTML path (default: <bundle>/viz.html)")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Graph title")] = None,
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="Open the result in a browser")] = False,
) -> None:
    """Render an OKF bundle as an interactive Cytoscape.js graph (self-contained HTML).

    Resolve the bundle from a registered domain (`--domain`) or point at it
    directly (`--bundle`). Nodes are concepts colored by type; edges are typed
    links from concept bodies.
    """
    from agentic_cli.kg.okf.visualize import build_graph, write_html

    if bundle is not None:
        bundle_dir = Path(bundle)
    elif domain:
        from agentic_cli.kg.okf.enrichment.domain_paths import default_bundle_dir
        bundle_dir = default_bundle_dir(domain)
    else:
        console.print("[red]✗[/red] Provide --domain or --bundle.")
        raise typer.Exit(1)

    if not bundle_dir.exists():
        console.print(f"[red]✗[/red] Bundle not found: {bundle_dir}")
        raise typer.Exit(1)

    graph = build_graph(bundle_dir)
    if graph.node_count == 0:
        console.print(f"[yellow]![/yellow] No concepts found in {bundle_dir}.")
        raise typer.Exit(1)

    out_path = write_html(
        bundle_dir, out=out,
        title=title or f"{domain or bundle_dir.name} — OKF Knowledge Graph",
    )

    table = Table(title="OKF visualize")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Concepts (nodes)", str(graph.node_count))
    table.add_row("Typed links (edges)", str(graph.edge_count))
    table.add_row("Concept types", str(len(graph.type_counts)))
    console.print(table)
    console.print(f"  graph: [cyan]{out_path}[/cyan]")

    if open_browser:
        import webbrowser
        webbrowser.open(out_path.resolve().as_uri())


@okf_app.command()
def validate(
    bundle: Annotated[Path, typer.Argument(help="Bundle directory")] = Path("."),
) -> None:
    """Validate an OKF bundle against its okf.schema.yaml."""
    raise typer.Exit(0 if _run_validate(Path(bundle)) else 1)


def _run_validate(bundle: Path) -> bool:
    from agentic_cli.kg.okf.validate import validate_bundle

    try:
        rep = validate_bundle(bundle)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        return False

    console.print(f"  concepts: {rep.concepts}   links: {rep.links} ({rep.typed_links} typed)")
    for w in rep.warnings:
        console.print(f"  [yellow]![/yellow] {w}")
    if rep.errors:
        console.print(f"\n[bold red]VIOLATIONS: {len(rep.errors)}[/bold red]")
        for e in rep.errors[:200]:
            console.print(f"  [red]x[/red] {e}")
        console.print("\n[bold red]FAIL[/bold red]")
        return False
    console.print("\n[bold green]PASS — bundle is conformant.[/bold green]")
    return True


@okf_app.command()
def trace(
    bundle: Annotated[Path, typer.Argument(help="Bundle directory")] = Path("."),
    freq: Annotated[str | None, typer.Option("--freq", help="Filter to one FREQ id, e.g. CWOW-301456")] = None,
    gaps: Annotated[bool, typer.Option("--gaps", help="Exit non-zero if any FREQ lacks code/test coverage")] = False,
    hydrate: Annotated[bool, typer.Option("--hydrate", help="Resolve transient Jira status live via Jira MCP")] = False,
) -> None:
    """Show FREQ dev/QA traceability and coverage gaps."""
    from agentic_cli.kg.okf.trace import trace_bundle

    try:
        report = trace_bundle(Path(bundle), only_freq=freq)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if not report.freqs:
        console.print("[yellow]No matching FREQ concepts found.[/yellow]")
        raise typer.Exit(1)

    for f in report.freqs:
        console.print(f"\n[bold]{f.freq_id}[/bold]  {f.title}")
        console.print(f"  jira: {f.jira or '-'}")
        status = "(live via Jira MCP — run with --hydrate)" if not hydrate else \
                 "(--hydrate: resolve via mcp0_jira_get_issue at runtime)"
        console.print(f"  status [transient]: {status}")
        console.print(f"  part-of:    {', '.join(f.part_of) or '-'}")
        console.print(f"  references: {', '.join(f.references) or '-'}")
        console.print("  [DEV] implemented by:")
        if f.implemented_by:
            for title, res in f.implemented_by:
                console.print(f"     - {title}  ({res})")
        else:
            console.print("     - [red](none) DEV GAP[/red]")
        console.print("  [QA] verified by:")
        if f.tested_by:
            for title, res in f.tested_by:
                console.print(f"     - {title}  ({res})")
        else:
            console.print("     - [red](none) QA GAP[/red]")
        if f.acceptance_criteria:
            console.print(f"  [QA] acceptance criteria ({len(f.acceptance_criteria)}):")
            for ac in f.acceptance_criteria:
                console.print(f"     - {ac}")

    console.print(f"\nFREQs: {len(report.freqs)}   coverage gaps: {report.gap_count}")
    if gaps and report.gap_count:
        raise typer.Exit(1)


def _resolve_bundle(domain: str | None, source: str, bundle: Path | None) -> Path:
    """Resolve the bundle directory from --bundle, or --domain + --source."""
    if bundle is not None:
        return Path(bundle)
    if not domain:
        console.print("[red]✗[/red] Provide either --bundle <dir> or --domain <slug>.")
        raise typer.Exit(1)
    if source == "export":
        return Path.cwd() / "knowledge-export" / domain
    return _default_bundle_dir(domain)


def _derive_folder_name(domain: str | None, bundle_dir: Path,
                        folder_name: str | None, folder_id: str | None, no_folder: bool) -> str | None:
    """Default folder name to '<domain>-okf' unless an id/--no-folder is given."""
    from agentic_cli.kg.okf.bundle import Bundle
    from agentic_cli.kg.okf.devin import bundle_domain, default_folder_name

    if no_folder:
        return None
    if folder_name:
        return folder_name
    if folder_id:
        return None  # explicit id wins
    dom = domain or bundle_domain(Bundle.load(bundle_dir))
    return default_folder_name(dom) or None


@okf_app.command("push-devin")
def push_devin(
    domain: Annotated[str | None, typer.Option("--domain", help="Domain slug, e.g. cwow-facility")] = None,
    source: Annotated[str, typer.Option("--source", help="Bundle source: 'export' or 'authored'")] = "export",
    bundle: Annotated[Path | None, typer.Option("--bundle", help="Explicit bundle dir (overrides --domain)")] = None,
    types: Annotated[str, typer.Option("--types", help="Comma-separated concept types to push")] = "FREQ,Requirement",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Render payloads to <bundle>/devin/ without calling the API")] = False,
    api_key: Annotated[str | None, typer.Option("--api-key", help="Devin API key (else $DEVIN_API_KEY)")] = None,
    folder: Annotated[str | None, typer.Option("--folder", help="Devin parent_folder_id (explicit id)")] = None,
    folder_name: Annotated[str | None, typer.Option("--folder-name", help="Devin folder NAME to place entries in (default '<domain>-okf'; must already exist in Devin)")] = None,
    no_folder: Annotated[bool, typer.Option("--no-folder", help="Push to the Knowledge root instead of a folder")] = False,
    folder_by_feature: Annotated[bool, typer.Option("--folder-by-feature", help="Place each entry in a per-feature folder '<domain>-<freq>' (must already exist in Devin)")] = False,
    release: Annotated[str, typer.Option("--release", help="Release/version label stamped in each entry footer")] = "",
    no_skip: Annotated[bool, typer.Option("--no-skip-unchanged", help="Re-send entries even if unchanged")] = False,
    no_validate: Annotated[bool, typer.Option("--no-validate", help="Skip the pre-push validation gate")] = False,
) -> None:
    """Push OKF concepts to Devin Cloud Knowledge (idempotent, versioned).

    Only STABLE knowledge is pushed; transient Jira state is never sent. A
    ``.devin-sync.json`` map records concept->{id,version,hash,folder} so re-runs
    skip unchanged entries, bump versions on change, and never duplicate.

    Entries are placed in a Devin folder named ``<domain>-okf`` by default. The
    Devin API CANNOT create folders, so create it once in the Devin UI first (or
    pass ``--no-folder`` to use the root). Use ``--dry-run`` to preview payloads.
    """
    from agentic_cli.kg.okf.devin import push_bundle, resolve_api_key

    bundle_dir = _resolve_bundle(domain, source, bundle)
    if not (bundle_dir / "okf.schema.yaml").exists():
        console.print(f"[red]✗[/red] No OKF bundle at [cyan]{bundle_dir}[/cyan] (missing okf.schema.yaml).")
        raise typer.Exit(1)

    type_tuple = tuple(t.strip() for t in types.split(",") if t.strip())
    if folder_by_feature:
        resolved_folder_name = None
        target = "per-feature folders '<domain>-<freq>'"
    else:
        resolved_folder_name = _derive_folder_name(domain, bundle_dir, folder_name, folder, no_folder)
        target = f"folder='{resolved_folder_name}'" if resolved_folder_name else (f"folder_id={folder}" if folder else "root")
    console.print(f"[bold]Devin push[/bold] {'(dry-run) ' if dry_run else ''}"
                  f"bundle=[cyan]{bundle_dir}[/cyan] types={','.join(type_tuple)} -> {target}")

    if not dry_run and not resolve_api_key(api_key):
        console.print("[red]✗[/red] No Devin API key. Set [cyan]$DEVIN_API_KEY[/cyan] or pass --api-key, "
                      "or use [cyan]--dry-run[/cyan] to preview payloads.")
        raise typer.Exit(1)

    try:
        result = push_bundle(
            bundle_dir, api_key=api_key, types=type_tuple, dry_run=dry_run,
            parent_folder_id=folder, folder_name=resolved_folder_name,
            folder_by_feature=folder_by_feature, release=release,
            skip_unchanged=not no_skip, validate_first=not no_validate,
        )
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if dry_run:
        console.print(f"[bold green]✓[/bold green] Wrote {len(result.entries)} payload(s) to "
                      f"[cyan]{result.out_dir}[/cyan]")
        table = Table(title="Planned Devin Knowledge entries")
        table.add_column("Concept", style="cyan")
        table.add_column("Action", style="yellow")
        table.add_column("Folder", style="magenta")
        table.add_column("Pinned repo", style="green")
        for e in result.entries:
            action = ("skip" if e.concept_id in result.skipped else
                      "update" if e.concept_id in result.updated else "create")
            table.add_row(e.concept_id, action, e.folder_name or "-", e.pinned_repo or "-")
        console.print(table)
        if folder_by_feature:
            folders_needed = sorted({e.folder_name for e in result.entries if e.folder_name})
            console.print(f"  feature folders required ({len(folders_needed)}): "
                          f"[magenta]{', '.join(folders_needed)}[/magenta]")
            console.print("  create any missing folders in the Devin UI before a live push.")
        console.print("  next: review payloads, then re-run without --dry-run (with $DEVIN_API_KEY set).")
        return

    console.print(f"[bold green]✓[/bold green] created={len(result.created)} "
                  f"updated={len(result.updated)} skipped={len(result.skipped)} "
                  f"failed={len(result.failed)}")
    for cid, err in result.failed:
        console.print(f"  [red]x[/red] {cid}: {err}")
    if result.failed:
        raise typer.Exit(1)


# ── Devin Knowledge management (list / prune / delete) ───────────────────────

devin_app = typer.Typer(help="Manage Devin Cloud Knowledge entries", rich_markup_mode=None)
okf_app.add_typer(devin_app, name="devin")


@devin_app.command("list")
def devin_list(
    api_key: Annotated[str | None, typer.Option("--api-key", help="Devin API key (else $DEVIN_API_KEY)")] = None,
    folder: Annotated[str | None, typer.Option("--folder", help="Filter to a folder name")] = None,
) -> None:
    """List all Devin Knowledge entries and folders for the org."""
    from agentic_cli.kg.okf.devin import list_entries

    try:
        data = list_entries(api_key=api_key)
    except (ValueError, Exception) as e:  # noqa: BLE001
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    folders = data.get("folders", [])
    folder_by_id = {f.get("id"): f.get("name") for f in folders}
    fid_filter = next((f.get("id") for f in folders if f.get("name") == folder), None) if folder else None

    console.print(f"[bold]Folders[/bold] ({len(folders)}): " +
                  (", ".join(f.get("name", "?") for f in folders) or "(none — create in Devin UI)"))
    table = Table(title="Devin Knowledge")
    table.add_column("Name", style="cyan", max_width=50)
    table.add_column("Folder", style="green")
    table.add_column("Repo", style="magenta")
    table.add_column("ID", style="dim")
    n = 0
    for k in data.get("knowledge", []):
        if fid_filter and k.get("parent_folder_id") != fid_filter:
            continue
        table.add_row(k.get("name", "?"), folder_by_id.get(k.get("parent_folder_id"), "-"),
                      k.get("pinned_repo") or "-", k.get("id", ""))
        n += 1
    console.print(table)
    console.print(f"  {n} entr{'y' if n == 1 else 'ies'}.")


@devin_app.command("prune")
def devin_prune(
    domain: Annotated[str | None, typer.Option("--domain", help="Domain slug")] = None,
    source: Annotated[str, typer.Option("--source", help="'export' or 'authored'")] = "export",
    bundle: Annotated[Path | None, typer.Option("--bundle", help="Explicit bundle dir")] = None,
    types: Annotated[str, typer.Option("--types", help="Concept types in scope")] = "FREQ,Requirement",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show orphans without deleting")] = False,
    api_key: Annotated[str | None, typer.Option("--api-key", help="Devin API key (else $DEVIN_API_KEY)")] = None,
) -> None:
    """Delete tracked Devin entries whose concept no longer exists in the bundle."""
    from agentic_cli.kg.okf.devin import prune_bundle

    bundle_dir = _resolve_bundle(domain, source, bundle)
    type_tuple = tuple(t.strip() for t in types.split(",") if t.strip())
    try:
        result = prune_bundle(bundle_dir, api_key=api_key, types=type_tuple, dry_run=dry_run)
    except (FileNotFoundError, ValueError, Exception) as e:  # noqa: BLE001
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if not result.orphans:
        console.print("[green]✓[/green] No orphaned Devin entries — bundle and Devin are in sync.")
        return
    console.print(f"[bold]Orphans[/bold] ({len(result.orphans)}):")
    for o in result.orphans:
        console.print(f"  - {o['concept_id']}  ({o['id']})")
    if dry_run:
        console.print("  (dry-run) re-run without --dry-run to delete these.")
        return
    console.print(f"[bold green]✓[/bold green] deleted={len(result.deleted)} failed={len(result.failed)}")
    for cid, err in result.failed:
        console.print(f"  [red]x[/red] {cid}: {err}")
    if result.failed:
        raise typer.Exit(1)


@devin_app.command("delete")
def devin_delete(
    ids: Annotated[list[str] | None, typer.Option("--id", help="Knowledge id(s) to delete (repeatable)")] = None,
    api_key: Annotated[str | None, typer.Option("--api-key", help="Devin API key (else $DEVIN_API_KEY)")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="Skip the confirmation prompt")] = False,
) -> None:
    """Delete specific Devin Knowledge entries by id."""
    from agentic_cli.kg.okf.devin import delete_entries

    if not ids:
        console.print("[red]✗[/red] Provide at least one --id.")
        raise typer.Exit(1)
    if not yes:
        confirm = typer.confirm(f"Delete {len(ids)} Devin knowledge entr{'y' if len(ids) == 1 else 'ies'}?")
        if not confirm:
            raise typer.Exit(0)
    try:
        deleted, failed = delete_entries(ids, api_key=api_key)
    except (ValueError, Exception) as e:  # noqa: BLE001
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)
    console.print(f"[bold green]✓[/bold green] deleted={len(deleted)} failed={len(failed)}")
    for nid, err in failed:
        console.print(f"  [red]x[/red] {nid}: {err}")
    if failed:
        raise typer.Exit(1)
