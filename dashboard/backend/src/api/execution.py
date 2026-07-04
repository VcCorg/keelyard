"""Execution API routes — vendor-neutral engines + portable context bundles."""

from fastapi import APIRouter, HTTPException

from src.services.execution_service import (
    EngineInfoModel,
    PortableContextRequest,
    PortableContextResult,
    list_engines,
    preview_portable_context,
)

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.get("/engines", response_model=list[EngineInfoModel])
async def get_engines():
    """List registered execution engines (Devin + local portable context)."""
    try:
        return list_engines()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/preview", response_model=PortableContextResult)
async def post_context_preview(req: PortableContextRequest):
    """Render a task's portable, engine-neutral context bundle (no files written)."""
    try:
        return preview_portable_context(req)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
