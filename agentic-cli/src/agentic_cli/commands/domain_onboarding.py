"""``keel domain`` commands for the onboarding review loop.

    keel domain add-docs      # track pages                      (elsewhere)
    keel domain classify-docs # what is each page for?
    keel domain extract       # in-memory read → review proposal
          ← the team reviews and edits the proposal
    keel domain finalize      # accept the reviewed set into .domain/
    keel domain score         # could a new teammate ship from this?

The proposal file is the source of truth for the review; these commands and the
dashboard are editors over it, which is what makes reviewing it as a pull request
the natural default. Nothing here writes a document body: extraction consumes
text in memory and only instructions survive.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli.onboarding import classify, extract, proposal, provenance, readiness, sources
from agentic_cli.tracker import (
    get_domain,
    get_domain_docs,
    get_domain_repos,
    record_activity,
    set_domain_doc_live_version,
    set_domain_doc_type,
    stale_domain_docs,
)

console = Console()

_STATUS_STYLE = {
    proposal.UNREVIEWED: "yellow",
    proposal.ACCEPTED: "green",
    proposal.REJECTED: "dim",
    proposal.STALE: "magenta",
}

_DIMENSION_STYLE = {
    readiness.OK: "green",
    readiness.WARN: "yellow",
    readiness.FAIL: "red",
    readiness.SKIPPED: "dim",
}


# ── shared resolution ───────────────────────────────────────────────────────

def _require_domain(slug: str) -> dict:
    domain = get_domain(slug)
    if not domain:
        console.print(f"[red]✗ Domain '{slug}' not found.[/red]")
        console.print(f"[dim]Register it first: {CLI_NAME} domain create <DOMAIN> --product <PRODUCT>[/dim]")
        raise typer.Exit(1)
    return domain


def _require_meta(slug: str) -> Path:
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    meta = detect_domain_meta_repo(slug)
    if meta is None:
        console.print(f"[red]✗ No meta-repo for '{slug}'.[/red]")
        console.print(f"[dim]Create one with: {CLI_NAME} domain init {slug}[/dim]")
        raise typer.Exit(1)
    return meta


def _domain_dir(meta: Path) -> Path:
    return meta / ".domain"


# ── classify-docs ───────────────────────────────────────────────────────────

def classify_docs(
    slug: Annotated[str, typer.Argument(help="Domain slug")],
    apply: Annotated[bool, typer.Option("--apply/--dry-run", help="Persist the classifications")] = True,
    set_type: Annotated[Optional[list[str]], typer.Option(
        "--set", help="Correct one page: --set <page-id>=<type>. Repeatable.")] = None,
) -> None:
    """Classify tracked docs by what they are *for*.

    An onboarding runbook and a meeting note used to produce identical concept
    refs, so nothing downstream could weight them. A ``--set`` correction is
    stored at full confidence and survives re-syncing.
    """
    _require_domain(slug)
    docs = get_domain_docs(slug)
    if not docs:
        console.print(f"[yellow]No docs tracked for '{slug}'. Run '{CLI_NAME} domain add-docs {slug}' first.[/yellow]")
        raise typer.Exit(0)

    corrections: dict[str, str] = {}
    for raw in set_type or []:
        page_id, _, doc_type = raw.partition("=")
        doc_type = doc_type.strip().lower()
        if doc_type not in classify.ALL_TYPES:
            console.print(f"[red]✗ Unknown type '{doc_type}'. One of: {', '.join(classify.ALL_TYPES)}[/red]")
            raise typer.Exit(1)
        corrections[page_id.strip()] = doc_type

    table = Table(title=f"Doc types — {slug}", show_lines=False)
    table.add_column("Page", style="dim", no_wrap=True)
    table.add_column("Title")
    table.add_column("Type")
    table.add_column("Confidence", justify="right")

    changed = 0
    for doc in docs:
        page_id = str(doc.get("source_page_id"))
        if page_id in corrections:
            verdict = classify.Classification(corrections[page_id], 1.0, "manual")
        else:
            verdict = classify.classify(doc.get("title") or "", doc.get("source_space_key") or "")

        if apply and set_domain_doc_type(slug, page_id, verdict.doc_type, verdict.confidence):
            changed += 1

        style = "bold" if verdict.operational else ""
        table.add_row(
            page_id,
            (doc.get("title") or "")[:56],
            f"[{style}]{verdict.doc_type}[/{style}]" if style else verdict.doc_type,
            f"{verdict.confidence:.0%}" + ("" if verdict.certain else " [yellow]?[/yellow]"),
        )

    console.print(table)
    counts = classify.counts({
        str(d["source_page_id"]): classify.classify(d.get("title") or "", d.get("source_space_key") or "")
        for d in docs
    })
    console.print("  ".join(f"[bold]{n}[/bold] {t}" for t, n in counts.items()))
    if apply:
        console.print(f"[green]✓[/green] Classified {changed} doc(s).")
    else:
        console.print("[dim](dry run — nothing written)[/dim]")

    record_activity(command="domain", subcommand="classify-docs",
                    args={"domain": slug, "docs": len(docs)})


# ── extract ─────────────────────────────────────────────────────────────────

def extract_intent(
    slug: Annotated[str, typer.Argument(help="Domain slug")],
    include_repos: Annotated[bool, typer.Option(
        "--repos/--no-repos", help="Also read CONTRIBUTING/docs/ADRs from linked repo clones")] = True,
    all_types: Annotated[bool, typer.Option(
        "--all-types", help="Read every tracked doc, not only onboarding and runbooks")] = False,
) -> None:
    """Read the onboarding corpus and propose instructions for review.

    Bodies are consumed in memory and discarded; only abstracted instructions,
    each citing its source by pointer, reach the proposal. Candidates carrying
    names, credentials or guard terms are **held** — recorded with their risk
    kinds and citation, never with their text.
    """
    _require_domain(slug)
    meta = _require_meta(slug)

    docs = get_domain_docs(slug)
    documents: list[sources.Document] = []
    unreachable = 0

    wanted = docs if all_types else [
        d for d in docs
        if (d.get("doc_type") or classify.classify(d.get("title") or "").doc_type)
        in classify.OPERATIONAL
    ]

    if wanted:
        console.print(f"[cyan]Reading {len(wanted)} tracked doc(s)...[/cyan]")
    for doc in wanted:
        page_id = str(doc.get("source_page_id"))
        fetched = sources.fetch_confluence(page_id, doc.get("title") or "")
        if fetched is None:
            unreachable += 1
            console.print(f"  [yellow]⚠[/yellow] unreachable: {doc.get('title') or page_id}")
            continue
        fetched.doc_type = doc.get("doc_type") or classify.ONBOARDING
        documents.append(fetched)
        # Observing the live version is the doc half of drift.
        if fetched.citation.version.isdigit():
            set_domain_doc_live_version(slug, page_id, int(fetched.citation.version))

    if include_repos:
        from agentic_cli import persona_workspace as pw

        for repo in get_domain_repos(slug):
            repo_slug = repo.get("repo_slug") or ""
            root = pw.store_repo_path(repo_slug)
            found = sources.repo_documents(root, repo_slug)
            if found:
                console.print(f"  [green]✓[/green] {repo_slug}: {len(found)} repo doc(s)")
            documents.extend(found)

    if not documents:
        console.print(
            f"[yellow]Nothing to read. Track onboarding pages with "
            f"'{CLI_NAME} domain add-docs {slug}', or sync repo clones with "
            f"'{CLI_NAME} domain sync {slug}'.[/yellow]"
        )
        raise typer.Exit(0)

    candidates: list[extract.Candidate] = []
    held: list[extract.Candidate] = []
    for document in documents:
        result = extract.extract(document.text, document.citation, document.doc_type)
        candidates.extend(result.candidates)
        held.extend(result.held)

    existing = proposal.load(meta, slug)
    merged = proposal.merge(existing, candidates + held, slug)
    path = proposal.save(meta, merged)

    counts = merged.counts
    console.print()
    console.print(Panel.fit(
        f"[bold]{len(documents)}[/bold] document(s) read and discarded\n"
        f"[bold]{len(candidates)}[/bold] instruction(s) proposed, "
        f"[bold]{len(held)}[/bold] held\n"
        + "  ".join(f"[{_STATUS_STYLE.get(s, '')}]{n} {s}[/]" for s, n in counts.items())
        + (f"\n[yellow]{unreachable} source(s) unreachable[/yellow]" if unreachable else ""),
        title="Extracted", border_style="cyan",
    ))
    console.print(f"[bold]Review:[/bold] {path}")
    console.print(f"[dim]Set `status: accepted` on what is correct, then: "
                  f"{CLI_NAME} domain finalize {slug}[/dim]")

    record_activity(command="domain", subcommand="extract",
                    args={"domain": slug, "documents": len(documents),
                          "proposed": len(candidates), "held": len(held)})


# ── review ──────────────────────────────────────────────────────────────────

def review(
    slug: Annotated[str, typer.Argument(help="Domain slug")],
    accept: Annotated[Optional[list[str]], typer.Option("--accept", help="Accept an id. Repeatable.")] = None,
    reject: Annotated[Optional[list[str]], typer.Option("--reject", help="Reject an id. Repeatable.")] = None,
    accept_kind: Annotated[Optional[str], typer.Option(
        "--accept-kind", help=f"Accept every pending instruction of one kind ({'|'.join(extract.KIND_ORDER)})")] = None,
    show_all: Annotated[bool, typer.Option("--all", help="Show settled entries too")] = False,
) -> None:
    """Show the review worklist, or record verdicts from the command line."""
    _require_domain(slug)
    meta = _require_meta(slug)
    review_set = proposal.load(meta, slug)
    if not review_set.entries:
        console.print(f"[yellow]No proposal yet. Run '{CLI_NAME} domain extract {slug}'.[/yellow]")
        raise typer.Exit(0)

    by_id = {e.id: e for e in review_set.entries}
    changed = 0
    for entry_id in accept or []:
        if entry_id in by_id and not by_id[entry_id].held:
            entry = by_id[entry_id]
            # Accepting a stale entry adopts the proposed replacement.
            if entry.status == proposal.STALE and entry.proposed_text:
                entry.text, entry.proposed_text = entry.proposed_text, ""
            entry.status = proposal.ACCEPTED
            changed += 1
    for entry_id in reject or []:
        if entry_id in by_id:
            by_id[entry_id].status = proposal.REJECTED
            changed += 1
    if accept_kind:
        for entry in review_set.entries:
            if entry.kind == accept_kind and entry.pending and not entry.held:
                if entry.status == proposal.STALE and entry.proposed_text:
                    entry.text, entry.proposed_text = entry.proposed_text, ""
                entry.status = proposal.ACCEPTED
                changed += 1

    if changed:
        proposal.save(meta, review_set)
        console.print(f"[green]✓[/green] Recorded {changed} verdict(s).")
        record_activity(command="domain", subcommand="review",
                        args={"domain": slug, "verdicts": changed})

    shown = review_set.entries if show_all else [e for e in review_set.entries if e.pending]
    if not shown:
        console.print(f"[green]✓ Nothing pending for '{slug}'.[/green]")
        console.print(f"[dim]{len(review_set.accepted)} instruction(s) accepted. "
                      f"Next: {CLI_NAME} domain finalize {slug}[/dim]")
        return

    # The citation rides under the instruction rather than in its own column:
    # with five columns at 80 chars Rich collapses the instruction to nothing,
    # which blanks exactly the rows a reviewer needs to read.
    table = Table(title=f"Review — {slug}", show_lines=True)
    table.add_column("Id", style="dim", no_wrap=True)
    table.add_column("Kind", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Instruction", overflow="fold", min_width=32, ratio=1)

    for entry in shown:
        if entry.held:
            body = f"[dim]held — {entry.reason}. Read the source to decide.[/dim]"
        elif entry.status == proposal.STALE:
            body = f"{entry.text}\n[magenta]→ {entry.proposed_text}[/magenta]"
        else:
            body = entry.text
        if entry.source_absent:
            body += "\n[yellow]source no longer yields this[/yellow]"
        table.add_row(
            entry.id, entry.kind,
            f"[{_STATUS_STYLE.get(entry.status, '')}]{entry.status}[/]",
            f"{body}\n[dim]{entry.citation}[/dim]",
        )

    console.print(table)
    console.print(f"[dim]Edit {proposal.path_for(meta)} directly, or: "
                  f"{CLI_NAME} domain review {slug} --accept <id>[/dim]")


# ── finalize ────────────────────────────────────────────────────────────────

_KIND_FILES = {
    extract.SETUP: ("setup.md", "Setup"),
    extract.RUNBOOK_STEP: ("runbook.md", "Operating"),
    extract.HAZARD: ("hazards.md", "Hazards"),
    extract.OWNERSHIP: ("ownership.md", "Ownership"),
    extract.GLOSSARY: ("glossary.md", "Glossary"),
}


def finalize(
    slug: Annotated[str, typer.Argument(help="Domain slug")],
    reviewer: Annotated[Optional[str], typer.Option("--reviewer", help="Recorded in the audit trail, not in the files")] = None,
) -> None:
    """Write the accepted instructions into ``.domain/`` and stamp them reviewed.

    The reviewer is recorded in the tracker, which already carries actor
    attribution — never in the generated files, which stay free of personal
    identifiers by construction.
    """
    _require_domain(slug)
    meta = _require_meta(slug)
    review_set = proposal.load(meta, slug)

    accepted = review_set.accepted
    if not accepted:
        console.print(f"[yellow]Nothing accepted yet for '{slug}'.[/yellow]")
        console.print(f"[dim]Review the proposal at {proposal.path_for(meta)}[/dim]")
        raise typer.Exit(0)

    domain_dir = _domain_dir(meta)
    domain_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for kind, (filename, heading) in _KIND_FILES.items():
        entries = [e for e in accepted if e.kind == kind]
        if not entries:
            continue
        path = domain_dir / filename
        body = [f"# {heading}", ""]
        for entry in entries:
            body.append(f"- {entry.text}  <!-- {entry.citation} -->")
        body.append("")
        path.write_text("\n".join(body), encoding="utf-8")
        provenance.stamp(path, _provenance_for(entries), reviewed=True)
        written.append(f"{filename} ({len(entries)})")

    console.print(Panel.fit(
        "\n".join(f"  [green]✓[/green] .domain/{name}" for name in written)
        + f"\n\n[bold]{len(accepted)}[/bold] instruction(s) finalized",
        title=f"Finalized — {slug}", border_style="green",
    ))
    if review_set.pending:
        console.print(f"[yellow]{len(review_set.pending)} instruction(s) still pending review.[/yellow]")
    console.print(f"[dim]Next: {CLI_NAME} domain score {slug}[/dim]")

    record_activity(command="domain", subcommand="finalize",
                    args={"domain": slug, "finalized": len(accepted)},
                    actor=reviewer)


def _provenance_for(entries: list[proposal.Entry]) -> str:
    """A stamp naming the dominant source scheme and how many sources fed it."""
    refs = [extract.Citation.parse(e.citation) for e in entries]
    schemes = [r.scheme for r in refs if r.scheme]
    dominant = max(set(schemes), key=schemes.count) if schemes else provenance.DOC
    unique = list(dict.fromkeys(r.ref for r in refs if r.scheme == dominant))
    if not unique:
        return dominant
    suffix = f"+{len(unique) - 1}" if len(unique) > 1 else ""
    return f"{dominant}:{unique[0]}{suffix}"


# ── score ───────────────────────────────────────────────────────────────────

def score(
    slug: Annotated[str, typer.Argument(help="Domain slug")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit the scorecard as JSON")] = False,
    write: Annotated[bool, typer.Option("--write/--no-write", help="Save to .platform/readiness.json")] = True,
    require: Annotated[Optional[float], typer.Option(
        "--require", help="Exit non-zero below this overall score (gate a pipeline)")] = None,
) -> None:
    """Score whether a new teammate could ship from this domain.

    Seven dimensions are deterministic. Answerability needs an LLM judge and
    reports SKIPPED without one — a missing credential must never look like an
    unready domain.
    """
    _require_domain(slug)
    meta = _require_meta(slug)
    card = readiness.score(gather(slug, meta))

    if write:
        target = meta / ".platform" / "readiness.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(card.to_dict(), indent=2) + "\n", encoding="utf-8")

    if as_json:
        console.print_json(json.dumps(card.to_dict()))
    else:
        table = Table(title=f"Readiness — {slug}", show_lines=False)
        table.add_column("Dimension", no_wrap=True)
        table.add_column("Score", justify="right", no_wrap=True)
        table.add_column("Detail")
        for dimension in card.dimensions:
            style = _DIMENSION_STYLE.get(dimension.status, "")
            value = "—" if dimension.score is None else f"{dimension.score:.0f}"
            table.add_row(
                f"[{style}]{dimension.label}[/]",
                f"[{style}]{value}[/]",
                dimension.detail + (f"\n[dim]{dimension.fix}[/dim]"
                                    if dimension.status in (readiness.FAIL, readiness.WARN) else ""),
            )
        console.print(table)
        overall = card.overall
        verdict = "[green]ready[/green]" if card.ready() else "[yellow]not ready[/yellow]"
        console.print(
            f"[bold]Overall:[/bold] {'n/a' if overall is None else f'{overall:.0f}'} "
            f"(grade {card.grade}) — {verdict}"
        )

    record_activity(command="domain", subcommand="score",
                    args={"domain": slug, "overall": card.overall, "grade": card.grade})

    if require is not None and (card.overall is None or card.overall < require):
        raise typer.Exit(1)


def gather(slug: str, meta: Path) -> readiness.Inputs:
    """Collect every signal the rubric needs. The only part that touches I/O."""
    import yaml

    from agentic_cli import persona_workspace as pw

    docs = get_domain_docs(slug)
    repos = []
    for repo in get_domain_repos(slug):
        repo_slug = repo.get("repo_slug") or ""
        root = pw.store_repo_path(repo_slug)
        repos.append({
            "slug": repo_slug,
            "has_codeowners": any(
                (root / name).is_file()
                for name in ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")
            ),
        })

    governance: dict = {}
    governance_path = meta / ".platform" / "config" / "governance.yaml"
    if governance_path.is_file():
        try:
            governance = yaml.safe_load(governance_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            governance = {}

    return readiness.Inputs(
        domain=slug,
        meta_repo=meta,
        docs=docs,
        classifications={
            str(d["source_page_id"]): classify.Classification(
                d.get("doc_type") or classify.OTHER, d.get("doc_type_confidence") or 0.0)
            for d in docs if d.get("source_page_id")
        },
        repos=repos,
        review=proposal.load(meta, slug),
        stamps=provenance.scan(_domain_dir(meta)),
        governance=governance,
        stale_docs=len(stale_domain_docs(slug)),
        judge_available=_judge_available(),
    )


def _judge_available() -> bool:
    """True when a model provider is configured for the answerability judge."""
    import os

    return any(os.environ.get(key) for key in (
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
        "VERTEX_PROJECT_ID",
    ))


def register(domain_app: typer.Typer) -> None:
    """Attach the onboarding commands to ``keel domain``."""
    domain_app.command("classify-docs")(classify_docs)
    domain_app.command("extract")(extract_intent)
    domain_app.command("review")(review)
    domain_app.command("finalize")(finalize)
    domain_app.command("score")(score)


__all__ = ["register", "gather", "classify_docs", "extract_intent", "review",
           "finalize", "score"]
