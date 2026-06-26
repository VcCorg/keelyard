"""Jira Server REST API client.

Wraps the Jira Server/Data Center REST API v2 for use by the MCP server.
"""

from typing import Any
from urllib.parse import urlparse

import httpx

from .config import JiraConfig


class JiraClient:
    """Client for Jira Server REST API v2."""

    def __init__(self, config: JiraConfig | None = None):
        self._config = config or JiraConfig()
        self._client: httpx.Client | None = None

    def __enter__(self):
        self._client = httpx.Client(
            base_url=self._config.api_base_url,
            headers=self._config.auth_headers,
            verify=self._config.jira_verify_ssl,
            timeout=30.0,
        )
        return self

    def __exit__(self, *args):
        if self._client:
            self._client.close()
            self._client = None

    # ── HTTP helpers ─────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        """GET request returning JSON."""
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: dict | None = None) -> dict[str, Any]:
        """POST request returning JSON."""
        resp = self._client.post(path, json=json_data)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _put(self, path: str, json_data: dict | None = None) -> dict[str, Any]:
        """PUT request returning JSON."""
        resp = self._client.put(path, json=json_data)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ── URL parsing ──────────────────────────────────────────────────────

    @staticmethod
    def parse_issue_url(url: str) -> str:
        """Parse a Jira issue URL into an issue key.

        Supports:
          https://jira.example.com/browse/PROJ-12345
          https://jira.example.com/browse/PROJ-12345?...
        """
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        try:
            browse_idx = parts.index("browse")
            return parts[browse_idx + 1]
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Cannot parse Jira issue URL: {url}. "
                "Expected format: .../browse/PROJECT-123"
            ) from e

    # ── Current user ─────────────────────────────────────────────────────

    def get_myself(self) -> dict[str, Any]:
        """Get current authenticated user info."""
        data = self._get("/myself")
        return {
            "key": data.get("key", ""),
            "name": data.get("name", ""),
            "display_name": data.get("displayName", ""),
            "email": data.get("emailAddress", ""),
        }

    # ── Issues ───────────────────────────────────────────────────────────

    def get_issue(self, issue_key: str, expand: str | None = None) -> dict[str, Any]:
        """Get issue details by key (e.g. CWHE-12345)."""
        params = {}
        if expand:
            params["expand"] = expand
        data = self._get(f"/issue/{issue_key}", params=params)
        fields = data.get("fields", {})

        assignee = fields.get("assignee") or {}
        reporter = fields.get("reporter") or {}
        priority = fields.get("priority") or {}
        status = fields.get("status") or {}
        issuetype = fields.get("issuetype") or {}
        project = fields.get("project") or {}
        resolution = fields.get("resolution") or {}
        parent = fields.get("parent") or {}

        # Extract fix versions
        fix_versions = [v.get("name", "") for v in fields.get("fixVersions", [])]

        # Extract components
        components = [c.get("name", "") for c in fields.get("components", [])]

        # Extract labels
        labels = fields.get("labels", [])

        # Extract subtasks
        subtasks = []
        for st in fields.get("subtasks", []):
            st_fields = st.get("fields", {})
            subtasks.append({
                "key": st.get("key", ""),
                "summary": st_fields.get("summary", ""),
                "status": (st_fields.get("status") or {}).get("name", ""),
                "issuetype": (st_fields.get("issuetype") or {}).get("name", ""),
            })

        # Extract linked issues
        issue_links = []
        for link in fields.get("issuelinks", []):
            link_type = link.get("type", {})
            if "outwardIssue" in link:
                linked = link["outwardIssue"]
                direction = "outward"
                relation = link_type.get("outward", "")
            elif "inwardIssue" in link:
                linked = link["inwardIssue"]
                direction = "inward"
                relation = link_type.get("inward", "")
            else:
                continue
            linked_fields = linked.get("fields", {})
            issue_links.append({
                "direction": direction,
                "relation": relation,
                "key": linked.get("key", ""),
                "summary": linked_fields.get("summary", ""),
                "status": (linked_fields.get("status") or {}).get("name", ""),
            })

        return {
            "key": data.get("key", ""),
            "id": data.get("id", ""),
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": status.get("name", ""),
            "status_category": (status.get("statusCategory") or {}).get("name", ""),
            "priority": priority.get("name", ""),
            "issuetype": issuetype.get("name", ""),
            "project": {
                "key": project.get("key", ""),
                "name": project.get("name", ""),
            },
            "assignee": assignee.get("displayName", "Unassigned"),
            "reporter": reporter.get("displayName", ""),
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "resolution": resolution.get("name") if resolution else None,
            "resolution_date": fields.get("resolutiondate"),
            "fix_versions": fix_versions,
            "components": components,
            "labels": labels,
            "parent": {
                "key": parent.get("key", ""),
                "summary": (parent.get("fields") or {}).get("summary", ""),
            } if parent else None,
            "subtasks": subtasks,
            "issue_links": issue_links,
            "link": f"{self._config.jira_server_url}/browse/{data.get('key', '')}",
        }

    def search_issues(
        self,
        jql: str,
        max_results: int = 20,
        fields: str | None = None,
    ) -> dict[str, Any]:
        """Search issues using JQL."""
        params: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
        }
        if fields:
            params["fields"] = fields
        else:
            params["fields"] = (
                "summary,status,priority,assignee,reporter,issuetype,"
                "project,created,updated,labels,components,fixVersions"
            )

        data = self._get("/search", params=params)

        issues = []
        for item in data.get("issues", []):
            f = item.get("fields", {})
            assignee = f.get("assignee") or {}
            reporter = f.get("reporter") or {}
            issues.append({
                "key": item.get("key", ""),
                "summary": f.get("summary", ""),
                "status": (f.get("status") or {}).get("name", ""),
                "priority": (f.get("priority") or {}).get("name", ""),
                "assignee": assignee.get("displayName", "Unassigned"),
                "reporter": reporter.get("displayName", ""),
                "issuetype": (f.get("issuetype") or {}).get("name", ""),
                "project": (f.get("project") or {}).get("key", ""),
                "created": f.get("created", ""),
                "updated": f.get("updated", ""),
                "labels": f.get("labels", []),
                "link": f"{self._config.jira_server_url}/browse/{item.get('key', '')}",
            })

        return {
            "total": data.get("total", 0),
            "max_results": data.get("maxResults", max_results),
            "start_at": data.get("startAt", 0),
            "issues": issues,
        }

    # ── Comments ─────────────────────────────────────────────────────────

    def get_comments(self, issue_key: str) -> list[dict[str, Any]]:
        """Get all comments on an issue."""
        data = self._get(f"/issue/{issue_key}/comment")
        comments = []
        for c in data.get("comments", []):
            author = c.get("author") or {}
            update_author = c.get("updateAuthor") or {}
            comments.append({
                "id": c.get("id", ""),
                "body": c.get("body", ""),
                "author": author.get("displayName", ""),
                "created": c.get("created", ""),
                "updated": c.get("updated", ""),
                "update_author": update_author.get("displayName", ""),
            })
        return comments

    def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        """Add a comment to an issue."""
        data = self._post(f"/issue/{issue_key}/comment", json_data={"body": body})
        author = (data.get("author") or {})
        return {
            "id": data.get("id", ""),
            "body": data.get("body", ""),
            "author": author.get("displayName", ""),
            "created": data.get("created", ""),
        }

    # ── Transitions ──────────────────────────────────────────────────────

    def get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Get available transitions for an issue."""
        data = self._get(f"/issue/{issue_key}/transitions")
        transitions = []
        for t in data.get("transitions", []):
            to_status = t.get("to") or {}
            transitions.append({
                "id": t.get("id", ""),
                "name": t.get("name", ""),
                "to_status": to_status.get("name", ""),
                "to_category": (to_status.get("statusCategory") or {}).get("name", ""),
            })
        return transitions

    def transition_issue(self, issue_key: str, transition_id: str) -> dict[str, Any]:
        """Perform a transition on an issue."""
        self._post(
            f"/issue/{issue_key}/transitions",
            json_data={"transition": {"id": transition_id}},
        )
        return {"status": "ok", "issue": issue_key, "transition_id": transition_id}

    # ── Assignment ───────────────────────────────────────────────────────

    def assign_issue(self, issue_key: str, assignee: str) -> dict[str, Any]:
        """Assign an issue to a user (use username/key, or '-1' for unassign)."""
        self._put(f"/issue/{issue_key}/assignee", json_data={"name": assignee})
        return {"status": "ok", "issue": issue_key, "assignee": assignee}

    # ── Projects ─────────────────────────────────────────────────────────

    def list_projects(self) -> list[dict[str, Any]]:
        """List all visible projects."""
        data = self._get("/project")
        projects = []
        for p in data:
            lead = p.get("lead") or {}
            projects.append({
                "key": p.get("key", ""),
                "name": p.get("name", ""),
                "project_type": p.get("projectTypeKey", ""),
                "lead": lead.get("displayName", ""),
            })
        return projects

    # ── Sprint / Board (Agile REST API) ──────────────────────────────────

    def get_sprint_issues(
        self, board_id: int, sprint_id: int | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        """Get issues in the active sprint for a board.

        Uses Jira Agile REST API (different base path).
        """
        agile_base = f"{self._config.jira_server_url.rstrip('/')}/rest/agile/1.0"

        if sprint_id is None:
            # Get active sprint
            resp = self._client.get(
                f"{agile_base}/board/{board_id}/sprint",
                params={"state": "active"},
            )
            resp.raise_for_status()
            sprints = resp.json().get("values", [])
            if not sprints:
                return {"sprint": None, "issues": [], "message": "No active sprint found"}
            sprint_id = sprints[0]["id"]
            sprint_name = sprints[0].get("name", "")
        else:
            sprint_name = ""

        resp = self._client.get(
            f"{agile_base}/sprint/{sprint_id}/issue",
            params={"maxResults": max_results},
        )
        resp.raise_for_status()
        data = resp.json()

        issues = []
        for item in data.get("issues", []):
            f = item.get("fields", {})
            assignee = f.get("assignee") or {}
            issues.append({
                "key": item.get("key", ""),
                "summary": f.get("summary", ""),
                "status": (f.get("status") or {}).get("name", ""),
                "priority": (f.get("priority") or {}).get("name", ""),
                "assignee": assignee.get("displayName", "Unassigned"),
                "issuetype": (f.get("issuetype") or {}).get("name", ""),
                "story_points": f.get("customfield_10002"),
            })

        return {
            "sprint_id": sprint_id,
            "sprint_name": sprint_name,
            "total": data.get("total", 0),
            "issues": issues,
        }
