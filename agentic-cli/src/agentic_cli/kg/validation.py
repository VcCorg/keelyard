"""Validation utilities for knowledge graph operations."""

import socket
from typing import Dict, Optional, Tuple

from agentic_cli.kg.config import KGConfig


def check_neo4j_availability(
    uri: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Check if Neo4j is available and accessible.
    
    Args:
        uri: Neo4j URI (uses config if None)
        username: Neo4j username (uses config if None)
        password: Neo4j password (uses config if None)
    
    Returns:
        Tuple of (is_available, message)
    """
    # Load config if parameters not provided
    if uri is None or username is None or password is None:
        config = KGConfig.load()
        uri = uri or config.neo4j_uri
        username = username or config.neo4j_username
        password = password or config.neo4j_password
    
    # Parse URI to get host and port
    try:
        # Extract host and port from bolt://host:port
        if uri.startswith("bolt://"):
            uri_parts = uri.replace("bolt://", "").split(":")
            host = uri_parts[0]
            port = int(uri_parts[1]) if len(uri_parts) > 1 else 7687
        elif uri.startswith("neo4j://"):
            uri_parts = uri.replace("neo4j://", "").split(":")
            host = uri_parts[0]
            port = int(uri_parts[1]) if len(uri_parts) > 1 else 7687
        else:
            return False, f"Invalid URI format: {uri}. Expected bolt:// or neo4j://"
    except Exception as e:
        return False, f"Failed to parse URI: {str(e)}"
    
    # Check if port is reachable
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return False, f"Cannot connect to Neo4j at {host}:{port}. Is Neo4j running?"
    except socket.gaierror:
        return False, f"Cannot resolve hostname: {host}"
    except Exception as e:
        return False, f"Connection check failed: {str(e)}"
    
    # Try to connect with credentials
    try:
        from neo4j import GraphDatabase
    except ImportError as e:
        return False, f"neo4j package not installed. Install with: uv pip install 'agent-cli\[kg]' (Error: {str(e)})"
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # Test connection with a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        
        driver.close()
        return True, "Neo4j is available and accessible"
    
    except ImportError as e:
        # Catch import errors that might occur during driver initialization
        return False, f"neo4j package import failed. Install with: uv pip install 'agent-cli\[kg]' (Error: {str(e)})"
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful error messages
        if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return False, f"Authentication failed. Check username/password."
        elif "connection refused" in error_msg.lower():
            return False, f"Connection refused. Is Neo4j running at {uri}?"
        elif "timeout" in error_msg.lower():
            return False, f"Connection timeout. Neo4j may be starting up or unreachable."
        else:
            return False, f"Neo4j connection failed: {error_msg}"


def check_docker_available() -> Tuple[bool, str]:
    """
    Check if Docker is available.
    
    Returns:
        Tuple of (is_available, message)
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"Docker is available: {version}"
        else:
            return False, "Docker command failed"
    
    except FileNotFoundError:
        return False, "Docker is not installed"
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except Exception as e:
        return False, f"Docker check failed: {str(e)}"


def check_docker_running() -> Tuple[bool, str]:
    """
    Check if Docker daemon is running.
    
    Returns:
        Tuple of (is_running, message)
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0:
            return True, "Docker daemon is running"
        else:
            return False, "Docker daemon is not running"
    
    except FileNotFoundError:
        return False, "Docker is not installed"
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except Exception as e:
        return False, f"Docker check failed: {str(e)}"


def check_neo4j_container() -> Tuple[bool, str, Optional[Dict[str, str]]]:
    """
    Check if Neo4j Docker container is running.
    
    Returns:
        Tuple of (is_running, message, container_info)
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=neo4j", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode != 0:
            return False, "Failed to check Docker containers", None
        
        output = result.stdout.strip()
        
        if not output:
            return False, "No Neo4j container found", None
        
        # Parse container info
        lines = output.split("\n")
        containers = []
        
        for line in lines:
            if line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "ports": parts[2] if len(parts) > 2 else "",
                    })
        
        if containers:
            container = containers[0]
            if "Up" in container["status"]:
                return True, f"Neo4j container '{container['name']}' is running", container
            else:
                return False, f"Neo4j container '{container['name']}' exists but is not running", container
        
        return False, "No Neo4j container found", None
    
    except FileNotFoundError:
        return False, "Docker is not installed", None
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out", None
    except Exception as e:
        return False, f"Container check failed: {str(e)}", None


def validate_prerequisites() -> Dict[str, Tuple[bool, str]]:
    """
    Validate all prerequisites for knowledge graph operations.
    
    Returns:
        Dictionary with validation results
    """
    results = {}
    
    # Check Docker
    docker_available, docker_msg = check_docker_available()
    results["docker_installed"] = (docker_available, docker_msg)
    
    if docker_available:
        docker_running, docker_run_msg = check_docker_running()
        results["docker_running"] = (docker_running, docker_run_msg)
        
        if docker_running:
            container_running, container_msg, _ = check_neo4j_container()
            results["neo4j_container"] = (container_running, container_msg)
    
    # Check Neo4j connection
    neo4j_available, neo4j_msg = check_neo4j_availability()
    results["neo4j_connection"] = (neo4j_available, neo4j_msg)
    
    return results


def get_setup_instructions(results: Optional[Dict[str, Tuple[bool, str]]] = None) -> str:
    """
    Get context-aware setup instructions for Neo4j.

    Inspects the diagnostic results to show only relevant instructions.
    If the container is already running but the Python package is missing,
    it shows the package install command instead of the full infra setup.

    Args:
        results: Diagnostic results from validate_prerequisites().

    Returns:
        Formatted setup instructions
    """
    # Detect situation from results
    container_ok = False
    package_missing = False
    if results:
        container_ok = results.get("neo4j_container", (False, ""))[0]
        conn_msg = results.get("neo4j_connection", (False, ""))[1]
        package_missing = "not installed" in conn_msg or "import failed" in conn_msg

    # Case 1: Container running, just missing the Python package
    if container_ok and package_missing:
        return """
Neo4j container is running but the Python driver is not installed.

Install the KG dependencies:
   uv pip install "agentic-cli\[kg]"

Then verify the connection:
   dva kg stats
"""

    # Case 2: Container not running — show full infra setup
    sections = ["Neo4j Setup Instructions:\n"]

    if not container_ok:
        sections.append(
            "1. Start the Neo4j container:\n"
            "   docker compose -f mcp-servers/docker-compose.yml up -d dva-neo4j\n\n"
            "   Or, from the infrastructure directory:\n"
            "   cd ../kg-infrastructure && make start\n\n"
            "2. Wait for Neo4j to be ready (30-60 seconds)\n"
        )

    if package_missing:
        sections.append(
            "3. Install the KG Python dependencies:\n"
            '   uv pip install "agent-cli\[kg]"\n'
        )

    sections.append(
        "4. Configure Agent-CLI (if not already done):\n"
        "   agent-cli kg init --provider neo4j \\\n"
        "     --uri bolt://localhost:7687 \\\n"
        "     --username neo4j \\\n"
        "     --password password\n\n"
        "5. Verify connection:\n"
        "   agent-cli kg stats\n"
    )

    return "\n".join(sections)
