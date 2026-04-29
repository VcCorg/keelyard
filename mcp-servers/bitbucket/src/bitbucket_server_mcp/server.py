"""Bitbucket Server MCP Server.

Exposes Bitbucket Server PR data via Model Context Protocol.
Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
Designed for use with Windsurf/Cascade, OpenCode, and other MCP-compatible AI assistants.
"""

import json
import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import BitbucketConfig
from .bitbucket_client import BitbucketClient

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize MCP server
_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs = {
    "name": "Bitbucket Server",
    "instructions": "Access Bitbucket Server pull requests for code review",
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "8126"))

mcp = FastMCP(**_mcp_kwargs)


def _get_client() -> BitbucketClient:
    """Create a configured Bitbucket client."""
    config = BitbucketConfig()
    if not config.is_configured:
        raise ValueError(
            "Bitbucket Server is not configured. "
            "Set BITBUCKET_SERVER_URL and BITBUCKET_PERSONAL_ACCESS_TOKEN environment variables."
        )
    return BitbucketClient(config)


def _resolve_pr(
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
    pr_url: str | None = None,
) -> tuple[str, str, int]:
    """Resolve PR coordinates from either explicit params or a URL."""
    if pr_url:
        return BitbucketClient.parse_pr_url(pr_url)
    if project and repo and pr_id:
        return project, repo, pr_id
    # Try defaults
    config = BitbucketConfig()
    p = project or config.default_project
    r = repo or config.default_repo
    if p and r and pr_id:
        return p, r, pr_id
    raise ValueError(
        "Provide either pr_url OR (project + repo + pr_id). "
        "You can also set BITBUCKET_DEFAULT_PROJECT and BITBUCKET_DEFAULT_REPO."
    )


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_pr_overview(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Get pull request overview including title, description, author, reviewers, and status.

    Provide either:
      - pr_url: Full Bitbucket PR URL (e.g. https://bitbucket.example.com/projects/CGP/repos/my-repo/pull-requests/123)
      - OR project + repo + pr_id separately

    Returns PR metadata, branch info, reviewer statuses, and merge readiness.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        overview = client.get_pr(proj, rp, pid)
        merge_status = client.get_pr_merge_status(proj, rp, pid)
        overview["merge_status"] = merge_status
        return json.dumps(overview, indent=2, default=str)


@mcp.tool()
def get_pr_diff(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
    context_lines: int = 10,
    file_path: str | None = None,
) -> str:
    """Get the unified diff for a pull request.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Args:
        context_lines: Number of context lines around changes (default 10)
        file_path: Optional - get diff for a specific file only

    Returns the raw unified diff text that can be reviewed for code changes.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        diff = client.get_pr_diff(proj, rp, pid, context_lines=context_lines, file_path=file_path)
        # If diff is very large, truncate with a note
        max_chars = 100_000
        if len(diff) > max_chars:
            diff = diff[:max_chars] + f"\n\n... [TRUNCATED - diff is {len(diff)} chars, showing first {max_chars}] ..."
        return diff


@mcp.tool()
def get_pr_files(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Get the list of files changed in a pull request.

    Returns file paths, change types (ADD, MODIFY, DELETE, RENAME), and node types.
    Useful for understanding the scope of changes before reviewing the full diff.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        changes = client.get_pr_changes(proj, rp, pid)

        summary = {
            "total_files": len(changes),
            "by_type": {},
            "files": changes,
        }
        for c in changes:
            ctype = c["type"]
            summary["by_type"][ctype] = summary["by_type"].get(ctype, 0) + 1

        return json.dumps(summary, indent=2)


@mcp.tool()
def get_pr_commits(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Get the commits in a pull request.

    Returns commit messages, authors, and timestamps.
    Useful for understanding the history and intent of changes.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        commits = client.get_pr_commits(proj, rp, pid)
        return json.dumps({"total_commits": len(commits), "commits": commits}, indent=2, default=str)


@mcp.tool()
def get_pr_comments(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Get existing review comments on a pull request.

    Returns all comments including inline code comments with file/line anchors.
    Useful for understanding existing review feedback.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        comments = client.get_pr_comments(proj, rp, pid)
        return json.dumps({"total_comments": len(comments), "comments": comments}, indent=2, default=str)


@mcp.tool()
def get_pr_activities(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Get all activities on a pull request (comments, approvals, rescopes, merges).

    Returns the full activity timeline for the PR.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        activities = client.get_pr_activities(proj, rp, pid)
        return json.dumps({"total_activities": len(activities), "activities": activities}, indent=2, default=str)


@mcp.tool()
def get_file_content(
    project: str,
    repo: str,
    file_path: str,
    ref: str | None = None,
) -> str:
    """Get the content of a specific file from a Bitbucket repository.

    Args:
        project: Bitbucket project key (e.g. CGP)
        repo: Repository slug (e.g. cwow-patient-query-spanner)
        file_path: Path to file in the repo
        ref: Optional branch, tag, or commit hash to read from

    Useful for reading full file content when the diff alone isn't sufficient context.
    """
    with _get_client() as client:
        content = client.get_file_content(project, repo, file_path, at_ref=ref)
        return content


@mcp.tool()
def review_pr(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
    context_lines: int = 10,
) -> str:
    """Get a comprehensive PR review package: overview + changed files + diff + commits + comments.

    This is a convenience tool that fetches all PR data in one call, suitable for
    a complete code review. For very large PRs, prefer using individual tools.

    Returns a structured JSON with all PR information needed for review.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        overview = client.get_pr(proj, rp, pid)
        merge_status = client.get_pr_merge_status(proj, rp, pid)
        changes = client.get_pr_changes(proj, rp, pid)
        commits = client.get_pr_commits(proj, rp, pid)
        comments = client.get_pr_comments(proj, rp, pid)

        # Get diff - truncate if huge
        diff = client.get_pr_diff(proj, rp, pid, context_lines=context_lines)
        max_diff = 80_000
        diff_truncated = False
        if len(diff) > max_diff:
            diff = diff[:max_diff]
            diff_truncated = True

        review_package = {
            "overview": overview,
            "merge_status": merge_status,
            "files": {
                "total": len(changes),
                "by_type": {},
                "list": changes,
            },
            "commits": {
                "total": len(commits),
                "list": commits,
            },
            "comments": {
                "total": len(comments),
                "list": comments,
            },
            "diff": diff,
            "diff_truncated": diff_truncated,
        }

        for c in changes:
            ctype = c["type"]
            review_package["files"]["by_type"][ctype] = (
                review_package["files"]["by_type"].get(ctype, 0) + 1
            )

        return json.dumps(review_package, indent=2, default=str)


@mcp.tool()
def list_my_prs(
    role: str = "reviewer",
    state: str = "OPEN",
    limit: int = 25,
) -> str:
    """List pull requests for the authenticated user.

    Args:
        role: Filter by role - 'reviewer' (PRs awaiting your review), 'author' (your PRs), or 'participant'
        state: PR state - 'OPEN', 'MERGED', 'DECLINED', or 'ALL'
        limit: Maximum number of PRs to return (default 25)

    Returns a list of PRs with title, author, repo, branch, and reviewer statuses.
    """
    with _get_client() as client:
        prs = client.get_dashboard_prs(role=role, state=state, limit=limit)
        summary = {
            "total": len(prs),
            "role": role,
            "state": state,
            "pull_requests": prs,
        }
        return json.dumps(summary, indent=2, default=str)


@mcp.tool()
def add_pr_comment(
    text: str,
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
    severity: str = "NORMAL",
) -> str:
    """Add a general comment to a pull request.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Args:
        text: Comment text (supports Markdown)
        severity: 'NORMAL' for regular comment, 'BLOCKER' to create a task

    Posts the comment as the authenticated user. Returns the created comment details.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.add_pr_comment(proj, rp, pid, text=text, severity=severity)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def add_pr_inline_comment(
    text: str,
    file_path: str,
    line: int,
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
    line_type: str = "ADDED",
    file_type: str = "TO",
    severity: str = "NORMAL",
) -> str:
    """Add an inline comment on a specific file and line in a pull request.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Args:
        text: Comment text (supports Markdown)
        file_path: Path to the file in the diff (e.g. 'src/main/java/com/example/MyClass.java')
        line: Line number to comment on (in the diff)
        line_type: 'ADDED' (new lines), 'REMOVED' (deleted lines), or 'CONTEXT' (unchanged lines)
        file_type: 'TO' (comment on new version) or 'FROM' (comment on old version)
        severity: 'NORMAL' for regular comment, 'BLOCKER' to create a task

    Posts an inline code comment as the authenticated user. Returns the created comment details.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.add_pr_inline_comment(
            proj, rp, pid,
            text=text,
            file_path=file_path,
            line=line,
            line_type=line_type,
            file_type=file_type,
            severity=severity,
        )
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def approve_pr(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Approve a pull request as the authenticated user.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Sets the reviewer status to APPROVED for the current user.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.approve_pr(proj, rp, pid)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def unapprove_pr(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Remove your approval from a pull request.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Reverts the reviewer status from APPROVED back to UNAPPROVED.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.unapprove_pr(proj, rp, pid)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def needs_work_pr(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Mark a pull request as 'Needs Work' (request changes).

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Sets the reviewer status to NEEDS_WORK, indicating changes are required.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.needs_work_pr(proj, rp, pid)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def decline_pr(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Decline (reject) a pull request.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    This closes the PR without merging. Only the PR author or project admin can decline.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.decline_pr(proj, rp, pid)
        return json.dumps(result, indent=2, default=str)


@mcp.tool()
def merge_pr(
    pr_url: str | None = None,
    project: str | None = None,
    repo: str | None = None,
    pr_id: int | None = None,
) -> str:
    """Merge a pull request.

    Provide either:
      - pr_url: Full Bitbucket PR URL
      - OR project + repo + pr_id separately

    Merges the PR if all merge checks pass (approvals, build status, etc.).
    Will fail if there are unresolved merge vetoes.
    """
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
    with _get_client() as client:
        result = client.merge_pr(proj, rp, pid)
        return json.dumps(result, indent=2, default=str)


# ── Project / Repo Listing ────────────────────────────────────────────────────


@mcp.tool()
def list_project_repos(
    project: str,
    limit: int = 100,
) -> str:
    """List all repositories in a Bitbucket project.

    Args:
        project: Bitbucket project key (e.g. 'CGF', 'CGP', 'IMTO')
        limit: Maximum number of repos to return (default: 100)

    Returns repo slugs, names, descriptions, clone URLs, and links.
    Useful for discovering available repositories before onboarding.
    """
    with _get_client() as client:
        repos = client.list_project_repos(project, limit=limit)
        return json.dumps({
            "project": project,
            "total": len(repos),
            "repos": repos,
        }, indent=2, default=str)


@mcp.tool()
def get_project_info(project: str) -> str:
    """Get details of a Bitbucket project.

    Args:
        project: Bitbucket project key (e.g. 'CGF', 'CGP')

    Returns project name, description, type, and links.
    """
    with _get_client() as client:
        info = client.get_project(project)
        return json.dumps(info, indent=2, default=str)


# ── Resources ────────────────────────────────────────────────────────────────


@mcp.resource("bitbucket://config")
def get_config_resource() -> str:
    """Current Bitbucket Server configuration (without secrets)."""
    config = BitbucketConfig()
    return json.dumps({
        "server_url": config.server_url,
        "configured": config.is_configured,
        "default_project": config.default_project or None,
        "default_repo": config.default_repo or None,
        "verify_ssl": config.verify_ssl,
    }, indent=2)


# ── Entry Point ──────────────────────────────────────────────────────────────


def main():
    """Run the MCP server.

    Transport is determined by MCP_TRANSPORT env var:
      - 'stdio' (default): for local CLI usage (Windsurf, OpenCode)
      - 'sse': for Docker/network usage (exposes HTTP+SSE endpoint)
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting Bitbucket Server MCP server (transport={transport})...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
