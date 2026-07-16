"""Tests for dashboard MCP server registration (CRUD over the CLI registry)."""

import pytest

from src.services.mcp_service import (
    MCPServerInfo,
    MCPServerUpsert,
    _probe_target,
    add_mcp_server,
    remove_mcp_server,
    update_mcp_server,
)


@pytest.fixture()
def tmp_registry(tmp_path, monkeypatch):
    """Point the CLI MCP registry at a temp dir so tests never touch ~."""
    from agentic_cli.mcp import config as mcp_config

    mcp_dir = tmp_path / "mcp"
    monkeypatch.setattr(mcp_config, "MCP_DIR", mcp_dir)
    monkeypatch.setattr(mcp_config, "REGISTRY_FILE", mcp_dir / "registry.json")
    return mcp_dir


def test_add_lists_and_removes_registry_server(tmp_registry):
    info = add_mcp_server(MCPServerUpsert(
        name="Team Jira", url="https://mcp.example.com:8128/sse",
        description="Shared Jira MCP", type="sse"))
    assert info.name == "team-jira"          # slugified
    assert info.source == "registry"
    assert info.url == "https://mcp.example.com:8128/sse"

    assert remove_mcp_server("team-jira") is True


def test_add_rejects_duplicates_and_bad_types(tmp_registry):
    add_mcp_server(MCPServerUpsert(name="gw", url="http://h:9090/sse"))
    with pytest.raises(ValueError, match="already exists"):
        add_mcp_server(MCPServerUpsert(name="gw", url="http://h:9090/sse"))
    with pytest.raises(ValueError, match="sse.*http|stdio"):
        add_mcp_server(MCPServerUpsert(name="x", url="ignored", type="stdio"))
    with pytest.raises(ValueError, match="required"):
        add_mcp_server(MCPServerUpsert(name="   ", url="http://h/sse"))


def test_update_changes_url_and_enabled(tmp_registry):
    add_mcp_server(MCPServerUpsert(name="gw", url="http://old:9090/sse"))
    info = update_mcp_server("gw", MCPServerUpsert(
        name="gw", url="http://new:9191/sse", enabled=False))
    assert info.url == "http://new:9191/sse"
    assert info.enabled is False


def test_update_and_remove_unknown_raise_keyerror(tmp_registry):
    with pytest.raises(KeyError):
        update_mcp_server("nope", MCPServerUpsert(name="nope", url="http://h/sse"))
    with pytest.raises(KeyError):
        remove_mcp_server("nope")


def test_probe_target_uses_url_host_for_remote_servers():
    """Health checks must probe the URL's host, not hardcoded localhost."""
    remote = MCPServerInfo(name="r", type="sse",
                           url="https://mcp.corp.example:8128/sse", port=8128)
    assert _probe_target(remote) == ("mcp.corp.example", 8128)

    # Scheme default port when none is declared anywhere.
    https_default = MCPServerInfo(name="r2", type="sse",
                                  url="https://mcp.corp.example/sse")
    assert _probe_target(https_default) == ("mcp.corp.example", 443)

    # Docker-style entries (no URL host beyond localhost) keep localhost:port.
    docker = MCPServerInfo(name="d", type="docker",
                           url="http://localhost:8128/sse", port=8128)
    assert _probe_target(docker) == ("localhost", 8128)

    no_url = MCPServerInfo(name="n", type="docker", port=9090)
    assert _probe_target(no_url) == ("localhost", 9090)
