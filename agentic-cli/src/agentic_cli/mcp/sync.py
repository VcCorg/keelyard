"""IDE configuration sync for MCP servers."""

import json
import os
from pathlib import Path
from typing import Any, Optional

from agentic_cli.mcp.config import (
    MCPServer,
    MCPServerType,
    MCPTransport,
    get_merged_servers,
)


class IDEType:
    """Supported IDE types."""
    WINDSURF = "windsurf"
    CLAUDE = "claude"
    VSCODE = "vscode"
    CURSOR = "cursor"


# IDE configuration paths
IDE_CONFIG_PATHS = {
    IDEType.WINDSURF: {
        "global": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        "workspace": ".windsurf/mcp_config.json",
    },
    IDEType.CLAUDE: {
        "global": Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        "workspace": ".claude/settings.json",
    },
    IDEType.VSCODE: {
        "global": Path.home() / ".vscode" / "settings.json",
        "workspace": ".vscode/settings.json",
    },
    IDEType.CURSOR: {
        "global": Path.home() / ".cursor" / "mcp.json",
        "workspace": ".cursor/mcp.json",
    },
}


def _resolve_env_vars(env: dict[str, str]) -> dict[str, str]:
    """Resolve environment variable references like ${VAR}."""
    resolved = {}
    for key, value in env.items():
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            resolved[key] = os.environ.get(env_var, value)
        else:
            resolved[key] = value
    return resolved


def _server_to_windsurf(key: str, server: MCPServer) -> dict[str, Any]:
    """Convert MCPServer to Windsurf MCP config format."""
    config: dict[str, Any] = {
        "disabled": not server.enabled,
        "timeout": server.timeout,
    }
    
    if server.type == MCPServerType.STDIO:
        config["command"] = server.command
        config["args"] = server.args
        if server.env:
            config["env"] = _resolve_env_vars(server.env)
    
    elif server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        config["url"] = server.url
        config["transport"] = server.transport.value
    
    elif server.type == MCPServerType.DOCKER:
        # Docker servers expose HTTP endpoint
        port = server.docker.port if server.docker else 8125
        config["url"] = server.url or f"http://localhost:{port}"
        config["transport"] = "http"
    
    # Add metadata
    if server.description or server.tools:
        config["metadata"] = {}
        if server.name:
            config["metadata"]["name"] = server.name
        if server.description:
            config["metadata"]["description"] = server.description
        if server.tools:
            config["metadata"]["tools"] = server.tools
    
    return config


def _server_to_claude(key: str, server: MCPServer) -> dict[str, Any]:
    """Convert MCPServer to Claude Desktop config format."""
    config: dict[str, Any] = {}
    
    if server.type == MCPServerType.STDIO:
        config["command"] = server.command
        config["args"] = server.args
        if server.env:
            config["env"] = _resolve_env_vars(server.env)
    
    elif server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        config["url"] = server.url
        config["transport"] = server.transport.value
    
    elif server.type == MCPServerType.DOCKER:
        port = server.docker.port if server.docker else 8125
        config["url"] = server.url or f"http://localhost:{port}"
        config["transport"] = "http"
    
    return config


def _server_to_vscode(key: str, server: MCPServer) -> dict[str, Any]:
    """Convert MCPServer to VS Code MCP config format."""
    config: dict[str, Any] = {
        "name": server.name or key,
    }
    
    if server.type == MCPServerType.STDIO:
        config["command"] = server.command
        config["args"] = server.args
        if server.env:
            config["env"] = _resolve_env_vars(server.env)
    
    elif server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        config["url"] = server.url
        config["transport"] = server.transport.value
    
    elif server.type == MCPServerType.DOCKER:
        port = server.docker.port if server.docker else 8125
        config["url"] = server.url or f"http://localhost:{port}"
        config["transport"] = "http"
    
    return config


def generate_windsurf_config(servers: dict[str, MCPServer]) -> dict[str, Any]:
    """Generate Windsurf MCP configuration."""
    mcp_servers = {}
    for key, server in servers.items():
        if server.enabled:
            mcp_servers[key] = _server_to_windsurf(key, server)
    
    return {"mcpServers": mcp_servers}


def generate_claude_config(servers: dict[str, MCPServer]) -> dict[str, Any]:
    """Generate Claude Desktop configuration."""
    mcp_servers = {}
    for key, server in servers.items():
        if server.enabled:
            mcp_servers[key] = _server_to_claude(key, server)
    
    return {"mcpServers": mcp_servers}


def generate_vscode_config(servers: dict[str, MCPServer]) -> dict[str, Any]:
    """Generate VS Code MCP configuration."""
    mcp_servers = []
    for key, server in servers.items():
        if server.enabled:
            mcp_servers.append(_server_to_vscode(key, server))
    
    return {"mcp.servers": mcp_servers}


def generate_cursor_config(servers: dict[str, MCPServer]) -> dict[str, Any]:
    """Generate Cursor MCP configuration (same as Windsurf)."""
    return generate_windsurf_config(servers)


# Generator mapping
IDE_GENERATORS = {
    IDEType.WINDSURF: generate_windsurf_config,
    IDEType.CLAUDE: generate_claude_config,
    IDEType.VSCODE: generate_vscode_config,
    IDEType.CURSOR: generate_cursor_config,
}


def sync_to_ide(
    ide: str,
    workspace: Optional[Path] = None,
    global_config: bool = False,
) -> Path:
    """
    Sync MCP configuration to IDE-specific format.
    
    Args:
        ide: IDE type (windsurf, claude, vscode, cursor)
        workspace: Workspace path (uses cwd if None)
        global_config: If True, write to global IDE config instead of workspace
    
    Returns:
        Path to the generated config file
    """
    ide = ide.lower()
    if ide not in IDE_GENERATORS:
        raise ValueError(f"Unsupported IDE: {ide}. Supported: {list(IDE_GENERATORS.keys())}")
    
    # Get merged servers
    servers = get_merged_servers(workspace)
    
    # Generate config
    generator = IDE_GENERATORS[ide]
    config = generator(servers)
    
    # Determine output path
    paths = IDE_CONFIG_PATHS[ide]
    if global_config:
        output_path = paths["global"]
    else:
        base = workspace or Path.cwd()
        output_path = base / paths["workspace"]
    
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # For VS Code, merge with existing settings
    if ide == IDEType.VSCODE and output_path.exists():
        existing = json.loads(output_path.read_text())
        existing.update(config)
        config = existing
    
    # Write config
    output_path.write_text(json.dumps(config, indent=2))
    
    return output_path


def sync_all_ides(workspace: Optional[Path] = None) -> dict[str, Path]:
    """
    Sync MCP configuration to all supported IDEs.
    
    Returns:
        Dict mapping IDE name to generated config path
    """
    results = {}
    for ide in IDE_GENERATORS:
        try:
            path = sync_to_ide(ide, workspace)
            results[ide] = path
        except Exception as e:
            results[ide] = None
    return results


def import_from_ide(
    ide: str,
    source_path: Optional[Path] = None,
) -> dict[str, MCPServer]:
    """
    Import MCP servers from an IDE configuration file.
    
    Args:
        ide: IDE type
        source_path: Path to config file (uses default if None)
    
    Returns:
        Dict of imported MCPServer objects
    """
    ide = ide.lower()
    if ide not in IDE_CONFIG_PATHS:
        raise ValueError(f"Unsupported IDE: {ide}")
    
    # Determine source path
    if source_path is None:
        source_path = IDE_CONFIG_PATHS[ide]["global"]
    
    if not source_path.exists():
        raise FileNotFoundError(f"Config file not found: {source_path}")
    
    data = json.loads(source_path.read_text())
    servers = {}
    
    # Parse based on IDE format
    if ide in (IDEType.WINDSURF, IDEType.CLAUDE, IDEType.CURSOR):
        mcp_servers = data.get("mcpServers", {})
        for key, config in mcp_servers.items():
            server = _parse_windsurf_server(key, config)
            if server:
                servers[key] = server
    
    elif ide == IDEType.VSCODE:
        mcp_servers = data.get("mcp.servers", [])
        for config in mcp_servers:
            name = config.get("name", f"server_{len(servers)}")
            server = _parse_vscode_server(name, config)
            if server:
                servers[name] = server
    
    return servers


def _parse_windsurf_server(key: str, config: dict[str, Any]) -> Optional[MCPServer]:
    """Parse Windsurf/Claude server config to MCPServer."""
    if "command" in config:
        return MCPServer(
            name=config.get("metadata", {}).get("name", key),
            type=MCPServerType.STDIO,
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env", {}),
            enabled=not config.get("disabled", False),
            timeout=config.get("timeout", 30000),
            tools=config.get("metadata", {}).get("tools", []),
            description=config.get("metadata", {}).get("description"),
        )
    elif "url" in config:
        transport = config.get("transport", "http")
        return MCPServer(
            name=config.get("metadata", {}).get("name", key),
            type=MCPServerType.HTTP if transport == "http" else MCPServerType.SSE,
            url=config["url"],
            transport=MCPTransport(transport),
            enabled=not config.get("disabled", False),
            timeout=config.get("timeout", 30000),
            tools=config.get("metadata", {}).get("tools", []),
            description=config.get("metadata", {}).get("description"),
        )
    return None


def _parse_vscode_server(name: str, config: dict[str, Any]) -> Optional[MCPServer]:
    """Parse VS Code server config to MCPServer."""
    if "command" in config:
        return MCPServer(
            name=config.get("name", name),
            type=MCPServerType.STDIO,
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env", {}),
        )
    elif "url" in config:
        transport = config.get("transport", "http")
        return MCPServer(
            name=config.get("name", name),
            type=MCPServerType.HTTP if transport == "http" else MCPServerType.SSE,
            url=config["url"],
            transport=MCPTransport(transport),
        )
    return None
