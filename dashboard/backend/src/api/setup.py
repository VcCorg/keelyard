"""CLI setup API — report config status and stream `keel init ...` steps."""

from typing import Optional

from fastapi import Depends, APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from src.services import setup_service as svc
from src.services.run_registry import registry

router = APIRouter(prefix="/api/setup", tags=["setup"])


def _require_configure():
    """Setup/init streams mutate platform config — require platform:configure."""
    from agentic_cli.auth import PERM_PLATFORM_CONFIGURE
    from src.services.auth_service import require

    return require(PERM_PLATFORM_CONFIGURE)


@router.get("/status", response_model=svc.SetupStatus)
async def setup_status():
    """Report which CLI init steps are done (drives the sidebar + banners)."""
    return svc.get_setup_status()


@router.get("/doctor", response_model=svc.DoctorReport)
async def setup_doctor(probe: bool = Query(False, description="Also probe integration host reachability")):
    """Structured `keel doctor` diagnostics — powers the wizard's health panel.

    Read-only, like /status: reports which dependencies are healthy so a
    first-run user can self-diagnose provider/KG/integration problems from the UI.
    """
    return svc.get_doctor_report(probe=probe)


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
    _principal=Depends(_require_configure()),
):
    """Run `keel init workspace --code <> --docs <>` (non-interactive)."""
    if not code.strip() or not docs.strip():
        raise HTTPException(status_code=400, detail="Both code and docs directories are required.")
    return _stream("init workspace", svc.init_workspace_args(code.strip(), docs.strip()))


@router.get("/init/vertex/stream")
async def init_vertex_stream(
    project_id: str = Query(..., description="Google Cloud project ID"),
    location: str = Query("us-central1", description="Google Cloud region"),
    model: Optional[str] = Query(None, description="Default model"),
    _principal=Depends(_require_configure()),
):
    """Run `keel init vertex-ai --project-id <> --skip-auth` (non-interactive).

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
    _principal=Depends(_require_configure()),
):
    """Run `keel kg init --provider neo4j ...` (non-interactive)."""
    if not password.strip():
        raise HTTPException(status_code=400, detail="Neo4j password is required.")
    return _stream("kg init (neo4j)", svc.kg_init_neo4j_args(uri.strip(), username.strip(), password))


@router.get("/init/integration/{kind}/stream")
async def init_integration_stream(
    kind: str,
    url: str = Query(..., description="Integration server URL"),
    token: str = Query(..., description="Personal access token"),
    _principal=Depends(_require_configure()),
):
    """Run `keel init <jira|bitbucket|confluence> --url <> --token <>`.

    Persists the credentials to ~/.keel/.env (chmod 600) via the CLI so they are
    loaded automatically — no shell export required.
    """
    if not url.strip() or not token.strip():
        raise HTTPException(status_code=400, detail="Both URL and token are required.")
    try:
        args = svc.init_integration_args(kind, url.strip(), token.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _stream(f"init {kind}", args)


@router.get("/init/builtin-model/stream")
async def init_builtin_model_stream(
    force: bool = Query(False, description="Re-download even if present"),
    _principal=Depends(_require_configure()),
):
    """Run `keel init builtin-model` — one-time ~400MB download with progress."""
    return _stream("init builtin-model", svc.init_builtin_model_args(force=force))


@router.get("/init/devin/stream")
async def init_devin_stream(
    api_key: str = Query(..., description="Devin API key"),
    _principal=Depends(_require_configure()),
):
    """Run `keel init devin --api-key <>` — persists DEVIN_API_KEY to ~/.keel/.env."""
    if not api_key.strip():
        raise HTTPException(status_code=400, detail="A Devin API key is required.")
    return _stream("init devin", svc.init_devin_args(api_key.strip()))


@router.get("/init/glean/stream")
async def init_glean_stream(
    url: str = Query(..., description="Glean instance URL"),
    mode: str = Query("token", description="'token' or 'sso'"),
    token: str = Query("", description="Glean API token (token mode)"),
    issuer: str = Query("", description="OIDC issuer (sso mode)"),
    client_id: str = Query("", description="OAuth client id (sso mode)"),
    client_secret: str = Query("", description="OAuth client secret (sso service token)"),
    scope: str = Query("", description="OAuth scope (sso mode, optional)"),
    _principal=Depends(_require_configure()),
):
    """Run `keel init glean ...` — configure Glean via API token or SSO/OAuth."""
    if not url.strip():
        raise HTTPException(status_code=400, detail="The Glean instance URL is required.")
    m = (mode or "token").strip().lower()
    if m == "sso":
        if not (issuer.strip() and client_id.strip()):
            raise HTTPException(status_code=400, detail="SSO mode needs issuer and client_id.")
    elif not token.strip():
        raise HTTPException(status_code=400, detail="Token mode needs a Glean API token.")
    return _stream("init glean", svc.init_glean_args(
        url.strip(), mode=m, token=token.strip(), issuer=issuer.strip(), client_id=client_id.strip(),
        client_secret=client_secret.strip(), scope=scope.strip()))
