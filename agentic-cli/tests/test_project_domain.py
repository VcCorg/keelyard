"""Tests for Phase 4: dva project create --domain auto-wiring."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from agentic_cli import tracker
from agentic_cli.main import app
from agentic_cli.commands.project import _wire_domain_context
from agentic_cli.skill_generator import gather_domain_context, FILE_NAMES, ROLES

runner = CliRunner()


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


@pytest.fixture
def sample_domain():
    """Register a sample domain with repos and docs."""
    tracker.register_product(name="CWOW", description="CWOW Platform")
    tracker.register_domain(
        name="cwow-facility",
        product="CWOW",
        domain="Facility",
        description="Facility management domain",
        jira_project="CWOW",
        bitbucket_project="CGF",
        confluence_space="MTT",
        jira_dashboard="https://jira.example.com/dash/81405",
        confluence_url="https://confluence.example.com/display/MTT",
    )
    tracker.link_repo_to_domain(
        "cwow-facility", "cwow-facility-service", "cwow-facility-service",
        "https://bb.example.com/scm/cgf/cwow-facility-service.git",
    )
    tracker.add_domain_doc(
        "cwow-facility",
        source_page_id="12345",
        source_space_key="MTT",
        title="Architecture Overview",
        source_version=3,
    )
    return tracker.get_domain("cwow-facility")


# ---------------------------------------------------------------------------
# _wire_domain_context unit tests
# ---------------------------------------------------------------------------

class TestWireDomainContext:
    def test_creates_skills_dir(self, sample_domain, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        _wire_domain_context("cwow-facility", sample_domain, target)

        skills_dir = target / ".skills" / "domain"
        assert skills_dir.exists()
        for role in ROLES:
            assert (skills_dir / FILE_NAMES[role]).exists()

    def test_creates_domain_context_json(self, sample_domain, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        _wire_domain_context("cwow-facility", sample_domain, target)

        ctx_file = target / ".domain-context.json"
        assert ctx_file.exists()
        data = json.loads(ctx_file.read_text())
        assert data["domain"] == "cwow-facility"
        assert data["product"] == "CWOW"
        assert data["jira_project"] == "CWOW"
        assert data["bitbucket_project"] == "CGF"
        assert data["confluence_space"] == "MTT"
        assert len(data["repos"]) == 1
        assert data["repos"][0]["slug"] == "cwow-facility-service"
        assert len(data["docs"]) == 1
        assert data["docs"][0]["title"] == "Architecture Overview"

    def test_appends_env_vars(self, sample_domain, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        env_file = target / ".env"
        env_file.write_text("EXISTING_VAR=hello\n")

        _wire_domain_context("cwow-facility", sample_domain, target, env_file)

        content = env_file.read_text()
        assert "EXISTING_VAR=hello" in content
        assert "DOMAIN_NAME=cwow-facility" in content
        assert "JIRA_PROJECT=CWOW" in content
        assert "JIRA_DASHBOARD_URL=https://jira.example.com/dash/81405" in content
        assert "BITBUCKET_PROJECT=CGF" in content
        assert "CONFLUENCE_SPACE=MTT" in content
        assert "MCP_BITBUCKET_URL=http://localhost:8126/sse" in content
        assert "MCP_GATEWAY_URL=http://localhost:9090/sse" in content

    def test_no_env_file(self, sample_domain, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        result = _wire_domain_context("cwow-facility", sample_domain, target, None)
        assert result is True
        assert not (target / ".env").exists()

    def test_returns_true(self, sample_domain, tmp_path):
        target = tmp_path / "project"
        target.mkdir()
        assert _wire_domain_context("cwow-facility", sample_domain, target) is True


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestProjectCreateWithDomain:
    def test_domain_not_found(self, tmp_path):
        result = runner.invoke(app, [
            "project", "create", "test-proj",
            "--path", str(tmp_path),
            "--domain", "nonexistent",
        ])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_create_with_domain(self, sample_domain, tmp_path):
        result = runner.invoke(app, [
            "project", "create", "test-proj",
            "--path", str(tmp_path),
            "--domain", "cwow-facility",
            "--force",
        ])
        assert result.exit_code == 0
        assert "auto-wired" in result.output

        proj_dir = tmp_path / "test-proj"
        assert proj_dir.exists()

        # Skills generated
        skills_dir = proj_dir / ".skills" / "domain"
        assert skills_dir.exists()
        assert (skills_dir / "DOMAIN.md").exists()
        assert (skills_dir / "DEV.md").exists()
        assert (skills_dir / "SM.md").exists()

        # Context JSON
        ctx_file = proj_dir / ".domain-context.json"
        assert ctx_file.exists()
        data = json.loads(ctx_file.read_text())
        assert data["domain"] == "cwow-facility"

    def test_create_without_domain(self, tmp_path):
        result = runner.invoke(app, [
            "project", "create", "plain-proj",
            "--path", str(tmp_path),
            "--force",
        ])
        assert result.exit_code == 0
        proj_dir = tmp_path / "plain-proj"
        assert proj_dir.exists()
        assert not (proj_dir / ".domain-context.json").exists()
        assert not (proj_dir / ".skills" / "domain").exists()
