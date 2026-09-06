"""What one source's change would do to every domain drawing on it — a dry run.

F1 answered *who is affected*. This answers *what would happen to them*, and it
answers it without writing anything: the plan is the artefact, and applying it is
a separate decision a human makes with the plan in front of them.

**Source-first, not domain-first.** ``keel domain diff`` walks one domain and
re-reads each of its sources. Turning that inside out — one source, N domains —
is not a loop over it. The source is fetched **once** and re-extracted **once**,
and that single extraction is then ruled against each domain's approved
instructions separately. On a shared platform doc that is one read instead of
one per domain, and the saving is the point: a fan-out that costs N re-reads is
one nobody runs before pushing.

That is only sound because a candidate's id excludes its citation *version* (see
:attr:`~agentic_cli.onboarding.extract.Candidate.id`). Domains routinely cite one
source at different versions — F1 calls that version skew — and if identity
depended on the revision, the shared extraction would report every instruction in
the lagging domain as changed. It does not, so one extraction genuinely serves
them all. Were that ever to change, this file breaks quietly, which is why the
reason is written down here rather than left to be rediscovered.

**Three outcomes, and they are not two.** A plan sorts each domain into
*settled* (the change lands with no human), *escalating* (a human owes a
decision), and *unknown* — and the third is not a rounding of the other two. A
domain whose proposal could not be read, or whose only tie to this source is a
held instruction carrying no text, is a domain we could not rule on. Reporting it
as settled would tell a reviewer the coast is clear on evidence nobody has;
reporting it as escalating would manufacture work. It gets counted as what it
is.

**An unreadable source produces no plan at all.** Not an empty one. An empty plan
says "this change affects nobody", which is precisely the wrong thing to tell
someone who is about to push, and it is indistinguishable from the answer where
the fetch failed unless the two are kept apart at the type level.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The plan was computed. Outcomes are real.
PLANNED = "planned"
#: The source could not be read, so there is nothing to plan against.
UNREADABLE = "unreadable"
#: Nothing draws on this source.
UNUSED = "unused"


@dataclass
class DomainOutcome:
    """What this source's current state would do to one domain."""

    domain: str
    #: Verdicts from :mod:`agentic_cli.onboarding.differ`, one per approved
    #: instruction drawn from this source.
    verdicts: list = field(default_factory=list)
    #: Approved instructions tied to this source that carry no text, so nothing
    #: can be ruled on them. Held by design — the review file records the risk
    #: kinds and a citation, never the text.
    held: int = 0
    #: False when this domain's proposal could not be read at all.
    readable: bool = True
    #: The version(s) this domain's instructions were extracted at.
    cited_versions: tuple[str, ...] = ()
    detail: str = ""

    @property
    def settled(self) -> list:
        """Verdicts needing no human: unchanged, or a reword something verified."""
        return [v for v in self.verdicts if v.settled]

    @property
    def escalating(self) -> list:
        """Verdicts a human owes a decision on."""
        return [v for v in self.verdicts if v.actionable]

    @property
    def unknown(self) -> list:
        """Verdicts where the source could not be re-read."""
        from agentic_cli.onboarding import differ

        return [v for v in self.verdicts if v.status == differ.UNKNOWN]

    @property
    def decidable(self) -> bool:
        """True when this domain's outcome rests on evidence rather than a gap.

        Held instructions and an unreadable proposal both leave a domain we did
        not rule on. Folding either into "settled" is how a fan-out reports a
        clear run it never verified.
        """
        return self.readable and not self.held and not self.unknown

    @property
    def blocked(self) -> bool:
        """True when a human must look before this domain can move."""
        return bool(self.escalating) or not self.decidable

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "readable": self.readable,
            "held": self.held,
            "cited_versions": list(self.cited_versions),
            "settled": len(self.settled),
            "escalating": len(self.escalating),
            "unknown": len(self.unknown),
            "decidable": self.decidable,
            "blocked": self.blocked,
            "detail": self.detail,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


@dataclass
class Plan:
    """One source's fan-out, ruled on. Writes nothing."""

    ref: str
    status: str = PLANNED
    #: The version the plan was computed against — what "now" meant when it ran.
    version: str = ""
    outcomes: list[DomainOutcome] = field(default_factory=list)
    #: Domains F1 could not read a proposal for. They are in :attr:`outcomes`
    #: too, marked unreadable; this is the flat list for a caller that only
    #: wants to know the index was incomplete.
    unreadable: list[str] = field(default_factory=list)
    detail: str = ""
    model: str = ""

    @property
    def planned(self) -> bool:
        return self.status == PLANNED

    @property
    def domains(self) -> list[str]:
        return sorted(o.domain for o in self.outcomes)

    @property
    def settled_domains(self) -> list[DomainOutcome]:
        """Domains this change lands in with nobody looking."""
        return [o for o in self.outcomes if not o.blocked]

    @property
    def blocked_domains(self) -> list[DomainOutcome]:
        return [o for o in self.outcomes if o.blocked]

    @property
    def version_skew(self) -> bool:
        """True when affected domains extracted this source at different versions.

        Straight from F1, and it belongs in the plan because it explains why two
        domains drawing on one source get different outcomes — without it the
        difference reads as a bug in the planner.
        """
        seen: set[str] = set()
        for outcome in self.outcomes:
            seen.update(v for v in outcome.cited_versions if v)
        return len(seen) > 1

    @property
    def counts(self) -> dict[str, int]:
        return {
            "domains": len(self.outcomes),
            "settled": len(self.settled_domains),
            "blocked": len(self.blocked_domains),
            "escalations": sum(len(o.escalating) for o in self.outcomes),
            "held": sum(o.held for o in self.outcomes),
        }

    def to_dict(self) -> dict:
        return {
            "ref": self.ref,
            "status": self.status,
            "version": self.version,
            "detail": self.detail,
            "model": self.model,
            "version_skew": self.version_skew,
            "counts": self.counts,
            "unreadable": list(self.unreadable),
            "outcomes": [o.to_dict() for o in self.outcomes],
        }


def build(ref: str, *, product: str = "", provider: Any = None,
          doc_type: str = "") -> Plan:
    """Rule this source's current state against every domain that draws on it.

    ``provider`` is passed through to the differ's judge. Without one, a reworded
    instruction stays *unverified* and never fast-forwards — token overlap cannot
    tell agreement from contradiction, so the plan asks a human rather than
    guessing in the direction that flatters it.
    """
    from agentic_cli import retrieval
    from agentic_cli.onboarding import classify, differ, extract, fanout, proposal
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    index = fanout.build(product=product)
    source = index.by_ref(ref)
    if source is None:
        # Nothing cites it. A real answer, and distinct from both of the others.
        return Plan(ref=ref, status=UNUSED, unreadable=list(index.unreadable),
                    detail="No domain draws on this source.")

    fetched = retrieval.fetch(ref, source=retrieval.ONBOARDING_SOURCE,
                              operation_prefix="plan")
    if not fetched.resolved or not fetched.text:
        # No plan, rather than a plan with no impact in it.
        return Plan(ref=ref, status=UNREADABLE,
                    unreadable=list(index.unreadable),
                    detail=f"{fetched.status}: {fetched.detail or 'nothing returned'}")

    # One extraction, reused for every domain. Sound because candidate ids do
    # not include the citation version — see this module's docstring.
    scheme, _, address = ref.partition(":")
    citation = extract.Citation(scheme, address.lstrip("/"), fetched.version)
    result = extract.extract(fetched.text, citation,
                             doc_type or classify.ONBOARDING)

    plan = Plan(ref=ref, version=fetched.version,
                unreadable=list(index.unreadable))

    for use in sorted(source.uses, key=lambda u: u.domain):
        outcome = DomainOutcome(domain=use.domain, cited_versions=use.versions)
        try:
            meta = detect_domain_meta_repo(use.domain)
            review = proposal.load(meta, use.domain) if meta else None
        except Exception as exc:  # noqa: BLE001 - one bad domain is not a failed plan
            logger.debug("could not read proposal for %s: %s", use.domain, exc)
            review = None

        if review is None:
            outcome.readable = False
            outcome.detail = "Proposal could not be read — nothing was ruled on."
            plan.outcomes.append(outcome)
            if use.domain not in plan.unreadable:
                plan.unreadable.append(use.domain)
            continue

        entries = [
            e for e in review.entries
            if e.status == proposal.ACCEPTED
            and f"{extract.Citation.parse(e.citation).scheme}:"
                f"{extract.Citation.parse(e.citation).ref}" == ref
        ]
        # A held entry ties this domain to the source but carries no text, so
        # the differ has nothing to rule on. Counted, never quietly dropped.
        outcome.held = sum(1 for e in entries if e.held or not e.text)

        report = differ.diff([e for e in entries if not e.held and e.text],
                             result.candidates, provider=provider)
        outcome.verdicts = report.verdicts
        plan.model = plan.model or report.model
        plan.outcomes.append(outcome)

    return plan


def for_change(refs: list[str], *, product: str = "",
               provider: Any = None) -> dict[str, Plan]:
    """Plan several sources at once — a commit touches more than one file."""
    return {ref: build(ref, product=product, provider=provider) for ref in refs}


__all__ = ["PLANNED", "UNREADABLE", "UNUSED", "DomainOutcome", "Plan", "build",
           "for_change"]
