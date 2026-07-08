"""Ideate API — requirements gathering and story drafting.

Draft → review → push: this module drafts reviewable Jira stories from
gathered requirements. Pushing approved stories to Jira is a separate,
confirmed step (added alongside the source connectors).
"""

import json
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services import ideate_service as svc
from src.services.ideate_agent import run_agent as _run_agent
from src.services.ideate_tools import ToolContext, agent_tool_name, list_tools

router = APIRouter(prefix="/api/ideate", tags=["ideate"])


def _forwarded_user_token(request: Request) -> Optional[str]:
    """The signed-in user's OAuth access token forwarded by the SSO proxy.

    oauth2-proxy sets ``X-Auth-Request-Access-Token`` (with --pass-access-token);
    some proxies use an Authorization bearer. Enables per-user Glean SSO.
    """
    h = request.headers
    tok = h.get("x-auth-request-access-token") or h.get("x-forwarded-access-token")
    if tok:
        return tok.strip()
    authz = h.get("authorization", "")
    if authz.lower().startswith("bearer "):
        return authz[7:].strip()
    return None


def _forwarded_user_email(request: Request) -> Optional[str]:
    """The signed-in user's email forwarded by the SSO proxy, if present."""
    h = request.headers
    email = h.get("x-auth-request-email") or h.get("x-forwarded-email")
    return email.strip() if email else None


def _get_activity(command: str, limit: int):
    """Query the central audit trail; empty list if unavailable."""
    try:
        from agentic_cli.tracker import get_activity
        return get_activity(command=command, limit=limit)
    except Exception:  # noqa: BLE001
        return []


class DraftRequest(BaseModel):
    context: str
    count: int = 5
    model: Optional[str] = None


@router.post("/draft", response_model=svc.DraftResult)
async def draft(req: DraftRequest):
    """Draft user stories from gathered requirement context."""
    if req.count < 1 or req.count > 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    return svc.draft_stories(req.context, count=req.count, model=req.model)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Extract text from an uploaded requirements document."""
    content = await file.read()
    text = svc.extract_text(content, file.filename or "")
    if not text:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the file (unsupported or empty).",
        )
    return {"filename": file.filename, "text": text, "chars": len(text)}


class SearchRequest(BaseModel):
    source: str  # "glean" | "confluence"
    query: str
    limit: int = 5


@router.post("/search")
async def search(req: SearchRequest, request: Request):
    """Gather structured results (title/url/snippet) — Glean REST or MCP fallback."""
    tok = _forwarded_user_token(request)
    try:
        results = await svc.search_results(req.source, req.query, limit=req.limit, user_token=tok)
        return {"source": req.source, "query": req.query,
                "results": [r.model_dump() for r in results]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/glean-status")
async def glean_status(request: Request):
    """How the Glean source resolves: configured REST API vs MCP fallback."""
    tok = _forwarded_user_token(request)
    return svc.glean_status(user_token=tok)


class PushStory(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: List[str] = []
    priority: Optional[str] = None
    labels: List[str] = []
    issue_type: str = "Story"
    epic_key: Optional[str] = None
    story_points: Optional[float] = None
    assignee: Optional[str] = None
    components: List[str] = []


class PushRequest(BaseModel):
    project_key: str
    stories: List[PushStory]


@router.get("/jira-status")
async def jira_status():
    """Jira availability + candidate project keys for pushing stories."""
    from src.services import jira_service

    status = jira_service.get_status()
    return {"configured": status.configured, "projects": status.projects}


@router.post("/push")
async def push(req: PushRequest, request: Request):
    """Create approved stories as Jira issues with real field mapping + audit."""
    if not req.stories:
        raise HTTPException(status_code=400, detail="No stories to push")
    if not req.project_key:
        raise HTTPException(status_code=400, detail="A Jira project key is required")

    actor = _forwarded_user_email(request)
    stories = [svc.Story(title=s.title, description=s.description,
        acceptance_criteria=s.acceptance_criteria, priority=s.priority or "Medium",
        labels=s.labels, issue_type=s.issue_type, epic_key=s.epic_key,
        story_points=s.story_points, assignee=s.assignee, components=s.components)
        for s in req.stories]
    return svc.push_stories(req.project_key, stories, actor=actor)


@router.get("/jira-meta")
async def jira_meta(project: str):
    """Issue types, epics, and available custom fields for a project."""
    from src.services import jira_service

    if not project:
        raise HTTPException(status_code=400, detail="A project key is required")
    meta = jira_service.get_create_meta(project)
    epics = jira_service.list_epics(project)
    return {"project": project,
            "issue_types": meta.issue_types or ["Story", "Task", "Bug", "Spike"],
            "epics": [e.model_dump() for e in epics],
            "fields": {"epic_link": meta.epic_link_field is not None,
                       "story_points": meta.story_points_field is not None,
                       "acceptance_criteria": meta.acceptance_criteria_field is not None,
                       "components": meta.has_components, "assignee": meta.has_assignee,
                       "priority": meta.has_priority}}


@router.get("/audit")
async def audit(limit: int = 50):
    """Recent Ideate mutating actions from the central audit trail."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return {"actions": _get_activity(command="ideate", limit=limit)}


@router.get("/tools")
async def tools(project: str = ""):
    """The enabled tool catalog for a scope (no run callables)."""
    specs = list_tools(ToolContext(project_key=project))
    return {"tools": [{"name": s.name, "kind": s.kind, "description": s.description,
                       "params": s.params, "mutating": s.mutating} for s in specs]}


def _discover_agents():
    """Discover built/imported agent projects; empty list if unavailable."""
    try:
        from src.services.agent_service import discover_agent_projects
        return discover_agent_projects()
    except Exception:  # noqa: BLE001
        return []


def _agent_has_answer(path: str) -> bool:
    """True if the project exposes an ``answer()`` entrypoint (agents-as-tools)."""
    try:
        from src.services.agent_service import get_agent_eval_spec
        return get_agent_eval_spec(path) is not None
    except Exception:  # noqa: BLE001
        return False


@router.get("/agents")
async def agents():
    """Built/imported agents that can be injected as tools (expose answer())."""
    out = []
    for a in _discover_agents():
        if _agent_has_answer(a.path):
            out.append({"name": a.name, "path": a.path, "use_case": a.use_case,
                        "tool_name": agent_tool_name(a.name)})
    return {"agents": out}


class AgentRef(BaseModel):
    name: str
    path: str


class AgentRunRequest(BaseModel):
    task: str = "Draft Jira user stories from the gathered context."
    context: str = ""
    project_key: str = ""
    model: Optional[str] = None
    agents: List[AgentRef] = []


@router.post("/agent/run")
async def agent_run(req: AgentRunRequest, request: Request):
    """Run the ReAct agent, streaming its trace + final stories as SSE."""
    from src.services import ideate_audit

    actor = _forwarded_user_email(request)
    tok = _forwarded_user_token(request)
    ctx = ToolContext(project_key=req.project_key, actor=actor, user_token=tok,
                      correlation_id=ideate_audit.new_correlation_id(),
                      agents=[a.model_dump() for a in req.agents])

    async def event_generator():
        try:
            async for ev in _run_agent(req.task, req.context, ctx, model=req.model):
                yield {"event": ev.type, "data": ev.model_dump_json()}
        except Exception as e:  # noqa: BLE001
            yield {"event": "error", "data": json.dumps({"type": "error", "error": str(e)})}

    return EventSourceResponse(event_generator())


class RefineRequest(BaseModel):
    story: svc.Story
    agent: AgentRef
    instruction: str = "Improve this story."


@router.post("/agent/refine")
async def agent_refine(req: RefineRequest):
    """Refine a single story card using a built/imported agent."""
    import asyncio
    return await asyncio.to_thread(
        svc.refine_story, req.story, req.agent.path, req.instruction)
