# Superpowers Analysis for Agentic Platform

## What Superpowers Does (Reference Point)

Superpowers is a **structured software development methodology** for coding agents, not just a template system. It enforces:

```
Brainstorm → Design → Plan → Execute → Test
```

With **composable skills** that agents use autonomously but with human checkpoints.

## Key Superpowers Insights for Agentic CLI

### 1. Skills Should Enforce Methodology, Not Just Tools

**Superpowers Approach:**
- Skill: "Brainstorming" - forces clarifying questions before design
- Skill: "Writing Plans" - breaks work into 2-5 minute tasks
- Skill: "Test-Driven Development" - enforces RED-GREEN-REFACTOR
- Skill: "Subagent-Driven Development" - dispatches parallel agents with review

**How to Apply to Agentic CLI:**
```
Current: Skills = "use this tool" (Jira, Bitbucket, etc.)
Better:  Skills = "follow this methodology" (Design Pattern, Code Review, Testing)
```

Skills should guide **how agents work**, not just **what tools they use**.

### 2. Code Onboarding = Structured Understanding

**Superpowers Pattern:**
- Agent asks clarifying questions before coding
- Presents design in digestible sections
- Creates implementation plan with exact file paths

**For Agentic CLI Code Onboarding:**
```
Command: agent code onboard <repo>
  ├─ Analyze: Repository structure, tech stack, conventions
  ├─ Brainstorm: What's the codebase trying to do?
  ├─ Plan: Create understanding document with:
  │   ├─ Architecture overview
  │   ├─ Key files and their purposes
  │   ├─ Development workflow
  │   ├─ Testing strategy
  │   └─ Common patterns
  └─ Skills: Generate domain-specific skills from findings
```

### 3. Skills Should Form a Coherent Development Workflow

**Superpowers Skills Stack:**
1. **Brainstorming Skill** → Clarify requirements
2. **Git Worktrees Skill** → Isolate work
3. **Writing Plans Skill** → Break into chunks
4. **Subagent-Driven Dev Skill** → Execute in parallel with review
5. **TDD Skill** → Enforce testing methodology

**For Agentic CLI - Recommended Skill Categories:**

#### Phase 1: Understanding & Planning
- `code-analysis-skill` - Understand repository structure
- `design-brainstorm-skill` - Question clarification & design approval
- `implementation-planning-skill` - Break tasks into 2-5 min chunks
- `architecture-mapping-skill` - Visualize tech stack & dependencies

#### Phase 2: Development Methodology
- `test-driven-development-skill` - RED-GREEN-REFACTOR enforcement
- `code-review-skill` - Spec compliance + quality review
- `git-workflow-skill` - Branching, commits, worktrees
- `documentation-skill` - Keep docs in sync with code

#### Phase 3: Collaboration & Quality
- `subagent-orchestration-skill` - Dispatch parallel tasks
- `integration-testing-skill` - Multi-component testing
- `refactoring-skill` - Systematic code improvement
- `debugging-skill` - Root cause analysis methodology

#### Phase 4: Deployment & Operations
- `deployment-skill` - Safe deployment practices
- `monitoring-skill` - Health checks & observability
- `rollback-skill` - Incident recovery
- `performance-optimization-skill` - Profiling & tuning

### 4. Skills Should Support Autonomous But Guided Agents

**Superpowers Model:**
```
Agent: "Here's my design"
Human: [Reviews & approves sections]
Agent: [Proceeds with implementation knowing it's aligned]
```

**For Agentic CLI:**
- Skills include "ask for approval" as a checkpoint
- Skills define when human input is **required** vs **optional**
- Skills track approval state and refuse to proceed without it
- Dashboard shows approval history and checkpoints

### 5. Code Onboarding Should Generate Skills

**Superpowers Insight:** Every project has patterns and conventions

**For Agentic CLI:**
```bash
agent code onboard <repo> --auto-skills
  └─ Generates skills from:
     ├─ Architecture patterns detected
     ├─ Testing conventions found
     ├─ Common code structures
     ├─ Domain-specific terminology
     └─ Team practices documented

Example skills generated:
  ✓ react-component-testing-skill
  ✓ fastapi-endpoint-pattern-skill
  ✓ database-migration-skill
  ✓ monorepo-workspace-skill
```

## Revised Starter Pack Concept

**NOT:** "Pick a template and scaffold it"

**YES:** "Pick a methodology and let agents guide you through it"

### New Starter Pack Definition

Instead of pre-built agents, offer **methodologies**:

```
Starter Methodology Packs:
├─ "Backend Development"
│  ├─ Design → Code → Test → Deploy workflow
│  ├─ Skills: API design, database migrations, API testing, monitoring
│  └─ Best practices: OpenAPI-first, TDD, git flow
│
├─ "Data Pipeline Development"
│  ├─ Explore → Plan → Build → Validate workflow
│  ├─ Skills: Data profiling, pipeline design, data quality, documentation
│  └─ Best practices: Reproducibility, lineage tracking, testing
│
├─ "Frontend Development"
│  ├─ Design → Component → Test → Review workflow
│  ├─ Skills: Component design, accessibility, E2E testing, performance
│  └─ Best practices: Atomic design, prop documentation, visual regression
│
├─ "DevOps & Infrastructure"
│  ├─ Plan → Code → Test → Deploy → Monitor workflow
│  ├─ Skills: IaC design, security scanning, integration testing, runbooks
│  └─ Best practices: GitOps, immutable infrastructure, chaos testing
│
└─ "Code Review & Refactoring"
   ├─ Analyze → Design → Refactor → Test → Review workflow
   ├─ Skills: Architecture analysis, refactoring patterns, automated testing, documentation
   └─ Best practices: Conservative changes, regression testing, incremental rollout
```

## How This Changes Our Dashboard/Platform

### Remove (Cosmetic)
- ❌ "Starter Packs" cards showing pre-built templates
- ❌ Generic "Install Starter Pack" buttons

### Add (Methodology-Based)
- ✅ **Methodologies** page with workflow visualization
- ✅ **Skill Sets** grouped by development phase
- ✅ **Agent Personas** (Backend Dev, Data Engineer, DevOps Engineer, QA, DevOps)
- ✅ **Approval Workflows** for design/planning checkpoints
- ✅ **Development Trackers** showing progress through methodology phases
- ✅ **Skill Generation** from code analysis

## Concrete Example: Code Onboarding with Superpowers Methodology

```bash
$ agent code onboard https://github.com/myteam/backend

Agent: Analyzing repository...
✓ Detected: Python 3.11, FastAPI, PostgreSQL, pytest
✓ Identified patterns: API-first, dependency injection, middleware stack
✓ Found conventions: snake_case, docstring style, testing structure

Agent: Before we generate skills, let me understand your architecture.
Using "Backend Development Methodology" skill set:

BRAINSTORM PHASE
================
? What is the primary business domain?
  > Inventory management system

? What are the key constraints?
  > Real-time updates, sub-100ms latency, 10K req/min scale

? Who are the users?
  > Team of 4 backend engineers, all proficient with TDD

? Integration points?
  > Stripe (payments), Datadog (monitoring), AWS S3 (files)

✓ Design questions complete. Generating understanding document...

DESIGN DOCUMENT
===============
Repository: myteam/backend
Framework: FastAPI + PostgreSQL
Scale: 10K requests/min, sub-100ms latency
Domain: Inventory & Order Management
Key Entities: Products, Warehouses, Orders, Transactions
Team: 4 engineers, TDD-focused

ARCHITECTURE OVERVIEW
├─ API Layer (FastAPI middleware, dependency injection)
├─ Business Logic (Domain models, repositories)
├─ Data Layer (SQLAlchemy ORM, Alembic migrations)
└─ Infrastructure (Docker, k8s, monitoring stack)

KEY FILES & PURPOSES
├─ app/main.py → FastAPI app initialization
├─ app/api/ → Route handlers (v1, v2)
├─ app/models/ → SQLAlchemy ORM models
├─ app/schemas/ → Pydantic request/response schemas
├─ app/services/ → Business logic layer
├─ tests/unit/ → Unit tests (pytest)
├─ tests/integration/ → API integration tests
├─ migrations/ → Alembic database migrations
└─ docker-compose.yml → Local dev environment

DEVELOPMENT WORKFLOW
1. Create feature branch from main
2. Add tests first (RED phase)
3. Implement feature (GREEN phase)
4. Refactor (REFACTOR phase)
5. Create PR with test evidence
6. Automated checks + human review
7. Squash merge to main

TESTING STRATEGY
├─ Unit tests: Models, utilities, helpers
├─ Integration tests: API endpoints, database
├─ E2E tests: User workflows (staging only)
├─ Performance tests: Load testing with k6
└─ Coverage: Minimum 80% required

COMMON PATTERNS
├─ API Versioning: /api/v1, /api/v2
├─ Error Handling: Custom exception hierarchy
├─ Async Operations: Celery for background jobs
├─ Caching: Redis layer for hot data
└─ Security: JWT + role-based access control

PLANNING PHASE
==============
Agent: "Here's my implementation plan for adding order cancellation feature:"

Task 1 (5min): Add is_cancelled flag to Order model
  Files: app/models/order.py
  Test: tests/unit/models/test_order.py
  Verification: `pytest tests/unit/models/test_order.py::test_cancel_order`

Task 2 (4min): Create cancel_order business logic
  Files: app/services/order_service.py
  Test: tests/unit/services/test_order_service.py
  Verification: `pytest tests/unit/services/test_order_service.py::test_cancel_order_logic`

Task 3 (3min): Add cancel endpoint
  Files: app/api/v1/orders.py
  Test: tests/integration/api/test_order_endpoints.py
  Verification: `pytest tests/integration/api/test_order_endpoints.py::test_cancel_order_endpoint`

Task 4 (2min): Add migration for schema change
  Files: migrations/versions/xxx_add_cancelled_flag.py
  Test: Run local migration: `alembic upgrade head`
  Verification: Check schema changed, no errors

[Human reviews and approves plan]

EXECUTION PHASE
===============
Using "Test-Driven Development Skill":

Task 1: RED → GREEN → REFACTOR
  1. Write failing test
  2. Verify it fails
  3. Write minimal code
  4. Verify test passes
  5. Refactor for clarity

[Agent executes each task with code review checkpoints]

GENERATED SKILLS
================
✓ fastapi-endpoint-development-skill
✓ sqlalchemy-model-skill
✓ database-migration-skill
✓ pytest-integration-testing-skill
✓ api-error-handling-skill
✓ jwt-authentication-skill
✓ redis-caching-skill

[These skills become available for future tasks in this project]
```

## Implementation Roadmap for Agentic CLI

### Phase 1: Refactor Skill System (Week 1-2)
**Current Problem:** Skills are mostly tool integrations (Jira, Bitbucket)

**What to Change:**
- Create **methodology skills** (design, planning, testing, review)
- Add skill **workflow orchestration** (which skills run in sequence)
- Implement **approval checkpoints** in skills
- Add skill **versioning** and **composition**

**New Skill Structure:**
```yaml
---
name: api-endpoint-development-skill
description: Develop REST API endpoints following TDD methodology
domain: backend-development
dependencies:
  - test-driven-development-skill
  - code-review-skill
  - git-workflow-skill

workflow:
  design:
    step: "Ask clarifying questions about endpoint"
    checkpoint: "user-approval"
  planning:
    step: "Create implementation plan with tasks"
    checkpoint: "user-approval"
  execution:
    step: "Execute tasks with subagent dispatch"
    checkpoint: "code-review-required"
  testing:
    step: "Run full test suite"
    checkpoint: "auto" # Passes if tests pass

requirements:
  - "FastAPI project structure"
  - "pytest configured"
  - "SQLAlchemy ORM setup"

capabilities:
  - create-endpoint
  - add-request-validation
  - add-response-schema
  - create-integration-tests
  - handle-errors
  - add-authentication
```

### Phase 2: Enhance Code Onboarding (Week 3-4)
**Current:** `agent code onboard` generates basic skills

**New Approach:**
1. Analyze codebase deeply (architecture, patterns, conventions)
2. Ask clarifying questions about domain/constraints
3. Generate **understanding document** (like Superpowers design doc)
4. Auto-generate **domain-specific skills** from patterns
5. Create **methodology pack** customized for the project

**Command:**
```bash
agent code onboard <repo> --auto-generate-skills --methodology-pack
```

### Phase 3: Implement Approval Workflows (Week 5)
**Add to Dashboard:**
- Approval queue for design/planning phases
- Skill execution tracker with checkpoints
- Human review interface for agent proposals
- Approval history and audit trail

### Phase 4: Refactor Starter Packs (Week 6)
**Replace cosmetic cards with methodologies:**
- Backend Development Methodology Pack
- Data Pipeline Development Methodology Pack
- Frontend Development Methodology Pack
- DevOps & Infrastructure Methodology Pack
- Code Review & Refactoring Methodology Pack

Each includes preset skills, workflow, best practices, and approval checkpoints.

## Comparison: Before vs After

### Before (Current Implementation)
```
Dashboard:
  ├─ Agents (run agents)
  ├─ Skills (list installed skills - mostly tool integrations)
  ├─ Deployments (where to deploy)
  ├─ Starter Packs (template cards)
  └─ Activity (execution logs)

Skills:
  ├─ jira-skill (access Jira)
  ├─ bitbucket-skill (access Bitbucket)
  ├─ confluence-skill (access Confluence)
  └─ custom-domain-skills (user-created)

Workflow:
  └─ Agent runs with skills, user watches logs
```

### After (Superpowers-Inspired)
```
Dashboard:
  ├─ Agents (run agents)
  ├─ Methodologies (development workflows)
  ├─ Skill Sets (grouped by domain)
  ├─ Approvals (design/planning review)
  ├─ Code Onboarding (auto-generate skills)
  ├─ Deployments (where to run)
  └─ Activity + Execution Tracker

Skills:
  ├─ Methodology Skills
  │  ├─ design-brainstorm-skill
  │  ├─ implementation-planning-skill
  │  ├─ test-driven-development-skill
  │  └─ code-review-skill
  │
  ├─ Domain Skills (Backend)
  │  ├─ fastapi-endpoint-skill
  │  ├─ database-migration-skill
  │  └─ api-error-handling-skill
  │
  ├─ Domain Skills (Data)
  │  ├─ data-pipeline-design-skill
  │  ├─ data-quality-skill
  │  └─ data-lineage-skill
  │
  └─ Tool Integration Skills (unchanged)
     ├─ jira-skill
     ├─ bitbucket-skill
     └─ confluence-skill

Workflow:
  1. Design phase (with approval checkpoint)
  2. Planning phase (with approval checkpoint)
  3. Execution phase (with subagent dispatch)
  4. Review phase (with code quality checks)
  5. Test phase (with coverage requirements)
```

## Lessons Learned From Superpowers

| Aspect | Superpowers | Agentic CLI (Apply?) |
|--------|------------|-------------------|
| **Skill Scope** | Methodology enforcement | Yes - shift from tool-only to methodology-based |
| **Code Onboarding** | Structured questions → Design doc | Yes - implement asking phase |
| **Human in Loop** | Approval checkpoints | Yes - add approval dashboard |
| **Task Decomposition** | 2-5 min chunks | Yes - implement planning skill |
| **Testing** | TDD enforcement | Yes - make TDD skill mandatory |
| **Subagents** | Parallel dispatch with review | Yes - already have agent dispatch |
| **Git Workflow** | Worktrees + branch isolation | Yes - enhance git-workflow-skill |
| **Documentation** | Generates understanding docs | Yes - create design doc generation |
| **Skill Generation** | Auto-generate from patterns | Yes - enhance code onboarding |

## Success Metrics (Post-Refactor)

1. ✅ **Code Onboarding** takes < 5 minutes to understand a new codebase
2. ✅ **Design Approval** captures user intent before coding starts
3. ✅ **TDD Enforcement** ensures all generated code has passing tests
4. ✅ **Subagent Coordination** allows parallel development on 5+ tasks simultaneously
5. ✅ **Skill Auto-generation** creates 10+ domain-specific skills per project
6. ✅ **Methodology Packs** reduce time-to-productivity from 1 week to 1 day

## References

- [Superpowers: obra/superpowers on GitHub](https://github.com/obra/superpowers)
- [Superpowers Methodology Blog](https://blog.fsck.com/2025/10/09/superpowers/)
- [Superpowers Skills Architecture](https://github.com/obra/superpowers/tree/main/skills)
