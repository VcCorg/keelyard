"""MCP server management API routes."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services.mcp_service import (
    MCPServerInfo,
    MCPHealthResult,
    list_mcp_servers,
    check_health,
    start_mcp_server,
    stop_mcp_server,
    get_mcp_logs,
)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class MCPActionResponse(BaseModel):
    success: bool
    message: str


def _apply_health(server: MCPServerInfo, hr: MCPHealthResult) -> None:
    """Merge a health result onto a server, deriving a combined status.

    Port up + valid/absent token → healthy. Port up but the required token is
    missing or rejected → degraded (so the UI never shows a misleading
    'healthy' for a server that can't actually authenticate). Port down →
    unhealthy.
    """
    server.auth_status = hr.auth_status
    server.auth_message = hr.auth_message
    if not hr.healthy:
        server.health_status = "unhealthy"
    elif hr.auth_status in ("missing", "invalid"):
        server.health_status = "degraded"
    else:
        server.health_status = "healthy"
    parts = [hr.message]
    if hr.auth_message and hr.auth_status not in ("ok", "n/a"):
        parts.append(hr.auth_message)
    server.health_message = " — ".join(p for p in parts if p)


@router.get("/servers", response_model=list[MCPServerInfo])
async def api_list_servers():
    """List all configured MCP servers."""
    servers = list_mcp_servers()
    # Enrich with health + auth status
    health_map = {r.name: r for r in check_health()}
    for server in servers:
        if server.name in health_map:
            _apply_health(server, health_map[server.name])
    return servers


@router.get("/servers/{name}", response_model=MCPServerInfo)
async def api_get_server(name: str):
    """Get details for a single MCP server."""
    servers = list_mcp_servers()
    for server in servers:
        if server.name == name:
            health = check_health(name=name)
            if health:
                _apply_health(server, health[0])
            return server
    raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")


@router.get("/health", response_model=list[MCPHealthResult])
async def api_check_health():
    """Check health of all MCP servers."""
    return check_health()


@router.post("/servers/{name}/start", response_model=MCPActionResponse)
async def api_start_server(name: str):
    """Start a Docker-based MCP server."""
    try:
        success = start_mcp_server(name)
        if success:
            return MCPActionResponse(success=True, message=f"MCP server '{name}' started")
        return MCPActionResponse(success=False, message=f"Failed to start '{name}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{name}/stop", response_model=MCPActionResponse)
async def api_stop_server(name: str):
    """Stop a Docker-based MCP server."""
    try:
        success = stop_mcp_server(name)
        if success:
            return MCPActionResponse(success=True, message=f"MCP server '{name}' stopped")
        return MCPActionResponse(success=False, message=f"Failed to stop '{name}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/servers/{name}/logs")
async def api_mcp_logs_sse(name: str, tail: int = Query(100, ge=1, le=5000)):
    """Stream Docker logs for an MCP server via SSE."""

    async def event_generator():
        last_count = 0
        lines = get_mcp_logs(name, tail=tail)
        for line in lines:
            yield {"event": "log", "data": line}
        last_count = len(lines)

        while True:
            await asyncio.sleep(3)
            lines = get_mcp_logs(name, tail=tail + 500)
            if len(lines) > last_count:
                new_lines = lines[last_count:]
                for line in new_lines:
                    yield {"event": "log", "data": line}
                last_count = len(lines)

    return EventSourceResponse(event_generator())
