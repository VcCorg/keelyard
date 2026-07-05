"""Ideate API — requirements gathering and story drafting.

Draft → review → push: this module drafts reviewable Jira stories from
gathered requirements. Pushing approved stories to Jira is a separate,
confirmed step (added alongside the source connectors).
"""

from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.services import ideate_service as svc

router = APIRouter(prefix="/api/ideate", tags=["ideate"])


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
async def search(req: SearchRequest):
    """Gather context text — configured Glean REST (preferred) or MCP fallback."""
    try:
        text = await svc.search_source(req.source, req.query, limit=req.limit)
        return {"source": req.source, "query": req.query, "text": text, "chars": len(text)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/glean-status")
async def glean_status():
    """How the Glean source resolves: configured REST API vs MCP fallback."""
    return svc.glean_status()


class PushStory(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: List[str] = []
    priority: Optional[str] = None
    labels: List[str] = []


class PushRequest(BaseModel):
    project_key: str
    stories: List[PushStory]
    issue_type: str = "Story"


@router.get("/jira-status")
async def jira_status():
    """Jira availability + candidate project keys for pushing stories."""
    from src.services import jira_service

    status = jira_service.get_status()
    return {"configured": status.configured, "projects": status.projects}


@router.post("/push")
async def push(req: PushRequest):
    """Create the approved stories as Jira issues (draft → review → push)."""
    from src.services import jira_service

    if not req.stories:
        raise HTTPException(status_code=400, detail="No stories to push")
    if not req.project_key:
        raise HTTPException(status_code=400, detail="A Jira project key is required")

    results = []
    for s in req.stories:
        # Fold acceptance criteria into the issue description.
        desc = s.description
        if s.acceptance_criteria:
            desc += "\n\nAcceptance criteria:\n" + "\n".join(f"- {a}" for a in s.acceptance_criteria)
        try:
            created = jira_service.create_issue(
                project_key=req.project_key,
                summary=s.title,
                description=desc,
                issue_type=req.issue_type,
                labels=s.labels,
                priority=s.priority,
            )
            results.append({"title": s.title, "ok": True, **created})
        except Exception as e:  # noqa: BLE001 - report per-story, don't abort the batch
            results.append({"title": s.title, "ok": False, "error": str(e)})

    return {"results": results, "created": sum(1 for r in results if r.get("ok"))}
