# KG Context & Skill Workflow Integration - Complete Index

**Date**: May 6, 2026  
**Topic**: How KG context flows into SKILL files and integrates with skill workflows  
**Documents**: 2 comprehensive guides + visual summary

---

## Quick Navigation

### 📚 Main Documents

1. **KG_CONTEXT_SKILL_WORKFLOW_SUMMARY.md** ⭐ START HERE
   - Visual overview of complete flow
   - Code onboarding to development workflow
   - KG context vs MCP context comparison
   - 10-minute read

2. **docs/plans/KG_CONTEXT_TO_SKILL_WORKFLOW.md**
   - Detailed technical explanation
   - SKILL.md file structure with KG context
   - Phase-by-phase workflow execution
   - Complete integration example
   - 20-minute read

---

## The Big Picture

```
Code Onboarding Phase (Initial)
    ↓
dva code onboard --path ./facility-service --kg --extract-entities
    ├─ Analyze code structure
    ├─ Query KG for cwow-facility domain knowledge
    ├─ Build kg-context.md
    └─ Generate domain-aware SKILL.md files with KG context embedded
    ↓
Generated SKILL Files
    ├─ fhir-api-endpoint-skill/SKILL.md (with KG context)
    ├─ database-optimizer-skill/SKILL.md (with KG context)
    ├─ security-validator-skill/SKILL.md (with KG context)
    ├─ sla-monitor-skill/SKILL.md (with KG context)
    └─ hipaa-compliance-skill/SKILL.md (with KG context)
    ↓
Development Workflow (Ongoing)
    ↓
agent run --path ./facility-service --task "Add FHIR endpoint"
    ├─ Phase 1: Design (loads SKILL.md, uses KG context)
    ├─ Phase 2: Planning (uses KG context for task breakdown)
    ├─ Phase 3: Execution (validates with KG context)
    └─ Phase 4: Review (checks against KG context)
```

---

## How KG Context is Attached

### Step 1: Code Onboarding Command
```bash
dva code onboard --path ./facility-service --kg --extract-entities
```

### Step 2: KG Query
```python
# Query KG for cwow-facility domain only
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

### Step 3: Embed in SKILL.md
```yaml
---
name: fhir-api-endpoint-skill
domain: cwow-facility

kg_context:
  domain: cwow-facility
  integration_specs:
    - type: FHIR API
      endpoint: https://fhir.example.com/api/v1
      authentication: OAuth 2.0
  security_policies:
    - type: HIPAA compliance
      requirement: required
      encryption_at_rest: AES-256
  slas:
    - type: Response time
      value: < 100ms
      implication: "Use caching, optimize queries"
  performance_requirements:
    - type: Concurrent users
      value: 10K
      implication: "Connection pooling required"

workflow:
  design:
    context_from_kg:
      - "Must implement OAuth 2.0 authentication"
      - "Must validate against FHIR R4 spec"
      - "Response time must be < 100ms"
  planning:
    context_from_kg:
      - "Task 1: Create FHIR schema validation"
      - "Task 2: Implement OAuth 2.0 middleware"
      - "Task 3: Add HIPAA audit logging"
      - "Task 4: Add caching for SLA compliance"
  execution:
    context_from_kg:
      - "Validate all FHIR payloads"
      - "Ensure HIPAA audit logging"
      - "Monitor response time (< 100ms)"
  review:
    context_from_kg:
      - "Verify HIPAA compliance"
      - "Verify FHIR validation"
      - "Verify response time < 100ms"
```

---

## How KG Context is Used in Workflows

### Phase 1: Design Phase

```
Skill: design-brainstorm-skill
Loads: fhir-api-endpoint-skill/SKILL.md
Reads: kg_context section

Questions (Informed by KG):
├─ What FHIR resource? (KG: Patient, Observation, etc.)
├─ Authentication? (KG: OAuth 2.0 required)
├─ Response time? (KG: < 100ms SLA)
└─ HIPAA compliance? (KG: Yes, required)

Design Proposal (Aligned with KG):
├─ Endpoint: GET /api/v1/patients/{patient_id}
├─ Auth: OAuth 2.0 (from KG)
├─ Validation: FHIR R4 (from KG)
├─ Logging: HIPAA audit (from KG)
└─ Performance: Caching for < 100ms (from KG SLA)
```

### Phase 2: Planning Phase

```
Skill: implementation-planning-skill
Reads: kg_context section from SKILL.md

Task 1: Create FHIR schema validation
├─ KG Context: Validate against FHIR R4 spec
├─ KG Context: Include HIPAA required fields
└─ KG Context: Ensure < 100ms validation

Task 2: Add OAuth 2.0 middleware
├─ KG Context: Implement OAuth 2.0 flow
├─ KG Context: Validate tokens
└─ KG Context: Log for HIPAA audit

Task 3: Create FHIR endpoint
├─ KG Context: FHIR validation
├─ KG Context: OAuth 2.0 authentication
├─ KG Context: HIPAA audit logging
└─ KG Context: Caching for < 100ms response

Task 4: Add response time monitoring
├─ KG Context: Monitor endpoint response time
├─ KG Context: Alert if > 100ms
└─ KG Context: Track availability

Task 5: Add HIPAA audit logging
├─ KG Context: Log all PHI access
├─ KG Context: Include user, timestamp, action
└─ KG Context: Encrypt logs with AES-256
```

### Phase 3: Execution Phase

```
Skill: test-driven-development-skill
Uses: KG context for validation

For each task:
├─ [RED] Write failing test
├─ [GREEN] Implement with KG validation
│  ├─ Validate FHIR (from KG)
│  ├─ Validate OAuth 2.0 (from KG)
│  ├─ Validate HIPAA logging (from KG)
│  └─ Validate response time (from KG SLA)
├─ ✅ Tests pass
└─ [REFACTOR] Improve code quality
```

### Phase 4: Review Phase

```
Skill: code-review-skill
Validates: Against KG requirements

KG Compliance Validation:
├─ ✅ FHIR R4 validation implemented (from KG)
├─ ✅ OAuth 2.0 authentication implemented (from KG)
├─ ✅ HIPAA audit logging implemented (from KG)
├─ ✅ Response time < 100ms with caching (from KG SLA)
├─ ✅ AES-256 encryption for logs (from KG)
└─ ✅ Availability monitoring implemented (from KG SLA)
```

---

## KG Context vs MCP Context

### KG Context (In SKILL.md)

```
When: Used during code onboarding
How: Embedded in generated SKILL files
Scope: Domain-specific (only cwow-facility)
Lifecycle: Static (until skill regenerated)

Purpose: Guide development workflow
├─ Inform design phase
├─ Inform planning phase
├─ Validate execution phase
└─ Check review phase

Example:
├─ "Must implement OAuth 2.0" (from KG)
├─ "Response time < 100ms" (from KG SLA)
├─ "HIPAA compliance required" (from KG)
└─ "FHIR R4 validation" (from KG)
```

### MCP Context (Memory MCP)

```
When: Used during agent execution (future)
How: Queried via MCP tools
Scope: Any domain (queried at runtime)
Lifecycle: Dynamic (can be updated)

Purpose: Support runtime decision-making
├─ Agent queries: "What are the SLAs?"
├─ Agent queries: "What integration patterns?"
├─ Agent queries: "What security policies?"
└─ Agent gets: Real-time answers from KG

Example:
├─ slas = await mcp.query_domain_rules("cwow-facility", "SLA")
├─ integration = await mcp.query_domain_rules("cwow-facility", "Integration")
├─ security = await mcp.query_domain_rules("cwow-facility", "Security")
└─ performance = await mcp.query_domain_rules("cwow-facility", "Performance")
```

### Key Difference

```
KG Context (SKILL.md)
├─ Static (embedded at skill generation)
├─ Used during onboarding
├─ Guides workflow
└─ Domain-specific

MCP Context (Memory MCP)
├─ Dynamic (queried at runtime)
├─ Used during execution
├─ Supports decisions
└─ Any domain
```

---

## Only Domain-Specific KG Context

### What Gets Embedded

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

---

## Complete Integration Example

### Scenario: Onboarding Facility Service

#### Step 1: Code Onboarding
```bash
$ dva code onboard --path ./facility-service --kg --extract-entities

✓ Analyzed code structure
✓ Queried KG for cwow-facility domain
✓ Generated kg-context.md
✓ Generated 5 domain-aware skills with KG context embedded
✓ Created methodology.yaml
```

#### Step 2: Project Structure
```
facility-service/
├── .skills/
│   ├── generated/
│   │   ├── fhir-api-endpoint-skill/
│   │   │   └─ SKILL.md (with KG context)
│   │   ├── database-optimizer-skill/
│   │   │   └─ SKILL.md (with KG context)
│   │   └─ ... [3 more]
│   └── methodology/
│       ├── design-brainstorm-skill/
│       ├── implementation-planning-skill/
│       ├── test-driven-development-skill/
│       └── code-review-skill/
├── .dva/
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

---

## Key Answers to Your Questions

### Q1: How is KG context attached with the command?

**Answer**: 
1. Command queries KG for domain (cwow-facility)
2. KG context is embedded in generated SKILL.md files
3. Workflow sections reference KG context
4. Skills use KG context to inform all phases

### Q2: Do I include only facility domain KG context?

**Answer**: YES
- Only cwow-facility domain knowledge is queried
- Only facility-specific SLAs, integration specs, security policies are included
- Other domains are not included
- This keeps skills focused and relevant

### Q3: Is KG context used initially only?

**Answer**: YES for initial onboarding
- KG context is embedded in SKILL.md during code onboarding
- Used to guide design, planning, execution, review phases
- MCP is for future queries (not used during initial onboarding)
- Skills can be regenerated if KG changes

### Q4: Do we need full entity extraction?

**Answer**: NO
- Light mode is sufficient for SKILL generation
- Entity extraction is overkill for your goal
- Your goal: Map code context to business requirements
- Light mode provides all needed information

### Q5: How does this integrate with skill workflows?

**Answer**: 
- SKILL.md includes kg_context section
- Workflow phases reference KG context
- Design phase uses KG for questions
- Planning phase uses KG for task breakdown
- Execution phase validates with KG
- Review phase checks against KG

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

---

## Reading Guide

**For Quick Understanding** (10 min):
- Read: `KG_CONTEXT_SKILL_WORKFLOW_SUMMARY.md`

**For Complete Understanding** (30 min):
- Read: `KG_CONTEXT_SKILL_WORKFLOW_SUMMARY.md`
- Read: `docs/plans/KG_CONTEXT_TO_SKILL_WORKFLOW.md`

**For Implementation** (60 min):
- Read all above documents
- Review SKILL_WORKFLOW_INTEGRATION.md
- Study SUPERPOWERS_REFERENCE_ANALYSIS.md

---

**Status**: ✅ COMPLETE & DOCUMENTED

All documents are committed to git and ready for team review!
