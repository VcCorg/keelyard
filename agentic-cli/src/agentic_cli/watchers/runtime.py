"""WatcherRuntime — asyncio scheduler hosted inside the backend sidecar.

Behavior:
  * On startup: **catch-up scan** — for every enabled watcher, poll once
    with ``since = max(cursor, now - CATCH_UP_WINDOW)``. Catches missed
    notifications from while the app was closed. Window is 3 days for
    Phase 1 (see docs/WATCHERS.md).
  * Steady state: per-watcher asyncio task polls every
    ``spec.poll_seconds`` (falling back to ``trigger.default_poll_seconds``).
    Tasks are staggered so 20 watchers don't hammer the same MCP at once.
  * Every matched event is:
      1. checked against the delivered-event LRU (idempotent replay),
      2. dispatched via ``execution.registry.create_session`` with
         ``origin=watcher/<name>``,
      3. recorded — the event id is remembered, cursor advances, state saved.

The runtime is designed to survive any single-watcher failure: a bad
adapter or a broken filter regex only pauses THAT watcher, never crashes
the loop.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

from .registry import try_get_trigger
from .store import load_all_state, load_specs, save_state
from .types import TriggerEvent, WatcherSpec, WatcherState, resolve_event_path

logger = logging.getLogger(__name__)


#: Catch-up window applied to the first poll after startup. 3 days matches
#: the user's guidance — enough to cover a long weekend / short absence,
#: bounded so a returning user isn't blasted with month-old events.
CATCH_UP_WINDOW = timedelta(days=3)


DispatchFn = Callable[[WatcherSpec, TriggerEvent], Awaitable[dict[str, Any]]]


class WatcherRuntime:
    """The scheduler + dispatcher. One instance per backend process.

    Tests inject a ``dispatch`` to intercept event delivery; production wires
    it to ``execution.registry.create_session`` at the API layer.
    """

    def __init__(self, dispatch: Optional[DispatchFn] = None) -> None:
        self._dispatch: DispatchFn = dispatch or _default_dispatch
        self._tasks: dict[str, asyncio.Task] = {}
        self._stop_event = asyncio.Event()
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Load specs, run catch-up, then kick off the per-watcher poll tasks."""
        if self._started:
            return
        self._started = True
        self._stop_event.clear()

        specs = [s for s in load_specs() if s.enabled]
        states = load_all_state()

        # Catch-up scan is serial per watcher (small N) but concurrent
        # across watchers so a slow MCP doesn't stall the others.
        await asyncio.gather(
            *(self._catch_up(spec, states.get(spec.name, WatcherState())) for spec in specs),
            return_exceptions=True,
        )

        for spec in specs:
            self._start_poll_task(spec)

    async def stop(self) -> None:
        """Cancel every poll task and wait for them to unwind."""
        if not self._started:
            return
        self._stop_event.set()
        for task in list(self._tasks.values()):
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        self._started = False

    def _start_poll_task(self, spec: WatcherSpec) -> None:
        """Launch the per-watcher poll loop with a small random stagger."""
        stagger = random.uniform(0, 5.0)
        task = asyncio.create_task(self._poll_loop(spec, initial_delay=stagger))
        self._tasks[spec.name] = task

    # ── Catch-up + steady-state loops ─────────────────────────────────

    async def _catch_up(self, spec: WatcherSpec, state: WatcherState) -> None:
        """One poll on startup, honoring the 3-day catch-up window."""
        now = datetime.now(timezone.utc)
        since = state.cursor if state.cursor else (now - CATCH_UP_WINDOW)
        # Never look further back than the window even if the cursor is old,
        # to protect against a "returning user after 2 months" blast.
        since = max(since, now - CATCH_UP_WINDOW)
        await self._poll_once(spec, state, since)

    async def _poll_loop(self, spec: WatcherSpec, initial_delay: float = 0.0) -> None:
        """Steady-state poll for a single watcher."""
        try:
            await asyncio.sleep(initial_delay)
            while not self._stop_event.is_set():
                trigger = try_get_trigger(spec.trigger_type)
                poll_secs = spec.poll_seconds or (trigger.info.default_poll_seconds if trigger else 300)
                state = load_all_state().get(spec.name, WatcherState())
                since = state.cursor or (datetime.now(timezone.utc) - CATCH_UP_WINDOW)
                await self._poll_once(spec, state, since)
                # Wait either poll_secs OR until stop is signalled.
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=poll_secs)
                    return  # stop was set
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — one watcher's bug can't kill the runtime
            logger.exception(f"watcher {spec.name} poll loop crashed: {e}")

    # ── The single poll step ──────────────────────────────────────────

    async def _poll_once(
        self,
        spec: WatcherSpec,
        state: WatcherState,
        since: datetime,
    ) -> list[TriggerEvent]:
        """Poll the trigger once, dispatch any new events, persist state."""
        state.last_polled = datetime.now(timezone.utc)
        trigger = try_get_trigger(spec.trigger_type)
        if trigger is None:
            state.last_error = f"unknown trigger '{spec.trigger_type}'"
            save_state(spec.name, state)
            return []

        try:
            events = await trigger.fetch(spec.filter, since)
        except Exception as e:  # noqa: BLE001 — record + move on
            state.last_error = f"fetch failed: {e}"
            save_state(spec.name, state)
            logger.info(f"watcher {spec.name} fetch failed: {e}")
            return []

        state.last_error = ""
        new_events: list[TriggerEvent] = []
        for event in events:
            if event.event_id in state.delivered:
                continue
            new_events.append(event)

        # Advance cursor to the newest event we saw (before dispatch, so a
        # crash mid-dispatch replays only the un-remembered events on restart).
        if events:
            newest_ts = max((e.ts for e in events), default=state.cursor)
            if newest_ts and (state.cursor is None or newest_ts > state.cursor):
                state.cursor = newest_ts
        save_state(spec.name, state)

        for event in new_events:
            await self._safe_dispatch(spec, event, state)
        return new_events

    async def _safe_dispatch(
        self,
        spec: WatcherSpec,
        event: TriggerEvent,
        state: WatcherState,
    ) -> None:
        """Dispatch one event; record delivery on success, log on failure."""
        try:
            await self._dispatch(spec, event)
            state.remember(event.event_id)
            state.last_fired = datetime.now(timezone.utc)
        except Exception as e:  # noqa: BLE001 — dead-letter after 1 retry (Phase 2)
            state.last_error = f"dispatch failed: {e}"
            logger.info(f"watcher {spec.name} dispatch failed: {e}")
        save_state(spec.name, state)

    # ── Public "run once" for the UI's test-run button ────────────────

    async def test_run(self, spec: WatcherSpec) -> list[TriggerEvent]:
        """Poll the trigger once and return matches WITHOUT dispatching.

        Used by the dashboard's "Test run" button so a user can validate a
        filter before wiring it live. State is not persisted.
        """
        trigger = try_get_trigger(spec.trigger_type)
        if trigger is None:
            return []
        since = datetime.now(timezone.utc) - CATCH_UP_WINDOW
        try:
            return await trigger.fetch(spec.filter, since)
        except Exception as e:  # noqa: BLE001
            logger.info(f"test-run failed for {spec.name}: {e}")
            return []


# ── Default dispatch — into the execution seam ──────────────────────────────


async def _default_dispatch(spec: WatcherSpec, event: TriggerEvent) -> dict[str, Any]:
    """Route a matched event into the vendor-neutral session-launch seam.

    Governance + audit ride on top of ``create_session``, so we get
    per-domain build_governance, tracker records, and persona filtering for
    free. Handler agent name + templated input are packed into the spec's
    ``engine_options`` bag so the adapter can surface them.
    """
    from agentic_cli.execution.registry import create_session
    from agentic_cli.execution.base import ExecutionSpec

    prompt = _render_prompt(spec, event)
    result = create_session(
        ExecutionSpec(
            prompt=prompt,
            title=f"watcher/{spec.name}",
            domain=spec.domain,
            tags=["watcher", spec.trigger_type, spec.name],
            context=[],
            engine_options={
                "watcher": {
                    "name": spec.name,
                    "trigger_type": spec.trigger_type,
                    "event_id": event.event_id,
                    "handler_agent": spec.handler.agent,
                    "handler_chain": list(spec.handler.chain),
                    "handler_input": _resolve_input(spec, event),
                },
            },
            idempotent=True,
        ),
    )
    return {"session_id": result.session_id, "url": result.url, "engine": result.engine}


def _render_prompt(spec: WatcherSpec, event: TriggerEvent) -> str:
    """Best-effort human-readable prompt for the session bag."""
    parts = [
        f"Watcher '{spec.name}' fired on '{spec.trigger_type}'.",
        f"Event id: {event.event_id}",
        f"Timestamp: {event.ts.astimezone(timezone.utc).isoformat()}",
        f"Handler agent: {spec.handler.agent}",
    ]
    if spec.handler.chain:
        parts.append(f"Chain (Phase 2): {' -> '.join(spec.handler.chain)}")
    return "\n".join(parts)


_PLACEHOLDER = re.compile(r"\$event\.([A-Za-z0-9_.]+)")


def _resolve_input(spec: WatcherSpec, event: TriggerEvent) -> dict[str, Any]:
    """Substitute ``$event.<path>`` placeholders in the handler input mapping."""
    resolved: dict[str, Any] = {}
    for key, value in spec.handler.input.items():
        if isinstance(value, str):
            resolved[key] = _PLACEHOLDER.sub(
                lambda m: str(resolve_event_path(event, m.group(1)) or ""),
                value,
            )
        else:
            resolved[key] = value
    return resolved
