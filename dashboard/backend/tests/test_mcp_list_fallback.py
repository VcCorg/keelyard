"""list_mcp_servers() must fall back to the canonical catalog.

Without a fallback, a backend that can't find docker-compose.yml (frozen
desktop sidecar, containerized backend) reports zero MCPs on the Dashboard
and banner while the MCP page's Docker stack panel still reports 9. This
test pins the fallback so those two views can't diverge again.
"""

from src.services import mcp_service


def test_lists_canonical_catalog_when_compose_missing(monkeypatch):
    """No compose file + no registry → still show every canonical MCP."""
    monkeypatch.setattr(mcp_service, "_find_compose_file", lambda: None)
    # Neutralize the CLI registry so we only test the compose→catalog fallback.
    monkeypatch.setattr(
        "agentic_cli.mcp.config.get_merged_servers",
        lambda: {},
        raising=False,
    )
    servers = mcp_service.list_mcp_servers()
    names = {s.name for s in servers}
    # The MCP page's Docker panel iterates the same catalog — the two totals
    # must be identical.
    assert names == set(mcp_service._DESCRIPTIONS.keys())
    # Every canonical service gets a container_name + a well-known port.
    for s in servers:
        assert s.container_name == f"keel-{s.name}"
        assert s.port == mcp_service._MCP_PORTS.get(s.name)
        assert s.type == "docker"


def test_compose_file_still_wins_when_present(monkeypatch, tmp_path):
    """When compose parses successfully, its services (not the fallback) win."""
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        """
services:
  only-one-mcp:
    container_name: keel-only-one-mcp
    ports:
      - 8199:80
""".strip()
    )
    monkeypatch.setattr(mcp_service, "_find_compose_file", lambda: compose)
    monkeypatch.setattr(
        "agentic_cli.mcp.config.get_merged_servers",
        lambda: {},
        raising=False,
    )
    servers = mcp_service.list_mcp_servers()
    names = {s.name for s in servers}
    # Compose file has ONE service; catalog fallback must not stomp on it.
    assert names == {"only-one-mcp"}
