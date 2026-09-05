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

# Which project (domain) the current work belongs to. Separate from the session
# id because the two have different lifetimes: a domain outlives any one session
# — `domain extract` binds it for a command that mints no session at all — and a
# session can legitimately have no domain, which is a category worth counting
# rather than a gap to fill in.
_session_domain: ContextVar[Optional[str]] = ContextVar(
    "keel_session_domain", default=None)

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


def current_domain() -> Optional[str]:
    """Which project the current work is for, or None when unattributed."""
    return _session_domain.get()


def set_domain(domain: Optional[str]) -> Any:
    """Bind a domain to the current context. Returns a reset token."""
    return _session_domain.set(domain or None)


def reset_domain(token: Any) -> None:
    """Restore the domain bound before :func:`set_domain` returned *token*."""
    try:
        _session_domain.reset(token)
    except (ValueError, LookupError) as exc:
        logger.debug("session domain not reset: %s", exc)


@contextlib.contextmanager
def session_scope(session_id: Optional[str] = None,
                  domain: Optional[str] = None) -> Iterator[str]:
    """Bind a session id — and the project it is for — for the block.

    Generates an id when not supplied, so callers that just want their reads
    grouped do not have to mint ids themselves::

        with session_scope(domain="titanic") as sid:
            ...          # every read in here carries sid AND the domain

    ``domain`` is what makes "what did this project cost" answerable. It rides
    a ContextVar for the same reason the session id does: the read that matters
    happens several frames down, inside a fetcher or an MCP client, and
    threading a project name through every signature on the way is how the
    attribution ends up missing from exactly the paths nobody remembered.
    """
    if not session_id:
        from agentic_cli.tracker import new_correlation_id

        session_id = new_correlation_id()
    token = _session_id.set(session_id)
    domain_token = _session_domain.set(domain or _session_domain.get())
    try:
        yield session_id
    finally:
        _session_id.reset(token)
        try:
            _session_domain.reset(domain_token)
        except (ValueError, LookupError) as exc:
            logger.debug("session domain not reset: %s", exc)


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
    payload: Optional[str] = None,
    payload_ref: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    domain: Optional[str] = None,
    model: str = "",
) -> None:
    """Record one context read against the active (or given) session.

    ``source`` is the store family - ``mcp``, ``kg``, ``retriever``.
    ``operation`` is what was called, e.g. ``jira/get_issue``.

    ``session_id`` should be passed explicitly by any caller that may cross a
    thread boundary before reaching here; it falls back to the ContextVar.

    ``payload`` is the retrieved text. It is offered to the configured tier-two
    store, which is disabled unless ``KEEL_PAYLOAD_STORE`` selects a backend —
    so passing it is safe everywhere and changes nothing until an operator opts
    in. The row records the resulting ref, or why there is none: a payload that
    was dropped for size should be visibly dropped, not indistinguishable from
    one that was never offered. Callers with a ref already in hand keep passing
    ``payload_ref``.

    It is also what the token count is taken from — and only what. A caller that
    passes ``size_bytes`` without ``payload`` gets no token count rather than a
    count inferred from the byte total: bytes-to-tokens is a second estimate
    stacked on the first, and the row would claim a precision nothing supports.
    ``payload`` never has to be *stored* for this; the text is counted in memory
    and handed to a store that is off by default.

    This function never raises. Telemetry must not be able to break retrieval:
    a failure to record is logged at debug and swallowed.
    """
    try:
        # record_activity, not record_action: the latter is a convenience
        # wrapper that drops duration_ms, and retrieval latency is worth a real
        # indexed column rather than a field buried in the details JSON.
        from agentic_cli.tracker import record_activity

        details: Dict[str, Any] = {"bytes": int(size_bytes)}
        # Counted from the text itself, in memory, whether or not it is stored.
        counted = None
        if payload:
            from agentic_cli import tokens as token_counter

            counted = token_counter.count(payload, model or "")
        digest = digest_args(arguments)
        if digest:
            details["args_digest"] = digest
        if payload is not None and not payload_ref:
            from agentic_cli import payload_store

            details.update(payload_store.get_store().put(
                payload,
                session_id=session_id if session_id is not None else current_session_id(),
                source=source, operation=operation, entity_id=entity_id,
            ).details())
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
            domain=domain,          # None falls back to the bound session domain
            size_bytes=int(size_bytes),
            tokens=counted.tokens if counted else None,
            token_basis=counted.basis if counted else None,
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


def details_of(row: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a row's details column, which may arrive as JSON text or a dict."""
    details = row.get("details") or {}
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (ValueError, TypeError):
            return {}
    return details if isinstance(details, dict) else {}


def list_sessions(limit: int = 25, scan: int = 2000) -> list[Dict[str, Any]]:
    """Recent sessions that read context, newest first.

    Scans the most recent ``scan`` context rows and groups them by session, so
    a caller can offer "which run do you want to inspect?" without knowing a
    correlation id up front. ``scan`` bounds the work: sessions whose reads all
    fall outside that window will not appear.
    """
    try:
        from agentic_cli.tracker import get_activity

        rows = get_activity(entity_type="context", limit=scan)
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not list sessions: %s", exc)
        return []

    sessions: Dict[str, Dict[str, Any]] = {}
    for r in rows:                      # newest first from the tracker
        sid = r.get("correlation_id")
        if not sid:
            continue                    # unattributed reads are not a session
        s = sessions.setdefault(sid, {
            "session_id": sid,
            "reads": 0,
            "bytes": 0,
            "errors": 0,
            "sources": set(),
            "latest": r.get("timestamp"),
            "earliest": r.get("timestamp"),
        })
        s["reads"] += 1
        s["bytes"] += int(details_of(r).get("bytes") or 0)
        if r.get("status") == "error":
            s["errors"] += 1
        if r.get("command"):
            s["sources"].add(r["command"])
        ts = r.get("timestamp")
        if ts:
            if not s["earliest"] or ts < s["earliest"]:
                s["earliest"] = ts
            if not s["latest"] or ts > s["latest"]:
                s["latest"] = ts

    out = [{**s, "sources": sorted(s["sources"])} for s in sessions.values()]
    out.sort(key=lambda s: s.get("latest") or "", reverse=True)
    return out[:limit]


def session_engine(session_id: str, limit: int = 500) -> Dict[str, str]:
    """Which engine and model ran a session, from its own audit row.

    Returns ``engine``, ``model_requested`` and ``model_served``, each empty
    when unknown. The two model fields are kept apart on purpose: a request can
    be ignored, substituted, or fall back mid-session, so a comparison keyed on
    the request rather than the answer measures the wrong thing.

    An empty ``model_served`` is an honest answer, not a gap to paper over — a
    hosted engine that chooses server-side may never report back, and the local
    engine's ``create_session`` only prepares a context bundle without running
    a model at all.
    """
    return _engine_from_chain(session_chain(session_id, limit=limit))


def _engine_from_chain(rows: list) -> Dict[str, str]:
    """Pull engine/model out of an already-fetched chain, so callers that have
    one do not pay for a second read."""
    out = {"engine": "", "model_requested": "", "model_served": ""}
    for row in rows:
        if row.get("entity_type") != "session":
            continue
        details = details_of(row)
        for key in out:
            if not out[key] and details.get(key):
                out[key] = str(details[key])
    return out


def session_summary(session_id: str, limit: int = 500) -> Dict[str, Any]:
    """Roll up a session's context ledger: totals, and a per-source breakdown.

    This is what the ledger view and the context-budget readout are built from.
    """
    chain = session_chain(session_id, limit=limit)
    rows = [r for r in chain if r.get("entity_type") == "context"]
    by_source: Dict[str, Dict[str, int]] = {}
    total_bytes = 0
    errors = 0
    for r in rows:
        src = r.get("command") or "unknown"
        size = int(details_of(r).get("bytes") or 0)
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
        **_engine_from_chain(chain),
    }
