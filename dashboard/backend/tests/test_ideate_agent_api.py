from fastapi import FastAPI
from fastapi.testclient import TestClient
import src.api.ideate as ideate_api


def _client():
    app = FastAPI()
    app.include_router(ideate_api.router)
    return TestClient(app)


def test_tools_endpoint():
    r = _client().get("/api/ideate/tools?project=CGF")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["tools"]}
    assert "glean_search" in names and "jira_create_issue" in names
    # run callables must NOT be serialized
    assert all("run" not in t for t in r.json()["tools"])


def test_agent_run_streams_events(monkeypatch):
    from src.services.ideate_agent import AgentEvent

    async def fake_run(task, context, ctx, model=None, **kw):
        yield AgentEvent(type="tool_call", tool="glean_search", args={"query": "x"})
        yield AgentEvent(type="stories", stories=[{"title": "T"}])

    monkeypatch.setattr(ideate_api, "_run_agent", fake_run)
    r = _client().post("/api/ideate/agent/run",
                       json={"task": "draft", "context": "ctx", "project_key": "CGF"},
                       headers={"x-auth-request-email": "jdoe@x.com"})
    assert r.status_code == 200
    body = r.text
    assert "glean_search" in body and "T" in body


def test_agents_endpoint_lists_answer_agents(monkeypatch):
    from src.services.agent_service import AgentProject

    monkeypatch.setattr(ideate_api, "_discover_agents", lambda: [
        AgentProject(name="Spec Writer", path="/tmp/spec", use_case="basic"),
        AgentProject(name="No Answer", path="/tmp/none", use_case="pr-reviewer"),
    ])
    monkeypatch.setattr(ideate_api, "_agent_has_answer",
                        lambda path: path == "/tmp/spec")
    r = _client().get("/api/ideate/agents")
    assert r.status_code == 200
    agents = r.json()["agents"]
    names = {a["name"] for a in agents}
    assert names == {"Spec Writer"}
    assert agents[0]["tool_name"] == "agent_spec_writer"


def test_agent_run_passes_injected_agents(monkeypatch):
    from src.services.ideate_agent import AgentEvent
    seen = {}

    async def fake_run(task, context, ctx, model=None, **kw):
        seen["agents"] = ctx.agents
        yield AgentEvent(type="stories", stories=[{"title": "T"}])

    monkeypatch.setattr(ideate_api, "_run_agent", fake_run)
    r = _client().post("/api/ideate/agent/run",
                       json={"task": "draft", "context": "ctx", "project_key": "CGF",
                             "agents": [{"name": "Spec Writer", "path": "/tmp/spec"}]})
    assert r.status_code == 200
    assert seen["agents"] == [{"name": "Spec Writer", "path": "/tmp/spec"}]


def _story_payload(**over):
    base = {"title": "Old", "description": "d", "acceptance_criteria": [],
            "priority": "Medium", "labels": [], "issue_type": "Story",
            "epic_key": None, "story_points": None, "assignee": None, "components": []}
    base.update(over)
    return base


def test_agent_refine_returns_refined_story(monkeypatch):
    import src.services.agent_service as agent_service
    monkeypatch.setattr(
        agent_service, "test_agent",
        lambda path, message, timeout=120: {
            "ok": True,
            "response": '{"title": "Refined", "acceptance_criteria": ["a", "b"]}',
        })
    r = _client().post("/api/ideate/agent/refine", json={
        "story": _story_payload(),
        "agent": {"name": "Spec Writer", "path": "/tmp/spec"},
        "instruction": "add acceptance criteria",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["story"]["title"] == "Refined"
    assert data["story"]["acceptance_criteria"] == ["a", "b"]


def test_agent_refine_falls_back_to_prose(monkeypatch):
    import src.services.agent_service as agent_service
    monkeypatch.setattr(
        agent_service, "test_agent",
        lambda path, message, timeout=120: {"ok": True, "response": "just some prose, no json"})
    r = _client().post("/api/ideate/agent/refine", json={
        "story": _story_payload(description="orig"),
        "agent": {"name": "Spec Writer", "path": "/tmp/spec"},
        "instruction": "improve",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    # original title preserved; agent prose folded into description
    assert data["story"]["title"] == "Old"
    assert "just some prose" in data["story"]["description"]


def test_agent_refine_reports_agent_error(monkeypatch):
    import src.services.agent_service as agent_service
    monkeypatch.setattr(
        agent_service, "test_agent",
        lambda path, message, timeout=120: {"ok": False, "error": "kaboom"})
    r = _client().post("/api/ideate/agent/refine", json={
        "story": _story_payload(),
        "agent": {"name": "Spec Writer", "path": "/tmp/spec"},
        "instruction": "improve",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False and "kaboom" in data["error"]
