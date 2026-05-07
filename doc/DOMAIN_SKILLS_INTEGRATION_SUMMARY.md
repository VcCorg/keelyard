# Domain Skills Integration — Executive Summary

## Vision

Create a **standardized, evolving skills framework** for domain-specific development by:
1. **Injecting** validated skills from superpowers as a baseline
2. **Validating** skills against real domain development tasks
3. **Customizing** skills for domain-specific requirements
4. **Contributing** validated skills back to superpowers

---

## The Problem We're Solving

| Current State | Desired State |
|---|---|
| Each domain starts from scratch | Each domain starts with proven skills |
| Skills are ad-hoc and inconsistent | Skills follow superpowers methodology |
| No validation process | Skills validated against real tasks |
| No feedback loop to superpowers | Domain innovations flow back upstream |
| Repos onboarded with generic skills | Repos onboarded with domain-validated skills |

---

## High-Level Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CREATE DOMAIN-CONTEXT REPO                                   │
│    dva domain init-context cwow-facility --bootstrap-skills     │
│                                                                  │
│    ✓ Scaffolds .domain/, .skills/, README.md                   │
│    ✓ Injects superpowers skills as git submodule               │
│    ✓ Generates SKILLS_MANIFEST.md (validation roadmap)         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. VALIDATE & CUSTOMIZE SKILLS                                  │
│    dva domain validate-skills cwow-facility \                   │
│      --skill pr-reviewer --task "Review PR #123" --feedback ok  │
│    dva domain fork-skill cwow-facility --skill pr-reviewer      │
│                                                                  │
│    ✓ Test skills against real development tasks                │
│    ✓ Fork skills that need domain customization                │
│    ✓ Track evolution in skills-evolution.json                  │
│    ✓ Update SKILLS_MANIFEST.md with validation status          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ONBOARD REPOS WITH DOMAIN SKILLS                             │
│    dva code onboard --path ./cwow-facility-service \            │
│      --domain cwow-facility --use-domain-skills                 │
│                                                                  │
│    ✓ Analyzes project tech stack                               │
│    ✓ Matches domain-validated skills (priority 1)              │
│    ✓ Matches domain-customized skills (priority 2)             │
│    ✓ Falls back to generic registry skills (priority 3)        │
│    ✓ Installs matched skills into repo                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. CONTRIBUTE VALIDATED SKILLS BACK                              │
│    dva domain contribute-skill cwow-facility \                  │
│      --skill pr-reviewer-domain --upstream-skill pr-reviewer    │
│                                                                  │
│    ✓ Generates git patch vs. upstream                          │
│    ✓ Creates GitHub PR with validation results                 │
│    ✓ Enables superpowers to benefit from domain innovations    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Domain-Context Repo Structure
```
domain-context-repo/
├── .skills/
│   ├── superpowers/              ← Git submodule (baseline)
│   │   └── skills/
│   │       ├── pr-reviewer/
│   │       ├── test-generator/
│   │       └── [others]
│   ├── pr-reviewer-domain/       ← Customized for domain
│   ├── test-generator-domain/    ← Customized for domain
│   └── [domain-specific-skills]
├── .domain/
│   ├── skills-manifest.json      ← Validation status
│   ├── skills-evolution.json     ← Change history
│   ├── kg-context.md
│   └── [other-domain-files]
└── README.md
```

### 2. Skills Manifest
Tracks validation status of all skills:

```json
{
  "pr-reviewer": {
    "source": "superpowers",
    "status": "injected",
    "validated": false
  },
  "pr-reviewer-domain": {
    "source": "superpowers",
    "status": "forked",
    "validated": true,
    "validation_date": "2026-05-15",
    "notes": "Validated on 5 PRs"
  }
}
```

### 3. Skills Evolution Log
Tracks changes over time:

```json
{
  "pr-reviewer-domain": [
    {
      "timestamp": "2026-05-15T10:30:00Z",
      "event": "forked",
      "reason": "Add domain-specific code review rules"
    },
    {
      "timestamp": "2026-05-16T14:20:00Z",
      "event": "validated",
      "result": "works",
      "notes": "Tested on 5 PRs"
    },
    {
      "timestamp": "2026-05-20T09:00:00Z",
      "event": "contributed",
      "pr_url": "https://github.com/obra/superpowers/pull/42"
    }
  ]
}
```

---

## Implementation Timeline

| Phase | Week | Focus | Deliverables |
|-------|------|-------|--------------|
| 1 | Week 1 | Skill Injection | `domain init-context --bootstrap-skills` |
| 2 | Week 2-3 | Validation & Customization | `domain validate-skills`, `domain fork-skill` |
| 3 | Week 3-4 | Code Onboard Integration | `code onboard --use-domain-skills` |
| 4 | Week 4-5 | Contribution Workflow | `domain contribute-skill` |
| 5 | Week 5 | Integration & Polish | End-to-end testing, docs, optimization |

---

## CLI Commands (Summary)

### Bootstrap Phase
```bash
# Create domain-context repo with superpowers skills
dva domain init-context cwow-facility \
  --git-remote https://github.com/company/cwow-facility-domain-context.git \
  --bootstrap-skills superpowers
```

### Validation Phase
```bash
# Validate a skill against a real task
dva domain validate-skills cwow-facility \
  --skill pr-reviewer \
  --task "Review PR #123 in cwow-facility-service" \
  --feedback "works" \
  --notes "Correctly identified 3 issues"

# List validation status
dva domain validate-skills cwow-facility --list

# Generate validation report
dva domain validate-skills cwow-facility --report

# Fork a skill for domain customization
dva domain fork-skill cwow-facility \
  --skill pr-reviewer \
  --reason "Add domain-specific code review rules"
```

### Onboarding Phase
```bash
# Onboard repo with domain-validated skills
dva code onboard --path ./cwow-facility-service \
  --domain cwow-facility \
  --use-domain-skills
```

### Contribution Phase
```bash
# Contribute validated skill back to superpowers
dva domain contribute-skill cwow-facility \
  --skill pr-reviewer-domain \
  --upstream-skill pr-reviewer \
  --message "Add facility-domain code review rules"
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Skill Injection Speed** | <2 min | Time to bootstrap domain-context repo |
| **Validation Turnaround** | <1 week | Time from domain creation to validated skills |
| **Skill Adoption** | 80%+ | % of domain repos using domain-validated skills |
| **Contribution Rate** | 1+ per domain | Domain-customized skills contributed back/year |
| **Upstream Sync** | <1 month | Time to merge superpowers updates |

---

## Benefits

### For Domain Teams
- ✓ Start with proven, validated skills
- ✓ Reduce time to productivity
- ✓ Ensure consistency across repos
- ✓ Evolve skills based on real feedback
- ✓ Contribute innovations back to community

### For Superpowers Project
- ✓ Receive validated, real-world improvements
- ✓ Grow ecosystem of domain-specific skills
- ✓ Build community of contributors
- ✓ Improve methodology through feedback loops

### For MyAgentPG Platform
- ✓ Standardized skill framework
- ✓ Clear validation & evolution process
- ✓ Seamless integration with code onboard
- ✓ Contribution mechanism for upstream
- ✓ Scalable to multiple domains

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Superpowers structure changes | Pin to commit; maintain compatibility layer |
| Skill conflicts between domains | Namespace by domain; clear naming convention |
| Validation takes too long | Provide quick-start checklist; automate tests |
| Contribution process is complex | Auto-generate PR; provide clear guide |
| Skill drift from upstream | Track evolution; provide sync commands |
| MCP dependency issues | Validate MCP availability before install |

---

## Next Steps

1. **Review & Approve Plan**
   - Stakeholder review of 4-phase approach
   - Feedback on timeline & scope

2. **Prototype Phase 1**
   - Implement skill injection
   - Test with superpowers repo
   - Validate git submodule approach

3. **Validate Superpowers Structure**
   - Clone repo and map skill locations
   - Understand registry.json format
   - Document any deviations from expected structure

4. **Begin Week 1 Implementation**
   - Create `agentic_cli/kg/domain_skills.py`
   - Extend `domain init-context` command
   - Write tests

---

## Documentation

For detailed information, see:

- **Full Plan**: `doc/DOMAIN_SKILLS_INTEGRATION_PLAN.md`
- **Superpowers Reference**: `doc/SUPERPOWERS_INTEGRATION_REFERENCE.md`
- **User Guide** (TBD): `doc/DOMAIN_SKILLS_USER_GUIDE.md`
- **Contribution Guide** (TBD): `doc/SKILL_CONTRIBUTION_GUIDE.md`

---

## Questions & Discussion

Key questions to address:

1. **Superpowers Compatibility**: Are there any breaking changes in superpowers structure we should know about?
2. **Validation Criteria**: What constitutes a "validated" skill? (# of tests, # of PRs, coverage %, etc.)
3. **Customization Scope**: How much domain customization is acceptable before a skill should be forked?
4. **Contribution Policy**: What's the bar for contributing skills back to superpowers?
5. **Timeline Feasibility**: Is 5-week timeline realistic given other priorities?

---

**Status**: Planning Phase ✓  
**Next Review**: After stakeholder feedback  
**Owner**: [Your Name]  
**Last Updated**: 2026-05-07
