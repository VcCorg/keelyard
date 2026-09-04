"""Classify a tracked domain doc by what it is *for*.

``domain add-docs`` tracks Confluence pages as an undifferentiated bag, and
``ConfluenceSource`` then maps every one of them to ``type="Requirement"``. An
onboarding runbook and a lunch-and-learn note produce identical concept refs, so
nothing downstream can weight, route, or prioritise them — and the highest-signal
document in the space is ingested at the same weight as a stale meeting note.

Classification is title-and-space heuristics first, deliberately:

- It is **auditable** — every verdict names the rule that fired, so a wrong
  call is a rule to fix rather than a model to re-prompt.
- It is **free and offline**, so it runs in test mode and in CI.
- Titles are unusually honest. Teams name onboarding pages "Onboarding"
  because they want new joiners to find them.

:func:`classify` therefore returns a confidence alongside the type, and callers
escalate only the ``OTHER``/low-confidence tail to a model (or to the reviewer,
which is cheaper and usually better).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: How a new joiner is brought up to speed — the highest-value corpus.
ONBOARDING = "onboarding"
#: How the thing is operated: deploys, on-call, incidents, troubleshooting.
RUNBOOK = "runbook"
#: A recorded decision and its rationale.
ADR = "adr"
#: Vocabulary, APIs, schemas — lookup material.
REFERENCE = "reference"
#: What the system must do.
REQUIREMENT = "requirement"
#: Everything else: meeting notes, retros, status pages.
OTHER = "other"

#: Types whose bodies are worth extracting operational intent from.
OPERATIONAL = frozenset({ONBOARDING, RUNBOOK})

ALL_TYPES = (ONBOARDING, RUNBOOK, ADR, REFERENCE, REQUIREMENT, OTHER)

# Ordered: the first rule that matches wins, so more specific phrases lead.
# (doc_type, weight, pattern) — weight becomes the confidence when it fires.
_RULES: tuple[tuple[str, float, str], ...] = (
    (ONBOARDING, 0.95, r"\bonboard(ing|ed)?\b"),
    (ONBOARDING, 0.95, r"\bnew\s+(joiner|hire|starter|developer|engineer)s?\b"),
    (ONBOARDING, 0.90, r"\bgetting\s+started\b"),
    (ONBOARDING, 0.90, r"\bramp[\s-]?up\b"),
    (ONBOARDING, 0.85, r"\b(first|day)\s+(day|one|1)\b|\bweek\s+(one|1)\b"),
    (ONBOARDING, 0.85, r"\b(dev|developer|local)\s+(environment|env|setup)\b"),
    (ONBOARDING, 0.80, r"\benvironment\s+setup\b|\bsetup\s+guide\b"),
    (ONBOARDING, 0.75, r"\bdeveloper\s+guide\b|\bstart\s+here\b"),

    (RUNBOOK, 0.95, r"\brun\s?book\b|\bplay\s?book\b"),
    (RUNBOOK, 0.90, r"\bon[\s-]?call\b|\bincident\b|\bpost[\s-]?mortem\b"),
    (RUNBOOK, 0.90, r"\btroubleshoot(ing)?\b|\bdisaster\s+recovery\b"),
    (RUNBOOK, 0.85, r"\b(deploy|release|rollback|cutover)\s+(process|guide|steps|checklist)\b"),
    (RUNBOOK, 0.80, r"\boperations?\s+(guide|manual)\b|\bsop\b"),

    (ADR, 0.95, r"\badr[\s-]?\d*\b|\barchitecture\s+decision\b"),
    (ADR, 0.90, r"\bdecision\s+record\b|\brfc[\s-]?\d+\b"),
    (ADR, 0.75, r"\bdesign\s+decision\b|\btrade[\s-]?off\s+analysis\b"),

    (REQUIREMENT, 0.90, r"\brequirements?\b|\bacceptance\s+criteria\b"),
    (REQUIREMENT, 0.85, r"\buser\s+stor(y|ies)\b|\bepic\b|\bfreq[\s-]?\d+\b"),
    (REQUIREMENT, 0.80, r"\b(functional|business)\s+spec(ification)?\b"),

    (REFERENCE, 0.90, r"\bglossar(y|ies)\b|\bterminolog(y|ies)\b|\bubiquitous\s+language\b"),
    (REFERENCE, 0.85, r"\bapi\s+(reference|docs?|contract|spec)\b|\bopenapi\b|\bswagger\b"),
    (REFERENCE, 0.80, r"\bdata\s+(model|dictionary)\b|\bschema\b|\berd\b"),
    (REFERENCE, 0.75, r"\barchitecture\b|\bsystem\s+design\b"),

    (OTHER, 0.85, r"\bmeeting\s+notes?\b|\bretro(spective)?\b|\bstand[\s-]?up\b"),
    (OTHER, 0.85, r"\bsprint\s+\d+\b|\bstatus\s+(update|report)\b|\bagenda\b"),
)

_COMPILED = tuple((t, w, re.compile(p, re.IGNORECASE)) for t, w, p in _RULES)


@dataclass(frozen=True)
class Classification:
    """What a doc is, how sure we are, and which rule decided."""

    doc_type: str
    confidence: float
    rule: str = ""

    @property
    def operational(self) -> bool:
        """True when this doc carries the how-do-I-work-here material."""
        return self.doc_type in OPERATIONAL

    @property
    def certain(self) -> bool:
        """True when the verdict is strong enough to act on without review."""
        return self.confidence >= 0.75

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type,
            "confidence": round(self.confidence, 2),
            "rule": self.rule,
        }


def classify(title: str, space_key: str = "", body_excerpt: str = "") -> Classification:
    """Classify one doc from its title, with space and body as tie-breakers.

    ``body_excerpt`` is read but never retained — see the extraction contract in
    :mod:`agentic_cli.onboarding.extract`.
    """
    haystack = (title or "").strip()
    if not haystack and not body_excerpt:
        return Classification(OTHER, 0.0, "empty")

    for doc_type, weight, pattern in _COMPILED:
        if pattern.search(haystack):
            return Classification(doc_type, weight, pattern.pattern)

    # A space named for onboarding lends weight its pages' titles may not carry.
    if space_key and re.search(r"onboard|welcome|induction", space_key, re.IGNORECASE):
        return Classification(ONBOARDING, 0.60, f"space:{space_key}")

    # Fall back to the body, at reduced confidence: a heading inside the page is
    # weaker evidence than a title, because pages link to each other's topics.
    if body_excerpt:
        for doc_type, weight, pattern in _COMPILED:
            if pattern.search(body_excerpt):
                return Classification(doc_type, weight * 0.6, f"body:{pattern.pattern}")

    return Classification(OTHER, 0.30, "no-rule-matched")


def classify_docs(docs: list[dict]) -> dict[str, Classification]:
    """Classify tracked ``domain_docs`` rows, keyed by ``source_page_id``."""
    out: dict[str, Classification] = {}
    for doc in docs:
        page_id = str(doc.get("source_page_id") or "")
        if not page_id:
            continue
        out[page_id] = classify(
            doc.get("title") or "",
            doc.get("source_space_key") or "",
        )
    return out


def counts(classifications: dict[str, Classification]) -> dict[str, int]:
    """Per-type counts, in declaration order, omitting empty types."""
    out: dict[str, int] = {}
    for doc_type in ALL_TYPES:
        n = sum(1 for c in classifications.values() if c.doc_type == doc_type)
        if n:
            out[doc_type] = n
    return out


__all__ = [
    "ONBOARDING", "RUNBOOK", "ADR", "REFERENCE", "REQUIREMENT", "OTHER",
    "OPERATIONAL", "ALL_TYPES", "Classification", "classify", "classify_docs",
    "counts",
]
