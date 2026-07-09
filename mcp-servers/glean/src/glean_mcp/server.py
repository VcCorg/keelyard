"""Glean MCP Server.

Exposes Glean enterprise search and AI assistant tools via Model Context Protocol.
Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
Designed for use with Windsurf/Cascade, OpenCode, and other MCP-compatible AI assistants.
"""

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .config import GleanConfig
from .glean_client import GleanClient
from .oauth import bearer_token_for

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize MCP server
_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs = {
    "name": "Glean",
    "instructions": "Search enterprise knowledge and chat with Glean AI assistants",
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "8127"))

mcp = FastMCP(**_mcp_kwargs)


async def _get_client() -> GleanClient:
    """Create a configured Glean client, resolving the bearer token per auth mode.

    Token mode uses the static GLEAN_API_TOKEN; SSO mode mints a short-lived
    service token via OAuth client-credentials (cached in oauth.py).
    """
    config = GleanConfig()
    if not config.is_configured:
        raise ValueError(
            "Glean is not configured. Set GLEAN_DOMAIN plus either GLEAN_API_TOKEN "
            "(token mode) or GLEAN_AUTH_MODE=sso with GLEAN_OAUTH_CLIENT_ID and "
            "GLEAN_OAUTH_CLIENT_SECRET (sso mode)."
        )
    token = await bearer_token_for(config)
    return GleanClient(config, bearer_token=token)


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def search_glean(
    query: str,
    datasources: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search across Glean datasources for documents and content.

    Args:
        query: Search query string
        datasources: Comma-separated list of datasource names to filter (optional)
        limit: Maximum number of results to return (default: 10)

    Returns search results with titles, snippets, URLs, and metadata.
    """
    async with await _get_client() as client:
        ds_list = datasources.split(",") if datasources else None
        results = await client.search(query, ds_list, limit)
        return json.dumps(results, indent=2)


@mcp.tool()
async def get_glean_document(document_id: str) -> str:
    """Retrieve a specific document from Glean by its ID.

    Args:
        document_id: The unique identifier of the document

    Returns full document details including content, metadata, and permissions.
    """
    async with await _get_client() as client:
        document = await client.get_document(document_id)
        return json.dumps(document, indent=2)


@mcp.tool()
async def list_glean_datasources() -> str:
    """List all available datasources in Glean.

    Returns datasource names, types, and configuration status.
    Useful for filtering searches to specific data sources.
    """
    async with await _get_client() as client:
        datasources = await client.list_datasources()
        return json.dumps(datasources, indent=2)


@mcp.tool()
async def list_glean_agents() -> str:
    """List all available Glean agents/assistants.

    Returns agent IDs, names, and descriptions.
    Use agent IDs with chat_with_glean_agent to interact with specific agents.
    """
    async with await _get_client() as client:
        agents = await client.list_agents()
        return json.dumps(agents, indent=2)


@mcp.tool()
async def chat_with_glean_agent(
    message: str,
    agent_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    include_citations: bool = True,
) -> str:
    """Send a message to a Glean agent and get a response.

    Args:
        message: The message to send to the agent
        agent_id: Optional ID of a specific Glean agent. If omitted, uses the default Glean Assistant.
        chat_id: Optional conversation ID to continue an existing conversation.
        include_citations: Whether to include source citations in the response (default: True)

    Returns the agent's response, citations, and conversation ID for follow-up messages.
    """
    async with await _get_client() as client:
        result = await client.chat(
            message=message,
            agent_id=agent_id,
            chat_id=chat_id,
            include_citations=include_citations,
        )
        return json.dumps(result, indent=2)


@mcp.tool()
async def get_glean_conversation(chat_id: str) -> str:
    """Retrieve the message history of a Glean agent conversation.

    Args:
        chat_id: The conversation ID returned from a previous chat_with_glean_agent call

    Returns the full conversation history with all messages and citations.
    """
    async with await _get_client() as client:
        conversation = await client.get_conversation(chat_id)
        return json.dumps(conversation, indent=2)


# ── Resources ────────────────────────────────────────────────────────────────


@mcp.resource("glean://config")
def get_config_resource() -> str:
    """Current Glean configuration (without secrets)."""
    config = GleanConfig()
    return json.dumps({
        "domain": config.domain,
        "auth_mode": "sso" if config.is_sso else "token",
        "configured": config.is_configured,
        "api_base_url": config.api_base_url,
        "oauth_client_id": config.oauth_client_id if config.is_sso else None,
        "oauth_token_url": (config.oauth_token_url or config.discovery_url) if config.is_sso else None,
    }, indent=2)


# ── Entry Point ──────────────────────────────────────────────────────────────


def main():
    """Run the MCP server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting Glean MCP server (transport={transport})...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
