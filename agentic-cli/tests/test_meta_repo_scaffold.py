"""Tests for domain meta-repo scaffolding."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from agentic_cli.meta_repo.scaffold import scaffold_domain_meta_repo


def _seed_skill(meta_repo: Path, rel: str, name: str, desc: str) -> None:
    """Write a minimal SKILL.md at ``rel`` under the meta-repo."""
    d = meta_repo / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n# {name}\n",
        encoding="utf-8",
    )


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


def test_scaffold_creates_skills_profiler_script():
    """The scaffold ships an executable, stdlib-only skills profiler."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        script = meta_repo / ".platform" / "scripts" / "profile_skills.py"

        assert script.exists()
        assert script.stat().st_mode & 0o111 != 0  # executable
        content = script.read_text()
        assert "build_manifest" in content
        assert "skills-manifest.json" in content


def test_scaffold_makefile_has_skills_targets():
    """Makefile wires load-skills into init and a skills profile into validate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        makefile = (meta_repo / "Makefile").read_text()

        assert "load-skills:" in makefile
        assert "skills:" in makefile
        # init loads skills after fetching submodules
        assert "load-skills" in makefile.split("init:")[1].split("update:")[0]
        # validate runs the profiler
        assert "profile_skills.py --check" in makefile


def test_skills_profiler_indexes_and_classifies():
    """Running the profiler indexes skills across sources and writes a manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        _seed_skill(meta_repo, ".agents/skills/personas/dev", "dev", "Dev persona")
        _seed_skill(meta_repo, ".agents/skills/water", "water-check", "Check water")
        _seed_skill(
            meta_repo, "repos/domain-context/skills/sync", "facility-sync", "Sync")
        _seed_skill(
            meta_repo, "repos/app/.skills/log", "app-log", "Structured logging")

        script = meta_repo / ".platform" / "scripts" / "profile_skills.py"
        result = subprocess.run(
            [sys.executable, str(script), "--write", "--summary"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Total: 4 skills" in result.stdout

        manifest = json.loads(
            (meta_repo / ".platform" / "skills-manifest.json").read_text())
        assert manifest["total"] == 4
        assert manifest["by_tier"]["persona"] == 1
        assert manifest["by_tier"]["domain-validated"] == 1
        assert manifest["by_tier"]["agent-skill"] == 1
        assert manifest["by_tier"]["linked:app"] == 1
        names = {s["name"] for s in manifest["skills"]}
        assert {"dev", "water-check", "facility-sync", "app-log"} <= names


def test_skills_profiler_flags_uninitialized_submodules():
    """--check warns when a registered submodule has not been fetched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        (meta_repo / "repos" / "reporting").mkdir(parents=True)
        (meta_repo / ".gitmodules").write_text(
            '[submodule "repos/reporting"]\n\tpath = repos/reporting\n'
            "\turl = https://example.com/reporting.git\n",
            encoding="utf-8",
        )

        script = meta_repo / ".platform" / "scripts" / "profile_skills.py"
        result = subprocess.run(
            [sys.executable, str(script), "--check"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Uninitialized submodules" in result.stdout
        assert "repos/reporting" in result.stdout


def test_scaffold_skills_yaml_has_persona_policy():
    """skills.yaml ships a persona-scoped governance block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        data = yaml.safe_load(
            (meta_repo / ".platform" / "config" / "skills.yaml").read_text())

        assert "personas" in data
        for pid in ("default", "dev", "qa", "ba", "sm", "domain"):
            assert pid in data["personas"]
            assert "allow" in data["personas"][pid]
            assert "deny" in data["personas"][pid]
        # QA is allow-list only (deny baseline); dev is unrestricted.
        assert data["personas"]["qa"]["deny"] == ["*"]
        assert data["personas"]["dev"]["allow"] == ["*"]


def test_makefile_passes_persona_flag():
    """Makefile threads PERSONA through skills/validate for governance scoping."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        makefile = (output_dir / "domain-test-domain-meta" / "Makefile").read_text()
        assert "PERSONA_FLAG" in makefile
        assert "--persona" in makefile


def test_profiler_persona_fresh_scaffold_is_green():
    """A fresh scaffold has no governance violations for any builtin persona."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        for pid in ("dev", "qa", "ba", "sm", "domain"):
            _seed_skill(meta_repo, f".agents/skills/personas/{pid}", pid, "persona")
        _seed_skill(
            meta_repo, "repos/domain-context/skills/sync", "facility-sync", "Sync")
        _seed_skill(meta_repo, ".agents/skills/water", "water-check", "Water")

        script = meta_repo / ".platform" / "scripts" / "profile_skills.py"
        for pid in ("dev", "qa", "ba", "sm", "domain"):
            result = subprocess.run(
                [sys.executable, str(script), "--check", "--persona", pid],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"persona {pid} unexpectedly failed"


def test_profiler_persona_reports_out_of_policy():
    """An allow-list persona sees non-granted skills as out-of-policy, not denied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        _seed_skill(meta_repo, ".agents/skills/personas/qa", "qa", "QA persona")
        _seed_skill(meta_repo, "repos/app/.skills/deploy", "prod-deploy", "Deploy")

        script = meta_repo / ".platform" / "scripts" / "profile_skills.py"
        result = subprocess.run(
            [sys.executable, str(script), "--check", "--persona", "qa"],
            capture_output=True, text=True,
        )
        # No explicit deny hit => advisory only, gate passes.
        assert result.returncode == 0
        assert "out-of-policy" in result.stdout
        assert "prod-deploy" in result.stdout


def test_profiler_persona_gate_fails_on_explicit_deny():
    """An explicitly denied loaded skill fails the validate gate for that persona."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        scaffold_domain_meta_repo(
            output_dir=output_dir, domain="test-domain", product="TEST",
            git_init=False,
        )
        meta_repo = output_dir / "domain-test-domain-meta"
        _seed_skill(meta_repo, ".agents/skills/personas/dev", "dev", "Dev persona")
        _seed_skill(meta_repo, "repos/app/.skills/deploy", "prod-deploy", "Deploy")
        # Author a deliberate deny: dev must never use prod-deploy.
        sy = meta_repo / ".platform" / "config" / "skills.yaml"
        sy.write_text(sy.read_text().replace(
            "  dev:\n    allow: ['*']\n    deny: []",
            "  dev:\n    allow: ['*']\n    deny: [prod-deploy]"))

        script = meta_repo / ".platform" / "scripts" / "profile_skills.py"
        result = subprocess.run(
            [sys.executable, str(script), "--check", "--persona", "dev"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "Governance violation" in result.stdout
        assert "prod-deploy" in result.stdout


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
