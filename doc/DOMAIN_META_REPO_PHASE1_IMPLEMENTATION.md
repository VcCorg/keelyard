# Domain Meta-Repo Integration — Phase 1 Implementation

**Status**: ✅ COMPLETE
**Date**: 2026-06-02
**Phase**: Phase 1 (Scaffolding & Detection)

---

## Overview

Phase 1 implements the foundational domain meta-repo infrastructure and basic detection/linking into code onboarding. This enables teams to create domain-specific meta-repos that follow meta-repo standards and integrate with the existing code onboarding workflow.

---

## What Was Implemented

### 1. New Module: `agentic_cli/meta_repo/`

A complete meta-repo management module with four submodules:

#### 1.1 `detector.py` — Meta-Repo Detection
- **`detect_domain_meta_repo(domain_slug, search_paths)`** — Find meta-repo by standard naming convention
  - Searches: CWD, CWD parent, custom search paths
  - Returns: Path to meta-repo or None
  
- **`_is_valid_meta_repo(path)`** — Validate meta-repo structure
  - Checks for `.platform/config/` directory
  - Returns: True if valid, False otherwise
  
- **`is_git_initialized(path)`** — Check if repo is git-initialized
- **`has_submodules(path)`** — Check if repo has git submodules

#### 1.2 `config.py` — Configuration Management
- **`DomainConfig`** — Domain metadata (domain, product, description, owner, tags)
- **`RepoConfig`** — Linked repository config (slug, clone_url, description, languages, frameworks, status)
- **`GovernanceConfig`** — Governance rules (branch pattern, pre-push hooks, CI gates, reviewers, test coverage)
- **`SkillsConfig`** — Skills configuration (validation rules, priority order)
- **`MetaRepoConfig`** — Main config loader
  - Loads all YAML configs from `.platform/config/`
  - Provides access to domain, repos, governance, and skills configs
  - Exports to JSON/dict for programmatic use

#### 1.3 `scaffold.py` — Meta-Repo Scaffolding
- **`scaffold_domain_meta_repo(...)`** — Create complete meta-repo structure
  - Creates directories: `.platform/`, `.agents/`, `repos/`, `docs/`, `plans/`, `.githooks/`
  - Generates config files: `domain.yaml`, `repos.yaml`, `governance.yaml`, `skills.yaml`
  - Writes documentation: `README.md`, `ONBOARDING.md`, `GOVERNANCE.md`, `ARCHITECTURE.md`
  - Creates `Makefile` with init/update/validate targets
  - Initializes git repo with submodules (optional)
  - Returns: Dict of created paths

#### 1.4 `__init__.py` — Module Exports
- Exports: `detect_domain_meta_repo`, `MetaRepoConfig`, `scaffold_domain_meta_repo`

### 2. New CLI Command: `dva domain init-meta`

Creates a domain meta-repo with full structure and configuration.

**Usage**:
```bash
dva domain init-meta cwow-facility
dva domain init-meta cwow-facility --context-repo https://github.com/company/facility-domain-context.git
dva domain init-meta cwow-facility --output ./facility-meta
```

**Options**:
- `--output, -o` — Custom output directory (default: workspace/domain-name)
- `--context-repo` — Git URL of domain-context-repo to add as submodule
- `--git-init/--no-git-init` — Initialize as git repo with submodules (default: True)

**Output**:
- Domain meta-repo directory with full structure
- Configuration files populated with domain data
- Documentation files with getting started guide
- Git repo initialized with submodules (if --git-init)
- Next steps printed to console

### 3. Enhanced Code Onboarding: `--link-meta-repo` Flag

Adds meta-repo detection and linking to `dva code onboard` command.

**Usage**:
```bash
dva code onboard --path ./my-repo --domain cwow-facility --link-meta-repo
```

**Behavior**:
1. Detects domain meta-repo by standard naming convention
2. If found:
   - Prints detection message
   - Adds as git submodule at `.domain-meta/`
   - Records in onboard result
3. If not found:
   - Warns user
   - Suggests: `dva domain init-meta <domain>`
4. Continues with normal onboarding flow

**Integration Points**:
- Step 9c-meta in code onboard pipeline
- Runs after domain context attachment, before KG pipeline
- Non-blocking: failures don't stop onboarding

### 4. Test Suite

Three comprehensive test modules:

#### 4.1 `tests/test_meta_repo_detector.py`
- Tests for `_is_valid_meta_repo()` with valid/invalid structures
- Tests for `detect_domain_meta_repo()` in various locations
- Tests for `is_git_initialized()` and `has_submodules()`

#### 4.2 `tests/test_meta_repo_config.py`
- Tests for all config classes (Domain, Repo, Governance, Skills)
- Tests for `MetaRepoConfig` loading and validation
- Tests for config export to JSON/dict

#### 4.3 `tests/test_meta_repo_scaffold.py`
- Tests for directory structure creation
- Tests for config file generation
- Tests for documentation file creation
- Tests for Makefile and .gitignore
- Tests for error handling (already exists, invalid output dir)

---

## Directory Structure Created

```
domain-<slug>-meta/
├── .platform/
│   ├── config/
│   │   ├── domain.yaml          ← Domain metadata
│   │   ├── repos.yaml           ← Linked repositories
│   │   ├── governance.yaml      ← Governance rules
│   │   └── skills.yaml          ← Skills configuration
│   └── common/
│       ├── __init__.py
│       └── config_loader.py     ← Config loading utilities
├── .agents/
│   ├── agents/                  ← Domain-specific agents
│   └── skills/                  ← Domain-specific skills
├── repos/
│   ├── domain-context           ← Git submodule (domain-context-repo)
│   ├── repo-1                   ← Git submodule (linked domain repo)
│   └── repo-2                   ← Git submodule (linked domain repo)
├── docs/
│   ├── README.md                ← Domain overview
│   ├── ONBOARDING.md            ← Repo onboarding guide
│   ├── GOVERNANCE.md            ← Branch/workflow rules
│   └── ARCHITECTURE.md          ← Domain architecture
├── plans/                       ← Local design specs (gitignored)
├── .githooks/                   ← Git hooks (pre-push, etc.)
├── Makefile                     ← Automation targets
├── .gitignore
└── .gitmodules                  ← Git submodule definitions
```

---

## Configuration Files

### `domain.yaml`
```yaml
domain: cwow-facility
product: CWOW
description: "Facility management domain"
owner: "facility-team@company.com"
created_at: "2026-06-02T00:00:00Z"
tags:
  - critical
  - production
```

### `repos.yaml`
```yaml
repos:
  - slug: cwow-facility-watercheck
    clone_url: "https://github.com/company/cwow-facility-watercheck.git"
    description: "Water quality monitoring"
    languages: [python, typescript]
    frameworks: [fastapi, react]
    status: active
  - slug: cwow-facility-api
    clone_url: "https://github.com/company/cwow-facility-api.git"
    description: "Facility API service"
    languages: [go]
    status: active
```

### `governance.yaml`
```yaml
branch_pattern: "^(feat|fix|docs|style|refactor|test|chore)/[A-Z]+-[0-9]+-.*$"
require_pre_push_hook: true
require_ci_gates: true
require_code_review: true
min_reviewers: 1
require_tests: true
test_coverage_min: 80.0
```

### `skills.yaml`
```yaml
validation_required: true
auto_inject_superpowers: true
allow_custom_skills: true
skill_priority_order:
  - validated
  - customized
  - injected
```

---

## Usage Examples

### Create a Domain Meta-Repo

```bash
# Basic creation
dva domain init-meta cwow-facility

# With domain-context-repo as submodule
dva domain init-meta cwow-facility \
  --context-repo https://github.com/company/facility-domain-context.git

# Custom output location
dva domain init-meta cwow-facility --output ./my-meta-repo

# Without git initialization
dva domain init-meta cwow-facility --no-git-init
```

### Initialize Submodules

```bash
cd domain-cwow-facility-meta
make init          # Initialize all submodules
make update        # Update all submodules
make validate      # Validate repo state
```

### Onboard with Meta-Repo Detection

```bash
# Detect and link domain meta-repo
dva code onboard --path ./my-repo --domain cwow-facility --link-meta-repo

# Full onboarding with domain skills and meta-repo
dva code onboard --path ./my-repo --domain cwow-facility \
  --use-domain-skills --link-meta-repo --kg
```

---

## Integration with Existing Features

### Domain Context Repo
- Meta-repo can reference domain-context-repo as a submodule
- Domain-context-repo remains unchanged (skills, docs, KG context)
- Both repos work independently or together

### Code Onboarding
- `--link-meta-repo` flag integrates with existing onboarding flow
- Non-blocking: doesn't affect other onboarding steps
- Works with `--use-domain-skills`, `--kg`, `--link-kg`, etc.

### Domain Skills
- Meta-repo can contain domain-specific skills in `.agents/skills/`
- Complements domain-context-repo skills
- Skills priority: validated > customized > injected (unchanged)

### Knowledge Graph
- Meta-repo structure can be indexed by KG
- Domain metadata available for KG queries
- Future: KG-driven skill discovery

---

## Files Created/Modified

### New Files
- `agentic_cli/meta_repo/__init__.py`
- `agentic_cli/meta_repo/detector.py`
- `agentic_cli/meta_repo/config.py`
- `agentic_cli/meta_repo/scaffold.py`
- `tests/test_meta_repo_detector.py`
- `tests/test_meta_repo_config.py`
- `tests/test_meta_repo_scaffold.py`

### Modified Files
- `agentic_cli/commands/domain.py` — Added `init-meta` command
- `agentic_cli/commands/code.py` — Added `--link-meta-repo` flag and detection logic

---

## Testing

All modules tested with:
- Unit tests for detector, config, and scaffold
- Integration tests for full scaffolding flow
- Error handling tests (invalid paths, already exists, etc.)

**Test Results**: ✅ All tests passing

---

## Next Steps (Phase 2)

Phase 2 will add:
1. **Config-driven onboarding** — Code onboard reads domain configs and applies skill rules
2. **Submodule discovery** — Discover linked repos from `repos.yaml`
3. **Onboard manifest enhancement** — Include meta-repo context in manifest
4. **Skill rule engine** — Apply domain-specific skill matching logic

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate meta-repo** | Keeps domain-context-repo focused on skills/docs; meta-repo handles governance/CI/CD |
| **Standard naming** | `domain-<slug>-meta` enables automatic detection without configuration |
| **YAML-based config** | Human-readable, version-controllable, easy to extend |
| **Submodule-based repos** | Reproducible, pinned commits, clear dependency management |
| **Makefile automation** | Familiar to developers, works across platforms |
| **Non-blocking detection** | Failures don't stop onboarding; teams can adopt gradually |

---

## Success Criteria Met

✅ `dva domain init-meta` creates valid meta-repo structure in <30s
✅ Code onboard detects and links domain meta-repo
✅ All tests passing
✅ Documentation complete
✅ Integration with existing features verified

---

## Known Limitations & Future Work

1. **Git operations** — Requires git to be installed and initialized
2. **Submodule pinning** — Currently pins to main branch; future: configurable branches
3. **Governance enforcement** — Currently informational; future: CI/CD integration
4. **Cross-repo skills** — Not yet supported; future: Phase 2+
5. **Meta-repo versioning** — Not yet tracked; future: semantic versioning

---

## References

- Plan: `/Users/your-user/.windsurf/plans/domain-meta-repo-integration-733edb.md`
- Test-Set Guide: `/Users/your-user/Downloads/test-set-guide.txt`
- Domain Skills Integration: `doc/DOMAIN_SKILLS_INTEGRATION_PLAN.md`
- Code Onboard Documentation: `doc/CODE_ONBOARD_WITH_DOMAIN_SKILLS.md`
