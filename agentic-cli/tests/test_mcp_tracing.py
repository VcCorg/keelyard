"""The MCP sensor: every tool call lands in the session ledger.

The important case is the dashboard one. ``_run_async`` hops to a worker
thread when a loop is already running, and ContextVars do not cross that
boundary -- so a sensor that reads the session id too late works perfectly
from the CLI and silently records nothing from the dashboard.
"""

import asyncio

import pytest

from agentic_cli import mcp_tool_client, tracing


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    import agentic_cli.tracker as tr

    db_dir = tmp_path / ".keel-tracker"
    db_dir.mkdir()
    monkeypatch.setattr(tr, "DB_DIR", db_dir)
    monkeypatch.setattr(tr, "DB_PATH", db_dir / "tracker.db")
    return tr


@pytest.fixture()
def fake_tool(monkeypatch):
    """Replace the network call, keeping the real _run_async thread behaviour."""
    calls = []

    async def _fake(sse_url, tool_name, arguments, timeout=30.0):
        calls.append((sse_url, tool_name, arguments))
        return {"ok": True, "tool": tool_name}

    monkeypatch.setattr(mcp_tool_client, "_call_tool_async", _fake)
    return calls


def test_successful_call_is_recorded(tracker, fake_tool):
    with tracing.session_scope("sess-mcp"):
        mcp_tool_client.call_mcp_tool(
            "http://localhost:8126/sse", "get_issue", {"key": "KEEL-412"})

    ledger = tracing.session_context("sess-mcp")
    assert len(ledger) == 1
    row = ledger[0]
    assert row["command"] == "mcp"
    assert row["subcommand"] == "bitbucket/get_issue"   # url resolved to a name
    assert row["status"] == "success"
    assert row["duration_ms"] is not None


def test_failed_call_is_still_recorded(tracker, monkeypatch):
    async def _boom(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(mcp_tool_client, "_call_tool_async", _boom)

    with tracing.session_scope("sess-err"):
        with pytest.raises(mcp_tool_client.MCPToolError):
            mcp_tool_client.call_mcp_tool("http://localhost:8126/sse", "get_issue")

    ledger = tracing.session_context("sess-err")
    assert len(ledger) == 1 and ledger[0]["status"] == "error"


def test_recorded_from_an_async_caller_across_the_thread_hop(tracker, fake_tool):
    """The dashboard path. This is the test that would catch a late read."""
    async def dashboard_request():
        # A loop is running, so _run_async spawns a worker thread here.
        return mcp_tool_client.call_mcp_tool(
            "http://localhost:8129/sse", "get_page", {"id": "1"})

    with tracing.session_scope("sess-async"):
        asyncio.run(dashboard_request())

    ledger = tracing.session_context("sess-async")
    assert len(ledger) == 1, "sensor lost the session across the thread boundary"
    assert ledger[0]["subcommand"] == "confluence/get_page"


def test_calls_outside_a_session_are_recorded_unattributed(tracker, fake_tool):
    mcp_tool_client.call_mcp_tool("http://localhost:8126/sse", "get_issue")
    rows = tracker.get_activity(entity_type="context", limit=10)
    assert len(rows) == 1 and rows[0]["correlation_id"] is None


def test_tool_arguments_never_reach_the_ledger(tracker, fake_tool):
    with tracing.session_scope("sess-secret"):
        mcp_tool_client.call_mcp_tool(
            "http://localhost:8126/sse", "get_issue",
            {"authorization": "Bearer super-secret-token"})

    blob = str(tracing.session_context("sess-secret"))
    assert "super-secret-token" not in blob
    assert "sha256:" in blob


def test_sensor_failure_does_not_break_the_call(monkeypatch, fake_tool):
    """A broken sensor must never surface as a retrieval failure."""
    def explode(**kwargs):
        raise RuntimeError("tracker exploded")

    monkeypatch.setattr(tracing, "record_context_read", explode)

    # Sanity: the patch really does raise when called directly.
    with pytest.raises(RuntimeError):
        tracing.record_context_read(source="x", operation="y")

    # The retrieval still succeeds and returns its real result.
    result = mcp_tool_client.call_mcp_tool("http://localhost:8126/sse", "get_issue")
    assert result == {"ok": True, "tool": "get_issue"}
