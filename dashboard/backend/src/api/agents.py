"""Agent management API routes."""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services.agent_service import (
    AgentInfo,
    AgentProject,
    ProjectValidation,
    list_agents,
    get_agent,
    start_agent,
    stop_agent,
    get_agent_logs,
    discover_agent_projects,
    validate_project,
    get_project_domain,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


class StartAgentRequest(BaseModel):
    path: str
    review_mode: Optional[str] = None
    poll_interval: Optional[int] = None


class AgentActionResponse(BaseModel):
    success: bool
    message: str
    agent: Optional[AgentInfo] = None


@router.get("", response_model=list[AgentInfo])
async def api_list_agents():
    """List all tracked agent instances with live status."""
    return list_agents()


@router.get("/projects", response_model=list[AgentProject])
async def api_discover_projects(
    workspace: Optional[str] = Query(None, description="Workspace path to scan"),
):
    """Discover agent projects in the workspace, enriched with validation and domain."""
    ws_path = Path(workspace) if workspace else None
    projects = discover_agent_projects(workspace=ws_path)
    for p in projects:
        p.validation = validate_project(p.path, p.use_case)
        p.domain = get_project_domain(p.path)
    return projects


@router.get("/{name}", response_model=AgentInfo)
async def api_get_agent(name: str):
    """Get a single agent by name."""
    agent = get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    return agent


@router.post("/{name}/start", response_model=AgentActionResponse)
async def api_start_agent(name: str, req: StartAgentRequest):
    """Start an agent as a background daemon."""
    try:
        agent = start_agent(
            name=name,
            path=req.path,
            review_mode=req.review_mode,
            poll_interval=req.poll_interval,
        )
        return AgentActionResponse(success=True, message=f"Agent '{name}' started", agent=agent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/stop", response_model=AgentActionResponse)
async def api_stop_agent(name: str):
    """Stop a running agent."""
    success = stop_agent(name)
    if success:
        return AgentActionResponse(success=True, message=f"Agent '{name}' stopped")
    raise HTTPException(status_code=404, detail=f"Agent '{name}' not found or not running")


@router.get("/{name}/logs")
async def api_agent_logs_sse(name: str, tail: int = Query(100, ge=1, le=5000)):
    """Stream agent logs via SSE. Sends existing lines then tails for new ones."""

    async def event_generator():
        last_count = 0
        # Send existing lines first
        lines = get_agent_logs(name, tail=tail)
        for line in lines:
            yield {"event": "log", "data": line}
        last_count = len(lines)

        # Then poll for new lines
        while True:
            await asyncio.sleep(2)
            lines = get_agent_logs(name, tail=tail + 500)
            if len(lines) > last_count:
                new_lines = lines[last_count:]
                for line in new_lines:
                    yield {"event": "log", "data": line}
                last_count = len(lines)

    return EventSourceResponse(event_generator())
