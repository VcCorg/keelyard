"""Build components API — catalog endpoints for agent ingredients.

Exposes the building blocks used to assemble an agent (tools, retrievers,
databases, models) so the Build section can surface every ingredient.
"""

from fastapi import APIRouter

from src.services import build_components_service as svc

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
