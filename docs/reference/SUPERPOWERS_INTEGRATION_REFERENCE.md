# Superpowers Integration Reference

## Overview

This document maps the superpowers project structure and explains how to integrate its skills framework into domain-specific repos.

**Superpowers Repo**: https://github.com/venkatchinta/superpowers (fork of obra/superpowers)

---

## Superpowers Project Structure

```
superpowers/
├── README.md                    # Main methodology guide
├── .github/
│   ├── workflows/              # CI/CD workflows
│   └── ISSUE_TEMPLATE/         # Issue templates
├── skills/                      # ← SKILLS FRAMEWORK (what we integrate)
│   ├── registry.json           # Skills registry metadata
│   ├── README.md               # Skills documentation
│   ├── pr-reviewer/            # Example skill
│   │   ├── SKILL.md            # Skill definition
│   │   ├── config.json         # Skill configuration
│   │   ├── prompts/            # LLM prompts
│   │   ├── tools/              # Helper tools
│   │   └── tests/              # Skill tests
│   ├── test-generator/         # Example skill
│   ├── doc-generator/          # Example skill
│   └── [other-skills]/
├── workflows/                   # Development workflows
│   ├── code-review.md
│   ├── testing.md
│   ├── deployment.md
│   └── [other-workflows]
├── templates/                   # Project templates
│   ├── python-project/
│   ├── nodejs-project/
│   └── [other-templates]
└── docs/                        # Documentation
    ├── METHODOLOGY.md
    ├── SKILL_DEVELOPMENT.md
    ├── BEST_PRACTICES.md
    └── [other-docs]
```

---

## Skills Framework Structure

### registry.json
Metadata about all available skills:

```json
{
  "version": "1.0",
  "skills": [
    {
      "name": "pr-reviewer",
      "description": "Automated code review for pull requests",
      "version": "1.0.0",
      "tags": ["code-review", "automation", "quality"],
      "tech_stack": ["python", "git", "github"],
      "mcp_requirements": ["bitbucket-mcp", "github-mcp"],
      "config_schema": {
        "review_rules": ["string"],
        "auto_approve_threshold": "number"
      }
    },
    {
      "name": "test-generator",
      "description": "Auto-generate unit tests from code",
      "version": "1.0.0",
      "tags": ["testing", "automation", "quality"],
      "tech_stack": ["python", "pytest", "unittest"],
      "mcp_requirements": [],
      "config_schema": {
        "test_framework": "string",
        "coverage_threshold": "number"
      }
    }
  ]
}
```

### Individual Skill Structure

Each skill is a directory with:

```
pr-reviewer/
├── SKILL.md                     # Skill definition (frontmatter + description)
├── config.json                  # Default configuration
├── prompts/
│   ├── system.md               # System prompt for LLM
│   ├── review-template.md      # Review template
│   └── [other-prompts]
├── tools/
│   ├── code_analyzer.py        # Helper tool
│   ├── rule_engine.py          # Rule evaluation
│   └── [other-tools]
├── tests/
│   ├── test_pr_reviewer.py
│   ├── fixtures/
│   └── [test-files]
└── README.md                    # Skill-specific documentation
```

### SKILL.md Format

```markdown
---
name: pr-reviewer
version: 1.0.0
description: Automated code review for pull requests
tags: [code-review, automation, quality]
tech_stack: [python, git, github]
mcp_requirements: [bitbucket-mcp]
config_schema:
  review_rules:
    type: array
    description: List of code review rules to enforce
  auto_approve_threshold:
    type: number
    description: Confidence threshold for auto-approval
---

# PR Reviewer Skill

## Overview
Automatically reviews pull requests using AI-powered analysis...

## Configuration
```json
{
  "review_rules": ["no-hardcoded-secrets", "test-coverage-minimum"],
  "auto_approve_threshold": 0.95
}
```

## Usage
...

## Examples
...
```

---

## Integration Points

### 1. Skills Discovery
When integrating superpowers, we need to:
- Clone superpowers repo (or reference as submodule)
- Parse `skills/registry.json`
- Discover all skill directories
- Load SKILL.md metadata from each

### 2. Skill Metadata Extraction
For each skill, extract:
- Name, version, description
- Tags (for categorization)
- Tech stack requirements
- MCP server dependencies
- Configuration schema

### 3. Domain-Specific Customization
When forking a skill for a domain:
- Copy skill directory to domain-context-repo
- Modify `config.json` with domain-specific settings
- Update prompts in `prompts/` for domain context
- Add domain-specific tools in `tools/`
- Create domain-specific tests

### 4. Skill Validation
Track validation against real development tasks:
- Which skills were tested
- On which projects/PRs
- Validation results (works/needs-tuning/broken)
- Feedback and notes
- Configuration changes made

---

## Mapping to MyAgentPG

### Current Skills Registry (MyAgentPG)
Location: `skills/` (separate repo)

```
skills/
├── registry.json
├── project-context/
├── domain-context/
├── [other-skills]
└── README.md
```

### Integration Strategy

**Option A: Git Submodule** (Recommended)
- Domain-context-repo includes superpowers as submodule
- Allows independent updates
- Clear separation of baseline vs. domain-specific

```
domain-context-repo/
├── .skills/
│   ├── superpowers/           ← Git submodule to superpowers
│   │   └── skills/
│   │       ├── pr-reviewer/
│   │       ├── test-generator/
│   │       └── [others]
│   ├── pr-reviewer-domain/    ← Domain-customized fork
│   ├── test-generator-domain/ ← Domain-customized fork
│   └── [domain-specific-skills]
├── .domain/
│   ├── skills-manifest.json
│   ├── skills-evolution.json
│   └── [other-domain-files]
└── README.md
```

**Option B: Copy & Track**
- Copy superpowers skills into domain-context-repo
- Track changes separately
- Harder to sync with upstream

### Code Onboard Integration

When onboarding a repo with domain context:

```bash
keel code onboard --path ./my-repo \
  --domain cwow-facility \
  --domain-context-repo <url> \
  --use-domain-skills
```

**Flow**:
1. Clone domain-context-repo
2. Load domain skills from `.skills/`
3. Load superpowers skills from `.skills/superpowers/` (submodule)
4. Match skills based on project analysis
5. Prioritize domain-customized skills
6. Install matched skills into repo

---

## Superpowers Workflows

Beyond skills, superpowers defines development workflows:

```
workflows/
├── code-review.md              # Code review process
├── testing.md                  # Testing strategy
├── deployment.md               # Deployment workflow
├── documentation.md            # Doc generation workflow
└── [other-workflows]
```

### Integration Approach

**Phase 1** (Current): Focus on skills injection

**Phase 2** (Future): Integrate workflows
- Copy workflow definitions to domain-context-repo
- Customize for domain-specific requirements
- Reference in domain README

Example:
```markdown
# Domain Workflows

## Code Review
See [superpowers code-review workflow](../../../.skills/superpowers/workflows/code-review.md)

Domain customizations:
- Require 2 approvals for facility-critical code
- Auto-assign to facility domain experts
```

---

## Skill Compatibility Matrix

### Tech Stack Matching
When onboarding a repo, match skills based on:
- Language (Python, JavaScript, Java, etc.)
- Framework (Django, FastAPI, React, etc.)
- Testing framework (pytest, Jest, JUnit, etc.)
- CI/CD platform (GitHub Actions, GitLab CI, etc.)

### MCP Requirements
Some skills require MCP servers:
- `pr-reviewer` → needs Bitbucket/GitHub MCP
- `test-generator` → no MCP required
- `doc-generator` → no MCP required

Verify MCP servers are available before installing skill.

---

## Validation Checklist for Integration

Before integrating superpowers skills into a domain:

- [ ] Clone superpowers repo and review structure
- [ ] Parse `skills/registry.json` successfully
- [ ] Load all SKILL.md files correctly
- [ ] Understand skill configuration schema
- [ ] Identify which skills apply to domain
- [ ] Plan customization strategy for each skill
- [ ] Set up git submodule integration
- [ ] Create validation roadmap
- [ ] Test skill injection in test domain
- [ ] Document domain-specific configurations

---

## Example: Integrating PR-Reviewer Skill

### Step 1: Discover Skill
```
superpowers/skills/pr-reviewer/
├── SKILL.md
├── config.json
├── prompts/
│   ├── system.md
│   └── review-template.md
├── tools/
│   ├── code_analyzer.py
│   └── rule_engine.py
└── tests/
```

### Step 2: Extract Metadata
From `SKILL.md`:
- Name: `pr-reviewer`
- Version: `1.0.0`
- Description: Automated code review
- Tags: `[code-review, automation]`
- Tech Stack: `[python, git]`
- MCP Requirements: `[bitbucket-mcp]`

### Step 3: Validate for Domain
- Does domain use Bitbucket? ✓
- Do domain repos need code review automation? ✓
- Are there domain-specific review rules? Yes → plan customization

### Step 4: Customize for Domain
Create `pr-reviewer-domain/`:
```
pr-reviewer-domain/
├── SKILL.md                    # Updated with domain info
├── config.json                 # Domain-specific rules
├── prompts/
│   ├── system.md              # Domain-specific system prompt
│   └── review-template.md     # Domain-specific template
├── tools/
│   ├── code_analyzer.py       # (copied from superpowers)
│   ├── rule_engine.py         # (copied from superpowers)
│   └── facility_rules.py      # NEW: Domain-specific rules
└── CUSTOMIZATION_NOTES.md     # Document changes
```

### Step 5: Validate Against Real Task
```bash
keel domain validate-skills cwow-facility \
  --skill pr-reviewer-domain \
  --task "Review PR #123 in cwow-facility-service" \
  --feedback "works" \
  --notes "Correctly identified 3 facility-specific issues"
```

### Step 6: Track Evolution
`skills-evolution.json` records:
- When skill was forked
- What was customized
- Validation results
- Ready for contribution back to superpowers

---

## Future: Contributing Back

Once a domain-customized skill is validated across multiple projects:

```bash
keel domain contribute-skill cwow-facility \
  --skill pr-reviewer-domain \
  --upstream-skill pr-reviewer \
  --message "Add facility-domain code review rules"
```

This generates:
- Git patch comparing domain vs. upstream
- GitHub PR template with validation results
- Link to submit back to superpowers

If merged upstream, domain can switch back to using upstream version:
```bash
git submodule update --remote .skills/superpowers
```

---

## References

- **Superpowers Repo**: https://github.com/venkatchinta/superpowers
- **Superpowers Methodology**: See `superpowers/docs/METHODOLOGY.md`
- **Skill Development Guide**: See `superpowers/docs/SKILL_DEVELOPMENT.md`
- **MyAgentPG Domain Context**: See `docs/plans/DOMAIN_SKILLS_INTEGRATION_PLAN.md`
