"""jira_service routes all Jira access through the Jira MCP server."""
import src.services.jira_service as js


def test_get_create_meta_uses_mcp(monkeypatch):
    calls = {}
    raw = {"projects": [{"key": "CGF", "issuetypes": [
        {"name": "Story", "fields": {"components": {"name": "Components"}}}]}]}
    def fake_call_tool(tool, args):
        calls["c"] = (tool, args)
        return raw

    monkeypatch.setattr(js, "is_configured", lambda: True)
    monkeypatch.setattr(js, "_call_tool", fake_call_tool)
    meta = js.get_create_meta("CGF")
    assert calls["c"] == ("get_create_meta", {"project_key": "CGF"})
    assert meta.issue_types == ["Story"] and meta.has_components is True


def test_get_create_meta_swallows_errors(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)

    def boom(tool, args):
        raise RuntimeError("mcp down")

    monkeypatch.setattr(js, "_call_tool", boom)
    meta = js.get_create_meta("CGF")
    assert meta.project_key == "CGF" and meta.issue_types == []


def test_list_epics_uses_search_tool(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)
    monkeypatch.setattr(js, "_call_tool", lambda tool, args: {
        "issues": [{"key": "CGF-1", "summary": "Epic One"}]})
    epics = js.list_epics("CGF")
    assert epics[0].key == "CGF-1" and epics[0].summary == "Epic One"


def test_list_my_domain_issues_maps_mcp_shape(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)
    monkeypatch.setattr(js, "_domain_project_keys", lambda: ["CGF"])
    monkeypatch.setattr(js, "_call_tool", lambda tool, args: {
        "total": 1,
        "issues": [{
            "key": "CGF-9", "summary": "Do a thing", "status": "In Progress",
            "status_category": "In Progress", "priority": "High", "issuetype": "Story",
            "project": "CGF", "created": "c", "updated": "u", "labels": ["x"],
            "link": "https://jira.example/browse/CGF-9",
        }],
    })
    resp = js.list_my_domain_issues()
    assert resp.configured and resp.total == 1
    i = resp.issues[0]
    assert i.key == "CGF-9" and i.status_category == "In Progress"
    assert i.project == "CGF" and i.link.endswith("/CGF-9")


def test_list_my_domain_issues_surfaces_error(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)
    monkeypatch.setattr(js, "_domain_project_keys", lambda: ["CGF"])

    def boom(tool, args):
        raise RuntimeError("Jira MCP tool 'search_issues' failed")

    monkeypatch.setattr(js, "_call_tool", boom)
    resp = js.list_my_domain_issues()
    assert resp.configured and resp.error and "search_issues" in resp.error


def test_get_issue_maps_nested_project(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)
    monkeypatch.setattr(js, "_call_tool", lambda tool, args: {
        "key": "CGF-3", "summary": "S", "status": "Open", "status_category": "To Do",
        "priority": "Low", "issuetype": "Bug", "project": {"key": "CGF", "name": "Coag"},
        "created": "c", "updated": "u", "labels": [], "description": "desc",
        "link": "https://jira.example/browse/CGF-3",
    })
    detail = js.get_issue("CGF-3")
    assert detail is not None
    assert detail.project == "CGF" and detail.description == "desc"


def test_get_issue_404_returns_none(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)

    def not_found(tool, args):
        raise RuntimeError("Client error '404 Not Found'")

    monkeypatch.setattr(js, "_call_tool", not_found)
    assert js.get_issue("CGF-404") is None
