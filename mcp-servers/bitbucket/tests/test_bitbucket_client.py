"""Tests for Bitbucket Server REST API client."""

import json
import pytest
import httpx
from unittest.mock import patch, MagicMock

from bitbucket_server_mcp.config import BitbucketConfig
from bitbucket_server_mcp.bitbucket_client import BitbucketClient


@pytest.fixture
def config():
    return BitbucketConfig(
        server_url="https://bitbucket.example.com",
        personal_access_token="test-token-123",
        default_project="PROJ",
        default_repo="my-repo",
    )


@pytest.fixture
def client(config):
    return BitbucketClient(config)


# ── URL Parsing ─────────────────────────────────────────────────────────────


class TestParseUrl:
    def test_parse_pr_url_with_overview(self):
        url = "https://bitbucket.example.com/projects/CGP/repos/cwow-patient-query-spanner/pull-requests/1936/overview"
        project, repo, pr_id = BitbucketClient.parse_pr_url(url)
        assert project == "CGP"
        assert repo == "cwow-patient-query-spanner"
        assert pr_id == 1936

    def test_parse_pr_url_without_overview(self):
        url = "https://bitbucket.example.com/projects/CGP/repos/cwow-patient-query-spanner/pull-requests/1936"
        project, repo, pr_id = BitbucketClient.parse_pr_url(url)
        assert project == "CGP"
        assert repo == "cwow-patient-query-spanner"
        assert pr_id == 1936

    def test_parse_pr_url_with_diff_tab(self):
        url = "https://bitbucket.example.com/projects/CGP/repos/my-repo/pull-requests/42/diff"
        project, repo, pr_id = BitbucketClient.parse_pr_url(url)
        assert project == "CGP"
        assert repo == "my-repo"
        assert pr_id == 42

    def test_parse_pr_url_invalid(self):
        with pytest.raises(ValueError, match="Cannot parse PR URL"):
            BitbucketClient.parse_pr_url("https://bitbucket.example.com/projects/CGP")

    def test_parse_pr_url_not_a_pr(self):
        with pytest.raises(ValueError, match="Cannot parse PR URL"):
            BitbucketClient.parse_pr_url("https://bitbucket.example.com/projects/CGP/repos/my-repo/browse")


# ── Config ──────────────────────────────────────────────────────────────────


class TestConfig:
    def test_api_base_url(self, config):
        assert config.api_base_url == "https://bitbucket.example.com/rest/api/1.0"

    def test_api_base_url_strips_trailing_slash(self):
        c = BitbucketConfig(server_url="https://example.com/", personal_access_token="t")
        assert c.api_base_url == "https://example.com/rest/api/1.0"

    def test_is_configured_true(self, config):
        assert config.is_configured is True

    def test_is_configured_false_no_token(self):
        c = BitbucketConfig(server_url="https://example.com", personal_access_token="")
        assert c.is_configured is False

    def test_auth_headers(self, config):
        headers = config.auth_headers
        assert headers["Authorization"] == "Bearer test-token-123"
        assert "Accept" in headers


# ── Client Methods (mocked HTTP) ────────────────────────────────────────────


class TestClientMethods:
    def test_get_pr(self, client):
        mock_response = {
            "id": 1936,
            "title": "Add new feature",
            "description": "This adds feature X",
            "state": "OPEN",
            "author": {"user": {"displayName": "John Doe"}},
            "createdDate": 1711800000000,
            "updatedDate": 1711900000000,
            "fromRef": {"displayId": "feature/new-thing"},
            "toRef": {"displayId": "main"},
            "reviewers": [
                {
                    "user": {"displayName": "Jane Smith", "name": "jsmith"},
                    "status": "APPROVED",
                    "role": "REVIEWER",
                }
            ],
            "participants": [],
            "properties": {},
            "links": {"self": [{"href": "https://example.com/pr/1936"}]},
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_pr("CGP", "my-repo", 1936)

        assert result["id"] == 1936
        assert result["title"] == "Add new feature"
        assert result["author"] == "John Doe"
        assert result["from_branch"] == "feature/new-thing"
        assert result["to_branch"] == "main"
        assert len(result["reviewers"]) == 1
        assert result["reviewers"][0]["status"] == "APPROVED"

    def test_get_pr_changes(self, client):
        mock_response = [
            {
                "path": {"toString": "src/main.py", "parent": "src"},
                "type": "MODIFY",
                "nodeType": "FILE",
            },
            {
                "path": {"toString": "src/new_file.py", "parent": "src"},
                "type": "ADD",
                "nodeType": "FILE",
            },
        ]

        with patch.object(client, "_get_all_pages", return_value=mock_response):
            result = client.get_pr_changes("CGP", "my-repo", 1936)

        assert len(result) == 2
        assert result[0]["path"] == "src/main.py"
        assert result[0]["type"] == "MODIFY"
        assert result[1]["type"] == "ADD"

    def test_get_pr_commits(self, client):
        mock_response = [
            {
                "id": "abc123def456789",
                "message": "Initial commit",
                "author": {"displayName": "John", "emailAddress": "john@example.com"},
                "authorTimestamp": 1711800000000,
                "parents": [{"id": "parent1234567"}],
            }
        ]

        with patch.object(client, "_get_all_pages", return_value=mock_response):
            result = client.get_pr_commits("CGP", "my-repo", 1936)

        assert len(result) == 1
        assert result[0]["id"] == "abc123def456"
        assert result[0]["message"] == "Initial commit"
        assert result[0]["author"] == "John"

    def test_get_pr_diff(self, client):
        mock_diff = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"

        with patch.object(client, "_get_text", return_value=mock_diff):
            result = client.get_pr_diff("CGP", "my-repo", 1936)

        assert "diff --git" in result
        assert "-old" in result
        assert "+new" in result

    def test_get_pr_activities_comments(self, client):
        mock_response = [
            {
                "action": "COMMENTED",
                "createdDate": 1711800000000,
                "comment": {
                    "author": {"displayName": "Reviewer"},
                    "text": "Looks good!",
                    "severity": "NORMAL",
                    "state": "OPEN",
                },
            },
            {
                "action": "APPROVED",
                "createdDate": 1711900000000,
                "user": {"displayName": "Reviewer"},
            },
        ]

        with patch.object(client, "_get_all_pages", return_value=mock_response):
            result = client.get_pr_activities("CGP", "my-repo", 1936)

        assert len(result) == 2
        assert result[0]["action"] == "COMMENTED"
        assert result[0]["text"] == "Looks good!"
        assert result[1]["action"] == "APPROVED"

    def test_get_pr_comments_filters_correctly(self, client):
        mock_activities = [
            {
                "action": "COMMENTED",
                "createdDate": 1711800000000,
                "comment": {
                    "author": {"displayName": "Reviewer"},
                    "text": "Fix this",
                    "severity": "NORMAL",
                    "state": "OPEN",
                },
            },
            {
                "action": "APPROVED",
                "createdDate": 1711900000000,
                "user": {"displayName": "Reviewer"},
            },
        ]

        with patch.object(client, "_get_all_pages", return_value=mock_activities):
            result = client.get_pr_comments("CGP", "my-repo", 1936)

        assert len(result) == 1
        assert result[0]["text"] == "Fix this"

    def test_get_file_content(self, client):
        mock_response = {
            "lines": [
                {"text": "import os"},
                {"text": ""},
                {"text": "def main():"},
                {"text": "    pass"},
            ]
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_file_content("CGP", "my-repo", "src/main.py")

        assert "import os" in result
        assert "def main():" in result

    def test_get_merge_status(self, client):
        mock_response = {
            "canMerge": True,
            "vetoes": [],
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_pr_merge_status("CGP", "my-repo", 1936)

        assert result["can_merge"] is True
        assert result["vetoes"] == []

    def test_get_merge_status_with_vetoes(self, client):
        mock_response = {
            "canMerge": False,
            "vetoes": [
                {
                    "summaryMessage": "Needs approvals",
                    "detailedMessage": "Requires 2 approvals, has 1",
                }
            ],
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_pr_merge_status("CGP", "my-repo", 1936)

        assert result["can_merge"] is False
        assert len(result["vetoes"]) == 1


# ── Project / Repo Listing ──────────────────────────────────────────────────


class TestProjectRepoListing:
    def test_list_project_repos(self, client):
        mock_repos = [
            {
                "slug": "cwow-patient-query-spanner",
                "name": "cwow-patient-query-spanner",
                "description": "Patient query service",
                "state": "AVAILABLE",
                "forkable": True,
                "public": False,
                "project": {"key": "CGF"},
                "links": {
                    "clone": [
                        {"name": "ssh", "href": "ssh://git@bitbucket.example.com:7999/cgf/cwow-patient-query-spanner.git"},
                        {"name": "http", "href": "https://bitbucket.example.com/scm/cgf/cwow-patient-query-spanner.git"},
                    ],
                    "self": [{"href": "https://bitbucket.example.com/projects/CGF/repos/cwow-patient-query-spanner"}],
                },
            },
            {
                "slug": "cwow-facility-service",
                "name": "cwow-facility-service",
                "description": "",
                "state": "AVAILABLE",
                "forkable": True,
                "public": False,
                "project": {"key": "CGF"},
                "links": {"clone": [], "self": [{"href": "https://bitbucket.example.com/projects/CGF/repos/cwow-facility-service"}]},
            },
        ]

        with patch.object(client, "_get_all_pages", return_value=mock_repos):
            result = client.list_project_repos("CGF")

        assert len(result) == 2
        assert result[0]["slug"] == "cwow-patient-query-spanner"
        assert result[0]["project"] == "CGF"
        assert "ssh" in result[0]["clone_url_ssh"]
        assert result[1]["slug"] == "cwow-facility-service"
        assert result[1]["clone_url_ssh"] == ""

    def test_list_project_repos_with_limit(self, client):
        mock_repos = [{"slug": f"repo-{i}", "name": f"repo-{i}", "project": {"key": "CGF"}, "links": {"clone": [], "self": [{}]}} for i in range(10)]

        with patch.object(client, "_get_all_pages", return_value=mock_repos):
            result = client.list_project_repos("CGF", limit=3)

        assert len(result) == 3

    def test_get_project(self, client):
        mock_response = {
            "key": "CGF",
            "name": "CWOW General Facility",
            "description": "CWOW Facility domain project",
            "public": False,
            "type": "NORMAL",
            "links": {"self": [{"href": "https://bitbucket.example.com/projects/CGF"}]},
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_project("CGF")

        assert result["key"] == "CGF"
        assert result["name"] == "CWOW General Facility"
        assert result["type"] == "NORMAL"


# ── Pagination ──────────────────────────────────────────────────────────────


class TestPagination:
    def test_get_all_pages_single_page(self, client):
        mock_response = {
            "values": [{"id": 1}, {"id": 2}],
            "isLastPage": True,
            "size": 2,
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = client._get_all_pages("/test")

        assert len(result) == 2

    def test_get_all_pages_multiple_pages(self, client):
        page1 = {"values": [{"id": 1}], "isLastPage": False, "nextPageStart": 1, "size": 1}
        page2 = {"values": [{"id": 2}], "isLastPage": True, "size": 1}

        with patch.object(client, "_get", side_effect=[page1, page2]):
            result = client._get_all_pages("/test")

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
