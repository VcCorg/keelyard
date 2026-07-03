"""Ideate API — requirements gathering and story drafting.

Draft → review → push: this module drafts reviewable Jira stories from
gathered requirements. Pushing approved stories to Jira is a separate,
confirmed step (added alongside the source connectors).
"""

from typing import Optional

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
