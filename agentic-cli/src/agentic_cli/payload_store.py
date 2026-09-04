"""Tier two of the context ledger — the retrieved text, when it is wanted.

Tier one records *facts about* a retrieval and keeps nothing readable. Ragas
needs the text itself: ``EvalRow.retrieved_contexts`` is a list of strings, and
no digest can tell you whether an answer followed from what was retrieved. This
is the store ``payload_ref`` was always meant to hang from.

**It is off by default, and that is the point.** Writing document bodies to disk
is a decision about retention and disclosure that belongs to whoever runs Keel,
not to whoever imports this module. ``KEEL_PAYLOAD_STORE`` selects a backend;
unset means nothing is stored and the ledger behaves exactly as it does today.

Two backends, because two consumers want opposite things:

- ``memory`` — process-local, never touches disk. Enough for run-and-score in
  one flow (the ablation playground), and provably free of anything at rest.
- ``sqlite`` — a **separate** database file. Not the tracker: that file is the
  audit trail, it is safe to copy into a support bundle today, and adding
  document bodies would silently change that without anything in the code
  saying so.

Three rules the implementation enforces rather than documents:

**Drop, never truncate.** A chunk cut mid-sentence makes Faithfulness score the
agent against a mutilated version of what it saw — a wrong number, not a missing
one. Over the cap, nothing is stored and the ledger records why.

**Masking is span-preserving and reported.** Identifiers are replaced with typed
markers rather than removed, and the row records which kinds were changed, so a
score computed over altered text can be identified as such later. Debugging a
"hallucination" that is really a redaction artifact, with nothing in the data to
say so, is the failure this avoids.

**Expiry actually erases.** ``DELETE`` in SQLite frees pages for reuse without
shrinking or zeroing the file, so expired bodies stay recoverable until a
``VACUUM``. ``secure_delete`` is enabled and the sweep vacuums, because a TTL
that leaves the data on disk is not a retention policy.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Protocol

from agentic_cli.onboarding import redaction

logger = logging.getLogger(__name__)

#: Which backend to use: unset/"off" | "memory" | "sqlite".
ENV_BACKEND = "KEEL_PAYLOAD_STORE"
#: Largest single payload kept, in bytes. Bigger ones are dropped, not cut.
ENV_MAX_BYTES = "KEEL_PAYLOAD_MAX_BYTES"
#: Days a stored payload survives. 0 disables expiry (discouraged).
ENV_TTL_DAYS = "KEEL_PAYLOAD_TTL_DAYS"

DEFAULT_MAX_BYTES = 64 * 1024
DEFAULT_TTL_DAYS = 7

#: Rows deleted in one sweep before the file is vacuumed.
_VACUUM_AFTER = 50


@dataclass
class Payload:
    """One stored retrieval body."""

    id: str
    text: str
    bytes: int = 0
    masked: tuple[str, ...] = ()
    session_id: str = ""
    source: str = ""
    operation: str = ""
    entity_id: str = ""
    stored_at: str = ""
    expires_at: str = ""

    @property
    def lossy(self) -> bool:
        """True when this is not verbatim what the agent saw."""
        return bool(self.masked)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "bytes": self.bytes, "masked": list(self.masked),
            "lossy": self.lossy, "session_id": self.session_id,
            "source": self.source, "operation": self.operation,
            "entity_id": self.entity_id, "stored_at": self.stored_at,
            "expires_at": self.expires_at,
        }


@dataclass
class Outcome:
    """What happened to a payload offered for storage.

    ``ref`` is None whenever nothing was stored, and ``reason`` says why in
    words a ledger row can carry — an omitted payload should be visibly
    omitted, never indistinguishable from one that was never offered.
    """

    ref: Optional[str] = None
    reason: str = ""
    masked: tuple[str, ...] = ()

    @property
    def stored(self) -> bool:
        return self.ref is not None

    def details(self) -> dict:
        """Fields to fold into the ledger row's details column."""
        out: dict = {}
        if self.ref:
            out["payload_ref"] = self.ref
        if self.reason:
            out["payload"] = self.reason
        if self.masked:
            out["payload_masked"] = list(self.masked)
        return out


class PayloadStore(Protocol):
    """The interface both backends implement."""

    scheme: str

    def put(self, text: str, **meta) -> Outcome: ...
    def get(self, ref: str) -> Optional[Payload]: ...
    def delete(self, ref: str) -> bool: ...
    def sweep(self) -> int: ...


# ── shared policy ───────────────────────────────────────────────────────────

def max_bytes() -> int:
    try:
        return max(0, int(os.environ.get(ENV_MAX_BYTES, DEFAULT_MAX_BYTES)))
    except ValueError:
        return DEFAULT_MAX_BYTES


def ttl_days() -> int:
    try:
        return max(0, int(os.environ.get(ENV_TTL_DAYS, DEFAULT_TTL_DAYS)))
    except ValueError:
        return DEFAULT_TTL_DAYS


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry() -> str:
    days = ttl_days()
    return (_now() + timedelta(days=days)).isoformat() if days else ""


def prepare(text: str) -> tuple[Optional[str], tuple[str, ...], str]:
    """Apply the cap and the mask. Returns ``(text|None, masked_kinds, reason)``.

    Masking runs *before* the cap so the cap measures what would actually be
    written. A masking failure stores nothing: unmasked text is exactly what
    this store exists to avoid putting on disk.
    """
    if not text or not text.strip():
        return None, (), "empty"

    try:
        result = redaction.mask(text)
    except Exception as exc:  # noqa: BLE001 - see docstring
        logger.debug("payload masking failed: %s", exc)
        return None, (), "omitted (masking failed)"

    size = len(result.text.encode("utf-8"))
    limit = max_bytes()
    if limit and size > limit:
        return None, result.masked, f"omitted (size {size} > {limit})"
    return result.text, result.masked, ""


# ── backends ────────────────────────────────────────────────────────────────

class NullStore:
    """Stores nothing. The default, so enabling tier two is a deliberate act."""

    scheme = "null"

    def put(self, text: str, **meta) -> Outcome:
        return Outcome(reason="not stored (payload store disabled)")

    def get(self, ref: str) -> Optional[Payload]:
        return None

    def delete(self, ref: str) -> bool:
        return False

    def sweep(self) -> int:
        return 0


class MemoryStore:
    """Process-local. Dies with the process, and never reaches disk.

    Serves the flow where retrieval and scoring happen in one run. It cannot
    serve ``keel eval`` over an earlier session — that is a different process,
    and this store has no way to be honest about that other than returning
    nothing.
    """

    scheme = "mem"

    def __init__(self) -> None:
        self._items: dict[str, Payload] = {}
        self._lock = threading.Lock()

    def put(self, text: str, **meta) -> Outcome:
        body, masked, reason = prepare(text)
        if body is None:
            return Outcome(reason=reason, masked=masked)
        pid = uuid.uuid4().hex[:16]
        payload = Payload(
            id=pid, text=body, bytes=len(body.encode("utf-8")), masked=masked,
            session_id=str(meta.get("session_id") or ""),
            source=str(meta.get("source") or ""),
            operation=str(meta.get("operation") or ""),
            entity_id=str(meta.get("entity_id") or ""),
            stored_at=_now().isoformat(), expires_at=_expiry(),
        )
        with self._lock:
            self._items[pid] = payload
        return Outcome(ref=f"{self.scheme}:{pid}", masked=masked)

    def get(self, ref: str) -> Optional[Payload]:
        with self._lock:
            return self._items.get(_ref_id(ref, self.scheme) or "")

    def delete(self, ref: str) -> bool:
        with self._lock:
            return self._items.pop(_ref_id(ref, self.scheme) or "", None) is not None

    def sweep(self) -> int:
        now = _now().isoformat()
        with self._lock:
            expired = [k for k, v in self._items.items() if v.expires_at and v.expires_at < now]
            for key in expired:
                del self._items[key]
        return len(expired)

    def session(self, session_id: str) -> list[Payload]:
        with self._lock:
            return [p for p in self._items.values() if p.session_id == session_id]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS payloads (
    id          TEXT PRIMARY KEY,
    session_id  TEXT,
    source      TEXT,
    operation   TEXT,
    entity_id   TEXT,
    text        TEXT NOT NULL,
    bytes       INTEGER NOT NULL,
    masked      TEXT,               -- comma-separated kinds; empty = verbatim
    stored_at   TEXT NOT NULL,
    expires_at  TEXT                -- empty = never expires
);
CREATE INDEX IF NOT EXISTS idx_payloads_session ON payloads(session_id);
CREATE INDEX IF NOT EXISTS idx_payloads_expires ON payloads(expires_at);
"""


class SqliteStore:
    """A separate database file under the tracker's directory.

    Separate on purpose: ``tracker.db`` is the audit trail and is safe to hand
    to someone debugging an issue. A file holding retrieved document bodies is
    not, and nothing in the code would flag the change if the two shared a file.
    Keeping them apart also means expiry can, in the worst case, delete the
    whole store without touching the audit history.
    """

    scheme = "sqlite"
    FILENAME = "payloads.db"

    def __init__(self, path: Optional[Path] = None) -> None:
        from agentic_cli.tracker import DB_DIR

        self.path = Path(path) if path else Path(DB_DIR) / self.FILENAME
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._since_vacuum = 0
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        # Without this, DELETE frees pages without zeroing them and expired
        # bodies stay readable in the file until a VACUUM.
        conn.execute("PRAGMA secure_delete = ON")
        return conn

    def put(self, text: str, **meta) -> Outcome:
        body, masked, reason = prepare(text)
        if body is None:
            return Outcome(reason=reason, masked=masked)
        pid = uuid.uuid4().hex[:16]
        try:
            with self._lock, closing(self._connect()) as conn:
                conn.execute(
                    """INSERT INTO payloads
                       (id, session_id, source, operation, entity_id, text,
                        bytes, masked, stored_at, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (pid, str(meta.get("session_id") or ""),
                     str(meta.get("source") or ""), str(meta.get("operation") or ""),
                     str(meta.get("entity_id") or ""), body,
                     len(body.encode("utf-8")), ",".join(masked),
                     _now().isoformat(), _expiry()),
                )
                conn.commit()
        except sqlite3.Error as exc:
            logger.debug("payload not stored: %s", exc)
            return Outcome(reason="omitted (store unavailable)", masked=masked)
        return Outcome(ref=f"{self.scheme}:{pid}", masked=masked)

    def get(self, ref: str) -> Optional[Payload]:
        pid = _ref_id(ref, self.scheme)
        if not pid:
            return None
        try:
            with closing(self._connect()) as conn:
                row = conn.execute("SELECT * FROM payloads WHERE id = ?", (pid,)).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        # An expired row that the sweep has not reached yet is already gone as
        # far as any reader is concerned.
        if row["expires_at"] and row["expires_at"] < _now().isoformat():
            return None
        return _row_to_payload(row)

    def session(self, session_id: str) -> list[Payload]:
        """Every live payload for one session, oldest first — the eval feed."""
        try:
            with closing(self._connect()) as conn:
                rows = conn.execute(
                    "SELECT * FROM payloads WHERE session_id = ? ORDER BY stored_at",
                    (session_id,)).fetchall()
        except sqlite3.Error:
            return []
        now = _now().isoformat()
        return [_row_to_payload(r) for r in rows
                if not (r["expires_at"] and r["expires_at"] < now)]

    def delete(self, ref: str) -> bool:
        pid = _ref_id(ref, self.scheme)
        if not pid:
            return False
        try:
            with self._lock, closing(self._connect()) as conn:
                cur = conn.execute("DELETE FROM payloads WHERE id = ?", (pid,))
                conn.commit()
                return cur.rowcount > 0
        except sqlite3.Error:
            return False

    def sweep(self) -> int:
        """Delete expired payloads, vacuuming once enough have gone."""
        now = _now().isoformat()
        try:
            with self._lock, closing(self._connect()) as conn:
                cur = conn.execute(
                    "DELETE FROM payloads WHERE expires_at != '' AND expires_at < ?",
                    (now,))
                removed = cur.rowcount or 0
                conn.commit()
                self._since_vacuum += removed
                if self._since_vacuum >= _VACUUM_AFTER:
                    conn.execute("VACUUM")
                    self._since_vacuum = 0
        except sqlite3.Error as exc:
            logger.debug("payload sweep failed: %s", exc)
            return 0
        return removed

    def purge(self) -> None:
        """Delete everything and reclaim the space. The break-glass option."""
        with self._lock, closing(self._connect()) as conn:
            conn.execute("DELETE FROM payloads")
            conn.commit()
            conn.execute("VACUUM")
        self._since_vacuum = 0


def _row_to_payload(row: sqlite3.Row) -> Payload:
    masked = tuple(k for k in (row["masked"] or "").split(",") if k)
    return Payload(
        id=row["id"], text=row["text"], bytes=row["bytes"], masked=masked,
        session_id=row["session_id"] or "", source=row["source"] or "",
        operation=row["operation"] or "", entity_id=row["entity_id"] or "",
        stored_at=row["stored_at"] or "", expires_at=row["expires_at"] or "",
    )


def _ref_id(ref: str, scheme: str) -> Optional[str]:
    prefix, _, pid = (ref or "").partition(":")
    return pid if prefix == scheme and pid else None


# ── selection ───────────────────────────────────────────────────────────────

_store: Optional[PayloadStore] = None
_store_key: Optional[str] = None


def backend_name() -> str:
    return (os.environ.get(ENV_BACKEND) or "off").strip().lower()


def get_store() -> PayloadStore:
    """The configured store. ``NullStore`` unless a backend is selected."""
    global _store, _store_key

    name = backend_name()
    if _store is not None and _store_key == name:
        return _store

    if name in ("memory", "mem"):
        _store = MemoryStore()
    elif name in ("sqlite", "db"):
        try:
            _store = SqliteStore()
        except Exception as exc:  # noqa: BLE001 - never break a run over telemetry
            logger.warning("payload store unavailable, continuing without: %s", exc)
            _store = NullStore()
    else:
        _store = NullStore()
    _store_key = name
    return _store


def reset_store() -> None:
    """Drop the cached store. For tests and for reacting to a config change."""
    global _store, _store_key
    _store, _store_key = None, None


def read(ref: str) -> Optional[Payload]:
    """Resolve a ``payload_ref`` through the configured store."""
    return get_store().get(ref) if ref else None


__all__ = [
    "ENV_BACKEND", "ENV_MAX_BYTES", "ENV_TTL_DAYS", "DEFAULT_MAX_BYTES",
    "DEFAULT_TTL_DAYS", "Payload", "Outcome", "PayloadStore", "NullStore",
    "MemoryStore", "SqliteStore", "prepare", "max_bytes", "ttl_days",
    "backend_name", "get_store", "reset_store", "read",
]
