"""Session context ledger — the read side of the KeelTrace sensors.

Surfaces what an agent actually read during a session: which sources, in what
order, how much came back, and how long each retrieval took. The rows come
from the same audit trail everything else writes to, keyed by the session's
correlation id.

Reads only, except the Context Playground at the foot of this module: replaying
a session writes new payloads by design, because a variant has to be a session
in its own right to be scorable by the same path as the original.
"""

from typing import Optional

from pydantic import BaseModel


class ContextRead(BaseModel):
    """One retrieval: a single thing an agent read during a session."""

    id: int
    timestamp: str
    source: str                       # store family: mcp, kg, retriever
    operation: str                    # e.g. bitbucket/get_issue
    entity_id: Optional[str] = None   # what was read, when identifiable
    bytes: int = 0
    duration_ms: Optional[int] = None
    status: str = "success"
    args_digest: Optional[str] = None  # fingerprint; raw args are never stored
    payload_ref: Optional[str] = None  # reserved: pointer to retrieved text (P3)


class SourceRollup(BaseModel):
    source: str
    reads: int
    bytes: int


class SessionLedger(BaseModel):
    """A session's full context ledger plus its budget rollup."""

    session_id: str
    reads: int = 0
    bytes: int = 0
    errors: int = 0
    by_source: list[SourceRollup] = []
    entries: list[ContextRead] = []


class SessionRef(BaseModel):
    """A session that read context, for the picker."""

    session_id: str
    reads: int
    bytes: int
    errors: int
    sources: list[str] = []
    earliest: Optional[str] = None
    latest: Optional[str] = None


def _to_read(row: dict) -> ContextRead:
    from agentic_cli.tracing import details_of

    details = details_of(row)
    return ContextRead(
        id=row.get("id") or 0,
        timestamp=row.get("timestamp") or "",
        source=row.get("command") or "unknown",
        operation=row.get("subcommand") or "",
        entity_id=row.get("entity_id") or None,
        bytes=int(details.get("bytes") or 0),
        duration_ms=row.get("duration_ms"),
        status=row.get("status") or "success",
        args_digest=details.get("args_digest"),
        payload_ref=details.get("payload_ref"),
    )


def list_sessions(limit: int = 25) -> list[SessionRef]:
    """Recent sessions that read context, newest first."""
    try:
        from agentic_cli.tracing import list_sessions as _list
    except ImportError:
        return []
    return [SessionRef(**s) for s in _list(limit=limit)]


def get_ledger(session_id: str, limit: int = 500) -> SessionLedger:
    """Return one session's ordered ledger and its rollup.

    An unknown session is not an error — it is an empty ledger. A session may
    legitimately have read nothing, and callers should render that rather than
    handle an exception.
    """
    try:
        from agentic_cli.tracing import session_context, session_summary
    except ImportError:
        return SessionLedger(session_id=session_id)

    rows = session_context(session_id, limit=limit)
    summary = session_summary(session_id, limit=limit)
    return SessionLedger(
        session_id=session_id,
        reads=summary.get("reads", 0),
        bytes=summary.get("bytes", 0),
        errors=summary.get("errors", 0),
        by_source=[
            SourceRollup(source=src, reads=v["reads"], bytes=v["bytes"])
            for src, v in sorted(summary.get("by_source", {}).items())
        ],
        entries=[_to_read(r) for r in rows],
    )


# ---------------------------------------------------------------------------
# Context Playground (KeelTrace P4)
#
# Delegates to agentic_cli.evaluation.playground so the surface and the CLI
# cannot disagree about what an ablation is.
# ---------------------------------------------------------------------------

class PlaygroundSource(BaseModel):
    key: str
    source: str
    operation: str
    payloads: int = 0
    bytes: int = 0


class PlaygroundVariant(BaseModel):
    label: str
    trace_id: str = ""
    excluded: list[str] = []
    contexts: int = 0
    answer: str = ""
    model: str = ""
    scores: dict[str, float] = {}
    problems: list[str] = []
    ran: bool = False
    scored: bool = False


class PlaygroundRequest(BaseModel):
    """One experiment: a baseline plus a variant per ablation and per model."""

    ablations: list[list[str]] = []
    models: list[str] = []
    metrics: list[str] = []
    score: bool = True


class PlaygroundComparison(BaseModel):
    session_id: str
    baseline: Optional[PlaygroundVariant] = None
    variants: list[PlaygroundVariant] = []
    deltas: list[dict] = []
    store_enabled: bool = True


def playground_sources(session_id: str) -> list[PlaygroundSource]:
    """Context slices a replay can switch off."""
    from agentic_cli.evaluation import playground

    return [PlaygroundSource(**s.to_dict()) for s in playground.list_sources(session_id)]


def playground_run(session_id: str, request: PlaygroundRequest) -> PlaygroundComparison:
    """Run the experiment. Never raises for a missing judge or provider.

    A replay that ran but could not be scored is still the useful half of the
    instrument — the answer changing is often enough to see what a source was
    contributing — so failures land on the variant rather than on the response.
    """
    from agentic_cli import payload_store
    from agentic_cli.evaluation import playground

    store_enabled = not isinstance(payload_store.get_store(), payload_store.NullStore)
    comparison = playground.compare(
        session_id,
        ablations=request.ablations or None,
        models=request.models or None,
        metrics=request.metrics or None,
        do_score=request.score,
    )
    data = comparison.to_dict()
    return PlaygroundComparison(
        session_id=session_id,
        baseline=PlaygroundVariant(**data["baseline"]) if data["baseline"] else None,
        variants=[PlaygroundVariant(**v) for v in data["variants"]],
        deltas=data["deltas"],
        store_enabled=store_enabled,
    )
