"""Tests for Jira MCP error unwrapping (Work Items must degrade gracefully)."""

from src.services import jira_service as svc


def test_root_exception_unwraps_exception_group():
    inner = ConnectionRefusedError("Connection refused")
    group = ExceptionGroup("unhandled errors in a TaskGroup", [inner])
    assert svc._root_exception(group) is inner


def test_root_exception_unwraps_nested_groups():
    inner = OSError("Connection refused")
    nested = ExceptionGroup("g1", [ExceptionGroup("g2", [inner])])
    assert svc._root_exception(nested) is inner


def test_friendly_error_for_connection_failure_is_actionable():
    group = ExceptionGroup("unhandled errors in a TaskGroup",
                           [ConnectionRefusedError("Connection refused")])
    msg = svc._friendly_mcp_error(group)
    assert "Jira MCP server" in msg
    assert "TaskGroup" not in msg  # the opaque wrapper never leaks to users


def test_friendly_error_passes_through_real_jira_errors():
    err = RuntimeError("Field 'priority' is required.")
    msg = svc._friendly_mcp_error(err)
    assert msg == "Field 'priority' is required."


def test_list_my_issues_reports_clean_error(monkeypatch):
    monkeypatch.setattr(svc, "is_configured", lambda: True)
    monkeypatch.setattr(svc, "_domain_project_keys", lambda: ["PROJ"])

    def boom(*_a, **_k):
        raise ExceptionGroup("unhandled errors in a TaskGroup",
                             [ConnectionRefusedError("Connection refused")])

    monkeypatch.setattr(svc, "_call_tool", boom)
    resp = svc.list_my_domain_issues()
    assert resp.configured is True
    assert resp.issues == []
    assert "Jira MCP server" in (resp.error or "")
    assert "TaskGroup" not in (resp.error or "")
