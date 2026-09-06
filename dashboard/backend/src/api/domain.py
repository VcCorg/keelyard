"""Domain onboarding API — thin proxy over the agentic-cli core logic.

Reads + simple mutations call `agentic_cli.tracker` via the domain_service.
Long-running steps stream the real `keel domain ...` CLI output over SSE.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services import domain_service as svc
from src.services import onboarding_service as onboarding

router = APIRouter(prefix="/api/domains", tags=["domains"])


class DocTypeRequest(BaseModel):
    doc_type: str


# ── Request bodies ──────────────────────────────────────────────────────────

class CreateDomainRequest(BaseModel):
    domain: str
    product: str
    description: Optional[str] = None
    jira_project: Optional[str] = None
    jira_board: Optional[str] = None
    bitbucket_project: Optional[str] = None
    bitbucket_url: Optional[str] = None
    github_org: Optional[str] = None
    github_url: Optional[str] = None
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
    github_org: Optional[str] = None
    github_url: Optional[str] = None
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
async def api_delete_product(
    name: str,
    cascade: bool = Query(False),
    wipe_meta: bool = Query(False),
):
    """Remove a product.

    By default this blocks (409) if the product still has domains. Pass
    ``cascade=true`` to also remove all of its domains, and ``wipe_meta=true``
    to additionally delete the on-disk meta-repos (testing/cleanup helper).
    """
    if cascade:
        result = svc.delete_product_cascade(name, wipe_meta=wipe_meta)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Product '{name}' not found")
        n = len(result["domains_removed"])
        wiped = len(result["wiped_paths"])
        msg = f"Product '{result['product']}' removed (+{n} domain(s)"
        msg += f", wiped {wiped} meta-repo(s))" if wipe_meta else ")"
        return ActionResponse(success=True, message=msg)

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
    """Run `keel domain fetch-repos <slug> --all` and stream output."""
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
    """Run `keel domain add-docs <slug> --all` and stream output."""
    args = ["add-docs", slug, "--all", "--limit", str(limit)]
    if filter:
        args += ["--filter", filter]
    return _sse(args)


@router.get("/{slug}/gen-skills/stream")
async def api_gen_skills_stream(slug: str, role: Optional[str] = Query(None)):
    """Run `keel domain gen-skills <slug>` and stream output."""
    args = ["gen-skills", slug]
    if role:
        args += ["--role", role]
    return _sse(args)


# ── Persona skills: review + regenerate ─────────────────────────────────────

class PersonaContent(BaseModel):
    id: str
    content: str


@router.get("/{slug}/personas", response_model=list[svc.GeneratedPersonaInfo])
async def api_list_generated_personas(slug: str):
    """Review: list persona skills generated into the domain meta-repo."""
    return svc.list_generated_personas(slug)


@router.get("/{slug}/personas/{persona_id}", response_model=PersonaContent)
async def api_get_persona_content(slug: str, persona_id: str):
    """Review: read a single generated persona's SKILL.md content."""
    content = svc.get_persona_content(slug, persona_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found for '{slug}'")
    return PersonaContent(id=persona_id, content=content)


@router.get("/{slug}/regen-personas/stream")
async def api_regen_personas_stream(
    slug: str,
    persona: Optional[list[str]] = Query(None),
    enrich: bool = Query(False),
):
    """Repo/domain-level: regenerate personas into the domain meta-repo.

    Available to all users — regenerates the effective catalog (or a subset)
    into <domain-meta>/.agents/skills/personas/.
    """
    args = ["regen-personas", slug]
    for pid in persona or []:
        args += ["--persona", pid]
    if enrich:
        args.append("--enrich")
    return _sse(args)


@router.get("/{slug}/scaffold-paths", response_model=svc.ScaffoldPaths)
async def api_scaffold_paths(slug: str):
    """Resolve the domain context-repo and meta-repo paths (+ existence).

    Lets the UI offer "Open in IDE" to review generated files after scaffolding.
    """
    return svc.get_scaffold_paths(slug)


@router.get("/{slug}/init/stream")
async def api_init_stream(
    slug: str,
    force: bool = Query(False),
    no_kg: bool = Query(False),
    kg_timeout: int = Query(20, ge=1, le=300),
    product_meta: Optional[str] = Query(None),
    code_assist_tool: str = Query("auto"),
):
    """Run `keel domain init <slug>` (unified context-meta) and stream output.

    Produces a single `<slug>-context-meta` repo (context + meta + skills) and
    bridges skills into the code assist tool. `force=true` overwrites; `no_kg`
    skips the KG query; `product_meta` references the product meta as a
    submodule; `code_assist_tool` controls where skills land ('auto' detects).
    """
    args = ["init", slug, "--code-assist-tool", code_assist_tool]
    if force:
        args.append("--force")
    if no_kg:
        args.append("--no-kg")
    args += ["--kg-timeout", str(kg_timeout)]
    if product_meta:
        args += ["--product-meta", product_meta]
    return _sse(args)


@router.get("/{slug}/init-context/stream")
async def api_init_context_stream(
    slug: str,
    force: bool = Query(False),
    no_kg: bool = Query(False),
    kg_timeout: int = Query(20, ge=1, le=300),
):
    """DEPRECATED: use `/init/stream`. Routes to the unified `keel domain init`
    so old clients still produce the merged context-meta repo.
    """
    args = ["init", slug]
    if force:
        args.append("--force")
    if no_kg:
        args.append("--no-kg")
    args += ["--kg-timeout", str(kg_timeout)]
    return _sse(args)


@router.get("/{slug}/init-meta/stream")
async def api_init_meta_stream(
    slug: str,
    product_meta: Optional[str] = Query(None),
    force: bool = Query(False),
):
    """DEPRECATED: use `/init/stream`. Routes to the unified `keel domain init`.

    `product_meta` references the product meta-repo as a submodule; `force`
    overwrites an existing repo.
    """
    args = ["init", slug]
    if product_meta:
        args += ["--product-meta", product_meta]
    if force:
        args.append("--force")
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
    name: str,
    org_methodology: Optional[str] = Query(None),
    force: bool = Query(False),
):
    """Run `keel product init-meta <name>` and stream output.

    Pass `force=true` to overwrite an existing product meta-repo (the CLI
    cannot prompt in this non-interactive context).
    """
    args = ["init-meta", name]
    if org_methodology:
        args += ["--org-methodology", org_methodology]
    if force:
        args.append("--force")
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


# ── Product persona catalog (admin tier) ────────────────────────────────────

class PersonaSectionBody(BaseModel):
    title: str
    body: str = ""


class AddPersonaRequest(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    sections: list[PersonaSectionBody] = []
    ai_enrich: bool = False


@router.get("/products/{name}/personas", response_model=list[svc.PersonaCatalogInfo])
async def api_product_personas(name: str):
    """List the effective persona catalog (built-ins + product customs)."""
    return svc.list_product_personas_catalog(name)


@router.post("/products/{name}/personas", response_model=svc.PersonaCatalogInfo)
async def api_product_add_persona(name: str, req: AddPersonaRequest):
    """Add (or replace) a product-specific persona. Admin action."""
    try:
        return svc.add_product_persona_entry(
            product=name,
            persona_id=req.id,
            label=req.label,
            description=req.description,
            sections=[s.model_dump() for s in req.sections],
            ai_enrich=req.ai_enrich,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/products/{name}/personas/{persona_id}", response_model=ActionResponse)
async def api_product_remove_persona(name: str, persona_id: str):
    """Remove a product-specific persona. Admin action."""
    if svc.remove_product_persona_entry(name, persona_id):
        return ActionResponse(success=True, message=f"Persona '{persona_id}' removed")
    raise HTTPException(
        status_code=404,
        detail=f"No custom persona '{persona_id}' in product '{name.upper()}'",
    )


@router.get("/products/{name}/regen-personas/stream")
async def api_product_regen_personas_stream(name: str, enrich: bool = Query(False)):
    """Product-level: regenerate personas across all domains in the product.

    Admin action — iterates every domain under the product and runs
    `keel domain regen-personas <slug>`, streaming a combined log.
    """
    async def gen():
        async for line in svc.stream_product_regen_personas(name, enrich=enrich):
            if line.startswith("__EXIT__"):
                yield {"event": "done", "data": line.split(" ", 1)[1].strip()}
            else:
                yield {"event": "log", "data": line}

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------
# Onboarding: classify → extract → review → finalize → score
#
# `extract` and `finalize` stream through the CLI like every other wizard step,
# so their logic is never duplicated here. Everything else is a read model over
# the review proposal on disk, which stays the single store.
# ---------------------------------------------------------------------------

@router.get("/{slug}/onboarding/docs", response_model=list[onboarding.DocClassification])
async def api_onboarding_docs(slug: str):
    """Tracked docs with what each one is *for*, and whether it has moved."""
    return onboarding.list_classified_docs(slug)


@router.patch("/{slug}/onboarding/docs/{page_id}", response_model=ActionResponse)
async def api_set_doc_type(slug: str, page_id: str, body: DocTypeRequest):
    """Correct one doc's type. Stored at full confidence; survives re-syncing."""
    if not onboarding.set_doc_type(slug, page_id, body.doc_type):
        raise HTTPException(status_code=400, detail=f"Unknown doc type '{body.doc_type}'")
    return ActionResponse(ok=True, message=f"{page_id} → {body.doc_type}")


@router.get("/{slug}/onboarding/proposal", response_model=onboarding.ReviewProposal)
async def api_onboarding_proposal(slug: str):
    """The review worklist. Held entries carry risk kinds, never text."""
    return onboarding.get_proposal(slug)


@router.post("/{slug}/onboarding/verdicts", response_model=onboarding.VerdictResult)
async def api_onboarding_verdicts(slug: str, body: onboarding.VerdictRequest):
    """Accept or reject reviewed instructions."""
    result = onboarding.record_verdicts(slug, body)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No meta-repo for '{slug}'")
    return result


@router.get("/{slug}/onboarding/extract/stream")
async def api_extract_stream(slug: str, repos: bool = Query(True), all_types: bool = Query(False)):
    """Run `keel domain extract <slug>` and stream output."""
    args = ["extract", slug, "--repos" if repos else "--no-repos"]
    if all_types:
        args.append("--all-types")
    return _sse(args)


@router.get("/{slug}/onboarding/finalize/stream")
async def api_finalize_stream(slug: str):
    """Run `keel domain finalize <slug>` and stream output."""
    return _sse(["finalize", slug])


@router.get("/readiness/portfolio", response_model=list[onboarding.PortfolioRow])
async def api_portfolio(product: Optional[str] = Query(None)):
    """Every domain's readiness, worst first.

    Declared before /{slug}/readiness so the literal path is not swallowed by
    the slug route.
    """
    return onboarding.get_portfolio(product)


@router.get("/{slug}/readiness")
async def api_readiness(slug: str):
    """The eight-dimension scorecard, computed live."""
    card = onboarding.get_readiness(slug)
    if card is None:
        raise HTTPException(status_code=404, detail=f"No meta-repo for '{slug}'")
    return card


@router.get("/{slug}/drift", response_model=list[onboarding.DriftSignal])
async def api_drift(slug: str):
    """Every drift signal for one domain, in one shape."""
    return onboarding.get_drift(slug)


@router.get("/{slug}/knowledge-map", response_model=onboarding.KnowledgeMap)
async def api_knowledge_map(slug: str):
    """Sources → instruction kinds → context artifacts, with staleness."""
    return onboarding.get_knowledge_map(slug)
