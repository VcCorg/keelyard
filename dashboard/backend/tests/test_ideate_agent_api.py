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
