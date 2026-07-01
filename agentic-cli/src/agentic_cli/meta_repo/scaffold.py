"""Scaffold domain meta-repo directory structure."""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from .config import DomainConfig, GovernanceConfig, RepoConfig, SkillsConfig
from .git_utils import register_submodule, resolve_remote_shas

logger = logging.getLogger(__name__)


def scaffold_domain_meta_repo(
    output_dir: Path,
    domain: str,
    product: str,
    description: str = "",
    owner: str = "",
    context_repo_url: Optional[str] = None,
    product_meta_url: Optional[str] = None,
    repos: Optional[list[dict]] = None,
    git_init: bool = True,
    code_assist_tool: str = "generic",
    personas: Optional[list] = None,
    persona_context: Optional[dict] = None,
    enrich_personas: bool = False,
    clone_repos: bool = False,
    write_blueprint: bool = True,
) -> dict[str, Path]:
    """Create domain meta-repo directory structure.

    Args:
        output_dir: Parent directory where meta-repo will be created
        domain: Domain slug (e.g., "cwow-facility")
        product: Product name (e.g., "CWOW")
        description: Domain description
        owner: Domain owner email
        context_repo_url: Git URL of domain-context-repo (optional)
        repos: List of linked repo configs (optional)
        git_init: Initialize as git repo with submodules
        code_assist_tool: Code assist tool (windsurf, cursor, or generic)
        personas: Resolved list of PersonaSpec to generate into
            ``.agents/skills/personas/<id>/SKILL.md`` (optional)
        persona_context: Domain context dict (from gather_domain_context) used
            to render personas. Required for persona generation.
        enrich_personas: Whether to AI-enrich custom personas marked ai_enrich.

    Returns:
        Dictionary mapping directory names to created paths.

    Raises:
        ValueError: If output_dir doesn't exist or is not writable
        RuntimeError: If git operations fail
    """
    if not output_dir.exists():
        raise ValueError(f"Output directory does not exist: {output_dir}")

    meta_repo_name = f"domain-{domain}-meta"
    meta_repo_path = output_dir / meta_repo_name

    if meta_repo_path.exists():
        raise ValueError(f"Meta-repo already exists: {meta_repo_path}")

    created = {}

    try:
        # Create root directory
        meta_repo_path.mkdir(parents=True, exist_ok=True)
        created["root"] = meta_repo_path

        # Create .platform directory structure
        platform_dir = meta_repo_path / ".platform"
        platform_dir.mkdir(exist_ok=True)
        created["platform"] = platform_dir

        config_dir = platform_dir / "config"
        config_dir.mkdir(exist_ok=True)
        created["config"] = config_dir

        common_dir = platform_dir / "common"
        common_dir.mkdir(exist_ok=True)
        created["common"] = common_dir

        # Create .agents directory structure
        agents_dir = meta_repo_path / ".agents"
        agents_dir.mkdir(exist_ok=True)
        created["agents"] = agents_dir

        agents_subdir = agents_dir / "agents"
        agents_subdir.mkdir(exist_ok=True)
        created["agents_subdir"] = agents_subdir

        skills_subdir = agents_dir / "skills"
        skills_subdir.mkdir(exist_ok=True)
        created["skills_subdir"] = skills_subdir

        # Create repos directory (for submodules)
        repos_dir = meta_repo_path / "repos"
        repos_dir.mkdir(exist_ok=True)
        created["repos"] = repos_dir

        # Create docs directory
        docs_dir = meta_repo_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        created["docs"] = docs_dir

        # Create plans directory (gitignored)
        plans_dir = meta_repo_path / "plans"
        plans_dir.mkdir(exist_ok=True)
        created["plans"] = plans_dir

        # Create .githooks directory
        githooks_dir = meta_repo_path / ".githooks"
        githooks_dir.mkdir(exist_ok=True)
        created["githooks"] = githooks_dir

        # Write configuration files
        _write_domain_config(config_dir, domain, product, description, owner)
        _write_repos_config(config_dir, repos or [])
        _write_governance_config(config_dir)
        _write_skills_config(config_dir)

        # Write platform common files
        _write_platform_common(common_dir)
        _write_platform_readme(platform_dir, domain)

        # Write documentation files
        _write_docs(meta_repo_path, domain, product, description)

        # Write root-level docs (README.md, AGENTS.md) per meta-repo standards
        _write_root_readme(meta_repo_path, domain, product, description)
        _write_agents_md(meta_repo_path, domain)

        # Generate persona skills into .agents/skills/personas/<id>/SKILL.md
        if personas and persona_context:
            persona_paths = _generate_personas(
                skills_subdir, personas, persona_context, enrich_personas
            )
            if persona_paths:
                created["personas"] = skills_subdir / "personas"

        # Write git hooks (pre-push branch-naming enforcement)
        _write_pre_push_hook(githooks_dir)

        # Write Makefile
        _write_makefile(meta_repo_path)

        # Write .gitignore
        _write_gitignore(meta_repo_path)

        # Write the Devin DRS snapshot blueprint (.devin/environment.yaml +
        # setup.sh). Generated here so it is captured in the initial commit;
        # the snapshot itself is built later via `dva domain build-snapshot`.
        if write_blueprint:
            from agentic_cli.devin.blueprint import (
                load_workspace_mcp_servers,
                write_domain_blueprint,
            )

            bp = write_domain_blueprint(
                meta_repo_path,
                domain,
                product,
                code_assist_tool=code_assist_tool,
                mcp_servers=load_workspace_mcp_servers(),
            )
            created["devin_blueprint"] = bp["environment"]

        # Initialize git repository if requested
        if git_init:
            _init_git_repo(
                meta_repo_path, context_repo_url, repos or [], product_meta_url,
                clone_repos=clone_repos,
            )

        logger.info(f"Created domain meta-repo at {meta_repo_path}")
        return created

    except Exception as e:
        logger.error(f"Failed to scaffold meta-repo: {e}")
        raise


def _write_domain_config(
    config_dir: Path, domain: str, product: str, description: str, owner: str
) -> None:
    """Write domain.yaml configuration file."""
    config = DomainConfig(
        domain=domain,
        product=product,
        description=description,
        owner=owner,
        created_at=datetime.utcnow().isoformat() + "Z",
    )

    config_file = config_dir / "domain.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote domain config: {config_file}")


def _write_repos_config(config_dir: Path, repos: list[dict]) -> None:
    """Write repos.yaml configuration file."""
    repos_config = {"repos": repos}

    config_file = config_dir / "repos.yaml"
    with open(config_file, "w") as f:
        yaml.dump(repos_config, f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote repos config: {config_file}")


def _write_governance_config(config_dir: Path) -> None:
    """Write governance.yaml configuration file."""
    governance = GovernanceConfig()

    config_file = config_dir / "governance.yaml"
    with open(config_file, "w") as f:
        yaml.dump(governance.to_dict(), f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote governance config: {config_file}")


def _write_skills_config(config_dir: Path) -> None:
    """Write skills.yaml configuration file."""
    skills = SkillsConfig()

    config_file = config_dir / "skills.yaml"
    with open(config_file, "w") as f:
        yaml.dump(skills.to_dict(), f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote skills config: {config_file}")


def _generate_personas(
    skills_subdir: Path,
    personas: list,
    persona_context: dict,
    enrich: bool,
) -> dict:
    """Render persona skills into .agents/skills/personas/<id>/SKILL.md.

    Lazy-imported to avoid an import cycle during meta_repo package init.
    """
    from agentic_cli.skill_generator import generate_personas

    personas_dir = skills_subdir / "personas"
    written = generate_personas(personas, persona_context, personas_dir, enrich=enrich)
    logger.debug("Generated %d persona skills in %s", len(written), personas_dir)
    return written


def _write_platform_common(common_dir: Path) -> None:
    """Write platform common files."""
    # __init__.py
    init_file = common_dir / "__init__.py"
    init_file.write_text('"""Platform common utilities."""\n')

    # config_loader.py
    config_loader_file = common_dir / "config_loader.py"
    config_loader_file.write_text(
        '''"""Load and parse platform configuration files."""

import yaml
from pathlib import Path
from typing import Any


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config(config_dir: Path, filename: str) -> dict[str, Any]:
    """Load config file from .platform/config/."""
    return load_yaml(config_dir / filename)
'''
    )

    logger.debug(f"Wrote platform common files to {common_dir}")


def _write_docs(meta_repo_path: Path, domain: str, product: str, description: str) -> None:
    """Write documentation files."""
    docs_dir = meta_repo_path / "docs"

    # README.md
    readme_file = docs_dir / "README.md"
    readme_file.write_text(
        f"""# {domain.upper()} Domain Meta-Repo

**Product**: {product}
**Domain**: {domain}

{description or "Domain-specific repository for managing code, skills, and governance."}

## Quick Start

```bash
# Initialize submodules
make init

# Update all submodules
make update

# Validate repo state
make validate
```

## Structure

- `.platform/config/` — Domain configuration (domain.yaml, repos.yaml, governance.yaml, skills.yaml)
- `.agents/` — Domain-specific agents and skills
- `repos/` — Git submodules for linked domain repositories
- `docs/` — Documentation
- `plans/` — Local design specs (gitignored)

## Linked Repositories

See `.platform/config/repos.yaml` for the list of linked domain repositories.

## Governance

See `.platform/config/governance.yaml` for domain governance rules.

## Skills

See `.platform/config/skills.yaml` for domain skills configuration.

## Getting Help

- Read `ONBOARDING.md` for repo onboarding guide
- Read `GOVERNANCE.md` for branch/workflow rules
- Read `ARCHITECTURE.md` for domain architecture
""",
        encoding="utf-8",
    )

    # ONBOARDING.md
    onboarding_file = docs_dir / "ONBOARDING.md"
    onboarding_file.write_text(
        f"""# {domain.upper()} Repository Onboarding Guide

This guide explains how to onboard a new repository into the {domain} domain.

## Prerequisites

- Git installed
- `dva` CLI installed
- Access to domain repositories

## Onboarding Steps

### 1. Clone the Repository

```bash
git clone <repo-url> <local-path>
cd <local-path>
```

### 2. Run Code Onboard

```bash
dva code onboard --path . --domain {domain} --link-meta-repo --use-domain-skills
```

This will:
- Detect and link the domain meta-repo
- Load domain-specific configurations
- Install domain-validated skills
- Generate project-context skill
- Create onboard manifest

### 3. Verify Installation

```bash
# Check .skills directory
ls -la .skills/

# Review onboard manifest
cat .onboard-manifest.json
```

## Domain-Specific Configuration

The domain meta-repo provides:
- **Domain settings** — `.platform/config/domain.yaml`
- **Linked repos** — `.platform/config/repos.yaml`
- **Governance rules** — `.platform/config/governance.yaml`
- **Skills config** — `.platform/config/skills.yaml`

## Support

For issues or questions, contact the domain owner or team.
""",
        encoding="utf-8",
    )

    # GOVERNANCE.md
    governance_file = docs_dir / "GOVERNANCE.md"
    governance_file.write_text(
        f"""# {domain.upper()} Governance Rules

This document outlines the governance rules for the {domain} domain.

## Branch Naming Convention

Branches must follow the pattern:
```
<type>/<JIRA-ID>-<kebab-case-description>
```

Examples:
- `feat/CWOW-123-add-water-quality-check`
- `fix/CWOW-456-resolve-facility-sync-bug`
- `docs/CWOW-789-update-api-docs`

## Pre-Push Hooks

All repositories must have pre-push hooks installed to enforce:
- Branch naming convention
- Commit message format
- Code quality checks

## CI/CD Gates

All code must pass:
- SAST (Static Application Security Testing)
- SCA (Software Composition Analysis)
- Unit tests (minimum 80% coverage)
- Code review (minimum 1 reviewer)

## Code Review

All pull requests require:
- Minimum 1 reviewer approval
- All conversations resolved
- CI/CD gates passing

## Submodule Management

- Submodules are pinned to specific commits
- Updates require explicit commits to parent repo
- Use `make update` to update all submodules

## Questions?

Contact the domain owner for clarification on governance rules.
""",
        encoding="utf-8",
    )

    # ARCHITECTURE.md
    architecture_file = docs_dir / "ARCHITECTURE.md"
    architecture_file.write_text(
        f"""# {domain.upper()} Domain Architecture

This document describes the architecture of the {domain} domain.

## Overview

The {domain} domain consists of multiple repositories organized as git submodules
in this meta-repo. Each repository serves a specific purpose.

## Repositories

See `.platform/config/repos.yaml` for the list of repositories and their descriptions.

## Skills

Domain-specific skills are managed in the domain-context-repo (linked as a submodule).

Skills are organized by:
- **Validated skills** — Tested and approved for domain use
- **Customized skills** — Forked from superpowers and tailored for domain
- **Injected skills** — Baseline skills from superpowers

## Configuration

Domain configuration is centralized in `.platform/config/`:
- `domain.yaml` — Domain metadata
- `repos.yaml` — Linked repositories
- `governance.yaml` — Governance rules
- `skills.yaml` — Skills configuration

## Development Workflow

1. Create a feature branch following naming convention
2. Make changes in your repository
3. Commit and push to feature branch
4. Create pull request
5. Get review approval
6. Merge to main

See `GOVERNANCE.md` for detailed governance rules.

## Deployment

Deployment procedures are repository-specific. See individual repository documentation.

## Support

For architecture questions, contact the domain owner.
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote documentation files to {docs_dir}")


def _write_makefile(meta_repo_path: Path) -> None:
    """Write Makefile with automation targets."""
    makefile_path = meta_repo_path / "Makefile"
    makefile_path.write_text(
        """.PHONY: init update update-one validate setup-hooks help

init: setup-hooks
	@echo "Initializing domain meta-repo (shallow, parallel)..."
	git -c protocol.file.allow=always submodule update --init --recursive --depth 1 --jobs 8
	@echo "✓ Submodules initialized"

update:
	@echo "Updating all submodules..."
	git submodule update --remote --merge
	@echo "✓ Submodules updated"

update-one:
	@if [ -z "$(REPO)" ]; then \\
		echo "Usage: make update-one REPO=repos/<name>"; \\
		exit 1; \\
	fi
	@echo "Updating submodule $(REPO)..."
	git submodule update --remote --merge "$(REPO)"
	@echo "✓ Submodule $(REPO) updated"

setup-hooks:
	@if [ -d ".githooks" ]; then \\
		git config core.hooksPath .githooks; \\
		chmod +x .githooks/* 2>/dev/null || true; \\
		echo "✓ Git hooks configured (core.hooksPath=.githooks)"; \\
	fi

validate:
	@echo "Validating repo state..."
	@if [ -d ".platform/config" ]; then \\
		echo "✓ .platform/config exists"; \\
	else \\
		echo "✗ .platform/config missing"; \\
		exit 1; \\
	fi
	@if [ -d "repos" ]; then \\
		echo "✓ repos directory exists"; \\
	else \\
		echo "✗ repos directory missing"; \\
		exit 1; \\
	fi
	@echo "✓ Validation passed"

help:
	@echo "Domain Meta-Repo Targets:"
	@echo "  make init        - Configure hooks + initialize submodules"
	@echo "  make update      - Update all submodules"
	@echo "  make update-one  - Update one submodule (REPO=repos/<name>)"
	@echo "  make setup-hooks - Configure git hooks path"
	@echo "  make validate    - Validate repo state"
	@echo "  make help        - Show this help message"
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote Makefile to {meta_repo_path}")


def _write_platform_readme(platform_dir: Path, domain: str) -> None:
    """Write .platform/README.md documenting config structure."""
    readme = platform_dir / "README.md"
    readme.write_text(
        f"""# .platform — Centralized Configuration

This directory holds all platform-wide configuration and shared utilities for
the **{domain}** domain meta-repo.

## Structure

- `config/` — YAML configuration files
  - `domain.yaml` — Domain metadata (product, owner, tags)
  - `repos.yaml` — Linked repositories (slug, clone_url, languages)
  - `governance.yaml` — Branch naming, review, and CI/CD rules
  - `skills.yaml` — Domain skill validation and priority rules
- `common/` — Shared Python utilities
  - `config_loader.py` — Helpers to load YAML configs

## Usage

```python
from pathlib import Path
from common.config_loader import load_config

config_dir = Path(__file__).parent / "config"
domain_cfg = load_config(config_dir, "domain.yaml")
repos_cfg = load_config(config_dir, "repos.yaml")
```

These configs are consumed by the `dva code onboard --use-meta-config` workflow.
""",
        encoding="utf-8",
    )
    logger.debug(f"Wrote .platform/README.md to {platform_dir}")


def _write_root_readme(
    meta_repo_path: Path, domain: str, product: str, description: str
) -> None:
    """Write root README.md per meta-repo standards."""
    readme = meta_repo_path / "README.md"
    readme.write_text(
        f"""# {domain} Domain Meta-Repo

**Product**: {product}

{description or "Meta-repository orchestrating code, skills, and governance for this domain."}

## Quickstart

```bash
make init        # Configure hooks + initialize submodules
make validate    # Validate repo state
make update      # Update all submodules
```

## Layout

| Path | Purpose |
|------|---------|
| `.platform/` | Centralized configs and shared utilities |
| `.agents/` | Agent and skill definitions (modular, discoverable) |
| `repos/` | Submodules (domain-context + linked repos) |
| `plans/` | Local-only design specs (gitignored) |
| `docs/` | Onboarding, governance, architecture guides |
| `.githooks/` | Git hooks (pre-push branch-naming enforcement) |
| `Makefile` | Automation targets |

## Documentation

- [AGENTS.md](AGENTS.md) — Agent/skill architecture and submodule workflow
- [docs/ONBOARDING.md](docs/ONBOARDING.md) — Repo onboarding guide
- [docs/GOVERNANCE.md](docs/GOVERNANCE.md) — Branch/workflow rules
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Domain architecture
- [.platform/README.md](.platform/README.md) — Config structure
""",
        encoding="utf-8",
    )
    logger.debug(f"Wrote root README.md to {meta_repo_path}")


def _write_agents_md(meta_repo_path: Path, domain: str) -> None:
    """Write AGENTS.md explaining agent/skill architecture and governance."""
    agents_md = meta_repo_path / "AGENTS.md"
    agents_md.write_text(
        f"""# Agents & Skills — {domain}

This document explains how agents and skills are organized in this meta-repo and
how they integrate with the submodule workflow and governance.

## Agent & Skill Discovery

- **Agents** live in `.agents/agents/` — each agent is a self-contained project.
- **Skills** live in `.agents/skills/` — each skill has a `SKILL.md` plus optional
  references and scripts.
- Domain-validated skills are sourced from the `repos/domain-context` submodule
  and prioritized during `dva code onboard --use-domain-skills`.

## Skill Priority Order

Defined in `.platform/config/skills.yaml`:

1. **validated** — Tested and approved for this domain (highest)
2. **customized** — Forked from superpowers and tailored
3. **injected** — Superpowers baseline (lowest)

## Submodule Workflow

1. Make changes inside the submodule first, commit there.
2. Update the parent meta-repo to point at the new submodule commit.
3. Pin submodules to specific commits (never floating branches in production).

```bash
make update-one REPO=repos/<name>   # Update a single submodule
make update                         # Update all submodules
```

## Governance

- Branch naming and review rules are enforced via `.githooks/pre-push` and CI.
- See `docs/GOVERNANCE.md` for the full ruleset.
- Never commit secrets or `.env` files.
""",
        encoding="utf-8",
    )
    logger.debug(f"Wrote AGENTS.md to {meta_repo_path}")


def _write_pre_push_hook(githooks_dir: Path) -> None:
    """Write a pre-push hook that enforces branch naming conventions."""
    hook = githooks_dir / "pre-push"
    hook.write_text(
        """#!/usr/bin/env bash
# Pre-push hook: enforce branch naming convention.
# Pattern: <type>/<JIRA-ID>-<kebab-case-description>
# Types: feat, fix, docs, style, refactor, test, chore

set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"

# Allow main/master/develop
if [[ "$branch" =~ ^(main|master|develop)$ ]]; then
  exit 0
fi

pattern='^(feat|fix|docs|style|refactor|test|chore)/[A-Z]+-[0-9]+-.+$'
if [[ ! "$branch" =~ $pattern ]]; then
  echo "✗ Branch name '$branch' does not match required pattern:" >&2
  echo "  <type>/<JIRA-ID>-<kebab-case-description>" >&2
  echo "  e.g. feat/CWOW-123-add-water-quality-check" >&2
  exit 1
fi

exit 0
""",
        encoding="utf-8",
    )
    try:
        hook.chmod(0o755)
    except OSError:
        pass
    logger.debug(f"Wrote pre-push hook to {githooks_dir}")


def _write_gitignore(meta_repo_path: Path) -> None:
    """Write .gitignore file."""
    gitignore_path = meta_repo_path / ".gitignore"
    gitignore_path.write_text(
        """# Local development
plans/
*.local
.DS_Store
.vscode/
.idea/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build artifacts
dist/
build/
*.egg-info/
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote .gitignore to {meta_repo_path}")


def _init_git_repo(
    meta_repo_path: Path,
    context_repo_url: Optional[str],
    repos: list[dict],
    product_meta_url: Optional[str] = None,
    *,
    clone_repos: bool = False,
) -> None:
    """Initialize git repository with submodules.

    By default, submodules are *registered* (``.gitmodules`` + pinned gitlink)
    without cloning — the working trees are fetched lazily via ``make init``
    (``git submodule update --init``). This keeps scaffolding fast even for
    domains with many linked repos. Pinned commit SHAs are resolved up-front in
    parallel with clone-free ``git ls-remote`` calls.

    Args:
        meta_repo_path: Path to meta-repo
        context_repo_url: Git URL of domain-context-repo (optional)
        repos: List of linked repo configs
        product_meta_url: Git URL/path of the product meta-repo (outer-loop
            shared tier) to reference as a submodule (optional)
        clone_repos: If True, also clone the submodule working trees now
            (shallow + parallel). If False (default), defer to ``make init``.

    Raises:
        RuntimeError: If git operations fail
    """
    try:
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )
        logger.debug(f"Initialized git repo at {meta_repo_path}")

        # Activate git hooks (branch-naming enforcement)
        if (meta_repo_path / ".githooks").exists():
            subprocess.run(
                ["git", "config", "core.hooksPath", ".githooks"],
                cwd=str(meta_repo_path),
                check=True,
                capture_output=True,
            )
            logger.debug("Configured core.hooksPath=.githooks")

        # Stage the scaffold files FIRST. This must happen before submodule
        # gitlinks are staged: `git add .` stages the deletion of any tracked
        # path missing from the working tree, which would clobber the gitlinks
        # for the (intentionally un-cloned) submodules registered below.
        subprocess.run(
            ["git", "add", "."],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )

        # Build the full submodule spec list: (path, url, branch).
        specs: list[tuple[str, str, Optional[str]]] = []
        if context_repo_url:
            specs.append(("repos/domain-context", context_repo_url, None))
        if product_meta_url:
            specs.append(("repos/product-meta", product_meta_url, None))
        for repo in repos:
            repo_slug = repo.get("slug")
            clone_url = repo.get("clone_url")
            if repo_slug and clone_url:
                specs.append((f"repos/{repo_slug}", clone_url, repo.get("branch")))

        # Resolve pinned commit SHAs in parallel WITHOUT cloning. This replaces
        # N sequential full clones with N cheap, concurrent `ls-remote` calls.
        sha_map = resolve_remote_shas([(p, u, b) for p, u, b in specs])

        for path, url, branch in specs:
            resolved = sha_map.get(path)
            sha = resolved[0] if resolved else None
            eff_branch = (resolved[1] if resolved else None) or branch
            register_submodule(meta_repo_path, url, path, sha=sha, branch=eff_branch)
            if not sha:
                logger.warning(
                    f"Could not resolve a commit for {url}; recorded pointer only "
                    f"(fetch later with `git submodule update --init --remote {path}`)."
                )

        # Stage only .gitmodules (the gitlinks were already staged via
        # update-index inside register_submodule). Avoid `git add .` here.
        if specs:
            subprocess.run(
                ["git", "add", ".gitmodules"],
                cwd=str(meta_repo_path),
                check=True,
                capture_output=True,
            )

        # Initial commit
        subprocess.run(
            ["git", "commit", "-m", "Initial commit: domain meta-repo scaffold"],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )
        logger.debug("Created initial git commit")

        # Optionally fetch the working trees now (shallow + parallel). This is
        # the same operation as `make init`, just run inline when requested.
        if clone_repos and specs:
            logger.debug("Cloning submodule working trees (shallow, parallel)...")
            subprocess.run(
                [
                    "git", "-c", "protocol.file.allow=always",
                    "submodule", "update", "--init", "--recursive",
                    "--depth", "1", "--jobs", "8",
                ],
                cwd=str(meta_repo_path),
                check=False,  # best-effort; pointers remain valid if a fetch fails
                capture_output=True,
            )

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        raise RuntimeError(f"Git operation failed: {stderr}")
