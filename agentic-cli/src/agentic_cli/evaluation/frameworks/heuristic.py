"""Deterministic context metrics — no model, no network, no credential.

The Ragas metrics are the real instrument, and they need a judge. That makes the
one thing the Context Playground exists to show — scores moving when a source is
removed — depend on a cloud round trip, which is both a demo risk and a hole in
the claim that Keel runs on your own infrastructure. The built-in framework does
not help: ``accuracy``, ``f1_score`` and ``bleu_score`` are all reference-based,
so a live session with no ground truth scores nothing at all.

These two metrics fill that gap. They are **heuristics and named as such** — no
overlap with a Ragas metric name — because a lexical overlap score is not a
judgement about faithfulness, and quoting it as one would be the same mistake as
scoring a truncated payload.

    context_utilization   how much of the answer is carried by the retrieved text
    context_contribution  how much of the retrieved text the answer actually used

They are inverses of each other, and that is the point. Under ablation:

- Remove a source the answer never needed → **utilization holds**, contribution
  rises. The source was dead weight.
- Remove the source the answer depended on → the replay either drops those facts
  or invents replacements, and **utilization falls**. That source was load-bearing.

So the pair separates "we are carrying context nobody reads" from "we just
removed the thing that was holding the answer up" without asking a model
anything.

**What they cannot do.** Neither notices a *correct* claim phrased in words the
context never used, and neither knows whether a supported claim is true. They
measure lexical grounding, which is a proxy. Where a judge is available, prefer
Ragas — these exist so the instrument still works when it is not.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from agentic_cli.evaluation.frameworks.base import EvalFramework, EvalRow, EvalScores

#: Share of the answer's content carried by the retrieved context.
UTILIZATION = "context_utilization"
#: Share of retrieved chunks that contributed anything to the answer.
CONTRIBUTION = "context_contribution"

METRICS = (UTILIZATION, CONTRIBUTION)

#: Words carrying no topical signal. Kept small and explicit rather than pulled
#: from a corpus package — a dependency here would defeat the purpose.
_STOP = frozenset("""
a an the and or but if then than so because as of at by for with about against
between into through during before after above below to from up down in out on
off over under again further once here there when where why how all any both
each few more most other some such no nor not only own same too very can will
just should now do does did done is are was were be been being have has had
having i you he she it we they them his her its our your their this that these
those what which who whom would could may might must shall
""".split())

_TOKEN = re.compile(r"[a-z0-9][a-z0-9._/-]*")


def _content_tokens(text: str) -> list[str]:
    """Lowercase content words, keeping identifiers like ``.tool-versions``."""
    return [t for t in _TOKEN.findall((text or "").lower())
            if t not in _STOP and len(t) > 1]


def _grams(text: str) -> set[str]:
    """Unigrams plus bigrams, pooled.

    Bigrams alone are too brittle for short answers; unigrams alone let common
    domain vocabulary inflate the score. Pooling both is the cheap compromise,
    and it is a compromise — see the module docstring.
    """
    tokens = _content_tokens(text)
    grams = set(tokens)
    grams.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
    return grams


def _containment(inner: set[str], outer: set[str]) -> float:
    """Share of ``inner`` present in ``outer``. Empty ``inner`` scores 0."""
    return len(inner & outer) / len(inner) if inner else 0.0


def utilization(row: EvalRow) -> float:
    """How much of the answer is carried by the retrieved context."""
    answer = _grams(row.response)
    context = set()
    for chunk in row.retrieved_contexts or []:
        context |= _grams(chunk)
    return _containment(answer, context)


def contribution(row: EvalRow) -> float:
    """Share of retrieved chunks that put something into the answer.

    Chunk-level rather than token-level on purpose: the actionable unit is
    "this source earned its place", and a chunk contributing one supported
    phrase has earned it.
    """
    chunks = row.retrieved_contexts or []
    if not chunks:
        return 0.0
    answer = _grams(row.response)
    if not answer:
        return 0.0
    used = sum(1 for chunk in chunks if _grams(chunk) & answer)
    return used / len(chunks)


_SCORERS = {UTILIZATION: utilization, CONTRIBUTION: contribution}


class HeuristicFramework(EvalFramework):
    """Context metrics computable offline, in test mode, and in CI."""

    name = "heuristic"

    def supported_metrics(self) -> List[str]:
        return list(METRICS)

    def validate_metrics(self, metrics: List[str]) -> List[str]:
        """Return the requested metrics this framework can actually compute."""
        return [m for m in metrics if m.lower() in _SCORERS]

    def evaluate(
        self,
        rows: List[EvalRow],
        metrics: List[str],
        **_: Any,
    ) -> EvalScores:
        wanted = self.validate_metrics(metrics) or list(METRICS)
        scores = EvalScores(framework=self.name)
        scores.metric_ranges = {name: (0.0, 1.0) for name in wanted}

        for row in rows:
            scores.per_row.append(
                {name: round(_SCORERS[name.lower()](row), 4) for name in wanted})

        for name in wanted:
            values = [r[name] for r in scores.per_row if name in r]
            if values:
                scores.aggregate[name] = round(sum(values) / len(values), 4)

        unknown = [m for m in metrics if m.lower() not in _SCORERS]
        if unknown:
            # Named rather than dropped: a caller asking for faithfulness here
            # should learn it was not computed, not read a table that quietly
            # lost a column.
            scores.errors.append(
                f"Not computable without a judge, so omitted: {', '.join(unknown)}. "
                f"This framework computes {', '.join(METRICS)}.")
        return scores


__all__ = [
    "UTILIZATION", "CONTRIBUTION", "METRICS", "HeuristicFramework",
    "utilization", "contribution",
]
