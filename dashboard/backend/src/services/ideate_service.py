"""Ideate — requirements gathering → drafted Jira stories.

Turns free-text / document / enterprise-search context into structured,
reviewable user stories that a human approves before anything is pushed to
Jira (draft → review → push). Story drafting uses the configured LLM provider
and degrades to a deterministic heuristic when no provider is configured, so
the module always returns something to review.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Story(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: List[str] = []
    priority: str = "Medium"
    labels: List[str] = []
    issue_type: str = "Story"
    epic_key: Optional[str] = None
    story_points: Optional[float] = None
    assignee: Optional[str] = None
    components: List[str] = []


class DraftResult(BaseModel):
    stories: List[Story]
    source: str  # "llm" | "heuristic"


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""


_PRIORITIES = {"high", "medium", "low"}


def _coerce_story(raw: Dict[str, Any]) -> Optional[Story]:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    priority = str(raw.get("priority") or "Medium").strip().capitalize()
    if priority.lower() not in _PRIORITIES:
        priority = "Medium"
    ac = raw.get("acceptance_criteria") or []
    if isinstance(ac, str):
        ac = [ac]
    labels = raw.get("labels") or []
    if isinstance(labels, str):
        labels = [labels]
    return Story(
        title=title[:200],
        description=str(raw.get("description") or "").strip(),
        acceptance_criteria=[str(x).strip() for x in ac if str(x).strip()],
        priority=priority,
        labels=[str(x).strip() for x in labels if str(x).strip()],
    )


def _parse_stories(text: str) -> List[Story]:
    """Extract a JSON array of stories from an LLM response (tolerant)."""
    if not text:
        return []
    # Strip code fences and locate the first JSON array.
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    out: List[Story] = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict):
            story = _coerce_story(item)
            if story:
                out.append(story)
    return out


def _fallback_stories(context: str, count: int) -> List[Story]:
    """Deterministic drafting when no LLM is configured: one story per bullet /
    sentence in the context, so the module still produces reviewable output."""
    # Prefer explicit bullet lines; else split into sentences.
    lines = [ln.strip(" -*\t") for ln in context.splitlines() if ln.strip(" -*\t")]
    if len(lines) < 2:
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context) if s.strip()]
    stories: List[Story] = []
    for chunk in lines[:count]:
        title = chunk[:80] + ("…" if len(chunk) > 80 else "")
        stories.append(
            Story(
                title=title,
                description=f"As a user, I want: {chunk}",
                acceptance_criteria=["The described behavior is implemented and verified."],
                priority="Medium",
                labels=["ideate"],
            )
        )
    return stories


_STORY_KEYS = {"title", "description", "acceptance_criteria", "priority", "labels",
               "issue_type", "epic_key", "story_points", "assignee", "components"}


def _first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Return the first balanced JSON object in ``text``, or None (tolerant)."""
    cleaned = re.sub(r"```(?:json)?", "", text or "")
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cleaned[start:i + 1])
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        break
        start = cleaned.find("{", start + 1)
    return None


def refine_story(story: "Story", agent_path: str, instruction: str) -> Dict[str, Any]:
    """Refine a single story using a built/imported agent (agents-as-tools).

    Sends the current story + instruction to the agent's ``answer()`` and merges
    any JSON story fields it returns onto the original. If the agent replies with
    prose (no JSON), that prose is folded into the description so nothing is lost.
    """
    from src.services import agent_service

    current = story.model_dump()
    prompt = (
        "You are refining a single Jira user story. Apply the instruction and "
        "return ONLY a JSON object with any of these keys you want to change: "
        f"{sorted(_STORY_KEYS)}.\n\n"
        f"Instruction: {instruction}\n\n"
        f"Current story:\n{json.dumps(current)}\n"
    )
    result = agent_service.test_agent(agent_path, prompt)
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "agent failed"), "story": current}

    text = str(result.get("response", ""))
    obj = _first_json_object(text)
    if obj:
        for k, v in obj.items():
            if k in _STORY_KEYS and v is not None:
                current[k] = v
    elif text.strip():
        current["description"] = (current.get("description", "") +
                                  f"\n\n[agent] {text.strip()}").strip()
    return {"ok": True, "story": Story(**current).model_dump()}


def push_stories(project_key: str, stories: List["Story"], actor: Optional[str] = None) -> Dict[str, Any]:
    """Create approved stories as Jira issues with real field mapping + audit.

    Fetches createmeta once per batch; records one audit row per issue (success
    and failure) under a shared correlation id. Never aborts on a single failure.
    """
    from src.services import ideate_audit, jira_service

    if not project_key:
        raise ValueError("A Jira project key is required")

    correlation_id = ideate_audit.new_correlation_id()
    meta = jira_service.get_create_meta(project_key)

    results: List[Dict[str, Any]] = []
    for s in stories:
        try:
            created = jira_service.create_issue(
                project_key=project_key, summary=s.title, description=s.description,
                issue_type=s.issue_type or "Story", labels=s.labels, priority=s.priority,
                epic_key=s.epic_key, story_points=s.story_points, assignee=s.assignee,
                components=s.components, acceptance_criteria=s.acceptance_criteria, meta=meta)
            results.append({"title": s.title, "ok": True, **created})
            ideate_audit.record_jira_create(
                project_key=project_key, key=created.get("key", ""),
                url=created.get("url", ""), ok=True, title=s.title, actor=actor,
                correlation_id=correlation_id)
        except Exception as e:  # noqa: BLE001 - per-story reporting
            results.append({"title": s.title, "ok": False, "error": str(e)})
            ideate_audit.record_jira_create(
                project_key=project_key, key="", url="", ok=False,
                title=s.title, error=str(e), actor=actor, correlation_id=correlation_id)

    return {"results": results, "created": sum(1 for r in results if r.get("ok")),
            "correlation_id": correlation_id}


def draft_stories(context: str, count: int = 5, model: Optional[str] = None) -> DraftResult:
    """Draft up to ``count`` user stories from gathered requirements."""
    context = (context or "").strip()
    if not context:
        return DraftResult(stories=[], source="heuristic")

    prompt = (
        f"You are a product analyst. From the requirements below, write up to {count} "
        "concise Jira user stories. Return ONLY a JSON array; each item must be an object "
        'with keys: "title" (string), "description" (string, in "As a … I want … so that …" '
        'form), "acceptance_criteria" (array of strings), "priority" ("High"|"Medium"|"Low"), '
        '"labels" (array of strings).\n\nRequirements:\n'
        f"{context}\n"
    )
    try:
        from agentic_cli.llm.factory import get_llm_provider

        provider = get_llm_provider(
            model_name=model,
            system_instruction="You write clear, testable Jira user stories as strict JSON.",
        )
        raw = provider.generate(prompt)
        stories = _parse_stories(raw)
        if stories:
            return DraftResult(stories=stories[:count], source="llm")
    except Exception:  # noqa: BLE001 - any provider/SDK issue → heuristic
        pass

    return DraftResult(stories=_fallback_stories(context, count), source="heuristic")


# ── Enterprise-search gathering (Glean / Confluence via MCP) ─────────────

_MCP_URLS = {
    "glean": "http://localhost:8127/sse",
    "confluence": "http://localhost:8129/sse",
}

_QUERY_KEYS = ("query", "q", "text", "keyword", "question", "search")


def _pick_search_tool(tools: List[Any]) -> Optional[Any]:
    """Choose the best search tool (exact 'search' name, else contains 'search')."""
    exact = [t for t in tools if getattr(t, "name", "").lower() == "search"]
    if exact:
        return exact[0]
    fuzzy = [t for t in tools if "search" in getattr(t, "name", "").lower()]
    return fuzzy[0] if fuzzy else None


def _pick_query_arg(tool: Any) -> str:
    """Find the parameter a search tool expects the query under."""
    schema = getattr(tool, "inputSchema", None) or {}
    props = list((schema.get("properties") or {}).keys())
    for key in _QUERY_KEYS:
        if key in props:
            return key
    return props[0] if props else "query"


def _result_text(result: Any, limit: int) -> str:
    """Join text content items from an MCP tool result."""
    chunks: List[str] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)
    joined = "\n".join(chunks).strip()
    # Cap so we don't overflow the drafting prompt.
    return joined[: limit * 2000] if joined else ""


_TITLE_KEYS = ("title", "name", "summary")
_SNIPPET_KEYS = ("excerpt", "description", "snippet", "body_text", "text", "content")
_URL_KEYS = ("url", "link")


def _nested_link(entry: Dict[str, Any]) -> str:
    """Extract a URL from a nested ``_links`` object (Confluence/Glean shapes)."""
    links = entry.get("_links")
    if isinstance(links, dict):
        for k in ("webui", "self", "download", "tinyui"):
            if links.get(k):
                return str(links[k])
    return ""


def _results_from_json(obj: Any, limit: int) -> List[SearchResult]:
    """Map a parsed JSON payload (dict/list of hits) to SearchResults, defensively."""
    if isinstance(obj, dict):
        entries = obj.get("results") if isinstance(obj.get("results"), list) else [obj]
    elif isinstance(obj, list):
        entries = obj
    else:
        return []
    out: List[SearchResult] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        title = next((str(e[k]) for k in _TITLE_KEYS if e.get(k)), "")
        url = next((str(e[k]) for k in _URL_KEYS if e.get(k)), "") or _nested_link(e)
        snippet = next((str(e[k]) for k in _SNIPPET_KEYS if e.get(k)), "")
        if not (title or url or snippet):
            continue
        out.append(SearchResult(title=title.strip(), url=url.strip(),
                                snippet=snippet.strip()[:1000]))
        if len(out) >= limit:
            break
    return out


def _parse_mcp_results(result: Any, limit: int) -> List[SearchResult]:
    """Turn an MCP tool result into structured SearchResults.

    Each content item is parsed as JSON (Confluence/Glean return JSON blobs);
    non-JSON text degrades to a single snippet-only result so nothing is lost.
    """
    out: List[SearchResult] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            out.append(SearchResult(snippet=text.strip()[:1000]))
            continue
        out.extend(_results_from_json(obj, limit))
        if len(out) >= limit:
            break
    return out[:limit]


def _result_block(r: SearchResult) -> str:
    """Render a SearchResult as a markdown context block for drafting."""
    head = r.title or r.url or "result"
    line = f"### {head}"
    if r.url:
        line += f"\n{r.url}"
    if r.snippet:
        line += f"\n{r.snippet}"
    return line.strip()


def glean_status(user_token: Optional[str] = None) -> Dict[str, Any]:
    """Report how the Glean source will resolve (configured REST vs MCP fallback)."""
    try:
        from agentic_cli.glean import GleanConfig
    except Exception:  # noqa: BLE001
        return {"mode": "mcp", "configured": False, "detail": "Glean package unavailable — using MCP server."}
    cfg = GleanConfig.load()
    reason = cfg.unavailable_reason(user_token)
    if reason is None:
        auth = cfg.auth_mode
        if auth == "sso":
            how = "per-user token" if user_token else "service token"
            detail = f"Configured Glean (SSO · {how}) at {cfg.api_url}"
        else:
            detail = f"Configured Glean (token) at {cfg.api_url}"
        return {"mode": "rest", "configured": True, "auth": auth, "detail": detail}
    # SSO configured but not live here, or unconfigured → MCP fallback.
    return {"mode": "mcp", "configured": cfg.is_configured(), "auth": cfg.auth_mode, "detail": reason}


async def search_results(source: str, query: str, limit: int = 5,
                         user_token: Optional[str] = None) -> List[SearchResult]:
    """Structured enterprise-search results (title / url / snippet) for Ideate.

    All sources (Glean and Confluence) are queried through their MCP servers so
    the dashboard keeps a single client path. Raises a clear RuntimeError when
    the MCP server is unavailable."""
    url = _MCP_URLS.get(source)
    if not url:
        raise ValueError(f"Unknown source '{source}'. Valid: {', '.join(_MCP_URLS)}")
    if not query.strip():
        raise ValueError("A search query is required")

    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("MCP client library is not available on the backend.") from exc

    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                tool = _pick_search_tool(tools)
                if not tool:
                    raise RuntimeError(f"No search tool exposed by the {source} MCP server.")
                arg = _pick_query_arg(tool)
                result = await session.call_tool(tool.name, {arg: query})
                if getattr(result, "isError", False):
                    text = "".join(
                        (getattr(i, "text", "") or "")
                        for i in (getattr(result, "content", None) or [])
                    ).strip()
                    raise RuntimeError(text or f"The {source} MCP server returned an error.")
                return _parse_mcp_results(result, limit)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001 - unreachable server, timeout, etc.
        raise RuntimeError(f"Could not reach the {source} MCP server: {exc}") from exc


async def search_source(source: str, query: str, limit: int = 5,
                        user_token: Optional[str] = None) -> str:
    """Gather context text for Ideate — structured results rendered as blocks.

    Thin wrapper over :func:`search_results` for callers (e.g. the agent tool
    loop) that want a single context string rather than structured hits."""
    results = await search_results(source, query, limit=limit, user_token=user_token)
    blocks = [b for b in (_result_block(r) for r in results) if b]
    return "\n\n".join(blocks).strip()


def extract_text(content: bytes, filename: str) -> str:
    """Extract text from an uploaded requirements document (best-effort)."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception:  # noqa: BLE001 - no pypdf / unreadable PDF
            return ""
    # Text-like formats.
    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception:  # noqa: BLE001
        return ""
