# Code Onboarding Implementation Guide - Complete Reference

**Date**: May 6, 2026  
**Topic**: Code onboarding for repository preparation and Windsurf integration  
**Status**: Ready for implementation

---

## Quick Navigation

### 📚 Core Documents

1. **CODE_ONBOARDING_WINDSURF_INTEGRATION.md** ⭐ START HERE
   - Visual overview of complete flow
   - Repository structure after onboarding
   - Windsurf integration steps
   - Developer experience
   - 10-minute read

2. **docs/plans/CODE_ONBOARDING_VS_AGENT_RUN.md**
   - Detailed distinction between code onboarding and agent run
   - Complete workflow examples
   - Windsurf extension points
   - 20-minute read

3. **docs/plans/KG_CONTEXT_TO_SKILL_WORKFLOW.md**
   - How KG context flows into SKILL files
   - SKILL.md structure with KG context
   - Workflow phase execution
   - 20-minute read

4. **KG_CONTEXT_SKILL_INTEGRATION_INDEX.md**
   - Master index for KG context integration
   - Quick answers to key questions
   - 10-minute read

---

## The Core Concept

### Code Onboarding is Repository Preparation

```
NOT: agent run --path ./facility-service --task "..."
     (This is for custom agents)

YES: keel code onboard --path ./facility-service --kg
     (This prepares the repository)
```

### What Code Onboarding Does

```
Code Onboarding
├─ Analyzes code structure
├─ Queries KG for domain knowledge (cwow-facility only)
├─ Generates domain-aware skills with KG context
├─ Creates project understanding documents
├─ Stores everything in repository
└─ Makes repository ready for Windsurf/IDE tools
```

### What Happens After Code Onboarding

```
Repository is now ready for development
├─ Skills available in .skills/generated/
├─ Context available in .keel/ and kg-context.md
├─ Domain metadata in .domain-context.json
└─ Developer opens in Windsurf and gets intelligent suggestions
```

---

## Implementation Steps

### Step 1: Code Onboarding (One-Time Setup)

```bash
# Onboard facility-service to cwow-facility domain
$ keel code onboard --path ./facility-service --kg

✓ Analyzed code structure
✓ Queried KG for cwow-facility domain
✓ Generated kg-context.md
✓ Generated 4 domain-aware skills with KG context
✓ Created .keel/codebase-understanding.md
✓ Created .keel/methodology.yaml
✓ Created .domain-context.json

Result: Repository is ready for development
```

### Step 2: Repository Structure

```
facility-service/
├── .skills/generated/
│   ├── fhir-api-endpoint-skill/
│   │   └─ SKILL.md (with KG context embedded)
│   ├── database-optimizer-skill/
│   │   └─ SKILL.md (with KG context embedded)
│   ├── security-validator-skill/
│   │   └─ SKILL.md (with KG context embedded)
│   └── sla-monitor-skill/
│       └─ SKILL.md (with KG context embedded)
│
├── .keel/
│   ├── codebase-understanding.md (architecture, patterns)
│   ├── methodology.yaml (workflow config)
│   └── onboarding/ (analysis, domain knowledge)
│
├── kg-context.md (business + code context)
├── .domain-context.json (domain metadata)
└── [rest of repository]
```

### Step 3: Developer Opens in Windsurf

```bash
$ windsurf ./facility-service

Windsurf detects and loads:
├─ .domain-context.json → Domain metadata
├─ .skills/generated/*.md → Domain-aware skills
├─ .keel/codebase-understanding.md → Project context
└─ kg-context.md → Business context

Windsurf is now context-aware
```

### Step 4: Developer Starts Development

```
Developer task: "Add FHIR Patient endpoint"

Windsurf provides:
├─ Skill suggestion: Use fhir-api-endpoint-skill
├─ Code pattern: Follow /api/v1/ versioning
├─ Implementation: OAuth 2.0 validation (from KG)
├─ Implementation: FHIR validation (from KG)
├─ Implementation: HIPAA audit logging (from KG)
├─ Performance: Add caching for < 100ms SLA (from KG)
├─ Testing: Follow TDD pattern
├─ File location: app/api/v1/endpoints/patients.py
└─ Example code: From SKILL.md

Developer implements with full context
```

---

## What Gets Generated

### Generated SKILL.md Structure

```yaml
---
name: fhir-api-endpoint-skill
description: Develop FHIR API endpoints for facility domain
domain: cwow-facility

# KG CONTEXT (Embedded from Knowledge Graph)
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
    - type: Availability
      value: > 99.9%
  performance_requirements:
    - type: Concurrent users
      value: 10K
      implication: "Connection pooling required"

# PROJECT CONTEXT (From code analysis)
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

# CAPABILITIES (What this skill enables)
capabilities:
  - create-fhir-endpoint
  - add-oauth2-authentication
  - add-fhir-validation
  - add-hipaa-audit-logging
  - add-response-time-monitoring

# EXAMPLES (For Windsurf to reference)
examples:
  - name: "Create FHIR Patient endpoint"
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

### Generated .domain-context.json

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
      "type": "domain-specific",
      "kg_aware": true
    },
    {
      "name": "database-optimizer-skill",
      "path": ".skills/generated/database-optimizer-skill",
      "type": "domain-specific",
      "kg_aware": true
    },
    {
      "name": "security-validator-skill",
      "path": ".skills/generated/security-validator-skill",
      "type": "domain-specific",
      "kg_aware": true
    },
    {
      "name": "sla-monitor-skill",
      "path": ".skills/generated/sla-monitor-skill",
      "type": "domain-specific",
      "kg_aware": true
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

### Generated kg-context.md

```markdown
# Facility Service - Business & Code Context

## Business Context (From KG)

### SLAs
- Response time < 100ms
- Availability > 99.9%

### Integration Requirements
- FHIR API integration
- OAuth 2.0 authentication

### Security Requirements
- HIPAA compliance
- AES-256 encryption
- Audit logging for all PHI access

### Performance Requirements
- 10K concurrent users
- DB latency < 50ms

## Code Structure (From Graphify)
- 45 code nodes
- 5 code communities
- FacilityService is highly connected

## Repository Overview (From GitIngest)
- Python 3.9+ with FastAPI
- PostgreSQL database
- 120 files, 25 dependencies
```

### Generated .keel/codebase-understanding.md

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
└─ migrations/ → Alembic database migrations

## Development Workflow
1. Create feature branch from main
2. Add tests first (RED phase)
3. Implement feature (GREEN phase)
4. Refactor (REFACTOR phase)
5. Create PR with test evidence
6. Automated checks + human review
7. Squash merge to main

## Common Patterns
├─ API Versioning: /api/v1, /api/v2
├─ Error Handling: Custom exception hierarchy
├─ Async Operations: Celery for background jobs
├─ Caching: Redis layer for hot data
└─ Security: JWT + role-based access control
```

---

## How Windsurf Uses Generated Files

### Windsurf Reads .domain-context.json
```
Windsurf learns:
├─ Domain: cwow-facility
├─ Project type: backend-development
├─ Tech stack: Python, FastAPI, PostgreSQL
├─ Available skills: 4 domain-aware skills
├─ SLAs: Response time < 100ms, Availability > 99.9%
├─ Integrations: FHIR API, OAuth 2.0
└─ Security policies: HIPAA, AES-256
```

### Windsurf Reads SKILL.md Files
```
Windsurf learns:
├─ Skill name: fhir-api-endpoint-skill
├─ KG context: FHIR API, OAuth 2.0, HIPAA, AES-256, SLAs
├─ Project context: Tech stack, conventions, file patterns
├─ Capabilities: What this skill can do
├─ Examples: Code examples to reference
└─ Uses this to suggest code, patterns, and implementations
```

### Windsurf Reads .keel/codebase-understanding.md
```
Windsurf learns:
├─ Architecture: How code is organized
├─ Key files: Where to make changes
├─ Development workflow: How to work
├─ Common patterns: How to code
└─ Uses this to suggest file locations, patterns, and workflows
```

### Windsurf Reads kg-context.md
```
Windsurf learns:
├─ Business requirements: What needs to be done
├─ SLAs: Performance constraints
├─ Integrations: External systems to integrate with
├─ Security: Security requirements
└─ Uses this to validate code and suggest implementations
```

---

## Developer Workflow

### Before Code Onboarding
```
Developer opens facility-service in Windsurf
├─ No context available
├─ No skill suggestions
├─ No business requirements visible
├─ Manual development
└─ Error-prone and time-consuming
```

### After Code Onboarding
```
Developer opens facility-service in Windsurf
├─ Full domain context available
├─ Skill suggestions available
├─ Business requirements visible
├─ Code patterns understood
├─ Development is guided by context
└─ Intelligent suggestions from Windsurf
```

---

## Key Implementation Points

### 1. Only Domain-Specific KG Context

```
When onboarding facility-service to cwow-facility:

✅ INCLUDED:
├─ cwow-facility domain knowledge
├─ Facility-specific SLAs
├─ Facility-specific integration specs
├─ Facility-specific security policies
└─ Facility-specific performance requirements

❌ NOT INCLUDED:
├─ Other domain knowledge
├─ Generic KG information
├─ Unrelated business rules
└─ Other domain's constraints
```

### 2. No Full Entity Extraction Needed

```
Light mode is sufficient:
├─ Query KG for domain knowledge
├─ Embed in SKILL.md files
├─ Create context documents
└─ No need for --extract-entities

Entity extraction is overkill for this use case
```

### 3. Skills are Domain-Aware

```
Generated skills include:
├─ KG context (SLAs, integrations, security)
├─ Project context (tech stack, conventions)
├─ Capabilities (what the skill enables)
└─ Examples (code examples to reference)
```

### 4. Repository is Ready for Development

```
After code onboarding:
├─ Skills available in .skills/
├─ Context available in .keel/ and kg-context.md
├─ Domain metadata in .domain-context.json
├─ No agent execution needed
└─ Windsurf provides all guidance
```

---

## Comparison: Code Onboarding vs Agent Run

| Aspect | Code Onboarding | Agent Run |
|--------|-----------------|-----------|
| **Purpose** | Prepare repository | Execute agent |
| **Scope** | Repository-ready | Agent-driven development |
| **Workflow** | Analyze → Extract → Generate → Store | Design → Plan → Execute → Review |
| **Execution** | One-time setup | Per task |
| **Output** | Skills + context + docs | Code changes + evidence |
| **Used by** | Windsurf/IDE tools | Custom agents |
| **Approval gates** | None | Yes (design, plan, review) |
| **Human involvement** | None (preparation) | Approval checkpoints |
| **Result** | Repository ready | Code changes with audit trail |

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
├─ Reads .keel/codebase-understanding.md
├─ Reads kg-context.md
├─ Becomes context-aware
└─ Provides intelligent suggestions for development
```

### Developer Workflow

```
1. Code onboarding prepares repository (one-time)
2. Developer opens in Windsurf
3. Windsurf loads all context automatically
4. Developer gets intelligent suggestions
5. Development is guided by context
6. No agent execution needed
```

### Key Points

✅ **Code onboarding prepares the repository** - Not for agent execution  
✅ **Skills are stored in .skills/ directory** - Available for Windsurf to use  
✅ **Context is stored in .keel/ and kg-context.md** - Available for Windsurf to read  
✅ **Windsurf picks up context automatically** - No manual configuration needed  
✅ **Developer gets intelligent suggestions** - Based on domain, business, and code context  
✅ **No agent execution needed** - Windsurf provides all necessary guidance  
✅ **Only domain-specific KG context** - Not all domains  
✅ **No full entity extraction needed** - Light mode is sufficient  

**Result**: Repository is fully prepared for development with all context and skills available to Windsurf/IDE tools.

---

## Reading Guide

**For Quick Understanding** (10 min):
- Read: `CODE_ONBOARDING_WINDSURF_INTEGRATION.md`

**For Complete Understanding** (30 min):
- Read: `CODE_ONBOARDING_WINDSURF_INTEGRATION.md`
- Read: `docs/plans/CODE_ONBOARDING_VS_AGENT_RUN.md`

**For Implementation** (60 min):
- Read all above documents
- Review `docs/plans/KG_CONTEXT_TO_SKILL_WORKFLOW.md`
- Review `KG_CONTEXT_SKILL_INTEGRATION_INDEX.md`

---

**Status**: ✅ READY FOR IMPLEMENTATION

All documentation is complete and committed to git!
