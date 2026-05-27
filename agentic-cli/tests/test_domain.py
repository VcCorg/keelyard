"""Tests for domain registry — tracker.py domain functions + commands/domain.py CLI."""

import json
import os
import sqlite3
import tempfile
import pytest
from unittest.mock import patch

from agentic_cli import tracker


# ---------------------------------------------------------------------------
# Fixtures — use a temp database to avoid touching the real one
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect tracker.db to a temp directory for each test."""
    db_dir = tmp_path / ".dva-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    # Force fresh schema
    tracker._ensure_db()
    yield db_dir


# ---------------------------------------------------------------------------
# Schema & Migration Tests
# ---------------------------------------------------------------------------

class TestSchemaMigration:
    def test_domains_table_exists(self):
        conn = sqlite3.connect(str(tracker.DB_PATH))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "domains" in table_names
        assert "domain_repos" in table_names
        assert "domain_docs" in table_names

    def test_products_table_exists(self):
        conn = sqlite3.connect(str(tracker.DB_PATH))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "products" in table_names

    def test_schema_version_is_7(self):
        conn = sqlite3.connect(str(tracker.DB_PATH))
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        conn.close()
        assert version == 8


# ---------------------------------------------------------------------------
# Product CRUD Tests
# ---------------------------------------------------------------------------

class TestRegisterProduct:
    def test_create_product(self):
        pid = tracker.register_product(name="CWOW", description="CWOW Platform", tags=["healthcare"])
        assert pid > 0
        p = tracker.get_product("CWOW")
        assert p is not None
        assert p["name"] == "CWOW"
        assert p["description"] == "CWOW Platform"
        assert p["tags"] == ["healthcare"]

    def test_product_name_uppercased(self):
        tracker.register_product(name="cwow")
        p = tracker.get_product("cwow")
        assert p["name"] == "CWOW"

    def test_update_existing_product(self):
        tracker.register_product(name="CWOW")
        tracker.register_product(name="CWOW", description="Updated")
        p = tracker.get_product("CWOW")
        assert p["description"] == "Updated"

    def test_list_products(self):
        tracker.register_product(name="CWOW")
        tracker.register_product(name="IMTO")
        products = tracker.get_products()
        assert len(products) == 2
        names = [p["name"] for p in products]
        assert "CWOW" in names
        assert "IMTO" in names

    def test_remove_product(self):
        tracker.register_product(name="CWOW")
        assert tracker.remove_product("CWOW") is True
        assert tracker.get_product("CWOW") is None

    def test_remove_nonexistent(self):
        assert tracker.remove_product("NOPE") is False

    def test_update_product_fields(self):
        tracker.register_product(name="CWOW")
        result = tracker.update_product("CWOW", description="New desc", tags=["a", "b"])
        assert result is True
        p = tracker.get_product("CWOW")
        assert p["description"] == "New desc"
        assert p["tags"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Domain CRUD Tests
# ---------------------------------------------------------------------------

class TestRegisterDomain:
    def test_create_new_domain(self):
        domain_id = tracker.register_domain(
            name="cwow-facility",
            product="CWOW",
            domain="Facility",
            description="CWOW Facility domain",
            jira_project="CWOW",
            bitbucket_project="CGF",
            confluence_space="MTT",
            tags=["healthcare", "gcp"],
        )
        assert domain_id > 0

        d = tracker.get_domain("cwow-facility")
        assert d is not None
        assert d["product"] == "CWOW"
        assert d["domain"] == "Facility"
        assert d["jira_project"] == "CWOW"
        assert d["bitbucket_project"] == "CGF"
        assert d["confluence_space"] == "MTT"
        assert d["tags"] == ["healthcare", "gcp"]

    def test_update_existing_domain(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.register_domain(
            name="cwow-facility",
            product="CWOW",
            domain="Facility",
            jira_project="CWOW-NEW",
        )
        d = tracker.get_domain("cwow-facility")
        assert d["jira_project"] == "CWOW-NEW"

    def test_create_multiple_domains(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.register_domain(name="cwow-patient", product="CWOW", domain="Patient")
        tracker.register_domain(name="imto-imaging", product="IMTO", domain="Imaging")

        all_domains = tracker.get_domains()
        assert len(all_domains) == 3

    def test_filter_by_product(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.register_domain(name="cwow-patient", product="CWOW", domain="Patient")
        tracker.register_domain(name="imto-imaging", product="IMTO", domain="Imaging")

        cwow = tracker.get_domains(product="CWOW")
        assert len(cwow) == 2
        assert all(d["product"] == "CWOW" for d in cwow)

        imto = tracker.get_domains(product="IMTO")
        assert len(imto) == 1


class TestUpdateDomain:
    def test_update_fields(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = tracker.update_domain(
            "cwow-facility",
            jira_project="CWOW-FAC",
            tags=["gcp", "spanner"],
        )
        assert result is True

        d = tracker.get_domain("cwow-facility")
        assert d["jira_project"] == "CWOW-FAC"
        assert d["tags"] == ["gcp", "spanner"]

    def test_update_nonexistent(self):
        result = tracker.update_domain("nope", jira_project="X")
        assert result is False

    def test_update_no_fields(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = tracker.update_domain("cwow-facility")
        assert result is False


class TestRemoveDomain:
    def test_remove_existing(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        assert tracker.remove_domain("cwow-facility") is True
        assert tracker.get_domain("cwow-facility") is None

    def test_remove_nonexistent(self):
        assert tracker.remove_domain("nope") is False


# ---------------------------------------------------------------------------
# Domain Repos Tests
# ---------------------------------------------------------------------------

class TestDomainRepos:
    def test_link_repo(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = tracker.link_repo_to_domain(
            "cwow-facility", "cwow-facility-service",
            repo_name="CWOW Facility Service",
            clone_url="https://bitbucket.example.com/scm/cgf/cwow-facility-service.git",
        )
        assert result is True

        repos = tracker.get_domain_repos("cwow-facility")
        assert len(repos) == 1
        assert repos[0]["repo_slug"] == "cwow-facility-service"
        assert repos[0]["repo_name"] == "CWOW Facility Service"
        assert repos[0]["onboarded"] == 0

    def test_link_duplicate_repo(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.link_repo_to_domain("cwow-facility", "cwow-facility-service")
        result = tracker.link_repo_to_domain("cwow-facility", "cwow-facility-service")
        assert result is False  # duplicate

    def test_link_repo_to_nonexistent_domain(self):
        result = tracker.link_repo_to_domain("nope", "some-repo")
        assert result is False

    def test_unlink_repo(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.link_repo_to_domain("cwow-facility", "repo-a")
        tracker.link_repo_to_domain("cwow-facility", "repo-b")

        assert tracker.unlink_repo_from_domain("cwow-facility", "repo-a") is True
        repos = tracker.get_domain_repos("cwow-facility")
        assert len(repos) == 1
        assert repos[0]["repo_slug"] == "repo-b"

    def test_mark_onboarded(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.link_repo_to_domain("cwow-facility", "cwow-facility-service")
        tracker.mark_domain_repo_onboarded("cwow-facility", "cwow-facility-service")

        repos = tracker.get_domain_repos("cwow-facility")
        assert repos[0]["onboarded"] == 1
        assert repos[0]["onboarded_at"] is not None

    def test_multiple_repos(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.link_repo_to_domain("cwow-facility", "repo-a")
        tracker.link_repo_to_domain("cwow-facility", "repo-b")
        tracker.link_repo_to_domain("cwow-facility", "repo-c")

        repos = tracker.get_domain_repos("cwow-facility")
        assert len(repos) == 3


# ---------------------------------------------------------------------------
# Domain Docs Tests
# ---------------------------------------------------------------------------

class TestDomainDocs:
    def test_add_doc(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = tracker.add_domain_doc(
            "cwow-facility",
            source_page_id="123456",
            source_space_key="MTT",
            title="Architecture Overview",
            source_version=3,
        )
        assert result is True

        docs = tracker.get_domain_docs("cwow-facility")
        assert len(docs) == 1
        assert docs[0]["title"] == "Architecture Overview"
        assert docs[0]["source_version"] == 3

    def test_update_existing_doc(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.add_domain_doc("cwow-facility", source_page_id="123", title="v1", source_version=1)
        tracker.add_domain_doc("cwow-facility", source_page_id="123", title="v2", source_version=2)

        docs = tracker.get_domain_docs("cwow-facility")
        assert len(docs) == 1
        assert docs[0]["title"] == "v2"
        assert docs[0]["source_version"] == 2

    def test_doc_for_nonexistent_domain(self):
        result = tracker.add_domain_doc("nope", source_page_id="123")
        assert result is False


# ---------------------------------------------------------------------------
# Cascade Delete Tests
# ---------------------------------------------------------------------------

class TestCascadeDelete:
    def test_removing_domain_removes_repos_and_docs(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        tracker.link_repo_to_domain("cwow-facility", "repo-a")
        tracker.link_repo_to_domain("cwow-facility", "repo-b")
        tracker.add_domain_doc("cwow-facility", source_page_id="111", title="Doc A")

        assert len(tracker.get_domain_repos("cwow-facility")) == 2
        assert len(tracker.get_domain_docs("cwow-facility")) == 1

        tracker.remove_domain("cwow-facility")

        assert tracker.get_domain("cwow-facility") is None
        assert len(tracker.get_domain_repos("cwow-facility")) == 0
        assert len(tracker.get_domain_docs("cwow-facility")) == 0


# ---------------------------------------------------------------------------
# Full Context Export
# ---------------------------------------------------------------------------

class TestFullContext:
    def test_includes_domains(self):
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        ctx = tracker.get_full_context()
        assert "domains" in ctx
        assert len(ctx["domains"]) == 1
        assert ctx["domains"][0]["name"] == "cwow-facility"

    def test_includes_products(self):
        tracker.register_product(name="CWOW")
        ctx = tracker.get_full_context()
        assert "products" in ctx
        assert len(ctx["products"]) == 1


# ---------------------------------------------------------------------------
# CLI Command Tests (via typer.testing)
# ---------------------------------------------------------------------------

from typer.testing import CliRunner
from agentic_cli.commands.domain import domain_app
from agentic_cli.commands.product import product_app

runner = CliRunner()


def _create_product(name="CWOW", desc=None):
    """Helper: register a product in the DB so domain create can reference it."""
    tracker.register_product(name=name, description=desc)


# ---------------------------------------------------------------------------
# Product CLI Tests
# ---------------------------------------------------------------------------

class TestProductCLI:
    def test_create_product(self):
        result = runner.invoke(product_app, [
            "create", "CWOW", "--description", "CWOW Platform", "--tags", "healthcare,gcp",
        ])
        assert result.exit_code == 0
        assert "CWOW" in result.output

    def test_list_products(self):
        runner.invoke(product_app, ["create", "CWOW"])
        runner.invoke(product_app, ["create", "IMTO"])
        result = runner.invoke(product_app, ["list"])
        assert result.exit_code == 0
        assert "CWOW" in result.output
        assert "IMTO" in result.output

    def test_show_product(self):
        runner.invoke(product_app, ["create", "CWOW", "--description", "Test"])
        result = runner.invoke(product_app, ["show", "CWOW"])
        assert result.exit_code == 0
        assert "CWOW" in result.output

    def test_show_not_found(self):
        result = runner.invoke(product_app, ["show", "NOPE"])
        assert result.exit_code == 1

    def test_update_product(self):
        runner.invoke(product_app, ["create", "CWOW"])
        result = runner.invoke(product_app, ["update", "CWOW", "--description", "Updated"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_remove_product(self):
        runner.invoke(product_app, ["create", "CWOW"])
        result = runner.invoke(product_app, ["remove", "CWOW", "--yes"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_remove_blocked_by_domains(self):
        runner.invoke(product_app, ["create", "CWOW"])
        _create_product("CWOW")  # ensure in DB
        tracker.register_domain(name="cwow-facility", product="CWOW", domain="Facility")
        result = runner.invoke(product_app, ["remove", "CWOW", "--yes"])
        assert result.exit_code == 1
        assert "domain" in result.output.lower()


# ---------------------------------------------------------------------------
# Domain CLI Tests (now require --product)
# ---------------------------------------------------------------------------

class TestDomainCLI:
    def test_create_command(self):
        _create_product("CWOW")
        result = runner.invoke(domain_app, [
            "create", "Facility",
            "--product", "CWOW",
            "--jira", "CWOW",
            "--bb", "CGF",
            "--confluence", "MTT",
            "--tags", "healthcare,gcp",
        ])
        assert result.exit_code == 0
        assert "cwow-facility" in result.output
        assert "CWOW" in result.output

    def test_create_fails_without_product(self):
        result = runner.invoke(domain_app, ["create", "Facility", "--product", "NOPE"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_list_command(self):
        _create_product("CWOW")
        runner.invoke(domain_app, ["create", "Facility", "--product", "CWOW", "--jira", "CWOW"])
        runner.invoke(domain_app, ["create", "Patient", "--product", "CWOW", "--jira", "CWOW"])

        result = runner.invoke(domain_app, ["list"])
        assert result.exit_code == 0
        assert "cwow-facility" in result.output
        assert "cwow-patient" in result.output

    def test_list_filter_product(self):
        _create_product("CWOW")
        _create_product("IMTO")
        runner.invoke(domain_app, ["create", "Facility", "--product", "CWOW"])
        runner.invoke(domain_app, ["create", "Imaging", "--product", "IMTO"])

        result = runner.invoke(domain_app, ["list", "--product", "CWOW"])
        assert result.exit_code == 0
        assert "cwow-facility" in result.output
        assert "imto-imaging" not in result.output

    def test_show_command(self):
        _create_product("CWOW")
        runner.invoke(domain_app, [
            "create", "Facility", "--product", "CWOW",
            "--jira", "CWOW", "--bb", "CGF",
            "--tags", "healthcare",
        ])

        result = runner.invoke(domain_app, ["show", "cwow-facility"])
        assert result.exit_code == 0
        assert "CWOW" in result.output
        assert "CGF" in result.output

    def test_show_not_found(self):
        result = runner.invoke(domain_app, ["show", "nope"])
        assert result.exit_code == 1

    def test_update_command(self):
        _create_product("CWOW")
        runner.invoke(domain_app, ["create", "Facility", "--product", "CWOW"])
        result = runner.invoke(domain_app, ["update", "cwow-facility", "--jira", "CWOW-FAC"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_link_and_list_repos(self):
        _create_product("CWOW")
        runner.invoke(domain_app, ["create", "Facility", "--product", "CWOW"])
        result = runner.invoke(domain_app, [
            "link-repo", "cwow-facility", "cwow-facility-service",
            "--name", "CWOW Facility Service",
        ])
        assert result.exit_code == 0
        assert "linked" in result.output

        result = runner.invoke(domain_app, ["repos", "cwow-facility"])
        assert result.exit_code == 0
        assert "cwow-facility-service" in result.output

    def test_unlink_repo(self):
        _create_product("CWOW")
        runner.invoke(domain_app, ["create", "Facility", "--product", "CWOW"])
        runner.invoke(domain_app, ["link-repo", "cwow-facility", "repo-a"])
        result = runner.invoke(domain_app, ["unlink-repo", "cwow-facility", "repo-a"])
        assert result.exit_code == 0
        assert "unlinked" in result.output

    def test_remove_command(self):
        _create_product("CWOW")
        runner.invoke(domain_app, ["create", "Facility", "--product", "CWOW"])
        result = runner.invoke(domain_app, ["remove", "cwow-facility", "--yes"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_create_with_description(self):
        _create_product("CWOW")
        result = runner.invoke(domain_app, [
            "create", "Facility", "--product", "CWOW",
            "--description", "CWOW Facility management domain",
        ])
        assert result.exit_code == 0

        result = runner.invoke(domain_app, ["show", "cwow-facility"])
        assert "Facility management" in result.output


# ---------------------------------------------------------------------------
# domain init-context CLI Tests
# ---------------------------------------------------------------------------

class TestInitContextCLI:
    def _setup_domain(self):
        _create_product("CWOW")
        runner.invoke(domain_app, [
            "create", "Facility", "--product", "CWOW",
            "--jira", "CWOW", "--bb", "CGF",
            "--description", "Facility management",
        ])
        runner.invoke(domain_app, ["link-repo", "cwow-facility", "facility-query"])

    def test_init_context_creates_structure(self, tmp_path):
        self._setup_domain()
        out_dir = tmp_path / "ctx-repo"

        with patch(
            "agentic_cli.kg.domain_context.query_domain_kg",
            return_value={
                "business_context": "Facility domain context",
                "slas": "99.9% uptime",
                "integrations": "",
                "security": "",
                "performance": "",
                "architecture": "",
            },
        ):
            result = runner.invoke(domain_app, [
                "init-context", "cwow-facility",
                "--output", str(out_dir),
                "--no-git-init",
            ])

        assert result.exit_code == 0
        assert (out_dir / ".domain" / "kg-context.md").exists()
        assert (out_dir / ".domain" / "domain-metadata.json").exists()
        assert (out_dir / "README.md").exists()
        assert "cwow-facility" in result.output

    def test_init_context_domain_not_found(self, tmp_path):
        result = runner.invoke(domain_app, [
            "init-context", "nonexistent",
            "--output", str(tmp_path / "out"),
            "--no-git-init",
        ])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_init_context_kg_failure_fallback(self, tmp_path):
        self._setup_domain()
        out_dir = tmp_path / "ctx-repo"

        with patch(
            "agentic_cli.kg.domain_context.query_domain_kg",
            side_effect=ConnectionError("LightRAG not running"),
        ):
            result = runner.invoke(domain_app, [
                "init-context", "cwow-facility",
                "--output", str(out_dir),
                "--no-git-init",
            ])

        assert result.exit_code == 0
        assert (out_dir / "README.md").exists()
        content = (out_dir / ".domain" / "kg-context.md").read_text()
        assert "No business context found" in content

    def test_init_context_includes_repos_in_readme(self, tmp_path):
        self._setup_domain()
        out_dir = tmp_path / "ctx-repo"

        with patch(
            "agentic_cli.kg.domain_context.query_domain_kg",
            return_value={k: "" for k in [
                "business_context", "slas", "integrations",
                "security", "performance", "architecture",
            ]},
        ):
            runner.invoke(domain_app, [
                "init-context", "cwow-facility",
                "--output", str(out_dir),
                "--no-git-init",
            ])

        readme = (out_dir / "README.md").read_text()
        assert "facility-query" in readme
