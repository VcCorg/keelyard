"""Which domains draw on a source — the question you want answered before editing it.

`proposal.merge` decides fast-forward versus escalate for **one** domain. The
merge-queue problem is the same decision across N, and the plan for it calls that
a fan-out rather than a new algorithm. This is the piece that has to exist first:
nothing today can answer *which domains cite this file*.

The reason nothing can is structural. Citations live inside each domain's
``proposal.yaml``, in that domain's own meta-repo, so the index runs the only
direction available — enumerate domains, read each proposal, group by citation
ref. That is a scan, and it is fine: proposals are small YAML files and an
organisation has tens of domains, not millions. Building a stored reverse index
would add a thing to keep in sync for a query nobody runs in a loop.

**Useful before any of the fan-out machinery exists.** "If I edit this file, who
do I affect?" is worth answering on its own, and answering it is most of the work
of answering "what would this change do to them".

Two findings this surfaces that were previously invisible:

**Unreadable is not unused.** A domain whose meta-repo cannot be read tells us
nothing about whether it cites a source. Counting it as a non-user would
under-report the blast radius of a change, which is the direction that gets
someone hurt — so those domains are returned separately and never as zero.

**Version skew.** Two domains citing the same source at different versions
extracted it at different times, so one of them is reasoning about text the other
has already moved past. Nothing flagged that before, and it is exactly the
condition a fan-out has to handle rather than assume away.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SourceUse:
    """One domain's use of one source."""

    domain: str
    ref: str
    scheme: str
    accepted: int = 0
    pending: int = 0
    versions: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return self.accepted + self.pending

    def to_dict(self) -> dict:
        return {"domain": self.domain, "ref": self.ref, "scheme": self.scheme,
                "accepted": self.accepted, "pending": self.pending,
                "versions": list(self.versions)}


@dataclass
class SourceFanout:
    """Every domain drawing on one source, and what that costs to change."""

    ref: str
    scheme: str
    uses: list[SourceUse] = field(default_factory=list)

    @property
    def domains(self) -> list[str]:
        return sorted(u.domain for u in self.uses)

    @property
    def shared(self) -> bool:
        return len(self.uses) > 1

    @property
    def accepted(self) -> int:
        return sum(u.accepted for u in self.uses)

    @property
    def pending(self) -> int:
        return sum(u.pending for u in self.uses)

    @property
    def cited_versions(self) -> tuple[str, ...]:
        found: set[str] = set()
        for use in self.uses:
            found.update(v for v in use.versions if v)
        return tuple(sorted(found))

    @property
    def version_skew(self) -> bool:
        """True when domains cite this source at different versions.

        One of them extracted before a change the other already absorbed, so a
        fan-out cannot treat them as one decision. Worth surfacing on its own —
        it is a real inconsistency nobody could see before.
        """
        return len(self.cited_versions) > 1

    def to_dict(self) -> dict:
        return {"ref": self.ref, "scheme": self.scheme,
                "domains": self.domains, "shared": self.shared,
                "accepted": self.accepted, "pending": self.pending,
                "versions": list(self.cited_versions),
                "version_skew": self.version_skew,
                "uses": [u.to_dict() for u in self.uses]}


@dataclass
class Index:
    """The whole reverse index, plus the domains we could not ask."""

    sources: dict[str, SourceFanout] = field(default_factory=dict)
    #: Domains whose proposal could not be read. Kept apart from the counts
    #: because "we could not ask" and "does not use it" are different answers
    #: and only one of them is safe to act on.
    unreadable: list[str] = field(default_factory=list)

    @property
    def shared(self) -> list[SourceFanout]:
        """Sources more than one domain draws on, widest blast radius first."""
        return sorted((s for s in self.sources.values() if s.shared),
                      key=lambda s: (-len(s.uses), -s.accepted, s.ref))

    def by_ref(self, ref: str) -> Optional[SourceFanout]:
        return self.sources.get(ref)

    @property
    def complete(self) -> bool:
        return not self.unreadable

    def to_dict(self) -> dict:
        return {
            "sources": {k: v.to_dict() for k, v in sorted(self.sources.items())},
            "unreadable": list(self.unreadable),
            "complete": self.complete,
        }


def build(product: str = "", domains: Optional[list[str]] = None) -> Index:
    """Read every domain's proposal and group accepted instructions by source.

    Held entries are counted but carry no text, which is already the contract
    everywhere else — a held instruction still ties its domain to a source, and
    that tie is the whole point of the index.
    """
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo
    from agentic_cli.onboarding import extract, proposal
    from agentic_cli.tracker import get_domains

    index = Index()
    names = domains if domains is not None else [
        d["name"] for d in get_domains()
        if not product or (d.get("product") or "").lower() == product.lower()
    ]

    for name in names:
        try:
            meta = detect_domain_meta_repo(name)
            if meta is None:
                # No meta-repo is not the same as an unreadable one: this domain
                # has no proposal to cite anything from, which is a real answer.
                continue
            review = proposal.load(meta, name)
        except Exception as exc:  # noqa: BLE001 - one bad domain is not a failed index
            logger.debug("could not read proposal for %s: %s", name, exc)
            index.unreadable.append(name)
            continue

        per_ref: dict[str, SourceUse] = {}
        versions: dict[str, set[str]] = {}
        for entry in review.entries:
            citation = extract.Citation.parse(entry.citation)
            if not citation.scheme or not citation.ref:
                continue
            ref = f"{citation.scheme}:{citation.ref}"
            use = per_ref.setdefault(
                ref, SourceUse(domain=name, ref=ref, scheme=citation.scheme))
            if entry.status == proposal.ACCEPTED:
                use.accepted += 1
            elif entry.pending:
                use.pending += 1
            if citation.version:
                versions.setdefault(ref, set()).add(citation.version)

        for ref, use in per_ref.items():
            use.versions = tuple(sorted(versions.get(ref, ())))
            fanout = index.sources.setdefault(
                ref, SourceFanout(ref=ref, scheme=use.scheme))
            fanout.uses.append(use)

    return index


def for_source(ref: str, product: str = "") -> Optional[SourceFanout]:
    """Which domains draw on one source, or None when nothing does."""
    return build(product=product).by_ref(ref)


def affected_by(refs: list[str], product: str = "") -> dict[str, list[str]]:
    """Domains touched by each of several sources — the blast radius of a change.

    Takes a list because a commit changes several files, and the union is what a
    reviewer actually wants to know before pushing it.
    """
    index = build(product=product)
    return {ref: (index.by_ref(ref).domains if index.by_ref(ref) else [])
            for ref in refs}


__all__ = ["SourceUse", "SourceFanout", "Index", "build", "for_source",
           "affected_by"]
