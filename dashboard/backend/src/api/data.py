"""Data source API — thin proxy over the agentic-cli `data` commands."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services import data_service as svc

router = APIRouter(prefix="/api/data", tags=["data"])


class CreateDataSourceRequest(BaseModel):
    name: str
    source_type: str
    source_location: str
    description: str = ""
    tags: list[str] = []
    project: str = ""
    confluence_space: str = ""
    git_branch: str = ""
    git_tag: str = ""


@router.get("/validate", response_model=svc.ValidationResult)
async def validate_location(source_type: str, location: str):
    """Validate a source location (path/URL) before creating a source."""
    return svc.validate_location(source_type, location)


@router.get("/sources", response_model=list[svc.DataSourceInfo])
async def list_sources():
    """List configured data sources."""
    try:
        return svc.list_data_sources()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources", response_model=svc.CommandResult)
async def create_source(req: CreateDataSourceRequest):
    """Create a data source (delegates validation to `dva data create`)."""
    result = svc.create_data_source(**req.model_dump())
    if not result.success:
        raise HTTPException(status_code=400, detail=result.output or "Create failed")
    return result


@router.delete("/sources/{name}", response_model=svc.CommandResult)
async def delete_source(name: str):
    result = svc.delete_data_source(name)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.output or "Delete failed")
    return result
