"""Code onboarding API — streams `dva code onboard ...` over SSE."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from src.services import code_service as svc
from src.services.run_registry import registry

router = APIRouter(prefix="/api/code", tags=["code"])


@router.get("/onboard/stream")
async def onboard_stream(
    repo: Optional[str] = Query(None, description="Git repo URL to clone and onboard"),
    path: Optional[str] = Query(None, description="Local project path to onboard"),
    repo_slug: Optional[str] = Query(None, description="Repo slug from a domain's linked repos"),
    domain: Optional[str] = Query(None),
    kg: bool = Query(False),
    extract_entities: bool = Query(False),
    use_domain_skills: bool = Query(False),
    link_kg: bool = Query(False),
    graphify: bool = Query(False),
    agent: bool = Query(False),
    code_assist_tool: str = Query("generic"),
):
    """Run `dva code onboard ...` and stream output over SSE."""
    if not (repo or path or repo_slug):
        raise HTTPException(
            status_code=400,
            detail="Provide one of: repo (git URL), path (local), or repo_slug (+domain).",
        )
    if repo_slug and not domain:
        raise HTTPException(status_code=400, detail="repo_slug requires a domain.")

    opts = svc.OnboardOptions(
        repo=repo, path=path, repo_slug=repo_slug, domain=domain,
        kg=kg, extract_entities=extract_entities, use_domain_skills=use_domain_skills,
        link_kg=link_kg, graphify=graphify, agent=agent, code_assist_tool=code_assist_tool,
    )
    args = svc.build_onboard_args(opts)
    cmd = svc.resolve_cli_command() + args

    target = repo or path or repo_slug or "project"
    label = f"onboard {target}"
    rec = registry.create(kind="code", label=label, cmd=cmd)

    async def gen():
        async for event in registry.stream(rec, cmd):
            yield event

    return EventSourceResponse(gen())
