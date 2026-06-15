"""Run history API — lists captured CLI command runs (code / eval / cli)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services.run_registry import registry, RunInfo

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunDetail(RunInfo):
    lines: list[str]


@router.get("", response_model=list[RunInfo])
async def list_runs(kind: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=100)):
    return registry.list_runs(kind=kind, limit=limit)


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str):
    rec = registry.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Run not found")
    info = rec.info()
    return RunDetail(**info.model_dump(), lines=rec.lines)
