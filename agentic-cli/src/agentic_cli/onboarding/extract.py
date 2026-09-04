"""Extract the *intent* of an onboarding doc, never its text.

The contract, in one sentence: **a body is read in memory, reduced to
instruction candidates, and discarded.** Nothing raw is written to disk, so this
path needs no payload store, no retention policy, and no redaction-at-rest
design — the questions that block KeelTrace tier two do not arise here.

What survives extraction is an abstracted imperative — *"run the bootstrap
target before the first build"* — carrying a type, a **citation as a pointer**
(page id + version, or path + sha; never content), a confidence, and a residual
risk list. An instruction points at where a live value lives; it never carries
the value.

Two design choices worth stating:

**Harvesting is deterministic; abstraction is optional.** The structure of a
document — ordered steps, code fences, headings, definition lines — is enough to
find the instructions without a model, so extraction runs in test mode, in CI,
and offline. A model can then sharpen a candidate into a cleaner intent
statement, but it is never required, and a model failure degrades the result
rather than breaking the run.

**Names are dropped as a correctness measure, not only a privacy one.** A
person's name is the fastest-decaying fact in any onboarding doc: *"ownership is
recorded in CODEOWNERS"* survives three reorgs, *"ask <name>"* is wrong within a
quarter. :func:`_pointerize` rewrites an ownership instruction to its durable
pointer when it can find one, and holds it when it cannot.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from agentic_cli.onboarding import redaction
from agentic_cli.onboarding.classify import ONBOARDING, RUNBOOK

# ── Candidate kinds ─────────────────────────────────────────────────────────

SETUP = "setup"
RUNBOOK_STEP = "runbook"
GLOSSARY = "glossary"
OWNERSHIP = "ownership"
HAZARD = "hazard"

KIND_ORDER = (SETUP, RUNBOOK_STEP, HAZARD, OWNERSHIP, GLOSSARY)

#: Verbs that open an instruction. Ordered by nothing; membership is the test.
_IMPERATIVES = frozenset("""
run install clone checkout set configure add create request open deploy build
check verify ensure use avoid enable disable start stop restart export import
copy download upload register grant apply update upgrade migrate generate
initialise initialize provision connect log login authenticate submit raise
""".split())

_HAZARD_MARKERS = re.compile(
    r"\b(warning|caution|danger|gotcha|careful|beware|do not|don't|never|"
    r"must not|will break|breaks|fails|pitfall|common mistake|note that)\b",
    re.IGNORECASE,
)

_OWNERSHIP_MARKERS = re.compile(
    r"\b(owner|owned by|maintained by|maintainer|contact|ask|reach out|"
    r"responsible for|on[\s-]?call|rota|escalat)\w*\b",
    re.IGNORECASE,
)

# Durable ownership pointers: a file, a group handle, a rota — things that stay
# true when people move on.
# Every alternative is boundary-anchored: without \b, "OWNERS" matches inside
# "Ownership" and every ownership sentence grows a phantom pointer.
_POINTER_RE = re.compile(
    r"(\bCODEOWNERS\b|\bOWNERS(?:\.md)?\b|@[\w-]+/[\w-]+|#[\w-]{3,}\b|"
    r"\b(?:the\s+)?[\w-]+\s+(?:team|guild|squad|chapter)\b|"
    r"\bon[\s-]?call\s+rota\b|\bpager\s?duty\b|\bescalation\s+path\b)",
    re.IGNORECASE,
)

# Stems, not whole words: "\bglossar\b" cannot match "Glossary".
_GLOSSARY_HEADING = re.compile(
    r"\b(glossar\w*|terminolog\w*|vocabular\w*|definitions?|ubiquitous\s+language)\b",
    re.IGNORECASE,
)
_DEFINITION_RE = re.compile(r"^\s*\*{0,2}([A-Z][\w \-/]{1,40}?)\*{0,2}\s*[:—-]\s+(.{10,})$")

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*\S)\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_FENCE_RE = re.compile(r"^\s*```")

#: Anything shorter is a fragment, anything longer is a paragraph we would be
#: guessing at. Both make poor instructions.
_MIN_LEN = 12
_MAX_LEN = 400


@dataclass(frozen=True)
class Citation:
    """A pointer back to a source. Never carries content."""

    scheme: str          # "confluence" | "repo"
    ref: str             # page id, or repo-relative path
    version: str = ""    # page version, or commit sha

    def __str__(self) -> str:
        return f"{self.scheme}:{self.ref}" + (f"@{self.version}" if self.version else "")

    @classmethod
    def parse(cls, raw: str) -> "Citation":
        body, _, version = (raw or "").partition("@")
        scheme, _, ref = body.partition(":")
        return cls(scheme=scheme, ref=ref, version=version)


@dataclass
class Candidate:
    """One extracted instruction, ready for review."""

    text: str
    kind: str
    citation: Citation
    confidence: float = 0.5
    risks: tuple[redaction.Risk, ...] = field(default_factory=tuple)
    abstracted: bool = False

    @property
    def held(self) -> bool:
        """True when this candidate's text must never be written to disk."""
        return bool(self.risks)

    @property
    def id(self) -> str:
        """Stable id from kind + citation + text, so re-extraction can match."""
        digest = hashlib.sha256(
            f"{self.kind}|{self.citation}|{self.text}".encode("utf-8")
        ).hexdigest()
        return digest[:12]

    def to_dict(self) -> dict:
        """Serialise for the review file. Held candidates omit their text."""
        out: dict = {
            "id": self.id,
            "kind": self.kind,
            "citation": str(self.citation),
            "confidence": round(self.confidence, 2),
        }
        if self.held:
            out["risks"] = [r.kind for r in self.risks]
            out["reason"] = "; ".join(r.describe() for r in self.risks)
        else:
            out["text"] = self.text
            out["abstracted"] = self.abstracted
        return out


@dataclass
class ExtractionResult:
    """Everything one document yielded."""

    citation: Citation
    candidates: list[Candidate] = field(default_factory=list)
    held: list[Candidate] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for kind in KIND_ORDER:
            n = sum(1 for c in self.candidates if c.kind == kind)
            if n:
                out[kind] = n
        return out


def extract(text: str, citation: Citation, doc_type: str = ONBOARDING) -> ExtractionResult:
    """Reduce one document body to instruction candidates.

    ``text`` is consumed and not retained. Every candidate is risk-scanned
    before it leaves this function, so a caller cannot accidentally write held
    text.
    """
    result = ExtractionResult(citation=citation)
    if not text or not text.strip():
        return result

    default_kind = RUNBOOK_STEP if doc_type == RUNBOOK else SETUP

    for raw, in_glossary in _walk(text):
        line = _clean(raw)
        if not (_MIN_LEN <= len(line) <= _MAX_LEN):
            continue

        candidate = _to_candidate(line, in_glossary, default_kind, citation)
        if candidate is None:
            continue

        candidate.risks = redaction.scan(candidate.text)
        (result.held if candidate.held else result.candidates).append(candidate)

    _dedupe(result)
    return result


def _walk(text: str):
    """Yield ``(line, in_glossary_section)``, skipping fenced code.

    Code fences are skipped rather than harvested: a command block is exactly
    where hosts, ports and credentials live, so its literal text is the thing we
    least want to carry. The prose around it states the intent.
    """
    in_fence = False
    in_glossary = False
    for raw in text.splitlines():
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _HEADING_RE.match(raw)
        if heading:
            in_glossary = bool(_GLOSSARY_HEADING.search(heading.group(2)))
            continue
        if raw.strip():
            yield raw, in_glossary


def _clean(raw: str) -> str:
    """Strip list markers and inline markup down to the sentence itself."""
    line = _LIST_ITEM_RE.match(raw)
    text = line.group(1) if line else raw.strip()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)   # links → their label
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _to_candidate(
    line: str, in_glossary: bool, default_kind: str, citation: Citation
) -> Candidate | None:
    """Decide what kind of instruction a line is, if any."""
    if in_glossary:
        match = _DEFINITION_RE.match(line)
        if match:
            term, meaning = match.group(1).strip(), match.group(2).strip()
            return Candidate(f"{term}: {meaning}", GLOSSARY, citation, 0.8)
        return None

    if _HAZARD_MARKERS.search(line):
        return Candidate(line, HAZARD, citation, 0.75)

    if _OWNERSHIP_MARKERS.search(line):
        pointer = _pointerize(line)
        if pointer is None:
            # No durable pointer: hold it rather than persist a person.
            return Candidate(line, OWNERSHIP, citation, 0.4,
                             risks=(redaction.Risk(redaction.PERSON),))
        return Candidate(pointer, OWNERSHIP, citation, 0.7, abstracted=True)

    first = re.sub(r"[^a-z]", "", line.split(" ", 1)[0].lower())
    if first in _IMPERATIVES:
        return Candidate(line, default_kind, citation, 0.7)

    return None


def _pointerize(line: str) -> str | None:
    """Rewrite an ownership line to its durable pointer, or ``None`` if it has none.

    *"Ask Jane Doe or the platform team"* becomes *"Ownership is recorded in: the
    platform team"*. A line naming only a person has nothing durable to keep.
    """
    unique: dict[str, str] = {}
    for match in _POINTER_RE.finditer(line):
        pointer = match.group(0).strip()
        unique.setdefault(pointer.lower(), pointer)
    if not unique:
        return None
    return "Ownership is recorded in: " + ", ".join(list(unique.values())[:3])


def _dedupe(result: ExtractionResult) -> None:
    """Drop repeats in place, keeping the highest-confidence instance of each."""
    for bucket in (result.candidates, result.held):
        best: dict[str, Candidate] = {}
        for candidate in bucket:
            key = candidate.text.lower() if not candidate.held else candidate.id
            if key not in best or candidate.confidence > best[key].confidence:
                best[key] = candidate
        bucket[:] = sorted(
            best.values(),
            key=lambda c: (KIND_ORDER.index(c.kind), -c.confidence),
        )


__all__ = [
    "SETUP", "RUNBOOK_STEP", "GLOSSARY", "OWNERSHIP", "HAZARD", "KIND_ORDER",
    "Citation", "Candidate", "ExtractionResult", "extract",
]
