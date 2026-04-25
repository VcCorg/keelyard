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
    """Open an SSE session, initialize, call the tool, parse response."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(sse_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

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

def call_mcp_tool(
    sse_url: str, tool_name: str, arguments: Optional[dict] = None, timeout: float = 30.0,
) -> Any:
    """Call an MCP tool synchronously. Handles connection errors gracefully."""
    try:
        return asyncio.run(
            _call_tool_async(sse_url, tool_name, arguments or {}, timeout)
        )
    except MCPToolError:
        raise
    except OSError as e:
        raise MCPToolError(
            f"Cannot connect to MCP server at {sse_url}. Is the server running? ({e})",
            is_connection_error=True,
        )
    except Exception as e:
        # ExceptionGroup from anyio wraps connection errors
        msg = str(e)
        if "connect" in msg.lower() or "refused" in msg.lower() or "timed out" in msg.lower():
            raise MCPToolError(
                f"Cannot connect to MCP server at {sse_url}. Is the server running?",
                is_connection_error=True,
            )
        raise MCPToolError(f"MCP call failed: {msg}")


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

            return asyncio.run(_check())
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
