"""Jira integration — routed entirely through the Jira MCP server.

All Jira REST access goes through the ``jira-mcp`` server (SSE) rather than a
separate HTTP client in the dashboard, so there is a single Jira client
implementation. The MCP server authenticates with the shared PAT
(``JIRA_PERSONAL_ACCESS_TOKEN`` / ``JIRA_SERVER_URL``); the dashboard only reads
those env vars to report configuration status and build browse links.

  - ``JIRA_SERVER_URL``: base URL of the Jira Server/Data Center instance
  - ``JIRA_PERSONAL_ACCESS_TOKEN``: PAT (used by the MCP server)
  - ``JIRA_MCP_URL``: SSE endpoint of the Jira MCP (default ``http://localhost:8128/sse``)

The set of Jira projects is derived from the onboarded domains (each domain's
``jira_project`` key), so "my work items" are scoped to what has actually been
onboarded rather than the whole instance. Issues are those where the PAT owner
is the assignee (JQL ``assignee = currentUser()``).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

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


def parse_jira_project_key(value: str) -> str:
    """Extract a Jira project key from a URL or return the raw value.

    Handles common Jira Server/Data Center URL patterns:
      - plain key: CWHE
      - browse URL: https://jira.example.com/browse/CWHE
      - projects URL: https://jira.example.com/projects/CWHE
      - board URL: https://jira.example.com/secure/RapidBoard.jspa?projectKey=CWHE
    """
    if not value:
        return ""
    value = value.strip()
    if "/" not in value:
        return value
    try:
        parsed = urlparse(value)
        qs = parse_qs(parsed.query)
        for key, vals in qs.items():
            if key.lower() in {"projectkey", "project", "selectedprojectkey"} and vals:
                return vals[0].strip()
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[-2].lower() in {"projects", "browse"}:
            return path_parts[-1].strip()
    except Exception:
        pass
    return value


def _domain_project_keys() -> list[str]:
    """Collect distinct Jira project keys from all onboarded domains."""
    try:
        from src.services.domain_service import list_domains

        keys: list[str] = []
        for d in list_domains():
            key = parse_jira_project_key((d.jira_project or "").strip()).upper()
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


def _jira_mcp_url() -> str:
    return os.environ.get("JIRA_MCP_URL", "http://localhost:8128/sse")


async def _acall_tool(tool: str, args: dict) -> Any:
    """Call a Jira MCP tool over SSE and return its parsed JSON payload."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(_jira_mcp_url()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            text = "".join(
                (getattr(item, "text", "") or "")
                for item in (getattr(result, "content", None) or [])
            )
            if getattr(result, "isError", False):
                raise RuntimeError(text or f"Jira MCP tool '{tool}' failed")
            return json.loads(text) if text.strip() else None


def _run(coro) -> Any:
    """Run an async coroutine from sync code, safe inside or outside a loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    box: dict = {}

    def worker() -> None:
        try:
            box["value"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller thread
            box["error"] = exc

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _call_tool(tool: str, args: dict) -> Any:
    """Synchronous wrapper around a Jira MCP tool call."""
    return _run(_acall_tool(tool, args))


def _root_exception(exc: BaseException) -> BaseException:
    """Unwrap an ExceptionGroup/TaskGroup to its first leaf cause.

    The MCP SSE client runs inside an anyio task group, so transport failures
    surface as ``ExceptionGroup`` ("unhandled errors in a TaskGroup") — an
    opaque message for users. Drill down to the underlying error.
    """
    seen = 0
    while getattr(exc, "exceptions", None) and seen < 10:
        exc = exc.exceptions[0]  # type: ignore[attr-defined]
        seen += 1
    return exc


def _friendly_mcp_error(exc: BaseException) -> str:
    """Turn a Jira MCP transport failure into an actionable message."""
    root = _root_exception(exc)
    msg = str(root) or root.__class__.__name__
    low = msg.lower()
    connection_like = (
        isinstance(root, (ConnectionError, OSError, TimeoutError))
        or any(s in low for s in (
            "connect", "refused", "timed out", "timeout", "unreachable",
            "all connection attempts failed", "name or service not known",
        ))
    )
    if connection_like:
        return (
            f"Couldn't reach the Jira service. The Jira MCP server "
            f"({_jira_mcp_url()}) isn't responding — start it (or check "
            f"JIRA_MCP_URL), then refresh."
        )
    return msg[:300]


def get_create_meta(project_key: str) -> CreateMeta:
    """Fetch+parse create screen metadata via MCP; empty CreateMeta on any error."""
    if not is_configured() or not project_key:
        return CreateMeta(project_key=project_key)
    try:
        data = _call_tool("get_create_meta", {"project_key": project_key})
        return _parse_create_meta(data or {}, project_key)
    except Exception:  # noqa: BLE001
        return CreateMeta(project_key=project_key)


def list_issue_types(project_key: str) -> list[str]:
    return get_create_meta(project_key).issue_types


def list_epics(project_key: str, max_results: int = 100) -> list[JiraEpic]:
    """List open epics (key + summary) for the epic picker."""
    if not is_configured() or not project_key:
        return []
    jql = f'project = "{project_key}" AND issuetype = Epic AND statusCategory != Done ORDER BY updated DESC'
    try:
        data = _call_tool("search_issues", {"jql": jql, "max_results": max_results})
    except Exception:  # noqa: BLE001
        return []
    return [JiraEpic(key=i.get("key", ""), summary=i.get("summary", ""))
            for i in (data or {}).get("issues", [])]


def create_issue(
    project_key: str,
    summary: str,
    description: str = "",
    issue_type: str = "Story",
    labels: Optional[list[str]] = None,
    priority: Optional[str] = None,
    epic_key: Optional[str] = None,
    story_points: Optional[float] = None,
    assignee: Optional[str] = None,
    components: Optional[list[str]] = None,
    acceptance_criteria: Optional[list[str]] = None,
    meta: Optional[CreateMeta] = None,
) -> dict:
    """Create a Jira issue with real field mapping. Returns {key, url}. Raises on failure."""
    if not is_configured():
        raise RuntimeError(
            "Jira is not configured. Set JIRA_SERVER_URL and "
            "JIRA_PERSONAL_ACCESS_TOKEN on the dashboard backend."
        )
    if not project_key:
        raise ValueError("A Jira project key is required")
    if not summary:
        raise ValueError("A summary is required")
    if meta is None:
        meta = get_create_meta(project_key)

    fields = _build_issue_fields(
        project_key=project_key, summary=summary, description=description,
        issue_type=issue_type, labels=labels, priority=priority, epic_key=epic_key,
        story_points=story_points, assignee=assignee, components=components,
        acceptance_criteria=acceptance_criteria, meta=meta)

    result = _call_tool("create_issue", {"fields": fields}) or {}
    key = result.get("key", "")
    if not key:
        raise RuntimeError("Jira create returned no issue key")
    url = result.get("url") or (f"{_server_url()}/browse/{key}" if key else "")
    return {"key": key, "url": url}


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

    try:
        data = _call_tool("search_issues", {"jql": jql, "max_results": max_results}) or {}
    except Exception as e:  # noqa: BLE001 - surface any transport error to the UI
        return MyIssuesResponse(
            configured=True, projects=projects, jql=jql,
            error=_friendly_mcp_error(e),
        )

    issues: list[JiraIssue] = []
    for item in data.get("issues", []):
        issues.append(
            JiraIssue(
                key=item.get("key", ""),
                summary=item.get("summary", ""),
                status=item.get("status", ""),
                status_category=item.get("status_category", ""),
                priority=item.get("priority", ""),
                issuetype=item.get("issuetype", ""),
                project=item.get("project", ""),
                created=item.get("created", ""),
                updated=item.get("updated", ""),
                labels=item.get("labels", []) or [],
                link=item.get("link", f"{_server_url()}/browse/{item.get('key', '')}"),
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

    try:
        item = _call_tool("get_issue", {"issue_key": key})
    except RuntimeError as e:
        msg = str(e)
        if "404" in msg or "not found" in msg.lower():
            return None
        raise RuntimeError(str(e)[:200]) from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(str(e)[:200]) from e

    if not item:
        return None

    project = item.get("project")
    project_key = project.get("key", "") if isinstance(project, dict) else (project or "")
    return JiraIssueDetail(
        key=item.get("key", key),
        summary=item.get("summary", ""),
        status=item.get("status", ""),
        status_category=item.get("status_category", ""),
        priority=item.get("priority", ""),
        issuetype=item.get("issuetype", ""),
        project=project_key,
        created=item.get("created", ""),
        updated=item.get("updated", ""),
        labels=item.get("labels", []) or [],
        link=item.get("link", f"{_server_url()}/browse/{item.get('key', key)}"),
        description=_description_text(item.get("description")),
    )
