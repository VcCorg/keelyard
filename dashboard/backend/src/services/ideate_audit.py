"""Ideate audit — records mutating actions to the central audit trail.

Thin wrapper over agentic_cli.tracker.record_action so every Jira issue created
from Ideate is traceable: who, what, target, status, correlation id.
"""
from __future__ import annotations

from typing import Optional

try:
    from agentic_cli.tracker import record_action as _tracker_record_action
    from agentic_cli.tracker import new_correlation_id as _new_correlation_id
except Exception:  # noqa: BLE001 - never break the request path
    def _tracker_record_action(feature, action, **kwargs):  # type: ignore
        return None

    def _new_correlation_id() -> str:  # type: ignore
        import uuid
        return uuid.uuid4().hex[:16]


def new_correlation_id() -> str:
    """Mint a correlation id to link a push batch's audit rows."""
    return _new_correlation_id()


def record_jira_create(*, project_key: str, key: str, url: str, ok: bool, title: str,
                       error: Optional[str] = None, actor: Optional[str] = None,
                       correlation_id: Optional[str] = None) -> None:
    """Audit a single Jira issue creation (success or failure)."""
    _tracker_record_action(
        "ideate", "jira_create",
        status="success" if ok else "error",
        entity_type="jira_issue", entity_id=key or project_key,
        source="dashboard", actor=actor, correlation_id=correlation_id,
        details={"title": title, "project": project_key, "url": url, "error": error})
