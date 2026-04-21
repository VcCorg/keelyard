"""Bitbucket Server REST API client.

Targets Bitbucket Server/Data Center REST API 1.0.
Reference: https://developer.atlassian.com/server/bitbucket/rest/
"""

import logging
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

import httpx

from .config import BitbucketConfig

logger = logging.getLogger(__name__)


class BitbucketClient:
    """Client for Bitbucket Server REST API 1.0."""

    def __init__(self, config: BitbucketConfig):
        self.config = config
        self._client = httpx.Client(
            base_url=config.api_base_url,
            headers=config.auth_headers,
            verify=config.verify_ssl,
            timeout=30.0,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make authenticated GET request."""
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _get_text(self, path: str, params: Optional[dict] = None) -> str:
        """Make authenticated GET request expecting text response."""
        resp = self._client.get(path, params=params, headers={"Accept": "text/plain"})
        resp.raise_for_status()
        return resp.text

    def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        """Make authenticated POST request."""
        resp = self._client.post(path, json=json_data)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, json_data: Optional[dict] = None) -> dict:
        """Make authenticated PUT request."""
        resp = self._client.put(path, json=json_data)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _delete(self, path: str) -> None:
        """Make authenticated DELETE request."""
        resp = self._client.delete(path)
        resp.raise_for_status()

    def _get_all_pages(self, path: str, params: Optional[dict] = None) -> list:
        """Fetch all pages from a paginated Bitbucket API endpoint."""
        params = params or {}
        results = []
        start = 0

        while True:
            params["start"] = start
            data = self._get(path, params)
            results.extend(data.get("values", []))
            if data.get("isLastPage", True):
                break
            start = data.get("nextPageStart", start + data.get("size", 25))

        return results

    # ── Project / Repo Listing ─────────────────────────────────────

    def list_project_repos(
        self, project: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List repositories in a Bitbucket project.

        Args:
            project: Bitbucket project key (e.g. 'CGF', 'CGP')
            limit: Maximum repos to return
        """
        path = f"/projects/{project}/repos"
        raw = self._get_all_pages(path, {"limit": min(limit, 1000)})

        repos = []
        for r in raw[:limit]:
            clone_urls = {}
            for link in r.get("links", {}).get("clone", []):
                clone_urls[link.get("name", "")] = link.get("href", "")

            repos.append({
                "slug": r.get("slug", ""),
                "name": r.get("name", ""),
                "description": r.get("description", ""),
                "state": r.get("state", "AVAILABLE"),
                "forkable": r.get("forkable", True),
                "public": r.get("public", False),
                "project": r.get("project", {}).get("key", project),
                "clone_url_ssh": clone_urls.get("ssh", ""),
                "clone_url_https": clone_urls.get("https", clone_urls.get("http", "")),
                "link": (
                    r.get("links", {}).get("self", [{}])[0].get("href", "")
                ),
            })

        return repos

    def get_project(self, project: str) -> dict[str, Any]:
        """Get project details by key."""
        path = f"/projects/{project}"
        data = self._get(path)
        return {
            "key": data.get("key", ""),
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "public": data.get("public", False),
            "type": data.get("type", "NORMAL"),
            "link": (
                data.get("links", {}).get("self", [{}])[0].get("href", "")
            ),
        }

    @staticmethod
    def parse_pr_url(url: str) -> tuple[str, str, int]:
        """Parse a Bitbucket PR URL into (project, repo, pr_id).

        Supports:
          https://bitbucket.example.com/projects/CGP/repos/cwow-patient-query-spanner/pull-requests/1936/overview
          https://bitbucket.example.com/projects/CGP/repos/cwow-patient-query-spanner/pull-requests/1936
        """
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]

        # Expected: ['projects', 'CGP', 'repos', 'cwow-...', 'pull-requests', '1936', ...]
        try:
            proj_idx = parts.index("projects")
            repo_idx = parts.index("repos")
            pr_idx = parts.index("pull-requests")
            project = parts[proj_idx + 1]
            repo = parts[repo_idx + 1]
            pr_id = int(parts[pr_idx + 1])
            return project, repo, pr_id
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Cannot parse PR URL: {url}. "
                "Expected format: .../projects/PROJECT/repos/REPO/pull-requests/ID"
            ) from e

    # ── PR Overview ─────────────────────────────────────────────────────

    def get_pr(self, project: str, repo: str, pr_id: int) -> dict[str, Any]:
        """Get pull request overview (title, description, author, reviewers, status)."""
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}"
        data = self._get(path)

        reviewers = []
        for r in data.get("reviewers", []):
            user = r.get("user", {})
            reviewers.append({
                "name": user.get("displayName", user.get("name", "unknown")),
                "status": r.get("status", "UNAPPROVED"),
                "role": r.get("role", "REVIEWER"),
            })

        participants = []
        for p in data.get("participants", []):
            user = p.get("user", {})
            participants.append({
                "name": user.get("displayName", user.get("name", "unknown")),
                "role": p.get("role", "PARTICIPANT"),
                "status": p.get("status", "UNAPPROVED"),
            })

        return {
            "id": data["id"],
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "state": data.get("state", ""),
            "author": data.get("author", {}).get("user", {}).get("displayName", "unknown"),
            "created_date": data.get("createdDate"),
            "updated_date": data.get("updatedDate"),
            "from_branch": data.get("fromRef", {}).get("displayId", ""),
            "to_branch": data.get("toRef", {}).get("displayId", ""),
            "reviewers": reviewers,
            "participants": participants,
            "merge_conflict": data.get("properties", {}).get("mergeResult", {}).get(
                "outcome", ""
            ) == "CONFLICTED",
            "link": data.get("links", {}).get("self", [{}])[0].get("href", ""),
        }

    # ── PR Diff ─────────────────────────────────────────────────────────

    def get_pr_diff(
        self,
        project: str,
        repo: str,
        pr_id: int,
        context_lines: int = 10,
        file_path: Optional[str] = None,
    ) -> str:
        """Get the raw unified diff for a pull request.

        Args:
            project: Bitbucket project key
            repo: Repository slug
            pr_id: Pull request ID
            context_lines: Number of context lines around changes
            file_path: Optional - get diff for a specific file only
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}.diff"
        params = {"contextLines": context_lines}
        if file_path:
            params["path"] = file_path
        return self._get_text(path, params)

    # ── PR Changed Files ────────────────────────────────────────────────

    def get_pr_changes(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get list of files changed in a pull request."""
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/changes"
        raw_changes = self._get_all_pages(path)

        changes = []
        for c in raw_changes:
            src_path = c.get("path", {}).get("toString", "")
            src_parent = c.get("path", {}).get("parent", "")
            change_type = c.get("type", "MODIFY")

            # Compute source/destination for renames
            src = c.get("srcPath", {}).get("toString", src_path) if c.get("srcPath") else src_path

            changes.append({
                "path": src_path,
                "src_path": src,
                "type": change_type,  # ADD, MODIFY, DELETE, RENAME, COPY
                "node_type": c.get("nodeType", "FILE"),
                "parent": src_parent,
            })

        return changes

    # ── PR Commits ──────────────────────────────────────────────────────

    def get_pr_commits(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get commits in a pull request."""
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/commits"
        raw_commits = self._get_all_pages(path)

        commits = []
        for c in raw_commits:
            commits.append({
                "id": c.get("id", "")[:12],
                "full_id": c.get("id", ""),
                "message": c.get("message", ""),
                "author": c.get("author", {}).get("displayName",
                          c.get("author", {}).get("name", "unknown")),
                "author_email": c.get("author", {}).get("emailAddress", ""),
                "authored_date": c.get("authorTimestamp"),
                "parents": [p.get("id", "")[:12] for p in c.get("parents", [])],
            })

        return commits

    # ── PR Comments / Activities ────────────────────────────────────────

    def get_pr_activities(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get pull request activities (comments, approvals, merges, etc.)."""
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/activities"
        raw_activities = self._get_all_pages(path)

        activities = []
        for a in raw_activities:
            action = a.get("action", "")
            entry: dict[str, Any] = {
                "action": action,
                "created_date": a.get("createdDate"),
            }

            if action == "COMMENTED":
                comment = a.get("comment", {})
                entry.update({
                    "author": comment.get("author", {}).get("displayName", "unknown"),
                    "text": comment.get("text", ""),
                    "severity": comment.get("severity", "NORMAL"),
                    "state": comment.get("state", "OPEN"),
                    "anchor": self._extract_comment_anchor(a),
                })
            elif action in ("APPROVED", "UNAPPROVED", "REVIEWED", "NEEDS_WORK"):
                entry["user"] = a.get("user", {}).get("displayName", "unknown")
            elif action == "MERGED":
                entry["user"] = a.get("user", {}).get("displayName", "unknown")
            elif action == "RESCOPED":
                entry["from_hash"] = a.get("fromHash", "")[:12]
                entry["to_hash"] = a.get("toHash", "")[:12]

            activities.append(entry)

        return activities

    def get_pr_comments(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get only comments from PR activities (convenience wrapper)."""
        activities = self.get_pr_activities(project, repo, pr_id)
        return [a for a in activities if a.get("action") == "COMMENTED"]

    @staticmethod
    def _extract_comment_anchor(activity: dict) -> Optional[dict]:
        """Extract file-line anchor from an inline comment."""
        comment_anchor = activity.get("commentAnchor")
        if not comment_anchor:
            return None
        return {
            "path": comment_anchor.get("path", ""),
            "line": comment_anchor.get("line"),
            "line_type": comment_anchor.get("lineType", ""),  # ADDED, REMOVED, CONTEXT
            "file_type": comment_anchor.get("fileType", ""),  # FROM, TO
        }

    # ── File Content ────────────────────────────────────────────────────

    def get_file_content(
        self, project: str, repo: str, file_path: str, at_ref: Optional[str] = None
    ) -> str:
        """Get file content from a repository.

        Args:
            project: Bitbucket project key
            repo: Repository slug
            file_path: Path to the file in the repo
            at_ref: Optional branch/tag/commit to read from
        """
        path = f"/projects/{project}/repos/{repo}/browse/{file_path}"
        params = {}
        if at_ref:
            params["at"] = at_ref

        data = self._get(path, params)

        # Bitbucket returns file content in "lines" array
        lines = data.get("lines", [])
        return "\n".join(line.get("text", "") for line in lines)

    # ── PR Tasks ────────────────────────────────────────────────────────

    def get_pr_tasks(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get tasks associated with a PR."""
        # Tasks are embedded in comments via activities
        comments = self.get_pr_comments(project, repo, pr_id)
        # Filter for task-like items (Bitbucket Server uses comment severity for tasks)
        tasks = []
        for c in comments:
            if c.get("severity") == "BLOCKER":
                tasks.append({
                    "text": c.get("text", ""),
                    "author": c.get("author", "unknown"),
                    "state": c.get("state", "OPEN"),
                    "anchor": c.get("anchor"),
                })
        return tasks

    # ── Dashboard / Inbox ─────────────────────────────────────────────

    def get_inbox_prs(self, limit: int = 25) -> list[dict[str, Any]]:
        """Get PRs in the authenticated user's review inbox."""
        path = "/inbox/pull-requests"
        raw = self._get_all_pages(path, {"limit": limit})
        return [self._summarize_pr(pr) for pr in raw]

    def get_dashboard_prs(
        self, role: str = "reviewer", state: str = "OPEN", limit: int = 25
    ) -> list[dict[str, Any]]:
        """Get PRs from the user's dashboard.

        Args:
            role: 'author', 'reviewer', or 'participant'
            state: 'OPEN', 'MERGED', 'DECLINED', or 'ALL'
            limit: Max results
        """
        path = "/dashboard/pull-requests"
        raw = self._get_all_pages(path, {"role": role, "state": state, "limit": limit})
        return [self._summarize_pr(pr) for pr in raw]

    @staticmethod
    def _summarize_pr(pr: dict) -> dict[str, Any]:
        """Create a compact summary of a PR for listing."""
        repo = pr.get("toRef", {}).get("repository", {})
        reviewers = []
        for r in pr.get("reviewers", []):
            user = r.get("user", {})
            reviewers.append({
                "name": user.get("displayName", user.get("name", "unknown")),
                "status": r.get("status", "UNAPPROVED"),
            })

        return {
            "id": pr.get("id"),
            "title": pr.get("title", ""),
            "state": pr.get("state", ""),
            "author": pr.get("author", {}).get("user", {}).get("displayName", "unknown"),
            "project": repo.get("project", {}).get("key", ""),
            "repo": repo.get("slug", ""),
            "from_branch": pr.get("fromRef", {}).get("displayId", ""),
            "to_branch": pr.get("toRef", {}).get("displayId", ""),
            "reviewers": reviewers,
            "created_date": pr.get("createdDate"),
            "updated_date": pr.get("updatedDate"),
            "link": pr.get("links", {}).get("self", [{}])[0].get("href", ""),
        }

    # ── Merge Check ─────────────────────────────────────────────────────

    def get_pr_merge_status(self, project: str, repo: str, pr_id: int) -> dict[str, Any]:
        """Check if a PR can be merged."""
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/merge"
        try:
            data = self._get(path)
            return {
                "can_merge": data.get("canMerge", False),
                "vetoes": [
                    {
                        "summary": v.get("summaryMessage", ""),
                        "detail": v.get("detailedMessage", ""),
                    }
                    for v in data.get("vetoes", [])
                ],
            }
        except httpx.HTTPStatusError as e:
            return {
                "can_merge": False,
                "error": str(e),
            }

    # ── PR Approval / Decline / Merge ──────────────────────────────────

    def approve_pr(self, project: str, repo: str, pr_id: int) -> dict[str, Any]:
        """Approve a pull request as the authenticated user.

        Bitbucket Server REST API: POST .../pull-requests/{id}/approve
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/approve"
        data = self._post(path)
        return {
            "status": "APPROVED",
            "user": data.get("user", {}).get("displayName", "unknown"),
            "role": data.get("role", "REVIEWER"),
        }

    def unapprove_pr(self, project: str, repo: str, pr_id: int) -> dict[str, Any]:
        """Remove approval from a pull request.

        Bitbucket Server REST API: DELETE .../pull-requests/{id}/approve
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/approve"
        self._delete(path)
        return {"status": "UNAPPROVED"}

    def needs_work_pr(self, project: str, repo: str, pr_id: int) -> dict[str, Any]:
        """Mark a pull request as needs work.

        Bitbucket Server REST API: PUT .../pull-requests/{id}/participants/{userSlug}
        with {"status": "NEEDS_WORK"}
        """
        # First get current user slug
        user_path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}"
        pr_data = self._get(user_path)
        # Find our participant entry to get the user slug
        # Use the participants endpoint with status update
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/participants"
        # The API accepts a PUT to the participants collection with user+status
        data = self._put(path, {"status": "NEEDS_WORK"})
        return {
            "status": "NEEDS_WORK",
            "user": data.get("user", {}).get("displayName", "unknown"),
        }

    def decline_pr(
        self, project: str, repo: str, pr_id: int, version: int = -1
    ) -> dict[str, Any]:
        """Decline a pull request.

        Bitbucket Server REST API: POST .../pull-requests/{id}/decline
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/decline"
        params = {}
        if version >= 0:
            params["version"] = version
        resp = self._client.post(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        return {
            "id": data.get("id"),
            "state": data.get("state", "DECLINED"),
            "title": data.get("title", ""),
        }

    def merge_pr(
        self, project: str, repo: str, pr_id: int, version: int = -1
    ) -> dict[str, Any]:
        """Merge a pull request.

        Bitbucket Server REST API: POST .../pull-requests/{id}/merge
        Requires all merge checks to pass.
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/merge"
        params = {}
        if version >= 0:
            params["version"] = version
        resp = self._client.post(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        return {
            "id": data.get("id"),
            "state": data.get("state", "MERGED"),
            "title": data.get("title", ""),
            "close_source_branch": data.get("closedDate") is not None,
        }

    # ── Comment Posting ─────────────────────────────────────────────────

    def add_pr_comment(
        self,
        project: str,
        repo: str,
        pr_id: int,
        text: str,
        severity: str = "NORMAL",
    ) -> dict[str, Any]:
        """Add a general comment to a pull request.

        Args:
            project: Bitbucket project key
            repo: Repository slug
            pr_id: Pull request ID
            text: Comment text (supports Markdown)
            severity: 'NORMAL' or 'BLOCKER' (blocker = task)
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/comments"
        payload = {"text": text, "severity": severity}
        data = self._post(path, payload)
        return {
            "id": data.get("id"),
            "text": data.get("text", ""),
            "author": data.get("author", {}).get("displayName", "unknown"),
            "created_date": data.get("createdDate"),
            "severity": data.get("severity", "NORMAL"),
        }

    def add_pr_inline_comment(
        self,
        project: str,
        repo: str,
        pr_id: int,
        text: str,
        file_path: str,
        line: int,
        line_type: str = "ADDED",
        file_type: str = "TO",
        severity: str = "NORMAL",
    ) -> dict[str, Any]:
        """Add an inline comment on a specific file/line in a pull request.

        Args:
            project: Bitbucket project key
            repo: Repository slug
            pr_id: Pull request ID
            text: Comment text (supports Markdown)
            file_path: Path to the file in the diff
            line: Line number to comment on
            line_type: 'ADDED', 'REMOVED', or 'CONTEXT'
            file_type: 'TO' (new version) or 'FROM' (old version)
            severity: 'NORMAL' or 'BLOCKER' (blocker = task)
        """
        path = f"/projects/{project}/repos/{repo}/pull-requests/{pr_id}/comments"
        payload = {
            "text": text,
            "severity": severity,
            "anchor": {
                "path": file_path,
                "line": line,
                "lineType": line_type,
                "fileType": file_type,
            },
        }
        data = self._post(path, payload)
        return {
            "id": data.get("id"),
            "text": data.get("text", ""),
            "author": data.get("author", {}).get("displayName", "unknown"),
            "created_date": data.get("createdDate"),
            "severity": data.get("severity", "NORMAL"),
            "anchor": {
                "path": file_path,
                "line": line,
                "line_type": line_type,
            },
        }
