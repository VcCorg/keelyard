"""Jira Server MCP Server.

Exposes Jira Server/Data Center issue tracking tools via Model Context Protocol.
Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
Designed for use with Windsurf/Cascade, OpenCode, and other MCP-compatible AI assistants.
"""

import json
import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import JiraConfig
from .jira_client import JiraClient

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize MCP server
_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs = {
    "name": "Jira Server",
    "instructions": "Access Jira Server/Data Center issues, comments, transitions, and sprints",
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "8128"))

mcp = FastMCP(**_mcp_kwargs)


def _get_client() -> JiraClient:
    """Create a configured Jira client."""
    config = JiraConfig()
    if not config.is_configured:
        raise ValueError(
            "Jira Server is not configured. "
            "Set JIRA_SERVER_URL and JIRA_PERSONAL_ACCESS_TOKEN environment variables."
        )
    return JiraClient(config)


def _resolve_issue_key(
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Resolve issue key from either explicit key or a URL."""
    if issue_url:
        return JiraClient.parse_issue_url(issue_url)
    if issue_key:
        return issue_key
    raise ValueError("Provide either issue_key (e.g. 'CWHE-12345') or issue_url.")


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_issue(
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Get detailed information about a Jira issue.

    Provide either:
      - issue_key: Jira issue key (e.g. CWHE-12345)
      - OR issue_url: Full Jira URL (e.g. https://jira.example.com/browse/CWHE-12345)

    Returns issue summary, description, status, priority, assignee, reporter,
    labels, components, fix versions, subtasks, and linked issues.
    """
    key = _resolve_issue_key(issue_key, issue_url)
    with _get_client() as client:
        issue = client.get_issue(key)
        return json.dumps(issue, indent=2, default=str)


@mcp.tool()
def search_issues(
    jql: str,
    max_results: int = 20,
) -> str:
    """Search Jira issues using JQL (Jira Query Language).

    Args:
        jql: JQL query string. Examples:
          - 'project = CWHE AND status = "In Progress"'
          - 'assignee = currentUser() AND resolution = Unresolved'
          - 'sprint in openSprints() AND project = CWHE'
          - 'text ~ "patient query" ORDER BY updated DESC'
          - 'labels = critical AND created >= -7d'
        max_results: Maximum number of results (default 20, max 50)

    Returns matching issues with key, summary, status, priority, assignee.
    """
    with _get_client() as client:
        results = client.search_issues(jql, max_results=min(max_results, 50))
        return json.dumps(results, indent=2, default=str)


@mcp.tool()
def get_my_issues(
    status: str | None = None,
    project: str | None = None,
    max_results: int = 20,
) -> str:
    """Get issues assigned to the current user.

    Args:
        status: Optional status filter (e.g. 'In Progress', 'Open', 'To Do')
        project: Optional project key filter (e.g. 'CWHE')
        max_results: Maximum number of results (default 20)

    Returns issues assigned to you, sorted by updated date descending.
    """
    jql_parts = ["assignee = currentUser()", "resolution = Unresolved"]
    if status:
        jql_parts.append(f'status = "{status}"')
    if project:
        jql_parts.append(f"project = {project}")
    jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"

    with _get_client() as client:
        results = client.search_issues(jql, max_results=min(max_results, 50))
        return json.dumps(results, indent=2, default=str)


@mcp.tool()
def get_comments(
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Get all comments on a Jira issue.

    Provide either:
      - issue_key: Jira issue key (e.g. CWHE-12345)
      - OR issue_url: Full Jira URL

    Returns comment text, author, and timestamps.
    """
    key = _resolve_issue_key(issue_key, issue_url)
    with _get_client() as client:
        comments = client.get_comments(key)
        return json.dumps({
            "issue": key,
            "total": len(comments),
            "comments": comments,
        }, indent=2, default=str)


@mcp.tool()
def add_comment(
    body: str,
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Add a comment to a Jira issue.

    Args:
        body: Comment text (supports Jira wiki markup)
        issue_key: Jira issue key (e.g. CWHE-12345)
        issue_url: Full Jira URL (alternative to issue_key)

    Posts the comment as the authenticated user.
    """
    key = _resolve_issue_key(issue_key, issue_url)
    with _get_client() as client:
        result = client.add_comment(key, body)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_transitions(
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Get available workflow transitions for a Jira issue.

    Provide either:
      - issue_key: Jira issue key (e.g. CWHE-12345)
      - OR issue_url: Full Jira URL

    Returns the list of transitions (status changes) available for the issue
    in its current state. Use the transition ID with transition_issue to change status.
    """
    key = _resolve_issue_key(issue_key, issue_url)
    with _get_client() as client:
        transitions = client.get_transitions(key)
        return json.dumps({
            "issue": key,
            "transitions": transitions,
        }, indent=2, default=str)


@mcp.tool()
def transition_issue(
    transition_id: str,
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Move a Jira issue to a new status using a workflow transition.

    Args:
        transition_id: The transition ID (get from get_transitions tool)
        issue_key: Jira issue key (e.g. CWHE-12345)
        issue_url: Full Jira URL (alternative to issue_key)

    Use get_transitions first to see available transitions and their IDs.
    """
    key = _resolve_issue_key(issue_key, issue_url)
    with _get_client() as client:
        result = client.transition_issue(key, transition_id)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def assign_issue(
    assignee: str,
    issue_key: str | None = None,
    issue_url: str | None = None,
) -> str:
    """Assign a Jira issue to a user.

    Args:
        assignee: Username/key of the assignee, or '-1' to unassign
        issue_key: Jira issue key (e.g. CWHE-12345)
        issue_url: Full Jira URL (alternative to issue_key)
    """
    key = _resolve_issue_key(issue_key, issue_url)
    with _get_client() as client:
        result = client.assign_issue(key, assignee)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def list_projects() -> str:
    """List all Jira projects visible to the current user.

    Returns project key, name, type, and lead for each project.
    """
    with _get_client() as client:
        projects = client.list_projects()
        return json.dumps({
            "total": len(projects),
            "projects": projects,
        }, indent=2, default=str)


@mcp.tool()
def get_sprint_issues(
    board_id: int,
    sprint_id: int | None = None,
    max_results: int = 50,
) -> str:
    """Get issues in the active sprint for a Jira board.

    Args:
        board_id: The Jira Agile board ID
        sprint_id: Optional specific sprint ID (defaults to active sprint)
        max_results: Maximum number of results (default 50)

    Returns sprint details and all issues with status, assignee, and story points.
    """
    with _get_client() as client:
        results = client.get_sprint_issues(board_id, sprint_id, max_results)
        return json.dumps(results, indent=2, default=str)


@mcp.tool()
def get_jira_config() -> str:
    """Show current Jira MCP server configuration (URL and auth status).

    Useful for debugging connection issues. Does not expose the token.
    """
    config = JiraConfig()
    return json.dumps({
        "server_url": config.jira_server_url,
        "is_configured": config.is_configured,
        "has_token": bool(config.jira_personal_access_token),
        "default_project": config.jira_default_project or None,
        "verify_ssl": config.jira_verify_ssl,
    }, indent=2)


# ── Entry Point ──────────────────────────────────────────────────────────────


def main():
    """Run the MCP server.

    Transport is determined by MCP_TRANSPORT env var:
      - 'stdio' (default): for local CLI usage (Windsurf, OpenCode)
      - 'sse': for Docker/network usage (exposes HTTP+SSE endpoint)
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting Jira Server MCP server (transport={transport})...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
