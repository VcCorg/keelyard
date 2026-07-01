"""Tests for Phase 6: DVA Agentic Dashboard API."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from agentic_cli import tracker
from agentic_cli.dashboard.api import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_dir = tmp_path / ".dva-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    tracker._ensure_db()
    yield db_dir


@pytest.fixture
def seed_data():
    """Seed products, domains, repos, docs, and a project."""
    tracker.register_product(name="CWOW", description="CWOW Platform")
    tracker.register_domain(
        name="cwow-facility",
        product="CWOW",
        domain="Facility",
        description="Facility management",
        jira_project="CWOW",
        bitbucket_project="CGF",
        confluence_space="MTT",
        jira_dashboard="https://jira.example.com/dash/81405",
    )
    tracker.link_repo_to_domain(
        "cwow-facility", "cwow-facility-service", "cwow-facility-service",
        "https://bitbucket.example.com/scm/cgf/cwow-facility-service.git",
    )
    tracker.add_domain_doc(
        "cwow-facility", source_page_id="111", source_space_key="MTT", title="Arch Doc",
    )
    tracker.register_project(
        name="sm-agent", path="/tmp/sm-agent", framework="adk", use_case="scrum-master",
        tools=["jira_mcp", "memory"],
    )
    tracker.record_activity(command="domain", subcommand="gen-skills", args={"domain": "cwow-facility"})


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class TestProducts:
    def test_list_products_empty(self):
        resp = client.get("/api/products")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_products(self, seed_data):
        resp = client.get("/api/products")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "CWOW"

    def test_get_product(self, seed_data):
        resp = client.get("/api/products/CWOW")
        assert resp.status_code == 200
        assert resp.json()["name"] == "CWOW"

    def test_get_product_not_found(self):
        resp = client.get("/api/products/NOPE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

class TestDomains:
    def test_list_domains(self, seed_data):
        resp = client.get("/api/domains")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_domains_filter(self, seed_data):
        resp = client.get("/api/domains?product=CWOW")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_domain_detail(self, seed_data):
        resp = client.get("/api/domains/cwow-facility")
        assert resp.status_code == 200
        d = resp.json()
        assert d["name"] == "cwow-facility"
        assert len(d["repos"]) == 1
        assert len(d["docs"]) == 1

    def test_get_domain_not_found(self):
        resp = client.get("/api/domains/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------

class TestRepos:
    def test_list_repos(self, seed_data):
        resp = client.get("/api/repos")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class TestProjects:
    def test_list_projects(self, seed_data):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        proj = [p for p in data if p["name"] == "sm-agent"][0]
        assert proj["use_case"] == "scrum-master"
        assert "validation" in proj
        assert "score" in proj["validation"]

    def test_validation_checks(self, seed_data):
        resp = client.get("/api/projects")
        proj = [p for p in resp.json() if p["name"] == "sm-agent"][0]
        v = proj["validation"]
        # /tmp/sm-agent doesn't exist, so all checks should be False
        assert v["path_exists"] is False
        assert v["score"] == 0


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

class TestActivity:
    def test_list_activity(self, seed_data):
        resp = client.get("/api/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["command"] == "domain"

    def test_list_activity_filter(self, seed_data):
        resp = client.get("/api/activity?command=domain")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_activity_summary(self, seed_data):
        resp = client.get("/api/activity/summary")
        assert resp.status_code == 200
        s = resp.json()
        assert "total_actions" in s


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

class TestCatalogue:
    def test_use_cases(self):
        resp = client.get("/api/catalogue/use-cases")
        assert resp.status_code == 200
        data = resp.json()
        values = [uc["value"] for uc in data]
        assert "scrum-master" in values
        assert "pr-reviewer" in values
        assert "basic" in values

    def test_frameworks(self):
        resp = client.get("/api/catalogue/frameworks")
        assert resp.status_code == 200
        data = resp.json()
        values = [f["value"] for f in data]
        assert "adk" in values

    def test_tools(self):
        resp = client.get("/api/catalogue/tools")
        assert resp.status_code == 200
        data = resp.json()
        values = [t["value"] for t in data]
        assert "jira_mcp" in values
        assert "confluence_mcp" in values


# ---------------------------------------------------------------------------
# MCP Health
# ---------------------------------------------------------------------------

class TestMCPHealth:
    def test_mcp_health(self):
        resp = client.get("/api/mcp/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "bitbucket" in data
        assert "jira" in data
        assert "confluence" in data
        for name, info in data.items():
            assert "url" in info
            assert "status" in info


# ---------------------------------------------------------------------------
# Full Context
# ---------------------------------------------------------------------------

class TestContext:
    def test_full_context(self, seed_data):
        resp = client.get("/api/context")
        assert resp.status_code == 200
        ctx = resp.json()
        assert "products" in ctx
        assert "domains" in ctx


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

class TestFrontend:
    def test_serves_index(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "DVA Agentic Dashboard" in resp.text
