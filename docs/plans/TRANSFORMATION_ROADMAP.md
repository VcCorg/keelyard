# Agentic Platform Transformation Roadmap

## Overview

Transform agentic-cli from **tool-focused** to **methodology-focused** agent platform, aligned with Superpowers reference architecture for code development and onboarding.

## Current State vs. Future State

### Current Architecture
```
Agent Playground (UI)
├─ Agents (run agents)
├─ Skills (tool integrations: Jira, Bitbucket, Confluence)
├─ Deployments (where to run)
├─ Activity (logs)
└─ NO governance, NO approval gates, NO methodology

CLI
├─ agent code onboard (basic analysis)
├─ agent skill create (template-based)
├─ agent skill install (from GitHub)
├─ agent skill list (installed only)
└─ NO structured workflows, NO checkpoints
```

### Future Architecture (Superpowers-Inspired)
```
Agent Playground (UI)
├─ Dashboard (overview)
├─ Agents (run agents)
├─ Skills (methodology + domain + tool integration)
├─ Methodologies (Development workflows)
├─ Approvals (Design/Planning review gates)
├─ Code Onboarding (Structured understanding)
├─ Deployments (multi-cloud deployment)
└─ Activity (logs + evidence trail)

CLI
├─ agent code onboard (structured analysis → questions → understanding doc → auto-skills)
├─ agent skill create (methodology-aware)
├─ agent skill install (from GitHub)
├─ agent skill generate (from code patterns)
├─ agent methodology apply (apply best-fit methodology)
└─ Full workflow with approval checkpoints
```

## Three Implementation Tracks

### Track 1: Code Onboarding (8-10 days)

**Goal:** Transform code onboarding into structured understanding with auto-skill generation

**Phases:**
```
1. Analyze codebase     (automated)
   ↓
2. Ask questions        (interactive)
   ↓
3. Generate doc         (AI-assisted)
   ↓
4. Create skills        (auto-generated)
   ↓
5. Apply methodology    (recommended)
```

**Output:**
- `.keel/codebase-understanding.md` - Structured understanding document
- 8-15 auto-generated domain-specific skills
- Methodology pack recommendation
- Approval checkpoints for major decisions

**Files to Create/Modify:**
```
Backend CLI:
├─ agentic_cli/commands/code.py (enhance code_onboard)
├─ agentic_cli/analysis/codebase_analyzer.py (NEW)
├─ agentic_cli/analysis/questionnaire.py (NEW)
├─ agentic_cli/analysis/understanding_generator.py (NEW)
├─ agentic_cli/analysis/skill_generator.py (NEW)
└─ agentic_cli/analysis/methodology_matcher.py (NEW)

Dashboard Backend:
├─ dashboard/backend/src/api/onboarding.py (NEW)
└─ dashboard/backend/src/services/onboarding_service.py (NEW)

Dashboard Frontend:
└─ dashboard/frontend/src/pages/CodeOnboarding.tsx (NEW)
```

**Success Criteria:**
- ✅ `agent code onboard <repo>` completes in < 5 minutes
- ✅ Generates 8+ accurate domain-specific skills
- ✅ Understanding document matches actual codebase
- ✅ Methodology pack recommendation is correct
- ✅ User can approve/reject at each phase

---

### Track 2: Approval Workflow Dashboard (5-7 days)

**Goal:** Add governance layer with design/planning review gates

**Features:**
```
Pending Approvals Panel
├─ Show pending reviews with countdown
├─ Quick actions: Approve, Reject, Ask Questions
└─ Escalation reminders

Design Review Modal
├─ Display agent's design proposal
├─ Show questions asked, user answers
├─ Display alternatives considered
└─ Approval/rejection with feedback

Planning Review Modal
├─ Display task breakdown
├─ Show estimated times, file paths
├─ Verification steps for each task
└─ Approval/rejection with feedback

Approval History Timeline
├─ Show all past approvals/rejections
├─ Timeline view with timestamps
├─ Feedback and reasoning captured
└─ Exportable audit trail
```

**Files to Create:**
```
Dashboard Frontend:
├─ src/pages/Approvals.tsx (NEW)
├─ src/components/ApprovalCard.tsx (NEW)
├─ src/components/ApprovalModal.tsx (NEW)
├─ src/components/ApprovalTimeline.tsx (NEW)
└─ src/lib/approval-types.ts (NEW)

Dashboard Backend:
├─ src/api/approvals.py (NEW)
├─ src/services/approval_service.py (NEW)
├─ src/models/approval.py (NEW)
└─ src/db/migrations/create_approvals_table.py (NEW)
```

**API Endpoints:**
```
GET    /api/approvals/pending
GET    /api/approvals/{id}
POST   /api/approvals/{id}/approve
POST   /api/approvals/{id}/reject
GET    /api/approvals/history
GET    /api/approvals/stats
```

**Success Criteria:**
- ✅ Pending approvals visible in UI immediately
- ✅ Approval/rejection with feedback captured
- ✅ Full audit trail stored (who, what, when, why)
- ✅ Approval history searchable and filterable
- ✅ Integrates with skill execution workflow

---

### Track 3: Methodology-Based Skills (12-15 days)

**Goal:** Transform skills from tool-focused to methodology-focused

**Current Skill Structure:**
```yaml
name: jira-skill
type: tool-integration
functions: [get-issues, create-issue, update-issue]
```

**New Skill Structure:**
```yaml
name: design-brainstorm-skill
type: methodology
domain: software-development
workflow_phases:
  - phase: questions (ask user for clarification)
  - phase: design (present design in sections)
  - phase: document (create design document)
approval_gates:
  - phase: design → requires user approval
  - phase: document → auto-pass
evidence: [questions, answers, design-doc, feedback]
```

**Key Changes:**

#### 1. Skill Definition Schema (Updated)
```yaml
---
name: {skill-name}
description: {description}

# Type of skill
type: methodology|domain|quality|tool  # NEW

# Domain classification
domain: backend-development|data-engineering|frontend|devops

# For methodology skills: orchestration flow
methodology:
  phases:
    - name: design
      description: Ask clarifying questions
      checkpoint: user-approval
      timeout: 2-hours
    - name: planning
      description: Create task breakdown
      checkpoint: user-approval
      timeout: 1-hour
    - name: execute
      description: Implement with TDD
      checkpoint: tests-pass
      checkpoint-blocking: true

# For domain skills: composition with other skills
composition:
  depends_on: [design-brainstorm-skill, test-driven-development-skill]
  orchestration: sequential|parallel
  
# Project context (learned from code onboarding)
context:
  project_name: order-management-backend
  tech_stack: [FastAPI, PostgreSQL, pytest]
  conventions:
    - Use dependency injection
    - Pydantic for validation
    - Minimum 80% coverage
  file_patterns:
    endpoints: "app/api/v1/endpoints/*.py"
    models: "app/models/*.py"
    tests: "tests/integration/test_*.py"
  examples:
    - path: "app/api/v1/endpoints/users.py"
      description: "Follow this endpoint pattern"
```

#### 2. Skill Execution with Checkpoints
```
Skill Invocation
├─ Phase 1 (Design)
│  ├─ Ask questions
│  ├─ Show design
│  └─ [CHECKPOINT] Wait for user approval
├─ Phase 2 (Planning)
│  ├─ Create tasks
│  ├─ Show breakdown
│  └─ [CHECKPOINT] Wait for user approval
├─ Phase 3 (Execute)
│  ├─ Run subagents per task
│  ├─ Enforce TDD
│  └─ [CHECKPOINT] All tests must pass
└─ Phase 4 (Review)
   ├─ Check code quality
   ├─ Verify conventions
   └─ [CHECKPOINT] Code review required
```

#### 3. Skill Taxonomy
```
Methodology Skills (Orchestrators)
├─ design-brainstorm-skill
├─ implementation-planning-skill
├─ test-driven-development-skill
├─ code-review-skill
├─ debugging-methodology-skill
├─ refactoring-methodology-skill
└─ documentation-methodology-skill

Domain Skills (Executors) - Backend
├─ fastapi-endpoint-development-skill
├─ sqlalchemy-orm-skill
├─ postgresql-migration-skill
├─ async-coroutine-skill
├─ error-handling-skill
├─ jwt-authentication-skill
└─ redis-caching-skill

Domain Skills - Frontend
├─ react-component-development-skill
├─ typescript-typing-skill
├─ tailwind-styling-skill
├─ e2e-testing-skill
└─ accessibility-skill

Domain Skills - Data
├─ data-pipeline-design-skill
├─ spark-sql-skill
├─ data-quality-skill
├─ lineage-tracking-skill
└─ dbt-modeling-skill

Quality Skills (Validators)
├─ code-coverage-validation-skill
├─ performance-validation-skill
├─ security-scanning-skill
├─ documentation-validation-skill
└─ accessibility-validation-skill

Tool Integration Skills (Connectors)
├─ jira-ticket-management-skill
├─ github-pr-management-skill
├─ slack-notification-skill
├─ datadog-monitoring-skill
└─ confluence-documentation-skill
```

**Files to Create/Modify:**
```
Backend CLI:
├─ agentic_cli/skill/models.py (update SkillDefinition)
├─ agentic_cli/skill/execution.py (NEW - with checkpoints)
├─ agentic_cli/skill/orchestrator.py (NEW - composition)
├─ agentic_cli/skill/methodology_enforcer.py (NEW)
└─ agentic_cli/skill/evidence_capturer.py (NEW)

Dashboard Backend:
├─ dashboard/backend/src/models/skill_execution.py (NEW)
├─ dashboard/backend/src/services/skill_executor.py (NEW)
└─ dashboard/backend/src/api/skill_execution.py (NEW)

Dashboard Frontend:
├─ dashboard/frontend/src/pages/SkillExecution.tsx (NEW)
├─ dashboard/frontend/src/components/SkillPhase.tsx (NEW)
├─ dashboard/frontend/src/components/CheckpointGate.tsx (NEW)
└─ dashboard/frontend/src/components/EvidenceCapture.tsx (NEW)
```

**Success Criteria:**
- ✅ Skills enforce methodology (not just provide tools)
- ✅ Checkpoints work (agent waits for approval)
- ✅ Evidence captured (audit trail complete)
- ✅ Composition works (skills call other skills)
- ✅ Context applied (project conventions enforced)
- ✅ Auto-generated skills are functional

---

## 8-Week Implementation Timeline

### Week 1-2: Code Onboarding (Track 1)
- Day 1-2: Design codebase analyzer
- Day 3-4: Build questionnaire system
- Day 5-6: Implement skill generator
- Day 7-8: Add to CLI and dashboard
- Day 9-10: Testing and refinement

**Deliverable:** `agent code onboard <repo>` produces understanding doc + 10 skills

### Week 3-4: Approval Workflow Dashboard (Track 2)
- Day 1-2: Design approval schema
- Day 3-4: Build dashboard UI components
- Day 5-6: Create backend API
- Day 7-8: Integrate with skill execution
- Day 9-10: Testing and refinement

**Deliverable:** Approvals page with full workflow integration

### Week 5-6: Methodology-Based Skills (Track 3) - Part 1
- Day 1-2: Update skill definition schema
- Day 3-4: Build skill execution engine with phases
- Day 5-6: Implement checkpoint gates
- Day 7-8: Add composition/orchestration
- Day 9-10: Testing and refinement

**Deliverable:** Skills with methodology enforcement and checkpoints

### Week 7-8: Methodology-Based Skills (Track 3) - Part 2
- Day 1-2: Create methodology skills (design, planning, TDD, review)
- Day 3-4: Generate domain skills from patterns
- Day 5-6: Apply project context to skills
- Day 7-8: Skill composition and orchestration
- Day 9-10: Integration, testing, documentation

**Deliverable:** Complete methodology-based skill system

---

## Success Metrics

### Code Onboarding
- ✅ Time to understanding: < 5 minutes
- ✅ Skill accuracy: 90%+ of generated skills are usable
- ✅ Coverage: 10-15 skills per project
- ✅ User approval: 95%+ of understanding documents approved on first pass

### Approval Workflow
- ✅ Approval time: < 10 minutes average
- ✅ Audit trail: 100% complete
- ✅ Rejection rate: < 5% (good design quality)
- ✅ Evidence capture: 100% of approvals tracked

### Methodology Skills
- ✅ Checkpoint enforcement: 100% of gates respected
- ✅ TDD compliance: 100% of generated code has tests
- ✅ Composition accuracy: Skills call correct sub-skills
- ✅ Context application: Project conventions enforced 100%

### Overall Platform
- ✅ Time to productivity: 1 day (vs current 1 week)
- ✅ Code quality consistency: 40% improvement
- ✅ Rework rate: 30% reduction (from better upfront design)
- ✅ Agent autonomy: 80% of tasks completed without intervention

---

## Expected Outcomes

### For Developers
- **Speed:** Onboard new codebases in 5 minutes instead of hours
- **Quality:** Consistent methodology enforcement across all agent work
- **Safety:** Approval gates prevent bad designs from being implemented
- **Transparency:** Full audit trail of decisions and approvals

### For Teams
- **Governance:** Explicit methodology enforcement
- **Knowledge:** Skills capture how your team builds software
- **Scaling:** Add developers with confidence in quality
- **Compliance:** Audit trail for regulatory/internal requirements

### For Agentic Platform
- **Differentiation:** Not just tools + templates, but methodology + governance
- **Competitive Advantage:** Align with Superpowers architecture but for multi-cloud
- **Enterprise Ready:** Approval workflows, audit trails, policy enforcement
- **User Adoption:** Better UX from approval gates + structured understanding

---

## Reference Documents

1. **SUPERPOWERS_REFERENCE_ANALYSIS.md** - Analysis of Superpowers architecture
2. **IMPLEMENTATION_SPECS.md** - Detailed specifications for all three tracks

## Next Steps

1. **Review** these documents with stakeholders
2. **Prioritize** which track to start with (recommend: Code Onboarding first)
3. **Create** detailed PRDs for chosen track
4. **Begin** implementation with acceptance criteria
5. **Iterate** based on user feedback and testing
