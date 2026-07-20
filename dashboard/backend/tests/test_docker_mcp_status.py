"""Tests for the Docker MCP stack status (MCP page panel)."""

from src.services import mcp_service as svc


def test_docker_unavailable_lists_expected_services(monkeypatch):
    monkeypatch.setattr(svc, "_docker_available", lambda: (False, "Docker is not installed"))
    monkeypatch.setattr(svc, "_find_compose_file", lambda: None)
    monkeypatch.setattr(svc, "_get_docker_status", lambda: {})

    st = svc.get_docker_mcp_status()
    assert st.docker_available is False
    assert "not installed" in st.docker_message
    # Falls back to the canonical MCP service set, all absent.
    names = {s.name for s in st.services}
    assert "jira-mcp" in names
    assert all(s.status == "absent" and not s.running for s in st.services)


def test_running_and_exited_containers_are_classified(monkeypatch):
    monkeypatch.setattr(svc, "_docker_available", lambda: (True, "Docker daemon is running"))
    monkeypatch.setattr(svc, "_find_compose_file", lambda: None)
    monkeypatch.setattr(svc, "_get_docker_status", lambda: {
        "keel-jira-mcp": "Up 3 minutes (healthy)",
        "keel-kg-mcp": "Exited (1) 2 minutes ago",
    })

    st = svc.get_docker_mcp_status()
    by = {s.name: s for s in st.services}
    assert by["jira-mcp"].running is True and by["jira-mcp"].status == "running"
    assert by["kg-mcp"].running is False and by["kg-mcp"].status == "exited"
    # A service with no container is absent.
    assert by["confluence-mcp"].status == "absent"


def test_endpoint_shape():
    from fastapi.testclient import TestClient
    from src.api.main import app

    r = TestClient(app).get("/api/mcp/docker")
    assert r.status_code == 200
    body = r.json()
    assert "docker_available" in body and "services" in body
    assert isinstance(body["services"], list)
