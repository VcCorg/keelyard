"""Watchers — react to external notifications and fire A2A agent workflows.

Three primitives, mirroring the execution / code_assist registry pattern the
platform already uses:

  * ``Trigger`` — pluggable source that emits typed events (e.g.
    ``bitbucket.pr.review_requested``, ``jira.issue.created``, ...). Adapters
    live in ``agentic_cli.watchers.triggers`` and register themselves on
    import.
  * ``WatcherSpec`` — a YAML-declared binding of one trigger + a filter + a
    handler agent. Users author them at ``~/.keel/watchers/*.yaml`` (or via
    the dashboard UI, which writes the same files).
  * ``WatcherRuntime`` — an asyncio scheduler hosted in the backend sidecar
    that polls every active watcher, dedupes events against a persisted
    cursor, and dispatches matches into the existing execution seam
    (``execution.registry.create_session``), so build governance + audit
    already apply for free.

Phase 1 ships polling only (no webhooks) and one adapter
(``bitbucket.pr.review_requested``). See ``docs/WATCHERS.md`` for the design.
"""

from .registry import get_trigger, list_triggers, register_trigger
from .types import (
    HandlerSpec,
    TriggerEvent,
    TriggerInfo,
    TriggerProtocol,
    WatcherSpec,
    WatcherState,
)

__all__ = [
    "HandlerSpec",
    "TriggerEvent",
    "TriggerInfo",
    "TriggerProtocol",
    "WatcherSpec",
    "WatcherState",
    "get_trigger",
    "list_triggers",
    "register_trigger",
]

# Preload built-in adapters so callers see them via list_triggers() without
# an explicit import.
from .triggers import bitbucket_pr  # noqa: F401,E402
from .triggers import drift  # noqa: F401,E402
