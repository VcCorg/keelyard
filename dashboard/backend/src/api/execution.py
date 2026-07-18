"""Execution API routes — vendor-neutral engines + portable context bundles."""

from fastapi import APIRouter, Depends, HTTPException, Request

from agentic_cli.auth import PERM_CONTEXT_BUILD
from src.services.auth_service import actor_of, require
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
async def post_context_preview(
    req: PortableContextRequest,
    request: Request,
    _principal=Depends(require(PERM_CONTEXT_BUILD)),
):
    """Render a task's portable, engine-neutral context bundle (no files written).

    Requires the ``context:build`` permission.
    """
    from agentic_cli.meta_repo.build_governance import GovernanceViolation

    try:
        return preview_portable_context(req, actor=actor_of(request))
    except GovernanceViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
