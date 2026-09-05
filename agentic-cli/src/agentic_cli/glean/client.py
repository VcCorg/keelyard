"""Glean REST Search client — turns a query into context snippets.

Token mode calls the Glean Client API (``POST /rest/api/v1/search`` with a
bearer token). The response parser is a pure function so it is unit-testable
without a network. SSO mode raises a clear, actionable error (live OAuth token
exchange is a production step).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from agentic_cli.glean.config import GleanConfig


class GleanError(RuntimeError):
    """Raised when Glean is unavailable or a search fails."""


@dataclass
class GleanResult:
    title: str = ""
    url: str = ""
    snippet: str = ""

    def as_text(self) -> str:
        head = self.title or self.url or "result"
        body = self.snippet.strip()
        line = f"### {head}"
        if self.url:
            line += f"\n{self.url}"
        if body:
            line += f"\n{body}"
        return line


def _snippet_text(snip: Any) -> str:
    """Glean snippet shapes vary: {'snippet': {'text': ...}} | {'text': ...} | str."""
    if isinstance(snip, str):
        return snip
    if isinstance(snip, dict):
        inner = snip.get("snippet")
        if isinstance(inner, dict) and inner.get("text"):
            return str(inner["text"])
        if snip.get("text"):
            return str(snip["text"])
    return ""


def parse_search_response(data: Any) -> List[GleanResult]:
    """Pure parser: Glean search JSON → results (defensive to shape drift)."""
    out: List[GleanResult] = []
    results = (data or {}).get("results", []) if isinstance(data, dict) else []
    for r in results if isinstance(results, list) else []:
        if not isinstance(r, dict):
            continue
        doc = r.get("document") if isinstance(r.get("document"), dict) else {}
        title = r.get("title") or doc.get("title") or ""
        url = r.get("url") or doc.get("url") or ""
        snippets = r.get("snippets") or []
        text = ""
        if isinstance(snippets, list):
            parts = [_snippet_text(s) for s in snippets]
            text = "\n".join(p for p in parts if p).strip()
        if not text:
            text = str(r.get("title") or "").strip()
        out.append(GleanResult(title=str(title), url=str(url), snippet=text))
    return out


def _auth_headers(cfg: GleanConfig, user_token: Optional[str]) -> dict:
    """Build the auth headers for a Glean request (token or OAuth/SSO)."""
    headers = {"Content-Type": "application/json"}
    if cfg.is_token_mode:
        headers["Authorization"] = f"Bearer {cfg.api_token}"
        return headers
    # SSO: acquire an OAuth access token (user token if forwarded, else service).
    from agentic_cli.glean.oauth import OAuthError, access_token_for

    try:
        token = access_token_for(cfg, user_token)
    except OAuthError as exc:
        raise GleanError(str(exc)) from exc
    headers["Authorization"] = f"Bearer {token}"
    # Glean requires this to distinguish an OAuth token from a Glean API token.
    headers["X-Glean-Auth-Type"] = "OAUTH"
    return headers


def search(query: str, page_size: int = 5, config: Optional[GleanConfig] = None,
           user_token: Optional[str] = None) -> List[GleanResult]:
    """Run a Glean search (token or SSO). Raises :class:`GleanError` if unavailable."""
    cfg = config or GleanConfig.load()
    reason = cfg.unavailable_reason(user_token)
    if reason:
        raise GleanError(reason)
    if not (query or "").strip():
        raise GleanError("A search query is required.")

    try:
        import httpx
    except Exception as exc:  # noqa: BLE001
        raise GleanError("httpx is not available on the backend.") from exc

    payload = {"query": query.strip(), "pageSize": max(1, min(page_size, 50))}
    headers = _auth_headers(cfg, user_token)

    def _run() -> List[GleanResult]:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(cfg.search_url, json=payload, headers=headers)
        except Exception as exc:  # noqa: BLE001 - network/TLS/timeout
            raise GleanError(f"Could not reach Glean at {cfg.api_url}: {exc}") from exc

        if resp.status_code in (401, 403):
            raise GleanError(f"Glean rejected the token ({resp.status_code}). Check GLEAN_API_TOKEN.")
        if resp.status_code >= 400:
            raise GleanError(f"Glean search failed ({resp.status_code}): {resp.text[:200]}")
        try:
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise GleanError("Glean returned a non-JSON response.") from exc
        return parse_search_response(data)

    # The seam wraps only the round trip. The configuration checks above raise
    # before anything is asked of Glean, and recording those would report reads
    # that never happened — a misconfigured install would look like a busy one.
    from agentic_cli import retrieval

    return retrieval.search(
        "glean", "search", _run, query=query,
        # Counted on what an agent is handed, not on the parsed objects: a repr
        # is neither the text that was sent nor a stable number, since it moves
        # whenever a field is added to the result type.
        text_of=lambda results: "\n\n".join(
            r.as_text() for r in results if r.as_text().strip()),
    )


def search_text(query: str, limit: int = 5, config: Optional[GleanConfig] = None,
                user_token: Optional[str] = None) -> str:
    """Search and render results as a single context block for drafting."""
    results = search(query, page_size=limit, config=config, user_token=user_token)
    blocks = [r.as_text() for r in results[:limit] if r.as_text().strip()]
    return "\n\n".join(blocks).strip()
