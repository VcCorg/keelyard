# Track A: Domain-Driven Business Context - Ready for Implementation

**Status**: ✅ Design Complete & Ready for Execution  
**Date**: May 6, 2026  
**Enhancement**: Leverage domain register infrastructure for business context extraction

---

## What Has Been Designed

A complete, production-ready design for Track A that leverages the existing `domain register` command infrastructure to automatically extract and internalize business context from Confluence when a domain is registered.

### Key Innovation
Instead of building a standalone business context system, we **reuse the domain registration system** that already exists and is actively used in the codebase.

---

## Documents Created

### 1. **TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md** (Detailed Design)
- Complete 5-phase implementation plan
- Code examples for each phase
- Database schema updates
- CLI usage examples
- 825 lines of detailed specifications

### 2. **TRACK_A_ENHANCEMENT_SUMMARY.md** (Executive Summary)
- Why this approach is better
- 5 phases overview
- Data flow diagram
- Benefits summary
- Comparison with generic approach

### 3. **TRACK_A_INTEGRATION_WITH_TRACKS_B_C.md** (Integration Guide)
- How Track A flows into Track B
- How Track A flows into Track C
- Complete end-to-end workflow
- Week 1 & 2 execution timeline
- Integration points and success criteria

### 4. **THREE_TRACK_IMPLEMENTATION_ROADMAP.md** (Updated)
- Phase 1 now reflects domain-driven approach
- References detailed design document
- 5 sub-phases with deliverables
- Success criteria

---

## The 5 Implementation Phases

### Phase 1: Domain Registration Enhancement (2-3 days)
**What**: Add CLI options to `domain create` command
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence MTT \
  --ingest-business-context \
  --context-pages "Business Rules,SLA,Integration Specs"
```

**Creates**: `DomainBusinessContextManager` class

**Files**:
- `agentic-cli/src/agentic_cli/domain_context/business_context_manager.py` (NEW)
- `agentic-cli/src/agentic_cli/commands/domain.py` (MODIFY)

---

### Phase 2: Confluence PDF Extraction (2-3 days)
**What**: Extend Confluence MCP with PDF capabilities

**New Methods**:
```python
list_page_attachments(page_id)
download_attachment(url)
extract_pdf_text(pdf_bytes)
list_space_pages(space_key)
```

**New MCP Tools**:
- `confluence_list_attachments`
- `confluence_download_attachment`
- `confluence_extract_pdf_text`
- `confluence_list_space_pages`

**Files**:
- `mcp-servers/confluence/src/confluence_mcp/confluence_client.py` (MODIFY)
- `mcp-servers/confluence/src/confluence_mcp/server.py` (MODIFY)

---

### Phase 3: Rule Extraction & Categorization (2-3 days)
**What**: Extract and categorize business rules from PDFs

**Creates**: `RuleExtractor` class with:
- LLM-based rule extraction
- Auto-categorization (SLA, Integration, Security, Performance)
- Regex fallback patterns
- Confidence scoring

**Categories**:
- SLA (Response time, Availability, Uptime)
- Integration (APIs, Endpoints, Protocols)
- Security (Authentication, Authorization, Encryption)
- Performance (Latency, Throughput, Capacity)
- Business (General business rules)
- Compliance (Regulatory requirements)

**Files**:
- `agentic-cli/src/agentic_cli/domain_context/rule_extractor.py` (NEW)

---

### Phase 4: Memory MCP Storage (1-2 days)
**What**: Store extracted rules as queryable entities in Memory MCP

**Entity Types**:
- `SLA` - Service level agreements
- `IntegrationSpec` - Integration specifications
- `SecurityPolicy` - Security policies
- `PerformanceRequirement` - Performance requirements
- `BusinessRule` - General business rules

**Capabilities**:
- Store entities with properties
- Create relationships
- Enable semantic search
- Query by domain
- Query by category

**Files**:
- `agentic-cli/src/agentic_cli/domain_context/business_context_manager.py` (MODIFY)

---

### Phase 5: Code Onboarding Integration (1-2 days)
**What**: Query and use business context during code analysis

**Integration Points**:
- Query business context during analysis
- Include in understanding documents
- Reference in generated skills
- Add to skill metadata

**New Sections in Understanding Document**:
- Business Context
- Applicable SLAs
- Integration Requirements
- Security Requirements
- Performance Requirements

**Files**:
- `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py` (MODIFY)
- `agentic-cli/src/agentic_cli/analysis/understanding_generator.py` (MODIFY)

---

## Database Schema

### New Table: domain_business_context
```sql
CREATE TABLE domain_business_context (
    id INTEGER PRIMARY KEY,
    domain_id TEXT NOT NULL,
    confluence_space TEXT,
    confluence_url TEXT,
    extracted_at TIMESTAMP,
    pages_extracted INTEGER,
    pdfs_extracted INTEGER,
    total_rules INTEGER,
    memory_mcp_entities TEXT,  -- JSON
    kg_node_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

### New Table: domain_business_rules
```sql
CREATE TABLE domain_business_rules (
    id INTEGER PRIMARY KEY,
    domain_context_id INTEGER,
    rule_title TEXT,
    rule_content TEXT,
    category TEXT,  -- SLA, Integration, Security, Performance, Business, Compliance
    source_page TEXT,
    confidence REAL,
    memory_mcp_entity_id TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (domain_context_id) REFERENCES domain_business_context(id)
);
```

---

## CLI Commands

### Register Domain with Business Context
```bash
# Extract all documentation
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context

# Extract specific pages
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context \
  --context-pages "Business Rules,SLA,Integration Specs,Security Policies"

# Extract without auto-categorization
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context \
  --no-auto-categorize
```

### Query Business Context (NEW)
```bash
dva domain show-context cwow-facility
dva domain search-rules --domain cwow-facility --category SLA
dva domain search-rules --category Integration
dva domain search-rules --keyword "authentication"
```

### Use During Code Onboarding
```bash
dva code onboard https://github.com/company/facility-service \
  --domain cwow-facility
```

---

## Data Flow

```
Domain Registration
    ↓
Extract Business Context
├─ List Confluence pages
├─ Download PDFs
├─ Extract text
└─ Extract rules using LLM
    ↓
Categorize Rules
├─ SLA
├─ Integration
├─ Security
├─ Performance
└─ Business
    ↓
Store in Memory MCP
├─ Create SLA entities
├─ Create IntegrationSpec entities
├─ Create SecurityPolicy entities
└─ Create PerformanceRequirement entities
    ↓
Store in KG (Neo4j)
├─ Create Domain node
├─ Create Rule nodes
└─ Create relationships
    ↓
Code Onboarding
├─ Query business context
├─ Include in understanding document
└─ Reference in generated skills
```

---

## Integration with Tracks B & C

### Track A → Track B (Code Onboarding)
- Business context queried during analysis
- Included in understanding documents
- Referenced in generated skills
- Skills aware of business constraints

### Track A → Track C (Knowledge Graph)
- Business rules stored in KG
- KG-enhanced analysis uses rules
- Skills generated from business patterns
- Business rule discovery across projects

---

## Success Criteria

### Phase 1: Domain Registration Enhancement
- [ ] New CLI options added
- [ ] DomainBusinessContextManager created
- [ ] Integration with domain create working
- [ ] Tests passing

### Phase 2: Confluence PDF Extraction
- [ ] PDF extraction working reliably
- [ ] MCP tools added and functional
- [ ] Tests with real PDFs passing
- [ ] Error handling for corrupted PDFs

### Phase 3: Rule Extraction & Categorization
- [ ] Rule extractor working
- [ ] LLM-based categorization accurate
- [ ] Regex fallback working
- [ ] Tests with real documents passing

### Phase 4: Memory MCP Storage
- [ ] Entities stored correctly
- [ ] Queries working
- [ ] Relationships established
- [ ] Tests passing

### Phase 5: Code Onboarding Integration
- [ ] Business context queried during analysis
- [ ] Included in understanding document
- [ ] Skills reference business rules
- [ ] End-to-end test passing

---

## Timeline

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1 | 2-3 days | Domain registration enhancement |
| 2 | 2-3 days | Confluence PDF extraction |
| 3 | 2-3 days | Rule extraction & categorization |
| 4 | 1-2 days | Memory MCP storage |
| 5 | 1-2 days | Code onboarding integration |
| **Total** | **8-13 days** | **Full domain-driven business context** |

---

## Files to Create

```
agentic-cli/src/agentic_cli/domain_context/
├── __init__.py
├── business_context_manager.py    # Orchestrate extraction and storage
├── rule_extractor.py              # Extract and categorize rules
└── tests/
    └── test_domain_context.py
```

---

## Files to Modify

```
agentic-cli/src/agentic_cli/
├── commands/domain.py             # Add new CLI options
├── tracker.py                     # Add database tables
├── analysis/codebase_analyzer.py  # Query business context
└── analysis/understanding_generator.py  # Include in document

mcp-servers/confluence/src/confluence_mcp/
├── confluence_client.py           # Add PDF methods
└── server.py                      # Add MCP tools
```

---

## Benefits

### For Domain Owners
- ✅ Business context automatically extracted
- ✅ No manual data entry
- ✅ Rules always up-to-date with Confluence
- ✅ Easy to update by updating Confluence

### For Code Onboarding
- ✅ Richer understanding with business context
- ✅ Generated skills aware of business constraints
- ✅ SLAs and security requirements documented
- ✅ Integration requirements clear

### For Agents
- ✅ Agents know business rules before coding
- ✅ Can query business context during execution
- ✅ Better compliance and governance
- ✅ Fewer surprises and rework

### For Organization
- ✅ Business knowledge captured and reused
- ✅ Consistent application across projects
- ✅ Better governance and compliance
- ✅ Reduced onboarding time

---

## Why This Approach Is Better

### Reuses Existing Infrastructure
- ✅ Domain registration already exists
- ✅ Domain metadata already stored
- ✅ No need for separate commands
- ✅ Leverages existing tracker.py database

### Automatic & Seamless
- ✅ Business context extracted when domain registered
- ✅ No separate manual steps
- ✅ Rules always up-to-date
- ✅ Single source of truth

### Domain-Scoped Context
- ✅ Business context tied to specific domain
- ✅ Easy to query rules for a domain
- ✅ Support for multi-domain products
- ✅ Clear ownership and governance

### Integrated with Code Onboarding
- ✅ When onboarding a domain's repository
- ✅ Automatically query business context
- ✅ Include in understanding documents
- ✅ Reference in generated skills

---

## Getting Started

### Step 1: Review (30 min)
- Read `TRACK_A_ENHANCEMENT_SUMMARY.md`
- Read `TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md`
- Review `TRACK_A_INTEGRATION_WITH_TRACKS_B_C.md`

### Step 2: Approve (1 hour)
- Discuss with team
- Get stakeholder approval
- Confirm approach

### Step 3: Begin Phase 1 (2-3 days)
- Extend domain registration command
- Create DomainBusinessContextManager
- Add CLI options
- Write tests

### Step 4: Continue Phases 2-5 (6-10 days)
- Follow the detailed design
- Daily standups
- Weekly syncs
- Integration testing

---

## Next Steps

1. **Review** this document and the three detailed design documents
2. **Approve** the domain-driven approach with stakeholders
3. **Assign** team member to Track A
4. **Begin Phase 1** - Domain registration enhancement
5. **Daily standups** to track progress
6. **Weekly syncs** to verify integration with Tracks B & C

---

## Document References

### Track A Design Documents
- `docs/plans/TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md` - Detailed 5-phase design
- `docs/plans/TRACK_A_ENHANCEMENT_SUMMARY.md` - Executive summary
- `docs/plans/TRACK_A_INTEGRATION_WITH_TRACKS_B_C.md` - Integration guide

### Three-Track Plan
- `docs/plans/THREE_TRACK_IMPLEMENTATION_ROADMAP.md` - Updated main roadmap
- `docs/plans/TRACKS_SUMMARY.md` - Executive overview
- `docs/guides/THREE_TRACKS_GETTING_STARTED.md` - Getting started guide

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**Date Prepared**: May 6, 2026  
**Target Start**: May 7, 2026  
**Target Completion**: May 20, 2026 (8-13 days)

---

## Summary

Track A has been redesigned to leverage the existing domain registration infrastructure for business context extraction. This approach is:

- **Better**: Reuses existing infrastructure
- **Simpler**: Automatic and seamless
- **Integrated**: Works with Tracks B & C
- **Scalable**: Supports multi-domain products

The design is complete and ready for implementation. All necessary documentation has been created. The team can begin Phase 1 immediately.

**Let's build this! 🚀**
