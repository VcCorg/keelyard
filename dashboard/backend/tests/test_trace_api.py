"""Context trace API: the read side of the KeelTrace ledger."""

import pytest


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    import agentic_cli.tracker as tr

    db_dir = tmp_path / ".keel-tracker"
    db_dir.mkdir()
    monkeypatch.setattr(tr, "DB_DIR", db_dir)
    monkeypatch.setattr(tr, "DB_PATH", db_dir / "tracker.db")
    return tr


@pytest.fixture()
def seeded(tracker):
    from agentic_cli import tracing

    with tracing.session_scope("sess-a"):
        tracing.record_context_read(source="mcp", operation="jira/get_issue",
                                    entity_id="KEEL-412", size_bytes=2100,
                                    duration_ms=41, arguments={"key": "KEEL-412"})
        tracing.record_context_read(source="kg", operation="query",
                                    entity_id="domain:payments", size_bytes=8400,
                                    duration_ms=120)
        tracing.record_context_read(source="mcp", operation="confluence/search",
                                    size_bytes=0, status="error")
    with tracing.session_scope("sess-b"):
        tracing.record_context_read(source="mcp", operation="bitbucket/get_file",
                                    size_bytes=6200)
    return tracker


def test_list_sessions_returns_rollups(seeded):
    from src.services.trace_service import list_sessions

    sessions = {s.session_id: s for s in list_sessions()}
    assert set(sessions) == {"sess-a", "sess-b"}
    a = sessions["sess-a"]
    assert a.reads == 3
    assert a.bytes == 10500
    assert a.errors == 1
    assert a.sources == ["kg", "mcp"]


def test_ledger_is_ordered_oldest_first_with_rollup(seeded):
    from src.services.trace_service import get_ledger

    led = get_ledger("sess-a")
    assert led.reads == 3
    assert led.bytes == 10500
    assert led.errors == 1
    assert [e.operation for e in led.entries] == [
        "jira/get_issue", "query", "confluence/search",
    ]
    rollup = {r.source: (r.reads, r.bytes) for r in led.by_source}
    assert rollup == {"mcp": (2, 2100), "kg": (1, 8400)}


def test_ledger_carries_latency_status_and_entity(seeded):
    from src.services.trace_service import get_ledger

    first = get_ledger("sess-a").entries[0]
    assert first.source == "mcp"
    assert first.entity_id is not None
    assert first.duration_ms == 41
    assert first.status == "success"
    assert first.bytes == 2100


def test_ledger_never_exposes_raw_arguments(seeded):
    """Arguments are fingerprinted at record time; the API must not leak them."""
    from src.services.trace_service import get_ledger

    first = get_ledger("sess-a").entries[0]
    assert first.args_digest and first.args_digest.startswith("sha256:")
    assert "KEEL-412" not in (first.args_digest or "")


def test_unknown_session_is_an_empty_ledger_not_an_error(seeded):
    from src.services.trace_service import get_ledger

    led = get_ledger("does-not-exist")
    assert led.session_id == "does-not-exist"
    assert led.reads == 0 and led.entries == [] and led.by_source == []


def test_sessions_are_isolated_from_each_other(seeded):
    from src.services.trace_service import get_ledger

    assert [e.operation for e in get_ledger("sess-b").entries] == ["bitbucket/get_file"]


def test_routes_are_registered_on_the_app():
    """The router is wired into main, not merely defined.

    Checked through the OpenAPI schema rather than app.routes: this FastAPI
    version keeps included routers as _IncludedRouter wrappers instead of
    flattening them into Route objects, so app.routes lists only the handlers
    declared directly on the app.
    """
    from src.api.main import app

    paths = app.openapi().get("paths", {})
    assert "/api/trace/sessions" in paths
    assert "/api/trace/sessions/{session_id}" in paths
