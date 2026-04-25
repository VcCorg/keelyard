"""Tests for kg/sync.py — KG Sync Layer."""

import json
import pytest
from unittest.mock import patch, MagicMock

from agentic_cli.kg.sync import (
    build_repos_document,
    build_projects_document,
    build_activity_document,
    sync_to_lightrag,
    KGSyncResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_REPOS = [
    {
        "name": "cwow-patient-query-spanner",
        "path": "/workspace/cwow-patient-query-spanner",
        "repo_url": "https://bitbucket.example.com/scm/cgf/cwow-patient-query-spanner.git",
        "languages": ["Java"],
        "frameworks": ["Spring Boot 3"],
        "build_tools": ["Gradle"],
        "test_frameworks": ["JUnit 5"],
        "databases": ["Cloud Spanner"],
        "dependencies": 42,
        "skills_installed": ["java-spring-boot", "database-spanner"],
        "has_docker": True,
        "onboarded_at": "2026-04-08T10:00:00Z",
        "last_updated_at": "2026-04-10T15:30:00Z",
    },
    {
        "name": "cwow-facility-service",
        "path": "/workspace/cwow-facility-service",
        "repo_url": None,
        "languages": ["Java"],
        "frameworks": ["Spring Boot 3"],
        "build_tools": ["Maven"],
        "test_frameworks": [],
        "databases": [],
        "dependencies": 25,
        "skills_installed": ["java-spring-boot"],
        "has_docker": False,
        "onboarded_at": "2026-04-09T08:00:00Z",
        "last_updated_at": "2026-04-09T08:00:00Z",
    },
]

SAMPLE_PROJECTS = [
    {
        "name": "cwow-pr-reviewer",
        "path": "/workspace/cwow-pr-reviewer",
        "framework": "adk",
        "use_case": "pr-reviewer",
        "tools": ["bitbucket", "jira"],
        "created_at": "2026-04-10T12:00:00Z",
    },
]

SAMPLE_ACTIVITIES = [
    {
        "timestamp": "2026-04-10T15:30:00Z",
        "command": "code",
        "subcommand": "onboard",
        "status": "success",
        "duration_ms": 12500,
        "details": json.dumps({"repo": "cwow-patient-query-spanner", "skills": 3}),
    },
    {
        "timestamp": "2026-04-10T14:00:00Z",
        "command": "project",
        "subcommand": "create",
        "status": "success",
        "duration_ms": 3400,
        "details": json.dumps({"name": "cwow-pr-reviewer"}),
    },
    {
        "timestamp": "2026-04-10T13:00:00Z",
        "command": "kg",
        "subcommand": "ingest-submit",
        "status": "error",
        "duration_ms": 500,
        "details": json.dumps({"error": "LightRAG not available"}),
    },
]

SAMPLE_SUMMARY = {
    "total_actions": 25,
    "errors": 2,
    "success_rate": "92.0%",
    "commands": {"code": 10, "project": 8, "kg": 7},
    "last_activity": "2026-04-10T15:30:00Z",
}


# ---------------------------------------------------------------------------
# Document Builder Tests
# ---------------------------------------------------------------------------

class TestBuildReposDocument:
    def test_empty_repos(self):
        assert build_repos_document([]) == ""

    def test_includes_all_repos(self):
        doc = build_repos_document(SAMPLE_REPOS)
        assert "cwow-patient-query-spanner" in doc
        assert "cwow-facility-service" in doc
        assert "2 repositories" in doc

    def test_includes_tech_stack(self):
        doc = build_repos_document(SAMPLE_REPOS)
        assert "Java" in doc
        assert "Spring Boot 3" in doc
        assert "Cloud Spanner" in doc
        assert "Gradle" in doc

    def test_includes_skills(self):
        doc = build_repos_document(SAMPLE_REPOS)
        assert "java-spring-boot" in doc
        assert "database-spanner" in doc

    def test_includes_docker_flag(self):
        doc = build_repos_document(SAMPLE_REPOS)
        assert "Docker:** Yes" in doc  # first repo
        assert "Docker:** No" in doc   # second repo

    def test_handles_string_json_fields(self):
        """Fields stored as JSON strings should still render."""
        repo = {
            "name": "test-repo",
            "path": "/tmp/test",
            "languages": '["Python"]',
            "frameworks": '["FastAPI"]',
            "build_tools": [],
            "test_frameworks": [],
            "databases": [],
            "dependencies": 5,
            "skills_installed": [],
            "has_docker": False,
            "onboarded_at": "2026-04-01",
            "last_updated_at": "2026-04-01",
        }
        doc = build_repos_document([repo])
        assert "test-repo" in doc


class TestBuildProjectsDocument:
    def test_empty_projects(self):
        assert build_projects_document([]) == ""

    def test_includes_project(self):
        doc = build_projects_document(SAMPLE_PROJECTS)
        assert "cwow-pr-reviewer" in doc
        assert "pr-reviewer" in doc
        assert "adk" in doc

    def test_includes_tools(self):
        doc = build_projects_document(SAMPLE_PROJECTS)
        assert "bitbucket" in doc
        assert "jira" in doc


class TestBuildActivityDocument:
    def test_empty_activities(self):
        assert build_activity_document([], {}) == ""

    def test_includes_summary_stats(self):
        doc = build_activity_document(SAMPLE_ACTIVITIES, SAMPLE_SUMMARY)
        assert "25" in doc  # total_actions
        assert "92.0%" in doc  # success_rate

    def test_includes_actions(self):
        doc = build_activity_document(SAMPLE_ACTIVITIES, SAMPLE_SUMMARY)
        assert "code onboard" in doc
        assert "project create" in doc

    def test_error_actions_marked(self):
        doc = build_activity_document(SAMPLE_ACTIVITIES, SAMPLE_SUMMARY)
        assert "✗" in doc  # error marker

    def test_since_label(self):
        doc = build_activity_document(SAMPLE_ACTIVITIES, SAMPLE_SUMMARY, since="2026-04-01")
        assert "since 2026-04-01" in doc


# ---------------------------------------------------------------------------
# Sync Engine Tests
# ---------------------------------------------------------------------------

class TestSyncToLightrag:
    @patch("agentic_cli.kg.sync.get_repos", return_value=SAMPLE_REPOS)
    @patch("agentic_cli.kg.sync.get_projects", return_value=SAMPLE_PROJECTS)
    @patch("agentic_cli.kg.sync.get_activity", return_value=SAMPLE_ACTIVITIES)
    @patch("agentic_cli.kg.sync.get_activity_summary", return_value=SAMPLE_SUMMARY)
    def test_sync_all(self, mock_summary, mock_activity, mock_projects, mock_repos):
        mock_client = MagicMock()
        mock_client.insert.return_value = {"characters": 500}

        with patch("agentic_cli.kg.config.KGConfig") as mock_config_cls, \
             patch("agentic_cli.kg.lightrag_client.LightRAGClient", return_value=mock_client):
            mock_config = MagicMock()
            mock_config.lightrag_url = "http://localhost:8001"
            mock_config.lightrag_timeout = 30.0
            mock_config_cls.load.return_value = mock_config

            result = sync_to_lightrag()

        assert result.repos_synced == 2
        assert result.projects_synced == 1
        assert result.activities_synced == 3
        assert result.total_chars == 1500  # 3 docs × 500
        assert mock_client.insert.call_count == 3
        assert result.errors == []

    @patch("agentic_cli.kg.sync.get_repos", return_value=SAMPLE_REPOS)
    def test_sync_repos_only(self, mock_repos):
        mock_client = MagicMock()
        mock_client.insert.return_value = {"characters": 800}

        with patch("agentic_cli.kg.config.KGConfig") as mock_config_cls, \
             patch("agentic_cli.kg.lightrag_client.LightRAGClient", return_value=mock_client):
            mock_config = MagicMock()
            mock_config.lightrag_url = "http://localhost:8001"
            mock_config.lightrag_timeout = 30.0
            mock_config_cls.load.return_value = mock_config

            result = sync_to_lightrag(sync_repos=True, sync_projects=False, sync_activity=False)

        assert result.repos_synced == 2
        assert result.projects_synced == 0
        assert result.activities_synced == 0
        assert mock_client.insert.call_count == 1

    @patch("agentic_cli.kg.sync.get_repos", return_value=SAMPLE_REPOS)
    def test_sync_handles_errors(self, mock_repos):
        mock_client = MagicMock()
        mock_client.insert.side_effect = Exception("Connection refused")

        with patch("agentic_cli.kg.config.KGConfig") as mock_config_cls, \
             patch("agentic_cli.kg.lightrag_client.LightRAGClient", return_value=mock_client):
            mock_config = MagicMock()
            mock_config.lightrag_url = "http://localhost:8001"
            mock_config.lightrag_timeout = 30.0
            mock_config_cls.load.return_value = mock_config

            result = sync_to_lightrag(sync_repos=True, sync_projects=False, sync_activity=False)

        assert result.repos_synced == 0
        assert len(result.errors) == 1
        assert "Connection refused" in result.errors[0]

    @patch("agentic_cli.kg.sync.get_repos", return_value=[])
    @patch("agentic_cli.kg.sync.get_projects", return_value=[])
    @patch("agentic_cli.kg.sync.get_activity", return_value=[])
    @patch("agentic_cli.kg.sync.get_activity_summary", return_value={})
    def test_sync_with_no_data(self, mock_summary, mock_activity, mock_projects, mock_repos):
        mock_client = MagicMock()

        with patch("agentic_cli.kg.config.KGConfig") as mock_config_cls, \
             patch("agentic_cli.kg.lightrag_client.LightRAGClient", return_value=mock_client):
            mock_config = MagicMock()
            mock_config.lightrag_url = "http://localhost:8001"
            mock_config.lightrag_timeout = 30.0
            mock_config_cls.load.return_value = mock_config

            result = sync_to_lightrag()

        assert result.repos_synced == 0
        assert result.projects_synced == 0
        assert result.activities_synced == 0
        assert mock_client.insert.call_count == 0


class TestKGSyncResult:
    def test_total_documents(self):
        r = KGSyncResult()
        assert r.total_documents == 0

        r.repos_synced = 2
        assert r.total_documents == 1

        r.projects_synced = 1
        r.activities_synced = 5
        assert r.total_documents == 3
