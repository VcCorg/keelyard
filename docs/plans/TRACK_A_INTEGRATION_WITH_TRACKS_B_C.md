# Track A Integration with Tracks B & C

**Date**: May 6, 2026  
**Status**: Design Complete  
**Focus**: How domain-driven business context flows through all three tracks

---

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRACK A: Domain Registration                     │
│                                                                         │
│  keel domain create Facility --product CWOW                             │
│    --jira CWOW --bb CGF --confluence MTT                              │
│    --ingest-business-context                                          │
│    --context-pages "Business Rules,SLA,Integration Specs"             │
│                                                                         │
│  ↓                                                                       │
│  Extract business context from Confluence                              │
│  ├─ List pages in MTT space                                            │
│  ├─ Download PDFs from pages                                           │
│  ├─ Extract text from PDFs                                             │
│  ├─ Extract rules using LLM                                            │
│  └─ Categorize (SLA, Integration, Security, Performance)              │
│                                                                         │
│  ↓                                                                       │
│  Store in Memory MCP                                                    │
│  ├─ SLA entities                                                        │
│  ├─ IntegrationSpec entities                                           │
│  ├─ SecurityPolicy entities                                            │
│  └─ PerformanceRequirement entities                                    │
│                                                                         │
│  ↓                                                                       │
│  Store in KG (Neo4j)                                                    │
│  ├─ Domain node                                                         │
│  ├─ Rule nodes                                                          │
│  └─ Relationships                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    TRACK B: Code Onboarding                             │
│                                                                         │
│  keel code onboard https://github.com/company/facility-service         │
│    --domain cwow-facility                                              │
│                                                                         │
│  ↓                                                                       │
│  Phase 1: Repository Analysis                                          │
│  ├─ Analyze code structure                                             │
│  ├─ Detect tech stack                                                  │
│  ├─ Identify patterns                                                  │
│  └─ [NEW] Query business context for domain                           │
│      ├─ Get SLAs from Memory MCP                                       │
│      ├─ Get integration specs from Memory MCP                          │
│      ├─ Get security policies from Memory MCP                          │
│      └─ Get performance requirements from Memory MCP                   │
│                                                                         │
│  ↓                                                                       │
│  Phase 2: Interactive Questionnaire                                    │
│  ├─ Ask about business goals                                           │
│  ├─ Ask about key workflows                                            │
│  ├─ Ask about pain points                                              │
│  └─ [NEW] Reference business context in questions                     │
│      └─ "How does this relate to SLA: <SLA from Track A>?"            │
│                                                                         │
│  ↓                                                                       │
│  Phase 3: Understanding Document                                       │
│  ├─ Architecture overview                                              │
│  ├─ Key files and purposes                                             │
│  ├─ Development workflow                                               │
│  ├─ Testing strategy                                                   │
│  └─ [NEW] Business Context section                                    │
│      ├─ Applicable SLAs                                                │
│      ├─ Integration Requirements                                       │
│      ├─ Security Requirements                                          │
│      └─ Performance Requirements                                       │
│                                                                         │
│  ↓                                                                       │
│  Phase 4: Auto-Skill Generation                                        │
│  ├─ Generate 8-15 domain-specific skills                               │
│  └─ [NEW] Skills aware of business context                            │
│      ├─ Skills include SLA compliance checks                           │
│      ├─ Skills include security requirements                           │
│      ├─ Skills include integration patterns                            │
│      └─ Skills include performance considerations                      │
│                                                                         │
│  ↓                                                                       │
│  Phase 5: Methodology Matching                                         │
│  └─ Recommend methodology based on analysis + business context        │
│                                                                         │
│  ↓                                                                       │
│  Output:                                                                │
│  ├─ .keel/codebase-understanding.md (includes business context)        │
│  ├─ 8-15 auto-generated skills (aware of business rules)              │
│  └─ Methodology pack recommendation                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                   TRACK C: Knowledge Graph Integration                  │
│                                                                         │
│  [Parallel to Track B]                                                 │
│                                                                         │
│  Phase 1: KG Entity Model                                              │
│  ├─ Project entity                                                     │
│  ├─ Framework entity                                                   │
│  ├─ Pattern entity                                                     │
│  ├─ Convention entity                                                  │
│  ├─ File entity                                                        │
│  └─ [NEW] BusinessRule entity (from Track A)                          │
│      └─ Link to Domain, SLA, IntegrationSpec, etc.                    │
│                                                                         │
│  ↓                                                                       │
│  Phase 2: KG-Enhanced Analysis                                         │
│  ├─ Query for similar projects                                         │
│  ├─ Query for known patterns                                           │
│  ├─ Query for conventions                                              │
│  └─ [NEW] Query for similar business contexts                         │
│      └─ "Find projects with similar SLAs"                             │
│                                                                         │
│  ↓                                                                       │
│  Phase 3: KG-Based Skill Generation                                    │
│  ├─ Generate skills from patterns                                      │
│  └─ [NEW] Generate skills from business patterns                      │
│      └─ "Generate skill for SLA compliance checking"                  │
│                                                                         │
│  ↓                                                                       │
│  Phase 4: KG Query Interface                                           │
│  ├─ agent kg search-projects                                           │
│  ├─ agent kg search-patterns                                           │
│  ├─ agent kg search-conventions                                        │
│  └─ [NEW] agent kg search-business-rules                              │
│      └─ "Find all SLAs across projects"                               │
│                                                                         │
│  Output:                                                                │
│  ├─ Semantic codebase graphs                                           │
│  ├─ Pattern reuse across projects                                      │
│  ├─ Similar project discovery                                          │
│  └─ Business rule discovery and reuse                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Through All Tracks

### Track A → Track B
```
Domain Business Context (Memory MCP)
    ↓
Code Onboarding Analysis
    ├─ Queries Memory MCP for domain's business context
    ├─ Includes in understanding document
    ├─ References in generated skills
    └─ Adds to skill metadata
```

**Example**:
```
Domain: cwow-facility
Business Context from Track A:
  - SLA: "Response time < 100ms"
  - Integration: "Must integrate with FHIR API"
  - Security: "HIPAA compliant"
  - Performance: "Support 10K concurrent users"

Code Onboarding (Track B):
  - Understanding doc includes SLA section
  - Generated skill: "FHIR Integration Skill"
    - Includes FHIR API integration patterns
    - References SLA for performance
    - Includes HIPAA compliance checks
```

### Track A → Track C
```
Domain Business Context (KG)
    ↓
KG-Enhanced Analysis
    ├─ Queries KG for business rule patterns
    ├─ Finds similar projects with same rules
    ├─ Generates skills from business patterns
    └─ Enables business rule discovery
```

**Example**:
```
Domain: cwow-facility
Business Rules in KG:
  - SLA: "Response time < 100ms"
  - SLA: "Availability > 99.9%"
  - Integration: "FHIR API"

KG Queries:
  - "Find other projects with FHIR integration"
    → cwow-patient, imto-imaging
  - "Find all SLA patterns"
    → Response time, Availability, Throughput
  - "Generate skill for SLA compliance"
    → Creates reusable SLA monitoring skill
```

### Track B → Track C
```
Code Analysis (Track B)
    ↓
KG Enrichment (Track C)
    ├─ Stores analysis results in KG
    ├─ Creates Project, Framework, Pattern entities
    ├─ Links to Business Rules from Track A
    └─ Enables pattern reuse
```

**Example**:
```
Code Onboarding Analysis:
  - Language: Python
  - Framework: FastAPI
  - Pattern: async-await
  - Convention: snake_case

KG Storage:
  - Project node: facility-service
  - Framework node: FastAPI
  - Pattern node: async-await
  - Convention node: snake_case
  - Links to Business Rules: SLA, Integration, Security
```

---

## Execution Timeline

### Week 1: Parallel Execution

**Monday-Tuesday**:
- Track A Phase 1: Domain registration enhancement
- Track B Phase 1: Repository analysis
- Track C Phase 1: KG entity model

**Wednesday-Thursday**:
- Track A Phase 2: Confluence PDF extraction
- Track B Phase 2: Questionnaire
- Track C Phase 1 (continued)

**Friday**:
- Sync and integration testing
- Verify Track A → Track B data flow

### Week 2: Integration & Completion

**Monday-Tuesday**:
- Track A Phase 3-4: Rule extraction and storage
- Track B Phase 3: Skill generation (using Track A context)
- Track C Phase 2: KG-enhanced analysis

**Wednesday-Thursday**:
- Track A Phase 5: Code onboarding integration
- Track B Phase 4-5: Methodology + CLI
- Track C Phase 3-4: KG skills + query interface

**Friday**:
- Final integration testing
- End-to-end workflow validation
- Prepare for release

---

## Integration Points

### 1. Memory MCP Integration
```
Track A stores rules in Memory MCP
    ↓
Track B queries Memory MCP during analysis
    ↓
Track C references Memory MCP entities in KG
```

### 2. KG Integration
```
Track A stores rules in KG
    ↓
Track B enriches analysis with KG data
    ↓
Track C uses KG for pattern discovery
```

### 3. Skill Generation Integration
```
Track A provides business context
    ↓
Track B generates skills aware of context
    ↓
Track C generates skills from business patterns
```

### 4. Code Onboarding Integration
```
Track A provides business context
    ↓
Track B includes context in understanding
    ↓
Track C enriches with pattern recommendations
```

---

## Example End-to-End Workflow

### Step 1: Register Domain with Business Context (Track A)
```bash
keel domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence MTT \
  --ingest-business-context \
  --context-pages "Business Rules,SLA,Integration Specs,Security Policies"
```

**Output**:
- Domain registered: cwow-facility
- Business context extracted: 15 rules
- Stored in Memory MCP: ✓
- Stored in KG: ✓

### Step 2: Onboard Repository (Track B)
```bash
keel code onboard https://github.com/company/facility-service \
  --domain cwow-facility
```

**Output**:
- Analysis complete
- Understanding document generated (includes business context)
- 12 skills auto-generated (aware of SLAs, security, integration)
- Methodology recommended: "Healthcare Development"

### Step 3: Discover Patterns (Track C)
```bash
agent kg search-business-rules --category SLA
agent kg search-projects --with-rule "Response time < 100ms"
agent kg search-patterns --domain cwow-facility
```

**Output**:
- Found 3 projects with similar SLAs
- Found 5 patterns used in healthcare projects
- Generated reusable SLA monitoring skill

---

## Benefits of Integration

### For Domain Owners
- ✅ Business context automatically extracted and reused
- ✅ Consistent application across all projects in domain
- ✅ Easy to discover related projects

### For Code Onboarding
- ✅ Richer understanding with business context
- ✅ Skills aware of business constraints
- ✅ Better recommendations

### For Knowledge Graph
- ✅ Business rules integrated with code patterns
- ✅ Cross-domain pattern discovery
- ✅ Better recommendations

### For Organization
- ✅ Business knowledge captured and reused
- ✅ Consistent governance across projects
- ✅ Faster onboarding with better context
- ✅ Better skill generation and reuse

---

## Success Criteria

### Integration Success
- [ ] Track A business context flows to Track B
- [ ] Track B includes business context in understanding
- [ ] Track B skills reference business rules
- [ ] Track C KG includes business rules
- [ ] Track C queries work across business rules
- [ ] End-to-end workflow smooth

### Data Consistency
- [ ] Business rules in Memory MCP match KG
- [ ] Domain metadata consistent across tracks
- [ ] Skill metadata includes business context
- [ ] Queries return consistent results

### User Experience
- [ ] Single command registers domain with context
- [ ] Code onboarding includes business context
- [ ] Skills are business-aware
- [ ] Pattern discovery works

---

## Next Steps

1. **Review** this integration design
2. **Approve** the approach
3. **Begin Week 1** with parallel execution
4. **Daily standups** to coordinate between tracks
5. **Weekly syncs** to verify integration points
6. **End-to-end testing** at the end of each week

---

**Document Status**: Ready for Implementation  
**Last Updated**: May 6, 2026  
**Next Step**: Begin three-track parallel execution
