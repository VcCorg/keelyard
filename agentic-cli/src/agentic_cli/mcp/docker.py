"""Docker operations for MCP servers."""

import subprocess
from pathlib import Path
from typing import Optional

from agentic_cli.mcp.config import (
    MCPServer,
    MCPServerType,
    get_merged_servers,
)


class DockerError(Exception):
    """Docker operation error."""
    pass


def check_docker_available() -> tuple[bool, str]:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "Docker command failed"
    except FileNotFoundError:
        return False, "Docker not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except Exception as e:
        return False, str(e)


def check_docker_running() -> tuple[bool, str]:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "Docker daemon is running"
        return False, result.stderr.strip() or "Docker daemon not running"
    except Exception as e:
        return False, str(e)


def get_docker_servers(workspace: Optional[Path] = None) -> dict[str, MCPServer]:
    """Get all Docker-based MCP servers."""
    servers = get_merged_servers(workspace)
    return {k: v for k, v in servers.items() if v.type == MCPServerType.DOCKER}


def start_server(server: MCPServer, detach: bool = True) -> tuple[bool, str]:
    """
    Start a Docker-based MCP server.
    
    Args:
        server: MCPServer with Docker configuration
        detach: Run in detached mode
    
    Returns:
        (success, message)
    """
    if server.type != MCPServerType.DOCKER:
        return False, f"Server '{server.name}' is not a Docker server"
    
    if not server.docker:
        return False, f"Server '{server.name}' has no Docker configuration"
    
    compose_path = Path(server.docker.compose_file).expanduser().resolve()
    if not compose_path.exists():
        return False, f"Docker compose file not found: {compose_path}"
    
    cmd = ["docker", "compose", "-f", str(compose_path), "up"]
    if detach:
        cmd.append("-d")
    
    if server.docker.service:
        cmd.append(server.docker.service)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=compose_path.parent,
        )
        if result.returncode == 0:
            return True, f"Started server '{server.name}'"
        return False, result.stderr.strip() or "Failed to start server"
    except subprocess.TimeoutExpired:
        return False, "Docker compose timed out"
    except Exception as e:
        return False, str(e)


def stop_server(server: MCPServer) -> tuple[bool, str]:
    """
    Stop a Docker-based MCP server.
    
    Args:
        server: MCPServer with Docker configuration
    
    Returns:
        (success, message)
    """
    if server.type != MCPServerType.DOCKER:
        return False, f"Server '{server.name}' is not a Docker server"
    
    if not server.docker:
        return False, f"Server '{server.name}' has no Docker configuration"
    
    compose_path = Path(server.docker.compose_file).expanduser().resolve()
    if not compose_path.exists():
        return False, f"Docker compose file not found: {compose_path}"
    
    cmd = ["docker", "compose", "-f", str(compose_path), "down"]
    
    if server.docker.service:
        cmd.append(server.docker.service)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=compose_path.parent,
        )
        if result.returncode == 0:
            return True, f"Stopped server '{server.name}'"
        return False, result.stderr.strip() or "Failed to stop server"
    except subprocess.TimeoutExpired:
        return False, "Docker compose timed out"
    except Exception as e:
        return False, str(e)


def restart_server(server: MCPServer) -> tuple[bool, str]:
    """
    Restart a Docker-based MCP server.
    
    Args:
        server: MCPServer with Docker configuration
    
    Returns:
        (success, message)
    """
    success, msg = stop_server(server)
    if not success:
        return False, f"Failed to stop: {msg}"
    
    return start_server(server)


def get_server_status(server: MCPServer) -> tuple[str, str]:
    """
    Get status of a Docker-based MCP server.
    
    Args:
        server: MCPServer with Docker configuration
    
    Returns:
        (status, details) where status is 'running', 'stopped', 'error', or 'unknown'
    """
    if server.type != MCPServerType.DOCKER:
        return "unknown", "Not a Docker server"
    
    if not server.docker:
        return "error", "No Docker configuration"
    
    compose_path = Path(server.docker.compose_file).expanduser().resolve()
    if not compose_path.exists():
        return "error", f"Compose file not found: {compose_path}"
    
    cmd = ["docker", "compose", "-f", str(compose_path), "ps", "--format", "json"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=compose_path.parent,
        )
        
        if result.returncode != 0:
            return "error", result.stderr.strip()
        
        output = result.stdout.strip()
        if not output:
            return "stopped", "No containers running"
        
        # Parse JSON output (one object per line)
        import json
        for line in output.split("\n"):
            if line.strip():
                try:
                    container = json.loads(line)
                    state = container.get("State", "").lower()
                    name = container.get("Name", "")
                    
                    # Check if this is the service we're looking for
                    if server.docker.service and server.docker.service not in name:
                        continue
                    
                    if state == "running":
                        return "running", f"Container: {name}"
                    elif state == "exited":
                        return "stopped", f"Container exited: {name}"
                    else:
                        return state, f"Container: {name}"
                except json.JSONDecodeError:
                    continue
        
        return "stopped", "No matching containers"
        
    except subprocess.TimeoutExpired:
        return "error", "Status check timed out"
    except Exception as e:
        return "error", str(e)


def get_server_logs(
    server: MCPServer,
    lines: int = 50,
    follow: bool = False,
) -> tuple[bool, str]:
    """
    Get logs from a Docker-based MCP server.
    
    Args:
        server: MCPServer with Docker configuration
        lines: Number of lines to show
        follow: Follow log output (blocking)
    
    Returns:
        (success, logs_or_error)
    """
    if server.type != MCPServerType.DOCKER:
        return False, "Not a Docker server"
    
    if not server.docker:
        return False, "No Docker configuration"
    
    compose_path = Path(server.docker.compose_file).expanduser().resolve()
    if not compose_path.exists():
        return False, f"Compose file not found: {compose_path}"
    
    cmd = ["docker", "compose", "-f", str(compose_path), "logs", f"--tail={lines}"]
    
    if follow:
        cmd.append("-f")
    
    if server.docker.service:
        cmd.append(server.docker.service)
    
    try:
        if follow:
            # For follow mode, run interactively
            subprocess.run(cmd, cwd=compose_path.parent)
            return True, ""
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=compose_path.parent,
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Log retrieval timed out"
    except Exception as e:
        return False, str(e)


def start_all_docker_servers(workspace: Optional[Path] = None) -> dict[str, tuple[bool, str]]:
    """Start all Docker-based MCP servers."""
    servers = get_docker_servers(workspace)
    results = {}
    for key, server in servers.items():
        results[key] = start_server(server)
    return results


def stop_all_docker_servers(workspace: Optional[Path] = None) -> dict[str, tuple[bool, str]]:
    """Stop all Docker-based MCP servers."""
    servers = get_docker_servers(workspace)
    results = {}
    for key, server in servers.items():
        results[key] = stop_server(server)
    return results
