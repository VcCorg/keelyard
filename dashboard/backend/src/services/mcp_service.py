"""MCP server service — discovers Docker MCP containers, checks health.

Primary source of truth: docker-compose.yml in keel-mcp-servers/
Enriches with CLI registry metadata when available.
"""

import json
import logging
import os
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
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
    health_status: str = "unknown"  # healthy, degraded, unhealthy, unknown
    health_message: str = ""
    container_name: Optional[str] = None
    container_status: Optional[str] = None
    # Auth/token status independent of port reachability.
    auth_status: str = "unknown"  # ok, missing, invalid, unreachable, n/a, unknown
    auth_message: str = ""
    # Where this entry came from: "docker" (compose stack, start/stop/logs) or
    # "registry" (user-registered in ~/.keel/mcp/registry.json — editable).
    source: str = "docker"


class MCPHealthResult(BaseModel):
    """Health check result for a single server."""
    name: str
    healthy: bool
    message: str
    auth_status: str = "unknown"  # ok, missing, invalid, unreachable, n/a, unknown
    auth_message: str = ""


class DockerServiceStatus(BaseModel):
    """One MCP service in the bundled Docker stack + its container state."""
    name: str
    description: str = ""
    container_name: str = ""
    port: Optional[int] = None
    running: bool = False
    status: str = "absent"  # running | exited | absent | <raw docker status>


class DockerMcpStatus(BaseModel):
    """Whether Docker + the bundled MCP compose stack are available/running.

    The bundled MCP servers (Jira, Confluence, Bitbucket, KG, …) require Docker.
    This surfaces, at a glance, whether Docker is up and which MCP containers are
    running — so a user knows why an MCP-dependent feature (e.g. Work Items) is
    unavailable, and whether to start the stack or register a remote server.
    """
    docker_available: bool = False
    docker_message: str = ""
    compose_found: bool = False
    compose_path: Optional[str] = None
    services: list[DockerServiceStatus] = []


def _check_port(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    """Quick TCP port check."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Port {port} is open"
    except OSError as e:
        return False, f"Port {port} unreachable: {e}"


# ── Auth / token verification ────────────────────────────────────────────────
# A port being open only proves the container is up. It does NOT prove the
# service can authenticate to its upstream (Glean/Jira/Bitbucket/Confluence).
# The checks below read the SAME tokens the containers receive (docker
# --env-file mcp-servers/.env, falling back to the loaded process env) and,
# when a token is present, make one lightweight authenticated call to detect
# expired/invalid tokens.

# docker-compose service -> (token env var, base-url env var, auth probe path)
_AUTH_SPEC: dict[str, tuple[str, str, str]] = {
    "bitbucket-mcp": ("BITBUCKET_PERSONAL_ACCESS_TOKEN", "BITBUCKET_SERVER_URL", "/rest/api/1.0/users?limit=1"),
    "jira-mcp": ("JIRA_PERSONAL_ACCESS_TOKEN", "JIRA_SERVER_URL", "/rest/api/2/myself"),
    "confluence-mcp": ("CONFLUENCE_PERSONAL_ACCESS_TOKEN", "CONFLUENCE_SERVER_URL", "/rest/api/user/current"),
    "glean-mcp": ("GLEAN_API_TOKEN", "GLEAN_DOMAIN", "/rest/api/v1/search"),
}

# Services with no upstream token to verify.
_NO_AUTH = {"memory-mcp", "kg-mcp", "agentic-mcp", "mcp-gateway", "mcp-proxy"}

_AUTH_TTL = 60.0  # seconds; avoid hammering upstreams on every 10s poll
_auth_cache: dict[str, tuple[float, str, str, str]] = {}  # name -> (ts, token_fp, status, message)


def _load_stack_env() -> dict[str, str]:
    """Read the tokens the containers actually run with.

    docker compose is launched with ``--env-file mcp-servers/.env`` (see mcp.sh),
    so that file is ground truth. Process env (loaded from ~/.dva/.env) overrides
    only when the stack file leaves a value blank.
    """
    env: dict[str, str] = {}
    compose = _find_compose_file()
    env_file = compose.parent / ".env" if compose else None
    if env_file and env_file.exists():
        try:
            for raw in env_file.read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
        except Exception as e:  # noqa: BLE001
            logger.debug("Could not parse stack .env: %s", e)
    # Fill blanks from the process environment (dashboard loads the global .env).
    backfill = set()
    for spec in _AUTH_SPEC.values():
        backfill.update((spec[0], spec[1]))
    backfill.update((
        "GLEAN_AUTH_MODE", "GLEAN_OAUTH_ISSUER", "GLEAN_OAUTH_CLIENT_ID",
        "GLEAN_OAUTH_CLIENT_SECRET", "GLEAN_OAUTH_SCOPE", "GLEAN_OAUTH_TOKEN_URL",
    ))
    for var in backfill:
        if not env.get(var) and os.environ.get(var):
            env[var] = os.environ[var]
    return env


def _fingerprint(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()[:12] if token else ""


def _probe_auth(name: str, env: dict[str, str]) -> tuple[str, str]:
    """Return (auth_status, auth_message) for one server. Cached for _AUTH_TTL."""
    if name in _NO_AUTH:
        return "n/a", "No upstream token required"
    spec = _AUTH_SPEC.get(name)
    if not spec:
        return "unknown", ""

    # Glean can authenticate via a static token OR SSO (OAuth client-credentials).
    if name == "glean-mcp" and (env.get("GLEAN_AUTH_MODE") or "token").strip().lower() == "sso":
        return _probe_glean_sso(env)

    token_var, url_var, path = spec
    token = (env.get(token_var) or "").strip()
    base_url = (env.get(url_var) or "").strip()
    fp = _fingerprint(token)

    if not token:
        return "missing", f"{token_var} is not set"

    # Serve cached result if the token is unchanged and still fresh.
    cached = _auth_cache.get(name)
    now = time.time()
    if cached and cached[1] == fp and (now - cached[0]) < _AUTH_TTL:
        return cached[2], cached[3]

    status, message = _live_auth_probe(name, token, base_url, path)
    _auth_cache[name] = (now, fp, status, message)
    return status, message


def _live_auth_probe(name: str, token: str, base_url: str, path: str) -> tuple[str, str]:
    """Make one short authenticated request to the upstream to validate the token."""
    if not base_url:
        return "unknown", "Upstream URL not configured"
    try:
        import httpx
    except Exception:  # noqa: BLE001
        return "unknown", "httpx unavailable; cannot verify token"

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = base_url.rstrip("/") + path
    try:
        if name == "glean-mcp":
            # Glean has no cheap ping; a minimal search validates the token.
            headers["Content-Type"] = "application/json"
            with httpx.Client(timeout=5.0) as c:
                resp = c.post(url, json={"query": "ping", "pageSize": 1}, headers=headers)
        else:
            with httpx.Client(timeout=5.0, follow_redirects=True) as c:
                resp = c.get(url, headers=headers)
    except Exception as e:  # noqa: BLE001 - network/TLS/timeout
        return "unreachable", f"Could not reach upstream: {str(e)[:120]}"

    if resp.status_code in (401, 403):
        return "invalid", f"Token rejected ({resp.status_code}) — likely expired or wrong scope"
    if resp.status_code >= 500:
        return "unreachable", f"Upstream error ({resp.status_code})"
    if resp.status_code >= 400:
        # e.g. 404 on the probe path — token itself was accepted (not 401/403).
        return "ok", f"Token accepted (probe returned {resp.status_code})"
    return "ok", "Token valid"


def _probe_glean_sso(env: dict[str, str]) -> tuple[str, str]:
    """Validate Glean SSO (OAuth client-credentials) by minting a service token.

    Mirrors the MCP/CLI flow: discover (or use) the token endpoint and request a
    client-credentials token. Cached for _AUTH_TTL keyed on the client id/secret.
    """
    client_id = (env.get("GLEAN_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (env.get("GLEAN_OAUTH_CLIENT_SECRET") or "").strip()
    if not (client_id and client_secret):
        return "missing", "SSO mode but GLEAN_OAUTH_CLIENT_ID/SECRET not set"

    fp = _fingerprint(client_id + ":" + client_secret)
    cached = _auth_cache.get("glean-mcp")
    now = time.time()
    if cached and cached[1] == fp and (now - cached[0]) < _AUTH_TTL:
        return cached[2], cached[3]

    try:
        import httpx
    except Exception:  # noqa: BLE001
        return "unknown", "httpx unavailable; cannot verify token"

    base = (env.get("GLEAN_OAUTH_ISSUER") or env.get("GLEAN_DOMAIN") or "").strip().rstrip("/")
    token_url = (env.get("GLEAN_OAUTH_TOKEN_URL") or "").strip()
    scope = (env.get("GLEAN_OAUTH_SCOPE") or "").strip()

    try:
        with httpx.Client(timeout=8.0) as c:
            if not token_url:
                if not base:
                    return "unknown", "No GLEAN_DOMAIN/ISSUER to discover token endpoint"
                disc = c.get(f"{base}/.well-known/oauth-authorization-server")
                if disc.status_code >= 400:
                    return "unreachable", f"OAuth discovery returned {disc.status_code}"
                token_url = (disc.json() or {}).get("token_endpoint", "")
                if not token_url:
                    return "unknown", "OAuth metadata has no token_endpoint"
            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
            if scope:
                data["scope"] = scope
            resp = c.post(token_url, data=data)
    except Exception as e:  # noqa: BLE001
        status, message = "unreachable", f"Could not reach OAuth server: {str(e)[:120]}"
        _auth_cache["glean-mcp"] = (now, fp, status, message)
        return status, message

    if resp.status_code in (400, 401):
        status, message = "invalid", f"OAuth client rejected ({resp.status_code}) — check client id/secret/scope"
    elif resp.status_code >= 400:
        status, message = "unreachable", f"OAuth server error ({resp.status_code})"
    elif not (resp.json() or {}).get("access_token"):
        status, message = "invalid", "Token response had no access_token"
    else:
        status, message = "ok", "SSO token minted (client-credentials)"

    _auth_cache["glean-mcp"] = (now, fp, status, message)
    return status, message


def _get_docker_status() -> dict[str, str]:
    """Get container name → status mapping for keel- containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=keel-", "--format", "{{.Names}}\t{{.Status}}"],
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


def _docker_available() -> tuple[bool, str]:
    """Whether the Docker daemon is reachable (reuses the CLI's doctor check)."""
    try:
        from agentic_cli.kg.validation import check_docker_running

        return check_docker_running()
    except Exception:  # noqa: BLE001 - fall back to a direct probe
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            return (r.returncode == 0,
                    "Docker daemon is running" if r.returncode == 0
                    else "Docker daemon is not running")
        except FileNotFoundError:
            return False, "Docker is not installed"
        except Exception as e:  # noqa: BLE001
            return False, str(e)[:200]


def get_docker_mcp_status() -> DockerMcpStatus:
    """Report Docker availability + the bundled MCP stack's container status.

    Uses the compose file's service list when discoverable; otherwise falls back
    to the canonical MCP service set, so the panel is informative even in a
    standalone install where no compose file is bundled. Container state comes
    from ``docker ps -a`` regardless.
    """
    available, message = _docker_available()
    compose_path = _find_compose_file()
    compose_found = bool(compose_path and compose_path.exists())

    # Canonical service set: compose services if found, else known descriptions.
    known: dict[str, tuple[str, Optional[int]]] = {}  # svc -> (container, port)
    if compose_found:
        try:
            import yaml  # type: ignore

            with open(compose_path) as f:
                data = yaml.safe_load(f) or {}
            for svc, sd in (data.get("services") or {}).items():
                ports = sd.get("ports") or []
                port = None
                if ports:
                    try:
                        port = int(str(ports[0]).split(":")[0])
                    except ValueError:
                        port = None
                container = sd.get("container_name", f"keel-{svc}")
                known[svc] = (container, port)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to parse compose for docker status: %s", e)
    if not known:
        known = {svc: (f"keel-{svc}", None) for svc in _DESCRIPTIONS}

    docker_status = _get_docker_status() if available else {}

    services: list[DockerServiceStatus] = []
    for svc, (container, port) in known.items():
        raw = docker_status.get(container, "")
        low = raw.lower()
        if low.startswith("up"):
            status, running = "running", True
        elif "exited" in low or "created" in low or "restarting" in low:
            status, running = ("exited" if "exited" in low else low.split()[0]), False
        elif raw:
            status, running = raw, False
        else:
            status, running = "absent", False
        services.append(DockerServiceStatus(
            name=svc, description=_DESCRIPTIONS.get(svc, ""),
            container_name=container, port=port, running=running, status=status))

    services.sort(key=lambda s: s.name)
    return DockerMcpStatus(
        docker_available=available, docker_message=message,
        compose_found=compose_found,
        compose_path=str(compose_path) if compose_path else None,
        services=services)


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
                    container = svc_data.get("container_name", f"keel-{svc_name}")
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
        from agentic_cli.mcp.config import get_merged_servers
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
                    source="registry",
                )
    except (ImportError, Exception) as e:
        logger.debug("CLI registry not available: %s", e)

    return list(servers.values())


def _probe_target(srv: MCPServerInfo) -> tuple[str, Optional[int]]:
    """Resolve (host, port) to health-check for a server.

    Docker-compose entries expose localhost ports, but registry entries may
    point at a REMOTE stack (the packaged desktop app has no local Docker) —
    probing localhost for those reports false 'unreachable'. Prefer the host
    embedded in the server URL; fall back to localhost + declared port.
    """
    host, port = "localhost", srv.port
    if srv.url:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(srv.url)
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port:
                port = parsed.port
            elif port is None and parsed.scheme in ("http", "https", "ws", "wss"):
                port = 443 if parsed.scheme in ("https", "wss") else 80
        except Exception:  # noqa: BLE001 - fall back to localhost:port
            pass
    return host, port


def check_health(name: Optional[str] = None, verify_auth: bool = True) -> list[MCPHealthResult]:
    """Check health of MCP servers.

    Two independent dimensions are reported:
    - ``healthy`` / ``message``: TCP port reachability + Docker container state.
    - ``auth_status`` / ``auth_message``: whether the required upstream token is
      present and (when ``verify_auth``) actually accepted. A port being open
      does NOT mean the token is valid, so a server can be reachable yet have a
      missing or expired token.
    """
    servers = list_mcp_servers()
    if name:
        servers = [s for s in servers if s.name == name]
    docker_status = _get_docker_status()

    # Probe upstream auth for reachable servers concurrently (short timeout, cached).
    auth_map: dict[str, tuple[str, str]] = {}
    if verify_auth:
        stack_env = _load_stack_env()
        to_probe = [s.name for s in servers]
        if to_probe:
            with ThreadPoolExecutor(max_workers=min(6, len(to_probe))) as pool:
                for sname, res in zip(
                    to_probe, pool.map(lambda n: _probe_auth(n, stack_env), to_probe)
                ):
                    auth_map[sname] = res

    results = []
    for srv in servers:
        auth_status, auth_message = auth_map.get(srv.name, ("unknown", ""))

        host, port = _probe_target(srv)
        if port:
            ok, msg = _check_port(host, port)
            cname = srv.container_name or f"keel-{srv.name}"
            cstatus = docker_status.get(cname, "")
            if cstatus:
                msg = f"{msg} ({cstatus})"
                srv.container_status = cstatus
            results.append(MCPHealthResult(
                name=srv.name, healthy=ok, message=msg,
                auth_status=auth_status, auth_message=auth_message,
            ))
        else:
            results.append(MCPHealthResult(
                name=srv.name, healthy=False, message="No port configured",
                auth_status=auth_status, auth_message=auth_message,
            ))

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
        workspace / "keel-mcp-servers" / "docker-compose.yml",
    ]

    # Also check MCP registry for docker compose paths
    try:
        from agentic_cli.mcp.config import load_registry
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


# ── User-registered MCP servers (CRUD over the CLI registry) ────────────────
# The CLI owns the store (~/.keel/mcp/registry.json, same one `keel mcp add`
# writes); the dashboard is a lens over it. This is what lets a packaged
# desktop install point at a REMOTE MCP stack with no local Docker at all.

class MCPServerUpsert(BaseModel):
    """Payload for registering/updating an MCP server from the dashboard."""
    name: str
    url: str
    type: str = "sse"            # sse | http (stdio/docker stay CLI-managed)
    description: str = ""
    enabled: bool = True
    tools: list[str] = []


def _slug(name: str) -> str:
    import re

    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s


def _audit(action: str, key: str, actor: Optional[str], details: dict) -> None:
    try:
        from agentic_cli.tracker import record_action

        record_action("mcp", action, entity_type="mcp_server", entity_id=key,
                      source="dashboard", actor=actor, details=details)
    except Exception:  # noqa: BLE001 - never break on audit
        pass


def add_mcp_server(req: MCPServerUpsert, actor: Optional[str] = None) -> MCPServerInfo:
    """Register a new (remote) MCP server in the CLI registry."""
    from agentic_cli.mcp.config import (
        MCPServer, MCPServerType, MCPTransport, load_registry, save_registry,
        validate_server_config,
    )

    key = _slug(req.name)
    if not key:
        raise ValueError("A server name is required")
    if req.type not in ("sse", "http"):
        raise ValueError("Only 'sse' or 'http' servers can be added here — "
                         "use `keel mcp add` for stdio/docker servers")

    registry = load_registry()
    existing = {s.name for s in list_mcp_servers()} | set(registry.servers)
    if key in existing:
        raise ValueError(f"An MCP server named '{key}' already exists")

    server = MCPServer(
        name=key,
        type=MCPServerType(req.type),
        transport=MCPTransport(req.type),
        url=req.url.strip(),
        description=req.description.strip() or None,
        enabled=req.enabled,
        tools=req.tools,
    )
    ok, msg = validate_server_config(server)
    if not ok:
        raise ValueError(msg)

    registry.servers[key] = server
    save_registry(registry)
    _audit("add_server", key, actor, {"url": server.url, "type": req.type})
    for info in list_mcp_servers():
        if info.name == key:
            return info
    return MCPServerInfo(name=key, type=req.type, url=server.url, source="registry")


def update_mcp_server(name: str, req: MCPServerUpsert, actor: Optional[str] = None) -> MCPServerInfo:
    """Update a registry-sourced MCP server (URL, description, enabled)."""
    from agentic_cli.mcp.config import (
        MCPServerType, MCPTransport, load_registry, save_registry,
        validate_server_config,
    )
    from datetime import datetime, timezone

    registry = load_registry()
    server = registry.servers.get(name)
    if server is None:
        raise KeyError(f"'{name}' is not a registered MCP server "
                       "(docker-compose servers are managed by the stack)")
    if req.type not in ("sse", "http"):
        raise ValueError("Only 'sse' or 'http' types are supported here")

    server.url = req.url.strip()
    server.type = MCPServerType(req.type)
    server.transport = MCPTransport(req.type)
    server.description = req.description.strip() or None
    server.enabled = req.enabled
    if req.tools:
        server.tools = req.tools
    server.updated_at = datetime.now(timezone.utc).isoformat()

    ok, msg = validate_server_config(server)
    if not ok:
        raise ValueError(msg)

    save_registry(registry)
    _audit("update_server", name, actor, {"url": server.url, "enabled": server.enabled})
    for info in list_mcp_servers():
        if info.name == name:
            return info
    return MCPServerInfo(name=name, type=req.type, url=server.url, source="registry")


def remove_mcp_server(name: str, actor: Optional[str] = None) -> bool:
    """Remove a registry-sourced MCP server. Docker-compose servers can't be removed."""
    from agentic_cli.mcp.config import load_registry, save_registry

    registry = load_registry()
    if name not in registry.servers:
        raise KeyError(f"'{name}' is not a registered MCP server "
                       "(docker-compose servers are managed by the stack)")
    del registry.servers[name]
    save_registry(registry)
    _audit("remove_server", name, actor, {})
    return True
