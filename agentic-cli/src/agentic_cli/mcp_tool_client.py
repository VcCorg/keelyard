"""MCP Tool Client — call MCP server tools from the CLI.

Routes all external API calls through running MCP servers, centralizing
credential management. The CLI never needs Bitbucket/Confluence tokens;
they live only in the MCP server configuration.

Uses the official MCP Python SDK (mcp) for correct SSE protocol handling:
    1. Opens SSE stream  2. Sends initialize handshake  3. Calls tool
    4. Reads response from SSE stream  5. Closes

Server URLs are configured via environment variables or defaults:
    MCP_BITBUCKET_URL   — default: http://localhost:8126/sse
    MCP_CONFLUENCE_URL  — default: http://localhost:8129/sse
    MCP_GATEWAY_URL     — default: http://localhost:9090/sse (optional)
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Default MCP server URLs (from docker-compose)
DEFAULT_BITBUCKET_URL = "http://localhost:8126/sse"
DEFAULT_CONFLUENCE_URL = "http://localhost:8129/sse"
DEFAULT_GATEWAY_URL = "http://localhost:9090/sse"


class MCPToolError(Exception):
    """Raised when an MCP tool call fails."""

    def __init__(self, message: str, is_connection_error: bool = False):
        super().__init__(message)
        self.is_connection_error = is_connection_error


# ---------------------------------------------------------------------------
# Core async helper — uses the official MCP SDK
# ---------------------------------------------------------------------------

async def _call_tool_async(
    sse_url: str, tool_name: str, arguments: dict, timeout: float = 30.0,
) -> Any:
    """Open an SSE session, initialize, call the tool, parse response.

    The ``timeout`` applies to the entire lifecycle (connect + initialize + call)
    so an unresponsive MCP server cannot hang the dashboard.
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async def _session() -> Any:
        async with sse_client(sse_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)

    result = await asyncio.wait_for(_session(), timeout=timeout)

    if result.isError:
        texts = [c.text for c in result.content if hasattr(c, "text")]
        raise MCPToolError(f"MCP tool error: {' '.join(texts)}")

    texts = [c.text for c in result.content if hasattr(c, "text")]
    combined = "\n".join(texts)

    if not combined:
        return {}

    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        return combined


# ---------------------------------------------------------------------------
# Synchronous wrapper
# ---------------------------------------------------------------------------

def _run_async(coro: Any) -> Any:
    """Run an async coroutine from either a sync or async caller.

    ``asyncio.run()`` raises ``RuntimeError`` when an event loop is already
    running on the current thread (e.g. inside a FastAPI ``async def``
    endpoint). When that happens, execute the coroutine on a dedicated thread
    with its own event loop so the synchronous MCP API stays usable from both
    the CLI and the async dashboard backend.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import threading

    box: dict[str, Any] = {}

    def _runner() -> None:
        try:
            box["result"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 — re-raised on caller thread
            box["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["result"]


def _server_label(sse_url: str) -> str:
    """Short name for the MCP server behind a URL, for readable ledger rows."""
    try:
        host = urlparse(sse_url).netloc or sse_url
    except Exception:  # noqa: BLE001
        return "mcp"
    for name, url in (
        ("bitbucket", _env_url("MCP_BITBUCKET_URL", DEFAULT_BITBUCKET_URL)),
        ("confluence", _env_url("MCP_CONFLUENCE_URL", DEFAULT_CONFLUENCE_URL)),
        ("gateway", _env_url("MCP_GATEWAY_URL", DEFAULT_GATEWAY_URL)),
    ):
        try:
            if urlparse(url).netloc == host:
                return name
        except Exception:  # noqa: BLE001
            continue
    return host


def _env_url(var: str, default: str) -> str:
    return os.environ.get(var, default)


def call_mcp_tool(
    sse_url: str, tool_name: str, arguments: Optional[dict] = None, timeout: float = 30.0,
) -> Any:
    """Call an MCP tool synchronously. Handles connection errors gracefully.

    Every call is recorded to the session context ledger (see
    ``agentic_cli.tracing``) so retrieval is visible to both the provenance
    viewer and context-aware evaluation.

    The session id is read HERE, on the caller's thread, and passed down
    explicitly. ``_run_async`` hops to a fresh ``threading.Thread`` when there
    is already a running loop (the FastAPI dashboard), and ContextVars do not
    cross that boundary - reading it any later yields None from the dashboard
    while working fine from the CLI.
    """
    from agentic_cli import tracing

    session_id = tracing.current_session_id()
    started = time.perf_counter()

    def _elapsed_ms() -> int:
        return int((time.perf_counter() - started) * 1000)

    def _record(status: str, size: int) -> None:
        # record_context_read guards itself, but belt-and-braces here too: a
        # telemetry fault must never surface as a retrieval failure.
        try:
            tracing.record_context_read(
                source="mcp",
                operation=f"{_server_label(sse_url)}/{tool_name}",
                session_id=session_id,
                entity_id=tracing.digest_args(arguments)[:64] if arguments else "",
                size_bytes=size,
                duration_ms=_elapsed_ms(),
                status=status,
                arguments=arguments,
            )
        except Exception:  # noqa: BLE001
            logger.debug("MCP context read not recorded", exc_info=True)

    try:
        result = _run_async(
            _call_tool_async(sse_url, tool_name, arguments or {}, timeout)
        )
    except MCPToolError:
        _record("error", 0)
        raise
    except OSError as e:
        _record("error", 0)
        raise MCPToolError(
            f"Cannot connect to MCP server at {sse_url}. Is the server running? ({e})",
            is_connection_error=True,
        )
    except Exception as e:
        _record("error", 0)
        # ExceptionGroup from anyio wraps connection errors
        msg = str(e)
        if "connect" in msg.lower() or "refused" in msg.lower() or "timed out" in msg.lower():
            raise MCPToolError(
                f"Cannot connect to MCP server at {sse_url}. Is the server running?",
                is_connection_error=True,
            )
        raise MCPToolError(f"MCP call failed: {msg}")

    _record("success", tracing.measure(result))
    return result


# ---------------------------------------------------------------------------
# Legacy MCPToolClient class (kept for test compatibility)
# ---------------------------------------------------------------------------

class MCPToolClient:
    """Synchronous client that calls MCP server tools via SSE transport."""

    def __init__(self, sse_url: str, timeout: float = 30.0):
        self.sse_url = sse_url
        self.timeout = timeout

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def call_tool(self, tool_name: str, arguments: Optional[dict] = None) -> Any:
        return call_mcp_tool(self.sse_url, tool_name, arguments, self.timeout)

    def is_available(self) -> bool:
        """Check if the MCP server is reachable."""
        try:
            from mcp.client.sse import sse_client

            async def _check():
                async with sse_client(self.sse_url) as (read, write):
                    from mcp import ClientSession
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return True

            return _run_async(_check())
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Convenience helpers — typed wrappers for specific MCP tools
# ---------------------------------------------------------------------------

def _get_bb_url() -> str:
    return os.environ.get("MCP_BITBUCKET_URL", DEFAULT_BITBUCKET_URL)


def _get_confluence_url() -> str:
    return os.environ.get("MCP_CONFLUENCE_URL", DEFAULT_CONFLUENCE_URL)


def parse_project_key(value: str) -> str:
    """Extract Bitbucket project key from URL or return as-is."""
    if not value or "/" not in value:
        return value
    parts = [p for p in urlparse(value).path.split("/") if p]
    try:
        return parts[parts.index("projects") + 1]
    except (ValueError, IndexError):
        return value


def parse_bitbucket_url(value: str) -> tuple[str, str]:
    """Extract (project_key, repo_slug) from a Bitbucket URL.

    Supports both web and SCM URL shapes:
        .../projects/CGF/repos/my-repo            -> ("CGF", "my-repo")
        .../projects/CGF                          -> ("CGF", "")
        .../scm/CGF/my-repo.git                   -> ("CGF", "my-repo")

    Returns:
        tuple: (project_key, repo_slug) - either may be empty if not found.
    """
    if not value or "/" not in value:
        return ("", "")

    parts = [p for p in urlparse(value).path.split("/") if p]
    project_key = ""
    repo_slug = ""

    # Web URL: /projects/KEY/repos/REPO
    try:
        idx = parts.index("projects")
        if idx + 1 < len(parts):
            project_key = parts[idx + 1]
        if "repos" in parts:
            ridx = parts.index("repos")
            if ridx + 1 < len(parts):
                repo_slug = parts[ridx + 1]
        return (project_key, repo_slug.removesuffix(".git"))
    except ValueError:
        pass

    # SCM URL: /scm/KEY/REPO.git
    try:
        idx = parts.index("scm")
        if idx + 1 < len(parts):
            project_key = parts[idx + 1]
        if idx + 2 < len(parts):
            repo_slug = parts[idx + 2]
    except ValueError:
        pass

    return (project_key, repo_slug.removesuffix(".git"))


def parse_space_key(value: str) -> str:
    """Extract Confluence space key from URL or return as-is."""
    if not value or "/" not in value:
        return value
    parts = [p for p in urlparse(value).path.split("/") if p]
    for segment in ("display", "spaces"):
        try:
            return parts[parts.index(segment) + 1]
        except (ValueError, IndexError):
            continue
    return value


def parse_confluence_url(value: str) -> tuple[str, str]:
    """Extract (space_key, page_id) from Confluence URL.
    
    Returns:
        tuple: (space_key, page_id) - one will be empty string if not found
    """
    if not value or "/" not in value:
        return ("", "")
    
    parts = [p for p in urlparse(value).path.split("/") if p]
    space_key = ""
    page_id = ""
    
    # Check for space URL: /spaces/SPACE_KEY or /display/SPACE_KEY
    for segment in ("display", "spaces"):
        try:
            idx = parts.index(segment)
            if idx + 1 < len(parts):
                space_key = parts[idx + 1]
                # Check if this is followed by /pages/PAGE_ID
                if idx + 2 < len(parts) and parts[idx + 2] == "pages" and idx + 3 < len(parts):
                    page_id = parts[idx + 3]
                break
        except (ValueError, IndexError):
            continue
    
    return (space_key, page_id)


# ── Bitbucket helpers ────────────────────────────────────────────────

def bb_list_project_repos(project: str, limit: int = 500) -> list[dict[str, Any]]:
    """Fetch repos from a Bitbucket project via MCP."""
    result = call_mcp_tool(_get_bb_url(), "list_project_repos", {
        "project": project,
        "limit": limit,
    })
    repos = result.get("repos", []) if isinstance(result, dict) else []
    return repos


def bb_get_project_info(project: str) -> dict[str, Any]:
    """Get Bitbucket project info via MCP."""
    return call_mcp_tool(_get_bb_url(), "get_project_info", {"project": project})


# ── Confluence helpers ───────────────────────────────────────────────

def confluence_get_space_pages(space_key: str, limit: int = 200) -> list[dict[str, Any]]:
    """Get pages in a Confluence space via MCP."""
    result = call_mcp_tool(_get_confluence_url(), "get_space_pages", {
        "space_key": space_key,
        "limit": limit,
    })
    return result.get("pages", []) if isinstance(result, dict) else []


def confluence_get_page(page_id: str, include_body: bool = False) -> dict[str, Any]:
    """Get a Confluence page by ID via MCP."""
    return call_mcp_tool(_get_confluence_url(), "get_confluence_page", {
        "page_id": page_id,
        "include_body": include_body,
    })


def confluence_create_space(key: str, name: str, description: str = "") -> dict[str, Any]:
    """Create a Confluence space via MCP."""
    return call_mcp_tool(_get_confluence_url(), "create_confluence_space", {
        "key": key,
        "name": name,
        "description": description,
    })


def confluence_create_page(
    space_key: str, title: str, body: str, parent_page_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a Confluence page via MCP."""
    args: dict = {"space_key": space_key, "title": title, "body": body}
    if parent_page_id:
        args["parent_page_id"] = parent_page_id
    return call_mcp_tool(_get_confluence_url(), "create_confluence_page", args)


def confluence_update_page(
    page_id: str, title: str, body: str, version_number: int,
) -> dict[str, Any]:
    """Update a Confluence page via MCP."""
    return call_mcp_tool(_get_confluence_url(), "update_confluence_page", {
        "page_id": page_id,
        "title": title,
        "body": body,
        "version_number": version_number,
    })


def confluence_get_space(space_key: str) -> dict[str, Any]:
    """Get Confluence space details via MCP."""
    return call_mcp_tool(_get_confluence_url(), "get_confluence_space", {"space_key": space_key})


def confluence_list_attachments(page_id: str) -> list[dict[str, Any]]:
    """List attachments for a Confluence page via MCP."""
    result = call_mcp_tool(_get_confluence_url(), "list_attachments", {
        "page_id": page_id,
    })
    return result.get("results", []) if isinstance(result, dict) else []


def confluence_get_attachment(attachment_id: str) -> dict[str, Any]:
    """Get attachment metadata and download URL via MCP."""
    return call_mcp_tool(_get_confluence_url(), "get_attachment", {
        "attachment_id": attachment_id,
    })

def confluence_download_attachment(attachment_id: str) -> str:
    """Download attachment content as base64 via MCP."""
    return call_mcp_tool(_get_confluence_url(), "download_attachment", {
        "attachment_id": attachment_id,
    })

def confluence_get_page_children(page_id: str) -> list[dict[str, Any]]:
    """Get direct child pages of a page via MCP."""
    result = call_mcp_tool(_get_confluence_url(), "get_page_children", {
        "page_id": page_id,
    })
    return json.loads(result) if isinstance(result, str) else result


def confluence_get_all_descendants(page_id: str, max_depth: int = 10) -> list[dict[str, Any]]:
    """Recursively fetch all descendant pages of a Confluence page.
    
    Args:
        page_id: The root page ID
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        List of all descendant pages (not including the root page)
    """
    all_pages = []
    
    def _fetch_recursive(current_page_id: str, current_depth: int):
        if current_depth >= max_depth:
            return
        
        try:
            children = confluence_get_page_children(current_page_id)
            for child in children:
                all_pages.append(child)
                # Recursively fetch children of this page
                _fetch_recursive(str(child.get("id")), current_depth + 1)
        except Exception:
            # If fetching children fails, skip this branch
            pass
    
    _fetch_recursive(page_id, 0)
    return all_pages
