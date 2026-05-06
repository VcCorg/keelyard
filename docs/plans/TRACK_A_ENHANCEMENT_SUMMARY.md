# Track A Enhancement: Domain-Driven Business Context

**Date**: May 6, 2026  
**Status**: Design Complete  
**Impact**: Leverages existing domain infrastructure for business context extraction

---

## The Enhancement

Instead of building a standalone business context system, Track A now leverages the existing `domain register` command infrastructure to automatically extract and internalize business context when a domain is registered with Confluence space links.

### Before (Generic Approach)
```bash
# Separate business context extraction
dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT
# Then separately:
dva business-context extract --confluence-space MTT --output context.json
```

### After (Domain-Driven Approach)
```bash
# Business context extracted automatically during domain registration
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --ingest-business-context \
  --context-pages "Business Rules,SLA,Integration Specs"
```

---

## Why This Is Better

### 1. **Reuses Existing Infrastructure**
- ✅ Domain registration already exists
- ✅ Domain metadata already stored
- ✅ No need for separate commands
- ✅ Leverages existing tracker.py database

### 2. **Automatic & Seamless**
- ✅ Business context extracted when domain registered
- ✅ No separate manual steps
- ✅ Rules always up-to-date with Confluence
- ✅ Single source of truth

### 3. **Domain-Scoped Context**
- ✅ Business context tied to specific domain
- ✅ Easy to query rules for a domain
- ✅ Support for multi-domain products
- ✅ Clear ownership and governance

### 4. **Integrated with Code Onboarding**
- ✅ When onboarding a domain's repository
- ✅ Automatically query business context
- ✅ Include in understanding documents
- ✅ Reference in generated skills

---

## Implementation Overview

### 5 Phases (8-13 days)

#### Phase 1: Domain Registration Enhancement (2-3 days)
**What**: Add CLI options to `domain create` command
```bash
--ingest-business-context      # Enable extraction
--context-pages "Page1,Page2"  # Specify pages
--auto-categorize              # Auto-categorize rules
```

**Creates**: `DomainBusinessContextManager` class

#### Phase 2: Confluence PDF Extraction (2-3 days)
**What**: Extend Confluence MCP with PDF capabilities
```python
list_page_attachments(page_id)
download_attachment(url)
extract_pdf_text(pdf_bytes)
list_space_pages(space_key)
```

**Adds**: 4 new MCP tools

#### Phase 3: Rule Extraction & Categorization (2-3 days)
**What**: Extract and categorize business rules
```python
RuleExtractor:
  - LLM-based extraction
  - Auto-categorization (SLA, Integration, Security, Performance)
  - Regex fallback
  - Confidence scoring
```

#### Phase 4: Memory MCP Storage (1-2 days)
**What**: Store rules as queryable entities
```
SLA entities
IntegrationSpec entities
SecurityPolicy entities
PerformanceRequirement entities
```

#### Phase 5: Code Onboarding Integration (1-2 days)
**What**: Query and use business context during analysis
```python
CodebaseAnalyzer:
  - Query business context for domain
  - Include in understanding document
  - Reference in generated skills
```

---

## CLI Usage Examples

### Register Domain with Business Context
```bash
# Extract all documentation pages
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context

# Extract specific pages
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context \
  --context-pages "Business Rules,SLA,Integration Specs,Security Policies"

# Extract without auto-categorization
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context \
  --no-auto-categorize
```

### Query Business Context
```bash
# NEW COMMANDS
dva domain show-context cwow-facility
dva domain search-rules --domain cwow-facility --category SLA
dva domain search-rules --category Integration
dva domain search-rules --keyword "authentication"
```

### Use During Code Onboarding
```bash
# Code onboarding automatically includes business context
dva code onboard https://github.com/company/facility-service \
  --domain cwow-facility

# Output includes:
# - Business Rules section
# - Applicable SLAs
# - Integration Requirements
# - Security Requirements
# - Performance Requirements
```

---

## Data Flow

```
Domain Registration
    ↓
    ├─→ Store domain metadata (existing)
    │
    ├─→ [NEW] Extract business context
    │   ├─ List Confluence pages in space
    │   ├─ Find and download PDFs
    │   ├─ Extract text from PDFs
    │   └─ Extract rules using LLM
    │
    ├─→ [NEW] Categorize rules
    │   ├─ SLA
    │   ├─ Integration
    │   ├─ Security
    │   ├─ Performance
    │   └─ Business
    │
    ├─→ [NEW] Store in Memory MCP
    │   ├─ Create SLA entities
    │   ├─ Create IntegrationSpec entities
    │   ├─ Create SecurityPolicy entities
    │   └─ Create PerformanceRequirement entities
    │
    └─→ [NEW] Store in KG
        ├─ Create Domain node
        ├─ Create Rule nodes
        └─ Create relationships
            ↓
Code Onboarding
    ↓
    ├─→ Query business context for domain
    │   ├─ Get SLAs
    │   ├─ Get integration specs
    │   ├─ Get security policies
    │   └─ Get performance requirements
    │
    ├─→ Include in understanding document
    │   ├─ Business Context section
    │   ├─ Applicable SLAs
    │   ├─ Integration Requirements
    │   ├─ Security Requirements
    │   └─ Performance Requirements
    │
    └─→ Reference in generated skills
        ├─ Skills aware of SLAs
        ├─ Skills aware of security requirements
        └─ Skills include compliance checks
```

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
    memory_mcp_entities TEXT,  -- JSON: {entity_type: entity_id}
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

## Files to Create/Modify

### New Files
```
agentic-cli/src/agentic_cli/domain_context/
├── __init__.py
├── business_context_manager.py    # Orchestrate extraction and storage
├── rule_extractor.py              # Extract and categorize rules
└── tests/
    └── test_domain_context.py
```

### Modified Files
```
agentic-cli/src/agentic_cli/
├── commands/domain.py             # Add new CLI options and integration
├── tracker.py                     # Add database tables
├── analysis/codebase_analyzer.py  # Query business context
└── analysis/understanding_generator.py  # Include in document

mcp-servers/confluence/src/confluence_mcp/
├── confluence_client.py           # Add PDF methods
└── server.py                      # Add MCP tools
```

---

## Success Criteria

### Phase 1: Domain Registration Enhancement
- [ ] New CLI options added and working
- [ ] DomainBusinessContextManager created
- [ ] Integration with domain create command
- [ ] Tests passing

### Phase 2: Confluence PDF Extraction
- [ ] PDF extraction working reliably
- [ ] MCP tools added and functional
- [ ] Tests with real PDFs
- [ ] Error handling for corrupted PDFs

### Phase 3: Rule Extraction & Categorization
- [ ] Rule extractor working
- [ ] LLM-based categorization accurate
- [ ] Regex fallback working
- [ ] Tests with real documents

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

## Benefits Summary

### For Domain Owners
- ✅ Business context automatically extracted when domain registered
- ✅ No manual data entry required
- ✅ Rules always up-to-date with Confluence
- ✅ Easy to update by updating Confluence pages

### For Code Onboarding
- ✅ Codebase understanding includes business context
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
- ✅ Consistent application of rules across projects
- ✅ Better governance and compliance
- ✅ Reduced onboarding time for new projects

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

## Comparison: Generic vs Domain-Driven

### Generic Approach (Original)
```
Pros:
- Standalone system
- Works without domain registration

Cons:
- Separate extraction process
- Manual configuration
- Not tied to domains
- Harder to query by domain
- Duplicate effort if multiple domains
```

### Domain-Driven Approach (Enhanced)
```
Pros:
- Leverages existing domain infrastructure
- Automatic extraction during registration
- Tied to specific domain
- Easy to query by domain
- Single source of truth
- Reuses domain metadata

Cons:
- Requires domain registration first
- More complex domain create command
```

**Verdict**: Domain-driven approach is better for multi-domain products like CWOW and IMTO.

---

## Next Steps

1. **Review** this enhancement with team
2. **Approve** the domain-driven approach
3. **Begin Phase 1** - Domain registration enhancement
4. **Follow phases** 2-5 in sequence
5. **Test** end-to-end with real domain and Confluence space

---

**Document Status**: Ready for Implementation  
**Last Updated**: May 6, 2026  
**Next Step**: Begin Phase 1 implementation
