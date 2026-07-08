"""Ideate tools — the registry the ReAct loop dispatches against.

Each ToolSpec wraps an async callable. Integration tools reuse existing
services (Glean/Confluence search, Jira search/create). Mutating tools
(``mutating=True``) are auto-audited through ``ideate_audit`` after a successful
call, so the agent's side effects are traceable exactly like the manual push.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

# Indirection so tests can monkeypatch the search entrypoint cleanly.
from src.services.ideate_service import search_source as _search_source


@dataclass
class ToolContext:
    project_key: str = ""
    actor: Optional[str] = None
    user_token: Optional[str] = None
    correlation_id: Optional[str] = None
    # Built/imported agents injected as tools: each {"name", "path"}.
    agents: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ToolSpec:
    name: str
    kind: str  # "integration" | "agent"
    description: str
    params: Dict[str, Any]
    mutating: bool
    run: Callable[[Dict[str, Any], ToolContext], Awaitable[Dict[str, Any]]]


# ── Tool implementations ─────────────────────────────────────────────────────

async def _glean_search(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    text = await _search_source("glean", args.get("query", ""), limit=args.get("limit", 5),
                                user_token=ctx.user_token)
    return {"text": text}


async def _confluence_search(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    text = await _search_source("confluence", args.get("query", ""), limit=args.get("limit", 5),
                                user_token=ctx.user_token)
    return {"text": text}


async def _jira_search(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    from src.services import jira_service
    resp = jira_service.list_my_domain_issues(max_results=args.get("limit", 20))
    issues = [{"key": i.key, "summary": i.summary, "status": i.status} for i in resp.issues]
    return {"issues": issues, "total": resp.total, "error": resp.error}


async def _jira_create_issue(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    from src.services import jira_service
    return jira_service.create_issue(
        project_key=ctx.project_key,
        summary=args.get("title") or args.get("summary") or "",
        description=args.get("description", ""),
        issue_type=args.get("issue_type", "Story"),
        labels=args.get("labels"),
        priority=args.get("priority"),
        epic_key=args.get("epic_key"),
        story_points=args.get("story_points"),
        assignee=args.get("assignee"),
        components=args.get("components"),
        acceptance_criteria=args.get("acceptance_criteria"),
    )


_SEARCH_PARAMS = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
_CREATE_PARAMS = {"type": "object", "properties": {
    "title": {"type": "string"}, "description": {"type": "string"},
    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
    "issue_type": {"type": "string"}}, "required": ["title"]}
_AGENT_PARAMS = {"type": "object", "properties": {"message": {"type": "string"}},
                 "required": ["message"]}


def agent_tool_name(name: str) -> str:
    """Deterministic, model-safe tool name for an injected agent."""
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return f"agent_{slug or 'agent'}"


def _make_agent_tool(name: str, path: str) -> ToolSpec:
    async def _run(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        from src.services import agent_service
        message = args.get("message") or args.get("query") or ""
        result = await asyncio.to_thread(agent_service.test_agent, path, message)
        if result.get("ok"):
            return {"text": result.get("response", "")}
        return {"error": result.get("error", "agent failed")}

    return ToolSpec(agent_tool_name(name), "agent",
                    f"Ask the '{name}' agent for help drafting or refining stories.",
                    _AGENT_PARAMS, False, _run)


def list_tools(ctx: ToolContext) -> List[ToolSpec]:
    """Return the enabled tool catalog for the given scope."""
    tools: List[ToolSpec] = [
        ToolSpec("glean_search", "integration", "Search Glean enterprise knowledge.",
                 _SEARCH_PARAMS, False, _glean_search),
        ToolSpec("confluence_search", "integration", "Search Confluence pages.",
                 _SEARCH_PARAMS, False, _confluence_search),
        ToolSpec("jira_search", "integration", "List the user's open Jira issues in scope.",
                 {"type": "object", "properties": {}}, False, _jira_search),
        ToolSpec("jira_create_issue", "integration",
                 "Create a Jira issue in the target project (mutating).",
                 _CREATE_PARAMS, True, _jira_create_issue),
    ]
    for a in ctx.agents or []:
        name, path = a.get("name", ""), a.get("path", "")
        if name and path:
            tools.append(_make_agent_tool(name, path))
    return tools


async def call_tool(name: str, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Dispatch a tool call. Mutating tools are audited on success.

    Returns the tool's result dict, or ``{"error": msg}`` on failure / unknown tool.
    """
    spec = next((t for t in list_tools(ctx) if t.name == name), None)
    if spec is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        result = await spec.run(args, ctx)
    except Exception as e:  # noqa: BLE001 - surface tool errors to the loop
        if spec.mutating and name == "jira_create_issue":
            _audit_jira_create(args, ctx, ok=False, error=str(e), created=None)
        return {"error": str(e)}
    if spec.mutating and name == "jira_create_issue":
        _audit_jira_create(args, ctx, ok=True, error=None, created=result)
    return result


def _audit_jira_create(args: Dict[str, Any], ctx: ToolContext, *, ok: bool,
                       error: Optional[str], created: Optional[Dict[str, Any]]) -> None:
    from src.services import ideate_audit
    ideate_audit.record_jira_create(
        project_key=ctx.project_key,
        key=(created or {}).get("key", ""),
        url=(created or {}).get("url", ""),
        ok=ok, title=args.get("title") or args.get("summary") or "",
        error=error, actor=ctx.actor, correlation_id=ctx.correlation_id)
