# Quick Reference: Skill Workflow Integration

## One-Page Overview

### The Integration (4 Points)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PROJECT CREATION                                         │
│    agent project create my-backend --use-case rag          │
│    └─> Apply methodology pack? (YES)                        │
│        └─> Adds: .skills/methodology/ + .dva/methodology.yaml
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CODE ONBOARDING (Optional but Recommended)               │
│    agent code onboard https://github.com/myteam/backend    │
│    └─> Generates:                                           │
│        ├─ .dva/codebase-understanding.md                    │
│        ├─ .skills/generated/ (8-15 auto-generated skills)   │
│        └─ .dva/methodology.yaml (methodology config)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. AGENT EXECUTION WITH WORKFLOW                            │
│    agent run --path ./my-backend --task "Add user auth"    │
│    └─> Loads .dva/methodology.yaml                          │
│        └─> Executes 4-Phase Workflow:                       │
│            1. Design → [User approves]                      │
│            2. Plan → [User approves]                        │
│            3. Execute → [Tests pass]                        │
│            4. Review → [Code review approves]               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. SKILLS HAVE PROJECT CONTEXT                              │
│    When skills execute, they know:                          │
│    ├─ Tech stack: FastAPI, PostgreSQL, pytest              │
│    ├─ Conventions: DI, Pydantic, custom exceptions         │
│    ├─ File patterns: app/api/v1/endpoints/*.py             │
│    └─ Requirements: 80% test coverage                       │
│                                                             │
│    Result: Skills are smart about THIS project             │
└─────────────────────────────────────────────────────────────┘
```

---

## The 4-Phase Workflow

```
PHASE 1: DESIGN
┌──────────────────────────────────┐
│ design-brainstorm-skill          │
├──────────────────────────────────┤
│ 1. Ask clarifying questions      │
│ 2. Propose design (5 sections)   │
│ 3. Store in .dva/approvals/      │
│ 4. [WAIT] User must approve ⏸️  │
└──────────────────────────────────┘
        ↓ (approved)
PHASE 2: PLANNING
┌──────────────────────────────────┐
│ implementation-planning-skill    │
├──────────────────────────────────┤
│ 1. Analyze approved design       │
│ 2. Break into 5 tasks            │
│ 3. Show file paths & tests       │
│ 4. [WAIT] User must approve ⏸️  │
└──────────────────────────────────┘
        ↓ (approved)
PHASE 3: EXECUTION
┌──────────────────────────────────┐
│ test-driven-development-skill    │
├──────────────────────────────────┤
│ For each task:                   │
│ 1. Write failing test (RED)      │
│ 2. Implement code (GREEN)        │
│ 3. Refactor (REFACTOR)           │
│ [AUTO] Tests must pass ✅        │
└──────────────────────────────────┘
        ↓ (all tests pass)
PHASE 4: REVIEW
┌──────────────────────────────────┐
│ code-review-skill                │
├──────────────────────────────────┤
│ 1. Check code quality            │
│ 2. Verify conventions            │
│ 3. Show quality report           │
│ 4. [WAIT] Code review ⏸️        │
└──────────────────────────────────┘
        ↓ (approved)
✅ COMPLETE
```

---

## Project Structure (With Skills)

```
my-backend/
├── src/
│   ├── main.py
│   ├── api/v1/
│   ├── models/
│   └── services/
├── tests/
│
└── .skills/                           ← Skills for this project
    ├── domain/                        ← Domain persona skills
    │   └─ backend-dev-skill
    │
    ├── generated/                     ← Auto-generated from code
    │   ├─ fastapi-endpoint-development-skill
    │   ├─ sqlalchemy-orm-skill
    │   ├─ postgresql-migration-skill
    │   ├─ async-coroutine-skill
    │   └─ error-handling-skill
    │
    └── methodology/                   ← From methodology pack
        ├─ design-brainstorm-skill
        ├─ implementation-planning-skill
        ├─ test-driven-development-skill
        └─ code-review-skill

└── .dva/
    ├── codebase-understanding.md      ← What this project is about
    ├── methodology.yaml               ← How to develop for it
    │
    └── approvals/                     ← Approval checkpoints
        ├── design-<uuid>/
        │   ├─ proposal.json
        │   └─ approval.json
        ├── plan-<uuid>/
        │   ├─ tasks.json
        │   └─ approval.json
        └── review-<uuid>/
            ├─ diff.json
            └─ approval.json
```

---

## Approval Checkpoints

### Checkpoint 1: Design Approval

```
User gets notification: "Design ready for review"
├─ Agent asked 7 questions
├─ Agent proposed JWT auth + Redis blacklist
├─ Agent explained rationale
├─ Agent listed alternatives
└─ Waiting for user to:
   ├─ agent approve <id>          OR
   ├─ agent reject <id> --reason  OR  
   └─ Check Agent Playground > Approvals

Stored in: .dva/approvals/design-<uuid>/
├─ proposal.json (what agent designed)
└─ approval.json (user's decision + feedback)
```

### Checkpoint 2: Plan Approval

```
User gets notification: "Plan ready for review"
├─ 5 tasks broken down
├─ Each task shows: files, code, tests, verification
└─ Waiting for user to:
   └─ agent approve <id>  OR  check dashboard

Stored in: .dva/approvals/plan-<uuid>/
├─ tasks.json (detailed task breakdown)
└─ approval.json (user's decision)
```

### Checkpoint 3: Execution (Automatic)

```
No user action needed - agent runs with TDD enforcement
├─ Task 1: RED → GREEN → REFACTOR → ✅
├─ Task 2: RED → GREEN → REFACTOR → ✅
├─ ...
└─ All tests must pass (47/47 tests passing)

If any test fails → Execution stops (blocking)
```

### Checkpoint 4: Code Review

```
User gets notification: "Code ready for review"
├─ Code quality report
│  ├─ Linting: PASS
│  ├─ Type checking: PASS
│  ├─ Coverage: 87% (✓ exceeds 80%)
│  └─ Conventions: PASS
└─ Waiting for user to:
   └─ agent approve <id>  OR  check dashboard

Stored in: .dva/approvals/review-<uuid>/
├─ diff.json (code changes + quality report)
└─ approval.json (code review approval)
```

---

## New CLI Commands

```bash
# Manage approvals
agent approvals list                    # See pending
agent approvals show <id>               # Details
agent approve <id> --message "..."      # Approve with feedback
agent reject <id> --reason "..."        # Reject with reason
agent approvals history                 # Timeline

# Resume after approval
agent run --continue <id>               # Pick up where stopped

# Project with methodology (new interactive prompt)
agent project create my-backend --use-case rag
  ↓ [NEW] "Apply methodology pack? (Y/n)"

# Enhanced code onboarding (new)
agent code onboard https://github.com/myteam/backend
  ↓ Analyze → Questions → Understanding → Skills → Methodology

# Skill execution with workflow (new)
agent run --path ./my-backend --task "..."
  ↓ Executes 4-phase workflow with checkpoints
```

---

## How Skills Get Project Context

**Scenario:** `fastapi-endpoint-development-skill` runs in `my-backend` project

```
Skill receives:
├─ Project root: /path/to/my-backend
├─ Methodology config: .dva/methodology.yaml
│  └─ Contains: tech_stack, conventions, file_patterns
├─ Understanding doc: .dva/codebase-understanding.md
│  └─ Contains: architecture, key files, patterns
└─ Examples: .skills/generated/ reference implementations
   └─ "Follow the pattern from fastapi-endpoint-development-skill"

Skill uses this to:
├─ Suggest correct file paths
│  └─ "Create endpoint in: app/api/v1/endpoints/users.py"
├─ Reference existing code
│  └─ "See app/api/v1/endpoints/orders.py for pattern"
├─ Enforce conventions
│  └─ "Use dependency injection (like in existing code)"
└─ Apply project standards
   └─ "80% test coverage required in this project"

Result: Skill is SMART about THIS project specifically
```

---

## The Big Picture

```
Superpowers Methodology
      ↓
Design → Plan → Execute → Review
      ↓
DVA Project Framework
      ↓
.skills/ (domain, generated, methodology)
.dva/methodology.yaml (workflow config)
.dva/approvals/ (checkpoints)
      ↓
CLI Commands
      ↓
agent run → loads methodology → executes 4-phase workflow
      ↓
Agent Playground Dashboard
      ↓
Approvals Panel (pending reviews)
Skill Execution Tracker (progress)
Activity Timeline (audit trail)
      ↓
✅ Enterprise-Grade AI Agent Platform
   with methodology enforcement, approval gates, and full traceability
```

---

## Key Differences: Before vs After

### BEFORE (Tool-Focused)
```
Skills = Tool access (Jira, Bitbucket, Confluence)
Workflow = Agent uses tools freely
Quality = Inconsistent (depends on agent)
Governance = None
Auditability = Logs only
```

### AFTER (Methodology-Focused)
```
Skills = Enforce development methodology
Workflow = 4 phases with approval gates
Quality = Consistent (enforced by methodology)
Governance = Design, plan, code review required
Auditability = Full evidence trail in .dva/approvals/
```

---

## Implementation Priority

### 🔴 High Priority (Week 1-4)
1. **Code Onboarding** (8-10 days)
   - Auto-generate skills from codebase
   - Create understanding documents
   - Apply methodology packs

2. **Methodology Skills** (12-15 days)
   - Create 4 core methodology skills
   - Implement checkpoint gates
   - Add skill composition

### 🟡 Medium Priority (Week 5-6)
3. **Approval Dashboard** (5-7 days)
   - Show pending approvals
   - Allow approve/reject with feedback
   - Display approval history

### 🟢 Lower Priority (Week 7-8)
4. **Integration & Polish**
   - Dashboard integration
   - CLI refinement
   - Documentation

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Code onboarding time | < 5 minutes |
| Skills auto-generated per project | 10-15 |
| TDD enforcement | 100% (all code has tests) |
| Design approval rate | < 10 min average |
| Audit trail completeness | 100% |
| Time to productivity | 1 day (vs 1 week) |

---

## Where to Go From Here

1. **Read** all 5 documentation files in repo root
2. **Discuss** with team (architecture, timeline, priorities)
3. **Choose** implementation track (recommend: Code Onboarding first)
4. **Create** detailed PRD with acceptance criteria
5. **Build** with TDD methodology (following Superpowers!)
6. **Test** with real DVA projects and collect feedback

Files:
- `SUPERPOWERS_REFERENCE_ANALYSIS.md`
- `IMPLEMENTATION_SPECS.md`
- `TRANSFORMATION_ROADMAP.md`
- `SKILL_WORKFLOW_INTEGRATION.md`
- `INTEGRATION_SUMMARY.md`
