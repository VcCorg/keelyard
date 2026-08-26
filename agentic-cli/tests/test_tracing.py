"""Tests for the session context ledger (KeelTrace P1 sensors)."""

import asyncio
import threading

import pytest

from agentic_cli import tracing


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    """Point the tracker at a temp DB so tests never touch the real one."""
    import agentic_cli.tracker as tr

    db_dir = tmp_path / ".keel-tracker"
    db_dir.mkdir()
    monkeypatch.setattr(tr, "DB_DIR", db_dir)
    monkeypatch.setattr(tr, "DB_PATH", db_dir / "tracker.db")
    return tr


# --------------------------------------------------------------------------
# Session identity
# --------------------------------------------------------------------------

def test_no_session_by_default():
    assert tracing.current_session_id() is None


def test_session_scope_binds_and_restores():
    assert tracing.current_session_id() is None
    with tracing.session_scope("abc123") as sid:
        assert sid == "abc123"
        assert tracing.current_session_id() == "abc123"
    assert tracing.current_session_id() is None


def test_session_scope_mints_an_id_when_not_given():
    with tracing.session_scope() as sid:
        assert sid and tracing.current_session_id() == sid


def test_session_scope_restores_on_exception():
    with pytest.raises(RuntimeError):
        with tracing.session_scope("boom"):
            raise RuntimeError("boom")
    assert tracing.current_session_id() is None


def test_nested_scopes_restore_the_outer_id():
    with tracing.session_scope("outer"):
        with tracing.session_scope("inner"):
            assert tracing.current_session_id() == "inner"
        assert tracing.current_session_id() == "outer"


# --------------------------------------------------------------------------
# The thread trap: ContextVars do not cross threading.Thread.
# This is the whole reason sensors read the id on the caller's thread.
# --------------------------------------------------------------------------

def test_contextvar_does_not_cross_a_thread_boundary():
    """Documents the constraint the sensor placement is designed around.

    If this ever starts passing with the id intact, the explicit session_id
    plumbing in call_mcp_tool could be simplified -- but until then, reading
    the ContextVar inside a worker thread yields None.
    """
    seen = {}

    def worker():
        seen["id"] = tracing.current_session_id()

    with tracing.session_scope("outer-thread"):
        t = threading.Thread(target=worker)
        t.start()
        t.join()

    assert seen["id"] is None, "ContextVar unexpectedly crossed a thread"


def test_contextvar_does_cross_into_asyncio_tasks():
    """Same-thread async is fine -- only the thread hop loses the binding."""
    async def main():
        return await asyncio.create_task(_read())

    async def _read():
        return tracing.current_session_id()

    with tracing.session_scope("async-ok"):
        assert asyncio.run(main()) == "async-ok"


# --------------------------------------------------------------------------
# Recording
# --------------------------------------------------------------------------

def test_record_context_read_attributes_to_active_session(tracker):
    with tracing.session_scope("sess-1"):
        tracing.record_context_read(
            source="mcp", operation="jira/get_issue",
            entity_id="KEEL-412", size_bytes=2100, duration_ms=42,
        )
    rows = tracker.get_activity(entity_type="context", limit=10)
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == "sess-1"
    assert rows[0]["command"] == "mcp"
    assert rows[0]["subcommand"] == "jira/get_issue"
    assert rows[0]["entity_id"] == "KEEL-412"
    assert rows[0]["duration_ms"] == 42


def test_explicit_session_id_beats_the_contextvar(tracker):
    """The sensor passes the id captured before a thread hop; it must win."""
    with tracing.session_scope("ambient"):
        tracing.record_context_read(
            source="mcp", operation="t", session_id="explicit",
        )
    rows = tracker.get_activity(entity_type="context", limit=10)
    assert rows[0]["correlation_id"] == "explicit"


def test_reads_without_a_session_are_still_recorded(tracker):
    tracing.record_context_read(source="kg", operation="query")
    rows = tracker.get_activity(entity_type="context", limit=10)
    assert len(rows) == 1 and rows[0]["correlation_id"] is None


def test_arguments_are_digested_never_stored(tracker):
    secret = {"token": "super-secret-value", "issue": "KEEL-412"}
    tracing.record_context_read(
        source="mcp", operation="jira/get_issue", arguments=secret,
    )
    rows = tracker.get_activity(entity_type="context", limit=10)
    blob = str(rows[0])
    assert "super-secret-value" not in blob
    assert "sha256:" in blob


def test_identical_arguments_digest_identically():
    a = tracing.digest_args({"b": 2, "a": 1})
    b = tracing.digest_args({"a": 1, "b": 2})
    assert a == b and a.startswith("sha256:")
    assert tracing.digest_args(None) == ""


def test_recording_never_raises(monkeypatch):
    """Telemetry must not be load-bearing."""
    import agentic_cli.tracker as tr

    def explode(*a, **k):
        raise RuntimeError("tracker down")

    monkeypatch.setattr(tr, "record_action", explode)
    tracing.record_context_read(source="mcp", operation="t")  # must not raise


def test_session_context_returns_only_that_session_oldest_first(tracker):
    with tracing.session_scope("s-a"):
        tracing.record_context_read(source="mcp", operation="first")
        tracing.record_context_read(source="mcp", operation="second")
    with tracing.session_scope("s-b"):
        tracing.record_context_read(source="mcp", operation="other")

    ledger = tracing.session_context("s-a")
    assert [r["subcommand"] for r in ledger] == ["first", "second"]


def test_session_summary_rolls_up_by_source(tracker):
    with tracing.session_scope("s-sum"):
        tracing.record_context_read(source="mcp", operation="jira/get", size_bytes=100)
        tracing.record_context_read(source="mcp", operation="bb/file", size_bytes=250)
        tracing.record_context_read(source="kg", operation="query", size_bytes=400)
        tracing.record_context_read(source="kg", operation="query", status="error")

    s = tracing.session_summary("s-sum")
    assert s["reads"] == 4
    assert s["bytes"] == 750
    assert s["errors"] == 1
    assert s["by_source"]["mcp"] == {"reads": 2, "bytes": 350}
    assert s["by_source"]["kg"]["reads"] == 2


def test_session_context_excludes_non_context_rows(tracker):
    """A session's own audit entry must not masquerade as a retrieval."""
    tracker.record_activity(
        "execution", "create_session", correlation_id="s-mix",
        entity_type="session", entity_id="abc",
    )
    with tracing.session_scope("s-mix"):
        tracing.record_context_read(source="mcp", operation="jira/get")

    assert len(tracing.session_chain("s-mix")) == 2
    ledger = tracing.session_context("s-mix")
    assert len(ledger) == 1 and ledger[0]["command"] == "mcp"


@pytest.mark.parametrize(
    "value,expected",
    [(None, 0), ("abc", 3), (b"abcd", 4)],
)
def test_measure_handles_common_shapes(value, expected):
    assert tracing.measure(value) == expected


def test_measure_survives_unserialisable_objects():
    class Weird:
        def __repr__(self):
            return "x" * 10

    assert tracing.measure(Weird()) > 0
