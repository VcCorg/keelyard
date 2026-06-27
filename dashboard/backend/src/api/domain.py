"""Domain onboarding API — thin proxy over the agentic-cli core logic.

Reads + simple mutations call `agentic_cli.tracker` via the domain_service.
Long-running steps stream the real `dva domain ...` CLI output over SSE.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services import domain_service as svc

router = APIRouter(prefix="/api/domains", tags=["domains"])


# ── Request bodies ──────────────────────────────────────────────────────────

class CreateDomainRequest(BaseModel):
    domain: str
    product: str
    description: Optional[str] = None
    jira_project: Optional[str] = None
    jira_board: Optional[str] = None
    bitbucket_project: Optional[str] = None
    bitbucket_url: Optional[str] = None
    confluence_space: Optional[str] = None
    confluence_url: Optional[str] = None
    jira_dashboard: Optional[str] = None
    tags: list[str] = []


class CreateProductRequest(BaseModel):
    name: str
    description: Optional[str] = None
    tags: list[str] = []


class UpdateProductRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class UpdateDomainRequest(BaseModel):
    domain: Optional[str] = None
    product: Optional[str] = None
    description: Optional[str] = None
    jira_project: Optional[str] = None
    jira_board: Optional[str] = None
    bitbucket_project: Optional[str] = None
    bitbucket_url: Optional[str] = None
    confluence_space: Optional[str] = None
    confluence_url: Optional[str] = None
    jira_dashboard: Optional[str] = None
    tags: Optional[list[str]] = None


class LinkRepoRequest(BaseModel):
    repo_slug: str
    repo_name: Optional[str] = None
    clone_url: Optional[str] = None


class AddDocRequest(BaseModel):
    source_page_id: str
    source_space_key: Optional[str] = None
    title: Optional[str] = None
    source_version: int = 0


class ActionResponse(BaseModel):
    success: bool
    message: str


# ── Products ────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[svc.ProductInfo])
async def api_list_products():
    """List registered products (for the onboarding wizard's product picker)."""
    try:
        return svc.list_products()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products", response_model=svc.ProductInfo)
async def api_create_product(req: CreateProductRequest):
    try:
        return svc.create_product(req.name, description=req.description, tags=req.tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/products/{name}", response_model=svc.ProductInfo)
async def api_update_product(name: str, req: UpdateProductRequest):
    updated = svc.update_product(name, description=req.description, tags=req.tags)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Product '{name}' not found")
    return updated


@router.delete("/products/{name}", response_model=ActionResponse)
async def api_delete_product(name: str):
    try:
        result = svc.delete_product(name)
    except svc.ProductInUseError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Product '{name}' not found")
    return ActionResponse(success=True, message=f"Product '{name.upper()}' removed")


# ── Domains CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=list[svc.DomainInfo])
async def api_list_domains(product: Optional[str] = Query(None)):
    try:
        return svc.list_domains(product=product)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=svc.DomainDetail)
async def api_create_domain(req: CreateDomainRequest):
    try:
        return svc.create_domain(**req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}", response_model=svc.DomainDetail)
async def api_get_domain(slug: str):
    detail = svc.get_domain_detail(slug)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")
    return detail


@router.patch("/{slug}", response_model=svc.DomainDetail)
async def api_update_domain(slug: str, req: UpdateDomainRequest):
    try:
        detail = svc.update_domain(slug, **req.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not detail:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")
    return detail


@router.delete("/{slug}", response_model=ActionResponse)
async def api_delete_domain(slug: str):
    if svc.delete_domain(slug):
        return ActionResponse(success=True, message=f"Domain '{slug}' removed")
    raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")


# ── Repos ───────────────────────────────────────────────────────────────────

@router.get("/{slug}/repos", response_model=list[svc.RepoInfo])
async def api_list_repos(slug: str):
    detail = svc.get_domain_detail(slug)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")
    return detail.repos


@router.get("/{slug}/bitbucket-repos", response_model=list[svc.BitbucketRepoCandidate])
async def api_bitbucket_candidates(
    slug: str,
    limit: int = Query(500, le=1000),
    filter: Optional[str] = Query(None),
):
    """Preview repos in the domain's Bitbucket project for selection."""
    try:
        return svc.list_bitbucket_candidates(slug, limit=limit, filter_text=filter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bitbucket fetch failed: {e}")


@router.post("/{slug}/repos", response_model=ActionResponse)
async def api_link_repo(slug: str, req: LinkRepoRequest):
    if not svc.get_domain_detail(slug):
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")
    added = svc.link_repo(slug, req.repo_slug, repo_name=req.repo_name, clone_url=req.clone_url)
    return ActionResponse(
        success=added,
        message=f"Linked '{req.repo_slug}'" if added else f"'{req.repo_slug}' already linked",
    )


@router.delete("/{slug}/repos/{repo_slug}", response_model=ActionResponse)
async def api_unlink_repo(slug: str, repo_slug: str):
    if svc.unlink_repo(slug, repo_slug):
        return ActionResponse(success=True, message=f"Unlinked '{repo_slug}'")
    raise HTTPException(status_code=404, detail=f"Repo '{repo_slug}' not linked to '{slug}'")


# ── Docs ────────────────────────────────────────────────────────────────────

@router.get("/{slug}/docs", response_model=list[svc.DocInfo])
async def api_list_docs(slug: str):
    detail = svc.get_domain_detail(slug)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")
    return detail.docs


@router.get("/{slug}/confluence-pages", response_model=list[svc.ConfluencePageCandidate])
async def api_confluence_candidates(
    slug: str,
    limit: int = Query(200, le=1000),
    filter: Optional[str] = Query(None),
):
    """Preview pages in the domain's Confluence space/URL for selection."""
    try:
        return svc.list_confluence_candidates(slug, limit=limit, filter_text=filter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Confluence fetch failed: {e}")


@router.post("/{slug}/docs", response_model=ActionResponse)
async def api_add_doc(slug: str, req: AddDocRequest):
    if not svc.get_domain_detail(slug):
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")
    added = svc.add_doc(
        slug,
        source_page_id=req.source_page_id,
        source_space_key=req.source_space_key,
        title=req.title,
        source_version=req.source_version,
    )
    return ActionResponse(
        success=added,
        message=f"Tracked page '{req.source_page_id}'" if added else "Already tracked",
    )


@router.delete("/{slug}/docs/{page_id}", response_model=ActionResponse)
async def api_remove_doc(slug: str, page_id: str):
    if svc.remove_doc(slug, page_id):
        return ActionResponse(success=True, message=f"Removed doc '{page_id}'")
    raise HTTPException(status_code=404, detail=f"Doc '{page_id}' not tracked on '{slug}'")


# ── Streaming long-running steps (SSE) ──────────────────────────────────────

def _sse(args: list[str]) -> EventSourceResponse:
    async def gen():
        async for line in svc.stream_domain_command(args):
            if line.startswith("__EXIT__"):
                code = line.split(" ", 1)[1].strip()
                yield {"event": "done", "data": code}
            else:
                yield {"event": "log", "data": line}

    return EventSourceResponse(gen())


@router.get("/{slug}/fetch-repos/stream")
async def api_fetch_repos_stream(
    slug: str,
    limit: int = Query(500, le=1000),
    filter: Optional[str] = Query(None),
):
    """Run `dva domain fetch-repos <slug> --all` and stream output."""
    args = ["fetch-repos", slug, "--all", "--limit", str(limit)]
    if filter:
        args += ["--filter", filter]
    return _sse(args)


@router.get("/{slug}/add-docs/stream")
async def api_add_docs_stream(
    slug: str,
    limit: int = Query(200, le=1000),
    filter: Optional[str] = Query(None),
):
    """Run `dva domain add-docs <slug> --all` and stream output."""
    args = ["add-docs", slug, "--all", "--limit", str(limit)]
    if filter:
        args += ["--filter", filter]
    return _sse(args)


@router.get("/{slug}/gen-skills/stream")
async def api_gen_skills_stream(slug: str, role: Optional[str] = Query(None)):
    """Run `dva domain gen-skills <slug>` and stream output."""
    args = ["gen-skills", slug]
    if role:
        args += ["--role", role]
    return _sse(args)


@router.get("/{slug}/init-context/stream")
async def api_init_context_stream(slug: str):
    """Run `dva domain init-context <slug>` and stream output."""
    return _sse(["init-context", slug])


@router.get("/{slug}/init-meta/stream")
async def api_init_meta_stream(slug: str, product_meta: Optional[str] = Query(None)):
    """Run `dva domain init-meta <slug>` and stream output.

    Pass `product_meta` (URL/path) to reference the product meta-repo as a
    submodule (threads the outer-loop shared tier into the domain meta).
    """
    args = ["init-meta", slug]
    if product_meta:
        args += ["--product-meta", product_meta]
    return _sse(args)


# ── Product tier (meta-repo, governance, exceptions) ─────────────────────────

def _sse_product(args: list[str]) -> EventSourceResponse:
    async def gen():
        async for line in svc.stream_product_command(args):
            if line.startswith("__EXIT__"):
                yield {"event": "done", "data": line.split(" ", 1)[1].strip()}
            else:
                yield {"event": "log", "data": line}

    return EventSourceResponse(gen())


@router.get("/products/{name}/init-meta/stream")
async def api_product_init_meta_stream(
    name: str, org_methodology: Optional[str] = Query(None)
):
    """Run `dva product init-meta <name>` and stream output."""
    args = ["init-meta", name]
    if org_methodology:
        args += ["--org-methodology", org_methodology]
    return _sse_product(args)


class AddExceptionRequest(BaseModel):
    rule: str
    reason: str
    scope: str
    owner: str
    expires: Optional[str] = None


@router.get("/products/{name}/governance", response_model=svc.GovernanceInfo)
async def api_product_governance(name: str):
    """Read governance.yaml + crosswalk.yaml from the product meta-repo."""
    return svc.get_product_governance(name)


@router.get("/products/{name}/exceptions", response_model=list[svc.ExceptionInfo])
async def api_product_exceptions(name: str):
    """List waivers in the product exceptions ledger."""
    return svc.list_product_exceptions(name)


@router.post("/products/{name}/exceptions", response_model=svc.ExceptionInfo)
async def api_product_add_exception(name: str, req: AddExceptionRequest):
    """Record a governance waiver in the product exceptions ledger."""
    try:
        return svc.add_product_exception(
            product=name, rule=req.rule, reason=req.reason,
            scope=req.scope, owner=req.owner, expires=req.expires or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
