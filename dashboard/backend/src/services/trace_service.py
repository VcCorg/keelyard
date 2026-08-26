"""Session context ledger — the read side of the KeelTrace sensors.

Surfaces what an agent actually read during a session: which sources, in what
order, how much came back, and how long each retrieval took. The rows come
from the same audit trail everything else writes to, keyed by the session's
correlation id.

Reads only. Nothing here writes to the tracker — the sensors do that, at the
point of retrieval (see ``agentic_cli.tracing``).
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
