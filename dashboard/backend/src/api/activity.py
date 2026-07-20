"""Activity feed API routes."""

from typing import Optional

from fastapi import APIRouter, Query

from src.services.activity_service import (
    ActivityEntry,
    ActivityStats,
    get_activity,
    get_activity_stats,
)

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("", response_model=list[ActivityEntry])
async def api_get_activity(
    command: Optional[str] = Query(None, description="Filter by command (e.g., agent, code, kg)"),
    subcommand: Optional[str] = Query(None, description="Filter by subcommand"),
    status: Optional[str] = Query(None, description="Filter by status (success, error)"),
    limit: int = Query(50, ge=1, le=500),
    since: Optional[str] = Query(None, description="ISO 8601 timestamp to filter from"),
    source: Optional[str] = Query(None, description="Filter by origin (cli, dashboard, …)"),
    actor: Optional[str] = Query(None, description="Filter by authenticated principal"),
    entity_type: Optional[str] = Query(None, description="Filter by entity kind (project, skill, story, …)"),
):
    """Get recent activity log entries (with audit-trail filters)."""
    return get_activity(
        command=command,
        subcommand=subcommand,
        status=status,
        limit=limit,
        since=since,
        source=source,
        actor=actor,
        entity_type=entity_type,
    )


@router.get("/stats", response_model=ActivityStats)
async def api_get_activity_stats():
    """Get aggregate activity statistics."""
    return get_activity_stats()
