"""Whose decision each escalation is — F4, and the answer is the domain owner.

F2 produces a plan: which domains a source's change lands in unattended, and
which owe somebody a decision. It stops at *somebody*. This names them.

The rule is one line and the rest of this module is the consequences of taking
it seriously: **the reviewer is the domain's owner**, read from the domain's own
``.platform/config/domain.yaml``. Ownership lives there rather than in the
tracker because it is the same kind of fact as the instructions being reviewed —
git-visible, reviewed as a pull request, owned by the team it describes. A
routing table in a local database would be a second answer to "who owns this"
that nobody reviews.

**No default owner, ever.** A domain with no owner recorded produces an
*unowned* item, reported as such. The tempting fallbacks are all worse than
saying so: assigning to the product owner tells one person to decide on behalf
of a team that never named a reviewer; assigning to whoever ran the command
makes the queue depend on who was curious; assigning to nobody drops the work
silently. The product owner *is* named where one exists, as a candidate to ask —
naming a person to talk to is not the same as putting work in their queue, and
the difference is the whole reason this is not automatic.

**An empty queue is not the same as an examined one.** A domain whose proposal
could not be read, or whose only tie to a source is a held instruction carrying
no text, produces no escalations — and it is not fine. Its owner would otherwise
see nothing and conclude nothing was needed, which is exactly the failure the
plan's third outcome exists to prevent. Those arrive as items too, marked as
what they are: nothing could be ruled on.

**One owner, one queue.** Somebody owning three affected domains has one list of
work, not three, and a commit touching four files is still one list. That
consolidation is the whole point of asking whose queue it is: without it the
answer "the domain owner" is just a column in the plan.

This routes and does not decide. Nothing here writes a verdict, and nothing here
changes a proposal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

#: One instruction a human owes a decision on.
ESCALATION = "escalation"
#: The domain is blocked but nothing could be ruled on — an owner must be able
#: to tell this from an empty queue.
UNRULED = "unruled"

REASONS = (ESCALATION, UNRULED)

#: Owner lookup outcomes, kept apart because they call for different actions.
OWNED = "owned"
#: The config was read and names no owner. Somebody must decide who reviews.
UNOWNED = "unowned"
#: The config could not be read at all. We do not know whether an owner exists.
UNKNOWN_OWNER = "unknown"


@dataclass
class Item:
    """One piece of work, addressed to one domain."""

    domain: str
    ref: str
    reason: str
    entry_id: str = ""
    #: The differ's verdict for this instruction, when there is one.
    status: str = ""
    detail: str = ""
    #: The version this domain's instructions were extracted at. Carried so a
    #: reviewer under version skew can see which revision they approved,
    #: rather than assuming it was the one being planned.
    cited_version: str = ""

    def to_dict(self) -> dict:
        out = {"domain": self.domain, "ref": self.ref, "reason": self.reason}
        for key in ("entry_id", "status", "detail", "cited_version"):
            if getattr(self, key):
                out[key] = getattr(self, key)
        return out


@dataclass
class Queue:
    """Everything one owner has to look at, across sources and domains."""

    owner: str
    items: list[Item] = field(default_factory=list)

    @property
    def domains(self) -> list[str]:
        return sorted({i.domain for i in self.items})

    @property
    def refs(self) -> list[str]:
        return sorted({i.ref for i in self.items})

    @property
    def escalations(self) -> list[Item]:
        return [i for i in self.items if i.reason == ESCALATION]

    @property
    def unruled(self) -> list[Item]:
        return [i for i in self.items if i.reason == UNRULED]

    def to_dict(self) -> dict:
        return {"owner": self.owner, "domains": self.domains,
                "refs": self.refs, "escalations": len(self.escalations),
                "unruled": len(self.unruled),
                "items": [i.to_dict() for i in self.items]}


@dataclass
class Routing:
    """Work sorted by who owns the decision, and everything that would not sort."""

    queues: list[Queue] = field(default_factory=list)
    #: Items whose domain records no owner. Never folded into a queue.
    unowned: list[Item] = field(default_factory=list)
    #: Items whose domain config could not be read — we do not even know
    #: whether an owner exists, which is weaker than knowing there is none.
    unknown: list[Item] = field(default_factory=list)
    #: Domain → the product owner, where one is recorded. A person to ask, not
    #: an assignment: naming somebody to talk to and putting work in their
    #: queue are different acts.
    fallback_contacts: dict = field(default_factory=dict)

    @property
    def routed(self) -> int:
        return sum(len(q.items) for q in self.queues)

    @property
    def unrouted(self) -> int:
        return len(self.unowned) + len(self.unknown)

    @property
    def complete(self) -> bool:
        """True when every item found an owner."""
        return not self.unrouted

    @property
    def counts(self) -> dict:
        return {"owners": len(self.queues), "routed": self.routed,
                "unowned": len(self.unowned), "unknown": len(self.unknown)}

    def for_owner(self, owner: str) -> Optional[Queue]:
        return next((q for q in self.queues if q.owner == owner), None)

    def to_dict(self) -> dict:
        return {
            "counts": self.counts,
            "complete": self.complete,
            "queues": [q.to_dict() for q in self.queues],
            "unowned": [i.to_dict() for i in self.unowned],
            "unknown": [i.to_dict() for i in self.unknown],
            "fallback_contacts": dict(sorted(self.fallback_contacts.items())),
        }


# ── ownership ───────────────────────────────────────────────────────────────

def owner_of(domain: str) -> tuple[str, str]:
    """The domain's recorded owner, and how confident we are there is one.

    Returns ``(owner, status)``. The three statuses are not two: a config that
    was read and names nobody is a domain whose team has not said who reviews,
    and a config that could not be read tells us nothing at all. The first is a
    gap somebody can close in a minute; the second may be a missing checkout.
    """
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    try:
        meta = detect_domain_meta_repo(domain)
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not locate meta-repo for %s: %s", domain, exc)
        return "", UNKNOWN_OWNER
    if meta is None:
        return "", UNKNOWN_OWNER

    # Checked directly rather than via MetaRepoConfig, which logs and returns
    # None for both a missing file and an unparsable one — the exact
    # distinction this function exists to keep.
    config_file = Path(meta) / ".platform" / "config" / "domain.yaml"
    if not config_file.is_file():
        return "", UNKNOWN_OWNER

    try:
        from agentic_cli.meta_repo.config import MetaRepoConfig

        config = MetaRepoConfig(Path(meta))
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not read domain config for %s: %s", domain, exc)
        return "", UNKNOWN_OWNER

    if config.domain is None:
        return "", UNKNOWN_OWNER
    owner = (config.domain.owner or "").strip()
    return (owner, OWNED) if owner else ("", UNOWNED)


def _product_contact(domain: str) -> str:
    """The product owner, where one is recorded. Named, never assigned."""
    try:
        from agentic_cli.tracker import get_domain, get_product

        record = get_domain(domain) or {}
        product = get_product(record.get("product") or "") or {}
        return str(product.get("owner") or "")
    except Exception as exc:  # noqa: BLE001
        logger.debug("no product contact for %s: %s", domain, exc)
        return ""


# ── routing ─────────────────────────────────────────────────────────────────

def items_for(plan) -> list[Item]:
    """Turn one plan into addressable work, losing nothing on the way.

    Every blocked domain produces at least one item. A domain that is blocked
    with no escalations — unreadable, or held-only — is the case that would
    otherwise vanish, and it is the one whose owner most needs to hear from us.
    """
    found: list[Item] = []
    for outcome in plan.outcomes:
        version = outcome.cited_versions[0] if outcome.cited_versions else ""
        for verdict in outcome.escalating:
            found.append(Item(
                domain=outcome.domain, ref=plan.ref, reason=ESCALATION,
                entry_id=verdict.entry_id, status=verdict.status,
                detail=verdict.detail, cited_version=version,
            ))
        if outcome.blocked and not outcome.escalating:
            found.append(Item(
                domain=outcome.domain, ref=plan.ref, reason=UNRULED,
                detail=_unruled_detail(outcome), cited_version=version,
            ))
    return found


def _unruled_detail(outcome) -> str:
    """Why nothing could be ruled on, most specific reason first."""
    if outcome.detail:
        return outcome.detail
    if outcome.held:
        return (f"{outcome.held} held instruction(s) carry no text, so nothing "
                f"could be ruled on.")
    return "Blocked, and nothing could be ruled on."


def route(plans) -> Routing:
    """Sort every plan's work by who owns the decision.

    Takes one plan or many: a commit touches several files, and an owner should
    get one queue for the change rather than one per file.
    """
    if hasattr(plans, "outcomes"):          # a single Plan
        plans = [plans]
    elif isinstance(plans, dict):           # {ref: Plan}, as `plan.for_change`
        plans = list(plans.values())

    routing = Routing()
    by_owner: dict[str, Queue] = {}
    # One lookup per domain, not one per item: a domain with nine escalations
    # is one ownership question, and re-reading its config nine times would
    # also make the answer able to change mid-run.
    resolved: dict[str, tuple[str, str]] = {}

    for plan in plans:
        for item in items_for(plan):
            if item.domain not in resolved:
                resolved[item.domain] = owner_of(item.domain)
            owner, status = resolved[item.domain]

            if status == OWNED:
                queue = by_owner.setdefault(owner, Queue(owner=owner))
                queue.items.append(item)
                continue

            if status == UNOWNED:
                routing.unowned.append(item)
            else:
                routing.unknown.append(item)
            if item.domain not in routing.fallback_contacts:
                contact = _product_contact(item.domain)
                if contact:
                    routing.fallback_contacts[item.domain] = contact

    routing.queues = sorted(by_owner.values(), key=lambda q: q.owner)
    return routing


def route_refs(refs: Iterable[str], *, product: str = "",
               provider=None) -> Routing:
    """Plan several sources and route the result — the whole F2→F4 path."""
    from agentic_cli.onboarding import plan as planner

    return route(planner.for_change(list(refs), product=product,
                                    provider=provider))


__all__ = ["ESCALATION", "UNRULED", "REASONS", "OWNED", "UNOWNED",
           "UNKNOWN_OWNER", "Item", "Queue", "Routing", "owner_of",
           "items_for", "route", "route_refs"]
