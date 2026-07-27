"""Watchers Phase 1 — pins storage, Bitbucket adapter, and runtime dispatch.

The runtime is the important one to lock: catch-up window, dedup, and
"cursor advances BEFORE dispatch" (so a crash mid-dispatch replays exactly
the un-remembered events on restart).
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agentic_cli.watchers import (
    HandlerSpec,
    TriggerEvent,
    WatcherSpec,
    WatcherState,
    get_trigger,
    list_triggers,
    register_trigger,
)
from agentic_cli.watchers.registry import TriggerNotFoundError
from agentic_cli.watchers.runtime import CATCH_UP_WINDOW, WatcherRuntime
from agentic_cli.watchers.store import (
    delete_spec,
    load_all_state,
    load_spec,
    load_specs,
    save_spec,
    save_state,
)
from agentic_cli.watchers.triggers import bitbucket_pr
from agentic_cli.watchers.types import TriggerInfo


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_watchers_dir(tmp_path, monkeypatch):
    """Point storage at a temp dir so we never touch a real ~/.keel."""
    monkeypatch.setenv("KEEL_WATCHERS_DIR", str(tmp_path))
    yield tmp_path


# ── Storage ─────────────────────────────────────────────────────────────────


def test_save_load_spec_roundtrip(temp_watchers_dir):
    spec = WatcherSpec(
        name="pr-nudge",
        trigger_type="bitbucket.pr.review_requested",
        handler=HandlerSpec(agent="pr-triage", chain=["pr-triage", "docs"], input={"pr_url": "$event.pr.url"}),
        filter={"project": "CWOW", "age_hours_gt": 24},
        domain="cwow-facility",
        enabled=True,
        poll_seconds=120,
        description="Nudge stale reviews",
    )
    save_spec(spec)
    loaded = load_spec("pr-nudge")
    assert loaded is not None
    assert loaded.name == spec.name
    assert loaded.trigger_type == spec.trigger_type
    assert loaded.handler.agent == "pr-triage"
    assert loaded.handler.chain == ["pr-triage", "docs"]
    assert loaded.handler.input == {"pr_url": "$event.pr.url"}
    assert loaded.filter == {"project": "CWOW", "age_hours_gt": 24}
    assert loaded.domain == "cwow-facility"
    assert loaded.poll_seconds == 120
    assert loaded.enabled is True


def test_delete_spec_removes_state_too(temp_watchers_dir):
    save_spec(WatcherSpec(name="w1", trigger_type="x", handler=HandlerSpec(agent="a")))
    save_state("w1", WatcherState(cursor=datetime.now(timezone.utc), delivered=["e1"]))
    assert load_spec("w1") is not None
    assert "w1" in load_all_state()

    assert delete_spec("w1") is True
    assert load_spec("w1") is None
    assert "w1" not in load_all_state()


def test_load_specs_skips_malformed_yaml(temp_watchers_dir):
    save_spec(WatcherSpec(name="good", trigger_type="x", handler=HandlerSpec(agent="a")))
    (Path(temp_watchers_dir) / "bad.yaml").write_text("this is: [not valid: yaml")
    specs = load_specs()
    # Good survives, bad is skipped without raising.
    assert {s.name for s in specs} == {"good"}


def test_state_lru_bounded():
    state = WatcherState()
    for i in range(600):
        state.remember(f"e{i}", max_len=100)
    assert len(state.delivered) == 100
    # Oldest dropped first — the last 100 remain.
    assert state.delivered[0] == "e500"
    assert state.delivered[-1] == "e599"


# ── Bitbucket adapter ───────────────────────────────────────────────────────


class _FakeBitbucketClient:
    """Stands in for the MCP client. Returns whatever PRs the test seeds."""

    def __init__(self, prs):
        self._prs = prs

    def list_open_prs(self, project=None, repo=None, reviewer_is_me=True, limit=200):
        return list(self._prs)


def _pr(id_, title, updated_at, seq=1):
    return {
        "id": id_,
        "title": title,
        "updated_at": updated_at,
        "review_request_seq": seq,
        "url": f"https://bb.example.com/pr/{id_}",
    }


def _install_fake_client(prs):
    bitbucket_pr.set_client_factory(lambda: _FakeBitbucketClient(prs))


def test_bitbucket_adapter_returns_events(monkeypatch):
    now = datetime.now(timezone.utc)
    _install_fake_client([
        _pr(1, "Fix docs", now.isoformat()),
        _pr(2, "Refactor auth", now.isoformat()),
    ])
    trigger = get_trigger("bitbucket.pr.review_requested")
    events = asyncio.run(trigger.fetch({}, since=now - timedelta(hours=1)))
    assert len(events) == 2
    assert all(e.type == "bitbucket.pr.review_requested" for e in events)


def test_bitbucket_adapter_since_filter_excludes_old(monkeypatch):
    now = datetime.now(timezone.utc)
    _install_fake_client([
        _pr(1, "Recent", now.isoformat()),
        _pr(2, "Old", (now - timedelta(days=10)).isoformat()),
    ])
    trigger = get_trigger("bitbucket.pr.review_requested")
    events = asyncio.run(trigger.fetch({}, since=now - timedelta(days=1)))
    titles = [e.data["pr"]["title"] for e in events]
    assert "Recent" in titles
    assert "Old" not in titles


def test_bitbucket_adapter_title_regex_filter(monkeypatch):
    now = datetime.now(timezone.utc)
    _install_fake_client([
        _pr(1, "[bug] leak", now.isoformat()),
        _pr(2, "Docs typo", now.isoformat()),
    ])
    trigger = get_trigger("bitbucket.pr.review_requested")
    events = asyncio.run(trigger.fetch({"title_matches": r"^\[bug\]"}, since=now - timedelta(hours=1)))
    assert [e.data["pr"]["id"] for e in events] == [1]


def test_bitbucket_adapter_age_hours_gt_filter(monkeypatch):
    now = datetime.now(timezone.utc)
    _install_fake_client([
        _pr(1, "Just now", now.isoformat()),
        _pr(2, "3h old", (now - timedelta(hours=3)).isoformat()),
    ])
    trigger = get_trigger("bitbucket.pr.review_requested")
    events = asyncio.run(trigger.fetch({"age_hours_gt": 2}, since=now - timedelta(days=1)))
    assert [e.data["pr"]["id"] for e in events] == [2]


def test_bitbucket_adapter_returns_empty_on_client_none(monkeypatch):
    bitbucket_pr.set_client_factory(lambda: None)
    trigger = get_trigger("bitbucket.pr.review_requested")
    events = asyncio.run(trigger.fetch({}, since=datetime.now(timezone.utc) - timedelta(hours=1)))
    assert events == []


# ── Registry ────────────────────────────────────────────────────────────────


def test_registry_lists_bitbucket_adapter():
    names = {t.info.name for t in list_triggers()}
    assert "bitbucket.pr.review_requested" in names


def test_registry_raises_on_unknown():
    with pytest.raises(TriggerNotFoundError):
        get_trigger("does.not.exist")


# ── Runtime ─────────────────────────────────────────────────────────────────


class _MockTrigger:
    """Adapter that just returns a scripted list of events for the test."""

    def __init__(self, events):
        self._events = events
        self.info = TriggerInfo(
            name="mock.trigger",
            label="Mock",
            description="For tests",
            filter_schema={},
            default_poll_seconds=1,
        )
        self.fetch_calls: list[datetime] = []

    async def fetch(self, filter, since, limit=200):
        self.fetch_calls.append(since)
        return list(self._events)


@pytest.fixture
def register_mock_trigger():
    from agentic_cli.watchers.registry import _REGISTRY

    def _install(events):
        trigger = _MockTrigger(events)
        register_trigger(trigger)
        return trigger

    yield _install
    _REGISTRY.pop("mock.trigger", None)


def _dispatched_collector():
    """Return (dispatched_list, dispatch_fn) — records calls to the runtime dispatcher."""
    dispatched: list[tuple[str, TriggerEvent]] = []

    async def _dispatch(spec: WatcherSpec, event: TriggerEvent):
        dispatched.append((spec.name, event))
        return {"session_id": f"sess-{event.event_id}", "url": "", "engine": "mock"}

    return dispatched, _dispatch


def test_runtime_catches_up_dispatches_and_dedupes(temp_watchers_dir, register_mock_trigger):
    now = datetime.now(timezone.utc)
    trigger = register_mock_trigger([
        TriggerEvent(type="mock.trigger", event_id="e1", ts=now - timedelta(hours=1), data={}),
        TriggerEvent(type="mock.trigger", event_id="e2", ts=now, data={}),
    ])
    save_spec(WatcherSpec(
        name="w-catchup",
        trigger_type="mock.trigger",
        handler=HandlerSpec(agent="a"),
        poll_seconds=999,
    ))
    dispatched, dispatch = _dispatched_collector()
    runtime = WatcherRuntime(dispatch=dispatch)

    # Run catch-up only (steady-state would tie up the loop with 999s waits).
    async def _run_catchup_once():
        specs = [s for s in load_specs() if s.enabled]
        states = load_all_state()
        for spec in specs:
            await runtime._catch_up(spec, states.get(spec.name, WatcherState()))  # noqa: SLF001

    asyncio.run(_run_catchup_once())
    ids = [ev.event_id for _, ev in dispatched]
    assert ids == ["e1", "e2"]

    # State was persisted; cursor advanced to the newest event's ts and both
    # ids are in the delivered LRU.
    state = load_all_state()["w-catchup"]
    assert state.cursor is not None
    assert state.cursor >= now - timedelta(seconds=1)
    assert set(state.delivered) == {"e1", "e2"}

    # A second catch-up run should NOT re-dispatch (dedup).
    dispatched.clear()
    asyncio.run(_run_catchup_once())
    assert dispatched == []


def test_runtime_catchup_window_caps_at_three_days(temp_watchers_dir, register_mock_trigger):
    """Even if the cursor is old, the catch-up scan never looks further back than
    the CATCH_UP_WINDOW — protects the "returning user after 2 months" case.
    """
    now = datetime.now(timezone.utc)
    trigger = register_mock_trigger([])
    save_spec(WatcherSpec(name="w-cap", trigger_type="mock.trigger", handler=HandlerSpec(agent="a"), poll_seconds=999))
    # Seed a very old cursor.
    save_state("w-cap", WatcherState(cursor=now - timedelta(days=30)))

    runtime = WatcherRuntime(dispatch=(_dispatched_collector()[1]))

    async def _run_catchup_once():
        specs = [s for s in load_specs() if s.enabled]
        states = load_all_state()
        for spec in specs:
            await runtime._catch_up(spec, states.get(spec.name, WatcherState()))  # noqa: SLF001

    asyncio.run(_run_catchup_once())
    since_used = trigger.fetch_calls[-1]
    # `since` should be within the last 3 days + a tiny slack for wall clock.
    assert (now - since_used) <= CATCH_UP_WINDOW + timedelta(seconds=5)


def test_test_run_does_not_dispatch_or_persist_state(temp_watchers_dir, register_mock_trigger):
    now = datetime.now(timezone.utc)
    register_mock_trigger([
        TriggerEvent(type="mock.trigger", event_id="preview", ts=now, data={"x": 1}),
    ])
    spec = WatcherSpec(name="w-preview", trigger_type="mock.trigger", handler=HandlerSpec(agent="a"))
    save_spec(spec)

    dispatched, dispatch = _dispatched_collector()
    runtime = WatcherRuntime(dispatch=dispatch)
    events = asyncio.run(runtime.test_run(spec))
    assert [e.event_id for e in events] == ["preview"]
    # Test run must NOT call the dispatcher or advance state.
    assert dispatched == []
    assert load_all_state().get("w-preview", WatcherState()).cursor is None


def test_runtime_records_error_but_does_not_crash_on_adapter_failure(temp_watchers_dir):
    """A trigger that raises inside fetch() is logged; state records the error."""

    class _Broken:
        info = TriggerInfo(name="broken.trigger", label="Broken", filter_schema={})

        async def fetch(self, filter, since, limit=200):
            raise RuntimeError("simulated")

    register_trigger(_Broken())
    try:
        save_spec(WatcherSpec(name="w-broken", trigger_type="broken.trigger", handler=HandlerSpec(agent="a")))
        _, dispatch = _dispatched_collector()
        runtime = WatcherRuntime(dispatch=dispatch)

        async def _once():
            spec = load_spec("w-broken")
            state = load_all_state().get("w-broken", WatcherState())
            await runtime._poll_once(spec, state, datetime.now(timezone.utc) - timedelta(hours=1))  # noqa: SLF001

        asyncio.run(_once())
        state = load_all_state()["w-broken"]
        assert "simulated" in state.last_error
    finally:
        from agentic_cli.watchers.registry import _REGISTRY

        _REGISTRY.pop("broken.trigger", None)
