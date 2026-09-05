"""Re-run a session's question against a different context, and watch the scores move.

The KeelTrace P4 surface, and the replay core the model-comparison and
drift-replay ideas both need. Ablation is what turns the ledger from a report
into an instrument: a score tells you a session went badly, but only removing a
source and re-running tells you *that source was why*.

**What a variant actually is.** The question and the retrieved text are already
in the tier-two store, so a replay does not need the original engine, the
original repo state, or a live MCP server. It rebuilds the prompt from stored
payloads minus whatever is excluded, asks a provider, and files the answer as a
new session with its own trace id and its own payloads. The variant is therefore
scorable by exactly the same path as the original — ``session_feed`` cannot tell
them apart, which is the point.

**Two axes, one mechanism.** Holding the model fixed and varying the context is
ablation; holding the context fixed and varying the model is the model-fit
question from the backlog. Both are this function with a different argument, so
neither needs its own harness.

**Scoring is optional and separate.** Re-running needs a provider; scoring needs
Ragas and a judge. A replay with no scores still shows the answer changing,
which is often enough to see what a source was contributing — so a missing judge
degrades the instrument rather than disabling it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: How much stored context to put in one prompt. Matches the local engine's
#: own limit so a replay is shaped like the run it is standing in for.
MAX_CONTEXT_CHARS = 8000

_SYSTEM = ("You answer questions about a codebase/domain using the provided "
           "context. Be concise; ground your answer in the context.")


@dataclass
class Source:
    """One ablatable slice of a session's context.

    Grouped by ``(source, operation)`` rather than by individual payload: a
    reviewer thinks in terms of "turn off the KG" or "turn off Confluence", not
    "turn off retrieval number seven".
    """

    key: str
    source: str
    operation: str
    payloads: int = 0
    bytes: int = 0

    def to_dict(self) -> dict:
        return {"key": self.key, "source": self.source,
                "operation": self.operation, "payloads": self.payloads,
                "bytes": self.bytes}


@dataclass
class Variant:
    """One replay: what was excluded, what came back, and how it scored."""

    label: str
    trace_id: str = ""
    excluded: tuple[str, ...] = ()
    contexts: int = 0
    answer: str = ""
    model: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def ran(self) -> bool:
        return bool(self.answer)

    @property
    def scored(self) -> bool:
        return bool(self.scores)

    def to_dict(self) -> dict:
        return {
            "label": self.label, "trace_id": self.trace_id,
            "excluded": list(self.excluded), "contexts": self.contexts,
            "answer": self.answer, "model": self.model,
            "scores": self.scores, "problems": list(self.problems),
            "ran": self.ran, "scored": self.scored,
        }


@dataclass
class Comparison:
    """A baseline and its variants, with the deltas that are the whole point."""

    session_id: str
    baseline: Optional[Variant] = None
    variants: list[Variant] = field(default_factory=list)

    def deltas(self) -> list[dict]:
        """Per-variant score movement against the baseline.

        A metric the baseline could not score is omitted rather than treated as
        zero: "we could not measure this before" and "this got worse" are
        different findings and must not render the same.
        """
        if self.baseline is None or not self.baseline.scored:
            return []
        out = []
        for variant in self.variants:
            moved = {
                name: round(variant.scores[name] - value, 3)
                for name, value in self.baseline.scores.items()
                if name in variant.scores
            }
            out.append({"label": variant.label, "excluded": list(variant.excluded),
                        "delta": moved})
        return out

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "variants": [v.to_dict() for v in self.variants],
            "deltas": self.deltas(),
        }


# ── reading a session ───────────────────────────────────────────────────────

def _payloads(session_id: str) -> list:
    from agentic_cli import payload_store

    store = payload_store.get_store()
    if isinstance(store, payload_store.NullStore) or not hasattr(store, "session"):
        return []
    return store.session(session_id)


def _split(payloads: list) -> tuple[Optional[Any], Optional[Any], list]:
    from agentic_cli.evaluation import session_feed

    prompt = response = None
    contexts = []
    for payload in payloads:
        if payload.source == "session" and payload.operation == session_feed.PROMPT_OP:
            prompt = prompt or payload
        elif payload.source == "session" and payload.operation == session_feed.RESPONSE_OP:
            response = response or payload
        else:
            contexts.append(payload)
    return prompt, response, contexts


def source_key(payload) -> str:
    return f"{payload.source}/{payload.operation}"


def list_sources(session_id: str) -> list[Source]:
    """The context slices a replay can switch off, largest first."""
    _, _, contexts = _split(_payloads(session_id))
    grouped: dict[str, Source] = {}
    for payload in contexts:
        key = source_key(payload)
        slot = grouped.setdefault(
            key, Source(key=key, source=payload.source, operation=payload.operation))
        slot.payloads += 1
        slot.bytes += payload.bytes
    return sorted(grouped.values(), key=lambda s: (-s.bytes, s.key))


# ── replay ──────────────────────────────────────────────────────────────────

def replay(
    session_id: str,
    *,
    exclude: Optional[list[str]] = None,
    model: Optional[str] = None,
    label: str = "",
    store_variant: bool = True,
) -> Variant:
    """Re-ask the session's question with some context removed.

    ``exclude`` names source keys from :func:`list_sources`. ``model`` swaps the
    provider while leaving the context alone — the same mechanism, turned the
    other way.
    """
    from agentic_cli import payload_store, tracing
    from agentic_cli.tracker import new_correlation_id

    excluded = tuple(exclude or ())
    variant = Variant(label=label or ("baseline" if not excluded else
                                      "without " + ", ".join(excluded)),
                      excluded=excluded)

    prompt, _, contexts = _split(_payloads(session_id))
    if prompt is None:
        variant.problems.append(
            "No question stored for this session — nothing to re-ask.")
        return variant

    kept = [c for c in contexts if source_key(c) not in excluded]
    variant.contexts = len(kept)

    try:
        from agentic_cli.llm.factory import get_llm_provider

        provider = get_llm_provider(model_name=model, system_instruction=_SYSTEM)
        variant.model = provider.get_name()
    except Exception as exc:  # noqa: BLE001
        variant.problems.append(f"No model provider available: {exc}")
        return variant

    block = _render(kept)
    try:
        variant.answer = provider.generate(
            f"Question: {prompt.text}\n\nContext:\n{block}")
    except Exception as exc:  # noqa: BLE001
        variant.problems.append(f"Provider failed: {exc}")
        return variant

    if not store_variant:
        return variant

    # File the replay as a session of its own, so it is scorable by exactly the
    # same path as the original rather than through a parallel one.
    trace_id = new_correlation_id()
    variant.trace_id = trace_id
    store = payload_store.get_store()
    try:
        store.put(prompt.text, session_id=trace_id, source="session", operation="prompt")
        store.put(variant.answer, session_id=trace_id, source="session", operation="response")
        for payload in kept:
            store.put(payload.text, session_id=trace_id, source=payload.source,
                      operation=payload.operation, entity_id=payload.entity_id)
        tracing.record_context_read(
            source="playground", operation="replay", session_id=trace_id,
            entity_id=session_id,
            extra={"excluded": list(excluded), "model": variant.model,
                   "contexts": len(kept)},
        )
    except Exception as exc:  # noqa: BLE001 - a replay that ran is still useful
        logger.debug("variant not stored: %s", exc)
        variant.problems.append("Variant ran but could not be stored, so it "
                                "cannot be scored.")
    return variant


def _render(payloads: list) -> str:
    """Assemble stored context into one block, capped like the live path."""
    parts, total = [], 0
    for payload in payloads:
        chunk = f"### {payload.source}/{payload.operation}\n{payload.text}"
        if total + len(chunk) > MAX_CONTEXT_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n\n".join(parts) if parts else "(no context)"


def score(variant: Variant, metrics: Optional[list[str]] = None,
          framework: str = "ragas") -> Variant:
    """Score a stored variant in place. Leaves it unscored rather than failing."""
    from agentic_cli.evaluation import session_feed
    from agentic_cli.evaluation.frameworks import get_framework

    if not variant.trace_id:
        variant.problems.append("Variant was not stored, so it cannot be scored.")
        return variant

    feed = session_feed.build(variant.trace_id)
    if not feed.scorable:
        variant.problems.extend(feed.problems)
        return variant

    try:
        engine = get_framework(framework)
        result = engine.evaluate([feed.row], metrics or list(session_feed.DEFAULT_METRICS))
    except Exception as exc:  # noqa: BLE001 - no judge is not a failed experiment
        variant.problems.append(f"Not scored: {exc}")
        return variant

    variant.scores = {k: float(v) for k, v in (result.aggregate or {}).items()
                      if isinstance(v, (int, float))}
    return variant


def compare(
    session_id: str,
    ablations: Optional[list[list[str]]] = None,
    *,
    models: Optional[list[str]] = None,
    metrics: Optional[list[str]] = None,
    do_score: bool = True,
) -> Comparison:
    """Run a baseline plus one variant per ablation (or per model), and score them."""
    comparison = Comparison(session_id=session_id)

    baseline = replay(session_id, label="baseline")
    if do_score and baseline.ran:
        score(baseline, metrics)
    comparison.baseline = baseline

    for exclude in (ablations or []):
        variant = replay(session_id, exclude=exclude)
        if do_score and variant.ran:
            score(variant, metrics)
        comparison.variants.append(variant)

    for model in (models or []):
        variant = replay(session_id, model=model, label=f"model: {model}")
        if do_score and variant.ran:
            score(variant, metrics)
        comparison.variants.append(variant)

    return comparison


__all__ = [
    "MAX_CONTEXT_CHARS", "Source", "Variant", "Comparison", "source_key",
    "list_sources", "replay", "score", "compare",
]
