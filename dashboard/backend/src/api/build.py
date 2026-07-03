"""Build components API — catalog endpoints for agent ingredients.

Exposes the building blocks used to assemble an agent (tools, retrievers,
databases, models) so the Build section can surface every ingredient.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services import build_components_service as svc
from src.services import agent_manifest_service as manifest_svc

router = APIRouter(prefix="/api/build", tags=["build"])


@router.get("/tools", response_model=svc.ComponentList)
async def tools():
    """Built-in template tools + reusable agent-tools registry entries."""
    return svc.list_tools()


@router.get("/retrievers", response_model=svc.ComponentList)
async def retrievers():
    """Supported retriever backends (FAISS / FTS / KG / hybrid)."""
    return svc.list_retrievers()


@router.get("/databases", response_model=svc.ComponentList)
async def databases():
    """Database connectors supported by the platform (database-* skills)."""
    return svc.list_databases()


@router.get("/models", response_model=svc.ComponentList)
async def models():
    """Supported LLM models (Vertex AI / Gemini), with the configured default."""
    return svc.list_models()


# ── Agent manifest (IR) ──────────────────────────────────────────────────

class ManifestResponse(BaseModel):
    manifest: Dict[str, Any]
    yaml: str


class WriteManifestRequest(BaseModel):
    path: str
    manifest: Optional[Dict[str, Any]] = None


@router.get("/manifest", response_model=ManifestResponse)
async def get_manifest(path: str = Query(..., description="Agent project path")):
    """Derive the agent.yaml manifest (IR) for a project."""
    try:
        m = manifest_svc.build_manifest(path)
        return ManifestResponse(manifest=m, yaml=manifest_svc.manifest_to_yaml(m))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to build manifest: {e}")


@router.post("/manifest")
async def post_manifest(req: WriteManifestRequest):
    """Write agent.yaml into the project (non-destructive — manifest only)."""
    try:
        return manifest_svc.write_manifest(req.path, req.manifest)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to write manifest: {e}")
