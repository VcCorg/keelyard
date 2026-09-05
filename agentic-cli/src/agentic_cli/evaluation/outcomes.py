"""A run, and what it scored — with the context that informed it still attached.

The backlog entry this closes says the gap in one line: nothing in the codebase
models an experiment with a numeric result. Ablation varies the context and
scores the *answer*; competition work varies a feature set or a fold split, and
its result is a number arriving from outside — a leaderboard, a holdout, a
benchmark. Those are the same object seen from two sides, and only one of them
existed.

**This is deliberately not an experiment tracker.** MLflow and Weights & Biases
record parameters and metrics well, and the right move is to integrate with one
rather than rebuild it badly. What none of them record is *the context the agent
read while it wrote the run*, so "which forum thread led to the feature that
gained 0.003?" is unanswerable there. That join is the whole contribution here,
and it is already made — a session's ledger says what it read; this supplies the
other half.

So the surface stays small on purpose. No sweeps, no parameter grids, no charts,
no metric registry. One verb — attach a result to a run — and one query: rank
the runs and show what each of them read. Anything past that is rebuilding a
tool that already exists, and it is where this stops.

**The outcome is never computed here.** It is supplied, and the row records who
supplied it. Keel scores *context* quality; a leaderboard scores *model*
performance, and the moment this file starts deriving that number it is claiming
authority over ground truth it does not have.

**Direction travels with the metric.** RMSE improving means going down and
accuracy improving means going up, so a ranking that assumes one is wrong half
the time — silently, and in the direction that looks like progress. There is no
default: :func:`record` demands it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

#: Ledger family and entity type for outcome rows.
SOURCE = "outcome"
ENTITY_TYPE = "outcome"

#: Which direction counts as better. No default — see the module docstring.
HIGHER = "higher"
LOWER = "lower"
DIRECTIONS = (HIGHER, LOWER)


@dataclass
class Outcome:
    """One externally supplied result for one run."""

    session_id: str
    metric: str
    value: float
    direction: str
    domain: str = ""
    note: str = ""
    reported_by: str = ""
    recorded_at: str = ""

    @property
    def better_is(self) -> str:
        return "↑" if self.direction == HIGHER else "↓"

    def beats(self, other: "Outcome") -> bool:
        """True when this run scored better than ``other`` on the same metric.

        Comparing across metrics is refused rather than guessed: an RMSE and an
        accuracy have no ordering between them, and returning False would read
        as "did not beat" rather than "not comparable".
        """
        if self.metric != other.metric or self.direction != other.direction:
            raise ValueError(
                f"cannot compare {self.metric} with {other.metric}: "
                "different metrics have no ordering between them")
        return (self.value > other.value if self.direction == HIGHER
                else self.value < other.value)

    def to_dict(self) -> dict:
        return {"session_id": self.session_id, "metric": self.metric,
                "value": self.value, "direction": self.direction,
                "domain": self.domain, "note": self.note,
                "reported_by": self.reported_by,
                "recorded_at": self.recorded_at}


@dataclass
class Run:
    """A run: its outcome, and what its session read to produce it."""

    outcome: Outcome
    sources: dict[str, int] = field(default_factory=dict)
    tokens: int = 0
    model: str = ""

    @property
    def session_id(self) -> str:
        return self.outcome.session_id

    @property
    def context_keys(self) -> frozenset[str]:
        """The context slices this run read, for comparing one run to another."""
        return frozenset(self.sources)

    def to_dict(self) -> dict:
        return {**self.outcome.to_dict(), "sources": dict(self.sources),
                "tokens": self.tokens, "model": self.model}


def record(session_id: str, metric: str, value: float, *, direction: str,
           domain: str = "", note: str = "", reported_by: str = "") -> Outcome:
    """Attach a result to a run. The value is supplied, never derived.

    ``direction`` is required: see the module docstring on why there is no
    default. Raises rather than recording a row that cannot be ranked — an
    outcome nobody can order is not a cheaper outcome, it is a wrong one.

    The row goes in the ledger beside the session's context reads, which is what
    makes the join free: the same ``correlation_id`` already carries everything
    that session read.
    """
    from agentic_cli import tracing
    from agentic_cli.tracker import record_activity

    session_id = (session_id or "").strip()
    metric = (metric or "").strip()
    if not session_id:
        raise ValueError("an outcome needs the run it belongs to")
    if not metric:
        raise ValueError("an outcome needs a metric name")
    if direction not in DIRECTIONS:
        raise ValueError(
            f"direction must be one of {DIRECTIONS}; without it a ranking is "
            "wrong half the time, in the direction that looks like progress")
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"outcome value must be a number, got {value!r}") from exc

    outcome = Outcome(
        session_id=session_id, metric=metric, value=value, direction=direction,
        domain=domain or (tracing.current_domain() or ""),
        note=note, reported_by=reported_by)

    record_activity(
        SOURCE, "record",
        entity_type=ENTITY_TYPE,
        entity_id=metric,
        correlation_id=session_id,
        domain=outcome.domain or None,
        details=outcome.to_dict(),
    )
    return outcome


def for_session(session_id: str) -> list[Outcome]:
    """Every outcome recorded against one run, newest first.

    A list rather than one value: a competition run is routinely scored on a
    public and a private leaderboard, and a model on several holdouts. Keeping
    them apart is the difference between two numbers and one wrong one.
    """
    return _outcomes(_rows(correlation_id=session_id))


def _rows(correlation_id: str = "", domain: str = "", limit: int = 500) -> list[dict]:
    from agentic_cli.tracker import get_action_chain, get_activity

    try:
        if correlation_id:
            rows = get_action_chain(correlation_id, limit=limit)
        else:
            rows = get_activity(command=SOURCE, limit=limit)
    except Exception as exc:  # noqa: BLE001 - a readout must not raise
        logger.debug("could not read outcomes: %s", exc)
        return []
    out = [r for r in rows if r.get("entity_type") == ENTITY_TYPE]
    if domain:
        out = [r for r in out if (r.get("domain") or "") == domain]
    return out


def _outcomes(rows: list[dict]) -> list[Outcome]:
    from agentic_cli.tracing import details_of

    found: list[Outcome] = []
    for row in rows:
        data = details_of(row)
        try:
            found.append(Outcome(
                session_id=str(data.get("session_id") or row.get("correlation_id") or ""),
                metric=str(data.get("metric") or row.get("entity_id") or ""),
                value=float(data.get("value")),
                direction=str(data.get("direction") or ""),
                domain=str(data.get("domain") or row.get("domain") or ""),
                note=str(data.get("note") or ""),
                reported_by=str(data.get("reported_by") or ""),
                recorded_at=str(row.get("timestamp") or ""),
            ))
        except (TypeError, ValueError):
            # A row we cannot read is skipped, not defaulted to zero: a zero
            # would sort as a real result, which is worse than a missing one.
            logger.debug("unreadable outcome row: %s", row.get("id"))
            continue
    return sorted(found, key=lambda o: o.recorded_at, reverse=True)


def runs(domain: str = "", metric: str = "", limit: int = 500) -> list[Run]:
    """Runs with an outcome, best first, each carrying what its session read.

    Ranking needs one metric, because two metrics have no ordering between them.
    When ``metric`` is not given and the rows carry only one, that one is used;
    where they carry several this returns them unranked in recording order
    rather than inventing a comparison — the caller is told to name one.
    """
    found = _outcomes(_rows(domain=domain, limit=limit))
    if metric:
        found = [o for o in found if o.metric == metric]
    if not found:
        return []

    metrics = {o.metric for o in found}
    built = [Run(outcome=o, **_context_of(o.session_id)) for o in found]
    if len(metrics) == 1:
        direction = found[0].direction
        built.sort(key=lambda r: r.outcome.value, reverse=(direction == HIGHER))
    return built


def metrics_seen(domain: str = "") -> list[str]:
    """Metric names recorded for a domain, so a caller can name one."""
    return sorted({o.metric for o in _outcomes(_rows(domain=domain))})


def _context_of(session_id: str) -> dict:
    """What one run's session read: slices, total tokens, and the model."""
    from agentic_cli import tracing

    sources: dict[str, int] = {}
    tokens = 0
    try:
        rows = tracing.session_chain(session_id, limit=500)
    except Exception:  # noqa: BLE001
        return {"sources": sources, "tokens": tokens, "model": ""}

    for row in rows:
        if row.get("entity_type") != "context":
            continue
        key = f"{row.get('command') or '?'}/{(row.get('subcommand') or '').split('/')[-1]}"
        sources[key] = sources.get(key, 0) + 1
        tokens += int(row.get("tokens") or 0)

    model = ""
    try:
        model = tracing._engine_from_chain(rows).get("model_served") or ""
    except Exception:  # noqa: BLE001
        pass
    return {"sources": sources, "tokens": tokens, "model": model}


def context_delta(better: Run, worse: Run) -> dict:
    """What the better run read that the worse one did not, and vice versa.

    This is the question the backlog entry named — *which insight led to the
    feature that gained 0.003* — reduced to the part Keel can actually answer.
    It says what differed in the context, not which difference caused the gain:
    a correlation between one run's sources and its score is a lead to chase,
    and calling it a cause would be exactly the overreach this module refuses.
    """
    return {
        "only_in_better": sorted(better.context_keys - worse.context_keys),
        "only_in_worse": sorted(worse.context_keys - better.context_keys),
        "shared": sorted(better.context_keys & worse.context_keys),
        "token_delta": better.tokens - worse.tokens,
        "value_delta": better.outcome.value - worse.outcome.value,
    }


__all__ = ["SOURCE", "ENTITY_TYPE", "HIGHER", "LOWER", "DIRECTIONS",
           "Outcome", "Run", "record", "for_session", "runs", "metrics_seen",
           "context_delta"]
