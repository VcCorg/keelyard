"""Is this domain ready to build on?

**A domain is ready when a competent new teammate could ship from it.** That is
the question teams already apply to their own onboarding documentation, so it is
the one worth scoring — and every dimension below maps to a signal we can compute
from data the platform already holds.

Before this, the only quality signal the whole onboarding pipeline emitted was::

    ✓ KG domain context retrieved (3/6 aspects)

— a count of non-empty strings. ``validate_product_meta`` is structural and
product-scoped, so nothing measured whether a *domain's* context was sufficient.

Two properties keep the score honest:

**Deterministic by default.** Seven of the eight dimensions need no model and no
credential, so the score runs in test mode, in CI, and offline. Answerability
needs an LLM judge, and reports ``SKIPPED`` rather than failing closed — a
missing credential must never look like a failing domain.

**Scoring is pure.** :func:`score` takes a :class:`Inputs` and returns a
scorecard; :func:`gather` is the only part that touches the tracker and the
filesystem. Tests exercise the rubric without a database.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agentic_cli.onboarding import classify, extract, provenance, proposal

OK = "ok"
WARN = "warn"
FAIL = "fail"
SKIPPED = "skipped"

#: At or above this a dimension is healthy; below the lower bound it fails.
_OK_AT = 75.0
_WARN_AT = 40.0

#: Default bar for "ready to build on". Deliberately not 100: a domain with
#: solid setup, ownership and hazards but a thin glossary is still workable.
READY_AT = 70.0


@dataclass
class Dimension:
    """One rubric row: what a new teammate would ask, and how we did."""

    key: str
    label: str
    question: str
    status: str
    score: Optional[float] = None
    detail: str = ""
    fix: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "question": self.question,
            "status": self.status,
            "score": None if self.score is None else round(self.score, 1),
            "detail": self.detail,
            "fix": self.fix,
        }


@dataclass
class Inputs:
    """Everything the rubric needs, gathered once so scoring stays pure."""

    domain: str
    meta_repo: Optional[Path] = None
    # Tracked docs (``domain_docs`` rows) and their classifications.
    docs: list[dict] = field(default_factory=list)
    classifications: dict[str, classify.Classification] = field(default_factory=dict)
    # Linked repos, each optionally carrying ``has_codeowners``.
    repos: list[dict] = field(default_factory=list)
    # The reviewed instruction set.
    review: Optional[proposal.Proposal] = None
    # Stamps for every ``.domain/`` file.
    stamps: list[provenance.Stamp] = field(default_factory=list)
    # ``governance.yaml`` as loaded from the meta-repo.
    governance: dict = field(default_factory=dict)
    # Docs whose upstream version moved since we last looked.
    stale_docs: int = 0
    # True when an LLM judge is configured, enabling answerability.
    judge_available: bool = False


@dataclass
class Scorecard:
    """The eight-dimension verdict for one domain."""

    domain: str
    dimensions: list[Dimension] = field(default_factory=list)
    generated_at: str = ""

    @property
    def scored(self) -> list[Dimension]:
        return [d for d in self.dimensions if d.score is not None]

    @property
    def overall(self) -> Optional[float]:
        """Weighted mean of the dimensions that could be scored."""
        scored = self.scored
        if not scored:
            return None
        total_weight = sum(d.weight for d in scored)
        return sum(d.score * d.weight for d in scored) / total_weight

    @property
    def grade(self) -> str:
        value = self.overall
        if value is None:
            return "n/a"
        for bound, letter in ((90, "A"), (80, "B"), (70, "C"), (55, "D")):
            if value >= bound:
                return letter
        return "F"

    def ready(self, threshold: float = READY_AT) -> bool:
        """True when the domain clears the bar and nothing outright failed."""
        value = self.overall
        return value is not None and value >= threshold and not self.failed

    @property
    def failed(self) -> bool:
        return any(d.status == FAIL for d in self.dimensions)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for status in (FAIL, WARN, OK, SKIPPED):
            n = sum(1 for d in self.dimensions if d.status == status)
            if n:
                out[status] = n
        return out

    def to_dict(self) -> dict:
        return {
            "schema": "keel-domain-readiness/v1",
            "domain": self.domain,
            "generated_at": self.generated_at,
            "overall": None if self.overall is None else round(self.overall, 1),
            "grade": self.grade,
            "ready": self.ready(),
            "counts": self.counts,
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


def _status_for(score: float) -> str:
    if score >= _OK_AT:
        return OK
    return WARN if score >= _WARN_AT else FAIL


def _share(part: int, whole: int) -> float:
    return 100.0 * part / whole if whole else 0.0


def _accepted(review: Optional[proposal.Proposal], kind: str) -> list[proposal.Entry]:
    if review is None:
        return []
    return [e for e in review.accepted if e.kind == kind]


def score(inputs: Inputs) -> Scorecard:
    """Apply the rubric. Pure: no I/O, no model calls."""
    card = Scorecard(
        domain=inputs.domain,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    card.dimensions = [
        _orientation(inputs),
        _runnable(inputs),
        _ownership(inputs),
        _path_to_prod(inputs),
        _hazards(inputs),
        _answerability(inputs),
        _groundedness(inputs),
        _freshness(inputs),
    ]
    return card


# ── Dimensions ──────────────────────────────────────────────────────────────

def _orientation(i: Inputs) -> Dimension:
    """What is this domain, and what words does it use?"""
    terms = _accepted(i.review, extract.GLOSSARY)
    # Ten defined terms is a working vocabulary; more is better but not linearly.
    value = min(100.0, _share(len(terms), 10))
    return Dimension(
        "orientation", "Orientation", "What is this domain, and what words does it use?",
        _status_for(value), value,
        detail=f"{len(terms)} defined term(s)",
        fix="Add a glossary section to an onboarding doc, then re-run extract.",
    )


def _runnable(i: Inputs) -> Dimension:
    """Can I get it running today?"""
    steps = _accepted(i.review, extract.SETUP)
    repos = len(i.repos) or 1
    # Three setup instructions per linked repo is a plausible bar for "runnable".
    value = min(100.0, _share(len(steps), 3 * repos))
    return Dimension(
        "runnable", "Runnable", "Can I get it running today?",
        _status_for(value), value,
        detail=f"{len(steps)} setup instruction(s) for {len(i.repos)} repo(s)",
        fix="Track the team's environment-setup page with `domain add-docs`, "
            "then extract and accept its steps.",
        weight=1.5,
    )


def _ownership(i: Inputs) -> Dimension:
    """Where is ownership recorded? A pointer, never a person."""
    pointers = _accepted(i.review, extract.OWNERSHIP)
    with_codeowners = sum(1 for r in i.repos if r.get("has_codeowners"))
    covered = min(len(i.repos), max(len(pointers), with_codeowners))
    value = _share(covered, len(i.repos)) if i.repos else _share(len(pointers), 1)
    return Dimension(
        "ownership", "Ownership", "Where is ownership recorded?",
        _status_for(value), min(100.0, value),
        detail=f"{covered}/{len(i.repos)} repo(s) with a durable owner pointer"
               if i.repos else f"{len(pointers)} owner pointer(s)",
        fix="Add CODEOWNERS to each repo, or name the owning team (not a person) "
            "in the onboarding doc.",
    )


def _path_to_prod(i: Inputs) -> Dimension:
    """How does my change reach users?"""
    promotion = i.governance.get("promotion_path") or []
    gate_map = i.governance.get("checkpoint_gate_map") or []
    value = 0.0
    if promotion:
        value += 60.0
    if gate_map:
        value += 40.0
    return Dimension(
        "path_to_prod", "Path to prod", "How does my change reach users?",
        _status_for(value), value,
        detail=f"{len(promotion)} promotion stage(s), {len(gate_map)} gate mapping(s)",
        fix="Populate promotion_path and checkpoint_gate_map in "
            ".platform/config/governance.yaml.",
    )


def _hazards(i: Inputs) -> Dimension:
    """What will bite me?"""
    warnings = _accepted(i.review, extract.HAZARD)
    runbooks = sum(
        1 for c in i.classifications.values() if c.doc_type == classify.RUNBOOK
    )
    value = min(100.0, _share(len(warnings), 5) * 0.7 + _share(runbooks, 2) * 0.3)
    return Dimension(
        "hazards", "Hazards", "What will bite me?",
        _status_for(value), value,
        detail=f"{len(warnings)} recorded hazard(s), {runbooks} runbook(s)",
        fix="Track the team's runbook or troubleshooting page and accept its warnings.",
    )


def _answerability(i: Inputs) -> Dimension:
    """Could I answer the questions a new joiner asks in week one?

    The load-bearing dimension, and the only one needing a model. A missing
    judge credential reports SKIPPED — never FAIL, which would make an
    unconfigured environment look like an unready domain.
    """
    if not i.judge_available:
        return Dimension(
            "answerability", "Answerability",
            "Could I answer a new joiner's week-one questions?",
            SKIPPED, None,
            detail="No LLM judge configured.",
            fix="Configure a model provider to enable persona-question scoring.",
            weight=2.0,
        )
    return Dimension(
        "answerability", "Answerability",
        "Could I answer a new joiner's week-one questions?",
        SKIPPED, None,
        detail="Judge configured; persona-question scoring not yet wired.",
        fix="",
        weight=2.0,
    )


def _groundedness(i: Inputs) -> Dimension:
    """Has a human stood behind this? Three-state, not two."""
    summary = provenance.summarize(i.stamps)
    total = summary["total"]
    review = i.review
    reviewed_share = (
        _share(len(review.accepted), len(review.entries)) if review and review.entries else 0.0
    )
    context_share = _share(summary["real"], total) if total else 0.0
    # Real content is the floor; human review is what lifts it.
    value = context_share * 0.5 + reviewed_share * 0.5
    detail = (
        f"{summary['real']}/{total} context file(s) carry real content; "
        f"{len(review.accepted) if review else 0} instruction(s) finalized"
    )
    return Dimension(
        "groundedness", "Groundedness", "Has a human stood behind this?",
        _status_for(value), value, detail=detail,
        fix="Run `domain extract`, review the proposal, then `domain finalize`.",
        weight=1.5,
    )


def _freshness(i: Inputs) -> Dimension:
    """Is it still true?"""
    docs = len(i.docs)
    stale = i.stale_docs
    pending = len(i.review.pending) if i.review else 0
    value = 100.0 - _share(stale, docs) if docs else 0.0
    if pending:
        # Instructions awaiting a decision are unresolved drift, not neutral.
        value = max(0.0, value - min(30.0, pending * 3.0))
    return Dimension(
        "freshness", "Freshness", "Is it still true?",
        _status_for(value), value,
        detail=f"{stale}/{docs} tracked doc(s) moved upstream; "
               f"{pending} instruction(s) pending review",
        fix="Re-run `domain extract` and clear the pending queue.",
    )


__all__ = [
    "OK", "WARN", "FAIL", "SKIPPED", "READY_AT", "Dimension", "Inputs",
    "Scorecard", "score",
]
