# Track A: Final Design - Simplified Separation of Concerns

**Status**: ✅ FINAL DESIGN - READY FOR IMPLEMENTATION  
**Date**: May 6, 2026  
**Approach**: Keep domain creation simple, move knowledge onboarding to separate commands

---

## The Insight

Domain creation should be **simple and fast** (< 1 second). Knowledge onboarding should be a **separate activity** that can run asynchronously, be refreshed independently, and be scheduled without affecting domain management.

---

## Two Simple Commands

### 1. Domain Create (Keep Simple)
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

### 2. Knowledge Onboarding (Separate Command)
```bash
dva kg onboard --domain cwow-facility --confluence-space CWOV
```

**What it does**:
- ✅ Scan Confluence for domain documents
- ✅ Collect and deduplicate documents
- ✅ Extract rules
- ✅ Store in Memory MCP and KG

**Can run**:
- ✅ Immediately after domain creation
- ✅ Asynchronously (background job)
- ✅ Periodically (scheduled refresh)
- ✅ Independently (without domain changes)

---

## Architecture

### Domain Creation Flow (< 1 second)
```
User: dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
    ↓
Validate inputs
    ↓
Store in database
    ↓
Done
    ↓
Output: Domain registered successfully
        Next: dva kg onboard --domain cwow-facility --confluence-space CWOV
```

### Knowledge Onboarding Flow (5-10 minutes)
```
User: dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
    ↓
Phase 1: Release Discovery
├─ Discover all releases
└─ Sort by release number
    ↓
Phase 2: Document Collection
├─ Find domain documents
├─ Extract metadata
└─ Deduplicate by version
    ↓
Phase 3: Content Extraction
├─ Extract page content
├─ Download PDFs
└─ Extract text
    ↓
Phase 4: Rule Extraction
├─ Extract rules using LLM
├─ Categorize rules
└─ Merge from multiple documents
    ↓
Phase 5: Storage
├─ Store in Memory MCP
└─ Index in KG
    ↓
Output: Knowledge onboarding complete
        Releases scanned: 5
        Documents found: 20
        After deduplication: 4
        Rules extracted: 45
```

---

## Implementation Plan

### Phase 1: Keep Domain Create As-Is (0 days)
**Status**: ✅ Already done
- Domain create command is already simple
- No changes needed
- Just add hint to run `dva kg onboard` next

### Phase 2: Create KG Onboarding Command (3-5 days)
**New command**: `dva kg onboard`

**New files**:
- `agentic-cli/src/agentic_cli/commands/kg.py` - KG commands
- `agentic-cli/src/agentic_cli/kg_integration/onboarding.py` - Orchestrator
- `agentic-cli/src/agentic_cli/kg_integration/release_document_collector.py` - Release discovery
- `agentic-cli/src/agentic_cli/kg_integration/document_deduplicator.py` - Version deduplication
- `agentic-cli/src/agentic_cli/kg_integration/version_comparator.py` - Version comparison

**New classes**:
- `KGOnboardingOrchestrator` - Orchestrate onboarding
- `ReleaseDocumentCollector` - Collect documents
- `DocumentDeduplicator` - Deduplicate versions
- `VersionComparator` - Compare versions
- `RuleExtractor` - Extract rules

**Output**: Domain knowledge stored in KG

### Phase 2.5: KG to Memory MCP Sync (1-2 days) [NEW]
**Purpose**: Expose domain knowledge as MCP tools for agents

**New file**: `agentic-cli/src/agentic_cli/kg_integration/kg_to_mcp_sync.py`

**Features**:
- Read rules from KG
- Create entities in Memory MCP
- Create relationships
- Agents can query Memory MCP

**New Memory MCP Tools**:
- `query_domain_rules(domain, category)` - Query rules by category
- `search_rules(keyword)` - Search rules by keyword
- `get_sla(domain)` - Get SLAs for domain
- `get_integration_specs(domain)` - Get integration specs
- `get_security_policies(domain)` - Get security policies
- `get_performance_requirements(domain)` - Get performance requirements

**Output**: Domain knowledge exposed as MCP tools

### Phase 3: Create Async Job System (2-3 days)
**New file**: `agentic-cli/src/agentic_cli/async_jobs/kg_onboarding_job.py`

**Features**:
- Background job execution
- Job status tracking
- Job result storage
- Job scheduling
- Automatic sync to Memory MCP after completion

**New commands**:
- `dva kg onboard --domain cwow-facility --async` - Run in background
- `dva kg status <job-id>` - Check job status
- `dva kg list-jobs` - List all jobs

### Phase 4: Integrate with Code Onboarding (1-2 days)
**Modify**: `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py`

**Features**:
- Query KG for domain knowledge (direct query)
- Include in understanding documents
- Reference in generated skills

**Note**: Code onboarding queries KG directly (not through MCP)

---

## CLI Usage

### Step 1: Create Domain
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
  dva kg onboard --domain cwow-facility --confluence-space CWOV
```

### Step 2a: Onboard Knowledge (Synchronous)
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
```

### Step 2b: Onboard Knowledge (Asynchronous)
```bash
$ dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware --async

Starting async knowledge onboarding for cwow-facility...
✓ Job started: job-20260506-001

Check status: dva kg status job-20260506-001

---

$ dva kg status job-20260506-001

Job Status: job-20260506-001
  Status: running
  Progress: 60% (Phase 3: Content Extraction)
  Started: 2026-05-06 12:52:00
  Estimated completion: 2026-05-06 13:02:00

---

$ dva kg status job-20260506-001

Job Status: job-20260506-001
  Status: completed
  Releases scanned: 5
  Documents found: 20
  After deduplication: 4
  Rules extracted: 45
  Completed: 2026-05-06 13:00:00
```

### Step 3: Use in Code Onboarding
```bash
$ dva code onboard https://github.com/company/facility-service --domain cwow-facility

✓ Code onboarding complete
  Understanding includes business context from KG
  Generated skills reference business rules
```

---

## New Commands

### `dva kg onboard`
```bash
# Basic: Onboard from Confluence space
dva kg onboard --domain cwow-facility --confluence-space CWOV

# Release-aware: Scan all releases, keep latest
dva kg onboard --domain cwow-facility --confluence-space CWOV \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service"

# Async: Run in background
dva kg onboard --domain cwow-facility --confluence-space CWOV --async

# With version strategy
dva kg onboard --domain cwow-facility --confluence-space CWOV \
  --release-aware \
  --version-strategy "latest"  # or "all" or "compare"
```

### `dva kg status`
```bash
# Check job status
dva kg status job-20260506-001

# List all jobs
dva kg list-jobs

# List jobs for a domain
dva kg list-jobs --domain cwow-facility
```

### `dva kg search` (Future)
```bash
# Search rules by domain
dva kg search --domain cwow-facility --category SLA

# Search rules by keyword
dva kg search --keyword "authentication"

# List documents for domain
dva kg list-documents --domain cwow-facility
```

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1 | 0 days | Domain create (already done) |
| 2 | 3-5 days | KG onboarding command |
| 2.5 | 1-2 days | KG to Memory MCP sync (NEW) |
| 3 | 2-3 days | Async job system |
| 4 | 1-2 days | Code onboarding integration |
| **Total** | **7-12 days** | **Complete Track A with MCP** |

---

## Files to Create

```
agentic-cli/src/agentic_cli/
├── commands/kg.py (NEW)
│   ├── onboard command
│   ├── status command
│   └── list-jobs command
├── kg_integration/ (NEW)
│   ├── __init__.py
│   ├── onboarding.py
│   ├── release_document_collector.py
│   ├── document_deduplicator.py
│   ├── version_comparator.py
│   └── kg_to_mcp_sync.py (NEW - Phase 2.5)
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

### For Future
- ✅ Refresh KG without domain changes
- ✅ Schedule periodic KG updates
- ✅ Support multiple knowledge sources
- ✅ Implement KG versioning
- ✅ Add KG search and query interface

---

## Success Criteria

- [ ] Domain create command works (already done)
- [ ] KG onboarding command working
- [ ] Release-aware document collection working
- [ ] Version deduplication working
- [ ] Rule extraction working
- [ ] Async job system working
- [ ] Job status tracking working
- [ ] Code onboarding integration smooth
- [ ] Tests passing

---

## Next Steps

1. **Review** this simplified design
2. **Approve** the separation of concerns approach
3. **Begin Phase 2** - Create KG onboarding command
4. **Follow phases 3-4** in sequence
5. **Daily standups** to track progress

---

## Related Documents

- `docs/plans/TRACK_A_SIMPLIFIED_DESIGN.md` - Detailed simplified design
- `docs/plans/TRACK_A_MCP_INTEGRATION_STRATEGY.md` - MCP integration strategy
- `docs/plans/TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md` - Original design (for reference)
- `docs/plans/TRACK_A_VERSIONED_RELEASE_DOCUMENTS.md` - Release strategy (for reference)

---

**Status**: ✅ FINAL DESIGN - READY FOR IMPLEMENTATION  
**Date Prepared**: May 6, 2026  
**Target Start**: May 7, 2026  
**Target Completion**: May 19, 2026 (7-12 days)

---

## Summary

Track A is now redesigned with **clean separation of concerns** and **dual MCP integration**:

### Three Components

1. **Domain Creation** - Simple, fast, metadata only
   ```bash
   dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
   ```

2. **Knowledge Onboarding** - Separate command, can run async
   ```bash
   dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
   ```

3. **MCP Integration** - Dual approach
   - **Memory MCP**: Agents query during execution
   - **Direct KG Query**: Code onboarding enrichment

### How MCP Fits In

```
KG Onboarding
    ↓
Knowledge Graph (Neo4j + LightRAG)
    ↓
├─ Sync to Memory MCP (agents query)
│  └─ Tools: query_domain_rules(), get_sla(), get_integration_specs()
│
└─ Direct Query (code onboarding)
   └─ Enrich understanding documents
```

### Benefits

- ✅ Simpler to understand
- ✅ Faster to execute
- ✅ Easier to test
- ✅ Better for future enhancements
- ✅ Supports async operations
- ✅ Business knowledge available to agents and code onboarding
- ✅ Single source of truth (KG)
- ✅ Multiple access patterns (MCP + direct query)

**Ready to implement! 🚀**
