"""Jira integration — list issues assigned to the current user.

Reuses the same environment credentials as the Jira MCP server:

  - ``JIRA_SERVER_URL``: base URL of the Jira Server/Data Center instance
  - ``JIRA_PERSONAL_ACCESS_TOKEN``: PAT used as a Bearer token
  - ``JIRA_VERIFY_SSL``: optional, ``0``/``false`` to disable TLS verification

The set of Jira projects is derived from the onboarded domains (each domain's
``jira_project`` key), so "my work items" are scoped to what has actually been
onboarded rather than the whole instance. Issues are those where the PAT owner
is the assignee (JQL ``assignee = currentUser()``).
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
from pydantic import BaseModel


# ── Transport shapes ─────────────────────────────────────────────────────────

class JiraStatus(BaseModel):
    configured: bool
    server_url: str = ""
    projects: list[str] = []


class CreateMeta(BaseModel):
    project_key: str
    issue_types: list[str] = []
    epic_link_field: Optional[str] = None
    story_points_field: Optional[str] = None
    acceptance_criteria_field: Optional[str] = None
    has_components: bool = False
    has_assignee: bool = False
    has_priority: bool = False


class JiraEpic(BaseModel):
    key: str
    summary: str = ""


class JiraIssue(BaseModel):
    key: str
    summary: str
    status: str = ""
    status_category: str = ""
    priority: str = ""
    issuetype: str = ""
    project: str = ""
    updated: str = ""
    created: str = ""
    labels: list[str] = []
    link: str = ""


class JiraIssueDetail(JiraIssue):
    description: str = ""


class MyIssuesResponse(BaseModel):
    configured: bool
    projects: list[str] = []
    jql: str = ""
    total: int = 0
    issues: list[JiraIssue] = []
    error: Optional[str] = None


# ── Config ───────────────────────────────────────────────────────────────────

def _server_url() -> str:
    return (os.environ.get("JIRA_SERVER_URL") or "").rstrip("/")


def _token() -> str:
    return os.environ.get("JIRA_PERSONAL_ACCESS_TOKEN") or ""


def _verify_ssl() -> bool:
    return (os.environ.get("JIRA_VERIFY_SSL", "true").lower() not in {"0", "false", "no"})


def is_configured() -> bool:
    return bool(_server_url() and _token())


def _domain_project_keys() -> list[str]:
    """Collect distinct Jira project keys from all onboarded domains."""
    try:
        from src.services.domain_service import list_domains

        keys: list[str] = []
        for d in list_domains():
            key = (d.jira_project or "").strip().upper()
            if key and key not in keys:
                keys.append(key)
        return keys
    except Exception:
        return []


# ── Public API ───────────────────────────────────────────────────────────────

def get_status() -> JiraStatus:
    return JiraStatus(
        configured=is_configured(),
        server_url=_server_url(),
        projects=_domain_project_keys(),
    )


def _parse_create_meta(data: dict, project_key: str) -> CreateMeta:
    """Turn a Jira /issue/createmeta payload into a typed CreateMeta.

    Detects custom-field ids for Epic Link, Story Points, and Acceptance
    Criteria by name; records whether components/assignee/priority are on the
    create screen.
    """
    project = next((p for p in (data.get("projects") or []) if p.get("key") == project_key), None)
    if not project:
        return CreateMeta(project_key=project_key)

    issue_types = [it.get("name", "") for it in project.get("issuetypes", []) if it.get("name")]
    epic = points = ac = None
    has_components = has_assignee = has_priority = False
    for it in project.get("issuetypes", []):
        for fid, meta in (it.get("fields") or {}).items():
            name = (meta.get("name") or "").strip().lower()
            if fid == "components":
                has_components = True
            elif fid == "assignee":
                has_assignee = True
            elif fid == "priority":
                has_priority = True
            elif name == "epic link" and not epic:
                epic = fid
            elif name == "story points" and not points:
                points = fid
            elif name == "acceptance criteria" and not ac:
                ac = fid
    return CreateMeta(
        project_key=project_key, issue_types=issue_types,
        epic_link_field=epic, story_points_field=points,
        acceptance_criteria_field=ac, has_components=has_components,
        has_assignee=has_assignee, has_priority=has_priority,
    )


def _build_issue_fields(
    project_key: str, summary: str, description: str = "", issue_type: str = "Story",
    labels: Optional[list[str]] = None, priority: Optional[str] = None,
    epic_key: Optional[str] = None, story_points: Optional[float] = None,
    assignee: Optional[str] = None, components: Optional[list[str]] = None,
    acceptance_criteria: Optional[list[str]] = None, meta: Optional[CreateMeta] = None,
) -> dict:
    """Assemble the Jira `fields` dict, mapping real fields when supported and
    degrading gracefully. meta=None → permissive for standard fields; custom
    fields omitted (AC appended to description)."""
    labels = labels or []
    components = components or []
    acceptance_criteria = [a for a in (acceptance_criteria or []) if a]
    fields: dict = {"project": {"key": project_key}, "summary": summary[:255],
                    "issuetype": {"name": issue_type or "Story"}}

    def ok(flag: bool) -> bool:
        return flag if meta is not None else True

    if labels:
        fields["labels"] = [l.replace(" ", "-") for l in labels if l]
    if priority and ok(getattr(meta, "has_priority", False)):
        fields["priority"] = {"name": priority}
    if assignee and ok(getattr(meta, "has_assignee", False)):
        fields["assignee"] = {"name": assignee}
    if components and ok(getattr(meta, "has_components", False)):
        fields["components"] = [{"name": c} for c in components if c]
    if epic_key and getattr(meta, "epic_link_field", None):
        fields[meta.epic_link_field] = epic_key
    if story_points is not None and getattr(meta, "story_points_field", None):
        fields[meta.story_points_field] = story_points

    ac_field = getattr(meta, "acceptance_criteria_field", None)
    desc = description or ""
    if acceptance_criteria:
        if ac_field:
            fields[ac_field] = "\n".join(acceptance_criteria)
        else:
            desc = (desc + "\n\nAcceptance criteria:\n"
                    + "\n".join(f"- {a}" for a in acceptance_criteria)).strip()
    if desc:
        fields["description"] = desc
    return fields


def create_issue(
    project_key: str,
    summary: str,
    description: str = "",
    issue_type: str = "Story",
    labels: Optional[list[str]] = None,
    priority: Optional[str] = None,
) -> dict:
    """Create a Jira issue and return {key, url}. Raises on failure."""
    if not is_configured():
        raise RuntimeError(
            "Jira is not configured. Set JIRA_SERVER_URL and "
            "JIRA_PERSONAL_ACCESS_TOKEN on the dashboard backend."
        )
    if not project_key:
        raise ValueError("A Jira project key is required")
    if not summary:
        raise ValueError("A summary is required")

    fields: dict = {
        "project": {"key": project_key},
        "summary": summary[:255],
        "issuetype": {"name": issue_type or "Story"},
    }
    if description:
        fields["description"] = description
    if labels:
        # Jira labels cannot contain spaces.
        fields["labels"] = [l.replace(" ", "-") for l in labels if l]
    if priority:
        fields["priority"] = {"name": priority}

    with httpx.Client(
        base_url=f"{_server_url()}/rest/api/2",
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        verify=_verify_ssl(),
        timeout=30.0,
    ) as client:
        resp = client.post("/issue", json={"fields": fields})
        if resp.status_code >= 300:
            raise RuntimeError(f"Jira create failed ({resp.status_code}): {resp.text[:300]}")
        key = resp.json().get("key", "")

    return {"key": key, "url": f"{_server_url()}/browse/{key}" if key else ""}


def list_my_domain_issues(
    statuses: Optional[list[str]] = None,
    max_results: int = 100,
) -> MyIssuesResponse:
    """Return issues assigned to the current user across onboarded domain projects.

    Args:
        statuses: optional status-category filter; defaults to open work
            (excludes Done).
        max_results: cap on issues returned.
    """
    projects = _domain_project_keys()

    if not is_configured():
        return MyIssuesResponse(
            configured=False,
            projects=projects,
            error=(
                "Jira is not configured. Set JIRA_SERVER_URL and "
                "JIRA_PERSONAL_ACCESS_TOKEN on the dashboard backend."
            ),
        )

    # Build JQL scoped to onboarded projects, assigned to the PAT owner.
    clauses = ["assignee = currentUser()"]
    if projects:
        joined = ", ".join(f'"{p}"' for p in projects)
        clauses.append(f"project in ({joined})")
    if statuses:
        joined_status = ", ".join(f'"{s}"' for s in statuses)
        clauses.append(f"status in ({joined_status})")
    else:
        clauses.append("statusCategory != Done")
    jql = " AND ".join(clauses) + " ORDER BY updated DESC"

    fields = (
        "summary,status,priority,assignee,issuetype,project,"
        "created,updated,labels"
    )
    try:
        with httpx.Client(
            base_url=f"{_server_url()}/rest/api/2",
            headers={
                "Authorization": f"Bearer {_token()}",
                "Accept": "application/json",
            },
            verify=_verify_ssl(),
            timeout=30.0,
        ) as client:
            resp = client.get(
                "/search",
                params={"jql": jql, "maxResults": max_results, "fields": fields},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response is not None else str(e)
        return MyIssuesResponse(
            configured=True, projects=projects, jql=jql,
            error=f"Jira returned {e.response.status_code}: {detail}",
        )
    except Exception as e:  # noqa: BLE001 - surface any transport error to the UI
        return MyIssuesResponse(
            configured=True, projects=projects, jql=jql, error=str(e)[:300]
        )

    issues: list[JiraIssue] = []
    for item in data.get("issues", []):
        f = item.get("fields", {})
        status = f.get("status") or {}
        issues.append(
            JiraIssue(
                key=item.get("key", ""),
                summary=f.get("summary", ""),
                status=status.get("name", ""),
                status_category=(status.get("statusCategory") or {}).get("name", ""),
                priority=(f.get("priority") or {}).get("name", ""),
                issuetype=(f.get("issuetype") or {}).get("name", ""),
                project=(f.get("project") or {}).get("key", ""),
                created=f.get("created", ""),
                updated=f.get("updated", ""),
                labels=f.get("labels", []) or [],
                link=f"{_server_url()}/browse/{item.get('key', '')}",
            )
        )

    return MyIssuesResponse(
        configured=True,
        projects=projects,
        jql=jql,
        total=data.get("total", len(issues)),
        issues=issues,
    )


def _description_text(raw) -> str:
    """Best-effort plain text from a Jira description (str for API v2)."""
    if isinstance(raw, str):
        return raw.strip()
    return ""


def get_issue(key: str) -> Optional[JiraIssueDetail]:
    """Fetch a single issue's detail (incl. description). None if not found.

    Raises RuntimeError with a readable message on config/transport errors so
    callers can surface it.
    """
    if not is_configured():
        raise RuntimeError(
            "Jira is not configured. Set JIRA_SERVER_URL and "
            "JIRA_PERSONAL_ACCESS_TOKEN on the dashboard backend."
        )

    fields = (
        "summary,status,priority,assignee,issuetype,project,"
        "created,updated,labels,description"
    )
    try:
        with httpx.Client(
            base_url=f"{_server_url()}/rest/api/2",
            headers={
                "Authorization": f"Bearer {_token()}",
                "Accept": "application/json",
            },
            verify=_verify_ssl(),
            timeout=30.0,
        ) as client:
            resp = client.get(f"/issue/{key}", params={"fields": fields})
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            item = resp.json()
    except httpx.HTTPStatusError as e:
        code = e.response.status_code if e.response is not None else "?"
        raise RuntimeError(f"Jira returned {code} for {key}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(str(e)[:200]) from e

    f = item.get("fields", {})
    status = f.get("status") or {}
    return JiraIssueDetail(
        key=item.get("key", key),
        summary=f.get("summary", ""),
        status=status.get("name", ""),
        status_category=(status.get("statusCategory") or {}).get("name", ""),
        priority=(f.get("priority") or {}).get("name", ""),
        issuetype=(f.get("issuetype") or {}).get("name", ""),
        project=(f.get("project") or {}).get("key", ""),
        created=f.get("created", ""),
        updated=f.get("updated", ""),
        labels=f.get("labels", []) or [],
        link=f"{_server_url()}/browse/{item.get('key', key)}",
        description=_description_text(f.get("description")),
    )
