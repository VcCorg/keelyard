"""Tests for Phase 2: Bitbucket client + dva domain fetch-repos command."""

import json
import pytest
from unittest.mock import patch, MagicMock

from agentic_cli import tracker
from agentic_cli.mcp_tool_client import MCPToolError, parse_project_key


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect tracker.db to a temp directory for each test."""
    db_dir = tmp_path / ".dva-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    tracker._ensure_db()
    yield db_dir


MOCK_REPOS_RAW = [
    {
        "slug": "cwow-facility-service",
        "name": "cwow-facility-service",
        "description": "Facility microservice",
        "state": "AVAILABLE",
        "project": {"key": "CGF"},
        "links": {
            "clone": [
                {"name": "ssh", "href": "ssh://git@bb.example.com:7999/cgf/cwow-facility-service.git"},
                {"name": "http", "href": "https://bb.example.com/scm/cgf/cwow-facility-service.git"},
            ],
            "self": [{"href": "https://bb.example.com/projects/CGF/repos/cwow-facility-service"}],
        },
    },
    {
        "slug": "cwow-facility-config",
        "name": "cwow-facility-config",
        "description": "Config repo",
        "state": "AVAILABLE",
        "project": {"key": "CGF"},
        "links": {
            "clone": [
                {"name": "http", "href": "https://bb.example.com/scm/cgf/cwow-facility-config.git"},
            ],
            "self": [{"href": "https://bb.example.com/projects/CGF/repos/cwow-facility-config"}],
        },
    },
    {
        "slug": "cwow-patient-query",
        "name": "cwow-patient-query",
        "description": "Patient query service",
        "state": "AVAILABLE",
        "project": {"key": "CGF"},
        "links": {"clone": [], "self": [{"href": ""}]},
    },
]


# ---------------------------------------------------------------------------
# BitbucketClient tests
# ---------------------------------------------------------------------------

class TestParseProjectKey:
    def test_plain_key(self):
        assert parse_project_key("CGF") == "CGF"

    def test_url_with_project(self):
        assert parse_project_key("https://bitbucket.example.com/projects/CGF") == "CGF"

    def test_url_with_repos(self):
        assert parse_project_key("https://bitbucket.example.com/projects/CGF/repos/my-repo") == "CGF"

    def test_empty_string(self):
        assert parse_project_key("") == ""

    def test_no_projects_segment(self):
        assert parse_project_key("https://example.com/foo/bar") == "https://example.com/foo/bar"


# ---------------------------------------------------------------------------
# Interactive picker tests
# ---------------------------------------------------------------------------

from agentic_cli.commands.domain import _interactive_repo_picker

MOCK_REPOS_PARSED = [
    {"slug": "repo-a", "name": "Repo A"},
    {"slug": "repo-b", "name": "Repo B"},
    {"slug": "repo-c", "name": "Repo C"},
    {"slug": "repo-d", "name": "Repo D"},
    {"slug": "repo-e", "name": "Repo E"},
]


class TestInteractivePicker:
    def test_select_single(self):
        with patch("builtins.input", return_value="2"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 1
        assert result[0]["slug"] == "repo-b"

    def test_select_multiple_comma(self):
        with patch("builtins.input", return_value="1,3,5"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 3
        slugs = [r["slug"] for r in result]
        assert slugs == ["repo-a", "repo-c", "repo-e"]

    def test_select_range(self):
        with patch("builtins.input", return_value="2-4"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 3
        slugs = [r["slug"] for r in result]
        assert slugs == ["repo-b", "repo-c", "repo-d"]

    def test_select_all(self):
        with patch("builtins.input", return_value="all"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 5

    def test_empty_input_cancels(self):
        with patch("builtins.input", return_value=""):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert result == []

    def test_skips_already_linked(self):
        with patch("builtins.input", return_value="all"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, {"repo-b", "repo-d"})
        assert len(result) == 3
        slugs = [r["slug"] for r in result]
        assert "repo-b" not in slugs
        assert "repo-d" not in slugs

    def test_invalid_input_skipped(self):
        with patch("builtins.input", return_value="1,abc,3"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 2
        slugs = [r["slug"] for r in result]
        assert slugs == ["repo-a", "repo-c"]

    def test_out_of_range_ignored(self):
        with patch("builtins.input", return_value="0,1,99"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 1
        assert result[0]["slug"] == "repo-a"

    def test_mixed_ranges_and_numbers(self):
        with patch("builtins.input", return_value="1,3-5"):
            result = _interactive_repo_picker(MOCK_REPOS_PARSED, set())
        assert len(result) == 4
        slugs = [r["slug"] for r in result]
        assert slugs == ["repo-a", "repo-c", "repo-d", "repo-e"]


# ---------------------------------------------------------------------------
# CLI fetch-repos tests (mocked Bitbucket API)
# ---------------------------------------------------------------------------

from typer.testing import CliRunner
from agentic_cli.commands.domain import domain_app

runner = CliRunner()

MOCK_BB_REPOS = [
    {"slug": "cwow-facility-service", "name": "CWOW Facility Service",
     "clone_url_https": "https://bb.example.com/scm/cgf/cwow-facility-service.git",
     "clone_url_ssh": "ssh://git@bb.example.com:7999/cgf/cwow-facility-service.git"},
    {"slug": "cwow-facility-config", "name": "CWOW Facility Config",
     "clone_url_https": "https://bb.example.com/scm/cgf/cwow-facility-config.git",
     "clone_url_ssh": ""},
    {"slug": "cwow-patient-query", "name": "CWOW Patient Query",
     "clone_url_https": "", "clone_url_ssh": ""},
]

MCP_PATCH = "agentic_cli.mcp_tool_client"


def _setup_domain():
    """Helper: create product + domain with BB project for fetch-repos tests."""
    tracker.register_product(name="CWOW")
    tracker.register_domain(
        name="cwow-facility",
        product="CWOW",
        domain="Facility",
        bitbucket_project="CGF",
    )


class TestFetchReposCLI:
    def test_domain_not_found(self):
        result = runner.invoke(domain_app, ["fetch-repos", "nope"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_no_bb_project(self):
        tracker.register_product(name="CWOW")
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = runner.invoke(domain_app, ["fetch-repos", "cwow-facility"])
        assert result.exit_code == 1
        assert "no Bitbucket project" in result.output

    def test_mcp_connection_error(self):
        _setup_domain()
        with patch(f"{MCP_PATCH}.bb_list_project_repos", side_effect=MCPToolError("Cannot connect", is_connection_error=True)):
            result = runner.invoke(domain_app, ["fetch-repos", "cwow-facility"])
        assert result.exit_code == 1
        assert "Cannot connect" in result.output

    def test_auto_link_all(self):
        _setup_domain()

        with patch(f"{MCP_PATCH}.bb_list_project_repos", return_value=MOCK_BB_REPOS):
            result = runner.invoke(domain_app, ["fetch-repos", "cwow-facility", "--all"])

        assert result.exit_code == 0
        assert "Linked" in result.output
        assert "3" in result.output  # 3 repos linked

        repos = tracker.get_domain_repos("cwow-facility")
        assert len(repos) == 3
        slugs = {r["repo_slug"] for r in repos}
        assert "cwow-facility-service" in slugs
        assert "cwow-facility-config" in slugs
        assert "cwow-patient-query" in slugs

    def test_auto_link_skips_existing(self):
        _setup_domain()
        # Pre-link one repo
        tracker.link_repo_to_domain("cwow-facility", "cwow-facility-service")

        with patch(f"{MCP_PATCH}.bb_list_project_repos", return_value=MOCK_BB_REPOS):
            result = runner.invoke(domain_app, ["fetch-repos", "cwow-facility", "--all"])

        assert result.exit_code == 0
        assert "2" in result.output  # only 2 new repos linked

        repos = tracker.get_domain_repos("cwow-facility")
        assert len(repos) == 3

    def test_filter_repos(self):
        _setup_domain()

        with patch(f"{MCP_PATCH}.bb_list_project_repos", return_value=MOCK_BB_REPOS):
            result = runner.invoke(domain_app, [
                "fetch-repos", "cwow-facility", "--filter", "facility", "--all",
            ])

        assert result.exit_code == 0
        repos = tracker.get_domain_repos("cwow-facility")
        assert len(repos) == 2  # only facility-service and facility-config
        slugs = {r["repo_slug"] for r in repos}
        assert "cwow-patient-query" not in slugs

    def test_filter_no_match(self):
        _setup_domain()

        with patch(f"{MCP_PATCH}.bb_list_project_repos", return_value=MOCK_BB_REPOS):
            result = runner.invoke(domain_app, [
                "fetch-repos", "cwow-facility", "--filter", "zzz-nope", "--all",
            ])

        assert result.exit_code == 0
        assert "No repos matching" in result.output

    def test_empty_project(self):
        _setup_domain()

        with patch(f"{MCP_PATCH}.bb_list_project_repos", return_value=[]):
            result = runner.invoke(domain_app, ["fetch-repos", "cwow-facility", "--all"])

        assert result.exit_code == 0
        assert "No repos found" in result.output
