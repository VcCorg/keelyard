"""Session tracing - record what enters an agent's context.

WHY THIS EXISTS
    The tracker records what the platform *did* (commands run, sessions
    created, repos onboarded) but not what an agent *read*. Retrieval is
    invisible: MCP tool calls and KG queries leave no trace. That makes two
    things impossible.

    First, provenance - answering "why did the agent say that?" by pointing at
    the sources that produced the claim.

    Second, context-aware evaluation. ``EvalRow.retrieved_contexts`` exists in
    ``evaluation/frameworks/base.py`` and ``ragas_adapter.py`` consumes it, but
    nothing in the codebase populates it. Every Ragas metric that needs
    retrieved context - Faithfulness, ContextPrecision, ContextRecall - is
    silently scoring against an empty list.

    Both are downstream of the same missing sensor. This module is that sensor.

SESSION IDENTITY
    Reuses the tracker's existing ``correlation_id`` column, which is already
    indexed and already documented as "links a chain of actions across
    features". No schema migration.

PROPAGATION, AND THE THREAD TRAP
    The id travels ambiently in a ``ContextVar`` rather than through every call
    signature - retrieval helpers are reached from roughly eighteen call sites
    across the CLI and the dashboard, and threading a parameter through all of
    them would be its own refactor.

    The trap: **ContextVars do not propagate across ``threading.Thread``.**
    ``mcp_tool_client._run_async`` spawns a thread with its own event loop when
    it is called from an async caller, which is exactly what the FastAPI
    dashboard does. A sensor reading the ContextVar *inside* the coroutine sees
    ``None`` - but only when driven from the dashboard, never from the CLI,
    which makes it look like a flake.

    So sensors read the session id on the CALLER's thread and pass it in
    explicitly. See ``mcp_tool_client.call_mcp_tool``.

STORAGE TIERS
    This module writes tier one only: metadata that is cheap, queryable, and
    safe to retain. Tool arguments are digested, never stored raw, because they
    routinely carry tokens and identifiers.

    Tier two - the retrieved text itself, which Ragas needs - is deliberately
    not here. It requires size caps, a retention policy, and redaction, and
    putting proprietary document bodies in the audit database by default would
    be the wrong default. ``payload_ref`` is the seam it will hang from.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

# The active session id, or None when work is not running under a session.
# Unattributed reads are still recorded - a context read with no session is
# less useful than one with, but far more useful than a missing row.
_session_id: ContextVar[Optional[str]] = ContextVar("keel_session_id", default=None)

# Tier-one rows record shape, not content. A single oversized value should not
# be able to bloat the audit database through the details column.
MAX_ENTITY_ID = 512


def current_session_id() -> Optional[str]:
    """Return the active session id, or None if not inside a session."""
    return _session_id.get()


def set_session_id(session_id: Optional[str]) -> Any:
    """Bind a session id to the current context. Returns a reset token.

    Pair with :func:`reset_session_id` in a ``try/finally``, or prefer
    :func:`session_scope`, which does that for you.
    """
    return _session_id.set(session_id)


def reset_session_id(token: Any) -> None:
    """Restore the session id bound before ``set_session_id`` returned *token*."""
    try:
        _session_id.reset(token)
    except (ValueError, LookupError) as exc:
        # Token minted in a different Context (e.g. reset from another thread).
        # Losing the restore is survivable; failing the caller is not.
        logger.debug("session id not reset: %s", exc)


@contextlib.contextmanager
def session_scope(session_id: Optional[str] = None) -> Iterator[str]:
    """Bind a session id for the duration of the block.

    Generates one when not supplied, so callers that just want their reads
    grouped do not have to mint ids themselves::

        with session_scope() as sid:
            ...          # every context read in here carries sid
    """
    if not session_id:
        from agentic_cli.tracker import new_correlation_id

        session_id = new_correlation_id()
    token = _session_id.set(session_id)
    try:
        yield session_id
    finally:
        _session_id.reset(token)


def digest_args(arguments: Optional[Dict[str, Any]]) -> str:
    """Fingerprint tool arguments without storing them.

    Arguments carry tokens, ticket bodies, and file contents. A digest still
    lets two identical retrievals be recognised as identical - enough to spot a
    duplicated call - without retaining anything sensitive.
    """
    if not arguments:
        return ""
    try:
        canonical = json.dumps(arguments, sort_keys=True, default=str)
    except Exception:  # noqa: BLE001 - never fail a call over telemetry
        canonical = repr(arguments)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def measure(value: Any) -> int:
    """Approximate the byte size of a retrieval result, defensively."""
    try:
        if value is None:
            return 0
        if isinstance(value, (bytes, bytearray)):
            return len(value)
        if isinstance(value, str):
            return len(value.encode("utf-8"))
        return len(json.dumps(value, default=str).encode("utf-8"))
    except Exception:  # noqa: BLE001
        try:
            return len(repr(value))
        except Exception:  # noqa: BLE001
            return 0


def record_context_read(
    *,
    source: str,
    operation: str,
    session_id: Optional[str] = None,
    entity_id: str = "",
    size_bytes: int = 0,
    duration_ms: Optional[int] = None,
    status: str = "success",
    arguments: Optional[Dict[str, Any]] = None,
    payload_ref: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Record one context read against the active (or given) session.

    ``source`` is the store family - ``mcp``, ``kg``, ``retriever``.
    ``operation`` is what was called, e.g. ``jira/get_issue``.

    ``session_id`` should be passed explicitly by any caller that may cross a
    thread boundary before reaching here; it falls back to the ContextVar.

    This function never raises. Telemetry must not be able to break retrieval:
    a failure to record is logged at debug and swallowed.
    """
    try:
        # record_activity, not record_action: the latter is a convenience
        # wrapper that drops duration_ms, and retrieval latency is worth a real
        # indexed column rather than a field buried in the details JSON.
        from agentic_cli.tracker import record_activity

        details: Dict[str, Any] = {"bytes": int(size_bytes)}
        digest = digest_args(arguments)
        if digest:
            details["args_digest"] = digest
        if payload_ref:
            details["payload_ref"] = payload_ref
        if extra:
            details.update(extra)

        record_activity(
            source,
            operation,
            entity_type="context",
            entity_id=(entity_id or "")[:MAX_ENTITY_ID],
            correlation_id=session_id if session_id is not None else current_session_id(),
            duration_ms=duration_ms,
            status=status,
            details=details,
        )
    except Exception as exc:  # noqa: BLE001 - telemetry is never load-bearing
        logger.debug("context read not recorded: %s", exc)


def session_chain(session_id: str, limit: int = 500) -> list[dict]:
    """Every audited action in a session, oldest first - reads and the rest."""
    try:
        from agentic_cli.tracker import get_action_chain

        return get_action_chain(session_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not read session chain: %s", exc)
        return []


def session_context(session_id: str, limit: int = 500) -> list[dict]:
    """Return the ordered context ledger for one session.

    The read side of the sensor: every context read recorded under
    ``session_id``, oldest first. Filters the full chain down to context rows,
    so the session's own audit entries do not appear as retrievals.
    """
    return [r for r in session_chain(session_id, limit=limit)
            if r.get("entity_type") == "context"]


def session_summary(session_id: str, limit: int = 500) -> Dict[str, Any]:
    """Roll up a session's context ledger: totals, and a per-source breakdown.

    This is what the ledger view and the context-budget readout are built from.
    """
    rows = session_context(session_id, limit=limit)
    by_source: Dict[str, Dict[str, int]] = {}
    total_bytes = 0
    errors = 0
    for r in rows:
        src = r.get("command") or "unknown"
        details = r.get("details") or {}
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except (ValueError, TypeError):
                details = {}
        size = int(details.get("bytes") or 0)
        total_bytes += size
        if r.get("status") == "error":
            errors += 1
        slot = by_source.setdefault(src, {"reads": 0, "bytes": 0})
        slot["reads"] += 1
        slot["bytes"] += size
    return {
        "session_id": session_id,
        "reads": len(rows),
        "bytes": total_bytes,
        "errors": errors,
        "by_source": by_source,
    }
