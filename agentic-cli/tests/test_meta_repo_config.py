"""Tests for domain meta-repo configuration."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from agentic_cli.meta_repo.config import (
    MetaRepoConfig,
    DomainConfig,
    RepoConfig,
    GovernanceConfig,
    SkillsConfig,
)


def test_domain_config_from_dict():
    """Test DomainConfig creation from dictionary."""
    data = {
        "domain": "cwow-facility",
        "product": "CWOW",
        "description": "Facility management",
        "owner": "facility-team@company.com",
        "created_at": "2026-06-02T00:00:00Z",
        "tags": ["critical", "production"],
    }

    config = DomainConfig.from_dict(data)
    assert config.domain == "cwow-facility"
    assert config.product == "CWOW"
    assert config.description == "Facility management"
    assert config.owner == "facility-team@company.com"
    assert config.tags == ["critical", "production"]


def test_domain_config_to_dict():
    """Test DomainConfig conversion to dictionary."""
    config = DomainConfig(
        domain="cwow-facility",
        product="CWOW",
        description="Facility management",
        owner="facility-team@company.com",
        created_at="2026-06-02T00:00:00Z",
        tags=["critical"],
    )

    data = config.to_dict()
    assert data["domain"] == "cwow-facility"
    assert data["product"] == "CWOW"
    assert data["tags"] == ["critical"]


def test_repo_config_from_dict():
    """Test RepoConfig creation from dictionary."""
    data = {
        "slug": "cwow-facility-watercheck",
        "clone_url": "https://github.com/company/cwow-facility-watercheck.git",
        "description": "Water quality monitoring",
        "languages": ["python", "typescript"],
        "frameworks": ["fastapi", "react"],
        "status": "active",
    }

    config = RepoConfig.from_dict(data)
    assert config.slug == "cwow-facility-watercheck"
    assert config.clone_url == "https://github.com/company/cwow-facility-watercheck.git"
    assert config.languages == ["python", "typescript"]
    assert config.status == "active"


def test_governance_config_defaults():
    """Test GovernanceConfig default values."""
    config = GovernanceConfig()
    assert config.require_pre_push_hook is True
    assert config.require_ci_gates is True
    assert config.min_reviewers == 1
    assert config.test_coverage_min == 80.0


def test_governance_config_from_dict():
    """Test GovernanceConfig creation from dictionary."""
    data = {
        "branch_pattern": "^(feat|fix)/.*$",
        "require_pre_push_hook": False,
        "min_reviewers": 2,
    }

    config = GovernanceConfig.from_dict(data)
    assert config.branch_pattern == "^(feat|fix)/.*$"
    assert config.require_pre_push_hook is False
    assert config.min_reviewers == 2


def test_skills_config_defaults():
    """Test SkillsConfig default values."""
    config = SkillsConfig()
    assert config.validation_required is True
    assert config.auto_inject_superpowers is True
    assert config.skill_priority_order == ["validated", "customized", "injected"]


def test_meta_repo_config_load_domain_config():
    """Test loading domain.yaml configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        config_dir = meta_repo / ".platform" / "config"
        config_dir.mkdir(parents=True)

        domain_data = {
            "domain": "cwow-facility",
            "product": "CWOW",
            "description": "Facility management",
        }
        with open(config_dir / "domain.yaml", "w") as f:
            yaml.dump(domain_data, f)

        config = MetaRepoConfig(meta_repo)
        assert config.domain is not None
        assert config.domain.domain == "cwow-facility"
        assert config.domain.product == "CWOW"


def test_meta_repo_config_load_repos_config():
    """Test loading repos.yaml configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        config_dir = meta_repo / ".platform" / "config"
        config_dir.mkdir(parents=True)

        repos_data = {
            "repos": [
                {
                    "slug": "repo-1",
                    "clone_url": "https://github.com/company/repo-1.git",
                    "description": "Repo 1",
                },
                {
                    "slug": "repo-2",
                    "clone_url": "https://github.com/company/repo-2.git",
                    "description": "Repo 2",
                },
            ]
        }
        with open(config_dir / "repos.yaml", "w") as f:
            yaml.dump(repos_data, f)

        config = MetaRepoConfig(meta_repo)
        assert len(config.repos) == 2
        assert config.repos[0].slug == "repo-1"
        assert config.repos[1].slug == "repo-2"


def test_meta_repo_config_get_repo():
    """Test getting a specific repo by slug."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        config_dir = meta_repo / ".platform" / "config"
        config_dir.mkdir(parents=True)

        repos_data = {
            "repos": [
                {
                    "slug": "repo-1",
                    "clone_url": "https://github.com/company/repo-1.git",
                },
            ]
        }
        with open(config_dir / "repos.yaml", "w") as f:
            yaml.dump(repos_data, f)

        config = MetaRepoConfig(meta_repo)
        repo = config.get_repo("repo-1")
        assert repo is not None
        assert repo.slug == "repo-1"

        repo = config.get_repo("nonexistent")
        assert repo is None


def test_meta_repo_config_to_json():
    """Test converting config to JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_repo = Path(tmpdir) / "domain-test-meta"
        config_dir = meta_repo / ".platform" / "config"
        config_dir.mkdir(parents=True)

        domain_data = {
            "domain": "cwow-facility",
            "product": "CWOW",
        }
        with open(config_dir / "domain.yaml", "w") as f:
            yaml.dump(domain_data, f)

        config = MetaRepoConfig(meta_repo)
        json_str = config.to_json()
        data = json.loads(json_str)

        assert data["domain"]["domain"] == "cwow-facility"
        assert data["domain"]["product"] == "CWOW"
