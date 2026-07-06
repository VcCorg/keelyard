"""Generic CLI runner API — streams whitelisted `keel ...` commands over SSE."""

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from src.services import cli_service as svc
from src.services.run_registry import registry

router = APIRouter(prefix="/api/cli", tags=["cli"])


@router.get("/groups", response_model=list[str])
async def groups():
    """List the whitelisted top-level command groups."""
    return svc.list_groups()


@router.get("/blocked", response_model=list[str])
async def blocked():
    """List destructive subcommands blocked unless danger mode is enabled."""
    return svc.list_blocked_subcommands()


@router.get("/run/stream")
async def run_stream(
    command: str = Query(..., description="e.g. 'kg stats' or 'domain list'"),
    allow_destructive: bool = Query(False, description="Danger mode: permit destructive subcommands"),
):
    """Validate and stream a whitelisted `keel` command (recorded in run history)."""
    try:
        cmd = svc.build_command(command, allow_destructive=allow_destructive)
    except svc.CommandNotAllowed as e:
        raise HTTPException(status_code=400, detail=str(e))

    rec = registry.create(kind="cli", label=command.strip(), cmd=cmd)

    async def gen():
        async for event in registry.stream(rec, cmd):
            yield event

    return EventSourceResponse(gen())
