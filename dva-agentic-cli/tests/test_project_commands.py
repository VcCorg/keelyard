"""Tests for project commands."""

import shutil
from pathlib import Path
from typer.testing import CliRunner

from dva_agentic_cli.main import app

runner = CliRunner()


def test_project_list_templates():
    """Test listing available templates."""
    result = runner.invoke(app, ["project", "list-templates"])
    assert result.exit_code == 0
    assert "Available Frameworks" in result.stdout
    assert "adk" in result.stdout
    assert "Available Use Cases" in result.stdout


def test_project_create_help():
    """Test project create help."""
    result = runner.invoke(app, ["project", "create", "--help"])
    assert result.exit_code == 0
    assert "Create a new agentic project" in result.stdout


def test_project_info_help():
    """Test project info help."""
    result = runner.invoke(app, ["project", "info", "--help"])
    assert result.exit_code == 0
    assert "Show information about an agentic project" in result.stdout


def test_project_create_and_info(tmp_path):
    """Test creating a project and getting info about it."""
    project_name = "test-project"
    
    # Create project
    result = runner.invoke(
        app,
        ["project", "create", project_name, "--path", str(tmp_path), "--force"],
    )
    assert result.exit_code == 0
    assert "Project created successfully" in result.stdout
    
    # Verify project was created
    project_path = tmp_path / project_name
    assert project_path.exists()
    assert (project_path / "pyproject.toml").exists()
    assert (project_path / "src").exists()
    assert (project_path / ".env").exists()
    
    # Get project info
    result = runner.invoke(app, ["project", "info", str(project_path)])
    assert result.exit_code == 0
    assert project_name in result.stdout
    assert "0.1.0" in result.stdout
    
    # Cleanup
    shutil.rmtree(project_path)


def test_project_create_invalid_framework(tmp_path):
    """Test creating project with invalid framework."""
    result = runner.invoke(
        app,
        ["project", "create", "test", "--path", str(tmp_path), "--framework", "invalid"],
    )
    assert result.exit_code == 1
    assert "Invalid framework" in result.stdout


def test_project_create_invalid_use_case(tmp_path):
    """Test creating project with invalid use case."""
    result = runner.invoke(
        app,
        ["project", "create", "test", "--path", str(tmp_path), "--use-case", "invalid"],
    )
    assert result.exit_code == 1
    assert "Invalid use case" in result.stdout


def test_project_create_with_use_case(tmp_path):
    """Test creating project with specific use case."""
    result = runner.invoke(
        app,
        ["project", "create", "kg-test", "--path", str(tmp_path), "--use-case", "knowledge-graph", "--force"],
    )
    assert result.exit_code == 0
    assert "Knowledge Graph Agent" in result.stdout
    
    # Verify KG tools were included
    project_path = tmp_path / "kg-test"
    assert (project_path / "src" / "tools" / "kg_query.py").exists()
    
    # Cleanup
    shutil.rmtree(project_path)


def test_project_info_nonexistent():
    """Test getting info for nonexistent project."""
    result = runner.invoke(app, ["project", "info", "/nonexistent/path"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout
