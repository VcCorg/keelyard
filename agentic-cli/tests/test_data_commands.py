"""Tests for data configuration commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from agentic_cli.main import app

runner = CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".dva-agentic"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_config_file(temp_config_dir):
    """Mock the config file location."""
    config_file = temp_config_dir / "config.json"
    with patch("agentic_cli.commands.data.CONFIG_DIR", temp_config_dir):
        with patch("agentic_cli.commands.data.CONFIG_FILE", config_file):
            yield config_file


def test_data_help():
    """Test that data command group shows help."""
    result = runner.invoke(app, ["data", "--help"])
    assert result.exit_code == 0
    assert "Manage data source configurations" in result.stdout


def test_data_init_gcs(mock_config_file):
    """Test initializing GCS configuration."""
    result = runner.invoke(
        app,
        [
            "data",
            "init",
            "--gcs-project-id",
            "test-project",
            "--gcs-bucket",
            "test-bucket",
            "--gcs-prefix",
            "data/",
        ],
    )
    assert result.exit_code == 0
    assert "Configuration saved" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    assert config["data"]["globals"]["gcs"]["project_id"] == "test-project"
    assert config["data"]["globals"]["gcs"]["default_bucket"] == "test-bucket"
    assert config["data"]["globals"]["gcs"]["default_prefix"] == "data/"


def test_data_init_confluence(mock_config_file):
    """Test initializing Confluence configuration."""
    result = runner.invoke(
        app,
        [
            "data",
            "init",
            "--confluence-url",
            "https://test.atlassian.net/wiki",
            "--confluence-username",
            "test@example.com",
            "--confluence-api-token-env",
            "MY_CONFLUENCE_TOKEN",
        ],
    )
    assert result.exit_code == 0
    assert "Configuration saved" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    assert config["data"]["globals"]["confluence"]["base_url"] == "https://test.atlassian.net/wiki"
    assert config["data"]["globals"]["confluence"]["username"] == "test@example.com"
    assert config["data"]["globals"]["confluence"]["api_token_env"] == "MY_CONFLUENCE_TOKEN"


def test_data_init_no_options(mock_config_file):
    """Test data init with no options shows error."""
    # Note: confluence-api-token-env has a default value, so we need to explicitly
    # test with no meaningful options
    result = runner.invoke(app, ["data", "init"])
    # With default confluence-api-token-env, it will save that value
    assert result.exit_code == 0
    # Check that it saved the default token env
    assert "Confluence Token Env: CONFLUENCE_API_TOKEN" in result.stdout


def test_data_create_local_doc(mock_config_file):
    """Test creating a local doc data source."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-docs",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test-docs",
            "--description",
            "Test documentation",
            "--tags",
            "test,local",
        ],
    )
    assert result.exit_code == 0
    assert "Data source created successfully" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert len(sources) == 1
    assert sources[0]["name"] == "test-docs"
    assert sources[0]["type"] == "doc"
    assert sources[0]["location"] == "/tmp/test-docs"
    assert sources[0]["description"] == "Test documentation"
    assert sources[0]["tags"] == ["test", "local"]
    assert "created_at" in sources[0]


def test_data_create_gcs_doc(mock_config_file):
    """Test creating a GCS doc data source."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "gcs-data",
            "--source-type",
            "doc",
            "--source-location",
            "gs://my-bucket/data/docs",
            "--description",
            "GCS documentation",
        ],
    )
    assert result.exit_code == 0
    assert "Valid GCS path format" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert len(sources) == 1
    assert sources[0]["name"] == "gcs-data"
    assert sources[0]["location"] == "gs://my-bucket/data/docs"


def test_data_create_confluence(mock_config_file):
    """Test creating a Confluence data source."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "team-wiki",
            "--source-type",
            "confluence",
            "--source-location",
            "https://mycompany.atlassian.net/wiki/spaces/TEAM",
            "--description",
            "Team wiki",
        ],
    )
    assert result.exit_code == 0
    assert "Valid Confluence URL format" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert len(sources) == 1
    assert sources[0]["name"] == "team-wiki"
    assert sources[0]["type"] == "confluence"


def test_data_create_duplicate_name(mock_config_file):
    """Test that creating a duplicate name fails."""
    # Create first source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-docs",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test",
        ],
    )
    
    # Try to create duplicate
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-docs",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test2",
        ],
    )
    assert result.exit_code == 1
    assert "already exists" in result.stdout


def test_data_create_invalid_type(mock_config_file):
    """Test that invalid source type fails."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test",
            "--source-type",
            "invalid",
            "--source-location",
            "/tmp/test",
        ],
    )
    assert result.exit_code == 1
    assert "Invalid source type" in result.stdout


def test_data_create_invalid_confluence_url(mock_config_file):
    """Test that invalid Confluence URL fails."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test",
            "--source-type",
            "confluence",
            "--source-location",
            "not-a-url",
        ],
    )
    assert result.exit_code == 1
    assert "must be a valid URL" in result.stdout


def test_data_list_empty(mock_config_file):
    """Test listing when no sources exist."""
    result = runner.invoke(app, ["data", "list"])
    assert result.exit_code == 0
    assert "No data sources configured" in result.stdout


def test_data_list_with_sources(mock_config_file):
    """Test listing data sources."""
    # Create some sources
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "source1",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test1",
        ],
    )
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "source2",
            "--source-type",
            "confluence",
            "--source-location",
            "https://example.com/wiki",
        ],
    )
    
    result = runner.invoke(app, ["data", "list"])
    assert result.exit_code == 0
    assert "source1" in result.stdout
    assert "source2" in result.stdout
    assert "2 total" in result.stdout


def test_data_show(mock_config_file):
    """Test showing a specific data source."""
    # Create a source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-source",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test",
            "--description",
            "Test description",
            "--tags",
            "tag1,tag2",
        ],
    )
    
    result = runner.invoke(app, ["data", "show", "test-source"])
    assert result.exit_code == 0
    assert "test-source" in result.stdout
    assert "Test description" in result.stdout
    assert "tag1, tag2" in result.stdout


def test_data_show_not_found(mock_config_file):
    """Test showing a non-existent source when no sources exist."""
    result = runner.invoke(app, ["data", "show", "nonexistent"])
    assert result.exit_code == 1
    assert "No data sources configured" in result.stdout


def test_data_update(mock_config_file):
    """Test updating a data source."""
    # Create a source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-source",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test",
            "--description",
            "Original description",
        ],
    )
    
    # Update it
    result = runner.invoke(
        app,
        [
            "data",
            "update",
            "test-source",
            "--description",
            "Updated description",
            "--tags",
            "new,tags",
        ],
    )
    assert result.exit_code == 0
    assert "updated successfully" in result.stdout
    
    # Verify update
    config = json.loads(mock_config_file.read_text())
    source = config["data"]["sources"][0]
    assert source["description"] == "Updated description"
    assert source["tags"] == ["new", "tags"]


def test_data_update_location(mock_config_file):
    """Test updating source location."""
    # Create a source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-source",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test",
        ],
    )
    
    # Update location
    result = runner.invoke(
        app,
        [
            "data",
            "update",
            "test-source",
            "--source-location",
            "gs://new-bucket/path",
        ],
    )
    assert result.exit_code == 0
    
    # Verify update
    config = json.loads(mock_config_file.read_text())
    source = config["data"]["sources"][0]
    assert source["location"] == "gs://new-bucket/path"


def test_data_update_not_found(mock_config_file):
    """Test updating a non-existent source when no sources exist."""
    result = runner.invoke(
        app,
        ["data", "update", "nonexistent", "--description", "test"],
    )
    assert result.exit_code == 1
    assert "No data sources configured" in result.stdout


def test_data_update_no_options(mock_config_file):
    """Test update with no options."""
    # Create a source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-source",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test",
        ],
    )
    
    result = runner.invoke(app, ["data", "update", "test-source"])
    assert result.exit_code == 0
    assert "No updates provided" in result.stdout


def test_data_delete(mock_config_file):
    """Test deleting a data source."""
    # Create a source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-source",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/test",
        ],
    )
    
    # Delete it
    result = runner.invoke(app, ["data", "delete", "test-source", "--yes"])
    assert result.exit_code == 0
    assert "deleted successfully" in result.stdout
    
    # Verify deletion
    config = json.loads(mock_config_file.read_text())
    assert len(config["data"]["sources"]) == 0


def test_data_delete_not_found(mock_config_file):
    """Test deleting a non-existent source when no sources exist."""
    result = runner.invoke(app, ["data", "delete", "nonexistent", "--yes"])
    assert result.exit_code == 1
    assert "No data sources configured" in result.stdout


def test_data_create_invalid_gcs_path(mock_config_file):
    """Test that invalid GCS path fails."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test",
            "--source-type",
            "doc",
            "--source-location",
            "gs://",  # Invalid - no bucket name
        ],
    )
    assert result.exit_code == 1
    assert "must include bucket name" in result.stdout


def test_data_create_git_https(mock_config_file):
    """Test creating a git source with HTTPS URL and branch."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-repo",
            "--source-type",
            "git",
            "--source-location",
            "https://github.com/user/repo.git",
            "--git-branch",
            "main",
            "--description",
            "Test repository",
        ],
    )
    assert result.exit_code == 0
    assert "Valid Git repository URL format" in result.stdout
    assert "Git branch: main" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert len(sources) == 1
    assert sources[0]["name"] == "test-repo"
    assert sources[0]["type"] == "git"
    assert sources[0]["location"] == "https://github.com/user/repo.git"
    assert sources[0]["git"]["branch"] == "main"


def test_data_create_git_ssh(mock_config_file):
    """Test creating a git source with SSH URL and tag."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "prod-repo",
            "--source-type",
            "git",
            "--source-location",
            "git@github.com:company/repo.git",
            "--git-tag",
            "v1.0.0",
        ],
    )
    assert result.exit_code == 0
    assert "Valid Git repository URL format" in result.stdout
    assert "Git tag: v1.0.0" in result.stdout
    
    # Verify config file
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert len(sources) == 1
    assert sources[0]["name"] == "prod-repo"
    assert sources[0]["type"] == "git"
    assert sources[0]["git"]["tag"] == "v1.0.0"


def test_data_create_git_no_branch_or_tag(mock_config_file):
    """Test creating a git source without branch or tag."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "default-repo",
            "--source-type",
            "git",
            "--source-location",
            "https://github.com/user/repo.git",
        ],
    )
    assert result.exit_code == 0
    assert "will use default branch" in result.stdout
    
    # Verify config file - should not have git metadata
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert len(sources) == 1
    assert "git" not in sources[0]


def test_data_create_git_both_branch_and_tag(mock_config_file):
    """Test that specifying both branch and tag fails."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "error-repo",
            "--source-type",
            "git",
            "--source-location",
            "https://github.com/user/repo.git",
            "--git-branch",
            "main",
            "--git-tag",
            "v1.0.0",
        ],
    )
    assert result.exit_code == 1
    assert "Cannot specify both --git-branch and --git-tag" in result.stdout


def test_data_create_git_invalid_url(mock_config_file):
    """Test that invalid git URL fails."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "invalid-repo",
            "--source-type",
            "git",
            "--source-location",
            "/local/path/repo",
        ],
    )
    assert result.exit_code == 1
    assert "must be a valid repository URL" in result.stdout


def test_data_create_git_invalid_ssh_format(mock_config_file):
    """Test that invalid SSH format fails."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "invalid-ssh",
            "--source-type",
            "git",
            "--source-location",
            "git@github.com",  # Missing colon separator
        ],
    )
    assert result.exit_code == 1
    assert "must include ':' separator" in result.stdout


def test_data_create_git_protocol_url(mock_config_file):
    """Test creating a git source with git:// protocol."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "git-protocol",
            "--source-type",
            "git",
            "--source-location",
            "git://github.com/user/repo.git",
        ],
    )
    assert result.exit_code == 0
    assert "Valid Git repository URL format" in result.stdout


def test_data_show_git_with_branch(mock_config_file):
    """Test showing a git source with branch."""
    # Create a git source
    runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "test-repo",
            "--source-type",
            "git",
            "--source-location",
            "https://github.com/user/repo.git",
            "--git-branch",
            "develop",
        ],
    )
    
    result = runner.invoke(app, ["data", "show", "test-repo"])
    assert result.exit_code == 0
    assert "test-repo" in result.stdout
    assert "git" in result.stdout
    assert "develop" in result.stdout


def test_data_create_git_params_ignored_for_non_git(mock_config_file):
    """Test that git parameters are ignored for non-git sources."""
    result = runner.invoke(
        app,
        [
            "data",
            "create",
            "--name",
            "doc-source",
            "--source-type",
            "doc",
            "--source-location",
            "/tmp/docs",
            "--git-branch",
            "main",  # Should be ignored
        ],
    )
    assert result.exit_code == 0
    assert "only applicable for git source type" in result.stdout
    
    # Verify git metadata not saved
    config = json.loads(mock_config_file.read_text())
    sources = config["data"]["sources"]
    assert "git" not in sources[0]
