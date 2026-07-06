# Implementation Specifications: Code Onboarding, Approvals, & Methodology Skills

## Part 1: Enhanced Code Onboarding System

### Overview
Transform `agent code onboard` from simple analysis to a complete structured understanding with approval gates and auto-skill generation.

### Command Flow

```bash
$ agent code onboard <repo-url> [--output-dir] [--auto-generate-skills] [--methodology-pack]
```

### Phase 1: Repository Analysis (Automated)

**Input:** Repository URL or local path  
**Output:** Analysis JSON with findings

**What to detect:**
```json
{
  "repository": {
    "name": "backend-api",
    "url": "https://github.com/myteam/backend",
    "path": "/workspace/backend",
    "size_mb": 245,
    "commit_count": 3421,
    "branches_count": 12
  },
  "tech_stack": {
    "languages": {
      "python": 68.5,
      "sql": 15.2,
      "yaml": 10.1,
      "other": 6.2
    },
    "frameworks": ["fastapi", "sqlalchemy", "pytest"],
    "databases": ["postgresql"],
    "infrastructure": ["docker", "kubernetes"],
    "ci_cd": ["github-actions"]
  },
  "project_structure": {
    "src": {
      "main_modules": ["api", "models", "services", "repositories"],
      "test_coverage": 0.82,
      "test_framework": "pytest",
      "test_dir": "tests/"
    },
    "has_makefile": true,
    "has_dockerfile": true,
    "has_docker_compose": true,
    "has_pyproject_toml": true
  },
  "code_patterns": {
    "api_style": "rest",
    "error_handling": "custom-exception-hierarchy",
    "async_pattern": "async-await",
    "dependency_injection": true,
    "middleware_stack": true,
    "orm": "sqlalchemy",
    "validation": "pydantic",
    "authentication": "jwt"
  },
  "conventions": {
    "naming": "snake_case",
    "imports": "organized-with-isort",
    "docstring_style": "google",
    "commit_style": "conventional",
    "branch_naming": "feature/*, bugfix/*, hotfix/*"
  },
  "quality_metrics": {
    "code_coverage": 0.82,
    "type_hints_adoption": 0.91,
    "test_success_rate": 0.98,
    "security_issues": 0,
    "linting_issues": 12
  },
  "estimated_complexity": {
    "overall": "medium",
    "async_complexity": "medium",
    "database_complexity": "high",
    "api_complexity": "medium"
  }
}
```

### Phase 2: Clarifying Questions (Interactive)

After analysis, agent asks structured questions. Store as JSON for reproducibility.

**Question Categories:**

#### A. Business Context (2-3 questions)
```
Q1: "What is the primary business purpose of this codebase?"
    Examples: Inventory management, Payment processing, Data pipeline
    User Answer: "Real-time order management and fulfillment"

Q2: "Who are the primary users of this system?"
    Examples: Internal team, External customers, Other services
    User Answer: "Team of 4 backend engineers + infrastructure team"

Q3: "What are the key business constraints or priorities?"
    Examples: Latency, Throughput, Cost, Security, Reliability
    User Answer: "Sub-100ms latency, 10K req/min scale, PCI-DSS compliance"
```

#### B. Technical Constraints (2-3 questions)
```
Q4: "What is the expected scale and performance target?"
    User Answer: "10K requests/minute, sub-100ms p99 latency"

Q5: "Are there security or compliance requirements?"
    User Answer: "PCI-DSS, OAuth 2.0, JWT tokens, encrypted database"

Q6: "What external systems does this integrate with?"
    User Answer: "Stripe (payments), Datadog (monitoring), S3 (files), Redis (cache)"
```

#### C. Development Practices (2-3 questions)
```
Q7: "What is your testing philosophy?"
    Options: [TDD, Test-after, Integration-first, Manual]
    User Answer: "TDD - write tests first, minimum 80% coverage"

Q8: "What's the typical development workflow?"
    Options: [Trunk-based, Git-flow, Feature-branching]
    User Answer: "Feature branches, require code review, squash merge"

Q9: "Are there team-specific conventions or patterns?"
    User Answer: "Dependency injection for services, middleware for cross-cutting, factory patterns for models"
```

**Store Responses:**
```json
{
  "understanding": {
    "business_context": {
      "domain": "Order Management & Fulfillment",
      "users": "Team of 4 backend engineers",
      "constraints": ["Sub-100ms latency", "10K req/min scale", "PCI-DSS compliance"]
    },
    "technical_context": {
      "scale": "10K requests/minute",
      "compliance": ["PCI-DSS", "OAuth 2.0", "encryption-at-rest"],
      "integrations": ["Stripe", "Datadog", "AWS S3", "Redis"]
    },
    "development_practices": {
      "testing_philosophy": "TDD",
      "workflow": "Feature-branching with code review",
      "conventions": ["Dependency injection", "Middleware patterns", "Factory patterns"]
    }
  }
}
```

### Phase 3: Generate Understanding Document

Combine analysis + responses into structured markdown document.

**Output File:** `.keel/codebase-understanding.md`

```markdown
# Codebase Understanding: Backend API

## Quick Overview
- **Repository:** myteam/backend
- **Purpose:** Real-time order management and fulfillment system
- **Team:** 4 backend engineers (TDD-focused)
- **Scale:** 10K req/min, sub-100ms latency, PCI-DSS compliance

## Technology Stack
- **Language:** Python 3.11
- **Framework:** FastAPI
- **Database:** PostgreSQL + Redis (caching)
- **ORM:** SQLAlchemy
- **Testing:** pytest (82% coverage)
- **Async:** asyncio with async-await pattern
- **Validation:** Pydantic schemas
- **Auth:** JWT tokens + OAuth 2.0

## Architecture Overview
```
┌─ API Layer (FastAPI)
│  ├─ Route handlers (v1, v2)
│  ├─ Dependency injection
│  └─ Middleware stack
├─ Business Logic
│  ├─ Domain models
│  ├─ Services (DDD pattern)
│  └─ Repositories
└─ Data Layer
   ├─ SQLAlchemy ORM
   ├─ PostgreSQL
   └─ Redis cache
```

## Key Files & Their Purposes
- `app/main.py` → FastAPI app initialization
- `app/api/` → Route handlers (v1, v2)
- `app/models/` → SQLAlchemy ORM models
- `app/schemas/` → Pydantic request/response schemas
- `app/services/` → Business logic layer
- `tests/unit/` → Unit tests (pytest)
- `tests/integration/` → API integration tests
- `migrations/` → Alembic database migrations

## Development Workflow
1. Create feature branch from main
2. Write failing test (RED)
3. Implement feature (GREEN)
4. Refactor (REFACTOR)
5. Create PR with test evidence
6. Automated checks + peer review
7. Squash merge to main

## Testing Strategy
- **Unit Tests:** Models, utilities, helpers (minimum 80% coverage)
- **Integration Tests:** API endpoints, database interactions
- **E2E Tests:** User workflows (staging only)
- **Performance:** Load testing with k6

## Common Patterns
- **Error Handling:** Custom exception hierarchy
- **Async Ops:** Background jobs with Celery
- **Caching:** Redis for hot data
- **Security:** JWT + role-based access control
- **API Versioning:** /api/v1, /api/v2

## Integrations
- **Payments:** Stripe API
- **Monitoring:** Datadog APM
- **Storage:** AWS S3
- **Cache:** Redis
```

### Phase 4: Skill Generation

Based on detected patterns + user answers, generate domain-specific skills.

**Generated Skills Example:**
```
✓ fastapi-endpoint-development-skill
✓ sqlalchemy-orm-skill
✓ postgresql-migration-skill
✓ pytest-integration-testing-skill
✓ pydantic-validation-skill
✓ async-coroutine-skill
✓ jwt-authentication-skill
✓ redis-caching-skill
✓ api-error-handling-skill
✓ dependency-injection-skill
```

Each skill is created with:
```yaml
---
name: fastapi-endpoint-development-skill
description: Develop FastAPI endpoints following TDD methodology for this project
domain: backend-development
context: order-management-system
technology_stack:
  - FastAPI
  - Pydantic
  - PostgreSQL
  - pytest

# Methodology enforcement
workflow:
  design:
    description: "Ask clarifying questions about endpoint requirements"
    examples: ["What entity is this endpoint managing?", "Is it read-only or write?"]
    checkpoint: "user-approval"
    
  planning:
    description: "Create task breakdown with exact file paths"
    examples: ["Task 1: Add Pydantic schema in app/schemas/orders.py", "Task 2: Add endpoint..."]
    checkpoint: "user-approval"
    
  execution:
    description: "Execute with TDD: RED → GREEN → REFACTOR"
    methodology: "test-driven-development"
    checkpoint: "test-pass-required"
    
  review:
    description: "Verify endpoint follows project conventions"
    checks: ["Docstring style", "Error handling", "Input validation", "Response codes"]
    checkpoint: "code-review"

# Project-specific context
conventions:
  - "Use Dependency Injection for services"
  - "Validate all inputs with Pydantic"
  - "Custom exception hierarchy for errors"
  - "Async/await for all I/O operations"
  - "Minimum 80% test coverage"

related_patterns:
  - dependency-injection-skill
  - pydantic-validation-skill
  - async-coroutine-skill
  - error-handling-skill

file_templates:
  - path: "app/schemas/*.py"
    description: "Pydantic request/response models"
  - path: "app/api/v1/endpoints/*.py"
    description: "FastAPI route handlers"
  - path: "tests/integration/test_endpoints.py"
    description: "Integration tests"
```

### Phase 5: Create Methodology Pack

Apply best-fit methodology pack based on tech stack and answers.

```
Suggested Methodology Pack: "Backend Development (FastAPI)"

This pack includes:
├─ Phase 1: Design (Ask requirements → Get approval)
├─ Phase 2: Planning (Break into 2-5 min tasks → Get approval)
├─ Phase 3: Execution (Implement with TDD)
├─ Phase 4: Review (Code quality + conventions)
└─ Phase 5: Test (Coverage + integration tests)

Included Skills:
├─ Methodology Skills
│  ├─ design-brainstorm-skill
│  ├─ implementation-planning-skill
│  ├─ test-driven-development-skill
│  └─ code-review-skill
├─ Backend-Specific Skills
│  ├─ fastapi-endpoint-development-skill
│  ├─ postgresql-migration-skill
│  ├─ pydantic-validation-skill
│  └─ error-handling-skill
└─ Quality Assurance
   ├─ pytest-integration-testing-skill
   ├─ performance-testing-skill
   └─ documentation-skill
```

### Implementation Plan

```yaml
backend/src/agentic_cli/commands/code.py:
  - Enhance code_onboard() function with 5-phase flow
  - Add interactive questionnaire (Q&A capture)
  - Implement analysis → questions → document → skills generation
  - Store understanding document in .keel/codebase-understanding.md
  - Create skill generation logic based on patterns + answers

backend/src/agentic_cli/analysis/:
  - Create codebase_analyzer.py (detect patterns, conventions, complexity)
  - Create questionnaire.py (interactive Q&A with validation)
  - Create understanding_generator.py (create markdown documentation)
  - Create skill_generator.py (auto-generate skill definitions)
  - Create methodology_matcher.py (recommend methodology pack)

dashboard/backend/src/api/:
  - Create onboarding.py endpoint: POST /api/onboarding/analyze
  - Add progress tracking: GET /api/onboarding/progress
  - Add approval endpoint: POST /api/onboarding/approve

dashboard/frontend/src/pages/:
  - Create CodeOnboarding.tsx page showing progress
  - Add analysis results visualization
  - Add Q&A interactive form
  - Add generated skills preview
```

---

## Part 2: Approval Workflow Dashboard

### Overview
Add dashboard page showing design/planning reviews with approval gates.

### Dashboard Structure

```
┌─ Agent Playground
   └─ Approvals (New Page)
      ├─ Pending Approvals (Quick)
      ├─ Design Reviews
      │  ├─ Requirement specs
      │  ├─ Architecture decisions
      │  └─ Tech choices
      ├─ Planning Reviews
      │  ├─ Task breakdown
      │  ├─ File paths
      │  └─ Verification steps
      ├─ Code Reviews
      │  ├─ Spec compliance
      │  └─ Quality checks
      └─ Approval History
         ├─ Approved items
         ├─ Rejected items (with feedback)
         └─ Timeline
```

### Approval Item Structure

```json
{
  "id": "apr-uuid",
  "type": "design|plan|code",
  "agent_name": "agent-backend-dev",
  "task_description": "Add user authentication endpoint",
  "phase": "design",
  "status": "pending|approved|rejected",
  "created_at": "2026-05-04T10:30:00Z",
  "expires_at": "2026-05-04T12:30:00Z",
  "content": {
    "summary": "Add JWT-based authentication",
    "details": "Design section 1 of 3...",
    "rationale": "Why this approach?",
    "alternatives": ["Alternative 1", "Alternative 2"]
  },
  "approval": {
    "reviewer": "user@company.com",
    "approved_at": "2026-05-04T10:35:00Z",
    "feedback": "Looks good, proceed with implementation",
    "approval_context": {
      "agreed_requirements": ["..."],
      "approved_scope": ["..."],
      "constraints_acknowledged": ["..."]
    }
  },
  "related_approvals": ["apr-uuid-design-phase"]
}
```

### Page Components

#### 1. Pending Approvals Card
```
┌────────────────────────────────────────┐
│ 🔔 3 Pending Approvals                 │
├────────────────────────────────────────┤
│                                        │
│ 1. Design: User Auth Endpoint (2min)  │
│    Agent: backend-dev                  │
│    Expires: in 1 hour                  │
│    [Review] [Approve] [Reject]         │
│                                        │
│ 2. Plan: Email Service Integration ... │
│ 3. Code: Database Migration Review ... │
│                                        │
└────────────────────────────────────────┘
```

#### 2. Design Review Modal
```
┌─────────────────────────────────────────────────────┐
│ Design Review: Add JWT Authentication               │ [X]
├─────────────────────────────────────────────────────┤
│                                                     │
│ SUMMARY                                             │
│ ├─ Approach: JWT tokens with refresh tokens       │
│ ├─ Storage: Redis for token blacklist             │
│ └─ Scope: User login and protected endpoints      │
│                                                     │
│ RATIONALE                                           │
│ ├─ Stateless authentication scales horizontally  │
│ ├─ Refresh tokens reduce token expiration risk   │
│ └─ Redis blacklist for logout functionality      │
│                                                     │
│ ALTERNATIVES CONSIDERED                            │
│ ├─ Session-based (rejected: requires sticky sessions) │
│ ├─ OAuth 2.0 (deferred: future integration)      │
│                                                     │
│ KEY FILES AFFECTED                                  │
│ ├─ app/auth/jwt.py (new)                          │
│ ├─ app/models/user.py (modify)                    │
│ ├─ app/api/v1/auth.py (new endpoints)             │
│ └─ tests/integration/test_auth.py (new tests)     │
│                                                     │
│ QUESTIONS FOR CLARIFICATION                        │
│ ? Are you comfortable with JWT approach?           │
│ ? Should we implement refresh token rotation?      │
│ ? Do we need additional security headers?          │
│                                                     │
│ [Approve] [Request Changes] [Need Clarification]   │
└─────────────────────────────────────────────────────┘
```

#### 3. Plan Review Modal
```
┌─────────────────────────────────────────────────────┐
│ Plan Review: Implement JWT Authentication           │
├─────────────────────────────────────────────────────┤
│ Status: Waiting for approval (design approved)      │
│                                                     │
│ TASK BREAKDOWN (5 tasks, ~15 minutes)              │
│                                                     │
│ Task 1 (3min): Create JWT utility module           │
│   File: app/auth/jwt.py                            │
│   Test: tests/unit/auth/test_jwt.py               │
│   Verify: Run unit tests, check coverage > 80%    │
│                                                     │
│ Task 2 (2min): Add User model fields              │
│   File: app/models/user.py                         │
│   Test: tests/unit/models/test_user.py            │
│   Verify: Run migration, check schema              │
│                                                     │
│ Task 3 (4min): Create login endpoint              │
│   File: app/api/v1/auth.py                         │
│   Test: tests/integration/api/test_auth.py        │
│   Verify: POST /api/v1/auth/login returns token   │
│                                                     │
│ Task 4 (3min): Add middleware for protected routes │
│   File: app/middleware/jwt_middleware.py           │
│   Test: tests/integration/middleware/test_jwt.py   │
│   Verify: Requests without token return 401        │
│                                                     │
│ Task 5 (2min): Create Redis blacklist service     │
│   File: app/services/token_blacklist.py            │
│   Test: tests/unit/services/test_blacklist.py     │
│   Verify: Blacklisted tokens are rejected          │
│                                                     │
│ [Approve Plan] [Request Changes] [Ask Questions]   │
└─────────────────────────────────────────────────────┘
```

#### 4. Approval History Timeline
```
┌─────────────────────────────────────────────────────┐
│ Approval History                                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 2026-05-04 10:35 ✅ APPROVED: Design - User Auth  │
│   Reviewer: alice@company.com                      │
│   Feedback: "Good approach, proceed"               │
│   Duration: 5 minutes                              │
│                                                     │
│ 2026-05-04 10:15 ⏳ PENDING: Plan - User Auth     │
│   Waiting for: alice@company.com                   │
│   Created: 10:15 (20 minutes ago)                  │
│   Expires: 11:35 (in 1 hour)                       │
│                                                     │
│ 2026-05-03 16:20 ✅ APPROVED: Design - Payments  │
│   Reviewer: bob@company.com                        │
│   Feedback: "Matches system requirements"          │
│   Duration: 8 minutes                              │
│                                                     │
│ 2026-05-03 15:45 ❌ REJECTED: Plan - Caching     │
│   Reviewer: charlie@company.com                    │
│   Feedback: "Need to include cache invalidation"   │
│   Re-submitted: 16:00 (after revision)             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Frontend Implementation

**New Files:**
- `dashboard/frontend/src/pages/Approvals.tsx` - Main page
- `dashboard/frontend/src/components/ApprovalCard.tsx` - Pending item card
- `dashboard/frontend/src/components/ApprovalModal.tsx` - Review interface
- `dashboard/frontend/src/components/ApprovalTimeline.tsx` - History view

**API Endpoints Needed:**
```
GET  /api/approvals/pending          # List pending approvals
GET  /api/approvals/{id}             # Get approval details
POST /api/approvals/{id}/approve     # Submit approval
POST /api/approvals/{id}/reject      # Reject with feedback
GET  /api/approvals/history          # Get approval history
```

### Backend Implementation

**New Files:**
- `dashboard/backend/src/services/approval_service.py` - Business logic
- `dashboard/backend/src/api/approvals.py` - API routes
- `dashboard/backend/src/models/approval.py` - Data model

---

## Part 3: Deep Analysis - Methodology-Based Skills

### Current Problem

**Current Skill Definition (Tool-Focused):**
```yaml
name: jira-skill
description: Access Jira for ticket management
type: tool-integration
endpoints:
  - get-issues
  - create-issue
  - update-issue
  - assign-issue
```

**Problem:** Agents use tools but without enforcing HOW to use them. No methodology, no checkpoints.

### Vision: Methodology-Based Skills

**Methodology Skill Definition (Process-Focused):**
```yaml
name: design-brainstorm-skill
description: Guide agent through structured design thinking before implementing
domain: methodology
enforces:
  - "Ask clarifying questions before designing"
  - "Present design in digestible sections"
  - "Get user approval on critical decisions"
  - "Document rationale and alternatives"
  
workflow_phases:
  1_questions:
    description: Ask 5-7 clarifying questions
    examples: ["What problem are we solving?", "Who are the users?"]
    checkpoint: user-answers-required
    
  2_design:
    description: Present design in 3-5 digestible sections
    sections: [Summary, Rationale, Alternatives, Architecture, Data Model]
    checkpoint: user-approval-required
    
  3_document:
    description: Create design document for reference
    output_file: design-document.md
    checkpoint: auto-pass

approval_gates:
  - phase: questions
    required: true
    timeout: 1-hour
    escalation: send-reminder
    
  - phase: design-approval
    required: true
    timeout: 2-hours
    allowed-outcomes: [approve, request-changes, need-clarification]
```

### Key Characteristics of Methodology Skills

#### 1. **Workflow Phases with Checkpoints**

Each skill enforces a sequence:

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   PHASE 1   │─────>│  CHECKPOINT  │─────>│   PHASE 2    │
│   Do Work   │      │   (Approval) │      │   Continue   │
└─────────────┘      └──────────────┘      └──────────────┘
```

**Example: API Endpoint Development Skill**
```
Phase 1: DESIGN
├─ Ask: What entity? What operations?
├─ Show: API design (request/response)
└─ Checkpoint: User approves design

Phase 2: PLAN
├─ Break: Into 5 tasks (2-5 min each)
├─ Show: File paths, verification steps
└─ Checkpoint: User approves plan

Phase 3: EXECUTE
├─ Run: Subagent per task
├─ TDD: Write test → implement → refactor
└─ Checkpoint: All tests pass

Phase 4: REVIEW
├─ Check: Code quality, conventions
├─ Show: Diff, coverage, lint results
└─ Checkpoint: Code review approval

Phase 5: TEST
├─ Run: Full integration tests
├─ Show: Coverage, performance metrics
└─ Checkpoint: Metrics meet thresholds
```

#### 2. **Skill Composition & Dependencies**

Skills can declare dependencies on other skills:

```yaml
name: api-endpoint-development-skill
domain: backend-development
depends_on:
  - design-brainstorm-skill      # Use for design phase
  - implementation-planning-skill # Use for planning
  - test-driven-development-skill # Use for execution
  - code-review-skill            # Use for review
  - pydantic-validation-skill    # Use for validation
  - error-handling-skill         # Use for error handling

composition:
  design_phase:
    skill: design-brainstorm-skill
    role: primary
    
  planning_phase:
    skill: implementation-planning-skill
    role: primary
    
  execution_phase:
    skill: test-driven-development-skill
    role: primary
    sub_skills: [pydantic-validation-skill, error-handling-skill]
    
  review_phase:
    skill: code-review-skill
    role: primary
    checks: ["Style", "Patterns", "Security"]
```

When `api-endpoint-development-skill` is invoked, it orchestrates a workflow that uses all dependent skills in sequence.

#### 3. **Project-Specific Context**

Skills can be customized with project context learned from code onboarding:

```yaml
name: fastapi-endpoint-development-skill
base_skill: api-endpoint-development-skill
context: order-management-backend

project_conventions:
  - "Use Dependency Injection for services"
  - "Validate with Pydantic schemas"
  - "Custom exception hierarchy"
  - "Async/await for I/O operations"
  - "Minimum 80% test coverage"

file_patterns:
  endpoints: "app/api/v1/endpoints/*.py"
  models: "app/models/*.py"
  schemas: "app/schemas/*.py"
  services: "app/services/*.py"
  tests: "tests/integration/test_*.py"

examples:
  - path: "app/api/v1/endpoints/users.py"
    description: "Existing user endpoint (follow this pattern)"
  - path: "app/schemas/user.py"
    description: "Pydantic schema example"
  - path: "tests/integration/test_users.py"
    description: "Integration test example"

tech_requirements:
  - "FastAPI >= 0.100"
  - "Pydantic >= 2.0"
  - "pytest >= 7.0"
  - "SQLAlchemy >= 2.0"
```

When this skill is invoked, the agent knows:
- How to structure endpoints (from file patterns)
- What conventions to follow (from project_conventions)
- Real examples to reference (from examples)

#### 4. **Approval Gates & Checkpoints**

Each phase can have different approval requirements:

```yaml
checkpoints:
  design_approval:
    required: true
    description: "User approves design before implementation"
    timeout: 2-hours
    escalation: "Send reminder after 1 hour"
    allowed_outcomes:
      - approve
      - request-changes
      - need-clarification
    
  plan_approval:
    required: true
    description: "User approves task breakdown"
    timeout: 1-hour
    escalation: "Send reminder after 30 min"
    allowed_outcomes:
      - approve
      - adjust-tasks
      
  execution_checkpoint:
    required: false  # Optional for simple tasks
    description: "User can view progress, pause if needed"
    auto_checkpoint: "Every 3 tasks or 15 minutes"
    
  test_checkpoint:
    required: true
    description: "Tests must pass before merging"
    threshold: "Coverage >= 80%, All tests pass"
    escalation: "Auto-block if coverage drops"
```

#### 5. **Evidence Capture**

Each phase produces evidence for audit trail:

```json
{
  "skill_execution": {
    "skill_id": "fastapi-endpoint-development-skill",
    "task": "Add user authentication endpoint",
    "phases": [
      {
        "phase": "design",
        "status": "completed",
        "timestamp": "2026-05-04T10:00:00Z",
        "evidence": {
          "questions_asked": 7,
          "user_answers": {...},
          "design_document": "link-to-doc",
          "alternatives_considered": 3,
          "approval": {
            "reviewer": "alice@company.com",
            "timestamp": "2026-05-04T10:35:00Z",
            "feedback": "Looks good, proceed"
          }
        }
      },
      {
        "phase": "planning",
        "status": "completed",
        "timestamp": "2026-05-04T10:35:00Z",
        "evidence": {
          "tasks_created": 5,
          "estimated_time_minutes": 15,
          "approval": {...}
        }
      },
      {
        "phase": "execution",
        "status": "in_progress",
        "timestamp": "2026-05-04T10:40:00Z",
        "evidence": {
          "tasks_completed": 2,
          "tasks_remaining": 3,
          "subagent_assignments": [...]
        }
      }
    ]
  }
}
```

### Skill Taxonomy

Organize skills by their role in the methodology:

#### A. Methodology Skills (Orchestrators)
These enforce HOW work gets done:
```
├─ design-brainstorm-skill
├─ implementation-planning-skill
├─ test-driven-development-skill
├─ code-review-skill
├─ debugging-methodology-skill
├─ refactoring-methodology-skill
└─ documentation-methodology-skill
```

#### B. Domain Skills (Executors)
These know HOW to do specific technical work:
```
Backend Development:
├─ fastapi-endpoint-development-skill
├─ sqlalchemy-orm-skill
├─ postgresql-migration-skill
├─ async-coroutine-skill
└─ error-handling-skill

Frontend Development:
├─ react-component-development-skill
├─ typescript-typing-skill
├─ css-styling-skill
└─ e2e-testing-skill

Data Pipeline:
├─ data-pipeline-design-skill
├─ spark-sql-skill
├─ data-quality-skill
└─ lineage-tracking-skill
```

#### C. Quality Skills (Validators)
These ensure standards are met:
```
├─ code-coverage-validation-skill
├─ performance-validation-skill
├─ security-scanning-skill
├─ documentation-validation-skill
└─ accessibility-validation-skill
```

#### D. Tool Integration Skills (Connectors)
Access external systems:
```
├─ jira-ticket-management-skill
├─ github-pr-management-skill
├─ slack-notification-skill
├─ datadog-monitoring-skill
└─ confluence-documentation-skill
```

### Skill Invocation Patterns

#### Pattern 1: Direct Invocation
```
Agent: "I need to add a new API endpoint"
System: Invoke fastapi-endpoint-development-skill
Flow: Design → Plan → Execute → Review → Test
Checkpoints: 5 approval gates
Result: Complete, tested, reviewed endpoint
```

#### Pattern 2: Composite Invocation
```
Agent: "Refactor this module for performance"
System: Invoke refactoring-methodology-skill
Sub-skills:
  - design-brainstorm-skill (analyze before refactoring)
  - implementation-planning-skill (plan changes)
  - test-driven-development-skill (implement with tests)
  - performance-validation-skill (measure improvements)
  - code-review-skill (peer review)
Result: Refactored code with performance proof
```

#### Pattern 3: Sequential Invocation
```
Command: "Build data pipeline from CSV to warehouse"
Steps:
  1. data-pipeline-design-skill (design flow) → approval
  2. implementation-planning-skill (break into tasks) → approval
  3. spark-sql-skill (implement transformations)
  4. data-quality-skill (validate output)
  5. documentation-methodology-skill (document flow)
Result: Complete pipeline with documentation
```

### Benefits of Methodology Skills

| Aspect | Tool-Focused | Methodology-Based |
|--------|------------|------------------|
| **Control** | Agent freely uses tools | Agent enforces process gates |
| **Quality** | Varies by agent ability | Consistent via methodology |
| **Traceability** | Tool logs only | Full approval trail + evidence |
| **Reusability** | Code sometimes, methodology never | Both code and methodology reusable |
| **Scalability** | More agents = inconsistency | More agents = consistent quality |
| **Knowledge** | Lost when agent stops | Captured in skill definitions |
| **Team Alignment** | Implicit expectations | Explicit methodology enforcement |

### Implementation Roadmap for Methodology Skills

**Phase 1 (Week 1-2): Core Methodology Skills**
- `design-brainstorm-skill` (structured Q&A + design doc)
- `implementation-planning-skill` (task decomposition)
- `test-driven-development-skill` (RED-GREEN-REFACTOR enforcement)
- `code-review-skill` (spec + quality validation)

**Phase 2 (Week 3-4): Domain Skills**
- FastAPI endpoint development
- React component development
- Data pipeline design
- Database migration patterns

**Phase 3 (Week 5-6): Skill Composition**
- Skill dependency resolution
- Composite skill orchestration
- Subagent dispatching with skill context
- Approval gate enforcement

**Phase 4 (Week 7-8): Project Customization**
- Auto-generate skills from code onboarding
- Apply project conventions to skills
- Create methodology packs
- Approval workflow dashboard

---

**Next Steps:**
1. Choose which implementation to start with (Code Onboarding, Approvals, or Methodology Skills)
2. Create detailed PRD for that component
3. Begin implementation with user acceptance criteria
4. Test with real agents and get feedback
