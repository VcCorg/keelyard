"""Confluence MCP Server.

Exposes Confluence Server wiki and documentation tools via Model Context Protocol.
Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
Designed for use with Windsurf/Cascade, OpenCode, and other MCP-compatible AI assistants.
"""

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .config import ConfluenceConfig
from .confluence_client import ConfluenceClient

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize MCP server
_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs = {
    "name": "Confluence Server",
    "instructions": "Access Confluence Server wiki pages, spaces, and documentation",
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "8129"))

mcp = FastMCP(**_mcp_kwargs)


def _get_client() -> ConfluenceClient:
    """Create a configured Confluence client."""
    config = ConfluenceConfig()
    if not config.is_configured:
        raise ValueError(
            "Confluence Server is not configured. "
            "Set CONFLUENCE_SERVER_URL and CONFLUENCE_PERSONAL_ACCESS_TOKEN environment variables."
        )
    return ConfluenceClient(config)


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def search_confluence(
    query: str,
    space_key: Optional[str] = None,
    content_type: str = "page",
    limit: int = 10,
) -> str:
    """Search Confluence content using CQL (Confluence Query Language).

    Args:
        query: Text to search for. Will be wrapped in a CQL text search.
        space_key: Optional space key to limit search scope (e.g. 'DEV', 'TEAM')
        content_type: Content type filter - 'page', 'blogpost', or 'comment' (default: 'page')
        limit: Maximum number of results (default: 10)

    Returns matching pages with titles, spaces, versions, and links.
    """
    cql_parts = [f'type={content_type}', f'text~"{query}"']
    if space_key:
        cql_parts.insert(0, f"space={space_key}")
    cql = " AND ".join(cql_parts)

    with _get_client() as client:
        results = client.search_content(cql, limit=limit, expand=["space", "version"])
        return json.dumps(results, indent=2, default=str)


@mcp.tool()
def search_confluence_cql(
    cql: str,
    limit: int = 10,
) -> str:
    """Search Confluence using a raw CQL query for advanced filtering.

    Args:
        cql: CQL query string (e.g. 'space=DEV AND label=api AND type=page')
        limit: Maximum number of results (default: 10)

    CQL reference: https://developer.atlassian.com/server/confluence/advanced-searching-using-cql/
    Common operators: =, !=, ~(contains), IN, AND, OR, ORDER BY
    """
    with _get_client() as client:
        results = client.search_content(cql, limit=limit, expand=["space", "version"])
        return json.dumps(results, indent=2, default=str)


@mcp.tool()
def get_confluence_page(
    page_id: Optional[str] = None,
    space_key: Optional[str] = None,
    title: Optional[str] = None,
    include_body: bool = True,
    plain_text: bool = False,
) -> str:
    """Get a Confluence page by ID or by space key + title.

    Provide either:
      - page_id: Numeric page ID
      - OR space_key + title to look up by name

    Args:
        page_id: Confluence page ID
        space_key: Space key (required if using title lookup)
        title: Page title (required if using space_key lookup)
        include_body: Include page content (default: True)
        plain_text: Strip HTML tags from body for cleaner reading (default: False)

    Returns page metadata, content, ancestors, and version info.
    """
    with _get_client() as client:
        if page_id:
            page = client.get_page(page_id, expand_body=include_body)
        elif space_key and title:
            page = client.get_page_by_title(space_key, title, expand_body=include_body)
            if not page:
                return json.dumps({"error": f"Page '{title}' not found in space '{space_key}'"})
        else:
            return json.dumps({"error": "Provide either page_id OR (space_key + title)"})

        if plain_text and "body_html" in page:
            page["body_text"] = ConfluenceClient.strip_html(page["body_html"])
            del page["body_html"]

        return json.dumps(page, indent=2, default=str)


@mcp.tool()
def list_confluence_spaces(
    limit: int = 25,
    space_type: Optional[str] = None,
) -> str:
    """List Confluence spaces.

    Args:
        limit: Maximum number of spaces (default: 25)
        space_type: Filter by type - 'global' or 'personal' (optional)

    Returns space keys, names, types, and descriptions.
    """
    with _get_client() as client:
        spaces = client.list_spaces(limit=limit, space_type=space_type)
        return json.dumps({"total": len(spaces), "spaces": spaces}, indent=2)


@mcp.tool()
def get_confluence_space(space_key: str) -> str:
    """Get details of a specific Confluence space.

    Args:
        space_key: The space key (e.g. 'DEV', 'TEAM', 'HR')

    Returns space name, description, homepage, and type.
    """
    with _get_client() as client:
        space = client.get_space(space_key)
        return json.dumps(space, indent=2, default=str)


@mcp.tool()
def get_child_pages(page_id: str, limit: int = 25) -> str:
    """Get child pages of a Confluence page.

    Args:
        page_id: Parent page ID
        limit: Maximum number of child pages (default: 25)

    Returns list of direct child pages with titles and metadata.
    """
    with _get_client() as client:
        children = client.get_child_pages(page_id, limit=limit)
        return json.dumps({"total": len(children), "children": children}, indent=2, default=str)


@mcp.tool()
def get_space_pages(
    space_key: str,
    limit: int = 25,
) -> str:
    """Get pages in a Confluence space.

    Args:
        space_key: The space key (e.g. 'DEV')
        limit: Maximum number of pages (default: 25)

    Returns pages with titles, versions, and update info.
    """
    with _get_client() as client:
        result = client.get_space_pages(space_key, limit=limit)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_page_comments(page_id: str, limit: int = 25) -> str:
    """Get comments on a Confluence page.

    Args:
        page_id: The page ID
        limit: Maximum number of comments (default: 25)

    Returns comments with authors, timestamps, and content.
    """
    with _get_client() as client:
        comments = client.get_page_comments(page_id, limit=limit)
        return json.dumps({"total": len(comments), "comments": comments}, indent=2, default=str)


@mcp.tool()
def add_confluence_comment(
    page_id: str,
    comment: str,
) -> str:
    """Add a comment to a Confluence page.

    Args:
        page_id: The page ID to comment on
        comment: Comment text (plain text will be wrapped in paragraph tags)

    Posts as the authenticated user. Returns the created comment details.
    """
    # Wrap plain text in storage format
    if not comment.strip().startswith("<"):
        comment = f"<p>{comment}</p>"

    with _get_client() as client:
        result = client.add_page_comment(page_id, comment)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_page_labels(page_id: str) -> str:
    """Get labels on a Confluence page.

    Args:
        page_id: The page ID

    Returns list of labels with names and prefixes.
    """
    with _get_client() as client:
        labels = client.get_page_labels(page_id)
        return json.dumps({"total": len(labels), "labels": labels}, indent=2)


@mcp.tool()
def list_attachments(page_id: str, limit: int = 100) -> str:
    """List attachments for a Confluence page.

    Args:
        page_id: Confluence page ID
        limit: Maximum number of attachments (default: 100)

    Returns list of attachments with filenames, media types, sizes, and download links.
    """
    with _get_client() as client:
        attachments = client.list_attachments(page_id, limit=limit)
        return json.dumps({"total": len(attachments), "results": attachments}, indent=2)


@mcp.tool()
def get_attachment(attachment_id: str) -> str:
    """Get attachment metadata and download URL.

    Args:
        attachment_id: Confluence attachment ID

    Returns attachment metadata with download link.
    """
    with _get_client() as client:
        attachment = client.get_attachment(attachment_id)
        return json.dumps(attachment, indent=2)


@mcp.tool()
def download_attachment(attachment_id: str) -> str:
    """Download attachment content as base64-encoded string.

    Args:
        attachment_id: Confluence attachment ID

    Returns base64-encoded attachment content.
    """
    import base64
    with _get_client() as client:
        content = client.download_attachment_content(attachment_id)
        return base64.b64encode(content).decode('utf-8')


@mcp.tool()
def get_page_children(page_id: str) -> str:
    """Get direct child pages of a page.

    Args:
        page_id: Confluence page ID

    Returns list of child page metadata as JSON.
    """
    with _get_client() as client:
        children = client.get_page_children(page_id)
        return json.dumps(children, indent=2)


# ── Create / Update ──────────────────────────────────────────────────────────


@mcp.tool()
def create_confluence_space(
    key: str,
    name: str,
    description: str = "",
) -> str:
    """Create a new Confluence space.

    Args:
        key: Space key — uppercase letters/numbers, e.g. 'KEELCWOW', 'KEELFAC'
        name: Display name for the space (e.g. 'KEEL CWOW Facility')
        description: Optional space description

    Creates a global space. Returns the new space key and link.
    Requires Confluence admin or space-create permissions.
    """
    with _get_client() as client:
        result = client.create_space(key, name, description)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def create_confluence_page(
    space_key: str,
    title: str,
    body: str,
    parent_page_id: Optional[str] = None,
) -> str:
    """Create a new page in a Confluence space.

    Args:
        space_key: Space key to create the page in (e.g. 'KEELCWOW')
        title: Page title
        body: Page content in Confluence storage format (XHTML).
              Use <p>text</p> for paragraphs, <h1>/<h2> for headings,
              <table>/<tr>/<td> for tables, <ac:structured-macro> for macros.
        parent_page_id: Optional parent page ID to create as a child page

    Returns the created page ID, title, space, and version.
    """
    with _get_client() as client:
        result = client.create_page(space_key, title, body, parent_page_id)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def update_confluence_page(
    page_id: str,
    title: str,
    body: str,
    version_number: int,
) -> str:
    """Update an existing Confluence page.

    Args:
        page_id: ID of the page to update
        title: New page title (can be same as current)
        body: New page content in Confluence storage format (XHTML)
        version_number: Current version number of the page (will be auto-incremented).
                        Get this from get_confluence_page first.

    Returns the updated page metadata including new version number.
    """
    with _get_client() as client:
        result = client.update_page(page_id, title, body, version_number)
        return json.dumps(result, indent=2, default=str)


# ── Resources ────────────────────────────────────────────────────────────────


@mcp.resource("confluence://config")
def get_config_resource() -> str:
    """Current Confluence Server configuration (without secrets)."""
    config = ConfluenceConfig()
    return json.dumps({
        "server_url": config.server_url,
        "configured": config.is_configured,
        "default_space": config.default_space or None,
        "verify_ssl": config.verify_ssl,
    }, indent=2)


# ── Entry Point ──────────────────────────────────────────────────────────────


def main():
    """Run the MCP server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting Confluence MCP server (transport={transport})...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
