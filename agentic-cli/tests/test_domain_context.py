"""Tests for kg/domain_context.py — domain KG context query, build, scaffold."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from agentic_cli.kg.domain_context import (
    build_domain_context_document,
    build_domain_metadata,
    build_domain_skill_md,
    query_domain_kg,
    scaffold_domain_context_repo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_domain_data() -> dict:
    return {
        "name": "cwow-facility",
        "product": "CWOW",
        "domain": "Facility",
        "description": "Manages facility lifecycle and attributes",
        "jira_project": "CWOW",
        "bitbucket_project": "CGF",
        "confluence_space": "MTT",
        "tags": ["healthcare", "gcp"],
    }


@pytest.fixture
def sample_repos() -> list[dict]:
    return [
        {"repo_slug": "facility-query", "onboarded": True, "repo_type": "query"},
        {"repo_slug": "facility-command", "onboarded": False, "repo_type": "command"},
        {"repo_slug": "facility-events", "onboarded": False, "repo_type": "events"},
    ]


@pytest.fixture
def sample_kg_context() -> dict:
    return {
        "business_context": "Facility domain manages physical locations.",
        "slas": "P99 latency < 200ms, 99.9% uptime.",
        "integrations": "REST APIs, Kafka events, Spanner DB.",
        "security": "HIPAA compliant, encrypted at rest.",
        "performance": "10k concurrent users, < 100ms avg.",
        "architecture": "CQRS with event sourcing on GCP.",
    }


@pytest.fixture
def empty_kg_context() -> dict:
    return {
        "business_context": "",
        "slas": "",
        "integrations": "",
        "security": "",
        "performance": "",
        "architecture": "",
    }


# ---------------------------------------------------------------------------
# query_domain_kg
# ---------------------------------------------------------------------------

class TestQueryDomainKG:
    def test_returns_all_aspects(self):
        mock_client = MagicMock()
        mock_client.health_check.return_value = {"status": "ok"}
        mock_client.query.return_value = {"response": "some context"}
        mock_client.close.return_value = None

        with patch(
            "agentic_cli.kg.lightrag_client.LightRAGClient",
            return_value=mock_client,
        ):
            result = query_domain_kg("cwow-facility")

        assert len(result) == 6
        assert all(k in result for k in [
            "business_context", "slas", "integrations",
            "security", "performance", "architecture",
        ])
        assert all(v == "some context" for v in result.values())

    def test_returns_subset_of_aspects(self):
        mock_client = MagicMock()
        mock_client.health_check.return_value = {"status": "ok"}
        mock_client.query.return_value = {"response": "data"}
        mock_client.close.return_value = None

        with patch(
            "agentic_cli.kg.lightrag_client.LightRAGClient",
            return_value=mock_client,
        ):
            result = query_domain_kg("cwow-facility", aspects=["slas", "security"])

        assert len(result) == 2
        assert "slas" in result
        assert "security" in result

    def test_handles_lightrag_connection_failure(self):
        with patch(
            "agentic_cli.kg.lightrag_client.LightRAGClient",
            side_effect=ConnectionError("refused"),
        ):
            result = query_domain_kg("cwow-facility")

        assert len(result) == 6
        assert all(v == "" for v in result.values())

    def test_handles_import_error(self):
        with patch(
            "agentic_cli.kg.domain_context._query_lightrag",
            return_value=None,
        ):
            result = query_domain_kg("cwow-facility")

        assert len(result) == 6
        assert all(v == "" or v is None for v in result.values())


# ---------------------------------------------------------------------------
# build_domain_context_document
# ---------------------------------------------------------------------------

class TestBuildDomainContextDocument:
    def test_contains_domain_header(self, sample_domain_data, sample_kg_context, sample_repos):
        doc = build_domain_context_document(
            "cwow-facility", sample_domain_data, sample_kg_context, sample_repos,
        )
        assert "# Domain Context: Facility" in doc
        assert "cwow-facility" in doc
        assert "CWOW" in doc

    def test_contains_repos_table(self, sample_domain_data, sample_kg_context, sample_repos):
        doc = build_domain_context_document(
            "cwow-facility", sample_domain_data, sample_kg_context, sample_repos,
        )
        assert "## Repositories (3)" in doc
        assert "`facility-query`" in doc
        assert "`facility-command`" in doc

    def test_contains_kg_sections(self, sample_domain_data, sample_kg_context):
        doc = build_domain_context_document(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert "## Business Context" in doc
        assert "## SLA Requirements" in doc
        assert "## Integration Specifications" in doc
        assert "## Security & Compliance" in doc
        assert "## Performance Requirements" in doc
        assert "## Architecture Patterns" in doc

    def test_contains_kg_content(self, sample_domain_data, sample_kg_context):
        doc = build_domain_context_document(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert "P99 latency" in doc
        assert "HIPAA compliant" in doc
        assert "CQRS" in doc

    def test_empty_kg_shows_placeholder(self, sample_domain_data, empty_kg_context):
        doc = build_domain_context_document(
            "cwow-facility", sample_domain_data, empty_kg_context,
        )
        assert "No business context found in Knowledge Graph" in doc

    def test_minimal_inputs(self):
        doc = build_domain_context_document("test-domain")
        assert "# Domain Context: test-domain" in doc

    def test_contains_tags(self, sample_domain_data, sample_kg_context):
        doc = build_domain_context_document(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert "healthcare" in doc
        assert "gcp" in doc


# ---------------------------------------------------------------------------
# build_domain_metadata
# ---------------------------------------------------------------------------

class TestBuildDomainMetadata:
    def test_basic_structure(self, sample_domain_data, sample_repos):
        meta = build_domain_metadata(
            "cwow-facility", sample_domain_data, sample_repos,
            domain_context_repo="https://github.com/company/facility-domain-context.git",
        )
        assert meta["domain"] == "cwow-facility"
        assert meta["product"] == "CWOW"
        assert meta["domain_label"] == "Facility"
        assert meta["domain_context_repo"] == "https://github.com/company/facility-domain-context.git"
        assert meta["domain_context_path"] == "./.domain-context"
        assert meta["domain_skills_path"] == "./.skills/domain"
        assert len(meta["repos"]) == 3
        assert "facility-query" in meta["repos"]
        assert "generated_at" in meta

    def test_minimal_inputs(self):
        meta = build_domain_metadata("test-domain")
        assert meta["domain"] == "test-domain"
        assert meta["product"] == ""
        assert meta["repos"] == []
        assert meta["domain_context_repo"] == ""

    def test_kg_aspects_listed(self, sample_domain_data):
        meta = build_domain_metadata("cwow-facility", sample_domain_data)
        assert "slas" in meta["kg_aspects"]
        assert "integrations" in meta["kg_aspects"]
        assert len(meta["kg_aspects"]) == 6


# ---------------------------------------------------------------------------
# build_domain_skill_md
# ---------------------------------------------------------------------------

class TestBuildDomainSkillMD:
    def test_contains_frontmatter(self, sample_domain_data, sample_kg_context):
        skill = build_domain_skill_md(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert "---" in skill
        assert "name: cwow-facility-domain-context" in skill
        assert "domain: cwow-facility" in skill

    def test_contains_mcp_instructions(self, sample_domain_data, sample_kg_context):
        skill = build_domain_skill_md(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert "query_domain_context" in skill
        assert "get_domain_slas" in skill
        assert "get_domain_integrations" in skill
        assert "get_domain_security_policies" in skill
        assert "search_business_context" in skill

    def test_contains_embedded_kg_content(self, sample_domain_data, sample_kg_context):
        skill = build_domain_skill_md(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert "### Business Requirements" in skill
        assert "### SLA Requirements" in skill
        assert "P99 latency" in skill
        assert "HIPAA compliant" in skill

    def test_empty_kg_shows_fallback(self, sample_domain_data, empty_kg_context):
        skill = build_domain_skill_md(
            "cwow-facility", sample_domain_data, empty_kg_context,
        )
        assert "No business context found in KG" in skill

    def test_contains_submodule_reference(self, sample_domain_data, sample_kg_context):
        skill = build_domain_skill_md(
            "cwow-facility", sample_domain_data, sample_kg_context,
        )
        assert ".domain-context" in skill
        assert "git submodule update --remote" in skill

    def test_repo_type_in_frontmatter(self, sample_domain_data, sample_kg_context):
        skill = build_domain_skill_md(
            "cwow-facility", sample_domain_data, sample_kg_context,
            repo_type="query",
        )
        assert "repo_type: query" in skill

    def test_minimal_inputs(self):
        skill = build_domain_skill_md("test-domain")
        assert "name: test-domain-domain-context" in skill
        assert "query_domain_context" in skill


# ---------------------------------------------------------------------------
# scaffold_domain_context_repo
# ---------------------------------------------------------------------------

class TestScaffoldDomainContextRepo:
    def test_creates_directory_structure(self, tmp_path, sample_domain_data, sample_kg_context, sample_repos):
        out = tmp_path / "facility-domain-context"
        created = scaffold_domain_context_repo(
            out, "cwow-facility", sample_domain_data, sample_kg_context, sample_repos,
        )

        assert (out / ".domain" / "kg-context.md").exists()
        assert (out / ".domain" / "domain-metadata.json").exists()
        assert (out / ".domain" / "architecture.md").exists()
        assert (out / ".skills" / "shared" / "cwow-facility-domain-skill" / "SKILL.md").exists()
        assert (out / "README.md").exists()
        assert len(created) == 5

    def test_kg_context_content(self, tmp_path, sample_domain_data, sample_kg_context):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, sample_kg_context)

        content = (out / ".domain" / "kg-context.md").read_text()
        assert "Facility" in content
        assert "P99 latency" in content

    def test_metadata_json_valid(self, tmp_path, sample_domain_data, sample_repos):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, repos=sample_repos)

        meta = json.loads((out / ".domain" / "domain-metadata.json").read_text())
        assert meta["domain"] == "cwow-facility"
        assert len(meta["repos"]) == 3

    def test_readme_lists_repos(self, tmp_path, sample_domain_data, sample_repos):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, repos=sample_repos)

        readme = (out / "README.md").read_text()
        assert "facility-query" in readme
        assert "facility-command" in readme

    def test_architecture_md_with_kg(self, tmp_path, sample_domain_data, sample_kg_context):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, sample_kg_context)

        arch = (out / ".domain" / "architecture.md").read_text()
        assert "CQRS" in arch

    def test_architecture_md_without_kg(self, tmp_path, sample_domain_data, empty_kg_context):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, empty_kg_context)

        arch = (out / ".domain" / "architecture.md").read_text()
        assert "populated from the Knowledge Graph" in arch

    def test_shared_skill_md(self, tmp_path, sample_domain_data, sample_kg_context):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, sample_kg_context)

        skill = (out / ".skills" / "shared" / "cwow-facility-domain-skill" / "SKILL.md").read_text()
        assert "query_domain_context" in skill
        assert "cwow-facility" in skill

    def test_idempotent_overwrite(self, tmp_path, sample_domain_data, sample_kg_context):
        out = tmp_path / "test-ctx"
        scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, sample_kg_context)
        # Run again — should overwrite without error
        created2 = scaffold_domain_context_repo(out, "cwow-facility", sample_domain_data, sample_kg_context)
        assert len(created2) == 5

    def test_minimal_inputs(self, tmp_path):
        out = tmp_path / "minimal"
        created = scaffold_domain_context_repo(out, "test-domain")
        assert (out / "README.md").exists()
        assert (out / ".domain" / "kg-context.md").exists()
        assert len(created) == 5
