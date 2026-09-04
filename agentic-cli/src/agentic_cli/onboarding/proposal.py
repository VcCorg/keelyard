"""The review proposal — git-visible, defaulting to unreviewed.

Finalization is an onboarding step, not an audit afterthought. ``domain extract``
proposes, the team that owns the domain reviews, ``domain finalize`` accepts:

    keel domain add-docs      # track pages
    keel domain extract       # in-memory read → this file
          ← the team reviews and edits
    keel domain finalize      # accept the reviewed set into .domain/

This file is the source of truth. A dashboard screen and a CLI picker are
editors over it, not parallel stores — which is what makes reviewing it as a
pull request the natural default: the team reviews its own instructions the way
it reviews its own onboarding guide.

Three invariants:

- **Nothing lands silently.** Every new candidate is written ``unreviewed``;
  only ``finalize`` acts on ``accepted``.
- **Held text is never written.** :meth:`Candidate.to_dict` omits the text of a
  risky candidate, and :func:`merge` never resurrects it. The reviewer gets the
  risk kinds and the citation and reads the source.
- **Re-extraction preserves human decisions.** A verdict survives until its
  source moves; when it does, the entry becomes ``stale`` and carries the
  proposed replacement beside the text that was approved, so the reviewer sees a
  diff rather than a silent overwrite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml

from agentic_cli.onboarding.extract import KIND_ORDER, Candidate, Citation

SCHEMA = "keel-onboarding-proposal/v1"

#: Written by ``extract``; ignored by ``finalize``.
UNREVIEWED = "unreviewed"
#: A human approved this instruction. ``finalize`` writes it into the domain.
ACCEPTED = "accepted"
#: A human rejected it. Never re-proposed unless its source changes.
REJECTED = "rejected"
#: Approved once, but its source has moved since. Needs a fresh decision.
STALE = "stale"

STATUSES = (UNREVIEWED, ACCEPTED, REJECTED, STALE)

#: Statuses a reviewer still owes a decision on.
PENDING = frozenset({UNREVIEWED, STALE})

PROPOSAL_REL = ".platform/onboarding/proposal.yaml"


@dataclass
class Entry:
    """One reviewable instruction and its verdict."""

    id: str
    kind: str
    citation: str
    status: str = UNREVIEWED
    text: str = ""
    confidence: float = 0.5
    abstracted: bool = False
    # Set when held: risk kinds only, never the matched text.
    risks: list[str] = field(default_factory=list)
    reason: str = ""
    # Set when the source moved after approval.
    proposed_text: str = ""
    # Set when a previously approved instruction no longer appears at its source.
    source_absent: bool = False

    @property
    def held(self) -> bool:
        return bool(self.risks)

    @property
    def pending(self) -> bool:
        return self.status in PENDING

    @classmethod
    def from_candidate(cls, candidate: Candidate, status: str = UNREVIEWED) -> "Entry":
        data = candidate.to_dict()
        return cls(
            id=data["id"],
            kind=data["kind"],
            citation=data["citation"],
            status=status,
            text=data.get("text", ""),
            confidence=data.get("confidence", 0.5),
            abstracted=data.get("abstracted", False),
            risks=list(data.get("risks", [])),
            reason=data.get("reason", ""),
        )

    def to_dict(self) -> dict:
        out: dict = {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "citation": self.citation,
            "confidence": self.confidence,
        }
        if self.held:
            out["risks"] = list(self.risks)
            out["reason"] = self.reason
        else:
            out["text"] = self.text
            if self.abstracted:
                out["abstracted"] = True
        if self.proposed_text:
            out["proposed_text"] = self.proposed_text
        if self.source_absent:
            out["source_absent"] = True
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Entry":
        return cls(
            id=str(data.get("id") or ""),
            kind=str(data.get("kind") or ""),
            citation=str(data.get("citation") or ""),
            status=str(data.get("status") or UNREVIEWED),
            text=str(data.get("text") or ""),
            confidence=float(data.get("confidence") or 0.5),
            abstracted=bool(data.get("abstracted")),
            risks=list(data.get("risks") or []),
            reason=str(data.get("reason") or ""),
            proposed_text=str(data.get("proposed_text") or ""),
            source_absent=bool(data.get("source_absent")),
        )


@dataclass
class Proposal:
    """Every reviewable instruction for one domain."""

    domain: str
    entries: list[Entry] = field(default_factory=list)
    generated_at: str = ""

    @property
    def accepted(self) -> list[Entry]:
        return [e for e in self.entries if e.status == ACCEPTED and not e.held]

    @property
    def pending(self) -> list[Entry]:
        return [e for e in self.entries if e.pending]

    @property
    def held(self) -> list[Entry]:
        return [e for e in self.entries if e.held]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for status in STATUSES:
            n = sum(1 for e in self.entries if e.status == status)
            if n:
                out[status] = n
        return out

    def by_kind(self, kind: str) -> list[Entry]:
        return [e for e in self.entries if e.kind == kind]

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "domain": self.domain,
            "generated_at": self.generated_at,
            "entries": [e.to_dict() for e in _sorted(self.entries)],
        }


def _sorted(entries: Iterable[Entry]) -> list[Entry]:
    """Pending first, then by kind — a reviewer's worklist, not a data dump."""
    order = {k: i for i, k in enumerate(KIND_ORDER)}
    return sorted(
        entries,
        key=lambda e: (not e.pending, order.get(e.kind, 99), -e.confidence, e.id),
    )


def path_for(meta_repo: Path) -> Path:
    return Path(meta_repo) / PROPOSAL_REL


def load(meta_repo: Path, domain: str = "") -> Proposal:
    """Read the proposal, or an empty one if none exists."""
    path = path_for(meta_repo)
    if not path.is_file():
        return Proposal(domain=domain)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return Proposal(domain=domain)
    return Proposal(
        domain=str(data.get("domain") or domain),
        generated_at=str(data.get("generated_at") or ""),
        entries=[Entry.from_dict(d) for d in (data.get("entries") or [])],
    )


def save(meta_repo: Path, proposal: Proposal) -> Path:
    """Write the proposal, creating ``.platform/onboarding/`` if needed."""
    path = path_for(meta_repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    proposal.generated_at = datetime.now(timezone.utc).isoformat()
    path.write_text(
        "# Reviewed and finalized by the team that owns this domain.\n"
        "# Set `status: accepted` on the instructions that are correct, then run\n"
        "# `keel domain finalize <domain>`. Held entries carry no text by design —\n"
        "# follow the citation and read the source.\n"
        + yaml.safe_dump(proposal.to_dict(), sort_keys=False, width=88,
                         allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    return path


def merge(existing: Proposal, candidates: list[Candidate], domain: str) -> Proposal:
    """Fold a fresh extraction into an existing proposal, preserving verdicts.

    A verdict survives until its source moves. When the citation for an approved
    instruction gains a new version and the text changed with it, the entry
    becomes ``stale`` and carries the replacement beside the approved text — the
    same fast-forward/escalate split ``template upgrade`` uses, applied to
    knowledge instead of files.
    """
    by_id = {e.id: e for e in existing.entries}
    # Approved entries indexed by what they were extracted from, so a source
    # that moves can be matched even though the id (which hashes the text) moved.
    approved_by_source: dict[tuple[str, str], Entry] = {
        (e.kind, Citation.parse(e.citation).ref): e
        for e in existing.entries
        if e.status in (ACCEPTED, STALE) and not e.held
    }

    merged: list[Entry] = []
    seen_ids: set[str] = set()
    matched_sources: set[tuple[str, str]] = set()

    for candidate in candidates:
        fresh = Entry.from_candidate(candidate)
        seen_ids.add(fresh.id)

        prior = by_id.get(fresh.id)
        if prior is not None:
            # Same instruction, same source: keep the human's decision.
            fresh.status = prior.status
            fresh.source_absent = False
            merged.append(fresh)
            matched_sources.add((fresh.kind, Citation.parse(fresh.citation).ref))
            continue

        source_key = (fresh.kind, Citation.parse(fresh.citation).ref)
        approved = approved_by_source.get(source_key)
        if approved is not None and not fresh.held:
            # The source moved and the instruction changed with it. Show the
            # reviewer both, rather than overwriting an approved instruction.
            matched_sources.add(source_key)
            merged.append(Entry(
                id=approved.id, kind=approved.kind, citation=fresh.citation,
                status=STALE, text=approved.text, confidence=fresh.confidence,
                abstracted=approved.abstracted, proposed_text=fresh.text,
            ))
            continue

        merged.append(fresh)

    # An approved instruction its source no longer yields is not silently
    # dropped — a human decides whether it stopped being true or merely moved.
    for entry in existing.entries:
        if entry.id in seen_ids:
            continue
        source_key = (entry.kind, Citation.parse(entry.citation).ref)
        if source_key in matched_sources:
            continue
        if entry.status == ACCEPTED and not entry.held:
            entry.source_absent = True
            merged.append(entry)
        elif entry.status == REJECTED:
            # Remember rejections so the next extract does not re-propose them.
            merged.append(entry)

    return Proposal(domain=domain, entries=merged,
                    generated_at=existing.generated_at)


__all__ = [
    "SCHEMA", "UNREVIEWED", "ACCEPTED", "REJECTED", "STALE", "STATUSES",
    "PENDING", "PROPOSAL_REL", "Entry", "Proposal", "path_for", "load", "save",
    "merge",
]
