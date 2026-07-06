# Skill Workflow Integration with KEEL CLI Project Framework

## Overview

KEEL Projects are the **execution containers** for agents. Skill workflows must integrate seamlessly with:
- Project creation (`agent project create`)
- Project structure (src/, tests/, .skills/)
- Agent execution (`agent run`)
- Activity tracking and approval checkpoints
- Evidence capture for audit trails

---

## Current KEEL Project Architecture

### Directory Structure
```
my-agent-project/
├── src/
│   ├── main.py              # Agent entry point
│   ├── agent.py             # Agent implementation
│   └── tools/               # Custom tools
├── tests/
│   ├── unit/
│   └── integration/
├── .skills/                 # Skills directory
│   ├── domain/              # Auto-wired domain skills
│   └── custom/              # User-created skills
├── .domain-context.json     # Domain metadata
├── .env                     # Environment configuration
├── pyproject.toml
└── README.md
```

### Key CLI Commands
```bash
agent project create <name>        # Create project from template
agent project list                 # List projects
agent project validate <path>      # Validate project structure
agent run --path <project>         # Run agent
agent skill install <url>          # Install skill into project
agent skill list --path <project>  # List skills in project
agent code onboard <repo>          # Analyze codebase (NEW)
```

---

## Skill Workflow Integration Points

### Point 1: Project Creation with Methodology Skills

**Command:**
```bash
agent project create my-backend \
  --use-case rag \
  --framework adk \
  --domain order-management
```

**What Happens Today:**
```
1. Generate project from template (basic ADK RAG structure)
2. Wire domain context if --domain provided
3. Create .skills/domain/ with persona skills
4. Done - project ready for manual agent development
```

**What Happens With Methodology Skills:**
```
1. Generate project from template
2. Wire domain context
3. Create .skills/domain/ with persona skills
4. [NEW] Prompt: "Do you want to apply a methodology pack?"
   └─ Options: Backend Development, Data Pipeline, DevOps, etc.
5. [NEW] Apply methodology pack → adds methodology skills to project
   ├─ design-brainstorm-skill
   ├─ implementation-planning-skill
   ├─ test-driven-development-skill
   └─ code-review-skill
6. [NEW] Create .keel/methodology.yaml with workflow config
7. [NEW] Store approval gates in .keel/approvals/config.yaml
```

**New File: `.keel/methodology.yaml`**
```yaml
---
methodology_pack: backend-development
applied_at: 2026-05-04T10:00:00Z
applied_by: user@company.com

workflow_phases:
  1_design:
    skill: design-brainstorm-skill
    required: true
    checkpoint: user-approval-required
    timeout_minutes: 120

  2_planning:
    skill: implementation-planning-skill
    required: true
    checkpoint: user-approval-required
    timeout_minutes: 60

  3_execution:
    skill: test-driven-development-skill
    required: true
    checkpoint: tests-must-pass
    blocking: true

  4_review:
    skill: code-review-skill
    required: true
    checkpoint: code-review-required
    blocking: false

domain_skills:
  - fastapi-endpoint-development-skill
  - sqlalchemy-orm-skill
  - postgresql-migration-skill
  - async-coroutine-skill
  - error-handling-skill

quality_requirements:
  min_test_coverage: 0.80
  max_lint_issues: 5
  required_docstrings: true

approval_gate_config:
  escalation_reminder_minutes: 30
  max_waittime_minutes: 120
  require_feedback_on_rejection: true
```

---

### Point 2: Code Onboarding Creates Project-Specific Skills

**Command:**
```bash
agent code onboard <repo-url> --output-dir ./my-backend-project
```

**Integrated Flow:**
```
Step 1: Analyze Codebase
  ├─ Detect: Python, FastAPI, PostgreSQL, pytest
  ├─ Patterns: API versioning, DI, middleware, ORM
  └─ Store: analysis.json in .keel/onboarding/

Step 2: Ask Clarifying Questions
  ├─ Domain: "Real-time order management"
  ├─ Scale: "10K req/min, sub-100ms latency"
  ├─ Testing: "TDD-focused, 80% minimum coverage"
  └─ Store: questionnaire.json in .keel/onboarding/

Step 3: Generate Understanding Document
  └─ Create: .keel/codebase-understanding.md with:
     ├─ Architecture overview
     ├─ Key files and purposes
     ├─ Development workflow
     ├─ Testing strategy
     └─ Common patterns

Step 4: Generate Project-Specific Skills
  └─ Create in .skills/generated/:
     ├─ fastapi-endpoint-development-skill.md
     │   └─ Includes: project conventions, file patterns, examples
     ├─ sqlalchemy-orm-skill.md
     ├─ postgresql-migration-skill.md
     ├─ async-coroutine-skill.md
     └─ error-handling-skill.md
     
Step 5: Apply Recommended Methodology Pack
  └─ Suggest: "Backend Development" methodology pack
     ├─ Create: .keel/methodology.yaml
     ├─ Add: Methodology skills to .skills/
     ├─ Ask: "Apply this methodology? (Y/n)"
     └─ Done: Project fully configured
```

**Result After Code Onboarding:**
```
my-backend-project/
├── src/
│   ├── main.py
│   ├── models/
│   │   ├── order.py
│   │   └── warehouse.py
│   ├── api/
│   │   └── v1/
│   │       └── orders.py
│   └── services/
├── tests/
├── .skills/
│   ├── domain/              # Auto-wired domain skills
│   ├── generated/           # Auto-generated from code onboarding
│   │   ├── fastapi-endpoint-development-skill/
│   │   ├── sqlalchemy-orm-skill/
│   │   └─ ... [4 more]
│   └── methodology/         # From methodology pack
│       ├── design-brainstorm-skill/
│       ├── implementation-planning-skill/
│       ├── test-driven-development-skill/
│       └── code-review-skill/
├── .keel/
│   ├── codebase-understanding.md  # Generated understanding doc
│   ├── methodology.yaml            # Methodology workflow config
│   ├── onboarding/
│   │   ├── analysis.json
│   │   └── questionnaire.json
│   └── approvals/
│       └── config.yaml
└── src/main.py
```

---

### Point 3: Agent Run Executes with Skill Workflow

**Command:**
```bash
agent run --path ./my-backend --task "Add user authentication endpoint"
```

**Skill Workflow Execution:**

#### Phase 1: Design (design-brainstorm-skill)
```
Agent Input: "Add user authentication endpoint"

Skill Execution (design-brainstorm-skill):
  1. Ask clarifying questions
     ? What auth method? (JWT, OAuth, etc.)
     ? Where to store users?
     ? Token expiration strategy?
     ? Refresh token rotation?
  
  2. Present design proposal
     Design: JWT + Redis blacklist + refresh tokens
     Architecture: [diagram]
     Rationale: [explanation]
     Alternatives: [3 options]
  
  3. Store design in .keel/approvals/design-<uuid>.json
  
  4. [CHECKPOINT] Wait for user approval
     ├─ User must approve design before proceeding
     ├─ Timeout: 2 hours with escalation reminder
     └─ Store approval in: .keel/approvals/<uuid>/approval.json
```

**CLI Output During Design Phase:**
```
$ agent run --path ./my-backend --task "Add user authentication"

🔄 Skill: design-brainstorm-skill
   ├─ Question 1/7: What authentication method?
   │  Your options: [JWT], [OAuth 2.0], [Session-based], [API Key]
   │  User: JWT
   │
   ├─ Question 2/7: Where to store user data?
   │  User: PostgreSQL with bcrypt hashing
   │
   └─ ... [5 more questions]

📋 DESIGN PROPOSAL
   ├─ Approach: JWT with refresh tokens + Redis blacklist
   ├─ Architecture:
   │  ├─ Login endpoint: POST /api/v1/auth/login
   │  ├─ Token storage: Redis (5min expiry)
   │  ├─ Refresh flow: POST /api/v1/auth/refresh
   │  └─ Logout: POST /api/v1/auth/logout (add to blacklist)
   │
   ├─ Rationale:
   │  ├─ Stateless: Scales horizontally
   │  ├─ Redis: Sub-millisecond blacklist lookup
   │  └─ Refresh tokens: Reduce exposure of main token
   │
   └─ Alternatives Considered:
      ├─ Session-based (requires sticky sessions)
      └─ OAuth 2.0 (deferred for future)

✋ APPROVAL REQUIRED
   The design has been saved to: .keel/approvals/design-<uuid>/
   
   Human Action Required:
   └─ Review design and run: agent approve --id <uuid>
      or: agent run --task "..." --approve-design
      or: Check Agent Playground > Approvals panel
      
   ⏱️ Expires: in 2 hours (escalation reminder sent in 1 hour)
```

#### Phase 2: Planning (implementation-planning-skill)
```
[Only runs after user approves design]

Skill Execution (implementation-planning-skill):
  1. Analyze approved design
  2. Break into 5 tasks (2-5 minutes each)
  3. For each task:
     ├─ Exact file paths to create/modify
     ├─ Code snippet expected
     ├─ Test cases needed
     └─ Verification step (what to check)
  
  4. Store plan in .keel/approvals/plan-<uuid>.json
  
  5. [CHECKPOINT] Wait for user approval
     ├─ User reviews task breakdown
     └─ Approves plan before execution starts
```

**CLI Output During Planning Phase:**
```
$ agent run --path ./my-backend --task "..." --approve-design

✅ Design Approved!

🔄 Skill: implementation-planning-skill
   Breaking down into tasks...

📋 IMPLEMENTATION PLAN (5 tasks, ~15 minutes)

Task 1 (3min): Create JWT utility module
  Files to create:
    └─ app/auth/jwt.py
  Expected output:
    ├─ encode_token(user_id, expires_in) → JWT string
    ├─ decode_token(token) → user_id or None
    └─ verify_token(token) → bool
  Tests needed:
    └─ tests/unit/auth/test_jwt.py
  Verification:
    └─ pytest tests/unit/auth/test_jwt.py (all pass)

Task 2 (2min): Add User model fields
  Files to modify:
    └─ app/models/user.py
  Changes needed:
    ├─ Add: password_hash (str)
    ├─ Add: last_login_at (datetime)
    └─ Add: login_attempts (int)
  Tests needed:
    └─ tests/unit/models/test_user.py
  Verification:
    └─ alembic upgrade head (migration succeeds)

Task 3 (4min): Create login endpoint
  Files to create:
    └─ app/api/v1/auth.py
  Expected endpoints:
    ├─ POST /api/v1/auth/login → {access_token, refresh_token}
    ├─ POST /api/v1/auth/refresh → new access_token
    └─ POST /api/v1/auth/logout → {success: true}
  Tests needed:
    └─ tests/integration/api/test_auth.py
  Verification:
    └─ pytest tests/integration/api/test_auth.py (all pass)

Task 4 (3min): Add JWT middleware
  Files to create:
    └─ app/middleware/auth_middleware.py
  Expected behavior:
    ├─ Check Authorization header
    ├─ Validate JWT token
    └─ Inject user_id into request context
  Tests needed:
    └─ tests/integration/middleware/test_auth.py
  Verification:
    └─ Requests without token: 401 Unauthorized

Task 5 (2min): Create token blacklist service
  Files to create:
    └─ app/services/token_blacklist.py
  Expected functions:
    ├─ blacklist_token(token, expires_at)
    ├─ is_blacklisted(token) → bool
    └─ cleanup_expired()
  Tests needed:
    └─ tests/unit/services/test_blacklist.py
  Verification:
    └─ pytest tests/unit/services/test_blacklist.py

✋ APPROVAL REQUIRED
   The plan has been saved to: .keel/approvals/plan-<uuid>/
   
   Review the tasks and run:
   └─ agent approve --id <uuid> --proceed-to-execution
      or: agent run --task "..." --approve-plan
      
   ⏱️ Expires: in 1 hour
```

#### Phase 3: Execution (test-driven-development-skill)
```
[Only runs after user approves plan]

Skill Execution (test-driven-development-skill):
  For each task from approved plan:
    1. Dispatch subagent with task context
    2. Enforce TDD:
       ├─ RED: Write failing test
       ├─ GREEN: Implement minimal code
       └─ REFACTOR: Improve code quality
    3. Verify tests pass
    4. Store evidence of completion
    5. Move to next task
```

**CLI Output During Execution:**
```
$ agent run --path ./my-backend --task "..." --approve-plan

✅ Plan Approved!

🔄 Phase: EXECUTION (TDD-Enforced)

📍 Task 1/5: Create JWT utility module
   Dispatching subagent...
   
   ├─ [RED] Writing failing test
   │  └─ test_jwt.py::test_encode_token → FAIL (as expected)
   │
   ├─ [GREEN] Writing implementation
   │  └─ jwt.py created (minimal code)
   │
   ├─ ✅ Running tests
   │  └─ test_jwt.py::test_encode_token → PASS
   │  └─ test_jwt.py::test_decode_token → PASS
   │  └─ Coverage: 94%
   │
   ├─ [REFACTOR] Improving code
   │  └─ Added error handling, docstrings
   │
   └─ ✅ Task 1 Complete
      Files changed: 2
      Tests passing: 12/12
      Coverage: 94%

📍 Task 2/5: Add User model fields
   ├─ [RED] Writing failing test → FAIL
   ├─ [GREEN] Adding fields → PASS
   ├─ [REFACTOR] Improving types → PASS
   └─ ✅ Task 2 Complete

... [Tasks 3-5] ...

✅ ALL TASKS COMPLETE

Summary:
  ├─ Files created: 5
  ├─ Files modified: 3
  ├─ Tests passing: 47/47
  ├─ Coverage: 87% (↑ from 82%)
  ├─ Lint issues: 0
  └─ Time elapsed: 18 minutes
```

#### Phase 4: Review (code-review-skill)
```
[Automatically after execution completes]

Skill Execution (code-review-skill):
  1. Check code quality
     ├─ Lint: black, flake8, mypy
     ├─ Tests: All passing?
     └─ Coverage: Meets 80% threshold?
  
  2. Verify conventions
     ├─ File naming matches patterns
     ├─ Docstrings present
     ├─ DI used for services
     └─ Error handling consistent
  
  3. [CHECKPOINT] Code review required
     ├─ Show code diff
     ├─ Wait for human approval
     └─ Allow merge only if approved
```

**CLI Output During Review:**
```
📋 CODE REVIEW CHECK

Spec Compliance:
  ✅ All 5 tasks completed as specified
  ✅ All endpoints created
  ✅ All tests passing
  ✅ File locations match plan

Code Quality:
  ✅ Black formatting: PASS
  ✅ Flake8 linting: PASS (0 issues)
  ✅ MyPy type checking: PASS
  ✅ Test coverage: 87% (✓ exceeds 80%)
  ✅ Documentation: 100% (all functions documented)

Conventions Check:
  ✅ Dependency injection used
  ✅ Error handling: Custom exception hierarchy
  ✅ Async/await: Correct usage
  ✅ API versioning: /api/v1/ ✓
  ✅ Pydantic validation: Present

✋ CODE REVIEW APPROVAL REQUIRED
   
   Changes Summary:
   ├─ 5 files created
   ├─ 3 files modified
   ├─ +287 lines of code
   ├─ 47 tests added
   └─ All checks passing
   
   Human Review Needed:
   ├─ Code quality approval
   ├─ Architecture alignment
   └─ Security review
   
   Action Required:
   └─ agent approve --id <uuid> --merge
      or: Check Agent Playground > Code Review panel
```

---

### Point 4: Skills Integrated into Project Structure

**Location of Skills:**
```
my-backend-project/.skills/
├── domain/                           # Wired from domain context
│   ├── backend-dev-skill/
│   ├── backend-qa-skill/
│   └── backend-sm-skill/
│
├── generated/                        # From code onboarding
│   ├── fastapi-endpoint-development-skill/
│   ├── sqlalchemy-orm-skill/
│   ├── postgresql-migration-skill/
│   ├── async-coroutine-skill/
│   └── error-handling-skill/
│
├── methodology/                      # From methodology pack
│   ├── design-brainstorm-skill/
│   ├── implementation-planning-skill/
│   ├── test-driven-development-skill/
│   └── code-review-skill/
│
└── user-created/                     # Manually created
    ├── my-custom-tool-skill/
    └── team-workflow-skill/
```

**How Skills Reference Project Context:**

When a skill executes within a project, it has access to project context:

```yaml
# Inside skill: fastapi-endpoint-development-skill/SKILL.md
---
name: fastapi-endpoint-development-skill
# ... metadata ...

# Project context automatically injected when skill runs in this project
project_context:
  project_root: /path/to/my-backend-project
  understanding_doc: .keel/codebase-understanding.md
  methodology: backend-development
  tech_stack: [FastAPI, SQLAlchemy, PostgreSQL, pytest]
  conventions:
    naming: snake_case
    api_versioning: /api/v1/
    error_handling: custom-exception-hierarchy
    testing: TDD with 80% minimum coverage
  file_patterns:
    endpoints: app/api/v1/endpoints/*.py
    models: app/models/*.py
    schemas: app/schemas/*.py
    tests: tests/integration/test_*.py

# Skill uses this context to:
# - Suggest correct file paths
# - Apply project conventions
# - Reference existing examples
# - Enforce project standards
```

---

## Integration Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    KEEL CLI Commands                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  agent project create                                       │
│    └─> [NEW] Apply methodology pack?                       │
│        ├─ YES: Add methodology skills + config              │
│        └─ NO: Standard project                              │
│                                                             │
│  agent code onboard <repo>                                  │
│    ├─ Analyze codebase                                      │
│    ├─ Ask questions                                         │
│    ├─ Generate understanding doc                            │
│    ├─ Generate project-specific skills                      │
│    └─ Apply methodology pack                                │
│                                                             │
│  agent run --path <project> --task "..."                   │
│    └─> Load .keel/methodology.yaml                           │
│        ├─ Design Phase (design-brainstorm-skill)            │
│        ├─ [CHECKPOINT] User approves design                 │
│        ├─ Planning Phase (implementation-planning-skill)    │
│        ├─ [CHECKPOINT] User approves plan                   │
│        ├─ Execution Phase (TDD-enforced)                    │
│        │  ├─ Dispatch subagents (one per task)             │
│        │  └─ Enforce: RED → GREEN → REFACTOR               │
│        ├─ [CHECKPOINT] Tests must pass                      │
│        ├─ Review Phase (code-review-skill)                  │
│        └─ [CHECKPOINT] Code review approval                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│           KEEL Project Framework (.skills/, .keel/)           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  .skills/                                                   │
│  ├─ domain/        (from --domain flag)                     │
│  ├─ generated/     (from code onboarding)                   │
│  ├─ methodology/   (from methodology pack)                  │
│  └─ user-created/  (manual)                                 │
│                                                             │
│  .keel/                                                      │
│  ├─ codebase-understanding.md                               │
│  ├─ methodology.yaml                                        │
│  └─ approvals/                                              │
│     ├─ design-<uuid>/                                       │
│     │  ├─ proposal.json                                     │
│     │  └─ approval.json                                     │
│     ├─ plan-<uuid>/                                         │
│     │  ├─ tasks.json                                        │
│     │  └─ approval.json                                     │
│     └─ review-<uuid>/                                       │
│        ├─ diff.json                                         │
│        └─ approval.json                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│          Agent Playground Dashboard Integration            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Approvals Panel                                            │
│  ├─ Shows pending design reviews                            │
│  ├─ Shows pending plan reviews                              │
│  ├─ Shows pending code reviews                              │
│  └─ Allows approve/reject with feedback                     │
│                                                             │
│  Skill Execution Tracker                                    │
│  ├─ Shows current phase                                     │
│  ├─ Shows checkpoint status                                 │
│  ├─ Shows task progress                                     │
│  └─ Shows evidence captured                                 │
│                                                             │
│  Code Onboarding Progress                                   │
│  ├─ Analysis results                                        │
│  ├─ Q&A interaction                                         │
│  ├─ Generated understanding doc                             │
│  └─ Auto-generated skills                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│              Activity Tracker & Audit Trail                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  record_activity()                                          │
│  ├─ Command: "skill:execute"                                │
│  ├─ Subcommand: "design-brainstorm"                         │
│  ├─ Metadata:                                               │
│  │  ├─ approval_id: <uuid>                                  │
│  │  ├─ phase: design                                        │
│  │  ├─ status: pending_approval                             │
│  │  └─ checkpoint_timeout: 2026-05-04T12:30:00Z            │
│  └─ Evidence: Full approval JSON                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Checkpoint Storage & Approval State Machine

**Approval State Flow:**
```
.keel/approvals/design-<uuid>/
├── proposal.json          # Agent's design proposal
│   └─ Questions asked + user answers
│   └─ Design sections (Summary, Rationale, Alternatives)
│   └─ Affected files + architecture diagrams
│
├── approval.json          # Approval decision
│   ├─ Status: pending | approved | rejected
│   ├─ Reviewer: user@company.com
│   ├─ Timestamp: 2026-05-04T10:35:00Z
│   ├─ Feedback: "Looks good, proceed" OR "Need refresh token rotation"
│   └─ Approval context: [what was approved]
│
└── evidence.json          # Audit trail
    ├─ Created: 2026-05-04T10:00:00Z
    ├─ Agent: backend-dev-agent
    ├─ Task: Add user authentication
    ├─ Method: agent run command
    ├─ User: developer@company.com
    └─ Status: pending_approval
```

**Similar Structure for Plan & Review Approvals**

---

## CLI Commands for Approval Workflow

```bash
# View pending approvals
agent approvals list                    # Show all pending approvals
agent approvals list --type design      # Show only design approvals
agent approvals show <approval-id>      # Show specific approval details

# Approve/Reject
agent approve <approval-id>             # Approve (interactive feedback prompt)
agent approve <approval-id> --message "Looks good!"
agent reject <approval-id> --reason "Need to add X"

# Resume execution after approval
agent run --continue <approval-id>      # Resume from where it stopped
agent run --path ./my-project --continue <approval-id>

# View approval history
agent approvals history --project ./my-project
agent approvals history --agent backend-dev-agent
```

---

## Execution Flow Summary

### Typical User Workflow

```bash
# 1. Create project with methodology
$ agent project create my-backend --use-case rag
   ↓ Asks: Apply methodology pack? (YES)
   ↓ Creates project + adds methodology skills

# 2. Run agent with a task
$ agent run --path ./my-backend --task "Add user auth"
   ↓ Phase 1: Design (asks questions, waits for approval)
   ↓ [User checks Agent Playground > Approvals panel]
   ↓ [User clicks: Approve]
   ↓ Resumes execution → Phase 2: Planning
   ↓ [User approves plan in dashboard]
   ↓ Phase 3: Execution (TDD-enforced, runs subagents)
   ↓ Phase 4: Review (code quality checks)
   ↓ [User approves code review in dashboard]
   ✅ Feature complete with full audit trail

# 3. View what was done
$ agent approvals history --project ./my-backend
   Shows: 3 approvals (design, plan, code review)
   Shows: Full evidence chain
   Shows: What was approved, feedback, timestamps
```

---

## Implementation Checklist

### Backend CLI Changes
- [ ] Update `project create` to offer methodology packs
- [ ] Update `agent run` to load `.keel/methodology.yaml`
- [ ] Implement skill workflow orchestrator
- [ ] Add approval gate enforcement
- [ ] Create `approvals` command group
- [ ] Add evidence capture to `record_activity`

### Dashboard Backend API Changes
- [ ] `POST /api/approvals/{id}/approve` - approve with feedback
- [ ] `POST /api/approvals/{id}/reject` - reject with reason
- [ ] `GET /api/approvals/pending` - pending list
- [ ] `GET /api/approvals/{id}` - approval details
- [ ] `GET /api/approvals/history` - history timeline

### Dashboard Frontend Changes
- [ ] Approvals page (new)
- [ ] ApprovalCard component
- [ ] ApprovalModal component (design/plan/review)
- [ ] ApprovalTimeline component
- [ ] Skill execution progress component

### Project Structure Changes
- [ ] Add `.keel/methodology.yaml` template
- [ ] Add `.keel/approvals/` directory structure
- [ ] Create approval state machine logic
- [ ] Integrate with skill execution engine

---

This architecture ensures that **skill workflows execute naturally within the KEEL project framework**, with full approval gating, evidence capture, and audit trails integrated at every step.
