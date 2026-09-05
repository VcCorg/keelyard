"""What did this project cost, and which half of it was building the context?

The ledger records every read as one row. That is the right grain to store and
the wrong grain to answer with, because "how much did this competition cost me
against that one" is really three questions wearing one coat:

**Context built** — the one-off investment. Reading a repo's docs, a Confluence
space and a KG to produce a finalized instruction set. Paid once per project and
amortized across every session afterwards.

**Context served** — the recurring cost. What Keel put in front of an agent on
each run. This is the number that multiplies by how much you work.

**Tools and retrieval** — MCP calls, KG queries, search hits. Fetched during a
session but not part of the domain's own context.

Rolling them into one total is what makes a cross-project comparison useless: a
project three days into onboarding is nearly all build cost, and one running
daily sessions off finished context is nearly all serve cost. Identical totals,
opposite situations, and only the split tells you which you are looking at.

Two things this module refuses to do, both for the same reason — a number whose
provenance is gone can only be quoted carelessly:

**It never presents an estimate as a measurement.** Most models have no
tokenizer we can run, so most counts are estimates. Every readout carries the
mix, and a total drawn from both says so.

**It never reports retrieved bytes as spend.** The ledger holds what Keel
*retrieved*. What an engine *assembled* into a prompt — after dedup, truncation,
reordering and caching — is a different number, and for a hosted engine we may
never see it. So this is honestly labelled *served*, never *billed*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

BUILD = "build"
SERVE = "serve"
TOOLS = "tools"

#: Ledger source families, grouped into the meter each belongs to.
#:
#: ``onboarding`` is the family the retrieval seam records extraction reads
#: under, which is precisely why it was given its own name rather than being
#: filed as ``context``: a page read to *derive* instructions was never put in
#: front of an agent, and the two costs answer different questions.
_METER_OF = {
    "onboarding": BUILD,
    "kg": BUILD,
    "context": SERVE,
    "mcp": TOOLS,
    "retriever": TOOLS,
}

METER_LABELS = {
    BUILD: "Context built",
    SERVE: "Context served",
    TOOLS: "Tools & retrieval",
}

#: Order a report shows meters in: the one-off first, then the recurring.
METER_ORDER = (BUILD, SERVE, TOOLS)


def meter_for(source: str) -> str:
    """Which meter a ledger source family belongs to.

    An unrecognised family counts as ``TOOLS`` rather than being dropped. A new
    retrieval path that nobody classified should show up in the total slightly
    misfiled, not vanish from it — an under-reported cost is the failure mode
    that goes unnoticed.
    """
    return _METER_OF.get((source or "").lower(), TOOLS)


@dataclass
class Meter:
    """One meter's totals for one project."""

    key: str
    reads: int = 0
    bytes: int = 0
    tokens: int = 0
    measured: int = 0
    estimated: int = 0
    #: Reads whose tokens were never counted — a path that records a size
    #: without the text behind it. Tracked separately because adding them in as
    #: zero is indistinguishable from them being free, and that is exactly the
    #: reading a cost table invites.
    uncounted: int = 0

    @property
    def label(self) -> str:
        return METER_LABELS.get(self.key, self.key)

    @property
    def counted(self) -> int:
        return self.reads - self.uncounted

    @property
    def complete(self) -> bool:
        """True when every read behind this meter contributed a token count."""
        return self.uncounted == 0

    @property
    def basis(self) -> str:
        """How the number was reached, including whether it is even complete.

        ``partial`` and ``uncounted`` come first because they outrank the
        measured/estimated distinction: an estimate over all the reads is a
        usable comparison, and an exact count over half of them is not.
        """
        if self.reads and self.uncounted == self.reads:
            return "uncounted"
        if self.uncounted:
            return f"partial ({self.counted}/{self.reads})"
        if self.measured and self.estimated:
            return "mixed"
        return "measured" if self.measured else "estimated"

    def add(self, row: dict) -> None:
        self.reads += int(row.get("reads") or 0)
        self.bytes += int(row.get("bytes") or 0)
        self.tokens += int(row.get("tokens") or 0)
        self.measured += int(row.get("measured") or 0)
        self.estimated += int(row.get("estimated") or 0)
        self.uncounted += int(row.get("uncounted") or 0)

    def to_dict(self) -> dict:
        return {"meter": self.key, "label": self.label, "reads": self.reads,
                "bytes": self.bytes, "tokens": self.tokens,
                "basis": self.basis, "measured": self.measured,
                "estimated": self.estimated, "uncounted": self.uncounted,
                "complete": self.complete}


@dataclass
class ProjectUsage:
    """Every meter for one project, plus what the ledger could not attribute."""

    domain: str
    meters: dict[str, Meter] = field(default_factory=dict)
    first_seen: str = ""
    last_seen: str = ""

    @property
    def named(self) -> str:
        return self.domain or "(unattributed)"

    @property
    def tokens(self) -> int:
        return sum(m.tokens for m in self.meters.values())

    @property
    def reads(self) -> int:
        return sum(m.reads for m in self.meters.values())

    @property
    def bytes(self) -> int:
        return sum(m.bytes for m in self.meters.values())

    @property
    def uncounted(self) -> int:
        return sum(m.uncounted for m in self.meters.values())

    @property
    def complete(self) -> bool:
        return self.uncounted == 0

    @property
    def basis(self) -> str:
        measured = sum(m.measured for m in self.meters.values())
        estimated = sum(m.estimated for m in self.meters.values())
        if self.uncounted:
            return f"partial ({self.reads - self.uncounted}/{self.reads})"
        if measured and estimated:
            return "mixed"
        return "measured" if measured else "estimated"

    @property
    def build_share(self) -> Optional[float]:
        """Fraction of tokens spent building the context, 0..1.

        ``None`` when nothing was counted — an unstarted project has no ratio,
        and reporting 0% would read as "all of this was serve cost", which is a
        claim about a project that has not spent anything yet.

        A ratio over partial coverage is still returned, because it is still the
        best available answer; :attr:`complete` is what says whether to trust it,
        and the readout shows both rather than suppressing the number.
        """
        total = self.tokens
        if not total:
            return None
        return self.meters.get(BUILD, Meter(BUILD)).tokens / total

    def meter(self, key: str) -> Meter:
        return self.meters.get(key, Meter(key))

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "reads": self.reads,
            "bytes": self.bytes,
            "tokens": self.tokens,
            "basis": self.basis,
            "uncounted": self.uncounted,
            "complete": self.complete,
            "build_share": (None if self.build_share is None
                            else round(self.build_share, 3)),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "meters": [self.meters[k].to_dict()
                       for k in METER_ORDER if k in self.meters],
        }


def by_project(domain: Optional[str] = None) -> list[ProjectUsage]:
    """Ledger usage per project, biggest first.

    Passing ``domain`` narrows to one. Otherwise every project is returned,
    including the unattributed bucket: work that predates the domain column, or
    ran outside any project, is real spend and dropping it would make the totals
    quietly disagree with the ledger they came from.
    """
    from agentic_cli.tracker import usage_by_domain

    projects: dict[str, ProjectUsage] = {}
    for row in usage_by_domain(domain=domain):
        slug = row.get("domain") or ""
        project = projects.setdefault(slug, ProjectUsage(domain=slug))
        key = meter_for(row.get("source") or "")
        project.meters.setdefault(key, Meter(key)).add(row)
        for field_name in ("first_seen", "last_seen"):
            value = row.get(field_name) or ""
            current = getattr(project, field_name)
            if not current or (value and (
                    value < current if field_name == "first_seen" else value > current)):
                setattr(project, field_name, value)

    return sorted(projects.values(), key=lambda p: (-p.tokens, p.named))


def compare(projects: list[ProjectUsage]) -> dict:
    """Totals across a portfolio, and the honest caveat that goes with them."""
    from agentic_cli import tokens as token_counter

    measured = sum(m.measured for p in projects for m in p.meters.values())
    estimated = sum(m.estimated for p in projects for m in p.meters.values())
    uncounted = sum(p.uncounted for p in projects)
    note = token_counter.summarise(
        {token_counter.MEASURED: measured, token_counter.ESTIMATED: estimated})
    if uncounted:
        # Said before the basis, not after: incomplete coverage matters more
        # than how the counted part was reached.
        note = (f"{uncounted} read(s) contributed no token count — the totals "
                f"are a floor, not a total; {note}")
    return {
        "projects": len(projects),
        "reads": sum(p.reads for p in projects),
        "tokens": sum(p.tokens for p in projects),
        "bytes": sum(p.bytes for p in projects),
        "uncounted": uncounted,
        "complete": uncounted == 0,
        "basis_note": note,
    }


__all__ = ["BUILD", "SERVE", "TOOLS", "METER_LABELS", "METER_ORDER",
           "meter_for", "Meter", "ProjectUsage", "by_project", "compare"]
