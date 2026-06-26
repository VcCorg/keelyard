# Domain-Specific Skills Integration Plan

## Objective

Integrate the **superpowers** project's standardized skills framework and development methodology into the domain context creation workflow. When creating a new domain-specific common repo, automatically inject validated skills from superpowers, then evolve them based on domain-specific development tasks.

---

## Current State Analysis

### MyAgentPG (This Project)
- **Code Onboard Flow**: `dva code onboard --path <repo> [--domain <slug>] [--kg]`
  - Analyzes project tech stack
  - Matches skills from registry
  - Generates project-context skill
  - Optionally ingests into KG
  - Optionally attaches domain context

- **Domain Context**: `dva domain init-context <slug>`
  - Creates central domain-context repo
  - Scaffolds `.domain/`, `.skills/shared/`, `README.md`
  - Generates domain-context skill from KG
  - Git submodule reference pattern

- **Skills Registry**: Local `skills/` repo with `registry.json` + skill definitions

### Superpowers (Reference Project)
- **Methodology**: Agentic skills framework + software development methodology
- **Skills**: Standardized, validated skills for common development tasks
- **Workflows**: Defined best practices and development patterns
- **Extensibility**: Skills designed to be forked/customized per domain

---

## Integration Strategy

### Phase 1: Superpowers Skills as Domain Baseline (Week 1)

**Goal**: When creating a domain-specific repo, inject superpowers skills as the starting point.

#### 1.1 Extend `domain init-context` Command
Add a new flag to bootstrap skills from superpowers:

```bash
dva domain init-context <domain-slug> \
  --git-remote <domain-context-repo-url> \
  --bootstrap-skills superpowers \
  --superpowers-url https://github.com/venkatchinta/superpowers.git
```

**What it does**:
- Creates domain-context repo structure (existing behavior)
- Clones superpowers skills into `.skills/superpowers/` as a git submodule
- Generates a `SKILLS_MANIFEST.md` listing all injected skills
- Creates a `SKILLS_VALIDATION_ROADMAP.md` for tracking skill validation against domain tasks

#### 1.2 Skills Injection Logic
Create new module: `agentic_cli/kg/domain_skills.py`

```python
def bootstrap_domain_skills(
    domain_slug: str,
    domain_context_repo_path: Path,
    superpowers_url: str = "https://github.com/venkatchinta/superpowers.git",
    skills_to_inject: Optional[List[str]] = None,  # None = all
) -> Dict[str, Any]:
    """
    Inject superpowers skills into domain-context repo.
    
    Returns:
        {
            "injected_skills": ["skill1", "skill2", ...],
            "manifest_path": Path,
            "validation_roadmap_path": Path,
        }
    """
    # 1. Clone superpowers repo (or use local copy)
    # 2. Discover skills in superpowers/.skills/
    # 3. Filter by skills_to_inject if provided
    # 4. Add as git submodule: .skills/superpowers/
    # 5. Generate SKILLS_MANIFEST.md
    # 6. Generate SKILLS_VALIDATION_ROADMAP.md
    # 7. Return metadata
```

#### 1.3 Generated Artifacts

**SKILLS_MANIFEST.md** (in domain-context repo):
```markdown
# Domain Skills Manifest

## Superpowers Skills (Injected)

| Skill | Purpose | Status | Validation Date |
|-------|---------|--------|-----------------|
| pr-reviewer | Code review automation | Injected | — |
| test-generator | Auto-generate tests | Injected | — |
| doc-generator | Generate docs | Injected | — |
| ... | ... | ... | ... |

## Domain-Specific Skills (Custom)

| Skill | Purpose | Status | Validation Date |
|-------|---------|--------|-----------------|
| ... | ... | ... | ... |

## Validation Status
- Total injected: N
- Validated: M
- Pending: N-M
```

**SKILLS_VALIDATION_ROADMAP.md** (in domain-context repo):
```markdown
# Skills Validation Roadmap

## Validation Process
1. Run skill against real domain development task
2. Collect feedback (works/needs-tuning/broken)
3. Update skill parameters or fork for domain
4. Mark as validated in SKILLS_MANIFEST.md

## Validation Checklist

### pr-reviewer
- [ ] Tested on 5 real PRs in domain repos
- [ ] Feedback: [notes]
- [ ] Status: [validated/needs-tuning/broken]
- [ ] Domain-specific config: [if any]

### test-generator
- [ ] Tested on domain codebase
- [ ] Feedback: [notes]
- [ ] Status: [validated/needs-tuning/broken]
- [ ] Domain-specific config: [if any]

...
```

---

### Phase 2: Domain-Specific Skill Customization (Week 2-3)

**Goal**: Evolve injected skills based on domain-specific development tasks.

#### 2.1 Skill Validation Workflow
Create new command: `dva domain validate-skills`

```bash
# Validate a specific skill against a task
dva domain validate-skills <domain-slug> \
  --skill pr-reviewer \
  --task "Review PR #123 in cwow-facility-service" \
  --feedback "works|needs-tuning|broken" \
  --notes "Feedback notes"

# List validation status
dva domain validate-skills <domain-slug> --list

# Generate validation report
dva domain validate-skills <domain-slug> --report
```

**Implementation**: `agentic_cli/commands/domain.py` → new subcommand

#### 2.2 Skill Forking for Domain
When a skill needs domain-specific tuning:

```bash
# Fork a superpowers skill for domain customization
dva domain fork-skill <domain-slug> \
  --skill pr-reviewer \
  --reason "Add domain-specific code review rules"
```

**What it does**:
- Copies `superpowers/.skills/pr-reviewer/` → `.skills/pr-reviewer-domain/`
- Updates `SKILLS_MANIFEST.md` to mark as "Domain-Customized"
- Creates `SKILL_CUSTOMIZATION_NOTES.md` documenting changes
- Generates a diff template for tracking changes vs. upstream

#### 2.3 Skill Evolution Tracking
Create: `agentic_cli/kg/skill_evolution.py`

```python
def track_skill_evolution(
    domain_slug: str,
    skill_name: str,
    changes: Dict[str, Any],  # What was changed
    validation_result: str,   # "validated" | "needs-tuning" | "broken"
    notes: str,
) -> None:
    """
    Track skill evolution over time.
    
    Stores in: domain-context-repo/.domain/skills-evolution.json
    
    Enables:
    - Skill version history
    - Comparison with upstream superpowers
    - Rollback capability
    - Contribution back to superpowers
    """
```

---

### Phase 3: Code Onboard Integration (Week 3-4)

**Goal**: When onboarding repos into a domain, automatically inject domain-validated skills.

#### 3.1 Extend `code onboard` Command
Add domain-aware skill injection:

```bash
# Onboard repo with domain-validated skills
dva code onboard --path ./cwow-facility-service \
  --domain cwow-facility \
  --use-domain-skills

# Or explicitly:
dva code onboard --path ./cwow-facility-service \
  --domain cwow-facility \
  --domain-context-repo https://github.com/company/cwow-facility-domain-context.git \
  --use-domain-skills
```

**What it does**:
1. Analyzes project (existing behavior)
2. Matches skills from registry (existing behavior)
3. **NEW**: Also matches domain-validated skills from domain-context-repo
4. **NEW**: Prioritizes domain-validated skills over generic registry skills
5. Installs both generic + domain skills
6. Generates `.skills/domain-skills/SKILL.md` listing domain-specific skills

#### 3.2 Domain Skills Priority Logic
In `agentic_cli/analyzer/matcher.py`:

```python
def match_skills_with_domain(
    analysis: ProjectAnalysis,
    registry_data: Dict,
    domain_context_repo: Optional[Path] = None,
    domain_slug: Optional[str] = None,
) -> List[SkillMatch]:
    """
    Match skills with domain-aware prioritization.
    
    Priority order:
    1. Domain-validated skills (from domain-context-repo)
    2. Domain-customized skills (forked from superpowers)
    3. Generic registry skills
    4. Superpowers baseline skills
    """
    matches = []
    
    # Load domain skills if domain context provided
    domain_skills = {}
    if domain_context_repo:
        domain_skills = _load_domain_skills(domain_context_repo)
    
    # Match in priority order
    for skill_name, skill_def in domain_skills.items():
        if _matches_project(skill_def, analysis):
            matches.append(SkillMatch(
                name=skill_name,
                source="domain",
                priority=1,  # Highest
                ...
            ))
    
    # Then generic registry skills
    for skill_name, skill_def in registry_data.items():
        if _matches_project(skill_def, analysis):
            matches.append(SkillMatch(
                name=skill_name,
                source="registry",
                priority=2,
                ...
            ))
    
    return sorted(matches, key=lambda m: m.priority)
```

---

### Phase 4: Skill Contribution Back to Superpowers (Week 4-5)

**Goal**: Enable domain-validated skills to be contributed back to superpowers.

#### 4.1 Contribution Workflow
New command: `dva domain contribute-skill`

```bash
# Propose a domain-customized skill back to superpowers
dva domain contribute-skill <domain-slug> \
  --skill pr-reviewer-domain \
  --upstream-skill pr-reviewer \
  --message "Add domain-specific code review rules for facility domain"
```

**What it does**:
1. Generates a git patch comparing domain skill vs. upstream
2. Creates a GitHub PR template with:
   - Skill name & domain
   - Validation results
   - Use cases & benefits
   - Diff vs. upstream
3. Outputs PR URL for manual review & submission

#### 4.2 Skill Merge Strategy
Document in: `doc/SKILL_CONTRIBUTION_GUIDE.md`

```markdown
# Contributing Domain Skills Back to Superpowers

## When to Contribute
- Skill is validated across 3+ domain projects
- Skill solves a general problem (not domain-specific)
- Skill improves on upstream version

## Contribution Process
1. Run `dva domain contribute-skill`
2. Review generated patch
3. Submit PR to superpowers repo
4. Superpowers maintainers review & merge
5. Update domain-context-repo to reference upstream version

## Keeping in Sync
After contribution is merged:
```bash
# Update domain-context-repo to use upstream
git submodule update --remote .skills/superpowers
```
```

---

## Implementation Roadmap

### Week 1: Phase 1 (Superpowers Skills Injection)
- [ ] Create `agentic_cli/kg/domain_skills.py`
- [ ] Extend `domain init-context` with `--bootstrap-skills` flag
- [ ] Implement git submodule addition for superpowers
- [ ] Generate SKILLS_MANIFEST.md & SKILLS_VALIDATION_ROADMAP.md
- [ ] Tests: 8 tests for skill injection logic

### Week 2: Phase 2 (Skill Customization)
- [ ] Create `dva domain validate-skills` command
- [ ] Create `dva domain fork-skill` command
- [ ] Create `agentic_cli/kg/skill_evolution.py`
- [ ] Implement skill evolution tracking
- [ ] Tests: 12 tests for validation & forking

### Week 3: Phase 3 (Code Onboard Integration)
- [ ] Extend `code onboard` with `--use-domain-skills` flag
- [ ] Enhance `agentic_cli/analyzer/matcher.py` with domain-aware matching
- [ ] Update skill installation logic to prioritize domain skills
- [ ] Tests: 10 tests for domain-aware matching

### Week 4: Phase 4 (Contribution Workflow)
- [ ] Create `dva domain contribute-skill` command
- [ ] Implement patch generation & PR template
- [ ] Create contribution guide documentation
- [ ] Tests: 6 tests for contribution workflow

### Week 5: Integration & Polish
- [ ] End-to-end testing across all phases
- [ ] Update workflows (`.windsurf/workflows/domain-context.md`)
- [ ] Create user guide: `doc/DOMAIN_SKILLS_USER_GUIDE.md`
- [ ] Performance optimization & edge case handling

---

## Data Structures

### Domain Skills Metadata
File: `.domain/skills-manifest.json`

```json
{
  "domain": "cwow-facility",
  "created_at": "2026-05-07T12:00:00Z",
  "superpowers_version": "main",
  "skills": {
    "pr-reviewer": {
      "source": "superpowers",
      "status": "injected",
      "validated": false,
      "validation_date": null,
      "customized": false,
      "notes": ""
    },
    "pr-reviewer-domain": {
      "source": "superpowers",
      "status": "forked",
      "validated": true,
      "validation_date": "2026-05-15T10:30:00Z",
      "customized": true,
      "customization_reason": "Add domain-specific code review rules",
      "upstream_version": "pr-reviewer",
      "notes": "Validated on 5 PRs in cwow-facility-service"
    }
  }
}
```

### Skill Evolution Log
File: `.domain/skills-evolution.json`

```json
{
  "pr-reviewer-domain": [
    {
      "timestamp": "2026-05-15T10:30:00Z",
      "event": "forked",
      "upstream": "pr-reviewer",
      "reason": "Add domain-specific code review rules"
    },
    {
      "timestamp": "2026-05-16T14:20:00Z",
      "event": "validated",
      "validation_result": "works",
      "notes": "Tested on PR #123, #124, #125 in cwow-facility-service",
      "changes": {
        "config": {
          "review_rules": ["facility-specific-rule-1", "facility-specific-rule-2"]
        }
      }
    },
    {
      "timestamp": "2026-05-20T09:00:00Z",
      "event": "contributed",
      "pr_url": "https://github.com/obra/superpowers/pull/42",
      "status": "pending"
    }
  ]
}
```

---

## CLI Command Summary

```bash
# Phase 1: Bootstrap
dva domain init-context <slug> \
  --bootstrap-skills superpowers \
  --superpowers-url <url>

# Phase 2: Validate & Customize
dva domain validate-skills <slug> --skill <name> --task <desc> --feedback <result>
dva domain validate-skills <slug> --list
dva domain validate-skills <slug> --report
dva domain fork-skill <slug> --skill <name> --reason <reason>

# Phase 3: Onboard with Domain Skills
dva code onboard --path <repo> --domain <slug> --use-domain-skills

# Phase 4: Contribute Back
dva domain contribute-skill <slug> --skill <name> --upstream-skill <name>
```

---

## Success Metrics

1. **Skill Injection**: Domain-context repos created with superpowers skills in <2 minutes
2. **Validation**: Skills validated against real tasks within 1 week of domain creation
3. **Adoption**: 80%+ of domain repos use domain-validated skills
4. **Contribution**: 1+ domain-customized skills contributed back to superpowers per domain
5. **Maintenance**: Upstream superpowers updates merged into domain skills within 1 month

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Superpowers repo structure changes | Pin to specific commit; maintain compatibility layer |
| Skill conflicts between domains | Namespace skills by domain; clear naming convention |
| Validation takes too long | Provide quick-start validation checklist; automate where possible |
| Contribution process is complex | Generate PR automatically; provide clear guide |
| Skill drift from upstream | Track evolution; provide merge/sync commands |

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Validate superpowers structure** — clone repo and map skill locations
3. **Prototype Phase 1** — implement skill injection in a test domain
4. **Iterate based on feedback** — adjust plan as needed
5. **Begin Week 1 implementation**
