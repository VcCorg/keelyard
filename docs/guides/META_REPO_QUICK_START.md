# Domain Meta-Repo Quick Start Guide

## What is a Domain Meta-Repo?

A domain meta-repo is a git repository that orchestrates all resources for a domain:
- **Configuration** — Domain settings, linked repos, governance rules, skills config
- **Submodules** — Domain-context-repo and linked domain repositories
- **Documentation** — Onboarding guide, governance rules, architecture
- **Automation** — Makefile targets for initialization and validation

---

## Creating a Domain Meta-Repo

### Step 1: Register the Domain

First, ensure your domain is registered:

```bash
keel domain create cwow-facility --product CWOW
```

### Step 2: Create the Meta-Repo

```bash
keel domain init-meta cwow-facility
```

This creates a new directory: `domain-cwow-facility-meta/`

**With domain-context-repo as submodule:**

```bash
keel domain init-meta cwow-facility \
  --context-repo https://github.com/company/facility-domain-context.git
```

### Step 3: Initialize Submodules

```bash
cd domain-cwow-facility-meta
make init
```

---

## Using Domain Meta-Repo with Code Onboarding

### Detect and Link Meta-Repo

```bash
keel code onboard --path ./my-repo --domain cwow-facility --link-meta-repo
```

This will:
1. Detect the domain meta-repo
2. Add it as a git submodule at `.domain-meta/`
3. Continue with normal onboarding

### Full Onboarding with Domain Features

```bash
keel code onboard --path ./my-repo --domain cwow-facility \
  --link-meta-repo \
  --use-domain-skills \
  --kg
```

---

## Meta-Repo Structure

```
domain-cwow-facility-meta/
├── .platform/
│   ├── config/
│   │   ├── domain.yaml          # Domain metadata
│   │   ├── repos.yaml           # Linked repositories
│   │   ├── governance.yaml      # Governance rules
│   │   └── skills.yaml          # Skills configuration
│   └── common/
│       └── config_loader.py     # Config utilities
├── .agents/
│   ├── agents/                  # Domain-specific agents
│   └── skills/                  # Domain-specific skills
├── repos/
│   ├── domain-context           # Git submodule
│   ├── repo-1                   # Git submodule
│   └── repo-2                   # Git submodule
├── docs/
│   ├── README.md                # Domain overview
│   ├── ONBOARDING.md            # Onboarding guide
│   ├── GOVERNANCE.md            # Governance rules
│   └── ARCHITECTURE.md          # Architecture
├── Makefile                     # Automation targets
└── .gitignore
```

---

## Configuration Files

### domain.yaml

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

### repos.yaml

```yaml
repos:
  - slug: cwow-facility-watercheck
    clone_url: "https://github.com/company/cwow-facility-watercheck.git"
    description: "Water quality monitoring"
    languages: [python, typescript]
    status: active
  - slug: cwow-facility-api
    clone_url: "https://github.com/company/cwow-facility-api.git"
    description: "Facility API service"
    languages: [go]
    status: active
```

### governance.yaml

```yaml
branch_pattern: "^(feat|fix|docs|style|refactor|test|chore)/[A-Z]+-[0-9]+-.*$"
require_pre_push_hook: true
require_ci_gates: true
require_code_review: true
min_reviewers: 1
require_tests: true
test_coverage_min: 80.0
```

### skills.yaml

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

## Makefile Targets

```bash
# Initialize all submodules
make init

# Update all submodules to latest
make update

# Validate repo state
make validate

# Show help
make help
```

---

## Common Tasks

### Update All Submodules

```bash
cd domain-cwow-facility-meta
make update
```

### Add a New Linked Repository

1. Edit `.platform/config/repos.yaml`
2. Add new repo entry
3. Run `make init` to add submodule

### Customize Domain Governance Rules

1. Edit `.platform/config/governance.yaml`
2. Commit changes
3. Push to remote

### Add Domain-Specific Skills

1. Create skill in `.agents/skills/<skill-name>/`
2. Add `SKILL.md` with skill definition
3. Update `.platform/config/skills.yaml` if needed

---

## Troubleshooting

### Meta-Repo Not Detected

**Problem**: `--link-meta-repo` doesn't find the meta-repo

**Solution**: Ensure meta-repo is in standard location:
- `<workspace>/<domain>/domain-<domain>-meta/`
- Or use absolute path

### Submodule Add Fails

**Problem**: Git submodule add fails during onboarding

**Solution**: Ensure:
- Project is a git repository
- Meta-repo path is correct
- Git is installed and working

### Config Files Missing

**Problem**: Config files not found in `.platform/config/`

**Solution**: Ensure meta-repo was created with `keel domain init-meta`

---

## Next Steps

- **Phase 2** (coming soon): Config-driven onboarding
  - Read domain configs during onboarding
  - Apply domain-specific skill rules
  - Discover linked repos automatically

- **Phase 3** (coming soon): Governance validation
  - Validate against domain governance rules
  - Bulk onboard all linked repos

---

## References

- Plan: `.windsurf/plans/domain-meta-repo-integration-733edb.md`
- Domain skills: `docs/plans/DOMAIN_SKILLS_INTEGRATION_PLAN.md`
- Code onboarding: `docs/guides/CODE_ONBOARD_WITH_DOMAIN_SKILLS.md`
