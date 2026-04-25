"""Health check utilities for MCP servers."""

import socket
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from agentic_cli.mcp.config import (
    MCPServer,
    MCPServerType,
    get_merged_servers,
)


def check_port_open(host: str, port: int, timeout: float = 5.0) -> tuple[bool, str]:
    """Check if a port is open and accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, f"Port {port} is open"
        return False, f"Port {port} is not open (error code: {result})"
    except socket.timeout:
        return False, f"Connection to {host}:{port} timed out"
    except socket.gaierror as e:
        return False, f"DNS resolution failed for {host}: {e}"
    except Exception as e:
        return False, f"Connection error: {e}"


def check_http_endpoint(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Check if an HTTP endpoint is responding."""
    try:
        import urllib.request
        import urllib.error
        
        # Try health endpoint first, then root
        endpoints = [
            f"{url.rstrip('/')}/health",
            url,
        ]
        
        for endpoint in endpoints:
            try:
                req = urllib.request.Request(endpoint, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    status = response.getcode()
                    if status == 200:
                        return True, f"HTTP {status} OK at {endpoint}"
                    return True, f"HTTP {status} at {endpoint}"
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    return True, f"HTTP {e.code} at {endpoint} (server responding)"
                continue
            except urllib.error.URLError:
                continue
        
        return False, f"No response from {url}"
        
    except Exception as e:
        return False, f"HTTP check failed: {e}"


def check_stdio_command(command: str, args: list[str] = None) -> tuple[bool, str]:
    """Check if a stdio command is available."""
    args = args or []
    
    # Check if command exists
    try:
        # Try to find the command
        if command in ("python", "python3"):
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, f"Command available: {result.stdout.strip()}"
        elif command in ("node", "npx"):
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, f"Command available: {result.stdout.strip()}"
        else:
            # Generic check using 'which' or 'where'
            which_cmd = "which" if not subprocess.sys.platform.startswith("win") else "where"
            result = subprocess.run(
                [which_cmd, command],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, f"Command found: {result.stdout.strip()}"
        
        return False, f"Command not found: {command}"
        
    except FileNotFoundError:
        return False, f"Command not found: {command}"
    except subprocess.TimeoutExpired:
        return False, f"Command check timed out: {command}"
    except Exception as e:
        return False, f"Command check failed: {e}"


def check_server_health(server: MCPServer) -> dict:
    """
    Check health of an MCP server.
    
    Returns:
        Dict with keys: healthy, status, message, details
    """
    result = {
        "name": server.name,
        "type": server.type.value,
        "healthy": False,
        "status": "unknown",
        "message": "",
        "details": {},
    }
    
    if not server.enabled:
        result["status"] = "disabled"
        result["message"] = "Server is disabled"
        return result
    
    if server.type == MCPServerType.STDIO:
        # Check if command is available
        success, msg = check_stdio_command(server.command, server.args)
        result["healthy"] = success
        result["status"] = "available" if success else "unavailable"
        result["message"] = msg
        
        # Check if script file exists (if args contain a path)
        if server.args:
            for arg in server.args:
                if arg.endswith(".py") or arg.endswith(".js"):
                    path = Path(arg).expanduser()
                    result["details"]["script_exists"] = path.exists()
                    if not path.exists():
                        result["healthy"] = False
                        result["status"] = "error"
                        result["message"] = f"Script not found: {arg}"
                    break
    
    elif server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        if not server.url:
            result["status"] = "error"
            result["message"] = "No URL configured"
            return result
        
        # Parse URL
        parsed = urlparse(server.url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        
        # Check port
        port_ok, port_msg = check_port_open(host, port)
        result["details"]["port_check"] = port_msg
        
        if port_ok:
            # Check HTTP endpoint
            http_ok, http_msg = check_http_endpoint(server.url)
            result["healthy"] = http_ok
            result["status"] = "running" if http_ok else "not_responding"
            result["message"] = http_msg
        else:
            result["healthy"] = False
            result["status"] = "not_running"
            result["message"] = port_msg
    
    elif server.type == MCPServerType.DOCKER:
        if not server.docker:
            result["status"] = "error"
            result["message"] = "No Docker configuration"
            return result
        
        # Check compose file exists
        compose_path = Path(server.docker.compose_file).expanduser()
        if not compose_path.exists():
            result["status"] = "error"
            result["message"] = f"Compose file not found: {compose_path}"
            return result
        
        result["details"]["compose_file"] = str(compose_path)
        
        # Import docker module to check status
        from agentic_cli.mcp.docker import get_server_status, check_docker_running
        
        # Check Docker daemon
        docker_ok, docker_msg = check_docker_running()
        result["details"]["docker_daemon"] = docker_msg
        
        if not docker_ok:
            result["status"] = "error"
            result["message"] = f"Docker not running: {docker_msg}"
            return result
        
        # Check container status
        status, details = get_server_status(server)
        result["details"]["container_status"] = details
        
        if status == "running":
            # Also check HTTP endpoint if port is configured
            port = server.docker.port
            url = server.url or f"http://localhost:{port}"
            http_ok, http_msg = check_http_endpoint(url)
            result["healthy"] = http_ok
            result["status"] = "running" if http_ok else "container_running_not_responding"
            result["message"] = http_msg if http_ok else f"Container running but not responding: {http_msg}"
        else:
            result["healthy"] = False
            result["status"] = status
            result["message"] = details
    
    return result


def check_all_servers_health(workspace: Optional[Path] = None) -> list[dict]:
    """Check health of all configured MCP servers."""
    servers = get_merged_servers(workspace)
    results = []
    for key, server in servers.items():
        health = check_server_health(server)
        health["key"] = key
        results.append(health)
    return results


def get_health_summary(workspace: Optional[Path] = None) -> dict:
    """Get summary of all server health statuses."""
    results = check_all_servers_health(workspace)
    
    summary = {
        "total": len(results),
        "healthy": sum(1 for r in results if r["healthy"]),
        "unhealthy": sum(1 for r in results if not r["healthy"] and r["status"] != "disabled"),
        "disabled": sum(1 for r in results if r["status"] == "disabled"),
        "servers": results,
    }
    
    return summary
