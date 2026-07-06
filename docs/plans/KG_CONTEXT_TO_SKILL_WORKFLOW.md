# KG Context to Skill Workflow Integration

**Date**: May 6, 2026  
**Question**: How is KG context attached to the code onboarding command and integrated into SKILL files for development workflows?

---

## The Complete Flow

```
Code Onboarding Phase (Initial)
    ↓
keel code onboard --path ./facility-service --kg --extract-entities
    ├─ Analyze code structure (Graphify)
    ├─ Query KG for domain knowledge (cwow-facility)
    ├─ Build kg-context.md (hybrid context)
    └─ Generate domain-aware skills
    ↓
Generated SKILL Files
    ├─ SKILL.md (with KG context embedded)
    ├─ project_context (KG info available)
    └─ Methodology skills (design, planning, execution)
    ↓
Development Phase (Ongoing)
    ↓
agent run --path ./facility-service --task "Add FHIR endpoint"
    ├─ Load SKILL files (with KG context)
    ├─ Load methodology.yaml (workflow config)
    ├─ Phase 1: Design (uses KG context for decisions)
    ├─ Phase 2: Planning (uses KG context for constraints)
    ├─ Phase 3: Execution (uses KG context for validation)
    └─ Phase 4: Review (validates against KG requirements)
```

---

## Part 1: Code Onboarding - KG Context Attachment

### Command
```bash
keel code onboard --path ./facility-service --kg --extract-entities
```

### What Happens

#### Step 1: Analyze Code
```python
# Analyze project structure
analysis = ProjectAnalyzer.analyze(project_path)
# Returns: languages, frameworks, dependencies, patterns
```

#### Step 2: Query KG for Domain Knowledge
```python
# Query KG for cwow-facility domain
domain_knowledge = query_kg_for_domain("cwow-facility")

# Returns:
{
    "domain": "cwow-facility",
    "slas": [
        {"title": "Response time", "value": "< 100ms"},
        {"title": "Availability", "value": "> 99.9%"}
    ],
    "integration_specs": [
        {"title": "FHIR API", "endpoint": "https://fhir.example.com/api/v1"},
        {"title": "OAuth 2.0", "flow": "authorization_code"}
    ],
    "security_policies": [
        {"title": "HIPAA compliance", "requirement": "required"},
        {"title": "AES-256 encryption", "scope": "data_at_rest"}
    ],
    "performance_requirements": [
        {"title": "Concurrent users", "value": "10K"},
        {"title": "DB latency", "value": "< 50ms"}
    ]
}
```

#### Step 3: Build kg-context.md
```markdown
# Facility Service - Codebase Understanding

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

### Performance Requirements
- 10K concurrent users
- DB latency < 50ms

## Code Structure (From Graphify)
[Code relationships, modules, architecture]

## Repository Overview (From GitIngest)
[File structure, technology stack]
```

#### Step 4: Generate Domain-Aware Skills
```
Generated Skills:
├─ fhir-api-endpoint-skill
│  └─ Aware of: FHIR API requirement, OAuth 2.0, response time SLA
├─ database-optimizer-skill
│  └─ Aware of: DB latency requirement (< 50ms), concurrent users (10K)
├─ security-validator-skill
│  └─ Aware of: HIPAA compliance, AES-256 encryption
└─ sla-monitor-skill
   └─ Aware of: Response time SLA (< 100ms), availability SLA (> 99.9%)
```

---

## Part 2: SKILL File Structure with KG Context

### Generated SKILL.md File

```yaml
---
name: fhir-api-endpoint-skill
description: Develop FHIR API endpoints for facility domain
domain: cwow-facility
version: 1.0.0

# KG CONTEXT EMBEDDED HERE
kg_context:
  domain: cwow-facility
  integration_specs:
    - type: FHIR API
      endpoint: https://fhir.example.com/api/v1
      authentication: OAuth 2.0
      format: FHIR R4
      validation_required: true
  
  security_policies:
    - type: HIPAA compliance
      requirement: required
      data_classification: PHI (Protected Health Information)
      encryption_at_rest: AES-256
      encryption_in_transit: TLS 1.2+
      audit_logging: required
  
  slas:
    - type: Response time
      value: < 100ms
      implication: "Use caching, optimize queries"
    - type: Availability
      value: > 99.9%
      implication: "Implement retry logic, circuit breakers"
  
  performance_requirements:
    - type: Concurrent users
      value: 10K
      implication: "Connection pooling required"
    - type: DB latency
      value: < 50ms
      implication: "Query optimization, indexing"

# PROJECT CONTEXT (Automatically Injected)
project_context:
  project_root: /path/to/facility-service
  understanding_doc: .keel/codebase-understanding.md
  methodology: backend-development
  tech_stack: [Python, FastAPI, PostgreSQL, pytest]
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

# SKILL WORKFLOW (For Development)
workflow:
  design:
    step: "Ask clarifying questions about FHIR endpoint"
    checkpoint: "user-approval-required"
    context_from_kg:
      - "What FHIR resource type? (Patient, Observation, etc.)"
      - "Must implement OAuth 2.0 authentication"
      - "Must validate against FHIR R4 spec"
      - "Response time must be < 100ms"
  
  planning:
    step: "Create implementation plan with tasks"
    checkpoint: "user-approval-required"
    context_from_kg:
      - "Task 1: Create FHIR schema validation"
      - "Task 2: Implement OAuth 2.0 middleware"
      - "Task 3: Create endpoint with HIPAA audit logging"
      - "Task 4: Add caching for SLA compliance"
      - "Task 5: Add monitoring for response time"
  
  execution:
    step: "Execute tasks with TDD enforcement"
    checkpoint: "tests-must-pass"
    context_from_kg:
      - "Validate all FHIR payloads"
      - "Ensure HIPAA audit logging"
      - "Monitor response time (< 100ms)"
      - "Verify OAuth 2.0 validation"
  
  review:
    step: "Code review with KG compliance check"
    checkpoint: "code-review-required"
    context_from_kg:
      - "Verify HIPAA compliance"
      - "Verify FHIR validation"
      - "Verify response time < 100ms"
      - "Verify OAuth 2.0 implementation"

# CAPABILITIES (What This Skill Can Do)
capabilities:
  - create-fhir-endpoint
  - add-oauth2-authentication
  - add-fhir-validation
  - add-hipaa-audit-logging
  - add-response-time-monitoring
  - add-caching-for-sla

# REQUIREMENTS (What Must Be Present)
requirements:
  - "FastAPI project structure"
  - "pytest configured"
  - "SQLAlchemy ORM setup"
  - "FHIR validator library"
  - "OAuth 2.0 client library"
  - "Audit logging configured"

# EXAMPLES (From KG Context)
examples:
  - name: "Create FHIR Patient endpoint"
    description: "Endpoint to fetch patient data from FHIR server"
    code: |
      @router.get("/api/v1/patients/{patient_id}", response_model=PatientSchema)
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

---

## Part 3: How KG Context is Used During Development

### Phase 1: Design Phase

```bash
$ agent run --path ./facility-service --task "Add FHIR Patient endpoint"

🔄 Skill: design-brainstorm-skill
   Using KG context from SKILL.md...

? What FHIR resource type?
  (KG Context: Must support Patient, Observation, Condition)
  Your answer: Patient

? Authentication method?
  (KG Context: Must use OAuth 2.0)
  Your answer: OAuth 2.0 (already specified in KG)

? Response time requirement?
  (KG Context: < 100ms SLA)
  Your answer: < 100ms (from KG SLA)

? HIPAA compliance needed?
  (KG Context: Yes, required)
  Your answer: Yes (from KG security policy)

📋 DESIGN PROPOSAL
   ├─ Endpoint: GET /api/v1/patients/{patient_id}
   ├─ Authentication: OAuth 2.0 (from KG)
   ├─ FHIR Validation: FHIR R4 (from KG)
   ├─ HIPAA Audit Logging: Required (from KG)
   ├─ Response Time: < 100ms with caching (from KG SLA)
   └─ Architecture: [diagram showing KG constraints]
```

### Phase 2: Planning Phase

```bash
✅ Design Approved!

🔄 Skill: implementation-planning-skill
   Using KG context from SKILL.md...

📋 IMPLEMENTATION PLAN (5 tasks, ~15 minutes)

Task 1 (3min): Create FHIR schema validation
  Files to create:
    └─ app/schemas/fhir_patient.py
  KG Context Applied:
    ├─ Validate against FHIR R4 spec (from KG)
    ├─ Include all required HIPAA fields (from KG)
    └─ Ensure response < 100ms (from KG SLA)
  Tests needed:
    └─ tests/unit/schemas/test_fhir_patient.py

Task 2 (2min): Add OAuth 2.0 middleware
  Files to create:
    └─ app/middleware/oauth2_middleware.py
  KG Context Applied:
    ├─ Implement OAuth 2.0 flow (from KG integration spec)
    ├─ Validate tokens (from KG security policy)
    └─ Log all access for HIPAA audit (from KG)
  Tests needed:
    └─ tests/integration/middleware/test_oauth2.py

Task 3 (4min): Create FHIR endpoint
  Files to create:
    └─ app/api/v1/endpoints/patients.py
  KG Context Applied:
    ├─ Implement FHIR validation (from KG)
    ├─ Use OAuth 2.0 authentication (from KG)
    ├─ Add HIPAA audit logging (from KG)
    └─ Implement caching for < 100ms response (from KG SLA)
  Tests needed:
    └─ tests/integration/api/test_patients.py

Task 4 (3min): Add response time monitoring
  Files to create:
    └─ app/monitoring/response_time.py
  KG Context Applied:
    ├─ Monitor endpoint response time (from KG SLA)
    ├─ Alert if > 100ms (from KG SLA threshold)
    └─ Track availability (from KG SLA)
  Tests needed:
    └─ tests/unit/monitoring/test_response_time.py

Task 5 (2min): Add HIPAA audit logging
  Files to create:
    └─ app/logging/hipaa_audit.py
  KG Context Applied:
    ├─ Log all PHI access (from KG security policy)
    ├─ Include user, timestamp, action (from KG)
    └─ Encrypt logs at rest with AES-256 (from KG)
  Tests needed:
    └─ tests/unit/logging/test_hipaa_audit.py
```

### Phase 3: Execution Phase

```bash
✅ Plan Approved!

🔄 Phase: EXECUTION (TDD-Enforced)
   Using KG context from SKILL.md...

📍 Task 1/5: Create FHIR schema validation
   ├─ [RED] Writing failing test
   │  └─ test_fhir_patient.py::test_validate_patient_schema → FAIL
   │
   ├─ [GREEN] Writing implementation
   │  └─ fhir_patient.py created
   │     ├─ Validates against FHIR R4 spec (from KG)
   │     ├─ Includes HIPAA required fields (from KG)
   │     └─ Ensures < 100ms validation (from KG SLA)
   │
   ├─ ✅ Running tests
   │  └─ test_fhir_patient.py → PASS
   │
   └─ [REFACTOR] Improving code
      └─ Added error handling, docstrings
         ├─ Document FHIR compliance (from KG)
         ├─ Document HIPAA requirements (from KG)
         └─ Document SLA implications (from KG)

... [Tasks 2-5] ...
```

### Phase 4: Review Phase

```bash
✅ ALL TASKS COMPLETE

📋 CODE REVIEW CHECK
   Using KG context from SKILL.md...

KG Compliance Validation:
  ✅ FHIR R4 validation implemented (from KG)
  ✅ OAuth 2.0 authentication implemented (from KG)
  ✅ HIPAA audit logging implemented (from KG)
  ✅ Response time < 100ms with caching (from KG SLA)
  ✅ AES-256 encryption for logs (from KG security policy)
  ✅ Availability monitoring implemented (from KG SLA)

Code Quality:
  ✅ All tests passing
  ✅ Test coverage: 87% (exceeds 80%)
  ✅ All KG requirements met
  ✅ All KG constraints validated
```

---

## Part 4: KG Context vs MCP Context

### KG Context (Initial Onboarding)
```
Used During: Code Onboarding Phase
├─ Extracted from Confluence documents
├─ Stored in Knowledge Graph
├─ Embedded in SKILL.md files
├─ Used to inform skill generation
└─ Used to guide development workflow

Purpose: Provide business context for development
├─ What are the business requirements?
├─ What are the constraints?
├─ What are the integration patterns?
└─ What are the security/performance requirements?
```

### MCP Context (Runtime Queries)
```
Used During: Agent Development & Execution
├─ Exposed via Memory MCP
├─ Queried by agents during task execution
├─ Available for runtime decision-making
└─ Can be refreshed/updated

Purpose: Provide queryable business context during development
├─ Agent asks: "What are the SLAs for this domain?"
├─ Agent asks: "What integration patterns are required?"
├─ Agent asks: "What security policies apply?"
└─ Agent gets: Real-time answers from KG
```

### Key Difference

```
KG Context in SKILL.md
├─ Static (embedded at skill generation time)
├─ Used to guide skill workflow
├─ Informs design, planning, execution, review phases
└─ Ensures consistency across tasks

MCP Context (Memory MCP)
├─ Dynamic (queried at runtime)
├─ Used by agents for decision-making
├─ Available for future enhancements
└─ Can be updated without regenerating skills
```

---

## Part 5: Complete Integration Example

### Scenario: Onboarding Facility Service

#### Step 1: Initial Code Onboarding
```bash
$ keel code onboard --path ./facility-service --kg --extract-entities

✓ Analyzed code structure
✓ Queried KG for cwow-facility domain
✓ Generated kg-context.md
✓ Generated 5 domain-aware skills:
  ├─ fhir-api-endpoint-skill (with KG context)
  ├─ database-optimizer-skill (with KG context)
  ├─ security-validator-skill (with KG context)
  ├─ sla-monitor-skill (with KG context)
  └─ hipaa-compliance-skill (with KG context)
✓ Created methodology.yaml
```

#### Step 2: Project Structure After Onboarding
```
facility-service/
├── src/
│   ├── main.py
│   ├── models/
│   ├── api/
│   └── services/
├── tests/
├── .skills/
│   ├── domain/
│   ├── generated/
│   │   ├── fhir-api-endpoint-skill/
│   │   │   └─ SKILL.md (with KG context embedded)
│   │   ├── database-optimizer-skill/
│   │   │   └─ SKILL.md (with KG context embedded)
│   │   └─ ... [3 more]
│   └── methodology/
│       ├── design-brainstorm-skill/
│       ├── implementation-planning-skill/
│       ├── test-driven-development-skill/
│       └── code-review-skill/
├── .keel/
│   ├── codebase-understanding.md
│   ├── methodology.yaml
│   └── approvals/
└── pyproject.toml
```

#### Step 3: Development Workflow
```bash
$ agent run --path ./facility-service --task "Add FHIR Patient endpoint"

Phase 1: Design
  ├─ Loads fhir-api-endpoint-skill/SKILL.md
  ├─ Reads KG context (FHIR API, OAuth 2.0, response time SLA)
  ├─ Asks clarifying questions informed by KG
  └─ Proposes design aligned with KG constraints

Phase 2: Planning
  ├─ Reads KG context from SKILL.md
  ├─ Creates 5 tasks informed by KG requirements
  ├─ Each task includes KG context implications
  └─ User approves plan

Phase 3: Execution
  ├─ Loads test-driven-development-skill
  ├─ Executes tasks with KG context validation
  ├─ Ensures FHIR validation (from KG)
  ├─ Ensures OAuth 2.0 (from KG)
  ├─ Ensures HIPAA logging (from KG)
  ├─ Ensures < 100ms response (from KG SLA)
  └─ All tests pass

Phase 4: Review
  ├─ Loads code-review-skill
  ├─ Validates against KG requirements
  ├─ Checks FHIR compliance (from KG)
  ├─ Checks HIPAA compliance (from KG)
  ├─ Checks response time (from KG SLA)
  └─ Code approved
```

#### Step 4: Future Development (Using MCP)
```bash
# Later, when adding another endpoint:
$ agent run --path ./facility-service --task "Add FHIR Observation endpoint"

Agent (during execution):
  "Let me check the KG for facility domain requirements..."
  
  // Query Memory MCP
  slas = await mcp.query_domain_rules("cwow-facility", "SLA")
  // Returns: Response time < 100ms, Availability > 99.9%
  
  integration_specs = await mcp.query_domain_rules("cwow-facility", "Integration")
  // Returns: FHIR API, OAuth 2.0
  
  security_policies = await mcp.query_domain_rules("cwow-facility", "Security")
  // Returns: HIPAA compliance, AES-256 encryption
  
  // Use this information to inform development decisions
```

---

## Summary

### KG Context Flow

```
1. Code Onboarding
   keel code onboard --path ./facility-service --kg
   ├─ Query KG for domain knowledge
   └─ Embed in generated SKILL.md files

2. SKILL File Generation
   Generated SKILL.md files
   ├─ Include kg_context section
   ├─ Include project_context section
   ├─ Include workflow with KG-informed steps
   └─ Include examples based on KG

3. Development Workflow
   agent run --path ./facility-service --task "..."
   ├─ Load SKILL.md (with KG context)
   ├─ Phase 1: Design (uses KG context)
   ├─ Phase 2: Planning (uses KG context)
   ├─ Phase 3: Execution (validates with KG context)
   └─ Phase 4: Review (checks against KG context)

4. Future Enhancements
   MCP queries during execution
   ├─ Agent queries Memory MCP for KG info
   ├─ Gets real-time domain knowledge
   ├─ Makes informed decisions
   └─ Can be updated without regenerating skills
```

### Key Points

✅ **KG context is embedded in SKILL.md** - Not just stored separately  
✅ **Workflow is informed by KG** - Design, planning, execution, review all use KG context  
✅ **Only facility domain KG context is included** - Not all domains  
✅ **MCP is for future queries** - Not used during initial onboarding  
✅ **Skills are domain-specific** - Generated from code + KG for that domain  
✅ **No unnecessary entity extraction** - Light mode is sufficient for SKILL generation  

**Result**: Skills are domain-aware, workflow is constrained by business requirements, and agents make decisions informed by KG context.
