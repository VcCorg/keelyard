"""Reusable Devin integration package.

A self-contained, domain-agnostic client for the Devin v1 API (Knowledge +
Sessions), plus configuration and local session tracking. The OKF-specific
"bundle -> knowledge" rendering lives in ``agentic_cli.kg.okf.devin`` and builds
on top of this package.

Public API::

    from agentic_cli.devin import (
        DevinClient, DevinError, get_client,
        resolve_api_key, resolve_verify, DevinConfig,
        SessionSpec, SessionResult, create_session, get_session,
        send_message, list_sessions, poll_session,
        list_entries, delete_entries, update_entry, move_entry,
    )
"""
from __future__ import annotations

from agentic_cli.devin.client import DevinClient, get_client
from agentic_cli.devin.config import (
    DEVIN_API_BASE,
    DEVIN_API_KEY_ENV,
    DevinConfig,
    has_api_key,
    resolve_api_key,
    resolve_verify,
)
from agentic_cli.devin.errors import DevinError
from agentic_cli.devin.knowledge import (
    delete_entries,
    list_entries,
    move_entry,
    update_entry,
)
from agentic_cli.devin.sessions import (
    SessionResult,
    SessionSpec,
    create_session,
    get_session,
    list_local,
    list_sessions,
    poll_session,
    send_message,
)

__all__ = [
    "DevinClient",
    "DevinError",
    "DevinConfig",
    "get_client",
    "resolve_api_key",
    "resolve_verify",
    "has_api_key",
    "DEVIN_API_BASE",
    "DEVIN_API_KEY_ENV",
    "SessionSpec",
    "SessionResult",
    "create_session",
    "get_session",
    "send_message",
    "list_sessions",
    "list_local",
    "poll_session",
    "list_entries",
    "delete_entries",
    "update_entry",
    "move_entry",
]
