"""Tests for Phase 3: MCP-based doc management — dva domain add-docs/docs/sync-docs commands."""

import pytest
from unittest.mock import patch, MagicMock

from agentic_cli import tracker
from agentic_cli.mcp_tool_client import MCPToolError, parse_space_key

MCP_PATCH = "agentic_cli.mcp_tool_client"


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


# ---------------------------------------------------------------------------
# parse_space_key tests
# ---------------------------------------------------------------------------

class TestParseSpaceKey:
    def test_plain_key(self):
        assert parse_space_key("MTT") == "MTT"

    def test_display_url(self):
        assert parse_space_key("https://confluence.example.com/display/MTT") == "MTT"

    def test_display_url_with_subpath(self):
        assert parse_space_key("https://confluence.example.com/display/MTT/Some+Page") == "MTT"

    def test_spaces_url(self):
        assert parse_space_key("https://confluence.example.com/spaces/DEV/overview") == "DEV"

    def test_empty_string(self):
        assert parse_space_key("") == ""

    def test_no_known_segment(self):
        assert parse_space_key("https://example.com/foo/bar") == "https://example.com/foo/bar"


# ---------------------------------------------------------------------------
# Interactive doc picker tests
# ---------------------------------------------------------------------------

from agentic_cli.commands.domain import _interactive_doc_picker

MOCK_PAGES = [
    {"id": "101", "title": "Architecture", "version": 3},
    {"id": "102", "title": "Runbook", "version": 1},
    {"id": "103", "title": "API Guide", "version": 5},
]


class TestDocPicker:
    def test_select_single(self):
        with patch("builtins.input", return_value="2"):
            result = _interactive_doc_picker(MOCK_PAGES, set())
        assert len(result) == 1
        assert result[0]["id"] == "102"

    def test_select_all(self):
        with patch("builtins.input", return_value="all"):
            result = _interactive_doc_picker(MOCK_PAGES, set())
        assert len(result) == 3

    def test_empty_cancels(self):
        with patch("builtins.input", return_value=""):
            result = _interactive_doc_picker(MOCK_PAGES, set())
        assert result == []

    def test_skips_already_tracked(self):
        with patch("builtins.input", return_value="all"):
            result = _interactive_doc_picker(MOCK_PAGES, {"102"})
        assert len(result) == 2
        ids = [p["id"] for p in result]
        assert "102" not in ids

    def test_range_selection(self):
        with patch("builtins.input", return_value="1-2"):
            result = _interactive_doc_picker(MOCK_PAGES, set())
        assert len(result) == 2


# ---------------------------------------------------------------------------
# CLI tests (mocked Confluence API)
# ---------------------------------------------------------------------------

from typer.testing import CliRunner
from agentic_cli.commands.domain import domain_app

runner = CliRunner()

MOCK_CONFLUENCE_PAGES = [
    {"id": "101", "title": "Architecture Overview", "space_key": "MTT", "version": 3,
     "last_updated": "2024-01-01", "last_updated_by": "Alice"},
    {"id": "102", "title": "Runbook", "space_key": "MTT", "version": 1,
     "last_updated": "2024-02-01", "last_updated_by": "Bob"},
    {"id": "103", "title": "API Reference", "space_key": "MTT", "version": 5,
     "last_updated": "2024-03-01", "last_updated_by": "Charlie"},
]


def _setup_domain_with_confluence():
    """Helper: create product + domain with Confluence space."""
    tracker.register_product(name="CWOW")
    tracker.register_domain(
        name="cwow-facility",
        product="CWOW",
        domain="Facility",
        confluence_space="MTT",
    )


class TestAddDocsCLI:
    def test_domain_not_found(self):
        result = runner.invoke(domain_app, ["add-docs", "nope"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_no_confluence_space(self):
        tracker.register_product(name="CWOW")
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = runner.invoke(domain_app, ["add-docs", "cwow-facility"])
        assert result.exit_code == 1
        assert "no Confluence space" in result.output

    def test_mcp_connection_error(self):
        _setup_domain_with_confluence()
        with patch(f"{MCP_PATCH}.confluence_get_space_pages", side_effect=MCPToolError("Cannot connect", is_connection_error=True)):
            result = runner.invoke(domain_app, ["add-docs", "cwow-facility"])
        assert result.exit_code == 1
        assert "Cannot connect" in result.output

    def test_auto_add_all(self):
        _setup_domain_with_confluence()

        with patch(f"{MCP_PATCH}.confluence_get_space_pages", return_value=MOCK_CONFLUENCE_PAGES):
            result = runner.invoke(domain_app, ["add-docs", "cwow-facility", "--all"])

        assert result.exit_code == 0
        assert "Tracked" in result.output
        assert "3" in result.output

        docs = tracker.get_domain_docs("cwow-facility")
        assert len(docs) == 3
        titles = {d["title"] for d in docs}
        assert "Architecture Overview" in titles

    def test_filter_docs(self):
        _setup_domain_with_confluence()

        with patch(f"{MCP_PATCH}.confluence_get_space_pages", return_value=MOCK_CONFLUENCE_PAGES):
            result = runner.invoke(domain_app, [
                "add-docs", "cwow-facility", "--filter", "runbook", "--all",
            ])

        assert result.exit_code == 0
        docs = tracker.get_domain_docs("cwow-facility")
        assert len(docs) == 1
        assert docs[0]["title"] == "Runbook"

    def test_empty_space(self):
        _setup_domain_with_confluence()

        with patch(f"{MCP_PATCH}.confluence_get_space_pages", return_value=[]):
            result = runner.invoke(domain_app, ["add-docs", "cwow-facility", "--all"])

        assert result.exit_code == 0
        assert "No pages found" in result.output

    def test_skips_already_tracked(self):
        _setup_domain_with_confluence()
        # Pre-track one doc
        tracker.add_domain_doc("cwow-facility", source_page_id="101", title="Pre-existing")

        with patch(f"{MCP_PATCH}.confluence_get_space_pages", return_value=MOCK_CONFLUENCE_PAGES):
            result = runner.invoke(domain_app, ["add-docs", "cwow-facility", "--all"])

        assert result.exit_code == 0
        assert "2" in result.output  # only 2 new
        docs = tracker.get_domain_docs("cwow-facility")
        assert len(docs) == 3


# ---------------------------------------------------------------------------
# dva domain docs CLI tests
# ---------------------------------------------------------------------------

class TestDocsCLI:
    def test_domain_not_found(self):
        result = runner.invoke(domain_app, ["docs", "nope"])
        assert result.exit_code == 1

    def test_no_docs(self):
        _setup_domain_with_confluence()
        result = runner.invoke(domain_app, ["docs", "cwow-facility"])
        assert result.exit_code == 0
        assert "No docs tracked" in result.output

    def test_list_docs(self):
        _setup_domain_with_confluence()
        tracker.add_domain_doc("cwow-facility", "101", source_space_key="MTT", title="Arch Doc", source_version=3)
        tracker.add_domain_doc("cwow-facility", "102", source_space_key="MTT", title="Runbook", source_version=1)
        result = runner.invoke(domain_app, ["docs", "cwow-facility"])
        assert result.exit_code == 0
        assert "Arch Doc" in result.output
        assert "Runbook" in result.output
        assert "MTT" in result.output


# ---------------------------------------------------------------------------
# dva domain sync-docs CLI tests
# ---------------------------------------------------------------------------

class TestSyncDocsCLI:
    def test_domain_not_found(self):
        result = runner.invoke(domain_app, ["sync-docs", "nope"])
        assert result.exit_code == 1

    def test_no_docs_to_sync(self):
        _setup_domain_with_confluence()
        result = runner.invoke(domain_app, ["sync-docs", "cwow-facility"])
        assert result.exit_code == 1
        assert "No docs tracked" in result.output

    def test_dry_run(self):
        _setup_domain_with_confluence()
        tracker.add_domain_doc("cwow-facility", "101", source_space_key="MTT", title="Arch")
        tracker.add_domain_doc("cwow-facility", "102", source_space_key="MTT", title="Run")

        result = runner.invoke(domain_app, ["sync-docs", "cwow-facility", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "create" in result.output.lower()
        assert "2 docs would be synced" in result.output

    def test_sync_creates_space_and_pages(self):
        _setup_domain_with_confluence()
        tracker.add_domain_doc("cwow-facility", "101", source_space_key="MTT", title="Arch Doc")

        # get_space raises 404 → triggers create_space
        def mock_get_space(key):
            raise MCPToolError("404 not found")

        mock_source_page = {
            "id": "101", "title": "Arch Doc", "space_key": "MTT",
            "version": 3, "body_html": "<p>Architecture content</p>",
        }
        mock_created_page = {
            "id": "55555", "title": "Arch Doc", "space_key": "DVACWOWFACILITY",
            "version": 1,
        }

        with patch(f"{MCP_PATCH}.confluence_get_space", side_effect=mock_get_space), \
             patch(f"{MCP_PATCH}.confluence_create_space", return_value={"key": "DVACWOWFACILITY", "name": "DVA Managed"}), \
             patch(f"{MCP_PATCH}.confluence_get_page", return_value=mock_source_page), \
             patch(f"{MCP_PATCH}.confluence_create_page", return_value=mock_created_page):
            result = runner.invoke(domain_app, ["sync-docs", "cwow-facility"])

        assert result.exit_code == 0
        assert "Created managed space" in result.output
        assert "Created: Arch Doc" in result.output
        assert "Synced" in result.output

        # Verify managed page ID recorded
        docs = tracker.get_domain_docs("cwow-facility")
        assert len(docs) == 1
        assert docs[0]["managed_page_id"] == "55555"

    def test_mcp_connection_error(self):
        _setup_domain_with_confluence()
        tracker.add_domain_doc("cwow-facility", "101", title="x")

        with patch(f"{MCP_PATCH}.confluence_get_space", side_effect=MCPToolError("Cannot connect", is_connection_error=True)):
            result = runner.invoke(domain_app, ["sync-docs", "cwow-facility"])

        assert result.exit_code == 1
        assert "Cannot connect" in result.output
