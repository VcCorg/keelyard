"""Build components API — catalog endpoints for agent ingredients.

Exposes the building blocks used to assemble an agent (tools, retrievers,
databases, models) so the Build section can surface every ingredient.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services import build_components_service as svc
from src.services import agent_manifest_service as manifest_svc
from src.services import retriever_service as retr_svc

router = APIRouter(prefix="/api/build", tags=["build"])


@router.get("/tools", response_model=svc.ComponentList)
async def tools():
    """Built-in template tools + reusable agent-tools registry entries."""
    return svc.list_tools()


@router.get("/retrievers", response_model=svc.ComponentList)
async def retrievers():
    """Supported retriever backends (FAISS / FTS / KG / hybrid)."""
    return svc.list_retrievers()


class CreateRetrieverRequest(BaseModel):
    name: str
    backend: str = "faiss"
    embedding_model: Optional[str] = None
    source: Optional[str] = None
    description: str = ""


@router.get("/retrievers/instances", response_model=retr_svc.RetrieverList)
async def retriever_instances():
    """List named retriever instances."""
    return retr_svc.list_instances()


@router.post("/retrievers/instances", response_model=retr_svc.RetrieverInstance)
async def create_retriever(req: CreateRetrieverRequest):
    """Create a named retriever instance."""
    try:
        return retr_svc.create_instance(
            name=req.name,
            backend=req.backend,
            embedding_model=req.embedding_model,
            source=req.source,
            description=req.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/retrievers/instances/{retriever_id}")
async def delete_retriever(retriever_id: str):
    """Delete a named retriever instance."""
    return {"deleted": retr_svc.delete_instance(retriever_id)}


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


# ── Build → Eval gate ────────────────────────────────────────────────────

# An agent "passes" when its latest eval run scores at or above this threshold.
EVAL_PASS_THRESHOLD = 0.7


class EvalStatus(BaseModel):
    eval_ready: bool
    spec: Optional[str] = None
    last_run: Optional[Dict[str, Any]] = None


@router.get("/eval-status", response_model=EvalStatus)
async def eval_status(path: str = Query(..., description="Agent project path")):
    """Eval gate for a project: is it eval-ready, and how did its last run score?"""
    from pathlib import Path as _Path

    # Eval readiness: does the agent expose an answer() entrypoint?
    spec: Optional[str] = None
    try:
        from src.services.agent_service import get_agent_eval_spec

        result = get_agent_eval_spec(path)
        spec = (result or {}).get("spec")
    except Exception:  # noqa: BLE001 - readiness is best-effort
        spec = None

    # Latest eval run for this project (matched by agent spec, then by name).
    last_run: Optional[Dict[str, Any]] = None
    try:
        from src.services import eval_service

        project_name = _Path(path).name
        runs = eval_service.list_runs()
        matches = [
            r
            for r in runs
            if (spec and r.agent == spec) or (project_name and project_name in (r.agent or ""))
        ]
        matches.sort(key=lambda r: r.timestamp or "", reverse=True)
        if matches:
            r = matches[0]
            last_run = {
                "eval_name": r.eval_name,
                "overall_score": r.overall_score,
                "timestamp": r.timestamp,
                "passed": r.overall_score >= EVAL_PASS_THRESHOLD,
            }
    except Exception:  # noqa: BLE001 - runs are best-effort
        last_run = None

    return EvalStatus(eval_ready=bool(spec), spec=spec, last_run=last_run)
