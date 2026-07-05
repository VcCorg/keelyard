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


class DraftResult(BaseModel):
    stories: List[Story]
    source: str  # "llm" | "heuristic"


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


def _glean_configured_search(query: str, limit: int, user_token: Optional[str] = None) -> Optional[str]:
    """Query the org-configured Glean (token or SSO) via its REST API.

    Returns text on success, ``None`` if Glean isn't configured for a live query
    (so the caller can fall back to the MCP server). Raises RuntimeError on a
    real failure (bad token, unreachable host). ``user_token`` is the signed-in
    user's forwarded access token, enabling per-user SSO (on-behalf-of).
    """
    try:
        from agentic_cli.glean import GleanConfig, GleanError, search_text
    except Exception:  # noqa: BLE001 - package optional
        return None
    cfg = GleanConfig.load()
    if cfg.unavailable_reason(user_token):
        return None  # not configured for a live query → let MCP handle it
    try:
        return search_text(query, limit=limit, config=cfg, user_token=user_token)
    except GleanError as exc:
        raise RuntimeError(str(exc)) from exc


async def search_source(source: str, query: str, limit: int = 5,
                        user_token: Optional[str] = None) -> str:
    """Gather context text for Ideate.

    For Glean, prefer the org-configured Glean REST API (``dva init glean``);
    fall back to a Glean/Confluence MCP server when Glean isn't configured for a
    live query. ``user_token`` (the signed-in user's forwarded access token)
    enables per-user SSO. Degrades with a clear RuntimeError when nothing is
    available."""
    url = _MCP_URLS.get(source)
    if not url:
        raise ValueError(f"Unknown source '{source}'. Valid: {', '.join(_MCP_URLS)}")
    if not query.strip():
        raise ValueError("A search query is required")

    if source == "glean":
        text = _glean_configured_search(query, limit, user_token)
        if text is not None:
            return text
        # else: not configured for a live query — try the MCP server below.

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
                return _result_text(result, limit)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001 - unreachable server, timeout, etc.
        raise RuntimeError(f"Could not reach the {source} MCP server: {exc}") from exc


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
