# Code Onboarding vs Agent Run - Clarification

**Date**: May 6, 2026  
**Question**: Code onboarding is for repository preparation, not agent execution. How does Windsurf pick up skills and context?

---

## The Key Distinction

### Agent Run (Custom Agents)
```
Purpose: Execute a custom agent to perform a task
Scope: Agent-driven development
Workflow: Design → Plan → Execute → Review (agent-driven)
Example: agent run --path ./my-agent-project --task "..."

Used for:
├─ Custom agents with specific workflows
├─ Autonomous task execution
├─ Approval-gated development
└─ Full methodology enforcement
```

### Code Onboarding (Repository Preparation)
```
Purpose: Prepare a repository for future development
Scope: Repository-ready state
Workflow: Analyze → Extract → Generate → Store (one-time)
Example: dva code onboard --path ./facility-service --kg

Used for:
├─ Preparing repositories for development
├─ Extracting business context (KG)
├─ Generating domain-aware skills
├─ Creating project context documents
└─ Making repo ready for Windsurf/IDE tools
```

---

## Code Onboarding Flow (Repository Preparation)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Code Onboarding Phase                        │
│              (Prepare Repository for Development)               │
└─────────────────────────────────────────────────────────────────┘

$ dva code onboard --path ./facility-service --kg

Step 1: Analyze Repository
├─ Detect: Languages, frameworks, dependencies
├─ Detect: Code patterns, conventions
└─ Store: analysis.json in .dva/onboarding/

Step 2: Query KG for Domain Knowledge
├─ Domain: cwow-facility
├─ Extract: SLAs, integration specs, security policies
└─ Store: domain_knowledge.json in .dva/onboarding/

Step 3: Generate Understanding Document
├─ Create: .dva/codebase-understanding.md
├─ Include: Architecture, key files, development workflow
└─ Include: Testing strategy, common patterns

Step 4: Generate Domain-Aware Skills
├─ Create: .skills/generated/fhir-api-endpoint-skill/
├─ Create: .skills/generated/database-optimizer-skill/
├─ Create: .skills/generated/security-validator-skill/
└─ Create: .skills/generated/sla-monitor-skill/

Step 5: Create Project Context
├─ Create: .dva/methodology.yaml
├─ Create: .domain-context.json
└─ Create: kg-context.md

Step 6: Store Everything in Repository
├─ .skills/ (generated domain-aware skills)
├─ .dva/ (project context, understanding docs)
├─ kg-context.md (hybrid context)
└─ .domain-context.json (domain metadata)

✅ RESULT: Repository is now ready for development
   ├─ Skills available for use
   ├─ Context available for reference
   ├─ Methodology configured
   └─ Ready for Windsurf/IDE tools to use
```

---

## After Code Onboarding - Repository Structure

```
facility-service/
├── src/
│   ├── main.py
│   ├── models/
│   ├── api/
│   └── services/
├── tests/
│
├── .skills/                          # Generated skills
│   ├── domain/                       # Domain persona skills
│   │   ├── backend-dev-skill/
│   │   ├── backend-qa-skill/
│   │   └── backend-sm-skill/
│   │
│   ├── generated/                    # From code onboarding
│   │   ├── fhir-api-endpoint-skill/
│   │   │   ├── SKILL.md (with KG context)
│   │   │   ├── examples/
│   │   │   └── templates/
│   │   ├── database-optimizer-skill/
│   │   ├── security-validator-skill/
│   │   └── sla-monitor-skill/
│   │
│   └── methodology/                  # Methodology skills
│       ├── design-brainstorm-skill/
│       ├── implementation-planning-skill/
│       ├── test-driven-development-skill/
│       └── code-review-skill/
│
├── .dva/                             # Project context
│   ├── codebase-understanding.md     # Generated understanding doc
│   ├── methodology.yaml              # Workflow configuration
│   ├── onboarding/
│   │   ├── analysis.json             # Code analysis
│   │   ├── domain_knowledge.json     # KG extracted knowledge
│   │   └── questionnaire.json        # Q&A from onboarding
│   └── approvals/                    # For future agent runs
│
├── kg-context.md                     # Hybrid context (code + business)
├── .domain-context.json              # Domain metadata
├── .env                              # Environment config
├── pyproject.toml
└── README.md
```

---

## Windsurf Integration - How It Picks Up Skills and Context

### Scenario: Developer Opens Repository in Windsurf

```
1. Developer opens facility-service in Windsurf
   └─ Windsurf detects .skills/ directory
   └─ Windsurf detects .dva/ directory
   └─ Windsurf detects .domain-context.json

2. Windsurf Initialization
   ├─ Reads .domain-context.json
   │  └─ Identifies domain: cwow-facility
   │  └─ Identifies project type: backend-development
   │
   ├─ Loads .dva/codebase-understanding.md
   │  └─ Understands architecture
   │  └─ Understands conventions
   │  └─ Understands development workflow
   │
   ├─ Loads .dva/methodology.yaml
   │  └─ Understands workflow phases
   │  └─ Understands approval gates
   │
   ├─ Discovers .skills/generated/
   │  └─ Loads fhir-api-endpoint-skill/SKILL.md
   │  └─ Loads database-optimizer-skill/SKILL.md
   │  └─ Loads security-validator-skill/SKILL.md
   │  └─ Loads sla-monitor-skill/SKILL.md
   │
   └─ Reads kg-context.md
      └─ Understands business requirements
      └─ Understands SLAs, integration specs, security policies

3. Windsurf Context Available
   ├─ Skills context: What can be done?
   ├─ Project context: How to do it?
   ├─ Business context: Why do it?
   └─ Code context: Where to do it?

4. Developer Starts Development Task
   ├─ "Add FHIR Patient endpoint"
   │
   ├─ Windsurf suggests:
   │  ├─ Use fhir-api-endpoint-skill (from .skills/)
   │  ├─ Follow conventions from .dva/codebase-understanding.md
   │  ├─ Implement OAuth 2.0 (from kg-context.md)
   │  ├─ Ensure < 100ms response (from kg-context.md SLA)
   │  └─ Add HIPAA audit logging (from kg-context.md)
   │
   └─ Developer implements with full context
```

---

## How Windsurf Uses Generated Skills

### SKILL.md Structure (Available to Windsurf)

```yaml
---
name: fhir-api-endpoint-skill
description: Develop FHIR API endpoints for facility domain
domain: cwow-facility
version: 1.0.0

# KG CONTEXT (Windsurf reads this)
kg_context:
  domain: cwow-facility
  integration_specs:
    - type: FHIR API
      endpoint: https://fhir.example.com/api/v1
      authentication: OAuth 2.0
      format: FHIR R4
  security_policies:
    - type: HIPAA compliance
      requirement: required
      encryption_at_rest: AES-256
  slas:
    - type: Response time
      value: < 100ms
      implication: "Use caching, optimize queries"

# PROJECT CONTEXT (Windsurf reads this)
project_context:
  tech_stack: [Python, FastAPI, PostgreSQL, pytest]
  conventions:
    naming: snake_case
    api_versioning: /api/v1/
    error_handling: custom-exception-hierarchy
  file_patterns:
    endpoints: app/api/v1/endpoints/*.py
    models: app/models/*.py
    tests: tests/integration/test_*.py

# CAPABILITIES (Windsurf knows what this skill enables)
capabilities:
  - create-fhir-endpoint
  - add-oauth2-authentication
  - add-fhir-validation
  - add-hipaa-audit-logging
  - add-response-time-monitoring

# EXAMPLES (Windsurf can reference these)
examples:
  - name: "Create FHIR Patient endpoint"
    description: "Endpoint to fetch patient data"
    code: |
      @router.get("/api/v1/patients/{patient_id}")
      async def get_patient(patient_id: str, current_user: User = Depends(oauth2_scheme)):
          """Get patient data from FHIR server.
          
          - Validates OAuth 2.0 token
          - Fetches from FHIR API
          - Validates response against FHIR R4
          - Logs access for HIPAA audit trail
          - Caches for < 100ms response time
          """
          # Implementation
```

### Windsurf Usage Scenarios

#### Scenario 1: Code Completion
```
Developer types: "def get_patient"
Windsurf reads: fhir-api-endpoint-skill/SKILL.md
Windsurf suggests:
├─ Function signature with OAuth 2.0 validation
├─ FHIR validation code
├─ HIPAA audit logging
├─ Caching for SLA compliance
└─ Error handling patterns
```

#### Scenario 2: Code Review
```
Developer submits code for review
Windsurf reads: fhir-api-endpoint-skill/SKILL.md
Windsurf checks:
├─ ✅ OAuth 2.0 validation present?
├─ ✅ FHIR validation present?
├─ ✅ HIPAA audit logging present?
├─ ✅ Response time < 100ms (caching)?
└─ ✅ Error handling consistent?
```

#### Scenario 3: Documentation
```
Developer asks: "What should this endpoint do?"
Windsurf reads: fhir-api-endpoint-skill/SKILL.md
Windsurf provides:
├─ Capability description
├─ KG context (FHIR API, OAuth 2.0)
├─ SLA implications (< 100ms)
├─ Security requirements (HIPAA, AES-256)
└─ Example code
```

#### Scenario 4: Refactoring
```
Developer asks: "How should I structure this?"
Windsurf reads: .dva/codebase-understanding.md
Windsurf suggests:
├─ File patterns from project_context
├─ Naming conventions
├─ Error handling patterns
├─ Testing strategy
└─ Common patterns in the codebase
```

---

## Codebase Understanding Document (Available to Windsurf)

### .dva/codebase-understanding.md

```markdown
# Facility Service - Codebase Understanding

## Architecture Overview
├─ API Layer (FastAPI middleware, dependency injection)
├─ Business Logic (Domain models, repositories)
├─ Data Layer (SQLAlchemy ORM, Alembic migrations)
└─ Infrastructure (Docker, k8s, monitoring stack)

## Key Files & Purposes
├─ app/main.py → FastAPI app initialization
├─ app/api/ → Route handlers (v1, v2)
├─ app/models/ → SQLAlchemy ORM models
├─ app/schemas/ → Pydantic request/response schemas
├─ app/services/ → Business logic layer
├─ tests/unit/ → Unit tests (pytest)
├─ tests/integration/ → API integration tests
├─ migrations/ → Alembic database migrations
└─ docker-compose.yml → Local dev environment

## Development Workflow
1. Create feature branch from main
2. Add tests first (RED phase)
3. Implement feature (GREEN phase)
4. Refactor (REFACTOR phase)
5. Create PR with test evidence
6. Automated checks + human review
7. Squash merge to main

## Testing Strategy
├─ Unit tests: Models, utilities, helpers
├─ Integration tests: API endpoints, database
├─ E2E tests: User workflows (staging only)
├─ Performance tests: Load testing with k6
└─ Coverage: Minimum 80% required

## Common Patterns
├─ API Versioning: /api/v1, /api/v2
├─ Error Handling: Custom exception hierarchy
├─ Async Operations: Celery for background jobs
├─ Caching: Redis layer for hot data
└─ Security: JWT + role-based access control
```

---

## Business Context Document (Available to Windsurf)

### kg-context.md

```markdown
# Facility Service - Business Context

## SLAs
- Response time < 100ms
- Availability > 99.9%

## Integration Requirements
- FHIR API integration
- OAuth 2.0 authentication

## Security Requirements
- HIPAA compliance
- AES-256 encryption
- Audit logging for all PHI access

## Performance Requirements
- 10K concurrent users
- DB latency < 50ms

## Code Structure
[From Graphify analysis]
- 45 code nodes
- 5 code communities
- FacilityService is highly connected

## Repository Overview
[From GitIngest]
- Python 3.9+ with FastAPI
- PostgreSQL database
- 120 files, 25 dependencies
```

---

## Domain Context Metadata (Available to Windsurf)

### .domain-context.json

```json
{
  "domain": "cwow-facility",
  "project_type": "backend-development",
  "tech_stack": ["Python", "FastAPI", "PostgreSQL", "pytest"],
  "methodology": "backend-development",
  "skills": [
    {
      "name": "fhir-api-endpoint-skill",
      "path": ".skills/generated/fhir-api-endpoint-skill",
      "type": "domain-specific"
    },
    {
      "name": "database-optimizer-skill",
      "path": ".skills/generated/database-optimizer-skill",
      "type": "domain-specific"
    },
    {
      "name": "security-validator-skill",
      "path": ".skills/generated/security-validator-skill",
      "type": "domain-specific"
    },
    {
      "name": "sla-monitor-skill",
      "path": ".skills/generated/sla-monitor-skill",
      "type": "domain-specific"
    }
  ],
  "slas": {
    "response_time_ms": 100,
    "availability_percent": 99.9
  },
  "integrations": ["FHIR API", "OAuth 2.0"],
  "security_policies": ["HIPAA compliance", "AES-256 encryption"],
  "performance_requirements": {
    "concurrent_users": 10000,
    "db_latency_ms": 50
  }
}
```

---

## Windsurf Extension Points

### How Windsurf Integrates

```
Windsurf IDE
├─ Reads .domain-context.json on startup
├─ Loads all SKILL.md files from .skills/
├─ Reads .dva/codebase-understanding.md
├─ Reads kg-context.md
│
├─ Provides context to:
│  ├─ Code completion (IntelliSense)
│  ├─ Code suggestions
│  ├─ Code review
│  ├─ Refactoring suggestions
│  ├─ Documentation generation
│  └─ Testing suggestions
│
└─ Available to developer via:
   ├─ Inline suggestions
   ├─ Context panel
   ├─ Command palette
   ├─ Hover tooltips
   └─ Chat/assistant features
```

---

## Complete Workflow: Code Onboarding → Windsurf Development

### Step 1: Code Onboarding (One-Time Setup)
```bash
$ dva code onboard --path ./facility-service --kg

✓ Analyzed code structure
✓ Queried KG for cwow-facility domain
✓ Generated kg-context.md
✓ Generated 4 domain-aware skills
✓ Created .dva/codebase-understanding.md
✓ Created .dva/methodology.yaml
✓ Created .domain-context.json

Result: Repository is ready for development
```

### Step 2: Repository Structure Ready
```
facility-service/
├── .skills/generated/
│   ├── fhir-api-endpoint-skill/SKILL.md (with KG context)
│   ├── database-optimizer-skill/SKILL.md (with KG context)
│   ├── security-validator-skill/SKILL.md (with KG context)
│   └── sla-monitor-skill/SKILL.md (with KG context)
├── .dva/
│   ├── codebase-understanding.md
│   └── methodology.yaml
├── kg-context.md
└── .domain-context.json
```

### Step 3: Developer Opens in Windsurf
```
$ windsurf ./facility-service

Windsurf detects:
├─ .domain-context.json → Loads domain metadata
├─ .skills/ → Loads all SKILL.md files
├─ .dva/codebase-understanding.md → Loads project context
└─ kg-context.md → Loads business context

Windsurf is now context-aware for development
```

### Step 4: Developer Starts Development
```
Developer: "I need to add a FHIR Patient endpoint"

Windsurf provides:
├─ Suggestions from fhir-api-endpoint-skill/SKILL.md
├─ Code patterns from .dva/codebase-understanding.md
├─ Business requirements from kg-context.md
├─ File location suggestions from project_context
├─ Example code from SKILL.md examples
└─ Testing patterns from codebase-understanding.md

Developer implements with full context
```

### Step 5: Development Continues
```
For any future task:
├─ Developer opens facility-service in Windsurf
├─ Windsurf loads all context automatically
├─ Developer gets suggestions based on:
│  ├─ Domain-aware skills
│  ├─ Business requirements (KG)
│  ├─ Code patterns (codebase understanding)
│  └─ Project conventions
└─ Development is guided by context
```

---

## Key Differences: Agent Run vs Code Onboarding

| Aspect | Agent Run | Code Onboarding |
|--------|-----------|-----------------|
| **Purpose** | Execute agent autonomously | Prepare repository for development |
| **Scope** | Custom agents | Repository preparation |
| **Workflow** | Design → Plan → Execute → Review | Analyze → Extract → Generate → Store |
| **Execution** | Agent-driven | One-time setup |
| **Approval Gates** | Yes (design, plan, review) | No (preparation only) |
| **Output** | Code changes + evidence | Skills + context + documentation |
| **Used By** | Custom agents | Windsurf/IDE tools |
| **Frequency** | Per task | One-time per repository |
| **Human Involvement** | Approval checkpoints | None (preparation) |

---

## Summary

### Code Onboarding Purpose

```
Code Onboarding
├─ Prepares repository for development
├─ Extracts business context from KG
├─ Generates domain-aware skills
├─ Creates project understanding documents
├─ Stores everything in repository
└─ Makes repository ready for Windsurf/IDE tools
```

### Windsurf Integration

```
Windsurf opens repository
├─ Detects .domain-context.json
├─ Loads all SKILL.md files
├─ Reads .dva/codebase-understanding.md
├─ Reads kg-context.md
├─ Becomes context-aware
└─ Provides intelligent suggestions for development
```

### Developer Experience

```
Developer opens facility-service in Windsurf
├─ Full context available
├─ Skills suggestions available
├─ Business requirements visible
├─ Code patterns understood
├─ Development is guided by context
└─ No need for agent execution
```

### Key Points

✅ **Code onboarding prepares the repository** - Not for agent execution  
✅ **Skills are stored in .skills/ directory** - Available for Windsurf to use  
✅ **Context is stored in .dva/ and kg-context.md** - Available for Windsurf to read  
✅ **Windsurf picks up context automatically** - No manual configuration needed  
✅ **Developer gets intelligent suggestions** - Based on domain, business, and code context  
✅ **No agent execution needed** - Windsurf provides all necessary guidance  

**Result**: Repository is fully prepared for development with all context and skills available to Windsurf/IDE tools.
