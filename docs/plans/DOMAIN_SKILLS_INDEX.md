# Domain Skills Integration — Complete Documentation Index

## Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| **DOMAIN_SKILLS_INTEGRATION_SUMMARY.md** | Executive overview | Stakeholders, decision-makers |
| **DOMAIN_SKILLS_INTEGRATION_PLAN.md** | Detailed 4-phase plan | Project managers, architects |
| **SUPERPOWERS_INTEGRATION_REFERENCE.md** | Superpowers structure & mapping | Developers, integrators |
| **CODE_ONBOARD_WITH_DOMAIN_SKILLS.md** | Implementation guide for Phase 3 | Developers, engineers |

---

## Document Descriptions

### 1. DOMAIN_SKILLS_INTEGRATION_SUMMARY.md
**Length**: ~2 pages | **Read Time**: 5 minutes

**What it covers**:
- Vision & problem statement
- High-level workflow (visual flowchart)
- Key components (structure, manifests, logs)
- Implementation timeline (5 weeks)
- CLI commands summary
- Success metrics & benefits
- Risk mitigation

**Best for**: Getting a quick understanding of the entire initiative

**Key Takeaway**: 4-phase approach to inject, validate, customize, and contribute domain skills

---

### 2. DOMAIN_SKILLS_INTEGRATION_PLAN.md
**Length**: ~8 pages | **Read Time**: 20 minutes

**What it covers**:
- Current state analysis (MyAgentPG vs. Superpowers)
- Integration strategy (4 phases in detail)
- Phase 1: Superpowers skills as domain baseline
- Phase 2: Domain-specific skill customization
- Phase 3: Code onboard integration
- Phase 4: Skill contribution back to superpowers
- Implementation roadmap (week-by-week)
- Data structures (JSON schemas)
- CLI command summary
- Success metrics
- Risks & mitigations
- Next steps

**Best for**: Understanding the complete plan and implementation approach

**Key Takeaway**: Detailed roadmap for each phase with code examples and data structures

---

### 3. SUPERPOWERS_INTEGRATION_REFERENCE.md
**Length**: ~6 pages | **Read Time**: 15 minutes

**What it covers**:
- Superpowers project structure
- Skills framework structure
- registry.json format
- Individual skill structure (SKILL.md format)
- Integration points
- Mapping to MyAgentPG
- Git submodule vs. copy strategy
- Code onboard integration
- Superpowers workflows
- Skill compatibility matrix
- Validation checklist
- Example: Integrating pr-reviewer skill
- Future: Contributing back

**Best for**: Understanding superpowers structure and how to integrate it

**Key Takeaway**: Superpowers uses git submodules; skills are modular with SKILL.md metadata

---

### 4. CODE_ONBOARD_WITH_DOMAIN_SKILLS.md
**Length**: ~7 pages | **Read Time**: 18 minutes

**What it covers**:
- Current code onboard flow (visual)
- Enhanced flow with domain skills
- New flags: --domain, --use-domain-skills
- Code changes required (5 sections)
  - Extend command signature
  - Create domain skills loader
  - Enhance skill matching
  - Generate domain-skills skill
  - Update manifest
- Example usage scenario
- Resulting repo structure
- Testing strategy
- Backward compatibility
- Performance considerations
- Future enhancements

**Best for**: Developers implementing Phase 3 of the plan

**Key Takeaway**: Domain-aware skill matching with priority order: domain-validated > domain-customized > generic > superpowers

---

## Reading Paths

### For Stakeholders & Decision-Makers
1. **DOMAIN_SKILLS_INTEGRATION_SUMMARY.md** (5 min)
2. Questions? → **DOMAIN_SKILLS_INTEGRATION_PLAN.md** (20 min)

### For Project Managers
1. **DOMAIN_SKILLS_INTEGRATION_SUMMARY.md** (5 min)
2. **DOMAIN_SKILLS_INTEGRATION_PLAN.md** (20 min)
3. Focus on: Implementation timeline, success metrics, risks

### For Architects & Tech Leads
1. **DOMAIN_SKILLS_INTEGRATION_PLAN.md** (20 min)
2. **SUPERPOWERS_INTEGRATION_REFERENCE.md** (15 min)
3. **CODE_ONBOARD_WITH_DOMAIN_SKILLS.md** (18 min)

### For Developers (Phase 1)
1. **DOMAIN_SKILLS_INTEGRATION_PLAN.md** → Phase 1 section (5 min)
2. **SUPERPOWERS_INTEGRATION_REFERENCE.md** (15 min)
3. Start implementing skill injection

### For Developers (Phase 2)
1. **DOMAIN_SKILLS_INTEGRATION_PLAN.md** → Phase 2 section (5 min)
2. Implement validation & customization commands

### For Developers (Phase 3)
1. **CODE_ONBOARD_WITH_DOMAIN_SKILLS.md** (18 min)
2. Implement domain-aware skill matching

### For Developers (Phase 4)
1. **DOMAIN_SKILLS_INTEGRATION_PLAN.md** → Phase 4 section (5 min)
2. Implement contribution workflow

---

## Implementation Phases

### Phase 1: Skill Injection (Week 1)
**Documents to read**: 
- DOMAIN_SKILLS_INTEGRATION_PLAN.md → Phase 1
- SUPERPOWERS_INTEGRATION_REFERENCE.md → Integration Points

**Deliverable**: `domain init-context --bootstrap-skills`

**Key Files to Create**:
- `agentic_cli/kg/domain_skills.py`
- Tests for skill injection

---

### Phase 2: Validation & Customization (Week 2-3)
**Documents to read**:
- DOMAIN_SKILLS_INTEGRATION_PLAN.md → Phase 2
- SUPERPOWERS_INTEGRATION_REFERENCE.md → Skill Customization

**Deliverables**: 
- `domain validate-skills` command
- `domain fork-skill` command

**Key Files to Create**:
- `agentic_cli/commands/domain.py` → new subcommands
- `agentic_cli/kg/skill_evolution.py`

---

### Phase 3: Code Onboard Integration (Week 3-4)
**Documents to read**:
- CODE_ONBOARD_WITH_DOMAIN_SKILLS.md (entire document)
- DOMAIN_SKILLS_INTEGRATION_PLAN.md → Phase 3

**Deliverable**: `code onboard --domain --use-domain-skills`

**Key Files to Modify**:
- `agentic_cli/commands/code.py`
- `agentic_cli/analyzer/matcher.py`

---

### Phase 4: Contribution Workflow (Week 4-5)
**Documents to read**:
- DOMAIN_SKILLS_INTEGRATION_PLAN.md → Phase 4
- SUPERPOWERS_INTEGRATION_REFERENCE.md → Contributing Back

**Deliverable**: `domain contribute-skill` command

**Key Files to Create**:
- `agentic_cli/commands/domain.py` → new subcommand
- Contribution guide documentation

---

## Key Concepts

### Domain-Context Repository
Central repo that contains:
- Domain metadata (`.domain/`)
- Domain-validated skills (`.skills/`)
- Domain-customized skills (forked from superpowers)
- Git submodule to superpowers baseline skills
- Skills manifest & evolution log

### Skills Manifest
JSON file tracking validation status of all skills:
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
    "validation_date": "2026-05-15"
  }
}
```

### Skills Evolution Log
JSON file tracking changes to skills over time:
```json
{
  "pr-reviewer-domain": [
    {"timestamp": "...", "event": "forked", "reason": "..."},
    {"timestamp": "...", "event": "validated", "result": "works"},
    {"timestamp": "...", "event": "contributed", "pr_url": "..."}
  ]
}
```

### Skill Priority Order
When onboarding with domain skills:
1. **Domain-validated skills** (highest priority)
2. **Domain-customized skills** (forked from superpowers)
3. **Generic registry skills**
4. **Superpowers baseline skills** (lowest priority)

---

## CLI Commands Reference

### Bootstrap Phase
```bash
keel domain init-context <slug> \
  --bootstrap-skills superpowers \
  --superpowers-url <url>
```

### Validation Phase
```bash
keel domain validate-skills <slug> --skill <name> --task <desc> --feedback <result>
keel domain validate-skills <slug> --list
keel domain validate-skills <slug> --report
keel domain fork-skill <slug> --skill <name> --reason <reason>
```

### Onboarding Phase
```bash
keel code onboard --path <repo> --domain <slug> --use-domain-skills
```

### Contribution Phase
```bash
keel domain contribute-skill <slug> --skill <name> --upstream-skill <name>
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Skill Injection Speed | <2 minutes |
| Validation Turnaround | <1 week |
| Skill Adoption | 80%+ |
| Contribution Rate | 1+ per domain/year |
| Upstream Sync | <1 month |

---

## FAQ

**Q: Why use git submodules instead of copying skills?**
A: Submodules allow independent updates, clear separation of baseline vs. domain-specific, and easy sync with upstream superpowers.

**Q: What if superpowers repo structure changes?**
A: We pin to specific commits and maintain a compatibility layer. Breaking changes are documented.

**Q: How long does skill validation take?**
A: Typically 1-2 weeks per skill, depending on domain complexity. Quick-start checklists can accelerate this.

**Q: Can we contribute skills back to superpowers?**
A: Yes! Phase 4 includes a contribution workflow. Skills must be validated across 3+ projects and solve general problems.

**Q: What if a domain-customized skill conflicts with another domain?**
A: Skills are namespaced by domain (e.g., `pr-reviewer-cwow-facility`). Clear naming conventions prevent conflicts.

**Q: Is this backward compatible with existing code onboard?**
A: Yes. `code onboard` without `--domain` works exactly as before. Domain skills are an optional enhancement.

---

## Glossary

- **Domain**: A business domain (e.g., cwow-facility)
- **Domain-Context Repository**: Central repo containing domain metadata, skills, and KG context
- **Domain-Validated Skill**: A skill tested and approved for use in a domain
- **Domain-Customized Skill**: A skill forked from superpowers and modified for domain-specific needs
- **Superpowers**: Reference project providing standardized skills framework
- **Skills Manifest**: JSON file tracking validation status of all skills
- **Skills Evolution Log**: JSON file tracking changes to skills over time
- **Git Submodule**: Git mechanism for including external repos as subdirectories
- **Skill Priority**: Order in which skills are matched during onboarding

---

## Related Documents

- **Domain Context Workflow**: `.windsurf/workflows/domain-context.md`
- **Code Onboard Workflow**: `.windsurf/workflows/code-onboard.md` (TBD)
- **Skill Contribution Guide**: `docs/plans/SKILL_CONTRIBUTION_GUIDE.md` (TBD)
- **Domain Skills User Guide**: `docs/guides/DOMAIN_SKILLS_USER_GUIDE.md` (TBD)

---

## Document Maintenance

| Document | Last Updated | Owner | Status |
|----------|--------------|-------|--------|
| DOMAIN_SKILLS_INTEGRATION_SUMMARY.md | 2026-05-07 | [Owner] | Draft |
| DOMAIN_SKILLS_INTEGRATION_PLAN.md | 2026-05-07 | [Owner] | Draft |
| SUPERPOWERS_INTEGRATION_REFERENCE.md | 2026-05-07 | [Owner] | Draft |
| CODE_ONBOARD_WITH_DOMAIN_SKILLS.md | 2026-05-07 | [Owner] | Draft |
| DOMAIN_SKILLS_INDEX.md | 2026-05-07 | [Owner] | Draft |

---

## Next Steps

1. **Review all documents** with stakeholders
2. **Get approval** on 4-phase approach
3. **Validate superpowers structure** by cloning repo
4. **Prototype Phase 1** in test domain
5. **Begin Week 1 implementation**

---

**Status**: Planning Phase ✓  
**Next Review**: After stakeholder feedback  
**Last Updated**: 2026-05-07
