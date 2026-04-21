"""Tests for MCP management commands and modules."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from dva_agentic_cli.main import app
from dva_agentic_cli.mcp.config import (
    MCPServer,
    MCPServerType,
    MCPTransport,
    MCPRegistry,
    MCPProjectConfig,
    DockerConfig,
    load_registry,
    save_registry,
    load_project_config,
    save_project_config,
    get_merged_servers,
    validate_server_config,
)
from dva_agentic_cli.mcp.sync import (
    generate_windsurf_config,
    generate_claude_config,
    generate_vscode_config,
    sync_to_ide,
    import_from_ide,
)
from dva_agentic_cli.mcp.health import (
    check_port_open,
    check_stdio_command,
    check_server_health,
)

runner = CliRunner()


class TestMCPConfig:
    """Tests for MCP configuration management."""

    def test_mcp_server_creation(self):
        """Test creating an MCPServer."""
        server = MCPServer(
            name="Test Server",
            type=MCPServerType.STDIO,
            command="python",
            args=["server.py"],
        )
        assert server.name == "Test Server"
        assert server.type == MCPServerType.STDIO
        assert server.command == "python"
        assert server.args == ["server.py"]
        assert server.enabled is True

    def test_mcp_server_docker(self):
        """Test creating a Docker MCPServer."""
        server = MCPServer(
            name="Docker Server",
            type=MCPServerType.DOCKER,
            docker=DockerConfig(
                compose_file="/path/to/docker-compose.yml",
                service="mcp-server",
                port=8125,
            ),
            url="http://localhost:8125",
        )
        assert server.type == MCPServerType.DOCKER
        assert server.docker.compose_file == "/path/to/docker-compose.yml"
        assert server.docker.port == 8125

    def test_mcp_server_http(self):
        """Test creating an HTTP MCPServer."""
        server = MCPServer(
            name="HTTP Server",
            type=MCPServerType.HTTP,
            url="http://localhost:8000",
            transport=MCPTransport.HTTP,
        )
        assert server.type == MCPServerType.HTTP
        assert server.url == "http://localhost:8000"

    def test_registry_save_load(self, tmp_path):
        """Test saving and loading registry."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                registry = MCPRegistry()
                registry.servers["test"] = MCPServer(
                    name="Test",
                    type=MCPServerType.STDIO,
                    command="python",
                    args=["test.py"],
                )
                save_registry(registry)
                
                loaded = load_registry()
                assert "test" in loaded.servers
                assert loaded.servers["test"].name == "Test"

    def test_project_config_save_load(self, tmp_path):
        """Test saving and loading project config."""
        config = MCPProjectConfig(
            inherit_global=True,
            servers={"local": {"enabled": True}},
        )
        path = save_project_config(config, tmp_path)
        assert path.exists()
        
        loaded = load_project_config(tmp_path)
        assert loaded is not None
        assert loaded.inherit_global is True
        assert "local" in loaded.servers

    def test_validate_stdio_server(self):
        """Test validation of STDIO server."""
        server = MCPServer(
            name="Test",
            type=MCPServerType.STDIO,
            command="python",
        )
        valid, msg = validate_server_config(server)
        assert valid is True

        server_no_cmd = MCPServer(
            name="Test",
            type=MCPServerType.STDIO,
        )
        valid, msg = validate_server_config(server_no_cmd)
        assert valid is False
        assert "command" in msg.lower()

    def test_validate_http_server(self):
        """Test validation of HTTP server."""
        server = MCPServer(
            name="Test",
            type=MCPServerType.HTTP,
            url="http://localhost:8000",
        )
        valid, msg = validate_server_config(server)
        assert valid is True

        server_no_url = MCPServer(
            name="Test",
            type=MCPServerType.HTTP,
        )
        valid, msg = validate_server_config(server_no_url)
        assert valid is False
        assert "url" in msg.lower()


class TestMCPSync:
    """Tests for IDE sync functionality."""

    def test_generate_windsurf_config(self):
        """Test generating Windsurf config."""
        servers = {
            "test": MCPServer(
                name="Test Server",
                type=MCPServerType.STDIO,
                command="python",
                args=["server.py"],
                enabled=True,
            ),
        }
        config = generate_windsurf_config(servers)
        assert "mcpServers" in config
        assert "test" in config["mcpServers"]
        assert config["mcpServers"]["test"]["command"] == "python"

    def test_generate_claude_config(self):
        """Test generating Claude config."""
        servers = {
            "http-server": MCPServer(
                name="HTTP Server",
                type=MCPServerType.HTTP,
                url="http://localhost:8000",
                enabled=True,
            ),
        }
        config = generate_claude_config(servers)
        assert "mcpServers" in config
        assert "http-server" in config["mcpServers"]
        assert config["mcpServers"]["http-server"]["url"] == "http://localhost:8000"

    def test_generate_vscode_config(self):
        """Test generating VS Code config."""
        servers = {
            "test": MCPServer(
                name="Test",
                type=MCPServerType.STDIO,
                command="node",
                args=["server.js"],
                enabled=True,
            ),
        }
        config = generate_vscode_config(servers)
        assert "mcp.servers" in config
        assert len(config["mcp.servers"]) == 1
        assert config["mcp.servers"][0]["command"] == "node"

    def test_disabled_server_excluded(self):
        """Test that disabled servers are excluded."""
        servers = {
            "enabled": MCPServer(
                name="Enabled",
                type=MCPServerType.STDIO,
                command="python",
                enabled=True,
            ),
            "disabled": MCPServer(
                name="Disabled",
                type=MCPServerType.STDIO,
                command="python",
                enabled=False,
            ),
        }
        config = generate_windsurf_config(servers)
        assert "enabled" in config["mcpServers"]
        assert "disabled" not in config["mcpServers"]

    def test_sync_to_ide(self, tmp_path):
        """Test syncing to IDE config file."""
        with patch("dva_agentic_cli.mcp.sync.get_merged_servers") as mock_servers:
            mock_servers.return_value = {
                "test": MCPServer(
                    name="Test",
                    type=MCPServerType.STDIO,
                    command="python",
                    enabled=True,
                ),
            }
            path = sync_to_ide("windsurf", tmp_path)
            assert path.exists()
            
            config = json.loads(path.read_text())
            assert "mcpServers" in config


class TestMCPHealth:
    """Tests for health check functionality."""

    def test_check_stdio_command_python(self):
        """Test checking Python command."""
        success, msg = check_stdio_command("python")
        # Should succeed if Python is installed
        assert isinstance(success, bool)
        assert isinstance(msg, str)

    def test_check_stdio_command_nonexistent(self):
        """Test checking non-existent command."""
        success, msg = check_stdio_command("nonexistent_command_xyz")
        assert success is False
        assert "not found" in msg.lower()

    def test_check_server_health_disabled(self):
        """Test health check for disabled server."""
        server = MCPServer(
            name="Disabled",
            type=MCPServerType.STDIO,
            command="python",
            enabled=False,
        )
        result = check_server_health(server)
        assert result["status"] == "disabled"
        assert result["healthy"] is False


class TestMCPCommands:
    """Tests for MCP CLI commands."""

    def test_mcp_help(self):
        """Test mcp --help."""
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "mcp" in result.output.lower()

    def test_mcp_init(self, tmp_path):
        """Test mcp init command."""
        result = runner.invoke(app, ["mcp", "init", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / ".mcp" / "mcp.json").exists()

    def test_mcp_init_already_exists(self, tmp_path):
        """Test mcp init when config already exists."""
        # First init
        runner.invoke(app, ["mcp", "init", "--workspace", str(tmp_path)])
        # Second init without force
        result = runner.invoke(app, ["mcp", "init", "--workspace", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output.lower()

    def test_mcp_init_force(self, tmp_path):
        """Test mcp init --force."""
        runner.invoke(app, ["mcp", "init", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["mcp", "init", "--workspace", str(tmp_path), "--force"])
        assert result.exit_code == 0

    def test_mcp_list_empty(self, tmp_path):
        """Test mcp list with no servers."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                result = runner.invoke(app, ["mcp", "list"])
                assert result.exit_code == 0
                assert "no mcp servers" in result.output.lower()

    def test_mcp_add_stdio(self, tmp_path):
        """Test adding a STDIO server."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                result = runner.invoke(app, [
                    "mcp", "add", "test-server",
                    "--type", "stdio",
                    "--command", "python",
                    "--args", "server.py",
                    "--name", "Test Server",
                ])
                assert result.exit_code == 0
                assert "added" in result.output.lower()

    def test_mcp_add_http(self, tmp_path):
        """Test adding an HTTP server."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                result = runner.invoke(app, [
                    "mcp", "add", "http-server",
                    "--type", "http",
                    "--url", "http://localhost:8000",
                ])
                assert result.exit_code == 0

    def test_mcp_add_docker(self, tmp_path):
        """Test adding a Docker server."""
        # Create a fake compose file
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("services:\n  test:\n    image: test")
        
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                result = runner.invoke(app, [
                    "mcp", "add", "docker-server",
                    "--type", "docker",
                    "--compose", str(compose_file),
                    "--port", "8125",
                ])
                assert result.exit_code == 0

    def test_mcp_add_missing_command(self, tmp_path):
        """Test adding STDIO server without command."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                result = runner.invoke(app, [
                    "mcp", "add", "test",
                    "--type", "stdio",
                ])
                assert result.exit_code == 1
                assert "require" in result.output.lower()

    def test_mcp_remove(self, tmp_path):
        """Test removing a server."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Add first
                runner.invoke(app, [
                    "mcp", "add", "to-remove",
                    "--type", "stdio",
                    "--command", "python",
                ])
                # Remove
                result = runner.invoke(app, ["mcp", "remove", "to-remove", "--yes"])
                assert result.exit_code == 0
                assert "removed" in result.output.lower()

    def test_mcp_remove_not_found(self, tmp_path):
        """Test removing non-existent server."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                result = runner.invoke(app, ["mcp", "remove", "nonexistent", "--yes"])
                assert result.exit_code == 1
                assert "not found" in result.output.lower()

    def test_mcp_show(self, tmp_path):
        """Test showing server details."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Add first
                runner.invoke(app, [
                    "mcp", "add", "show-test",
                    "--type", "stdio",
                    "--command", "python",
                    "--args", "server.py",
                    "--description", "Test description",
                ])
                # Show
                result = runner.invoke(app, ["mcp", "show", "show-test"])
                assert result.exit_code == 0
                assert "show-test" in result.output.lower() or "Server" in result.output

    def test_mcp_list_json(self, tmp_path):
        """Test mcp list --json."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Add a server
                runner.invoke(app, [
                    "mcp", "add", "json-test",
                    "--type", "stdio",
                    "--command", "python",
                ])
                # List as JSON
                result = runner.invoke(app, ["mcp", "list", "--json"])
                assert result.exit_code == 0
                data = json.loads(result.output)
                assert "json-test" in data

    def test_mcp_sync_windsurf(self, tmp_path):
        """Test syncing to Windsurf."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Add a server
                runner.invoke(app, [
                    "mcp", "add", "sync-test",
                    "--type", "stdio",
                    "--command", "python",
                ])
                # Sync
                result = runner.invoke(app, [
                    "mcp", "sync",
                    "--ide", "windsurf",
                    "--workspace", str(tmp_path),
                ])
                assert result.exit_code == 0
                assert (tmp_path / ".windsurf" / "mcp_config.json").exists()

    def test_mcp_health(self, tmp_path):
        """Test health check command."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Add a server
                runner.invoke(app, [
                    "mcp", "add", "health-test",
                    "--type", "stdio",
                    "--command", "python",
                ])
                # Check health
                result = runner.invoke(app, ["mcp", "health"])
                assert result.exit_code == 0


class TestMergedServers:
    """Tests for server merging logic."""

    def test_merge_global_only(self, tmp_path):
        """Test merging with only global servers."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                registry = MCPRegistry()
                registry.servers["global"] = MCPServer(
                    name="Global",
                    type=MCPServerType.STDIO,
                    command="python",
                )
                save_registry(registry)
                
                servers = get_merged_servers(tmp_path)
                assert "global" in servers

    def test_merge_project_override(self, tmp_path):
        """Test project config overriding global."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Global server
                registry = MCPRegistry()
                registry.servers["test"] = MCPServer(
                    name="Global Test",
                    type=MCPServerType.STDIO,
                    command="python",
                    enabled=True,
                )
                save_registry(registry)
                
                # Project override - disable it
                project_config = MCPProjectConfig(
                    inherit_global=True,
                    servers={"test": {"enabled": False}},
                )
                save_project_config(project_config, tmp_path)
                
                servers = get_merged_servers(tmp_path)
                # Disabled servers are filtered out
                assert "test" not in servers

    def test_merge_no_inherit(self, tmp_path):
        """Test project config without inheriting global."""
        with patch("dva_agentic_cli.mcp.config.MCP_DIR", tmp_path):
            with patch("dva_agentic_cli.mcp.config.REGISTRY_FILE", tmp_path / "registry.json"):
                # Global server
                registry = MCPRegistry()
                registry.servers["global"] = MCPServer(
                    name="Global",
                    type=MCPServerType.STDIO,
                    command="python",
                )
                save_registry(registry)
                
                # Project config - don't inherit
                project_config = MCPProjectConfig(
                    inherit_global=False,
                    servers={
                        "local": {
                            "name": "Local Only",
                            "type": "stdio",
                            "command": "node",
                            "enabled": True,
                        }
                    },
                )
                save_project_config(project_config, tmp_path)
                
                servers = get_merged_servers(tmp_path)
                assert "global" not in servers
                assert "local" in servers
