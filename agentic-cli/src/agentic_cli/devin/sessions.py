"""Devin Sessions orchestration + local tracking.

Triggers and follows remote Devin sessions via the v1 Sessions API. A local
store (``~/.dva/devin/sessions.json``) records every session the CLI starts so
``sessions list`` works offline and re-runs can be made idempotent on a prompt
hash + tags.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from agentic_cli.devin.client import get_client
from agentic_cli.devin.config import DEVIN_API_BASE, DEFAULT_MAX_ACU

# Global session store (cross-domain; survives between commands).
STORE_DIR = Path.home() / ".dva" / "devin"
STORE_FILE = STORE_DIR / "sessions.json"

# Terminal session states (confirm exact set against docs.devin.ai per plan).
TERMINAL_STATES = {"finished", "blocked", "expired", "stopped", "suspended"}


# ── Spec / result models ─────────────────────────────────────────────────────

@dataclass
class SessionSpec:
    """Everything needed to create a Devin session."""
    prompt: str
    title: str = ""
    snapshot_id: str | None = None
    playbook_id: str | None = None
    knowledge_ids: list[str] = field(default_factory=list)
    secret_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    idempotent: bool = False
    max_acu_limit: int | None = None
    unlisted: bool = False
    # provenance (not sent to the API; stored locally)
    domain: str = ""
    jira: str = ""

    def prompt_hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.prompt.encode("utf-8"))
        h.update(b"\x00")
        h.update(",".join(sorted(self.tags)).encode("utf-8"))
        return h.hexdigest()[:16]

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": self.prompt}
        if self.title:
            payload["title"] = self.title
        if self.snapshot_id:
            payload["snapshot_id"] = self.snapshot_id
        if self.playbook_id:
            payload["playbook_id"] = self.playbook_id
        if self.knowledge_ids:
            payload["knowledge_ids"] = self.knowledge_ids
        if self.secret_ids:
            payload["secret_ids"] = self.secret_ids
        if self.tags:
            payload["tags"] = self.tags
        if self.idempotent:
            payload["idempotent"] = True
        if self.max_acu_limit is not None:
            payload["max_acu_limit"] = self.max_acu_limit
        if self.unlisted:
            payload["unlisted"] = True
        return payload


@dataclass
class SessionResult:
    dry_run: bool = False
    session_id: str | None = None
    url: str | None = None
    is_new: bool = True
    status: str | None = None
    structured_output: Any = None
    payload: dict[str, Any] = field(default_factory=dict)
    reused_local: bool = False  # matched an existing live local session


# ── Local store ──────────────────────────────────────────────────────────────

def load_store() -> dict[str, Any]:
    if STORE_FILE.exists():
        try:
            return json.loads(STORE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"sessions": {}}
    return {"sessions": {}}


def save_store(store: dict[str, Any]) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record(spec: SessionSpec, session_id: str, url: str | None, status: str | None) -> None:
    store = load_store()
    store.setdefault("sessions", {})[session_id] = {
        "session_id": session_id,
        "url": url,
        "title": spec.title,
        "domain": spec.domain,
        "jira": spec.jira,
        "tags": spec.tags,
        "prompt_hash": spec.prompt_hash(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_status": status,
    }
    save_store(store)


def update_status(session_id: str, status: str | None) -> None:
    store = load_store()
    rec = store.get("sessions", {}).get(session_id)
    if rec:
        rec["last_status"] = status
        rec["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_store(store)


def find_live_local(spec: SessionSpec) -> Optional[dict[str, Any]]:
    """Return a tracked, non-terminal session matching this spec's prompt hash."""
    ph = spec.prompt_hash()
    for rec in load_store().get("sessions", {}).values():
        if rec.get("prompt_hash") == ph and (rec.get("last_status") not in TERMINAL_STATES):
            return rec
    return None


def list_local() -> list[dict[str, Any]]:
    return sorted(load_store().get("sessions", {}).values(),
                  key=lambda r: r.get("created_at", ""), reverse=True)


# ── Orchestration ────────────────────────────────────────────────────────────

def _extract_status(data: dict[str, Any]) -> str | None:
    return data.get("status_enum") or data.get("status")


def create_session(spec: SessionSpec, api_key: str | None = None, dry_run: bool = False,
                   base_url: str = DEVIN_API_BASE) -> SessionResult:
    """Create (or reuse) a Devin session from ``spec``.

    When ``spec.idempotent`` is set, an existing tracked live session with the
    same prompt hash is reused instead of spawning a new one.
    """
    if spec.max_acu_limit is None:
        spec.max_acu_limit = DEFAULT_MAX_ACU

    if dry_run:
        return SessionResult(dry_run=True, payload=spec.to_payload())

    if spec.idempotent:
        existing = find_live_local(spec)
        if existing:
            return SessionResult(
                session_id=existing.get("session_id"), url=existing.get("url"),
                is_new=False, status=existing.get("last_status"),
                payload=spec.to_payload(), reused_local=True,
            )

    with get_client(api_key, base_url=base_url) as client:
        resp = client.create_session(spec.to_payload())
    session_id = resp.get("session_id") or resp.get("id")
    url = resp.get("url")
    status = _extract_status(resp)
    if session_id:
        _record(spec, session_id, url, status)
    return SessionResult(
        session_id=session_id, url=url,
        is_new=bool(resp.get("is_new_session", True)),
        status=status, payload=spec.to_payload(),
    )


def get_session(session_id: str, api_key: str | None = None,
                base_url: str = DEVIN_API_BASE) -> SessionResult:
    with get_client(api_key, base_url=base_url) as client:
        data = client.get_session(session_id)
    status = _extract_status(data)
    update_status(session_id, status)
    return SessionResult(
        session_id=session_id, url=data.get("url"),
        status=status, structured_output=data.get("structured_output"),
        payload=data,
    )


def send_message(session_id: str, message: str, api_key: str | None = None,
                 base_url: str = DEVIN_API_BASE) -> dict[str, Any]:
    with get_client(api_key, base_url=base_url) as client:
        return client.send_message(session_id, message)


def list_sessions(api_key: str | None = None, base_url: str = DEVIN_API_BASE,
                  params: dict[str, Any] | None = None) -> dict[str, Any]:
    with get_client(api_key, base_url=base_url) as client:
        return client.list_sessions(params)


def poll_session(session_id: str, api_key: str | None = None, base_url: str = DEVIN_API_BASE,
                 interval: float = 8.0, timeout: float = 1800.0,
                 on_update: Callable[[str | None], None] | None = None) -> SessionResult:
    """Poll until the session reaches a terminal state or ``timeout`` elapses."""
    deadline = time.monotonic() + timeout
    last: SessionResult = SessionResult(session_id=session_id)
    while True:
        last = get_session(session_id, api_key=api_key, base_url=base_url)
        if on_update:
            on_update(last.status)
        if (last.status or "") in TERMINAL_STATES or time.monotonic() >= deadline:
            return last
        time.sleep(interval)
