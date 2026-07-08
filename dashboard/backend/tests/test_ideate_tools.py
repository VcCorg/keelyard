import asyncio

import src.services.ideate_tools as tools
from src.services.ideate_tools import ToolContext, list_tools, call_tool


def test_list_tools_includes_integration_tools():
    ctx = ToolContext(project_key="CGF", actor="jdoe@x.com")
    names = {t.name for t in list_tools(ctx)}
    assert {"glean_search", "confluence_search", "jira_search", "jira_create_issue"} <= names


def test_list_tools_marks_mutating():
    ctx = ToolContext(project_key="CGF")
    by_name = {t.name: t for t in list_tools(ctx)}
    assert by_name["jira_create_issue"].mutating is True
    assert by_name["glean_search"].mutating is False


def test_call_search_tool(monkeypatch):
    async def fake_search(source, query, limit=5, user_token=None):
        return f"results for {query} from {source}"
    monkeypatch.setattr(tools, "_search_source", fake_search)
    ctx = ToolContext(project_key="CGF")
    out = asyncio.run(call_tool("glean_search", {"query": "auth"}, ctx))
    assert "results for auth from glean" in out["text"]


def test_call_mutating_tool_audits(monkeypatch):
    created, audits = [], []
    import src.services.jira_service as js
    monkeypatch.setattr(js, "create_issue", lambda **kw: created.append(kw) or {"key": "CGF-7", "url": "u"})
    import src.services.ideate_audit as audit
    monkeypatch.setattr(audit, "record_jira_create", lambda **kw: audits.append(kw))
    ctx = ToolContext(project_key="CGF", actor="jdoe@x.com", correlation_id="c1")
    out = asyncio.run(call_tool("jira_create_issue", {"title": "New", "acceptance_criteria": ["a"]}, ctx))
    assert out["key"] == "CGF-7"
    assert created[0]["summary"] == "New"
    assert len(audits) == 1 and audits[0]["ok"] is True and audits[0]["actor"] == "jdoe@x.com"


def test_call_unknown_tool_errors():
    ctx = ToolContext(project_key="CGF")
    out = asyncio.run(call_tool("nope", {}, ctx))
    assert "error" in out


def test_injected_agents_registered_as_tools():
    ctx = ToolContext(project_key="CGF", agents=[
        {"name": "Spec Writer", "path": "/tmp/spec-writer"},
        {"name": "PR-Reviewer", "path": "/tmp/pr"},
    ])
    by_name = {t.name: t for t in list_tools(ctx)}
    assert "agent_spec_writer" in by_name and "agent_pr_reviewer" in by_name
    spec = by_name["agent_spec_writer"]
    assert spec.kind == "agent" and spec.mutating is False


def test_call_agent_tool_invokes_answer(monkeypatch):
    calls = []

    def fake_test_agent(path, message, timeout=120):
        calls.append((path, message))
        return {"ok": True, "response": "agent says hi"}

    import src.services.agent_service as agent_service
    monkeypatch.setattr(agent_service, "test_agent", fake_test_agent)

    ctx = ToolContext(project_key="CGF", agents=[{"name": "Spec Writer", "path": "/tmp/spec-writer"}])
    out = asyncio.run(call_tool("agent_spec_writer", {"message": "draft"}, ctx))
    assert out["text"] == "agent says hi"
    assert calls[0][0] == "/tmp/spec-writer" and calls[0][1] == "draft"


def test_call_agent_tool_surfaces_error(monkeypatch):
    import src.services.agent_service as agent_service
    monkeypatch.setattr(agent_service, "test_agent",
                        lambda path, message, timeout=120: {"ok": False, "error": "boom"})
    ctx = ToolContext(project_key="CGF", agents=[{"name": "Spec Writer", "path": "/tmp/x"}])
    out = asyncio.run(call_tool("agent_spec_writer", {"message": "draft"}, ctx))
    assert "boom" in out["error"]
