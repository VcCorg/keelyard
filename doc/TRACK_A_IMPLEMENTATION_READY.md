# Track A: Implementation Ready - Complete Design Summary

**Status**: ✅ READY FOR IMPLEMENTATION  
**Date**: May 6, 2026  
**Timeline**: 7-12 days  
**Approach**: Simplified separation of concerns with dual MCP integration

---

## Executive Summary

Track A has been completely redesigned with a focus on **simplicity, separation of concerns, and dual MCP integration**:

1. **Domain Creation** - Keep simple (< 1 second)
2. **Knowledge Onboarding** - Separate activity (can run async)
3. **MCP Integration** - Dual approach (Memory MCP + Direct KG Query)

This design is production-ready and can begin implementation on May 7, 2026.

---

## The Three Components

### 1. Domain Creation (Simple & Fast)

**Command**:
```bash
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence CWOV
```

**What it does**:
- ✅ Register domain metadata
- ✅ Store Jira/Bitbucket/Confluence links
- ✅ Done in < 1 second

**What it does NOT do**:
- ❌ Extract documents
- ❌ Extract rules
- ❌ Index in KG
- ❌ Sync to Memory MCP

**Status**: ✅ Already implemented (no changes needed)

---

### 2. Knowledge Onboarding (Separate Activity)

**Command**:
```bash
# Synchronous
dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Asynchronous
dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware --async
```

**What it does**:
- ✅ Scan Confluence space
- ✅ Discover all releases (Release 29, 28, 27, ...)
- ✅ Find domain documents in each release
- ✅ Deduplicate by version (keep latest)
- ✅ Extract content and PDFs
- ✅ Extract rules using LLM
- ✅ Categorize rules (SLA, Integration, Security, Performance)
- ✅ Store in KG
- ✅ Sync to Memory MCP
- ✅ Track job status (if async)

**Benefits**:
- ✅ Can run asynchronously
- ✅ Can be refreshed independently
- ✅ Can be scheduled
- ✅ Doesn't block domain creation

**Timeline**: 5-10 minutes (sync) or background (async)

---

### 3. MCP Integration (Dual Approach)

#### Approach A: Memory MCP (For Agents)

**Purpose**: Agents query business rules during execution

**New Memory MCP Tools**:
```python
# Query rules by category
query_domain_rules(domain, category)
  # Returns: SLAs, Integration specs, Security policies, Performance requirements

# Search rules by keyword
search_rules(keyword)
  # Returns: All rules matching keyword

# Get specific rule types
get_sla(domain)
get_integration_specs(domain)
get_security_policies(domain)
get_performance_requirements(domain)
```

**Agent Usage Example**:
```python
# Agent executing code for Facility domain

# Query Memory MCP for SLA
sla = await mcp_client.call_tool(
    "query_domain_rules",
    {"domain": "cwow-facility", "category": "SLA"}
)

# Agent sees: "Response time < 100ms, Availability > 99.9%"
# Agent uses this in decision-making

if response_time > 100:
    logger.warning(f"SLA violation: {response_time}ms > 100ms")
```

#### Approach B: Direct KG Query (For Code Onboarding)

**Purpose**: Code onboarding enriched with business context

**How it works**:
```
Code Onboarding Analysis
    ↓
Query KG directly for domain knowledge
    ↓
Enrich understanding document
├─ Add Business Context section
├─ List applicable SLAs
├─ List integration requirements
├─ List security requirements
└─ List performance requirements
    ↓
Generate skills aware of business rules
```

**Understanding Document Example**:
```markdown
# Facility Service - Codebase Understanding

## Business Context

### Applicable SLAs
- Response time < 100ms
- Availability > 99.9%

### Integration Requirements
- Must integrate with FHIR API
- Use OAuth 2.0

### Security Requirements
- HIPAA compliant
- AES-256 encryption

### Performance Requirements
- Support 10K concurrent users
- Database query latency < 50ms
```

---

## Implementation Phases

### Phase 1: Keep Domain Create As-Is (0 days)
**Status**: ✅ Already done
- Domain create command is already simple
- Just add hint to run `dva kg onboard` next

### Phase 2: Create KG Onboarding Command (3-5 days)
**New command**: `dva kg onboard`

**New files**:
- `commands/kg.py` - KG commands
- `kg_integration/onboarding.py` - Orchestrator
- `kg_integration/release_document_collector.py` - Release discovery
- `kg_integration/document_deduplicator.py` - Version deduplication
- `kg_integration/version_comparator.py` - Version comparison

**Output**: Domain knowledge stored in KG

### Phase 2.5: KG to Memory MCP Sync (1-2 days)
**Purpose**: Expose domain knowledge as MCP tools for agents

**New file**:
- `kg_integration/kg_to_mcp_sync.py` - Sync logic

**Features**:
- Read rules from KG
- Create entities in Memory MCP
- Create relationships
- Automatic sync after KG onboarding

**Output**: Domain knowledge exposed as MCP tools

### Phase 3: Create Async Job System (2-3 days)
**New file**: `async_jobs/kg_onboarding_job.py`

**Features**:
- Background job execution
- Job status tracking
- Job result storage
- Automatic sync to Memory MCP after completion

**New commands**:
- `dva kg onboard --async` - Run in background
- `dva kg status <job-id>` - Check job status
- `dva kg list-jobs` - List all jobs

### Phase 4: Integrate with Code Onboarding (1-2 days)
**Modify**: `analysis/codebase_analyzer.py`

**Features**:
- Query KG for domain knowledge (direct query)
- Include in understanding documents
- Reference in generated skills

---

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Confluence Releases                          │
│                  (Release 29, 28, 27, ...)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  KG Onboarding      │
                    │  (dva kg onboard)   │
                    └─────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  Knowledge Graph    │
                    │  (Neo4j + LightRAG) │
                    └─────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
        ┌──────────────────┐  ┌──────────────────┐
        │  Sync to Memory  │  │  Direct Query    │
        │  MCP             │  │  (Code Onboarding)
        └──────────────────┘  └──────────────────┘
                    ↓                   ↓
        ┌──────────────────┐  ┌──────────────────┐
        │  Memory MCP      │  │  Code Onboarding │
        │  (Agents query)  │  │  (Enrich docs)   │
        └──────────────────┘  └──────────────────┘
                    ↓                   ↓
        ┌──────────────────┐  ┌──────────────────┐
        │  Agent Execution │  │  Generated Skills│
        │  (Runtime)       │  │  (Aware of rules)│
        └──────────────────┘  └──────────────────┘
```

---

## CLI Workflow

### Step 1: Create Domain (< 1 second)
```bash
$ dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV

✓ Domain registered: cwow-facility

Domain Details
  Name: cwow-facility
  Product: CWOW
  Domain: Facility
  Jira Project: CWOW
  Bitbucket Project: CGF
  Confluence Space: CWOV

Next: Onboard domain knowledge:
  dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
```

### Step 2: Onboard Knowledge (5-10 minutes or async)
```bash
$ dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

Onboarding knowledge for cwow-facility...

✓ Knowledge onboarding complete

Onboarding Summary
  Domain: cwow-facility
  Releases scanned: 5
  Documents found: 20
  After deduplication: 4
  Rules extracted: 45
  Stored in KG: ✓
  Synced to Memory MCP: ✓
```

### Step 3: Code Onboarding (Uses KG)
```bash
$ dva code onboard https://github.com/company/facility-service --domain cwow-facility

✓ Code onboarding complete
  Understanding includes business context from KG
  Generated skills reference business rules
```

### Step 4: Agent Execution (Queries Memory MCP)
```python
# Agent running code for Facility domain

# Query Memory MCP for SLA
sla = await mcp_client.call_tool(
    "query_domain_rules",
    {"domain": "cwow-facility", "category": "SLA"}
)

# Agent sees: "Response time < 100ms"
# Agent uses this in implementation
```

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1 | 0 days | Domain create (already done) |
| 2 | 3-5 days | KG onboarding command |
| 2.5 | 1-2 days | KG to Memory MCP sync |
| 3 | 2-3 days | Async job system |
| 4 | 1-2 days | Code onboarding integration |
| **Total** | **7-12 days** | **Complete Track A** |

---

## Files to Create

```
agentic-cli/src/agentic_cli/
├── commands/kg.py (NEW)
├── kg_integration/ (NEW)
│   ├── __init__.py
│   ├── onboarding.py
│   ├── release_document_collector.py
│   ├── document_deduplicator.py
│   ├── version_comparator.py
│   └── kg_to_mcp_sync.py
└── async_jobs/ (NEW)
    ├── __init__.py
    └── kg_onboarding_job.py
```

---

## Files to Modify

```
agentic-cli/src/agentic_cli/
├── commands/__init__.py (add kg_app)
├── commands/domain.py (add hint for kg onboard)
├── tracker.py (add kg_onboarding_jobs table)
└── analysis/codebase_analyzer.py (query KG)
```

---

## Database Schema

### New Table: kg_onboarding_jobs
```sql
CREATE TABLE kg_onboarding_jobs (
    id INTEGER PRIMARY KEY,
    job_id TEXT UNIQUE,
    domain_id TEXT NOT NULL,
    confluence_space TEXT,
    status TEXT,  -- pending, running, completed, failed
    releases_scanned INTEGER,
    documents_found INTEGER,
    documents_after_dedup INTEGER,
    rules_extracted INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

---

## Success Criteria

- [ ] Domain create command works (already done)
- [ ] KG onboarding command working
- [ ] Release-aware document collection working
- [ ] Version deduplication working
- [ ] Rule extraction working
- [ ] KG storage working
- [ ] Memory MCP sync working
- [ ] Async job system working
- [ ] Code onboarding integration smooth
- [ ] Agents can query Memory MCP
- [ ] Tests passing

---

## Key Design Decisions

### 1. Separation of Concerns
- Domain creation is simple and fast
- Knowledge onboarding is separate and can run async
- Each command has single responsibility

### 2. Dual MCP Integration
- Memory MCP for agents (runtime queries)
- Direct KG Query for code onboarding (analysis time)
- Single source of truth (KG)

### 3. Release-Aware Document Collection
- Scan all releases automatically
- Deduplicate by version (keep latest)
- Support version strategies (latest, all, compare)

### 4. Async Support
- KG onboarding can run in background
- Job status tracking
- Automatic sync to Memory MCP after completion

---

## Benefits

### For Users
- ✅ Domain creation is fast and simple
- ✅ Knowledge onboarding is a separate, clear step
- ✅ Can refresh knowledge without recreating domain
- ✅ Can run knowledge onboarding in background

### For Development
- ✅ Each command has single responsibility
- ✅ Easy to test independently
- ✅ Easy to add new features
- ✅ Easy to handle failures

### For Agents
- ✅ Can query business rules during execution
- ✅ Real-time access to domain knowledge
- ✅ Can make better decisions

### For Code Onboarding
- ✅ Understanding documents include business context
- ✅ Generated skills aware of business constraints
- ✅ Better code analysis

### For Future
- ✅ Refresh KG without domain changes
- ✅ Schedule periodic KG updates
- ✅ Support multiple knowledge sources
- ✅ Implement KG versioning
- ✅ Add KG search and query interface

---

## Next Steps

1. **Review** this complete design
2. **Approve** the approach
3. **Begin Phase 2** on May 7, 2026
4. **Daily standups** to track progress
5. **Weekly syncs** to verify integration

---

## Related Documents

- `docs/plans/TRACK_A_SIMPLIFIED_DESIGN.md` - Detailed simplified design
- `docs/plans/TRACK_A_MCP_INTEGRATION_STRATEGY.md` - MCP integration strategy
- `TRACK_A_FINAL_DESIGN.md` - Final design summary

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**Date Prepared**: May 6, 2026  
**Target Start**: May 7, 2026  
**Target Completion**: May 19, 2026 (7-12 days)

---

## Summary

Track A is now completely designed with:

✅ **Simple domain creation** - Just metadata, < 1 second  
✅ **Separate knowledge onboarding** - Can run async, be refreshed, be scheduled  
✅ **Dual MCP integration** - Memory MCP for agents, Direct KG Query for code onboarding  
✅ **Release-aware document collection** - Scan all releases, deduplicate by version  
✅ **Clean separation of concerns** - Each component has single responsibility  

This is a production-ready design that can begin implementation immediately.

**Ready to build! 🚀**
