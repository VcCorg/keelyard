"""Build an :class:`EvalRow` from a real session — the KeelTrace eval feed (P3).

``EvalRow.retrieved_contexts`` has existed since the eval framework was written
and nothing ever populated it, so every Ragas metric needing retrieved context
was silently scoring against an empty list. The framework was never incomplete;
it was starved. Tier one gave us the ledger, tier two gives us the text, and
this joins them into rows the existing adapter already knows how to score.

**What a live session can and cannot be scored on.** Two of the three metrics
KeelTrace named turn out to need a ground-truth answer, which a real session by
definition does not have:

| Metric | Reference needed | Usable on a session |
|---|---|---|
| Faithfulness | no | yes — did the answer follow from the context? |
| ResponseRelevancy | no | yes — did the answer address the question? |
| ContextPrecision (without reference) | no | yes — was the retrieved context useful? |
| ContextRecall | **yes** | no — needs the right answer to know what was missed |

So the reference-free set is what :data:`DEFAULT_METRICS` runs. ContextRecall
stays available for dataset-driven evaluation, where a reference exists; asking
for it here would score every session against an empty reference and return a
confident zero. That is worse than declining.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from agentic_cli.evaluation.frameworks.base import EvalRow

logger = logging.getLogger(__name__)

#: Payload operations that carry the question and the answer rather than context.
PROMPT_OP = "prompt"
RESPONSE_OP = "response"
_SESSION_SOURCE = "session"

#: Reference-free metrics a live session supports. See the module docstring for
#: why ContextRecall is absent.
DEFAULT_METRICS = ("faithfulness", "responserelevancy", "contextprecisionwithoutreference")

#: What the offline framework computes. Deliberately disjoint from the Ragas
#: names — a lexical overlap score is not a judgement about faithfulness, and a
#: table that mixed the two under one heading would invite exactly that reading.
HEURISTIC_METRICS = ("context_utilization", "context_contribution")


@dataclass
class FeedResult:
    """One session's row, plus why it might not be scorable."""

    session_id: str
    row: Optional[EvalRow] = None
    contexts: int = 0
    masked_kinds: tuple[str, ...] = ()
    problems: list[str] = field(default_factory=list)

    @property
    def scorable(self) -> bool:
        return self.row is not None and not self.problems

    @property
    def lossy(self) -> bool:
        """True when some context was masked before storage.

        A caller reporting a score without saying this is presenting a number
        computed over text the agent did not literally see.
        """
        return bool(self.masked_kinds)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "scorable": self.scorable,
            "contexts": self.contexts,
            "masked_kinds": list(self.masked_kinds),
            "lossy": self.lossy,
            "problems": list(self.problems),
        }


def build(session_id: str, reference: str = "") -> FeedResult:
    """Assemble the eval row for one session from the payload store.

    Every reason a session cannot be scored is collected rather than raised:
    "the store is off", "no answer was recorded" and "nothing was retrieved" are
    different problems with different fixes, and a single exception would flatten
    them into one.
    """
    from agentic_cli import payload_store

    result = FeedResult(session_id=session_id)
    store = payload_store.get_store()

    if isinstance(store, payload_store.NullStore):
        result.problems.append(
            "Payload store is disabled — there is no retrieved text to score "
            f"against. Set {payload_store.ENV_BACKEND} before the session runs.")
        return result

    if not hasattr(store, "session"):
        result.problems.append("This payload backend cannot list a session.")
        return result

    payloads = store.session(session_id)
    if not payloads:
        result.problems.append(
            "No payloads stored for this session. It may predate the store "
            "being enabled, or its payloads may have expired.")
        return result

    prompt = _first(payloads, PROMPT_OP)
    response = _first(payloads, RESPONSE_OP)
    contexts = [
        p for p in payloads
        if not (p.source == _SESSION_SOURCE and p.operation in (PROMPT_OP, RESPONSE_OP))
    ]

    if prompt is None:
        result.problems.append("No question recorded for this session.")
    if response is None:
        result.problems.append("No answer recorded — nothing to score.")
    if not contexts:
        result.problems.append(
            "No retrieved context recorded. Context metrics would score against "
            "an empty list, which reads as a failing retriever rather than an "
            "absent one.")

    result.contexts = len(contexts)
    masked: list[str] = []
    for payload in payloads:
        for kind in payload.masked:
            if kind not in masked:
                masked.append(kind)
    result.masked_kinds = tuple(masked)

    if result.problems:
        return result

    result.row = EvalRow(
        input_text=prompt.text,
        response=response.text,
        reference=reference,
        retrieved_contexts=[c.text for c in contexts],
        row_id=session_id,
    )
    return result


def _first(payloads: list, operation: str):
    for payload in payloads:
        if payload.source == _SESSION_SOURCE and payload.operation == operation:
            return payload
    return None


def metrics_for(reference: str = "", framework: str = "ragas") -> list[str]:
    """The metric set a session supports, for the framework about to score it."""
    if framework.lower() in ("heuristic", "offline"):
        # No judge, so a reference buys nothing here.
        return list(HEURISTIC_METRICS)
    metrics = list(DEFAULT_METRICS)
    if reference:
        # With ground truth the reference-bound metrics become meaningful.
        metrics.append("contextrecall")
    return metrics


def resolve_framework(preferred: str = "ragas") -> tuple[str, str]:
    """Pick a framework that can actually run. Returns ``(name, note)``.

    Falls back to the offline metrics when the judge-backed framework is
    unavailable, and returns a note saying so. The fallback is never silent:
    a heuristic reported under a Ragas heading would be read as a judgement it
    is not.
    """
    from agentic_cli.evaluation.frameworks import get_framework

    if preferred.lower() in ("heuristic", "offline"):
        return "heuristic", ""
    try:
        if get_framework(preferred).available():
            return preferred, ""
        reason = "its optional dependencies are not installed"
    except Exception as exc:  # noqa: BLE001 - unavailable, not broken
        reason = str(exc)
    return "heuristic", (
        f"{preferred} unavailable ({reason}); scored with offline heuristics "
        f"instead. These measure lexical grounding, not faithfulness.")


__all__ = [
    "PROMPT_OP", "RESPONSE_OP", "DEFAULT_METRICS", "HEURISTIC_METRICS",
    "FeedResult", "build", "metrics_for", "resolve_framework",
]
