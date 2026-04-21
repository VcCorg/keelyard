"""Tests for Phase 3.5: dva domain gen-skills — role-based persona skill generation."""

import pytest
from pathlib import Path

from dva_agentic_cli import tracker
from dva_agentic_cli.skill_generator import (
    ROLES,
    ROLE_LABELS,
    FILE_NAMES,
    gather_domain_context,
    generate_skill_files,
    generate_domain_md,
    generate_dev_md,
    generate_qa_md,
    generate_sm_md,
    generate_ba_md,
)


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
    """Register a sample domain and return its data."""
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
    tracker.link_repo_to_domain(
        "cwow-facility", "cwow-facility-query", "cwow-facility-query",
        "https://bb.example.com/scm/cgf/cwow-facility-query.git",
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
# gather_domain_context tests
# ---------------------------------------------------------------------------

class TestGatherContext:
    def test_returns_all_fields(self, sample_domain):
        repos = tracker.get_domain_repos("cwow-facility")
        docs = tracker.get_domain_docs("cwow-facility")
        ctx = gather_domain_context(sample_domain, repos, docs)

        assert ctx["name"] == "cwow-facility"
        assert ctx["product"] == "CWOW"
        assert ctx["domain_label"] == "Facility"
        assert ctx["jira_project"] == "CWOW"
        assert ctx["bitbucket_project"] == "CGF"
        assert ctx["confluence_space"] == "MTT"
        assert ctx["jira_dashboard"] == "https://jira.example.com/dash/81405"
        assert ctx["confluence_url"] == "https://confluence.example.com/display/MTT"
        assert len(ctx["repos"]) == 2
        assert len(ctx["docs"]) == 1
        assert "generated_at" in ctx

    def test_handles_empty_repos_docs(self):
        tracker.register_product(name="TEST", description="Test")
        tracker.register_domain(name="test-empty", product="TEST", domain="Empty")
        d = tracker.get_domain("test-empty")
        ctx = gather_domain_context(d, [], [])
        assert ctx["repos"] == []
        assert ctx["docs"] == []


# ---------------------------------------------------------------------------
# Individual generator tests
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx(sample_domain):
    """Full context dict for generators."""
    repos = tracker.get_domain_repos("cwow-facility")
    docs = tracker.get_domain_docs("cwow-facility")
    return gather_domain_context(sample_domain, repos, docs)


class TestGenerateDomainMd:
    def test_contains_frontmatter(self, ctx):
        md = generate_domain_md(ctx)
        assert "name: cwow-facility-domain" in md
        assert "role: domain" in md

    def test_contains_links(self, ctx):
        md = generate_domain_md(ctx)
        assert "**Jira Project:** CWOW" in md
        assert "**Jira Dashboard:** https://jira.example.com/dash/81405" in md
        assert "**Confluence Space:** MTT" in md

    def test_contains_repos(self, ctx):
        md = generate_domain_md(ctx)
        assert "cwow-facility-service" in md
        assert "cwow-facility-query" in md

    def test_contains_docs(self, ctx):
        md = generate_domain_md(ctx)
        assert "Architecture Overview" in md


class TestGenerateDevMd:
    def test_contains_frontmatter(self, ctx):
        md = generate_dev_md(ctx)
        assert "role: dev" in md

    def test_contains_repo_list(self, ctx):
        md = generate_dev_md(ctx)
        assert "### `cwow-facility-service`" in md

    def test_contains_pr_conventions(self, ctx):
        md = generate_dev_md(ctx)
        assert "CWOW-<ticket-number>" in md or "CWOW-<number>" in md


class TestGenerateQaMd:
    def test_contains_frontmatter(self, ctx):
        md = generate_qa_md(ctx)
        assert "role: qa" in md

    def test_contains_test_strategy(self, ctx):
        md = generate_qa_md(ctx)
        assert "Unit Tests" in md
        assert "Integration Tests" in md

    def test_contains_repo_table(self, ctx):
        md = generate_qa_md(ctx)
        assert "cwow-facility-service" in md


class TestGenerateSmMd:
    def test_contains_jira_config(self, ctx):
        md = generate_sm_md(ctx)
        assert "**Project Key:** CWOW" in md
        assert "**Dashboard:** https://jira.example.com/dash/81405" in md

    def test_contains_sprint_workflow(self, ctx):
        md = generate_sm_md(ctx)
        assert "Sprint Planning" in md
        assert "Daily Standup" in md

    def test_contains_story_points(self, ctx):
        md = generate_sm_md(ctx)
        assert "Story Points" in md
        assert "| 5 |" in md

    def test_contains_ticket_pattern(self, ctx):
        md = generate_sm_md(ctx)
        assert "`CWOW-<number>`" in md


class TestGenerateBaMd:
    def test_contains_frontmatter(self, ctx):
        md = generate_ba_md(ctx)
        assert "role: ba" in md

    def test_contains_acceptance_criteria(self, ctx):
        md = generate_ba_md(ctx)
        assert "Acceptance Criteria" in md
        assert "Given" in md
        assert "When" in md
        assert "Then" in md

    def test_contains_glossary(self, ctx):
        md = generate_ba_md(ctx)
        assert "Domain Glossary" in md
        assert "Facility" in md

    def test_contains_docs(self, ctx):
        md = generate_ba_md(ctx)
        assert "Architecture Overview" in md


# ---------------------------------------------------------------------------
# generate_skill_files tests
# ---------------------------------------------------------------------------

class TestGenerateSkillFiles:
    def test_generates_all_roles(self, ctx, tmp_path):
        out = tmp_path / "skills"
        written = generate_skill_files(ctx, out)
        assert len(written) == 5
        for role in ROLES:
            assert (out / FILE_NAMES[role]).exists()

    def test_generates_single_role(self, ctx, tmp_path):
        out = tmp_path / "skills"
        written = generate_skill_files(ctx, out, roles=["dev"])
        assert len(written) == 1
        assert (out / "DEV.md").exists()
        assert not (out / "SM.md").exists()

    def test_creates_output_dir(self, ctx, tmp_path):
        out = tmp_path / "nested" / "deep" / "skills"
        generate_skill_files(ctx, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------

from typer.testing import CliRunner
from dva_agentic_cli.main import app

runner = CliRunner()


class TestGenSkillsCLI:
    def test_domain_not_found(self):
        result = runner.invoke(app, ["domain", "gen-skills", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_invalid_role(self, sample_domain):
        result = runner.invoke(app, ["domain", "gen-skills", "cwow-facility", "--role", "ceo"])
        assert result.exit_code != 0
        assert "Unknown role" in result.output

    def test_generate_all(self, sample_domain, tmp_path):
        out = str(tmp_path / "out")
        result = runner.invoke(app, ["domain", "gen-skills", "cwow-facility", "--output", out])
        assert result.exit_code == 0
        assert "Domain Overview" in result.output
        assert "Developer" in result.output
        assert "Quality Assurance" in result.output
        assert "Scrum Master" in result.output
        assert "Business Analyst" in result.output
        assert (Path(out) / "DOMAIN.md").exists()
        assert (Path(out) / "DEV.md").exists()
        assert (Path(out) / "QA.md").exists()
        assert (Path(out) / "SM.md").exists()
        assert (Path(out) / "BA.md").exists()

    def test_generate_single_role(self, sample_domain, tmp_path):
        out = str(tmp_path / "out")
        result = runner.invoke(app, ["domain", "gen-skills", "cwow-facility", "--role", "sm", "--output", out])
        assert result.exit_code == 0
        assert "Scrum Master" in result.output
        assert (Path(out) / "SM.md").exists()
        assert not (Path(out) / "DEV.md").exists()
