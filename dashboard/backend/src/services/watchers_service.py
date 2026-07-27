"""Watchers service — thin proxy over agentic_cli.watchers.

Pydantic models on this side; validation + persistence + runtime on the CLI
side. Follows the same "backend is a lens" pattern as admin_service /
integrations_service.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HandlerModel(BaseModel):
    agent: str = ""
    chain: list[str] = Field(default_factory=list)
    input: dict[str, Any] = Field(default_factory=dict)


class WatcherModel(BaseModel):
    name: str
    trigger_type: str
    handler: HandlerModel = HandlerModel()
    filter: dict[str, Any] = Field(default_factory=dict)
    domain: str = ""
    enabled: bool = True
    poll_seconds: int = 0
    description: str = ""


class WatcherStateModel(BaseModel):
    """Per-watcher runtime state (cursor, last-fired, error). Read-only for the UI."""
    cursor: Optional[str] = None
    last_polled: Optional[str] = None
    last_fired: Optional[str] = None
    last_error: str = ""
    delivered_count: int = 0


class WatcherView(BaseModel):
    """Combined spec + state for the list UI (one round-trip)."""
    spec: WatcherModel
    state: WatcherStateModel


class TriggerFieldModel(BaseModel):
    type: str
    label: str
    required: bool = False
    help: str = ""


class TriggerModel(BaseModel):
    name: str
    label: str
    description: str = ""
    source_mcp: str = ""
    filter_schema: dict[str, TriggerFieldModel] = Field(default_factory=dict)
    default_poll_seconds: int = 300


class TestRunEventModel(BaseModel):
    event_id: str
    ts: str
    data: dict[str, Any]


class TestRunResult(BaseModel):
    trigger_type: str
    matched: int
    events: list[TestRunEventModel]
    error: str = ""


# ── Name validation (belt-and-suspenders alongside store._spec_path sanitation)

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")


def _valid_name(name: str) -> bool:
    return bool(_NAME_RE.match(name or ""))


# ── Model <-> CLI type bridging ─────────────────────────────────────────────


def _spec_from_model(m: WatcherModel):
    from agentic_cli.watchers.types import HandlerSpec, WatcherSpec

    return WatcherSpec(
        name=m.name,
        trigger_type=m.trigger_type,
        handler=HandlerSpec(
            agent=m.handler.agent,
            chain=list(m.handler.chain),
            input=dict(m.handler.input),
        ),
        filter=dict(m.filter),
        domain=m.domain,
        enabled=m.enabled,
        poll_seconds=m.poll_seconds,
        description=m.description,
    )


def _model_from_spec(spec) -> WatcherModel:
    return WatcherModel(
        name=spec.name,
        trigger_type=spec.trigger_type,
        handler=HandlerModel(
            agent=spec.handler.agent,
            chain=list(spec.handler.chain),
            input=dict(spec.handler.input),
        ),
        filter=dict(spec.filter),
        domain=spec.domain,
        enabled=spec.enabled,
        poll_seconds=spec.poll_seconds,
        description=spec.description,
    )


def _state_model(state) -> WatcherStateModel:
    return WatcherStateModel(
        cursor=state.cursor.isoformat() if state.cursor else None,
        last_polled=state.last_polled.isoformat() if state.last_polled else None,
        last_fired=state.last_fired.isoformat() if state.last_fired else None,
        last_error=state.last_error,
        delivered_count=len(state.delivered),
    )


# ── Public service functions (called by the API layer) ─────────────────────


def list_watchers() -> list[WatcherView]:
    from agentic_cli.watchers.store import load_all_state, load_specs

    specs = load_specs()
    states = load_all_state()
    from agentic_cli.watchers.types import WatcherState

    return [
        WatcherView(
            spec=_model_from_spec(s),
            state=_state_model(states.get(s.name, WatcherState())),
        )
        for s in specs
    ]


def get_watcher(name: str) -> Optional[WatcherView]:
    from agentic_cli.watchers.store import load_all_state, load_spec
    from agentic_cli.watchers.types import WatcherState

    spec = load_spec(name)
    if spec is None:
        return None
    state = load_all_state().get(name, WatcherState())
    return WatcherView(spec=_model_from_spec(spec), state=_state_model(state))


def upsert_watcher(model: WatcherModel) -> WatcherView:
    """Create or replace a watcher. Validates the trigger + filter schema."""
    from agentic_cli.watchers.registry import get_trigger, TriggerNotFoundError
    from agentic_cli.watchers.store import save_spec
    from agentic_cli.watchers.types import WatcherState

    if not _valid_name(model.name):
        raise ValueError(
            f"invalid watcher name '{model.name}' "
            f"(must match {_NAME_RE.pattern})"
        )
    try:
        trigger = get_trigger(model.trigger_type)
    except TriggerNotFoundError as e:
        raise ValueError(str(e)) from e
    for key, value in model.filter.items():
        if key not in trigger.info.filter_schema:
            logger.info(
                f"watcher '{model.name}' filter has unknown field '{key}' "
                f"for trigger '{trigger.info.name}'; passing through"
            )
    spec = _spec_from_model(model)
    save_spec(spec)
    return WatcherView(spec=_model_from_spec(spec), state=_state_model(WatcherState()))


def delete_watcher(name: str) -> bool:
    from agentic_cli.watchers.store import delete_spec

    return delete_spec(name)


def set_enabled(name: str, enabled: bool) -> Optional[WatcherView]:
    from agentic_cli.watchers.store import load_all_state, load_spec, save_spec
    from agentic_cli.watchers.types import WatcherState

    spec = load_spec(name)
    if spec is None:
        return None
    spec.enabled = enabled
    save_spec(spec)
    state = load_all_state().get(name, WatcherState())
    return WatcherView(spec=_model_from_spec(spec), state=_state_model(state))


def list_triggers() -> list[TriggerModel]:
    from agentic_cli.watchers.registry import list_triggers as _list

    return [
        TriggerModel(
            name=t.info.name,
            label=t.info.label,
            description=t.info.description,
            source_mcp=t.info.source_mcp,
            filter_schema={
                fname: TriggerFieldModel(**field)
                for fname, field in t.info.filter_schema.items()
            },
            default_poll_seconds=t.info.default_poll_seconds,
        )
        for t in _list()
    ]


async def test_run(name: str) -> TestRunResult:
    """Poll a watcher once and return matches without dispatching."""
    from agentic_cli.watchers.store import load_spec

    spec = load_spec(name)
    if spec is None:
        return TestRunResult(trigger_type="", matched=0, events=[], error="not found")

    from src.services.watcher_runtime import get_runtime  # avoid circular at import

    runtime = get_runtime()
    try:
        events = await runtime.test_run(spec)
    except Exception as e:  # noqa: BLE001
        return TestRunResult(trigger_type=spec.trigger_type, matched=0, events=[], error=str(e))
    return TestRunResult(
        trigger_type=spec.trigger_type,
        matched=len(events),
        events=[
            TestRunEventModel(event_id=e.event_id, ts=e.ts.isoformat(), data=e.data)
            for e in events
        ],
    )


def watchers_for_agent(agent: str) -> list[WatcherView]:
    """List watchers whose handler fires ``agent``. Powers the Agent Builder section."""
    return [v for v in list_watchers() if v.spec.handler.agent == agent]
