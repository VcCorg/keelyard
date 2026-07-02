"""Jira API — surface work items assigned to the current user.

Issues are scoped to the Jira projects of onboarded domains and filtered to
the authenticated PAT owner (assignee = currentUser()).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.services import jira_service as svc
from src.services import workflow_service as wf

router = APIRouter(prefix="/api/jira", tags=["jira"])


@router.get("/status", response_model=svc.JiraStatus)
async def status():
    """Report whether Jira is configured and which domain projects are in scope."""
    return svc.get_status()


@router.get("/my-issues", response_model=svc.MyIssuesResponse)
async def my_issues(
    status: Optional[str] = Query(
        None,
        description="Comma-separated status names to filter by (default: all open work).",
    ),
    max_results: int = Query(100, ge=1, le=200),
):
    """List issues assigned to the current user across onboarded domain projects."""
    statuses = [s.strip() for s in status.split(",") if s.strip()] if status else None
    return svc.list_my_domain_issues(statuses=statuses, max_results=max_results)


@router.get("/issues/{key}/contract", response_model=wf.TaskContract)
async def task_contract(key: str):
    """Assemble the governed Task Contract used by the 'Start work' launcher.

    Resolves the issue's domain, governance rules, Devin snapshot/playbook, and
    local meta-workspace readiness, and computes a branch name + agent prompt.
    """
    try:
        return wf.build_task_contract(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
