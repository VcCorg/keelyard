"""MCP configuration management."""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class MCPServerType(str, Enum):
    """MCP server types."""
    STDIO = "stdio"
    HTTP = "http"
    DOCKER = "docker"
    SSE = "sse"


class MCPTransport(str, Enum):
    """MCP transport protocols."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class DockerConfig(BaseModel):
    """Docker-specific configuration."""
    compose_file: str = Field(..., description="Path to docker-compose.yml")
    service: Optional[str] = Field(None, description="Service name in compose file")
    port: int = Field(8125, description="Exposed port")
    network: Optional[str] = Field(None, description="Docker network name")


class MCPServer(BaseModel):
    """MCP server configuration."""
    name: str = Field(..., description="Display name")
    type: MCPServerType = Field(..., description="Server type")
    enabled: bool = Field(True, description="Whether server is enabled")
    
    # For stdio servers
    command: Optional[str] = Field(None, description="Command to run")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    
    # For HTTP/SSE servers
    url: Optional[str] = Field(None, description="Server URL")
    transport: MCPTransport = Field(MCPTransport.STDIO, description="Transport protocol")
    
    # For Docker servers
    docker: Optional[DockerConfig] = Field(None, description="Docker configuration")
    
    # Common
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    tools: list[str] = Field(default_factory=list, description="Available tools")
    timeout: int = Field(30000, description="Timeout in milliseconds")
    
    # Metadata
    description: Optional[str] = Field(None, description="Server description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    def model_post_init(self, __context: Any) -> None:
        """Set timestamps if not provided."""
        now = datetime.now(timezone.utc).isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now


class MCPRegistry(BaseModel):
    """Global MCP server registry."""
    version: str = Field("1.0", description="Registry version")
    servers: dict[str, MCPServer] = Field(default_factory=dict, description="Registered servers")


class MCPProjectConfig(BaseModel):
    """Project-level MCP configuration."""
    version: str = Field("1.0", description="Config version")
    inherit_global: bool = Field(True, description="Inherit global servers")
    servers: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Project servers")


# Configuration paths
CONFIG_DIR = Path.home() / ".dva-agentic"
MCP_DIR = CONFIG_DIR / "mcp"
REGISTRY_FILE = MCP_DIR / "registry.json"

# Project config filename
PROJECT_MCP_DIR = ".mcp"
PROJECT_MCP_FILE = "mcp.json"


def ensure_mcp_dir() -> Path:
    """Ensure MCP configuration directory exists."""
    MCP_DIR.mkdir(parents=True, exist_ok=True)
    return MCP_DIR


def load_registry() -> MCPRegistry:
    """Load global MCP registry."""
    if REGISTRY_FILE.exists():
        data = json.loads(REGISTRY_FILE.read_text())
        # Convert server dicts to MCPServer objects
        servers = {}
        for key, server_data in data.get("servers", {}).items():
            # Handle docker config
            if "docker" in server_data and server_data["docker"]:
                server_data["docker"] = DockerConfig(**server_data["docker"])
            servers[key] = MCPServer(**server_data)
        return MCPRegistry(version=data.get("version", "1.0"), servers=servers)
    return MCPRegistry()


def save_registry(registry: MCPRegistry) -> None:
    """Save global MCP registry."""
    ensure_mcp_dir()
    data = {
        "version": registry.version,
        "servers": {
            key: server.model_dump(exclude_none=True)
            for key, server in registry.servers.items()
        }
    }
    REGISTRY_FILE.write_text(json.dumps(data, indent=2))


def get_project_mcp_path(workspace: Optional[Path] = None) -> Path:
    """Get project MCP config path."""
    base = workspace or Path.cwd()
    return base / PROJECT_MCP_DIR / PROJECT_MCP_FILE


def load_project_config(workspace: Optional[Path] = None) -> Optional[MCPProjectConfig]:
    """Load project-level MCP configuration."""
    config_path = get_project_mcp_path(workspace)
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return MCPProjectConfig(**data)
    return None


def save_project_config(config: MCPProjectConfig, workspace: Optional[Path] = None) -> Path:
    """Save project-level MCP configuration."""
    base = workspace or Path.cwd()
    mcp_dir = base / PROJECT_MCP_DIR
    mcp_dir.mkdir(parents=True, exist_ok=True)
    config_path = mcp_dir / PROJECT_MCP_FILE
    config_path.write_text(json.dumps(config.model_dump(), indent=2))
    return config_path


def get_merged_servers(workspace: Optional[Path] = None) -> dict[str, MCPServer]:
    """
    Get merged servers from global registry and project config.
    
    Project config can:
    - Enable/disable global servers
    - Override global server settings
    - Add project-specific servers
    """
    # Start with global registry
    registry = load_registry()
    servers = dict(registry.servers)
    
    # Load project config
    project_config = load_project_config(workspace)
    if project_config is None:
        return servers
    
    if not project_config.inherit_global:
        servers = {}
    
    # Apply project overrides
    for key, overrides in project_config.servers.items():
        if key in servers:
            # Update existing server
            server_data = servers[key].model_dump()
            server_data.update(overrides)
            # Handle docker config
            if "docker" in server_data and isinstance(server_data["docker"], dict):
                server_data["docker"] = DockerConfig(**server_data["docker"])
            servers[key] = MCPServer(**server_data)
        else:
            # Add new project-specific server
            if "docker" in overrides and isinstance(overrides["docker"], dict):
                overrides["docker"] = DockerConfig(**overrides["docker"])
            servers[key] = MCPServer(**overrides)
    
    # Filter out disabled servers
    return {k: v for k, v in servers.items() if v.enabled}


def validate_server_config(server: MCPServer) -> tuple[bool, str]:
    """
    Validate server configuration.
    
    Returns:
        (is_valid, message)
    """
    if server.type == MCPServerType.STDIO:
        if not server.command:
            return False, "STDIO server requires 'command'"
    
    elif server.type == MCPServerType.HTTP or server.type == MCPServerType.SSE:
        if not server.url:
            return False, f"{server.type.value.upper()} server requires 'url'"
    
    elif server.type == MCPServerType.DOCKER:
        if not server.docker:
            return False, "Docker server requires 'docker' configuration"
        if not server.docker.compose_file:
            return False, "Docker server requires 'compose_file'"
        compose_path = Path(server.docker.compose_file).expanduser()
        if not compose_path.exists():
            return False, f"Docker compose file not found: {compose_path}"
    
    return True, "Valid configuration"
