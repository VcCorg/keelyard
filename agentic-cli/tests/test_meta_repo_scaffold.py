"""Tests for domain meta-repo scaffolding."""

import tempfile
from pathlib import Path

import pytest
import yaml

from agentic_cli.meta_repo.scaffold import scaffold_domain_meta_repo


def test_scaffold_domain_meta_repo_creates_structure():
    """Test that scaffolding creates the correct directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        created = scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        assert meta_repo.exists()
        assert (meta_repo / ".platform").exists()
        assert (meta_repo / ".platform" / "config").exists()
        assert (meta_repo / ".platform" / "common").exists()
        assert (meta_repo / ".agents").exists()
        assert (meta_repo / ".agents" / "agents").exists()
        assert (meta_repo / ".agents" / "skills").exists()
        assert (meta_repo / "repos").exists()
        assert (meta_repo / "docs").exists()
        assert (meta_repo / "plans").exists()
        assert (meta_repo / ".githooks").exists()


def test_scaffold_domain_meta_repo_creates_config_files():
    """Test that scaffolding creates configuration files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        config_dir = meta_repo / ".platform" / "config"

        assert (config_dir / "domain.yaml").exists()
        assert (config_dir / "repos.yaml").exists()
        assert (config_dir / "governance.yaml").exists()
        assert (config_dir / "skills.yaml").exists()


def test_scaffold_domain_meta_repo_creates_documentation():
    """Test that scaffolding creates documentation files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        docs_dir = meta_repo / "docs"

        assert (docs_dir / "README.md").exists()
        assert (docs_dir / "ONBOARDING.md").exists()
        assert (docs_dir / "GOVERNANCE.md").exists()
        assert (docs_dir / "ARCHITECTURE.md").exists()


def test_scaffold_domain_meta_repo_creates_makefile():
    """Test that scaffolding creates Makefile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        makefile = meta_repo / "Makefile"

        assert makefile.exists()
        content = makefile.read_text()
        assert "init:" in content
        assert "update:" in content
        assert "validate:" in content


def test_scaffold_domain_meta_repo_creates_gitignore():
    """Test that scaffolding creates .gitignore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        gitignore = meta_repo / ".gitignore"

        assert gitignore.exists()
        content = gitignore.read_text()
        assert "plans/" in content
        assert "__pycache__/" in content


def test_scaffold_domain_meta_repo_domain_config_content():
    """Test that domain.yaml contains correct content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        domain_yaml = meta_repo / ".platform" / "config" / "domain.yaml"

        with open(domain_yaml) as f:
            data = yaml.safe_load(f)

        assert data["domain"] == "test-domain"
        assert data["product"] == "TEST"
        assert data["description"] == "Test domain"
        assert data["owner"] == "test@company.com"


def test_scaffold_domain_meta_repo_repos_config_with_repos():
    """Test that repos.yaml contains linked repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        repos = [
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

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            repos=repos,
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        repos_yaml = meta_repo / ".platform" / "config" / "repos.yaml"

        with open(repos_yaml) as f:
            data = yaml.safe_load(f)

        assert len(data["repos"]) == 2
        assert data["repos"][0]["slug"] == "repo-1"
        assert data["repos"][1]["slug"] == "repo-2"


def test_scaffold_domain_meta_repo_already_exists():
    """Test that scaffolding fails if meta-repo already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Create first meta-repo
        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        # Try to create again - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            scaffold_domain_meta_repo(
                output_dir=output_dir,
                domain="test-domain",
                product="TEST",
                description="Test domain",
                owner="test@company.com",
                git_init=False,
            )


def test_scaffold_domain_meta_repo_invalid_output_dir():
    """Test that scaffolding fails with invalid output directory."""
    with pytest.raises(ValueError, match="does not exist"):
        scaffold_domain_meta_repo(
            output_dir=Path("/nonexistent/directory"),
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )


def test_scaffold_domain_meta_repo_platform_common_files():
    """Test that platform common files are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        common_dir = meta_repo / ".platform" / "common"

        assert (common_dir / "__init__.py").exists()
        assert (common_dir / "config_loader.py").exists()


def test_scaffold_creates_root_readme_and_agents_md():
    """Test that root README.md and AGENTS.md are created per meta-repo standards."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"

        assert (meta_repo / "README.md").exists()
        assert (meta_repo / "AGENTS.md").exists()
        assert (meta_repo / ".platform" / "README.md").exists()


def test_scaffold_creates_pre_push_hook():
    """Test that an executable pre-push hook enforcing branch naming is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        hook = meta_repo / ".githooks" / "pre-push"

        assert hook.exists()
        assert hook.stat().st_mode & 0o111 != 0  # executable
        content = hook.read_text()
        assert "JIRA-ID" in content


def test_scaffold_makefile_has_update_one_and_setup_hooks():
    """Test that Makefile includes update-one and setup-hooks targets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        scaffold_domain_meta_repo(
            output_dir=output_dir,
            domain="test-domain",
            product="TEST",
            description="Test domain",
            owner="test@company.com",
            git_init=False,
        )

        meta_repo = output_dir / "domain-test-domain-meta"
        makefile = (meta_repo / "Makefile").read_text()

        assert "update-one:" in makefile
        assert "setup-hooks:" in makefile
        assert "init: setup-hooks" in makefile
