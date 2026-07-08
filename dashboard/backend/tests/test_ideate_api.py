from fastapi import FastAPI
from fastapi.testclient import TestClient
import src.api.ideate as ideate_api


def _client():
    app = FastAPI()
    app.include_router(ideate_api.router)
    return TestClient(app)


def test_push_endpoint(monkeypatch):
    seen = {}

    def fake(project_key, stories, actor=None):
        seen.update({"project": project_key, "n": len(stories), "actor": actor, "epic": stories[0].epic_key})
        return {"results": [{"title": "A", "ok": True, "key": "CGF-1"}], "created": 1, "correlation_id": "c1"}

    monkeypatch.setattr(ideate_api.svc, "push_stories", fake)
    r = _client().post("/api/ideate/push", json={"project_key": "CGF",
        "stories": [{"title": "A", "issue_type": "Story", "epic_key": "CGF-9", "acceptance_criteria": ["ac1"]}]},
        headers={"x-auth-request-email": "jdoe@x.com"})
    assert r.status_code == 200 and r.json()["created"] == 1
    assert seen["project"] == "CGF" and seen["epic"] == "CGF-9" and seen["actor"] == "jdoe@x.com"


def test_jira_meta_endpoint(monkeypatch):
    from src.services.jira_service import CreateMeta, JiraEpic
    import src.services.jira_service as js
    monkeypatch.setattr(js, "get_create_meta", lambda pk: CreateMeta(project_key=pk, issue_types=["Story", "Task"]))
    monkeypatch.setattr(js, "list_epics", lambda pk: [JiraEpic(key="CGF-1", summary="Epic One")])
    r = _client().get("/api/ideate/jira-meta?project=CGF")
    assert r.status_code == 200
    assert r.json()["issue_types"] == ["Story", "Task"] and r.json()["epics"][0]["key"] == "CGF-1"


def test_audit_endpoint(monkeypatch):
    monkeypatch.setattr(ideate_api, "_get_activity",
                        lambda command, limit: [{"subcommand": "jira_create", "status": "success"}])
    r = _client().get("/api/ideate/audit?limit=10")
    assert r.status_code == 200 and r.json()["actions"][0]["subcommand"] == "jira_create"
