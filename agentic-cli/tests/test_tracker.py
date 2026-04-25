"""Tests for the centralized activity tracker."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_cli.tracker import (
    DB_PATH,
    ActivityTimer,
    _ensure_db,
    _get_conn,
    _now_iso,
    get_activity,
    get_activity_summary,
    get_full_context,
    get_projects,
    get_repos,
    record_activity,
    register_project,
    register_repo,
    remove_repo,
)


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    """Redirect the tracker database to a temp directory for each test."""
    temp_db_dir = tmp_path / ".dva-agentic"
    temp_db_path = temp_db_dir / "tracker.db"
    monkeypatch.setattr("agentic_cli.tracker.DB_DIR", temp_db_dir)
    monkeypatch.setattr("agentic_cli.tracker.DB_PATH", temp_db_path)
    yield temp_db_path


class TestSchema:
    """Test database schema creation."""

    def test_ensure_db_creates_file(self, use_temp_db):
        _ensure_db()
        assert use_temp_db.exists()

    def test_schema_version_set(self, use_temp_db):
        _ensure_db()
        conn = sqlite3.connect(str(use_temp_db))
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        conn.close()
        assert row[0] == 7

    def test_tables_exist(self, use_temp_db):
        _ensure_db()
        conn = sqlite3.connect(str(use_temp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        table_names = [t[0] for t in tables]
        assert "activity_log" in table_names
        assert "repos" in table_names
        assert "projects" in table_names

    def test_idempotent_schema(self, use_temp_db):
        _ensure_db()
        _ensure_db()  # Should not error on second call
        assert use_temp_db.exists()


class TestActivityLog:
    """Test activity logging."""

    def test_record_activity_basic(self):
        record_activity(command="test", subcommand="run")
        entries = get_activity(command="test")
        assert len(entries) == 1
        assert entries[0]["command"] == "test"
        assert entries[0]["subcommand"] == "run"
        assert entries[0]["status"] == "success"

    def test_record_activity_with_args(self):
        record_activity(
            command="code",
            subcommand="onboard",
            args={"path": "/tmp/my-repo"},
            details={"languages": ["python"]},
            repo_path="/tmp/my-repo",
        )
        entries = get_activity(command="code", subcommand="onboard")
        assert len(entries) == 1
        entry = entries[0]
        assert entry["repo_path"] == "/tmp/my-repo"
        args = json.loads(entry["args"])
        assert args["path"] == "/tmp/my-repo"
        details = json.loads(entry["details"])
        assert details["languages"] == ["python"]

    def test_record_activity_error(self):
        record_activity(command="kg", subcommand="ingest", status="error")
        entries = get_activity(status="error")
        assert len(entries) == 1
        assert entries[0]["status"] == "error"

    def test_record_activity_with_duration(self):
        record_activity(command="project", subcommand="create", duration_ms=1234)
        entries = get_activity(command="project")
        assert entries[0]["duration_ms"] == 1234

    def test_get_activity_limit(self):
        for i in range(10):
            record_activity(command="batch", subcommand=f"op{i}")
        entries = get_activity(command="batch", limit=5)
        assert len(entries) == 5

    def test_get_activity_no_results(self):
        entries = get_activity(command="nonexistent")
        assert entries == []

    def test_get_activity_summary_empty(self):
        summary = get_activity_summary()
        assert summary["total_actions"] == 0
        assert summary["errors"] == 0

    def test_get_activity_summary(self):
        record_activity(command="code", subcommand="onboard")
        record_activity(command="code", subcommand="onboard")
        record_activity(command="kg", subcommand="ingest", status="error")
        summary = get_activity_summary()
        assert summary["total_actions"] == 3
        assert summary["errors"] == 1
        assert summary["commands"]["code"] == 2
        assert summary["commands"]["kg"] == 1
        assert "100" not in summary["success_rate"]  # 66.7%


class TestActivityTimer:
    """Test the ActivityTimer context manager."""

    def test_timer_records_success(self):
        with ActivityTimer("test", "timer") as t:
            t.set_details(result="ok")
        entries = get_activity(command="test", subcommand="timer")
        assert len(entries) == 1
        assert entries[0]["status"] == "success"
        assert entries[0]["duration_ms"] is not None
        assert entries[0]["duration_ms"] >= 0

    def test_timer_records_error(self):
        with ActivityTimer("test", "error-timer") as t:
            t.set_error("something broke")
        entries = get_activity(command="test", subcommand="error-timer")
        assert len(entries) == 1
        assert entries[0]["status"] == "error"

    def test_timer_catches_exception(self):
        with pytest.raises(ValueError):
            with ActivityTimer("test", "exception"):
                raise ValueError("boom")
        entries = get_activity(command="test", subcommand="exception")
        assert len(entries) == 1
        assert entries[0]["status"] == "error"
        details = json.loads(entries[0]["details"])
        assert "boom" in details["error"]


class TestReposRegistry:
    """Test onboarded repos tracking."""

    def test_register_repo(self):
        register_repo(
            name="my-repo",
            path="/tmp/my-repo",
            repo_url="https://github.com/user/repo.git",
            languages=["python", "javascript"],
            frameworks=["fastapi"],
            build_tools=["make"],
            test_frameworks=["pytest"],
            databases=["postgres"],
            dependencies=42,
            skills_installed=["project-context", "python-fastapi"],
            has_docker=True,
        )
        repos = get_repos()
        assert len(repos) == 1
        repo = repos[0]
        assert repo["name"] == "my-repo"
        assert repo["path"] == "/tmp/my-repo"
        assert repo["repo_url"] == "https://github.com/user/repo.git"
        assert repo["languages"] == ["python", "javascript"]
        assert repo["frameworks"] == ["fastapi"]
        assert repo["dependencies"] == 42
        assert repo["skills_installed"] == ["project-context", "python-fastapi"]
        assert repo["has_docker"] == 1

    def test_register_repo_update(self):
        register_repo(name="repo1", path="/tmp/repo1", languages=["python"])
        register_repo(name="repo1-updated", path="/tmp/repo1", languages=["python", "go"])
        repos = get_repos()
        assert len(repos) == 1
        assert repos[0]["name"] == "repo1-updated"
        assert repos[0]["languages"] == ["python", "go"]

    def test_get_repos_filter_by_name(self):
        register_repo(name="alpha-service", path="/tmp/alpha")
        register_repo(name="beta-service", path="/tmp/beta")
        register_repo(name="gamma-lib", path="/tmp/gamma")
        repos = get_repos(name="service")
        assert len(repos) == 2

    def test_remove_repo(self):
        register_repo(name="to-remove", path="/tmp/to-remove")
        assert remove_repo("/tmp/to-remove") is True
        repos = get_repos()
        assert len(repos) == 0

    def test_remove_repo_not_found(self):
        assert remove_repo("/tmp/nonexistent") is False

    def test_multiple_repos(self):
        for i in range(5):
            register_repo(name=f"repo-{i}", path=f"/tmp/repo-{i}", languages=["python"])
        repos = get_repos()
        assert len(repos) == 5


class TestProjectsRegistry:
    """Test created projects tracking."""

    def test_register_project(self):
        register_project(
            name="my-agent",
            path="/tmp/my-agent",
            framework="adk",
            use_case="rag",
            tools=["web_search", "vector_search"],
        )
        projects = get_projects()
        assert len(projects) == 1
        proj = projects[0]
        assert proj["name"] == "my-agent"
        assert proj["framework"] == "adk"
        assert proj["use_case"] == "rag"
        assert proj["tools"] == ["web_search", "vector_search"]

    def test_register_project_update(self):
        register_project(name="proj1", path="/tmp/proj1", framework="adk")
        register_project(name="proj1", path="/tmp/proj1", framework="langgraph")
        projects = get_projects()
        assert len(projects) == 1
        assert projects[0]["framework"] == "langgraph"


class TestFullContext:
    """Test the agent-facing context export."""

    def test_full_context_empty(self):
        ctx = get_full_context()
        assert ctx["repos"] == []
        assert ctx["projects"] == []
        assert ctx["activity_summary"]["total_actions"] == 0
        assert ctx["recent_activity"] == []

    def test_full_context_populated(self):
        register_repo(name="repo1", path="/tmp/repo1", languages=["python"])
        register_project(name="proj1", path="/tmp/proj1", framework="adk")
        record_activity(command="code", subcommand="onboard")
        ctx = get_full_context()
        assert len(ctx["repos"]) == 1
        assert len(ctx["projects"]) == 1
        assert ctx["activity_summary"]["total_actions"] == 1
        assert len(ctx["recent_activity"]) == 1
