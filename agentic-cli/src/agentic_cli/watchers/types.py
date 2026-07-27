"""Types shared across the watcher runtime, adapters, and API layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Protocol, runtime_checkable


@dataclass
class TriggerEvent:
    """One notification a trigger emits.

    ``event_id`` must be stable for the same underlying record (e.g. PR id +
    review-request seq number) so the runtime can dedupe on catch-up. The
    ``ts`` is the source timestamp (created_at, updated_at, etc.), used both
    for the catch-up window and for age-based filtering.
    """

    #: Trigger type this event came from (matches TriggerInfo.name).
    type: str
    #: Stable identifier — used for the delivered-event dedup index.
    event_id: str
    #: Source timestamp (UTC).
    ts: datetime
    #: Provider-native payload. Watcher filters and handler input templates
    #: address fields here as ``$event.<path>`` (dotted-path resolution).
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "event_id": self.event_id,
            "ts": self.ts.astimezone(timezone.utc).isoformat(),
            "data": self.data,
        }


@dataclass
class TriggerInfo:
    """Descriptor a trigger publishes to callers.

    The ``filter_schema`` drives the create-watcher form: the dashboard
    renders one input per entry, and the runtime uses the same shape to
    validate filter values before persisting.
    """

    #: Stable id used by watcher specs (e.g. ``bitbucket.pr.review_requested``).
    name: str
    #: Short human label for the UI dropdown.
    label: str
    #: One-sentence description shown under the label.
    description: str = ""
    #: The MCP server this adapter reads from (informational; keeps the UI
    #: honest about what needs to be configured for this trigger).
    source_mcp: str = ""
    #: Per-field filter schema: ``{field: {type, label, required, help}}``.
    #: Types: ``string``, ``int``, ``bool``, ``regex``, ``duration``.
    filter_schema: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Default poll cadence in seconds. UIs may override per watcher.
    default_poll_seconds: int = 300


@runtime_checkable
class TriggerProtocol(Protocol):
    """The interface every trigger adapter implements.

    Deliberately narrow — the runtime does dedup, cursor storage, dispatch,
    and governance. Adapters only need to *fetch and yield events*.
    """

    info: TriggerInfo

    async def fetch(
        self,
        filter: dict[str, Any],
        since: datetime,
        limit: int = 200,
    ) -> list[TriggerEvent]:
        """Return events for this trigger with ts >= ``since``.

        Adapters MUST:
        - honor ``since`` (used both for steady-state polling and the 3-day
          catch-up scan on startup).
        - respect ``limit`` (runtime pages through if more exist).
        - not raise on transient failure — return ``[]`` and log; the runtime
          will retry on the next poll.
        """
        ...


@dataclass
class HandlerSpec:
    """What to do when a filtered event arrives.

    Phase 1 supports a single agent handler. ``chain`` accepts a list of
    agent names — the runtime will call the first for now; multi-step
    chain execution ships in Phase 2. Storing the chain field today lets
    users author it without a subsequent spec migration.
    """

    #: The agent this event fires. Must exist in the agent registry.
    agent: str
    #: Optional list for multi-step A2A chains (Phase 2 will execute the
    #: full chain; Phase 1 executes only agent + logs chain in audit).
    chain: list[str] = field(default_factory=list)
    #: Extra input mapped into the handler's prompt / context.
    #: Values may reference event fields as ``$event.<path>``.
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class WatcherSpec:
    """A single watcher declaration — one YAML file at ``~/.keel/watchers/<name>.yaml``."""

    #: Unique watcher name (matches file stem).
    name: str
    #: Trigger type (e.g. ``bitbucket.pr.review_requested``).
    trigger_type: str
    #: Handler agent + optional chain.
    handler: HandlerSpec
    #: Filter values keyed by ``TriggerInfo.filter_schema`` field name.
    filter: dict[str, Any] = field(default_factory=dict)
    #: Domain this watcher belongs to (for KG context + governance scope).
    domain: str = ""
    #: True when the watcher is polled; false pauses it.
    enabled: bool = True
    #: Poll cadence override (0 = use trigger.default_poll_seconds).
    poll_seconds: int = 0
    #: Free-form description shown in the list UI.
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trigger_type": self.trigger_type,
            "handler": {
                "agent": self.handler.agent,
                "chain": list(self.handler.chain),
                "input": dict(self.handler.input),
            },
            "filter": dict(self.filter),
            "domain": self.domain,
            "enabled": self.enabled,
            "poll_seconds": self.poll_seconds,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WatcherSpec":
        handler_raw = raw.get("handler", {}) or {}
        return cls(
            name=str(raw.get("name", "")),
            trigger_type=str(raw.get("trigger_type", "")),
            handler=HandlerSpec(
                agent=str(handler_raw.get("agent", "")),
                chain=[str(c) for c in (handler_raw.get("chain") or [])],
                input=dict(handler_raw.get("input") or {}),
            ),
            filter=dict(raw.get("filter") or {}),
            domain=str(raw.get("domain", "")),
            enabled=bool(raw.get("enabled", True)),
            poll_seconds=int(raw.get("poll_seconds", 0) or 0),
            description=str(raw.get("description", "")),
        )


@dataclass
class WatcherState:
    """Per-watcher persisted state kept in ``~/.keel/watchers/state.json``.

    Held separately from the YAML spec so state can be rewritten frequently
    without touching the user-authored file (git-friendly, audit-friendly).
    """

    #: Watermark of the most recent event we've SEEN. Next poll queries
    #: ``since=cursor``. On first run this is ``None`` and the runtime uses
    #: ``now - catch_up_window`` (3 days) as the effective ``since``.
    cursor: Optional[datetime] = None
    #: Delivered event ids (bounded LRU). Prevents re-dispatching the same
    #: event when a source's cursor is coarse (e.g. day-precision).
    delivered: list[str] = field(default_factory=list)
    #: Last poll attempt timestamp — informational for the UI.
    last_polled: Optional[datetime] = None
    #: Last successful dispatch timestamp — informational for the UI.
    last_fired: Optional[datetime] = None
    #: Last error message from the trigger, if any.
    last_error: str = ""

    def remember(self, event_id: str, max_len: int = 500) -> None:
        """Record ``event_id`` in the delivered LRU (drops oldest first)."""
        if event_id in self.delivered:
            return
        self.delivered.append(event_id)
        if len(self.delivered) > max_len:
            # Drop oldest first (front of list).
            del self.delivered[: len(self.delivered) - max_len]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cursor": self.cursor.astimezone(timezone.utc).isoformat() if self.cursor else None,
            "delivered": list(self.delivered),
            "last_polled": self.last_polled.astimezone(timezone.utc).isoformat() if self.last_polled else None,
            "last_fired": self.last_fired.astimezone(timezone.utc).isoformat() if self.last_fired else None,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WatcherState":
        return cls(
            cursor=_parse_dt(raw.get("cursor")),
            delivered=[str(x) for x in (raw.get("delivered") or [])],
            last_polled=_parse_dt(raw.get("last_polled")),
            last_fired=_parse_dt(raw.get("last_fired")),
            last_error=str(raw.get("last_error", "")),
        )


def _parse_dt(value: Any) -> Optional[datetime]:
    """Coerce a stored ISO 8601 string to a tz-aware datetime; None on empty."""
    if value is None or value == "":
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# Utility used by the handler input template + filter resolution.
def resolve_event_path(event: TriggerEvent, dotted_path: str) -> Any:
    """Look up ``dotted_path`` on the event (e.g. ``pr.url`` → event.data['pr']['url']).

    Special paths:
      * ``id`` / ``event_id`` → the stable event id
      * ``ts`` → ISO 8601 timestamp string
      * anything else → walks ``event.data`` by ``.``-separated keys
    Missing keys return None (never raise) so a filter typo doesn't crash a
    running watcher; the UI can validate paths before saving.
    """
    if dotted_path in ("id", "event_id"):
        return event.event_id
    if dotted_path == "ts":
        return event.ts.astimezone(timezone.utc).isoformat()
    node: Any = event.data
    for part in dotted_path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node
