# KG Context → SKILL Workflow - Visual Summary

**Date**: May 6, 2026  
**Focus**: How KG context flows into SKILL files and development workflows

---

## The Complete Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Code Onboarding Phase                        │
│                   (Initial - One Time)                          │
└─────────────────────────────────────────────────────────────────┘

dva code onboard --path ./facility-service --kg --extract-entities
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Analyze Code                                            │
│ ├─ Detect: Python, FastAPI, PostgreSQL                         │
│ ├─ Patterns: API versioning, DI, middleware                    │
│ └─ Store: analysis.json                                         │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Query KG for Domain Knowledge                           │
│ ├─ Domain: cwow-facility                                        │
│ ├─ SLAs: Response time < 100ms, Availability > 99.9%           │
│ ├─ Integration: FHIR API, OAuth 2.0                            │
│ ├─ Security: HIPAA compliance, AES-256 encryption              │
│ └─ Performance: 10K concurrent users, DB latency < 50ms        │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Build kg-context.md                                     │
│ ├─ Business Context (from KG)                                   │
│ ├─ Code Structure (from Graphify)                               │
│ └─ Repository Overview (from GitIngest)                         │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Generate Domain-Aware Skills                            │
│ ├─ fhir-api-endpoint-skill (with KG context)                   │
│ ├─ database-optimizer-skill (with KG context)                  │
│ ├─ security-validator-skill (with KG context)                  │
│ ├─ sla-monitor-skill (with KG context)                         │
│ └─ hipaa-compliance-skill (with KG context)                    │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Generated SKILL.md Files                                        │
│                                                                 │
│ fhir-api-endpoint-skill/SKILL.md                               │
│ ├─ name: fhir-api-endpoint-skill                               │
│ ├─ domain: cwow-facility                                        │
│ │                                                               │
│ ├─ kg_context:                                                  │
│ │  ├─ integration_specs:                                        │
│ │  │  ├─ FHIR API: https://fhir.example.com/api/v1            │
│ │  │  └─ OAuth 2.0: authorization_code flow                   │
│ │  ├─ security_policies:                                       │
│ │  │  ├─ HIPAA compliance: required                            │
│ │  │  ├─ Encryption at rest: AES-256                          │
│ │  │  └─ Audit logging: required                              │
│ │  └─ slas:                                                     │
│ │     ├─ Response time: < 100ms                                │
│ │     └─ Availability: > 99.9%                                 │
│ │                                                               │
│ ├─ project_context:                                             │
│ │  ├─ tech_stack: [Python, FastAPI, PostgreSQL]               │
│ │  ├─ conventions: snake_case, /api/v1/, TDD                  │
│ │  └─ file_patterns: app/api/v1/*, tests/integration/*        │
│ │                                                               │
│ ├─ workflow:                                                    │
│ │  ├─ design: Ask questions informed by KG                    │
│ │  ├─ planning: Create tasks informed by KG                   │
│ │  ├─ execution: Execute with KG validation                   │
│ │  └─ review: Review against KG requirements                  │
│ │                                                               │
│ └─ capabilities:                                                │
│    ├─ create-fhir-endpoint                                      │
│    ├─ add-oauth2-authentication                                 │
│    ├─ add-fhir-validation                                       │
│    ├─ add-hipaa-audit-logging                                   │
│    └─ add-response-time-monitoring                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Development Workflow Using KG Context

```
┌─────────────────────────────────────────────────────────────────┐
│                   Development Phase                             │
│                  (Ongoing - Per Task)                           │
└─────────────────────────────────────────────────────────────────┘

agent run --path ./facility-service --task "Add FHIR Patient endpoint"
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: DESIGN (design-brainstorm-skill)                       │
│                                                                 │
│ Loads: fhir-api-endpoint-skill/SKILL.md                        │
│ Reads: kg_context section                                       │
│                                                                 │
│ Questions (Informed by KG):                                     │
│ ├─ What FHIR resource? (KG: Patient, Observation, etc.)       │
│ ├─ Authentication? (KG: OAuth 2.0 required)                    │
│ ├─ Response time? (KG: < 100ms SLA)                            │
│ └─ HIPAA compliance? (KG: Yes, required)                       │
│                                                                 │
│ Design Proposal (Aligned with KG):                              │
│ ├─ Endpoint: GET /api/v1/patients/{patient_id}                │
│ ├─ Auth: OAuth 2.0 (from KG)                                   │
│ ├─ Validation: FHIR R4 (from KG)                               │
│ ├─ Logging: HIPAA audit (from KG)                              │
│ └─ Performance: Caching for < 100ms (from KG SLA)             │
│                                                                 │
│ ✋ CHECKPOINT: User approves design                             │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: PLANNING (implementation-planning-skill)               │
│                                                                 │
│ Reads: kg_context section from SKILL.md                        │
│                                                                 │
│ Task 1: Create FHIR schema validation                          │
│ ├─ KG Context: Validate against FHIR R4 spec                  │
│ ├─ KG Context: Include HIPAA required fields                  │
│ └─ KG Context: Ensure < 100ms validation                      │
│                                                                 │
│ Task 2: Add OAuth 2.0 middleware                               │
│ ├─ KG Context: Implement OAuth 2.0 flow                       │
│ ├─ KG Context: Validate tokens                                │
│ └─ KG Context: Log for HIPAA audit                            │
│                                                                 │
│ Task 3: Create FHIR endpoint                                   │
│ ├─ KG Context: FHIR validation                                │
│ ├─ KG Context: OAuth 2.0 authentication                       │
│ ├─ KG Context: HIPAA audit logging                            │
│ └─ KG Context: Caching for < 100ms response                   │
│                                                                 │
│ Task 4: Add response time monitoring                           │
│ ├─ KG Context: Monitor endpoint response time                 │
│ ├─ KG Context: Alert if > 100ms                               │
│ └─ KG Context: Track availability                             │
│                                                                 │
│ Task 5: Add HIPAA audit logging                                │
│ ├─ KG Context: Log all PHI access                             │
│ ├─ KG Context: Include user, timestamp, action                │
│ └─ KG Context: Encrypt logs with AES-256                      │
│                                                                 │
│ ✋ CHECKPOINT: User approves plan                              │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: EXECUTION (test-driven-development-skill)              │
│                                                                 │
│ For each task:                                                  │
│ ├─ [RED] Write failing test                                    │
│ ├─ [GREEN] Implement with KG validation                        │
│ │  ├─ Validate FHIR (from KG)                                  │
│ │  ├─ Validate OAuth 2.0 (from KG)                             │
│ │  ├─ Validate HIPAA logging (from KG)                         │
│ │  └─ Validate response time (from KG SLA)                     │
│ ├─ ✅ Tests pass                                                │
│ └─ [REFACTOR] Improve code quality                             │
│                                                                 │
│ ✅ CHECKPOINT: All tests must pass                              │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: REVIEW (code-review-skill)                             │
│                                                                 │
│ KG Compliance Validation:                                       │
│ ├─ ✅ FHIR R4 validation implemented (from KG)                 │
│ ├─ ✅ OAuth 2.0 authentication implemented (from KG)           │
│ ├─ ✅ HIPAA audit logging implemented (from KG)                │
│ ├─ ✅ Response time < 100ms with caching (from KG SLA)        │
│ ├─ ✅ AES-256 encryption for logs (from KG)                    │
│ └─ ✅ Availability monitoring implemented (from KG SLA)        │
│                                                                 │
│ Code Quality:                                                   │
│ ├─ ✅ All tests passing (47/47)                                │
│ ├─ ✅ Test coverage: 87% (exceeds 80%)                         │
│ ├─ ✅ All KG requirements met                                   │
│ └─ ✅ All KG constraints validated                              │
│                                                                 │
│ ✋ CHECKPOINT: Code review approval                             │
└─────────────────────────────────────────────────────────────────┘
    ↓
✅ FEATURE COMPLETE
   ├─ Code aligned with KG requirements
   ├─ All business constraints satisfied
   ├─ All security policies implemented
   ├─ All SLAs met
   └─ Full audit trail captured
```

---

## KG Context vs MCP Context

### During Code Onboarding (KG Context)

```
KG Context in SKILL.md
├─ Static (embedded at skill generation time)
├─ Includes:
│  ├─ Domain: cwow-facility
│  ├─ Integration specs: FHIR API, OAuth 2.0
│  ├─ Security policies: HIPAA, AES-256
│  ├─ SLAs: Response time, availability
│  └─ Performance requirements: Concurrent users, latency
├─ Used for:
│  ├─ Guiding design phase
│  ├─ Informing planning phase
│  ├─ Validating execution phase
│  └─ Checking review phase
└─ Result: Skills are domain-aware and workflow-constrained
```

### During Future Development (MCP Context)

```
MCP Context (Memory MCP)
├─ Dynamic (queried at runtime)
├─ Available for:
│  ├─ Agents to query domain rules
│  ├─ Agents to get SLA information
│  ├─ Agents to understand integration patterns
│  └─ Agents to check security requirements
├─ Used for:
│  ├─ Runtime decision-making
│  ├─ Constraint validation
│  ├─ Pattern matching
│  └─ Requirement checking
└─ Result: Agents can make informed decisions without regenerating skills
```

### Key Difference

```
KG Context (SKILL.md)
├─ When: Used during code onboarding
├─ How: Embedded in generated SKILL files
├─ Scope: Domain-specific (only cwow-facility)
├─ Lifecycle: Static (until skill regenerated)
└─ Purpose: Guide development workflow

MCP Context (Memory MCP)
├─ When: Used during agent execution
├─ How: Queried via MCP tools
├─ Scope: Any domain (queried at runtime)
├─ Lifecycle: Dynamic (can be updated)
└─ Purpose: Support runtime decision-making
```

---

## Only Domain-Specific KG Context

### What Gets Embedded

```
When onboarding facility-service to cwow-facility domain:

✅ INCLUDED:
├─ cwow-facility domain knowledge
├─ Facility-specific SLAs
├─ Facility-specific integration specs
├─ Facility-specific security policies
└─ Facility-specific performance requirements

❌ NOT INCLUDED:
├─ Other domain knowledge (e.g., patient-domain)
├─ Generic KG information
├─ Unrelated business rules
└─ Other domain's constraints
```

### Example

```yaml
# SKILL.md for facility-service

kg_context:
  domain: cwow-facility  # Only this domain
  
  slas:
    - title: Response time
      value: < 100ms
      domain: cwow-facility  # Facility-specific
  
  integration_specs:
    - type: FHIR API
      domain: cwow-facility  # Facility-specific
  
  security_policies:
    - type: HIPAA compliance
      domain: cwow-facility  # Facility-specific
```

---

## Summary

### The Flow

```
1. Code Onboarding
   dva code onboard --path ./facility-service --kg
   └─ Query KG for cwow-facility domain only
   └─ Embed in SKILL.md files

2. SKILL File Generation
   Generated SKILL.md
   └─ Include kg_context (facility domain only)
   └─ Include workflow informed by KG

3. Development Workflow
   agent run --path ./facility-service --task "..."
   ├─ Phase 1: Design (uses KG context)
   ├─ Phase 2: Planning (uses KG context)
   ├─ Phase 3: Execution (validates with KG context)
   └─ Phase 4: Review (checks against KG context)

4. Future Development (Optional)
   MCP queries during execution
   └─ Agent can query Memory MCP for updated KG info
   └─ No need to regenerate skills
```

### Key Points

✅ **KG context is embedded in SKILL.md** - Not just stored separately  
✅ **Only facility domain KG context** - Not all domains  
✅ **Workflow is informed by KG** - All phases use KG context  
✅ **No unnecessary entity extraction** - Light mode is sufficient  
✅ **MCP is for future queries** - Not used during initial onboarding  
✅ **Skills are domain-aware** - Generated from code + KG for that domain  

**Result**: Domain-aware skills, constrained workflows, and informed development decisions.
