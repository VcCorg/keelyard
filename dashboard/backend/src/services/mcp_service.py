"""MCP server service — discovers Docker MCP containers, checks health.

Primary source of truth: docker-compose.yml in dva-mcp-servers/
Enriches with CLI registry metadata when available.
"""

import json
import logging
import socket
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Friendly descriptions for known MCP services
_DESCRIPTIONS = {
    "bitbucket-mcp": "Bitbucket Server — PR review, comments, merge",
    "glean-mcp": "Glean — enterprise search & AI assistants",
    "jira-mcp": "Jira Server — issues, sprints, transitions",
    "confluence-mcp": "Confluence Server — pages, spaces, search",
    "memory-mcp": "Neo4j Agent Memory — short/long-term + reasoning",
    "kg-mcp": "Knowledge Graph — business context & requirements",
    "mcp-gateway": "Unified gateway aggregating all MCP tools",
    "mcp-proxy": "Named-server proxy (Bitbucket + Jira stdio)",
}


class MCPServerInfo(BaseModel):
    """MCP server summary for the dashboard."""
    name: str
    type: str  # stdio, http, docker, sse
    enabled: bool = True
    url: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    tools: list[str] = []
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    health_message: str = ""
    container_name: Optional[str] = None
    container_status: Optional[str] = None


class MCPHealthResult(BaseModel):
    """Health check result for a single server."""
    name: str
    healthy: bool
    message: str


def _check_port(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    """Quick TCP port check."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Port {port} is open"
    except OSError as e:
        return False, f"Port {port} unreachable: {e}"


def _get_docker_status() -> dict[str, str]:
    """Get container name → status mapping for dva- containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=dva-", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return {}
        mapping = {}
        for line in result.stdout.strip().split("\n"):
            if "\t" in line:
                name, status = line.split("\t", 1)
                mapping[name] = status
        return mapping
    except Exception:
        return {}


def list_mcp_servers() -> list[MCPServerInfo]:
    """Discover MCP servers from docker-compose.yml + running containers."""
    compose_path = _find_compose_file()
    servers: dict[str, MCPServerInfo] = {}

    # Primary: parse docker-compose.yml
    if compose_path and compose_path.exists():
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None

        if yaml:
            try:
                with open(compose_path) as f:
                    data = yaml.safe_load(f)
                for svc_name, svc_data in data.get("services", {}).items():
                    ports = svc_data.get("ports", [])
                    port = None
                    if ports:
                        port_str = str(ports[0]).split(":")[0]
                        port = int(port_str)
                    container = svc_data.get("container_name", f"dva-{svc_name}")
                    servers[svc_name] = MCPServerInfo(
                        name=svc_name,
                        type="docker",
                        url=f"http://localhost:{port}/sse" if port else None,
                        port=port,
                        description=_DESCRIPTIONS.get(svc_name, ""),
                        container_name=container,
                    )
            except Exception as e:
                logger.warning("Failed to parse docker-compose.yml: %s", e)

    # Enrich with CLI registry metadata (tools list, descriptions)
    # CLI keys like "jira" match Docker keys like "jira-mcp"
    try:
        from dva_agentic_cli.mcp.config import get_merged_servers
        for key, srv in get_merged_servers().items():
            # Match by exact key or by "{key}-mcp" docker convention
            docker_key = f"{key}-mcp" if f"{key}-mcp" in servers else None
            match_key = key if key in servers else docker_key
            if match_key:
                if srv.tools:
                    servers[match_key].tools = srv.tools
                if srv.description and not servers[match_key].description:
                    servers[match_key].description = srv.description
            else:
                # Only add if not a duplicate of a Docker service
                port = None
                if srv.docker:
                    port = srv.docker.port
                elif srv.url:
                    try:
                        from urllib.parse import urlparse
                        port = urlparse(srv.url).port
                    except Exception:
                        pass
                servers[key] = MCPServerInfo(
                    name=key,
                    type=srv.type.value,
                    enabled=srv.enabled,
                    url=srv.url,
                    port=port,
                    description=srv.description or "",
                    tools=srv.tools,
                )
    except (ImportError, Exception) as e:
        logger.debug("CLI registry not available: %s", e)

    return list(servers.values())


def check_health(name: Optional[str] = None) -> list[MCPHealthResult]:
    """Check health of MCP servers via port check + Docker status."""
    servers = list_mcp_servers()
    docker_status = _get_docker_status()
    results = []

    for srv in servers:
        if name and srv.name != name:
            continue

        # Check port connectivity
        if srv.port:
            ok, msg = _check_port("localhost", srv.port)
            # Append container status if available
            cname = srv.container_name or f"dva-{srv.name}"
            cstatus = docker_status.get(cname, "")
            if cstatus:
                msg = f"{msg} ({cstatus})"
                srv.container_status = cstatus
            results.append(MCPHealthResult(name=srv.name, healthy=ok, message=msg))
        else:
            results.append(MCPHealthResult(name=srv.name, healthy=False, message="No port configured"))

    return results


def start_mcp_server(name: str) -> bool:
    """Start a Docker-based MCP server."""
    compose_path = _find_compose_file()
    if not compose_path:
        raise RuntimeError("docker-compose.yml not found")

    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "up", "-d", name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def stop_mcp_server(name: str) -> bool:
    """Stop a Docker-based MCP server."""
    compose_path = _find_compose_file()
    if not compose_path:
        raise RuntimeError("docker-compose.yml not found")

    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "stop", name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def get_mcp_logs(name: str, tail: int = 100) -> list[str]:
    """Get Docker logs for an MCP server."""
    compose_path = _find_compose_file()
    if not compose_path:
        return []

    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "logs", "--tail", str(tail), "--no-color", name],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    return []


def _find_compose_file() -> Optional[Path]:
    """Find the MCP docker-compose.yml."""
    # Try workspace-relative path
    workspace = Path(__file__).resolve().parents[4]
    candidates = [
        workspace / "mcp-servers" / "docker-compose.yml",
        workspace / "dva-mcp-servers" / "docker-compose.yml",
    ]

    # Also check MCP registry for docker compose paths
    try:
        from dva_agentic_cli.mcp.config import load_registry
        registry = load_registry()
        for server in registry.servers.values():
            if server.docker and server.docker.compose_file:
                candidates.append(Path(server.docker.compose_file).expanduser())
    except (ImportError, Exception):
        pass

    for path in candidates:
        if path.exists():
            return path
    return None
