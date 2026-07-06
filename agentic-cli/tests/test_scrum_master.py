"""Tests for Phase 5: Scrum Master agent template and project creation."""

import json
import pytest
from pathlib import Path

from typer.testing import CliRunner

from agentic_cli import tracker
from agentic_cli.main import app
from agentic_cli.templates import (
    Framework,
    UseCase,
    Tool,
    TemplateConfig,
    TemplateGenerator,
    USE_CASE_TOOLS,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_dir = tmp_path / ".keel-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    tracker._ensure_db()
    yield db_dir


@pytest.fixture
def sample_domain():
    tracker.register_product(name="CWOW", description="CWOW Platform")
    tracker.register_domain(
        name="cwow-facility",
        product="CWOW",
        domain="Facility",
        jira_project="CWOW",
        bitbucket_project="CGF",
        confluence_space="MTT",
        jira_dashboard="https://jira.example.com/dash/81405",
    )
    tracker.link_repo_to_domain(
        "cwow-facility", "cwow-facility-service", "cwow-facility-service",
        "https://bitbucket.example.com/scm/cgf/cwow-facility-service.git",
    )
    return tracker.get_domain("cwow-facility")


# ---------------------------------------------------------------------------
# Enum / config tests
# ---------------------------------------------------------------------------

class TestScrumMasterEnum:
    def test_use_case_exists(self):
        assert UseCase.SCRUM_MASTER == "scrum-master"

    def test_display_name(self):
        assert "Scrum Master" in UseCase.SCRUM_MASTER.display_name

    def test_description(self):
        assert "Jira" in UseCase.SCRUM_MASTER.description

    def test_tool_confluence_mcp(self):
        assert Tool.CONFLUENCE_MCP == "confluence_mcp"

    def test_use_case_tools(self):
        tools = USE_CASE_TOOLS[UseCase.SCRUM_MASTER]
        assert Tool.JIRA_MCP in tools
        assert Tool.CONFLUENCE_MCP in tools
        assert Tool.BITBUCKET_MCP in tools
        assert Tool.MEMORY in tools


class TestScrumMasterConfig:
    def test_auto_populate_tools(self):
        config = TemplateConfig(name="sm", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        assert Tool.JIRA_MCP in config.tools
        assert Tool.CONFLUENCE_MCP in config.tools

    def test_dependencies_include_mcp(self):
        config = TemplateConfig(name="sm", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        deps = config.dependencies
        dep_names = [d.split(">=")[0] for d in deps]
        assert "mcp" in dep_names
        assert "google-generativeai" in dep_names


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------

class TestScrumMasterGenerator:
    def test_generates_scrum_master_files(self, tmp_path):
        config = TemplateConfig(name="sm-test", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        gen = TemplateGenerator(config)
        target = tmp_path / "sm-test"
        gen.generate(target)

        src = target / "src"
        assert (src / "mcp_clients.py").exists()
        assert (src / "sprint_manager.py").exists()
        assert (src / "standup_generator.py").exists()
        assert (src / "domain_loader.py").exists()

    def test_mcp_clients_content(self, tmp_path):
        config = TemplateConfig(name="sm-test", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        gen = TemplateGenerator(config)
        target = tmp_path / "sm-test"
        gen.generate(target)

        content = (target / "src" / "mcp_clients.py").read_text()
        assert "class JiraMCP" in content
        assert "class ConfluenceMCP" in content
        assert "class BitbucketMCP" in content
        assert "search_issues" in content

    def test_sprint_manager_content(self, tmp_path):
        config = TemplateConfig(name="sm-test", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        gen = TemplateGenerator(config)
        target = tmp_path / "sm-test"
        gen.generate(target)

        content = (target / "src" / "sprint_manager.py").read_text()
        assert "class SprintManager" in content
        assert "get_sprint_summary" in content
        assert "get_blockers" in content
        assert "get_stale_tickets" in content

    def test_standup_generator_content(self, tmp_path):
        config = TemplateConfig(name="sm-test", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        gen = TemplateGenerator(config)
        target = tmp_path / "sm-test"
        gen.generate(target)

        content = (target / "src" / "standup_generator.py").read_text()
        assert "class StandupGenerator" in content
        assert "daily_standup" in content
        assert "sprint_review" in content

    def test_domain_loader_content(self, tmp_path):
        config = TemplateConfig(name="sm-test", framework=Framework.ADK, use_case=UseCase.SCRUM_MASTER)
        gen = TemplateGenerator(config)
        target = tmp_path / "sm-test"
        gen.generate(target)

        content = (target / "src" / "domain_loader.py").read_text()
        assert "load_domain_context" in content
        assert "load_persona_skill" in content
        assert ".domain-context.json" in content


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestScrumMasterCLI:
    def test_create_scrum_master_project(self, tmp_path):
        result = runner.invoke(app, [
            "project", "create", "my-sm",
            "--use-case", "scrum-master",
            "--path", str(tmp_path),
            "--force",
        ])
        assert result.exit_code == 0
        proj = tmp_path / "my-sm"
        assert (proj / "src" / "mcp_clients.py").exists()
        assert (proj / "src" / "sprint_manager.py").exists()

    def test_create_scrum_master_with_domain(self, sample_domain, tmp_path):
        result = runner.invoke(app, [
            "project", "create", "sm-facility",
            "--use-case", "scrum-master",
            "--domain", "cwow-facility",
            "--path", str(tmp_path),
            "--force",
        ])
        assert result.exit_code == 0
        proj = tmp_path / "sm-facility"

        # SM agent files
        assert (proj / "src" / "sprint_manager.py").exists()

        # Domain auto-wired
        assert (proj / ".domain-context.json").exists()
        ctx = json.loads((proj / ".domain-context.json").read_text())
        assert ctx["domain"] == "cwow-facility"
        assert ctx["jira_project"] == "CWOW"

        # Persona skills
        assert (proj / ".skills" / "domain" / "SM.md").exists()
        assert (proj / ".skills" / "domain" / "DOMAIN.md").exists()

    def test_list_templates_includes_scrum_master(self):
        result = runner.invoke(app, ["project", "list-templates"])
        assert result.exit_code == 0
        assert "scrum-master" in result.output
