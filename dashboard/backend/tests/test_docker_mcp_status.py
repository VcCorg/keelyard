"""Tests for the Docker MCP stack status (MCP page panel).

Running state is derived from TCP port reachability so it works even when the
backend can't reach the `docker` CLI. Tests stub both `_docker_available` and
`_check_port` for determinism (no real sockets / docker calls).
"""

from src.services import mcp_service as svc


def _no_ports(*_a, **_k):
    return (False, "closed")


def test_stack_down_lists_expected_services(monkeypatch):
    monkeypatch.setattr(svc, "_docker_available", lambda: (False, "Docker is not installed"))
    monkeypatch.setattr(svc, "_find_compose_file", lambda: None)
    monkeypatch.setattr(svc, "_get_docker_status", lambda: {})
    monkeypatch.setattr(svc, "_check_port", _no_ports)

    st = svc.get_docker_mcp_status()
    assert st.docker_available is False
    assert st.stack_reachable is False and st.running_count == 0
    names = {s.name for s in st.services}
    assert "jira-mcp" in names
    # Ports come from the canonical map even without a compose file.
    assert next(s for s in st.services if s.name == "jira-mcp").port == 8128
    assert all(s.status == "absent" and not s.running for s in st.services)


def test_reachable_port_marks_running_even_without_docker_cli(monkeypatch):
    """The reported bug: containers up, but the backend can't run `docker`."""
    monkeypatch.setattr(svc, "_docker_available", lambda: (False, "Docker is not installed"))
    monkeypatch.setattr(svc, "_find_compose_file", lambda: None)
    monkeypatch.setattr(svc, "_get_docker_status", lambda: {})
    # Only Jira's port responds.
    monkeypatch.setattr(svc, "_check_port",
                        lambda host, port, **k: (port == 8128, ""))

    st = svc.get_docker_mcp_status()
    assert st.docker_available is False           # CLI genuinely unavailable
    assert st.stack_reachable is True and st.running_count == 1
    jira = next(s for s in st.services if s.name == "jira-mcp")
    assert jira.running is True and jira.reachable is True and jira.status == "running"


def test_docker_cli_status_classifies_exited(monkeypatch):
    monkeypatch.setattr(svc, "_docker_available", lambda: (True, "Docker daemon is running"))
    monkeypatch.setattr(svc, "_find_compose_file", lambda: None)
    monkeypatch.setattr(svc, "_get_docker_status", lambda: {
        "keel-jira-mcp": "Up 3 minutes (healthy)",
        "keel-kg-mcp": "Exited (1) 2 minutes ago",
    })
    monkeypatch.setattr(svc, "_check_port", _no_ports)  # ports closed; rely on docker ps

    st = svc.get_docker_mcp_status()
    by = {s.name: s for s in st.services}
    assert by["jira-mcp"].running is True and by["jira-mcp"].status == "running"
    assert by["kg-mcp"].running is False and by["kg-mcp"].status == "exited"
    assert by["confluence-mcp"].status == "absent"


def test_endpoint_shape():
    from fastapi.testclient import TestClient
    from src.api.main import app

    r = TestClient(app).get("/api/mcp/docker")
    assert r.status_code == 200
    body = r.json()
    assert "stack_reachable" in body and "running_count" in body and "services" in body
    assert isinstance(body["services"], list)
