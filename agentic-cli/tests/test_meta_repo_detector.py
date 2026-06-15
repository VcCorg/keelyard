"""Tests for domain meta-repo detector."""

import tempfile
from pathlib import Path

import pytest

from agentic_cli.meta_repo.detector import (
    detect_domain_meta_repo,
    _is_valid_meta_repo,
    is_git_initialized,
    has_submodules,
)


def test_is_valid_meta_repo_with_valid_structure():
    """Test detection of valid meta-repo structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()
        (meta_repo / ".platform").mkdir()
        (meta_repo / ".platform" / "config").mkdir()

        assert _is_valid_meta_repo(meta_repo) is True


def test_is_valid_meta_repo_without_platform_dir():
    """Test rejection when .platform missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()

        assert _is_valid_meta_repo(meta_repo) is False


def test_is_valid_meta_repo_without_config_dir():
    """Test rejection when .platform/config missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()
        (meta_repo / ".platform").mkdir()

        assert _is_valid_meta_repo(meta_repo) is False


def test_is_valid_meta_repo_nonexistent_path():
    """Test rejection of nonexistent path."""
    assert _is_valid_meta_repo(Path("/nonexistent/path")) is False


def test_detect_domain_meta_repo_in_cwd():
    """Test detection in current working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        meta_repo = tmpdir_path / "domain-test-meta"
        meta_repo.mkdir()
        (meta_repo / ".platform").mkdir()
        (meta_repo / ".platform" / "config").mkdir()

        # Detect with custom search paths
        result = detect_domain_meta_repo("test", search_paths=[tmpdir_path])
        assert result == meta_repo


def test_detect_domain_meta_repo_not_found():
    """Test when meta-repo doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = detect_domain_meta_repo("nonexistent", search_paths=[Path(tmpdir)])
        assert result is None


def test_is_git_initialized_with_git_repo():
    """Test detection of git-initialized repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()
        (meta_repo / ".git").mkdir()

        assert is_git_initialized(meta_repo) is True


def test_is_git_initialized_without_git():
    """Test detection of non-git repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()

        assert is_git_initialized(meta_repo) is False


def test_has_submodules_with_gitmodules():
    """Test detection of .gitmodules file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()
        (meta_repo / ".gitmodules").touch()

        assert has_submodules(meta_repo) is True


def test_has_submodules_without_gitmodules():
    """Test detection when .gitmodules missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        meta_repo.mkdir()

        assert has_submodules(meta_repo) is False
