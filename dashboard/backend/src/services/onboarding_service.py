"""Domain onboarding readiness, review, and drift — read models for the dashboard.

Delegates to ``agentic_cli.onboarding`` rather than reimplementing any of it:
the CLI is the single source of truth, and the review proposal on disk is the
single store. These functions shape that into what the wizard renders.

Long-running steps (``extract``, ``finalize``) are *not* here — they stream
through ``stream_domain_command`` like every other wizard step, so their logic
lives in exactly one place.

The knowledge map is the piece with no CLI equivalent. It answers a question a
table cannot: **where did this domain's knowledge come from, and where is drift
entering it?** Sources flow to instruction kinds, kinds flow to context files,
and every hop carries its own freshness — so a stale source and the artifacts
downstream of it light up together.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from agentic_cli.commands.domain_onboarding import FILE_KINDS
from agentic_cli.meta_repo.detector import detect_domain_meta_repo
from agentic_cli.onboarding import classify, extract, proposal, provenance
from agentic_cli.tracker import (
    get_domain,
    get_domain_docs,
    set_domain_doc_type,
    stale_domain_docs,
)


# ── models ──────────────────────────────────────────────────────────────────

class DocClassification(BaseModel):
    source_page_id: str
    title: Optional[str] = None
    doc_type: str
    confidence: float
    operational: bool
    stale: bool = False
    source_version: int = 0
    live_version: int = 0


class ReviewEntry(BaseModel):
    id: str
    kind: str
    status: str
    citation: str
    confidence: float
    text: str = ""
    proposed_text: str = ""
    risks: list[str] = []
    reason: str = ""
    held: bool = False
    pending: bool = False
    source_absent: bool = False


class ReviewProposal(BaseModel):
    domain: str
    generated_at: str = ""
    exists: bool = False
    counts: dict[str, int] = {}
    entries: list[ReviewEntry] = []


class VerdictRequest(BaseModel):
    accept: list[str] = []
    reject: list[str] = []


class VerdictResult(BaseModel):
    changed: int
    counts: dict[str, int]


class DriftSignal(BaseModel):
    """One drift source, normalised so the UI renders them uniformly."""

    key: str
    label: str
    count: int
    total: int = 0
    severity: str = "ok"          # ok | warn | fail
    detail: str = ""
    fix: str = ""


class KnowledgeNode(BaseModel):
    id: str
    label: str
    group: str                    # source | kind | artifact
    scheme: str = ""              # confluence | repo | ""
    count: int = 0
    reviewed: bool = False
    stale: bool = False
    held: int = 0
    pending: int = 0


class KnowledgeFlow(BaseModel):
    source: str
    target: str
    count: int
    stale: bool = False


class KnowledgeMap(BaseModel):
    domain: str
    nodes: list[KnowledgeNode] = []
    flows: list[KnowledgeFlow] = []
    totals: dict[str, int] = {}


# ── resolution ──────────────────────────────────────────────────────────────

def _meta(slug: str) -> Optional[Path]:
    if not get_domain(slug):
        return None
    return detect_domain_meta_repo(slug)


def _load(slug: str) -> tuple[Optional[Path], proposal.Proposal]:
    meta = _meta(slug)
    if meta is None:
        return None, proposal.Proposal(domain=slug)
    return meta, proposal.load(meta, slug)


# ── docs ────────────────────────────────────────────────────────────────────

def list_classified_docs(slug: str) -> list[DocClassification]:
    """Tracked docs with their type, classifying any that lack one."""
    stale_ids = {str(d["source_page_id"]) for d in stale_domain_docs(slug)}
    out: list[DocClassification] = []
    for doc in get_domain_docs(slug):
        page_id = str(doc.get("source_page_id") or "")
        doc_type = doc.get("doc_type")
        confidence = float(doc.get("doc_type_confidence") or 0.0)
        if not doc_type:
            verdict = classify.classify(doc.get("title") or "", doc.get("source_space_key") or "")
            doc_type, confidence = verdict.doc_type, verdict.confidence
        out.append(DocClassification(
            source_page_id=page_id,
            title=doc.get("title"),
            doc_type=doc_type,
            confidence=confidence,
            operational=doc_type in classify.OPERATIONAL,
            stale=page_id in stale_ids,
            source_version=int(doc.get("source_version") or 0),
            live_version=int(doc.get("live_version") or 0),
        ))
    return out


def set_doc_type(slug: str, page_id: str, doc_type: str) -> bool:
    """Record a reviewer's correction at full confidence."""
    if doc_type not in classify.ALL_TYPES:
        return False
    return set_domain_doc_type(slug, page_id, doc_type, 1.0)


# ── review ──────────────────────────────────────────────────────────────────

def _to_entry(entry: proposal.Entry) -> ReviewEntry:
    return ReviewEntry(
        id=entry.id, kind=entry.kind, status=entry.status,
        citation=entry.citation, confidence=entry.confidence,
        text=entry.text, proposed_text=entry.proposed_text,
        risks=list(entry.risks), reason=entry.reason,
        held=entry.held, pending=entry.pending,
        source_absent=entry.source_absent,
    )


def get_proposal(slug: str) -> ReviewProposal:
    meta, review = _load(slug)
    return ReviewProposal(
        domain=slug,
        generated_at=review.generated_at,
        exists=meta is not None and proposal.path_for(meta).is_file(),
        counts=review.counts,
        entries=[_to_entry(e) for e in review.entries],
    )


def record_verdicts(slug: str, request: VerdictRequest) -> Optional[VerdictResult]:
    """Apply accept/reject decisions to the proposal on disk.

    A held entry can never be accepted here, exactly as on the command line:
    its text was never written, so there is nothing to approve. Accepting a
    stale entry adopts the proposed replacement — that is what the reviewer is
    looking at when they click.
    """
    meta, review = _load(slug)
    if meta is None:
        return None

    by_id = {e.id: e for e in review.entries}
    changed = 0

    for entry_id in request.accept:
        entry = by_id.get(entry_id)
        if entry is None or entry.held:
            continue
        if entry.status == proposal.STALE and entry.proposed_text:
            entry.text, entry.proposed_text = entry.proposed_text, ""
        entry.status = proposal.ACCEPTED
        changed += 1

    for entry_id in request.reject:
        entry = by_id.get(entry_id)
        if entry is None:
            continue
        entry.status = proposal.REJECTED
        changed += 1

    if changed:
        proposal.save(meta, review)
    return VerdictResult(changed=changed, counts=review.counts)


# ── readiness ───────────────────────────────────────────────────────────────

def get_readiness(slug: str) -> Optional[dict]:
    """The scorecard, computed live rather than read from the saved copy."""
    from agentic_cli.commands.domain_onboarding import gather
    from agentic_cli.onboarding import readiness

    meta = _meta(slug)
    if meta is None:
        return None
    return readiness.score(gather(slug, meta)).to_dict()


# ── drift ───────────────────────────────────────────────────────────────────

def get_drift(slug: str) -> list[DriftSignal]:
    """Every drift signal for one domain, in one shape.

    Delegates to ``agentic_cli.onboarding.drift``, which owns the detectors so
    the watcher trigger and this page cannot disagree about what drift means.
    """
    from agentic_cli.onboarding import drift

    return [DriftSignal(**signal.to_dict()) for signal in drift.detect(slug)]


# ── knowledge map ───────────────────────────────────────────────────────────

def get_knowledge_map(slug: str) -> KnowledgeMap:
    """Where this domain's knowledge came from, and where drift enters it.

    Three columns — sources, instruction kinds, context artifacts — with a flow
    for each hop. Staleness propagates forward along the flows, so a source
    that moved upstream visibly taints everything built from it. That is the
    property a table of counts cannot show and the reason this exists.
    """
    meta, review = _load(slug)
    stale_pages = {str(d["source_page_id"]) for d in stale_domain_docs(slug)}
    doc_titles = {
        str(d["source_page_id"]): (d.get("title") or str(d["source_page_id"]))
        for d in get_domain_docs(slug)
    }

    nodes: dict[str, KnowledgeNode] = {}
    flows: dict[tuple[str, str], KnowledgeFlow] = {}

    def bump_flow(source: str, target: str, stale: bool) -> None:
        flow = flows.get((source, target))
        if flow is None:
            flows[(source, target)] = KnowledgeFlow(
                source=source, target=target, count=1, stale=stale)
        else:
            flow.count += 1
            flow.stale = flow.stale or stale

    for entry in review.entries:
        citation = extract.Citation.parse(entry.citation)
        source_id = f"src:{citation.scheme}:{citation.ref}"
        kind_id = f"kind:{entry.kind}"
        is_stale = citation.scheme == "confluence" and citation.ref in stale_pages

        label = (
            doc_titles.get(citation.ref, citation.ref)
            if citation.scheme == "confluence" else citation.ref.rsplit("/", 1)[-1]
        )
        source = nodes.setdefault(source_id, KnowledgeNode(
            id=source_id, label=label, group="source", scheme=citation.scheme,
            stale=is_stale))
        kind = nodes.setdefault(kind_id, KnowledgeNode(
            id=kind_id, label=entry.kind, group="kind"))

        source.count += 1
        kind.count += 1
        if entry.held:
            source.held += 1
            kind.held += 1
        if entry.pending:
            source.pending += 1
            kind.pending += 1
        if entry.status == proposal.ACCEPTED and not entry.held:
            bump_flow(source_id, kind_id, is_stale)

    if meta is not None:
        for stamp in provenance.scan(meta / ".domain"):
            artifact_id = f"art:{stamp.path.name}"
            nodes[artifact_id] = KnowledgeNode(
                id=artifact_id, label=stamp.path.name, group="artifact",
                scheme=stamp.provenance, reviewed=stamp.reviewed,
                stale=not stamp.real,
            )
            # Authoritative mapping from the writer, not a filename heuristic.
            kind = FILE_KINDS.get(stamp.path.name)
            if kind and f"kind:{kind}" in nodes:
                bump_flow(f"kind:{kind}", artifact_id, not stamp.real)

    return KnowledgeMap(
        domain=slug,
        nodes=sorted(nodes.values(), key=lambda n: (n.group, n.label)),
        flows=list(flows.values()),
        totals={
            "sources": sum(1 for n in nodes.values() if n.group == "source"),
            "kinds": sum(1 for n in nodes.values() if n.group == "kind"),
            "artifacts": sum(1 for n in nodes.values() if n.group == "artifact"),
            "instructions": len(review.entries),
            "accepted": len(review.accepted),
            "held": len(review.held),
            "pending": len(review.pending),
        },
    )
