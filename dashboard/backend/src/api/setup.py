"""CLI setup API — report config status and stream `dva init ...` steps."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from src.services import setup_service as svc
from src.services.run_registry import registry

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status", response_model=svc.SetupStatus)
async def setup_status():
    """Report which CLI init steps are done (drives the sidebar + banners)."""
    return svc.get_setup_status()


def _stream(label: str, args: list[str]) -> EventSourceResponse:
    cmd = svc.resolve_cli_command() + args
    rec = registry.create(kind="cli", label=label, cmd=cmd)

    async def gen():
        async for event in registry.stream(rec, cmd):
            yield event

    return EventSourceResponse(gen())


@router.get("/init/workspace/stream")
async def init_workspace_stream(
    code: str = Query(..., description="Code workspace directory"),
    docs: str = Query(..., description="Docs workspace directory"),
):
    """Run `dva init workspace --code <> --docs <>` (non-interactive)."""
    if not code.strip() or not docs.strip():
        raise HTTPException(status_code=400, detail="Both code and docs directories are required.")
    return _stream("init workspace", svc.init_workspace_args(code.strip(), docs.strip()))


@router.get("/init/vertex/stream")
async def init_vertex_stream(
    project_id: str = Query(..., description="Google Cloud project ID"),
    location: str = Query("us-central1", description="Google Cloud region"),
    model: Optional[str] = Query(None, description="Default model"),
):
    """Run `dva init vertex-ai --project-id <> --skip-auth` (non-interactive).

    gcloud Application Default Credentials login is interactive — run
    `gcloud auth application-default login` in the Terminal page if needed.
    """
    if not project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required.")
    return _stream("init vertex-ai", svc.init_vertex_args(project_id.strip(), location.strip(), (model or "").strip()))


@router.get("/init/neo4j/stream")
async def init_neo4j_stream(
    uri: str = Query("bolt://localhost:7687", description="Neo4j connection URI"),
    username: str = Query("neo4j", description="Neo4j username"),
    password: str = Query(..., description="Neo4j password"),
):
    """Run `dva kg init --provider neo4j ...` (non-interactive)."""
    if not password.strip():
        raise HTTPException(status_code=400, detail="Neo4j password is required.")
    return _stream("kg init (neo4j)", svc.kg_init_neo4j_args(uri.strip(), username.strip(), password))


@router.get("/init/integration/{kind}/stream")
async def init_integration_stream(
    kind: str,
    url: str = Query(..., description="Integration server URL"),
    token: str = Query(..., description="Personal access token"),
):
    """Run `dva init <jira|bitbucket|confluence> --url <> --token <>`.

    Persists the credentials to ~/.dva/.env (chmod 600) via the CLI so they are
    loaded automatically — no shell export required.
    """
    if not url.strip() or not token.strip():
        raise HTTPException(status_code=400, detail="Both URL and token are required.")
    try:
        args = svc.init_integration_args(kind, url.strip(), token.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _stream(f"init {kind}", args)
