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
from agentic_cli.onboarding import (
    answerability, classify, extract, proposal, provenance, readiness, sources,
)
from agentic_cli.tracker import (
    doc_ref,
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

    # Everything read from here down is this project's context-building cost.
    # Binding the domain around the whole command is what separates "what did
    # it cost to build this context" from "what did it cost to use it" — the
    # two meters that a single undifferentiated byte total cannot tell apart.
    from agentic_cli import tracing

    with tracing.session_scope(domain=slug, phase=tracing.BUILD):
        _extract_intent(slug, meta, include_repos, all_types)


def _extract_intent(slug: str, meta: Path, include_repos: bool,
                    all_types: bool) -> None:
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
        # By ref, not by page id: the scheme decides the reader, so a Kaggle
        # competition tracked with `domain add-source` extracts exactly like a
        # Confluence page rather than needing a branch here.
        fetched = sources.fetch_source(doc_ref(doc), doc.get("title") or "")
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

#: Which ``.domain/`` file each instruction kind is written to, and its heading.
#: Exported because the dashboard maps artifacts back to kinds and must not
#: re-derive the relationship from filenames.
KIND_FILES: dict[str, tuple[str, str]] = {
    extract.SETUP: ("setup.md", "Setup"),
    extract.RUNBOOK_STEP: ("runbook.md", "Operating"),
    extract.HAZARD: ("hazards.md", "Hazards"),
    extract.OWNERSHIP: ("ownership.md", "Ownership"),
    extract.GLOSSARY: ("glossary.md", "Glossary"),
}

#: The inverse: ``setup.md`` → ``setup``.
FILE_KINDS: dict[str, str] = {filename: kind for kind, (filename, _) in KIND_FILES.items()}


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

    for kind, (filename, heading) in KIND_FILES.items():
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

def _score_portfolio(
    product: Optional[str], *, as_json: bool, write: bool, require: Optional[float]
) -> None:
    """Score every domain and rank them worst-first.

    A domain without a meta-repo is listed rather than skipped: "not set up yet"
    and "set up and scoring badly" are different problems, and a portfolio view
    that silently omits the first one is the more misleading of the two.
    """
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo
    from agentic_cli.tracker import get_domains

    domains = [
        d for d in get_domains()
        if not product or (d.get("product") or "").lower() == product.lower()
    ]
    if not domains:
        console.print(f"[yellow]No domains registered"
                      f"{f' for product {product}' if product else ''}.[/yellow]")
        raise typer.Exit(0)

    rows: list[dict] = []
    for domain in domains:
        slug = domain["name"]
        meta = detect_domain_meta_repo(slug)
        if meta is None:
            rows.append({"domain": slug, "product": domain.get("product") or "",
                         "overall": None, "grade": "—", "ready": False,
                         "note": "no meta-repo — run `domain init`"})
            continue
        card = readiness.score(gather(slug, meta))
        if write:
            target = meta / ".platform" / "readiness.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(card.to_dict(), indent=2) + "\n", encoding="utf-8")
        weakest = sorted(
            (d for d in card.dimensions if d.score is not None),
            key=lambda d: d.score)[:2]
        rows.append({
            "domain": slug, "product": domain.get("product") or "",
            "overall": card.overall, "grade": card.grade, "ready": card.ready(),
            "note": ", ".join(f"{d.label} {d.score:.0f}" for d in weakest),
        })

    # Worst first: an unscorable domain sorts to the top, because it is the most
    # actionable row on the page.
    rows.sort(key=lambda r: (r["overall"] is not None, r["overall"] or 0))

    if as_json:
        console.print_json(json.dumps({"product": product, "domains": rows}))
    else:
        table = Table(title="Domain readiness" + (f" — {product}" if product else ""),
                      show_lines=False)
        table.add_column("Domain", no_wrap=True)
        table.add_column("Grade", justify="center", no_wrap=True)
        table.add_column("Overall", justify="right", no_wrap=True)
        table.add_column("Weakest", overflow="fold")
        for row in rows:
            style = ("green" if row["ready"] else
                     "dim" if row["overall"] is None else "yellow")
            table.add_row(
                row["domain"],
                f"[{style}]{row['grade']}[/]",
                "—" if row["overall"] is None else f"{row['overall']:.0f}",
                row["note"],
            )
        console.print(table)
        ready = sum(1 for r in rows if r["ready"])
        console.print(f"[bold]{ready}[/bold]/{len(rows)} ready to build on")

    record_activity(command="domain", subcommand="score",
                    args={"product": product, "domains": len(rows),
                          "ready": sum(1 for r in rows if r["ready"])})

    lowest = min((r["overall"] for r in rows if r["overall"] is not None), default=None)
    if require is not None and (lowest is None or lowest < require):
        raise typer.Exit(1)


def score(
    slug: Annotated[Optional[str], typer.Argument(help="Domain slug (omit with --all)")] = None,
    all_domains: Annotated[bool, typer.Option(
        "--all", help="Score every domain, worst first — the portfolio readout")] = False,
    product: Annotated[Optional[str], typer.Option(
        "--product", "-p", help="With --all, limit to one product's domains")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the scorecard as JSON")] = False,
    write: Annotated[bool, typer.Option("--write/--no-write", help="Save to .platform/readiness.json")] = True,
    require: Annotated[Optional[float], typer.Option(
        "--require", help="Exit non-zero below this overall score (gate a pipeline)")] = None,
) -> None:
    """Score whether a new teammate could ship from this domain.

    Seven dimensions are deterministic. Answerability needs an LLM judge and
    reports SKIPPED without one — a missing credential must never look like an
    unready domain.

    ``--all`` scores every domain worst-first, which is the question a lead
    actually has: not "how is this one doing" but "which of mine needs attention
    this morning".
    """
    if all_domains:
        _score_portfolio(product, as_json=as_json, write=write, require=require)
        return
    if not slug:
        console.print("[red]✗ Give a domain slug, or --all for every domain.[/red]")
        raise typer.Exit(1)

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


def _run_answerability(
    slug: str, meta: Path, repos: list[dict], product: str = ""
) -> Optional[answerability.Report]:
    """Ask a judge whether the finalized context answers a new joiner's questions.

    Returns None whenever the judge cannot run or cannot be read — no provider,
    an empty context, a reply we cannot parse. The scorecard turns that into
    SKIPPED, which is the honest reading: nothing was learned about the domain.
    """
    if not _judge_available():
        return None

    domain_dir = _domain_dir(meta)
    bodies: dict[str, str] = {}
    for stamp in provenance.scan(domain_dir):
        if not stamp.real:
            continue
        try:
            bodies[stamp.path.name] = stamp.path.read_text(encoding="utf-8")
        except OSError:
            continue
    context = answerability.render_context(bodies)
    if not context.strip():
        return None

    try:
        from agentic_cli.llm.factory import get_llm_provider

        provider = get_llm_provider(
            system_instruction="You grade onboarding documentation strictly and "
                               "reply with JSON only.")
        # Test mode answers deterministically without a model; grading against
        # it would produce a confident number backed by nothing.
        if provider.get_name().startswith("test-mode"):
            return None
    except Exception:  # noqa: BLE001 - an unavailable judge is not a failing domain
        return None

    questions = answerability.build_questions(slug, product, repos)
    return answerability.judge(questions, context, provider)


def stale_repo_entries(slug: str, review: proposal.Proposal) -> list[proposal.Entry]:
    """Accepted instructions whose repo source has changed since we read it.

    Confluence staleness is a version comparison held in the tracker; repo
    staleness has to be recomputed, because the citation carries a digest of the
    file's content rather than a number someone else increments. Entries whose
    file cannot be read are left out entirely — unknown is not stale.

    The comparison itself lives in :func:`agentic_cli.retrieval.is_stale`, which
    is scheme-agnostic. The ``repo`` filter here is the caller's, not the seam's:
    this feeds a signal labelled "changed repo files", and widening it to
    Confluence would change what that number means without changing its name.
    """
    from agentic_cli import retrieval

    stale: list[proposal.Entry] = []
    for entry in review.entries:
        if entry.held or entry.status != proposal.ACCEPTED:
            continue
        citation = extract.Citation.parse(entry.citation)
        if citation.scheme != "repo" or "/" not in citation.ref:
            continue
        if retrieval.is_stale(f"repo:{citation.ref}", citation.version) is True:
            stale.append(entry)
    return stale


def diff_domain(slug: str, review: proposal.Proposal, *,
                provider=None) -> "differ.Report":
    """Rule on what a source's move actually did to the instructions from it.

    Two passes, cheap one first. The digest says *look* — it is one read and it
    is right about whether anything moved. The differ says *what changed*, and
    it costs a re-extraction, so it runs only over the sources the digest
    flagged. On a domain where nothing moved this does one fetch per source and
    no extraction at all, which is what makes it safe to hang off a drift poll.

    Scheme-agnostic by construction: entries carry ``repo:`` and ``confluence:``
    citations alike and both resolve through the retrieval seam, so this needed
    no knowledge of either source.
    """
    from agentic_cli import retrieval
    from agentic_cli.onboarding import differ

    by_source: dict[str, list[proposal.Entry]] = {}
    for entry in review.entries:
        if entry.held or entry.status != proposal.ACCEPTED or not entry.text:
            continue
        citation = extract.Citation.parse(entry.citation)
        if not citation.scheme or not citation.ref:
            continue
        by_source.setdefault(f"{citation.scheme}:{citation.ref}", []).append(entry)

    reports: list[differ.Report] = []
    for ref, entries in sorted(by_source.items()):
        fetched = retrieval.fetch(ref, source=retrieval.ONBOARDING_SOURCE,
                                  operation_prefix="diff", trace=False)
        if not fetched.known or not fetched.text:
            # We could not ask. Reporting these absent would retract the team's
            # own approved context because a checkout was missing.
            reports.append(differ.unknown_for(entries, ref))
            continue
        cited = {extract.Citation.parse(e.citation).version for e in entries}
        if fetched.version and cited == {fetched.version}:
            continue                    # nothing moved; no re-extraction needed

        citation = extract.Citation(*ref.split(":", 1), fetched.version)
        result = extract.extract(fetched.text, citation, classify.ONBOARDING)
        reports.append(differ.diff(entries, result.candidates, provider=provider))

    return differ.merge_reports(reports)


def gather(slug: str, meta: Path) -> readiness.Inputs:
    """Collect every signal the rubric needs. The only part that touches I/O."""
    import yaml

    from agentic_cli import persona_workspace as pw

    d = get_domain(slug) or {}
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

    review = proposal.load(meta, slug)
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
        review=review,
        stamps=provenance.scan(_domain_dir(meta)),
        governance=governance,
        stale_docs=len(stale_domain_docs(slug)),
        stale_instructions=len(stale_repo_entries(slug, review)),
        judge_available=_judge_available(),
        answerability=_run_answerability(slug, meta, repos, product=d.get("product") or ""),
    )


# ── diff ────────────────────────────────────────────────────────────────────

_VERDICT_STYLE = {
    "unchanged": "dim",
    "reworded": "yellow",
    "contradicted": "red",
    "absent": "red",
    "unknown": "dim",
}


def _diff_judge():
    """A provider for ruling on agreement, or None when there is no judge."""
    if not _judge_available():
        return None
    try:
        from agentic_cli.llm.factory import get_llm_provider

        provider = get_llm_provider(
            system_instruction="You compare instructions for agreement and "
                               "reply with JSON only.")
        # Test mode answers deterministically without a model. A confident
        # "these agree" backed by nothing is worse here than no answer: it is
        # the verdict that lets an instruction fast-forward unreviewed.
        if provider.get_name().startswith("test-mode"):
            return None
        return provider
    except Exception:  # noqa: BLE001 - no judge is a degraded run, not a failure
        return None


def diff_command(
    slug: Annotated[str, typer.Argument(help="Domain slug")],
    judge: Annotated[bool, typer.Option(
        "--judge/--no-judge",
        help="Ask a model whether a reworded source still agrees")] = True,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the report as JSON")] = False,
) -> None:
    """What did the source changes actually do to our approved instructions?

    ``domain score`` and the drift signals tell you a source moved. This tells
    you whether the move mattered: an instruction that came back unchanged, one
    reworded, one the source now contradicts, and one it no longer supports are
    four different problems, and only two of them are yours today.

    Without a judge this still separates unchanged from moved and catches a
    reversed instruction, but it will not certify a reword as safe — an
    unverified reword is reported as needing a human, never fast-forwarded.

    Exits non-zero when an instruction is contradicted or no longer supported,
    so it can gate a pull request. An unverified reword does not fail the run.
    """
    from agentic_cli.onboarding import differ

    _require_domain(slug)
    meta = _require_meta(slug)
    review = proposal.load(meta, slug)
    if not review.accepted:
        console.print(f"[yellow]No accepted instructions for '{slug}' yet. "
                      f"Run `{CLI_NAME} domain review {slug}` first.[/yellow]")
        raise typer.Exit(0)

    from agentic_cli import tracing

    provider = _diff_judge() if judge else None
    with tracing.session_scope(domain=slug, phase=tracing.BUILD):
        report = diff_domain(slug, review, provider=provider)
    by_id = {e.id: e for e in review.entries}

    if not report.verdicts and not as_json:
        console.print(f"[green]✓[/green] Every source behind {len(review.accepted)} "
                      f"accepted instruction(s) is unchanged.")
        raise typer.Exit(0)

    if as_json:
        # Falls through to the exit gate rather than returning here: a pipeline
        # reading the JSON is the caller most likely to be relying on the exit
        # code, so it is the last place that should quietly always succeed.
        console.print_json(json.dumps(report.to_dict()))
        _exit_on_broken(report)
        raise typer.Exit(0)

    # Worst first. An unchanged instruction is not news and sorts last.
    order = {differ.CONTRADICTED: 0, differ.ABSENT: 1, differ.REWORDED: 2,
             differ.UNKNOWN: 3, differ.UNCHANGED: 4}
    verdicts = sorted(report.verdicts,
                      key=lambda v: (order.get(v.status, 9), -v.similarity))

    table = Table(title=f"Source changes — {slug}", show_lines=True)
    table.add_column("Verdict", no_wrap=True)
    table.add_column("Approved instruction", overflow="fold")
    table.add_column("Its source now says", overflow="fold")
    for verdict in verdicts:
        if verdict.status == differ.UNCHANGED:
            continue                    # summarised in the footer instead
        entry = by_id.get(verdict.entry_id)
        label = verdict.status
        if verdict.status == differ.REWORDED and not verdict.checked:
            label += "\n[dim](unverified)[/dim]"
        table.add_row(
            f"[{_VERDICT_STYLE.get(verdict.status, '')}]{label}[/]",
            (entry.text if entry else verdict.entry_id)[:220],
            (verdict.replacement or f"[dim]{verdict.detail}[/dim]")[:220],
        )
    if table.row_count:
        console.print(table)

    counts = report.counts
    console.print("  ".join(
        f"[{_VERDICT_STYLE.get(k, '')}]{n} {k}[/]" for k, n in sorted(counts.items())))
    if not provider:
        console.print("[dim]No judge configured — rewordings are unverified. "
                      "A contradiction is only caught when it flips a negation.[/dim]")
    if report.unreadable:
        console.print(f"[yellow]{len(report.unreadable)} source(s) could not be "
                      f"read; their instructions are unknown, not absent.[/yellow]")

    record_activity(command="domain", subcommand="diff",
                    args={"domain": slug, "judged": bool(provider), **counts})

    _exit_on_broken(report)


def _exit_on_broken(report) -> None:
    """Exit non-zero for instructions we have positive evidence are broken.

    This is what makes ``domain diff`` usable as a CI gate: "did this pull
    request contradict approved domain context?". An unverified reword is not
    evidence of anything — on a domain with no judge *every* reword is
    unverified, and failing on those would make the exit code mean "a source
    changed", which the digest already said for free.
    """
    from agentic_cli.onboarding import differ

    if report.of(differ.CONTRADICTED) or report.of(differ.ABSENT):
        raise typer.Exit(1)


# ── usage ───────────────────────────────────────────────────────────────────

def _thousands(n: int) -> str:
    """Compact a token count without losing the order of magnitude."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def usage_command(
    slug: Annotated[Optional[str], typer.Argument(
        help="Domain slug (omit with --all)")] = None,
    all_projects: Annotated[bool, typer.Option(
        "--all", help="Every project, biggest first — the portfolio readout")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the readout as JSON")] = False,
    rates_init: Annotated[bool, typer.Option(
        "--rates-init", help="Copy the example rate card so costs can be shown")] = False,
) -> None:
    """How much context each project built, served, and read from tools.

    Split three ways on purpose. Building a domain's context is a one-off
    investment; serving it is what recurs every session. A single total hides
    which of the two a project is actually spending on, and two projects with
    identical totals can be in opposite situations — one three days into
    onboarding, one running daily off finished context.

    Tokens are the unit a model window and a bill are denominated in, so that is
    what this reports. Most are estimates, because no vendor tokenizer is
    bundled, and every row says which — an estimate is fine for comparing two
    projects, where a systematic bias cancels, and is not a statement about money.

    A read that contributed no token count is shown as uncounted rather than as
    zero, and a total containing one is prefixed ``≥``. A retrieval path that
    records a size without the text behind it is not free, and a cost table is
    exactly where a zero gets read as though it were.

    Costs appear only when a rate card is configured — Keel ships no prices,
    because a wrong price is worse than no price. They cover model calls alone:
    retrieval is not billed by anyone, and context turns into money when a model
    reads it, not when Keel fetches it.
    """
    from agentic_cli import usage

    if rates_init:
        _init_rate_card()
        raise typer.Exit(0)

    if not all_projects and not slug:
        console.print("[red]✗ Give a domain slug, or --all for every project.[/red]")
        raise typer.Exit(1)
    if slug:
        _require_domain(slug)

    projects = usage.by_project(domain=None if all_projects else slug)
    if not projects:
        console.print(f"[yellow]Nothing recorded"
                      f"{'' if all_projects else f' for {slug}'} yet.[/yellow]")
        raise typer.Exit(0)

    summary = usage.compare(projects)
    if as_json:
        console.print_json(json.dumps(
            {"projects": [p.to_dict() for p in projects], "summary": summary}))
        raise typer.Exit(0)

    table = Table(title="Context usage" + ("" if all_projects else f" — {slug}"),
                  show_lines=False)
    table.add_column("Project", no_wrap=True)
    table.add_column("Meter", no_wrap=True)
    table.add_column("Reads", justify="right", no_wrap=True)
    table.add_column("In", justify="right", no_wrap=True)
    table.add_column("Out", justify="right", no_wrap=True)
    table.add_column("Basis", no_wrap=True)

    for project in projects:
        first = True
        for key in usage.METER_ORDER:
            if key not in project.meters:
                continue
            meter = project.meters[key]
            # A meter nothing was counted for shows a dash, never a zero. Zero
            # reads as "this was free", which is the reading a cost table
            # invites and the opposite of what an uncounted row means.
            shown = "—" if not meter.counted else _thousands(meter.tokens)
            style = "yellow" if not meter.complete else "dim"
            # Only a model call has an output side. A dash elsewhere, never a
            # zero: zero would read as a model that returned nothing rather than
            # as a row that is not about a model.
            out = _thousands(meter.tokens_out) if key == usage.GENERATE else "—"
            table.add_row(
                f"[bold]{project.named}[/bold]" if first else "",
                meter.label,
                f"{meter.reads:,}",
                shown,
                out,
                f"[{style}]{meter.basis}[/{style}]",
            )
            first = False
        share = project.build_share
        total = _thousands(project.tokens)
        if not project.complete:
            # "at least" rather than a bare figure: some reads contributed
            # nothing, so the number is a floor.
            total = f"≥{total}"
        table.add_row(
            "" if not first else f"[bold]{project.named}[/bold]",
            "[dim]total[/dim]",
            f"[bold]{project.reads:,}[/bold]",
            f"[bold]{total}[/bold]",
            f"[bold]{_thousands(project.generated)}[/bold]"
            if project.generated else "—",
            "" if share is None else f"[dim]{share:.0%} building[/dim]",
        )
    console.print(table)
    console.print(f"[dim]{summary['basis_note']}.[/dim]")
    # Said only when both numbers exist, because the comparison is the point and
    # a lone served figure invites being read as the prompt size.
    served = sum(p.meter(usage.SERVE).tokens for p in projects)
    admitted = sum(p.admitted for p in projects)
    if served and admitted:
        # The gap is named, never its direction. A prompt can be smaller than
        # what Keel retrieved (dedup, truncation, a cache hit) or larger (system
        # instructions, the question, conversation history) — asserting either
        # way would be a claim about an engine's internals we cannot see.
        console.print(
            f"[dim]Keel served {_thousands(served)}; the models read "
            f"{_thousands(admitted)}. The two differ by whatever the engine "
            f"added or dropped on the way in — retrieved is not sent.[/dim]")
    else:
        console.print("[dim]Retrieval rows are what Keel served, not what an "
                      "engine admitted to its prompt.[/dim]")

    _print_cost(None if all_projects else slug)

    record_activity(command="domain", subcommand="usage",
                    args={"domain": slug or "*", "projects": len(projects),
                          "tokens": summary["tokens"]})


def _init_rate_card() -> None:
    """Copy the example rate card into place, refusing to clobber an edited one."""
    import shutil

    from agentic_cli import pricing

    target = pricing.card_path()
    if target.exists():
        console.print(f"[yellow]A rate card already exists at {target}.[/yellow]")
        console.print("[dim]Edit it, or delete it and re-run to start from the "
                      "example.[/dim]")
        raise typer.Exit(1)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pricing.example_path(), target)
    console.print(f"[green]✓[/green] Rate card written to {target}")
    console.print("[dim]Check the figures against your vendor's pricing page "
                  "before trusting them, and update `as_of` when you do.[/dim]")


def _print_cost(slug) -> None:
    """The money half, kept apart from the token table on purpose.

    Retrieval carries tokens and no cost — nobody bills for reading a file off
    disk. Context becomes money when a model reads it, so putting a cost column
    on the retrieval meters would have invited adding the two together.
    """
    from agentic_cli import pricing, usage

    report = usage.cost_by_project(domain=slug)
    card = report["card"]
    if not card.configured:
        console.print(
            f"\n[dim]No rate card configured, so no costs are shown. "
            f"`{CLI_NAME} domain usage --rates-init` writes one you can edit; "
            f"Keel ships no prices of its own.[/dim]")
        return
    if not report["projects"]:
        return

    table = Table(title="Cost — model calls only", show_lines=False)
    table.add_column("Project", no_wrap=True)
    table.add_column("Phase", no_wrap=True)
    table.add_column("Calls", justify="right", no_wrap=True)
    # "In"/"Out", matching the usage table above. "Read"/"Wrote" would read as
    # cache read and cache write in a table that is about billing, which is
    # exactly the pair a reader is primed for here.
    table.add_column("In", justify="right", no_wrap=True)
    table.add_column("Out", justify="right", no_wrap=True)
    table.add_column("Cost", justify="right", no_wrap=True)

    total = 0.0
    unpriced = 0
    for project, phases in sorted(report["projects"].items()):
        first = True
        for phase in phases:
            total += phase.cost
            unpriced += phase.unpriced_calls
            table.add_row(
                f"[bold]{project or '(unattributed)'}[/bold]" if first else "",
                phase.label,
                f"{phase.calls:,}",
                _thousands(phase.admitted),
                _thousands(phase.generated),
                # A phase with unpriced calls shows its cost as a floor, since
                # the models the card does not name contributed nothing to it.
                ("≥" if phase.unpriced_calls else "")
                + pricing.money(phase.cost, card.currency),
            )
            first = False
    console.print(table)
    console.print(f"[bold]{('≥' if unpriced else '')}"
                  f"{pricing.money(total, card.currency)}[/bold] total")

    age = f"{card.age_days} days old" if card.age_days is not None else "undated"
    style = "yellow" if card.stale else "dim"
    console.print(f"[{style}]Rates from {card.path}, as of "
                  f"{card.as_of or 'unknown'} ({age})"
                  + (" — re-check them before quoting this." if card.stale else "")
                  + f"[/{style}]")
    if report["unpriced_models"]:
        console.print(f"[yellow]{unpriced} call(s) on "
                      f"{', '.join(report['unpriced_models'])} are not in the "
                      f"rate card — they add nothing to the total.[/yellow]")


# ── sources (fan-out reverse index) ─────────────────────────────────────────

def sources_command(
    ref: Annotated[Optional[str], typer.Argument(
        help="A source ref, e.g. repo:svc/CONTRIBUTING.md. Omit to list them all.")] = None,
    product: Annotated[Optional[str], typer.Option(
        "--product", "-p", help="Limit to one product's domains")] = None,
    shared: Annotated[bool, typer.Option(
        "--shared", help="Only sources more than one domain draws on")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the index as JSON")] = False,
) -> None:
    """Which domains draw instructions from a source — the blast radius of an edit.

    Answer this before changing a shared file. `proposal.merge` decides
    fast-forward versus escalate for one domain; doing that across N is the
    merge-queue problem, and nothing could previously say which N.

    Citations live inside each domain's proposal, so this scans rather than
    reading an index. That is deliberate: proposals are small, domains number in
    the tens, and a stored index would be one more thing to keep in sync for a
    query nobody runs in a loop.
    """
    from agentic_cli.onboarding import fanout

    index = fanout.build(product=product or "")

    if ref:
        found = index.by_ref(ref)
        if found is None:
            console.print(f"[yellow]No domain cites {ref}.[/yellow]")
            _warn_unreadable(index)
            raise typer.Exit(0)
        if as_json:
            console.print_json(json.dumps(found.to_dict()))
            raise typer.Exit(0)
        _print_one(found)
        _warn_unreadable(index)
        raise typer.Exit(0)

    entries = index.shared if shared else sorted(
        index.sources.values(), key=lambda s: (-len(s.uses), -s.accepted, s.ref))
    if not entries:
        console.print("[yellow]No cited sources found"
                      + (" shared across domains" if shared else "") + ".[/yellow]")
        _warn_unreadable(index)
        raise typer.Exit(0)

    if as_json:
        console.print_json(json.dumps(
            {"sources": [e.to_dict() for e in entries],
             "unreadable": index.unreadable}))
        raise typer.Exit(0)

    table = Table(title="Sources by blast radius"
                        + (f" — {product}" if product else ""), show_lines=False)
    table.add_column("Source", overflow="fold")
    table.add_column("Domains", justify="right", no_wrap=True)
    table.add_column("Accepted", justify="right", no_wrap=True)
    table.add_column("Drawn on by", overflow="fold")
    for entry in entries:
        table.add_row(
            entry.ref,
            f"[bold]{len(entry.uses)}[/bold]" if entry.shared else str(len(entry.uses)),
            str(entry.accepted),
            ", ".join(entry.domains)
            + ("  [yellow]⚠ version skew[/yellow]" if entry.version_skew else ""),
        )
    console.print(table)
    skewed = [e for e in entries if e.version_skew]
    if skewed:
        console.print(f"[yellow]{len(skewed)} source(s) are cited at different "
                      f"versions by different domains[/yellow] [dim]— one "
                      f"extracted before a change the other absorbed, so they "
                      f"are not one decision.[/dim]")
    _warn_unreadable(index)

    record_activity(command="domain", subcommand="sources",
                    args={"product": product or "*", "sources": len(entries)})


def _print_one(found) -> None:
    table = Table(title=f"Domains drawing on {found.ref}", show_lines=False)
    table.add_column("Domain", no_wrap=True)
    table.add_column("Accepted", justify="right", no_wrap=True)
    table.add_column("Pending", justify="right", no_wrap=True)
    table.add_column("Cited at", overflow="fold")
    for use in sorted(found.uses, key=lambda u: (-u.accepted, u.domain)):
        table.add_row(use.domain, str(use.accepted), str(use.pending),
                      ", ".join(use.versions) or "[dim]unversioned[/dim]")
    console.print(table)
    if found.version_skew:
        console.print("[yellow]⚠ Cited at different versions[/yellow] [dim]— these "
                      "domains extracted at different times, so a change to this "
                      "source is not one decision for all of them.[/dim]")


def _warn_unreadable(index) -> None:
    """Unreadable is not unused, and under-reporting a blast radius is the
    direction that gets someone hurt."""
    if index.unreadable:
        console.print(f"[yellow]{len(index.unreadable)} domain(s) could not be "
                      f"read ({', '.join(index.unreadable)}) — they may cite this "
                      f"too. Unreadable is not unused.[/yellow]")


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
    domain_app.command("diff")(diff_command)
    domain_app.command("usage")(usage_command)
    domain_app.command("sources")(sources_command)


__all__ = ["register", "gather", "stale_repo_entries", "diff_domain",
           "KIND_FILES", "FILE_KINDS", "classify_docs",
           "extract_intent", "review", "finalize", "score", "diff_command",
           "usage_command", "sources_command"]
