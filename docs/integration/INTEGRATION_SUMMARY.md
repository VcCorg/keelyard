# Skill Workflow + DVA CLI Integration - Visual Summary

## Quick Answer: How Skills Execute in DVA Projects

### The Flow

```
User Command
    ↓
agent run --path <project> --task "Add authentication"
    ↓
Load .dva/methodology.yaml (from project config)
    ↓
Invoke 4 Skills in Sequence:
┌─────────────────────────────────────────────────┐
│ 1. design-brainstorm-skill                      │
│    ├─ Ask clarifying questions                  │
│    ├─ Propose design in sections                │
│    └─ [CHECKPOINT] Wait for user approval ⏸️   │
├─────────────────────────────────────────────────┤
│ 2. implementation-planning-skill                │
│    ├─ Break into 2-5 min tasks                  │
│    ├─ Show file paths & verification steps      │
│    └─ [CHECKPOINT] Wait for user approval ⏸️   │
├─────────────────────────────────────────────────┤
│ 3. test-driven-development-skill                │
│    ├─ Dispatch subagents (one per task)        │
│    ├─ Enforce RED → GREEN → REFACTOR           │
│    └─ [CHECKPOINT] Tests must pass ✅          │
├─────────────────────────────────────────────────┤
│ 4. code-review-skill                            │
│    ├─ Check code quality                        │
│    ├─ Verify conventions                        │
│    └─ [CHECKPOINT] Code review approval ⏸️     │
└─────────────────────────────────────────────────┘
    ↓
Store Evidence
    ├─ .dva/approvals/design-<uuid>/
    ├─ .dva/approvals/plan-<uuid>/
    ├─ .dva/approvals/review-<uuid>/
    └─ Full audit trail in tracker
    ↓
✅ COMPLETE (with full approval history)
```

---

## Four Key Integration Points

### 1️⃣ Project Creation (Starting Point)

**Before:**
```bash
agent project create my-backend --use-case rag
  └─ Creates standard project structure
  └─ Done (no methodology)
```

**After:**
```bash
agent project create my-backend --use-case rag
  ├─ Creates standard project structure
  ├─ [NEW] Asks: "Apply methodology pack? (Y/n)"
  │   └─ Recommended: "Backend Development"
  ├─ [YES] Adds to project:
  │   ├─ .dva/methodology.yaml (workflow config)
  │   ├─ .skills/methodology/
  │   │   ├─ design-brainstorm-skill
  │   │   ├─ implementation-planning-skill
  │   │   ├─ test-driven-development-skill
  │   │   └─ code-review-skill
  │   └─ .dva/approvals/ (checkpoint directory)
  └─ ✅ Project ready with methodology enforcement
```

### 2️⃣ Code Onboarding (Analysis → Skills → Methodology)

**Command:**
```bash
agent code onboard https://github.com/myteam/backend \
  --output-dir ./my-backend-project
```

**What Happens:**
```
Step 1: Analyze Codebase
  └─ Detect: Python, FastAPI, PostgreSQL, pytest
  └─ Save: .dva/onboarding/analysis.json

Step 2: Ask Clarifying Questions
  ├─ "What's the primary business purpose?"
  ├─ "What scale/latency requirements?"
  ├─ "What's your testing philosophy?"
  └─ Save: .dva/onboarding/questionnaire.json

Step 3: Generate Understanding Document
  └─ Create: .dva/codebase-understanding.md
     ├─ Architecture overview
     ├─ Key files and purposes
     ├─ Development workflow
     ├─ Testing strategy
     └─ Common patterns

Step 4: Generate Project-Specific Skills
  └─ Create: .skills/generated/
     ├─ fastapi-endpoint-development-skill
     │   └─ Includes: project conventions, file patterns, examples
     ├─ sqlalchemy-orm-skill
     ├─ postgresql-migration-skill
     ├─ async-coroutine-skill
     └─ error-handling-skill

Step 5: Apply Methodology Pack
  ├─ Suggest: "Backend Development" methodology
  ├─ Create: .dva/methodology.yaml
  ├─ Approve? (Y/n)
  └─ ✅ Project fully configured with methodology
```

**Result:** Project with 10+ auto-generated, context-aware skills + methodology enforcement

### 3️⃣ Agent Execution (Workflow with Checkpoints)

**Command:**
```bash
agent run --path ./my-backend --task "Add user authentication"
```

**What Happens:**

```
┌─ PHASE 1: DESIGN
│  └─ design-brainstorm-skill executes
│     ├─ Ask: What auth method?
│     ├─ Ask: Where to store users?
│     ├─ Ask: Token expiration?
│     ├─ Show: Design proposal
│     └─ Store: .dva/approvals/design-<uuid>/proposal.json
│
│  [EXECUTION PAUSES] ⏸️
│  └─ Waiting for user approval
│     └─ User reviews in: Agent Playground > Approvals panel
│        └─ Clicks: APPROVE (or REJECT with feedback)
│           └─ Stored: .dva/approvals/design-<uuid>/approval.json
│
│ ✅ Approval received → Continue to Phase 2
│
├─ PHASE 2: PLANNING
│  └─ implementation-planning-skill executes
│     ├─ Analyze approved design
│     ├─ Break into 5 tasks (2-5 min each)
│     ├─ For each task: Show files, code, tests, verification
│     └─ Store: .dva/approvals/plan-<uuid>/tasks.json
│
│  [EXECUTION PAUSES] ⏸️
│  └─ Waiting for user approval
│     └─ User reviews task breakdown in dashboard
│        └─ Approves or asks for changes
│
│ ✅ Plan approved → Continue to Phase 3
│
├─ PHASE 3: EXECUTION (NO PAUSE)
│  └─ test-driven-development-skill executes
│     ├─ For Task 1:
│     │  ├─ Dispatch subagent with task context
│     │  ├─ Enforce: Write failing test (RED)
│     │  ├─ Enforce: Implement code (GREEN)
│     │  ├─ Enforce: Refactor (REFACTOR)
│     │  └─ Verify: Tests pass ✅
│     ├─ For Task 2-5: [same TDD cycle]
│     └─ All tests passing → Continue to Phase 4
│
│ [CHECKPOINT: Tests must pass]
│ └─ If any test fails → Execution stops (blocking)
│
├─ PHASE 4: REVIEW (APPROVAL NEEDED)
│  └─ code-review-skill executes
│     ├─ Check: Code quality (lint, type checking)
│     ├─ Check: Conventions match project
│     ├─ Check: Test coverage > 80%
│     ├─ Show: Code diff with quality report
│     └─ Store: .dva/approvals/review-<uuid>/diff.json
│
│  [EXECUTION PAUSES] ⏸️
│  └─ Waiting for code review approval
│     └─ User reviews code in dashboard
│        └─ Approves with final sign-off
│
└─ ✅ COMPLETE
   └─ All phases done with approvals at each step
   └─ Full audit trail captured
   └─ Changes ready to merge
```

### 4️⃣ Project Context Injection (Skills Know Your Project)

**Inside `.dva/methodology.yaml`:**
```yaml
---
methodology_pack: backend-development
tech_stack: [FastAPI, PostgreSQL, pytest]
conventions:
  naming: snake_case
  api_versioning: /api/v1/
  error_handling: custom-exception-hierarchy
  testing: TDD with 80% minimum coverage
file_patterns:
  endpoints: app/api/v1/endpoints/*.py
  models: app/models/*.py
  tests: tests/integration/test_*.py
```

**When a skill executes:**
```
Skill: fastapi-endpoint-development-skill

Available Context:
├─ Project root: /path/to/my-backend
├─ Understanding doc: .dva/codebase-understanding.md
├─ Tech stack: FastAPI, PostgreSQL
├─ Conventions: DI, Pydantic, custom exceptions
├─ File patterns: Where to create files
└─ Examples: Reference implementations

The Skill Uses This To:
├─ Suggest correct file paths
│  └─ "Create in: app/api/v1/endpoints/users.py"
├─ Reference existing patterns
│  └─ "Follow pattern from app/api/v1/endpoints/orders.py"
├─ Enforce conventions
│  └─ "Use DI for services (like in existing code)"
└─ Apply project standards
   └─ "Minimum 80% test coverage (this project requires it)"
```

---

## Skills Taxonomy in DVA Project

### Where Skills Come From

```
my-backend-project/.skills/
├── domain/
│   ├── backend-dev-skill/           ← From --domain flag
│   ├── backend-qa-skill/            ← Wired when creating project
│   └── backend-sm-skill/
│
├── generated/
│   ├── fastapi-endpoint-development-skill/  ← From code onboarding
│   ├── sqlalchemy-orm-skill/                ├─ Auto-generated from
│   ├── postgresql-migration-skill/          │  code analysis
│   ├── async-coroutine-skill/               └─ Includes project
│   └── error-handling-skill/                   context
│
├── methodology/
│   ├── design-brainstorm-skill/     ← From methodology pack
│   ├── implementation-planning-skill/├─ Added when creating
│   ├── test-driven-development-skill/│  project or applying
│   └── code-review-skill/           └─  methodology
│
└── user-created/
    ├── my-custom-tool-skill/        ← User created manually
    └── team-workflow-skill/
```

### How Skills Compose

```
When you run: agent run --task "Add auth"

The Execution Engine:
1. Loads .dva/methodology.yaml
2. Sees: 4 phases with 4 skills
3. For each phase:
   ├─ Load skill (e.g., design-brainstorm-skill)
   ├─ Inject project context (from .dva/)
   ├─ Execute skill with project awareness
   └─ Wait for checkpoint (approval)

Result:
└─ Agent knows:
   ├─ How this project is structured
   ├─ What conventions to follow
   ├─ Where to create files
   ├─ What tests to write
   └─ Who to ask for approvals
```

---

## Approval Checkpoints Storage

```
.dva/approvals/
├── design-550e8400-e29b-41d4-a716-446655440000/
│   ├── proposal.json
│   │   └─ Agent's design proposal (questions, answers, design)
│   ├── approval.json
│   │   └─ User approval (who, when, feedback)
│   └── status: approved | rejected | pending
│
├── plan-550e8400-e29b-41d4-a716-446655440001/
│   ├── tasks.json
│   │   └─ Task breakdown (5 tasks with files, tests)
│   ├── approval.json
│   │   └─ User approval (who, when, feedback)
│   └─ status: approved | rejected | pending
│
└── review-550e8400-e29b-41d4-a716-446655440002/
    ├── diff.json
    │   └─ Code changes with quality report
    ├── approval.json
    │   └─ Code review approval
    └─ status: approved | rejected | pending
```

---

## Activity Tracking (Audit Trail)

**Every skill execution is recorded:**

```bash
$ agent approvals history --project ./my-backend

┌─ APPROVAL HISTORY
├─ 2026-05-04 10:35:00 ✅ APPROVED
│  ├─ Type: design
│  ├─ Reviewer: alice@company.com
│  ├─ Task: "Add user authentication"
│  ├─ Feedback: "Good approach, proceed"
│  └─ Evidence: [link to design-550e8400.../approval.json]
│
├─ 2026-05-04 10:42:00 ✅ APPROVED
│  ├─ Type: plan
│  ├─ Reviewer: alice@company.com
│  ├─ Feedback: "Tasks are clear"
│  └─ Evidence: [link to plan-550e8400.../approval.json]
│
├─ 2026-05-04 11:00:00 ✅ PASS
│  ├─ Type: execution
│  ├─ Phase: test-driven-development
│  ├─ Status: All tests passing (47/47)
│  └─ Evidence: [test results, coverage report]
│
└─ 2026-05-04 11:08:00 ✅ APPROVED
   ├─ Type: code-review
   ├─ Reviewer: bob@company.com
   ├─ Feedback: "Code quality looks good"
   └─ Evidence: [link to review-550e8400.../approval.json]
```

---

## CLI Commands (New)

```bash
# Create project with methodology
agent project create my-backend --use-case rag
  └─ [NEW] Applies methodology pack

# Code onboarding (new)
agent code onboard https://github.com/myteam/backend
  └─ [NEW] Generates skills + methodology

# Run with skill workflow
agent run --path ./my-backend --task "Add auth"
  └─ [NEW] Executes 4-phase workflow with checkpoints

# Manage approvals (new)
agent approvals list                    # Show pending
agent approvals show <id>               # Show details
agent approve <id> --message "..."      # Approve
agent reject <id> --reason "..."        # Reject
agent approvals history                 # View history
agent run --continue <id>               # Resume after approval
```

---

## Complete Example: Real Workflow

```bash
# 1. Create project with methodology
$ agent project create order-api --use-case rag
✓ Project created
? Apply methodology pack? (Y/n) Y
✓ Backend Development methodology applied
✓ Methodology skills added
✓ Project ready with 4-phase workflow

# 2. Run agent with task (uses 4-phase skill workflow)
$ agent run --path ./order-api --task "Add payment processing"

🔄 PHASE 1: DESIGN (design-brainstorm-skill)
  ? What payment provider? Stripe
  ? Webhook handling? Yes
  ? Retry strategy? Exponential backoff
  ✓ Design proposal created
  
✋ APPROVAL NEEDED
   → Check Agent Playground > Approvals panel
   → Or run: agent approve <design-id>

[User goes to dashboard, reviews design, clicks APPROVE]

🔄 PHASE 2: PLANNING (implementation-planning-skill)
  ✓ Task 1: Create Stripe client wrapper (2min)
  ✓ Task 2: Add Order model fields (2min)
  ✓ Task 3: Create payment endpoint (4min)
  ✓ Task 4: Add webhook handler (3min)
  ✓ Task 5: Create integration tests (4min)
  
✋ APPROVAL NEEDED
   → Review plan in dashboard
   → Click APPROVE

[User approves plan in dashboard]

🔄 PHASE 3: EXECUTION (test-driven-development-skill)
  📍 Task 1/5: Create Stripe client wrapper
    ├─ [RED] Writing test → FAIL
    ├─ [GREEN] Writing code → PASS
    ├─ [REFACTOR] Improving → PASS
    └─ ✅ Complete
  
  📍 Task 2/5: Add Order model fields
    └─ ✅ Complete
  
  ... [Tasks 3-5] ...
  
  ✅ ALL TASKS COMPLETE
     └─ 47/47 tests passing
     └─ Coverage: 87%

🔄 PHASE 4: REVIEW (code-review-skill)
  ✅ Code quality: PASS
  ✅ Conventions: PASS
  ✅ Coverage: PASS (87% ≥ 80%)
  
✋ CODE REVIEW APPROVAL
   → Review code changes in dashboard
   → Click APPROVE

[User approves code in dashboard]

✅ FEATURE COMPLETE
   └─ All 4 phases passed
   └─ All approvals captured
   └─ Full audit trail available
   └─ Code ready to merge

# 3. View approval history
$ agent approvals history --project ./order-api
  ✅ Design approved by alice (05-04 10:35)
  ✅ Plan approved by alice (05-04 10:42)
  ✅ Execution passed (47 tests, 87% coverage)
  ✅ Code review approved by bob (05-04 11:08)
```

---

## Key Takeaways

### Skills Execute **Within** DVA Projects
- Skills have full access to project context
- Skills know conventions, file patterns, examples
- Skills enforce project standards automatically

### Workflow is **Checkpointed**
- Design phase: User approves before planning
- Planning phase: User approves before execution
- Execution phase: Tests must pass (automatic)
- Review phase: Code review required before merge

### Everything is **Traceable**
- Approvals stored in `.dva/approvals/`
- Full audit trail in activity tracker
- Evidence captured at each checkpoint
- History available for compliance/review

### Integration is **Seamless**
- Works with existing `agent project create`
- Works with existing `agent run`
- New `agent approvals` commands for management
- Dashboard Approvals panel shows everything

This is **Superpowers methodology + DVA project framework + multi-cloud deployments = Enterprise AI Agent Platform**
