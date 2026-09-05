"""Did the source change in a way that touches what we drew from it?

Drift detection today is digest-based: :func:`agentic_cli.retrieval.is_stale`
says a file moved. That is the right question for "should we look again" and the
wrong one for "is our context still true" — a typo fix and a reversed
instruction both change the digest, and the reviewer is handed the same
undifferentiated pile either way. Running against this repository, a single
formatting pass over ``CONTRIBUTING.md`` marks every instruction drawn from it
as needing a decision.

:func:`proposal.merge` already pairs an approved instruction with its
replacement — but only when the answer is *exactly one*, deliberately, because
matching by source alone would pair candidates arbitrarily and show a reviewer a
diff that never happened. That leaves the common case unhandled: a document
yielding six setup steps, one of which was reworded, has six fresh candidates
and one orphan, so nothing pairs. This module is the part ``merge`` refused to
guess at, done with evidence instead.

Four verdicts, and the split between the last two is the point:

``UNCHANGED``     the instruction came back with the same id. Nothing to do.
``REWORDED``      the source says this again, differently.
``CONTRADICTED``  the source now says something incompatible with it.
``ABSENT``        nothing at this source covers it any more.
``UNKNOWN``       we could not re-read the source. Never a verdict about it.

**Similarity is deterministic; agreement needs a judge.** Token overlap cannot
tell ``always run migrations before deploy`` from ``never run migrations before
deploy`` — they are the same sentence. So the lexical tier decides only *which
new instruction is talking about the same thing*, and whether the two agree is a
separate question. Without a judge, a pair is ``REWORDED`` with
:attr:`Verdict.checked` false, and nothing fast-forwards on it: we know the
source still speaks to this instruction, not that it still supports it.

One contradiction is catchable offline, and it is the one that matters most: a
negation appearing or disappearing across an otherwise-matching pair. Negation
markers are stripped before similarity is measured *on purpose*, so a reversed
instruction scores as a near-perfect match and is then caught by the profile
comparison rather than sailing through as a reword.

**Pairing is assigned across the whole source, not per instruction.** Two
orphans left to choose independently will both claim the single best candidate.
Matching runs greedily, best pair first, each side consumed once — so an
instruction is only ever paired with a candidate no better-matching instruction
wanted.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Iterable, Optional

from agentic_cli.onboarding.extract import Candidate, Citation

UNCHANGED = "unchanged"
REWORDED = "reworded"
CONTRADICTED = "contradicted"
ABSENT = "absent"
UNKNOWN = "unknown"

#: A pair must score at least this to be considered the same instruction.
#:
#: Calibrated, not guessed. Measured over this repository's own corpus — 161
#: instructions from 40 documents, giving 544 same-kind same-source pairs that
#: are all non-matches by construction — 0.60 admits 3 of them (0.55%), and
#: lowering it to 0.55 or 0.50 buys no additional true reword while 0.50 more
#: than doubles the false pairs. Rewordings of real instructions from this repo
#: score 0.53-0.92, so the bar sits inside a genuine gap rather than on a slope.
#:
#: The three admitted pairs are near-identical templated instructions (the same
#: sentence for two different credentials). They are harmless in practice for a
#: structural reason: an instruction that came back unchanged is removed from the
#: matching pool, so a surviving twin can never be offered as its deleted
#: sibling's replacement.
STRONG = 0.60

#: Words whose presence or absence flips an instruction's meaning. Removed
#: before similarity is measured, then compared separately — see the module
#: docstring.
_NEGATIONS = frozenset({
    "not", "no", "never", "dont", "cannot", "cant", "wont", "shouldnt",
    "mustnt", "avoid", "without", "neither", "nor", "unless", "except",
})

#: Function words that inflate the similarity of unrelated imperatives.
_STOPWORDS = frozenset({
    "a", "an", "the", "to", "of", "in", "on", "at", "for", "with", "and",
    "or", "is", "are", "be", "you", "your", "it", "this", "that", "from",
    "as", "by", "into", "then", "when", "if", "will", "should", "must",
})

_WORD = re.compile(r"[a-z0-9][a-z0-9._/-]*")


@dataclass
class Verdict:
    """What became of one approved instruction at its source."""

    entry_id: str
    status: str
    similarity: float = 0.0
    replacement: str = ""
    replacement_id: str = ""
    #: True when something ruled on *agreement*, not merely on similarity: a
    #: judge, or a negation flip. False means the pair is unverified.
    checked: bool = False
    detail: str = ""

    @property
    def settled(self) -> bool:
        """True when this needs no human: unchanged, or a verified reword."""
        return self.status == UNCHANGED or (self.status == REWORDED and self.checked)

    @property
    def actionable(self) -> bool:
        """True when a human owes this a decision."""
        return self.status in (CONTRADICTED, ABSENT) or (
            self.status == REWORDED and not self.checked)

    def to_dict(self) -> dict:
        out = {"entry_id": self.entry_id, "status": self.status,
               "similarity": round(self.similarity, 3), "checked": self.checked}
        if self.replacement:
            out["replacement"] = self.replacement
            out["replacement_id"] = self.replacement_id
        if self.detail:
            out["detail"] = self.detail
        return out


@dataclass
class Report:
    """Every verdict for one domain, and how it was reached."""

    verdicts: list[Verdict] = field(default_factory=list)
    model: str = ""
    #: Sources we could not re-read. Their instructions are UNKNOWN, not absent.
    unreadable: list[str] = field(default_factory=list)

    def of(self, status: str) -> list[Verdict]:
        return [v for v in self.verdicts if v.status == status]

    @property
    def actionable(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.actionable]

    @property
    def settled(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.settled]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in self.verdicts:
            out[v.status] = out.get(v.status, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "counts": self.counts,
            "unreadable": list(self.unreadable),
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


# ── lexical tier ────────────────────────────────────────────────────────────

def _normalise(text: str) -> list[str]:
    return _WORD.findall((text or "").lower().replace("'", ""))


def content_tokens(text: str) -> list[str]:
    """Comparison tokens: no stopwords, and **no negations**.

    Dropping negations is deliberate. It makes a reversed instruction score as a
    near-identical match, which is what puts it in front of the contradiction
    check instead of letting it pass as an unrelated new candidate.
    """
    return [t for t in _normalise(text)
            if t not in _STOPWORDS and t not in _NEGATIONS]


def negation_profile(text: str) -> frozenset[str]:
    """The negation markers an instruction carries."""
    return frozenset(t for t in _normalise(text) if t in _NEGATIONS)


def similarity(left: str, right: str) -> float:
    """How much two instructions are talking about the same thing (0..1).

    The better of two views, because rewording takes two shapes and each metric
    is blind to one of them. Sequence ratio reads edits in place — an added
    flag, a changed value — but collapses on reordering: *"Run keel doctor to
    verify the environment"* against *"Verify the environment by running keel
    doctor"* scores 0.40, which is indistinguishable from unrelated. Token
    overlap reads the reorder at 0.67 and is in turn blind to order.

    Taking the maximum cost nothing measurable: over the 544 real non-matching
    pairs this corpus provides, the blend admits exactly the same three as the
    sequence ratio alone at every threshold from 0.50 to 0.65. It only lifts the
    pairs that genuinely say the same thing in a different order.
    """
    a, b = content_tokens(left), content_tokens(right)
    if not a or not b:
        return 0.0
    ordered = SequenceMatcher(None, a, b).ratio()
    sa, sb = set(a), set(b)
    overlap = len(sa & sb) / len(sa | sb)
    return max(ordered, overlap)


def _source_key(citation: str) -> str:
    """Pairs are matched within a source, deliberately **not** within a kind.

    ``merge`` groups by ``(kind, ref)`` because it pairs by group size and needs
    every constraint it can get. Here the evidence is a measured score, so kind
    adds nothing — and it actively hides the case worth catching most. Negating
    an instruction changes its extracted kind: ``Check the license before adding
    a dependency`` is a ``setup`` step, and ``Do not check the license before
    adding a dependency`` is a ``hazard``, because "do not" is a hazard marker.
    Requiring the kinds to agree makes a reversed instruction structurally
    invisible — it reports as one absent step plus one unrelated new hazard.

    Measured on this repository's corpus, dropping the constraint admits 376
    additional cross-kind pairs and **none** of them clears 0.60; the highest
    scores 0.545. It costs nothing and buys the contradiction check its inputs.
    """
    return Citation.parse(citation).ref


def _pair(entries: list, candidates: list[Candidate],
          threshold: float) -> tuple[list[tuple[Any, Candidate, float]], list]:
    """Greedily match entries to candidates, best pair first.

    Returns the matched triples and the entries nothing was found for. Each side
    is consumed once: an entry is paired only with a candidate that no
    better-matching entry wanted, which is what keeps two orphans from both
    claiming the same replacement.
    """
    scored: list[tuple[float, int, int]] = []
    for i, entry in enumerate(entries):
        for j, candidate in enumerate(candidates):
            if candidate.held:
                continue    # held text is never written, so never proposed
            score = similarity(entry.text, candidate.text)
            if score >= threshold:
                scored.append((score, i, j))
    # Sort by score, then by index, so equal scores resolve the same way twice.
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))

    used_entries: set[int] = set()
    used_candidates: set[int] = set()
    matched: list[tuple[Any, Candidate, float]] = []
    for score, i, j in scored:
        if i in used_entries or j in used_candidates:
            continue
        used_entries.add(i)
        used_candidates.add(j)
        matched.append((entries[i], candidates[j], score))
    unmatched = [e for i, e in enumerate(entries) if i not in used_entries]
    return matched, unmatched


# ── judge tier ──────────────────────────────────────────────────────────────

AGREES = "agrees"
CONTRADICTS = "contradicts"
UNRELATED = "unrelated"

_JUDGE_PROMPT = """You are checking whether a team's approved onboarding \
instructions still hold, after the documents they came from were edited.

Each numbered item gives the APPROVED instruction and the CURRENT text found at \
the same source. For each, decide:

- "agrees"      - the current text says the same thing; only the wording moved
- "contradicts" - the current text says something incompatible with the approved
                  instruction (a reversed step, a changed command, a different
                  required order or value)
- "unrelated"   - the current text is about something else; the approved
                  instruction is no longer supported here

Judge only what the two texts say. A difference in detail that changes what \
someone would DO is "contradicts", not "agrees". Reply with JSON only, an array \
of objects with keys "n", "verdict", and "why" (at most 15 words).

ITEMS
-----
{items}
"""


def _ask_judge(pairs: list[tuple[Any, Candidate, float]],
               provider: Any) -> Optional[dict[int, tuple[str, str]]]:
    """Rule on agreement for each pair. ``None`` when the judge is unusable.

    Every failure path returns ``None`` rather than a verdict: a provider that
    raises, an unparseable reply, an empty batch. A judge having a bad day must
    not be able to mark a contradiction as agreement — the caller falls back to
    an unverified reword, which still asks a human.
    """
    if not pairs or provider is None:
        return None
    items = "\n\n".join(
        f"{i + 1}.\nAPPROVED: {entry.text}\nCURRENT: {candidate.text}"
        for i, (entry, candidate, _) in enumerate(pairs))
    try:
        raw = provider.generate(_JUDGE_PROMPT.format(items=items[:60_000]))
    except Exception:  # noqa: BLE001 - a judge failure is not a drift verdict
        return None
    return _parse(raw, len(pairs))


def _parse(raw: str, expected: int) -> Optional[dict[int, tuple[str, str]]]:
    """Read the judge's JSON, tolerating fenced or prose-wrapped replies."""
    if not raw:
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    else:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end > start:
            text = text[start:end + 1]
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, list) or not data:
        return None

    out: dict[int, tuple[str, str]] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("n")) - 1
        except (TypeError, ValueError):
            continue
        verdict = str(item.get("verdict") or "").strip().lower()
        if 0 <= index < expected and verdict in (AGREES, CONTRADICTS, UNRELATED):
            out[index] = (verdict, str(item.get("why") or "")[:120])
    return out or None


# ── the diff ────────────────────────────────────────────────────────────────

def diff(entries: Iterable, candidates: Iterable[Candidate], *,
         provider: Any = None, threshold: float = STRONG) -> Report:
    """Rule on each approved instruction against a fresh extraction.

    ``entries`` are approved :class:`~agentic_cli.onboarding.proposal.Entry`
    objects; ``candidates`` are what re-extracting their sources produced now.
    Replacements are looked for within a source but across kinds — see
    :func:`_source_key` for why the kind constraint had to go.
    """
    entries = [e for e in entries if getattr(e, "text", "")]
    candidates = list(candidates)
    candidate_ids = {c.id for c in candidates}

    verdicts: list[Verdict] = []
    outstanding: list = []
    survived: set[str] = set()
    for entry in entries:
        if entry.id in candidate_ids:
            survived.add(entry.id)
            verdicts.append(Verdict(entry_id=entry.id, status=UNCHANGED,
                                    similarity=1.0, checked=True,
                                    detail="Same instruction, same source."))
        else:
            outstanding.append(entry)

    # Group both sides by (kind, source) and match within each group.
    entry_groups: dict[str, list] = {}
    for entry in outstanding:
        entry_groups.setdefault(_source_key(entry.citation), []).append(entry)

    # A candidate that re-proposed an approved instruction verbatim is spoken
    # for; offering it as somebody else's replacement would move an instruction
    # off a source that still carries it.
    candidate_groups: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        if candidate.id in survived:
            continue
        candidate_groups.setdefault(
            _source_key(str(candidate.citation)), []).append(candidate)

    pairs: list[tuple[Any, Candidate, float]] = []
    for key, group in entry_groups.items():
        matched, unmatched = _pair(group, candidate_groups.get(key, []), threshold)
        pairs.extend(matched)
        for entry in unmatched:
            verdicts.append(Verdict(
                entry_id=entry.id, status=ABSENT, checked=True,
                detail="Nothing at this source covers it any more."))

    # A negation flip is a contradiction we can see without a model, and it is
    # the one most worth catching: the pair scores near-perfectly precisely
    # because negations were stripped before scoring.
    undecided: list[tuple[Any, Candidate, float]] = []
    for entry, candidate, score in pairs:
        if negation_profile(entry.text) != negation_profile(candidate.text):
            verdicts.append(Verdict(
                entry_id=entry.id, status=CONTRADICTED, similarity=score,
                replacement=candidate.text, replacement_id=candidate.id,
                checked=True,
                detail="A negation appears on one side and not the other."))
        else:
            undecided.append((entry, candidate, score))

    rulings = _ask_judge(undecided, provider)
    model = ""
    if rulings is not None:
        try:
            model = provider.get_name()
        except Exception:  # noqa: BLE001
            pass

    for i, (entry, candidate, score) in enumerate(undecided):
        ruling = (rulings or {}).get(i)
        if ruling is None:
            # Unverified: the source still speaks to this instruction, but
            # nothing has said the two agree. That is a reword a human reads.
            verdicts.append(Verdict(
                entry_id=entry.id, status=REWORDED, similarity=score,
                replacement=candidate.text, replacement_id=candidate.id,
                checked=False,
                detail="Reworded at its source; agreement not verified."))
            continue
        verdict, why = ruling
        status = {AGREES: REWORDED, CONTRADICTS: CONTRADICTED,
                  UNRELATED: ABSENT}[verdict]
        verdicts.append(Verdict(
            entry_id=entry.id, status=status, similarity=score,
            replacement="" if status == ABSENT else candidate.text,
            replacement_id="" if status == ABSENT else candidate.id,
            checked=True, detail=why))

    return Report(verdicts=verdicts, model=model)


def unknown_for(entries: Iterable, source: str = "") -> Report:
    """Every instruction from a source we could not re-read.

    A source we could not reach tells us nothing about the instructions drawn
    from it, and reporting them absent would retract the team's own approved
    context because a checkout was missing.
    """
    entries = list(entries)
    return Report(
        verdicts=[Verdict(entry_id=e.id, status=UNKNOWN,
                          detail="Source could not be read.") for e in entries],
        unreadable=[source] if source else [],
    )


def merge_reports(reports: Iterable[Report]) -> Report:
    """Fold per-source reports into one, keeping the model that was used."""
    out = Report()
    for report in reports:
        out.verdicts.extend(report.verdicts)
        out.unreadable.extend(report.unreadable)
        out.model = out.model or report.model
    return out


__all__ = [
    "UNCHANGED", "REWORDED", "CONTRADICTED", "ABSENT", "UNKNOWN", "STRONG",
    "AGREES", "CONTRADICTS", "UNRELATED", "Verdict", "Report",
    "content_tokens", "negation_profile", "similarity", "diff",
    "unknown_for", "merge_reports",
]
