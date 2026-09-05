"""Every drift signal for a domain, in one shape, from one place.

Three detectors existed and had never been introduced to each other: template
drift (a three-way hash over the meta-repo), doc freshness (an upstream version
comparison), and the review backlog (instructions whose source moved). They are
the same question asked of three corpora, so they belong behind one interface.

This lives in the CLI rather than the dashboard for two reasons. The dashboard
imports ``agentic_cli`` and not the reverse, so a watcher trigger — which runs
in the CLI — could not otherwise see drift at all. And a detector registry in
the dashboard would mean a second one in the CLI the first time anything
non-visual needed to know.

Detectors are registered, not branched: adding a source is a
:func:`register_detector` call, not another arm in a dispatch chain. A detector
that raises is reported as an unavailable signal rather than being allowed to
take the whole report down — a drift read must never be the reason a page or a
poll fails.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

OK = "ok"
WARN = "warn"
FAIL = "fail"

#: Severity ordering, least to most urgent.
SEVERITY_ORDER = (OK, WARN, FAIL)


@dataclass
class DriftSignal:
    """One drift source's verdict for one domain."""

    key: str
    label: str
    count: int = 0
    total: int = 0
    severity: str = OK
    detail: str = ""
    fix: str = ""

    @property
    def actionable(self) -> bool:
        return self.severity != OK

    def at_least(self, minimum: str) -> bool:
        """True when this signal is at or above ``minimum`` severity."""
        try:
            return SEVERITY_ORDER.index(self.severity) >= SEVERITY_ORDER.index(minimum)
        except ValueError:
            return self.actionable

    def to_dict(self) -> dict:
        return {
            "key": self.key, "label": self.label, "count": self.count,
            "total": self.total, "severity": self.severity,
            "detail": self.detail, "fix": self.fix,
        }


#: A detector takes a domain slug and returns one signal, or None when it has
#: nothing to say about this domain (no meta-repo, source not configured).
Detector = Callable[[str], Optional[DriftSignal]]

_DETECTORS: dict[str, Detector] = {}


def register_detector(key: str, detector: Detector) -> None:
    """Register (or replace) a detector. Idempotent, so tests can swap one in."""
    _DETECTORS[key] = detector


def detector_keys() -> list[str]:
    return sorted(_DETECTORS)


def detect(slug: str, keys: Optional[list[str]] = None) -> list[DriftSignal]:
    """Run every registered detector for one domain.

    A detector that raises becomes an ``unavailable`` signal naming itself,
    never an exception: callers are a dashboard page and a background poll, and
    neither should fail because one source is misconfigured.
    """
    wanted = set(keys) if keys else None
    signals: list[DriftSignal] = []
    for key in sorted(_DETECTORS):
        if wanted is not None and key not in wanted:
            continue
        try:
            signal = _DETECTORS[key](slug)
        except Exception as exc:  # noqa: BLE001 - see docstring
            logger.debug("drift detector %s failed for %s: %s", key, slug, exc)
            signals.append(DriftSignal(
                key=key, label=key.replace("-", " ").capitalize(),
                severity=WARN, detail="This detector could not run.",
                fix="Check its source is configured; drift for it is unknown, "
                    "not clear.",
            ))
            continue
        if signal is not None:
            signals.append(signal)
    return signals


def worst(signals: list[DriftSignal]) -> str:
    """The most urgent severity present."""
    return max((s.severity for s in signals),
               key=lambda v: SEVERITY_ORDER.index(v) if v in SEVERITY_ORDER else 0,
               default=OK)


# ── Built-in detectors ──────────────────────────────────────────────────────

def _meta(slug: str) -> Optional[Path]:
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    return detect_domain_meta_repo(slug)


def _review(slug: str):
    from agentic_cli.onboarding import proposal

    meta = _meta(slug)
    return proposal.load(meta, slug) if meta else proposal.Proposal(domain=slug)


def docs_detector(slug: str) -> Optional[DriftSignal]:
    """Tracked pages whose upstream version moved past what we read."""
    from agentic_cli.tracker import get_domain_docs, stale_domain_docs

    docs = get_domain_docs(slug)
    if not docs:
        return None
    stale = stale_domain_docs(slug)
    # A doc never checked is unknown, not fresh — it warns rather than passing.
    unchecked = sum(1 for d in docs if not (d.get("live_version") or 0))
    return DriftSignal(
        key="docs", label="Tracked docs moved upstream",
        count=len(stale), total=len(docs),
        severity=FAIL if stale else (WARN if unchecked else OK),
        detail=(f"{len(stale)} of {len(docs)} changed since we read them"
                + (f"; {unchecked} never checked" if unchecked else "")),
        fix=f"Re-run `keel domain extract {slug}` to re-read the changed pages.",
    )


def instructions_detector(slug: str) -> Optional[DriftSignal]:
    """Instructions still owed a human decision."""
    from agentic_cli.onboarding import proposal

    review = _review(slug)
    if not review.entries:
        return None
    stale = [e for e in review.entries if e.status == proposal.STALE]
    absent = [e for e in review.entries if e.source_absent]
    pending = review.pending
    return DriftSignal(
        key="instructions", label="Instructions needing a decision",
        count=len(pending), total=len(review.entries),
        severity=FAIL if (stale or absent) else (WARN if pending else OK),
        detail=(f"{len(pending)} pending"
                + (f", {len(stale)} superseded by a changed source" if stale else "")
                + (f", {len(absent)} no longer at their source" if absent else "")),
        fix=f"Clear the queue with `keel domain review {slug}`, then finalize.",
    )


def repo_sources_detector(slug: str) -> Optional[DriftSignal]:
    """Accepted instructions whose repo file has changed since extraction.

    Warns rather than fails, now that ``semantic`` can say what the change did.
    A moved digest means *look here* — a typo fix moves it exactly as far as a
    reversed step — and calling that a failure spent the loudest severity on the
    question nobody can act on. The failure belongs to the detector that knows
    whether the instruction survived.
    """
    from agentic_cli.commands.domain_onboarding import stale_repo_entries

    review = _review(slug)
    accepted = review.accepted
    if not accepted:
        return None
    stale = stale_repo_entries(slug, review)
    return DriftSignal(
        key="repo-sources", label="Accepted instructions over changed repo files",
        count=len(stale), total=len(accepted),
        severity=WARN if stale else OK,
        detail=(f"{len(stale)} instruction(s) we vouched for cite a file that "
                "has changed since" if stale
                else f"all {len(accepted)} accepted instruction(s) match their source"),
        fix=f"`keel domain diff {slug}` says which of them the change touched.",
    )


def semantic_detector(slug: str) -> Optional[DriftSignal]:
    """Of the sources that moved, which moves actually broke an instruction?

    Runs without a judge on purpose. This is called from a dashboard page load
    and a watcher poll, where a model call is latency nobody asked for and cost
    nobody approved. Offline it still catches the case worth catching — a
    negation appearing or disappearing — and everything else it can only call an
    unverified reword, which asks a human rather than guessing.
    """
    from agentic_cli.commands.domain_onboarding import diff_domain
    from agentic_cli.onboarding import differ

    review = _review(slug)
    if not review.accepted:
        return None
    report = diff_domain(slug, review)
    if not report.verdicts:
        # Nothing moved. Distinct from "moved and turned out fine", which is why
        # this says nothing rather than reporting a clean sweep of zero.
        return None

    contradicted = report.of(differ.CONTRADICTED)
    absent = report.of(differ.ABSENT)
    unverified = [v for v in report.of(differ.REWORDED) if not v.checked]
    unknown = report.of(differ.UNKNOWN)

    parts = []
    if contradicted:
        parts.append(f"{len(contradicted)} contradicted by their source")
    if absent:
        parts.append(f"{len(absent)} no longer supported there")
    if unverified:
        parts.append(f"{len(unverified)} reworded, unverified")
    if unknown:
        parts.append(f"{len(unknown)} unreadable")
    settled = len(report.settled)
    if settled:
        parts.append(f"{settled} unaffected")

    return DriftSignal(
        key="semantic", label="What the source changes did to our instructions",
        count=len(contradicted) + len(absent) + len(unverified),
        total=len(report.verdicts),
        severity=(FAIL if (contradicted or absent)
                  else (WARN if unverified else OK)),
        detail="; ".join(parts),
        fix=f"`keel domain diff {slug}` shows each one beside its source's "
            f"current wording.",
    )


def template_detector(slug: str) -> Optional[DriftSignal]:
    """Meta-repo files against a fresh render of the template that made them."""
    from agentic_cli.meta_repo import template_drift

    meta = _meta(slug)
    if meta is None:
        return None
    try:
        report = template_drift.classify(meta, domain=slug)
    except FileNotFoundError:
        return None
    conflicted, upgradable = len(report.conflicted), len(report.upgradable)
    return DriftSignal(
        key="template", label="Template drift",
        count=conflicted + upgradable, total=len(report.entries),
        severity=FAIL if conflicted else (WARN if upgradable else OK),
        detail=(f"{upgradable} can fast-forward"
                + (f", {conflicted} need a decision" if conflicted else "")),
        fix=f"`keel domain template upgrade {slug}` for the safe ones.",
    )


def placeholder_detector(slug: str) -> Optional[DriftSignal]:
    """Context files still carrying the scaffold's filler."""
    from agentic_cli.onboarding import provenance

    meta = _meta(slug)
    if meta is None:
        return None
    summary = provenance.summarize(provenance.scan(meta / ".domain"))
    if not summary["total"]:
        return None
    filler = summary["placeholder"] + summary["unknown"]
    return DriftSignal(
        key="placeholder", label="Context files without real content",
        count=filler, total=summary["total"],
        severity=FAIL if summary["placeholder"] else (WARN if filler else OK),
        detail=f"{summary['real']} of {summary['total']} carry real content; "
               f"{summary['reviewed']} reviewed",
        fix="Run extract, review the proposal, then finalize.",
    )


for _key, _fn in (
    ("docs", docs_detector),
    ("instructions", instructions_detector),
    ("repo-sources", repo_sources_detector),
    ("semantic", semantic_detector),
    ("template", template_detector),
    ("placeholder", placeholder_detector),
):
    register_detector(_key, _fn)


__all__ = [
    "OK", "WARN", "FAIL", "SEVERITY_ORDER", "DriftSignal", "Detector",
    "register_detector", "detector_keys", "detect", "worst",
]
