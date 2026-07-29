"""MCP Gateway Server.

Unified gateway that aggregates multiple upstream MCP servers behind
a single SSE endpoint. Tools are discovered dynamically at startup
and proxied to upstream servers on each call.

Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
"""

import asyncio
import inspect
import json
import logging
import os
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.client.sse import sse_client
from mcp import ClientSession

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

UPSTREAM_SERVERS: dict[str, str] = {}

def _load_upstream_config():
    """Load upstream server URLs from environment variables."""
    # Format: MCP_UPSTREAM_<NAME>=<url>
    # Or use known defaults
    defaults = {
        "bitbucket": os.environ.get(
            "MCP_UPSTREAM_BITBUCKET", "http://bitbucket-mcp:8126/sse"
        ),
        "jira": os.environ.get(
            "MCP_UPSTREAM_JIRA", "http://jira-mcp:8128/sse"
        ),
        "glean": os.environ.get(
            "MCP_UPSTREAM_GLEAN", "http://glean-mcp:8127/sse"
        ),
    }

    for name, url in defaults.items():
        if url:
            UPSTREAM_SERVERS[name] = url

    # Also scan for any MCP_UPSTREAM_* env vars
    for key, val in os.environ.items():
        if key.startswith("MCP_UPSTREAM_") and val:
            name = key.replace("MCP_UPSTREAM_", "").lower()
            if name not in UPSTREAM_SERVERS:
                UPSTREAM_SERVERS[name] = val

    logger.info(f"Configured upstream servers: {list(UPSTREAM_SERVERS.keys())}")


_load_upstream_config()

# ── Gateway MCP Server ───────────────────────────────────────────────────────

_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs: dict[str, Any] = {
    "name": "MCP Gateway",
    "instructions": (
        "Unified MCP Gateway that aggregates tools from multiple upstream servers. "
        "Tools are namespaced as <server>_<tool> (e.g., bitbucket_get_pr_overview, "
        "jira_get_issue, glean_search_glean). Call any tool directly."
    ),
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "9090"))

mcp = FastMCP(**_mcp_kwargs)


# ── Upstream proxy ───────────────────────────────────────────────────────────

async def _call_upstream(server_url: str, tool_name: str, arguments: dict) -> str:
    """Connect to an upstream MCP server and call a tool.

    Creates a fresh connection per call for simplicity and resilience.
    """
    async with sse_client(server_url) as streams:
        read_stream, write_stream = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.content:
                texts = []
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        texts.append(content_item.text)
                return "\n".join(texts) if texts else str(result.content)
            return ""


async def _discover_tools(server_name: str, server_url: str) -> list[dict]:
    """Discover tools from an upstream MCP server."""
    try:
        async with sse_client(server_url) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                tools = []
                for tool in tools_result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema or {},
                    })
                logger.info(
                    f"Discovered {len(tools)} tools from {server_name}: "
                    f"{[t['name'] for t in tools]}"
                )
                return tools
    except Exception as e:
        logger.error(f"Failed to discover tools from {server_name} ({server_url}): {e}")
        return []


# ── Schema-to-signature helpers ──────────────────────────────────────────────

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _json_type_to_python(prop_info: dict) -> type:
    """Convert a JSON-schema property descriptor to a Python type."""
    jtype = prop_info.get("type")
    if jtype and jtype in _JSON_TYPE_MAP:
        return _JSON_TYPE_MAP[jtype]
    # Handle anyOf / nullable unions
    any_of = prop_info.get("anyOf", [])
    if any_of:
        non_null = [t for t in any_of if t.get("type") != "null"]
        if non_null:
            return _json_type_to_python(non_null[0])
    return str  # safe default


def _build_signature(tool_schema: dict) -> tuple[inspect.Signature, dict[str, type]]:
    """Build an inspect.Signature and annotations dict from a JSON schema."""
    properties = tool_schema.get("properties", {})
    required_set = set(tool_schema.get("required", []))

    params: list[inspect.Parameter] = []
    annotations: dict[str, type] = {"return": str}

    for pname, pinfo in properties.items():
        py_type = _json_type_to_python(pinfo)
        if pname in required_set:
            param = inspect.Parameter(
                pname, inspect.Parameter.KEYWORD_ONLY,
                annotation=py_type,
            )
        else:
            opt_type = Optional[py_type]  # type: ignore[valid-type]
            param = inspect.Parameter(
                pname, inspect.Parameter.KEYWORD_ONLY,
                default=None, annotation=opt_type,
            )
        params.append(param)
        annotations[pname] = param.annotation

    return inspect.Signature(params, return_annotation=str), annotations


# ── Proxy tool registration ─────────────────────────────────────────────────


def _register_proxy_tool(
    server_name: str,
    server_url: str,
    tool_name: str,
    tool_description: str,
    tool_schema: dict,
):
    """Register a single namespaced proxy tool in the gateway."""
    namespaced_name = f"{server_name}_{tool_name}"

    # Build parameter documentation from schema
    properties = tool_schema.get("properties", {})
    required = tool_schema.get("required", [])
    param_lines = []
    for pname, pinfo in properties.items():
        ptype = pinfo.get("type", "any")
        pdesc = pinfo.get("description", "")
        req = " (required)" if pname in required else ""
        if pinfo.get("anyOf"):
            types = [t.get("type", "?") for t in pinfo["anyOf"] if t.get("type")]
            ptype = " | ".join(types)
        param_lines.append(f"    {pname} ({ptype}{req}): {pdesc}")

    full_description = f"[{server_name}] {tool_description}"
    if param_lines:
        full_description += "\n\nArgs:\n" + "\n".join(param_lines)

    # Build a proper function signature from the upstream schema so FastMCP
    # generates the correct parameter model (not a single 'kwargs' wrapper).
    sig, annotations = _build_signature(tool_schema)

    def _make_proxy(url: str, tool: str):
        async def proxy(**kwargs) -> str:
            call_args = {k: v for k, v in kwargs.items() if v is not None}
            return await _call_upstream(url, tool, call_args)
        return proxy

    fn = _make_proxy(server_url, tool_name)
    fn.__name__ = namespaced_name
    fn.__doc__ = full_description
    fn.__signature__ = sig
    fn.__annotations__ = annotations

    try:
        mcp.tool(name=namespaced_name, description=full_description)(fn)
        logger.debug(f"Registered proxy tool: {namespaced_name}")
    except Exception as e:
        logger.error(f"Failed to register tool {namespaced_name}: {e}")


def _discover_and_register_sync():
    """Synchronously discover and register all upstream tools at startup."""
    async def _run():
        for server_name, server_url in UPSTREAM_SERVERS.items():
            tools = await _discover_tools(server_name, server_url)
            for tool in tools:
                _register_proxy_tool(
                    server_name=server_name,
                    server_url=server_url,
                    tool_name=tool["name"],
                    tool_description=tool["description"],
                    tool_schema=tool["input_schema"],
                )
        logger.info(f"Gateway registration complete.")

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.warning(
            f"Could not discover upstream tools at startup: {e}. "
            "Tools will not be available until upstream servers are reachable."
        )


# ── Built-in gateway tools ───────────────────────────────────────────────────


@mcp.tool()
def gateway_status() -> str:
    """Show the MCP Gateway status including configured upstream servers.

    Returns the list of upstream MCP servers and their URLs.
    Useful for debugging connectivity issues.
    """
    servers = []
    for name, url in UPSTREAM_SERVERS.items():
        servers.append({"name": name, "url": url})
    return json.dumps({
        "gateway": "MCP Gateway",
        "version": "0.1.0",
        "upstream_servers": servers,
        "transport": _transport,
    }, indent=2)


@mcp.tool()
async def gateway_refresh() -> str:
    """Re-discover tools from all upstream MCP servers.

    Use this if upstream servers were restarted or new tools were added.
    Note: This adds newly discovered tools but does not remove stale ones.
    """
    results = {}
    for server_name, server_url in UPSTREAM_SERVERS.items():
        tools = await _discover_tools(server_name, server_url)
        for tool in tools:
            _register_proxy_tool(
                server_name=server_name,
                server_url=server_url,
                tool_name=tool["name"],
                tool_description=tool["description"],
                tool_schema=tool["input_schema"],
            )
        results[server_name] = [t["name"] for t in tools]

    return json.dumps({
        "status": "refreshed",
        "discovered_tools": results,
    }, indent=2)


# ── Startup ──────────────────────────────────────────────────────────────────

# Discover tools at import time (before server starts)
_discover_and_register_sync()


# ── Entry Point ──────────────────────────────────────────────────────────────

def main():
    """Run the MCP Gateway server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting MCP Gateway (transport={transport})...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
