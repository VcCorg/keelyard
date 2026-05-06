# Track A Design Index - Complete Documentation

**Status**: ✅ ALL DESIGN DOCUMENTS COMPLETE  
**Date**: May 6, 2026  
**Ready for Implementation**: May 7, 2026

---

## Quick Navigation

### 🚀 Start Here
1. **TRACK_A_IMPLEMENTATION_READY.md** - Complete design summary (THIS IS THE ONE)
2. **TRACK_A_FINAL_DESIGN.md** - Final design with MCP integration
3. **TRACK_A_SIMPLIFIED_DESIGN.md** - Separation of concerns approach

### 📋 Detailed Strategies
- **docs/plans/TRACK_A_MCP_INTEGRATION_STRATEGY.md** - How MCP fits in
- **docs/plans/TRACK_A_SIMPLIFIED_DESIGN.md** - Detailed separation of concerns
- **docs/plans/TRACK_A_VERSIONED_RELEASE_DOCUMENTS.md** - Release strategy (reference)

### 📚 Reference Documents (For Context)
- **docs/plans/TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md** - Original design (reference)
- **docs/plans/TRACK_A_ENHANCEMENT_SUMMARY.md** - Enhancement summary (reference)
- **docs/plans/TRACK_A_INTEGRATION_WITH_TRACKS_B_C.md** - Integration with other tracks (reference)

---

## Document Hierarchy

### Level 1: Implementation Ready (START HERE)
```
TRACK_A_IMPLEMENTATION_READY.md
├─ Executive summary
├─ Three components
├─ Four implementation phases
├─ Complete data flow
├─ CLI workflow
├─ Timeline
└─ Success criteria
```

**Read this first** - It has everything you need to understand and start implementation.

### Level 2: Final Design
```
TRACK_A_FINAL_DESIGN.md
├─ Simplified approach
├─ MCP integration
├─ Implementation plan
├─ CLI usage
├─ Timeline
└─ Files to create/modify
```

**Read this second** - More detailed than Level 1, includes MCP specifics.

### Level 3: Detailed Strategies
```
docs/plans/TRACK_A_SIMPLIFIED_DESIGN.md
├─ Problem with previous design
├─ Solution overview
├─ Domain create (simple)
├─ Knowledge onboarding (separate)
├─ Architecture
└─ Benefits

docs/plans/TRACK_A_MCP_INTEGRATION_STRATEGY.md
├─ Memory MCP approach
├─ Direct KG Query approach
├─ Comparison
├─ Implementation strategy
└─ Data flow
```

**Read these for detailed understanding** - Deep dives into specific aspects.

### Level 4: Reference Documents
```
docs/plans/TRACK_A_VERSIONED_RELEASE_DOCUMENTS.md
├─ Release-aware strategy
├─ Version deduplication
├─ Document collection
└─ Example workflow

docs/plans/TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md
├─ Original design (superseded)
├─ 5-phase approach (superseded)
└─ For reference only
```

**Read these for context** - Historical designs and strategies.

---

## The Final Design at a Glance

### Three Simple Components

#### 1. Domain Creation
```bash
dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
```
- ✅ Register domain metadata
- ✅ Done in < 1 second
- ✅ Already implemented

#### 2. Knowledge Onboarding
```bash
dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
```
- ✅ Scan Confluence space
- ✅ Discover all releases
- ✅ Find domain documents
- ✅ Deduplicate by version
- ✅ Extract rules
- ✅ Store in KG
- ✅ Sync to Memory MCP
- ✅ Can run async

#### 3. MCP Integration
```
Memory MCP (Agents query)
    ↓
Tools: query_domain_rules(), get_sla(), get_integration_specs()

Direct KG Query (Code onboarding)
    ↓
Enrich understanding documents
```

### Four Implementation Phases (7-12 days)

| Phase | Duration | What |
|-------|----------|------|
| 1 | 0 days | Keep domain create as-is |
| 2 | 3-5 days | Create KG onboarding command |
| 2.5 | 1-2 days | KG to Memory MCP sync |
| 3 | 2-3 days | Async job system |
| 4 | 1-2 days | Code onboarding integration |

---

## Key Design Decisions

### 1. Separation of Concerns ✅
- Domain creation: Simple, fast, metadata only
- Knowledge onboarding: Separate command, can run async
- Each component has single responsibility

### 2. Dual MCP Integration ✅
- Memory MCP: For agents (runtime queries)
- Direct KG Query: For code onboarding (analysis time)
- Single source of truth: KG

### 3. Release-Aware Document Collection ✅
- Scan all releases automatically
- Deduplicate by version (keep latest)
- Support version strategies (latest, all, compare)

### 4. Async Support ✅
- KG onboarding can run in background
- Job status tracking
- Automatic sync to Memory MCP after completion

---

## Complete Data Flow

```
Confluence Releases (Release 29, 28, 27, ...)
    ↓
KG Onboarding (dva kg onboard)
    ├─ Discover releases
    ├─ Find domain documents
    ├─ Deduplicate by version
    ├─ Extract content
    ├─ Extract rules
    └─ Store in KG
    ↓
Knowledge Graph (Neo4j + LightRAG)
    ├─ Domain knowledge
    ├─ Business rules
    ├─ SLAs
    ├─ Integration specs
    ├─ Security policies
    └─ Performance requirements
    ↓
    ├─ Sync to Memory MCP
    │  └─ Agents query during execution
    │     └─ Tools: query_domain_rules(), get_sla(), etc.
    │
    └─ Direct Query (Code Onboarding)
       └─ Enrich understanding documents
          └─ Reference in generated skills
```

---

## CLI Workflow

### Step 1: Create Domain (< 1 second)
```bash
dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
✓ Domain registered: cwow-facility
```

### Step 2: Onboard Knowledge (5-10 minutes or async)
```bash
dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
✓ Knowledge onboarding complete
  Releases scanned: 5
  Documents found: 20
  After deduplication: 4
  Rules extracted: 45
```

### Step 3: Code Onboarding (Uses KG)
```bash
dva code onboard https://github.com/company/facility-service --domain cwow-facility
✓ Code onboarding complete
  Understanding includes business context from KG
```

### Step 4: Agent Execution (Queries Memory MCP)
```python
sla = await mcp_client.call_tool(
    "query_domain_rules",
    {"domain": "cwow-facility", "category": "SLA"}
)
# Agent sees: "Response time < 100ms"
```

---

## Files to Create

```
agentic-cli/src/agentic_cli/
├── commands/kg.py (NEW)
├── kg_integration/ (NEW)
│   ├── onboarding.py
│   ├── release_document_collector.py
│   ├── document_deduplicator.py
│   ├── version_comparator.py
│   └── kg_to_mcp_sync.py
└── async_jobs/ (NEW)
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

## Reading Guide by Role

### For Project Manager
1. Read: **TRACK_A_IMPLEMENTATION_READY.md** (Executive Summary section)
2. Timeline: 7-12 days
3. Status: Ready for implementation

### For Tech Lead
1. Read: **TRACK_A_IMPLEMENTATION_READY.md** (Complete)
2. Read: **TRACK_A_FINAL_DESIGN.md** (Complete)
3. Review: Implementation phases and timeline
4. Plan: Resource allocation

### For Engineers (Implementation)
1. Read: **TRACK_A_IMPLEMENTATION_READY.md** (Complete)
2. Read: **TRACK_A_FINAL_DESIGN.md** (Complete)
3. Read: **docs/plans/TRACK_A_SIMPLIFIED_DESIGN.md** (Phase 2 details)
4. Read: **docs/plans/TRACK_A_MCP_INTEGRATION_STRATEGY.md** (Phase 2.5 details)
5. Start: Phase 2 implementation

### For Architects
1. Read: **TRACK_A_IMPLEMENTATION_READY.md** (Complete)
2. Read: **TRACK_A_FINAL_DESIGN.md** (Complete)
3. Read: **docs/plans/TRACK_A_MCP_INTEGRATION_STRATEGY.md** (MCP integration)
4. Review: Data flow and architecture

---

## Key Takeaways

✅ **Simple domain creation** - Just metadata, < 1 second  
✅ **Separate knowledge onboarding** - Can run async, be refreshed, be scheduled  
✅ **Dual MCP integration** - Memory MCP for agents, Direct KG Query for code onboarding  
✅ **Release-aware document collection** - Scan all releases, deduplicate by version  
✅ **Clean separation of concerns** - Each component has single responsibility  
✅ **Production-ready design** - Can begin implementation immediately  

---

## Next Steps

1. **Review** TRACK_A_IMPLEMENTATION_READY.md
2. **Approve** the design
3. **Begin Phase 2** on May 7, 2026
4. **Daily standups** to track progress
5. **Weekly syncs** to verify integration

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**All Design Documents**: Complete  
**Target Start**: May 7, 2026  
**Target Completion**: May 19, 2026 (7-12 days)

---

## Document Summary

| Document | Purpose | Length | Audience |
|----------|---------|--------|----------|
| TRACK_A_IMPLEMENTATION_READY.md | Complete design summary | 3 pages | Everyone |
| TRACK_A_FINAL_DESIGN.md | Final design with MCP | 2 pages | Tech leads |
| TRACK_A_SIMPLIFIED_DESIGN.md | Separation of concerns | 2 pages | Engineers |
| TRACK_A_MCP_INTEGRATION_STRATEGY.md | MCP integration | 2 pages | Architects |
| TRACK_A_VERSIONED_RELEASE_DOCUMENTS.md | Release strategy | 2 pages | Reference |
| TRACK_A_DESIGN_INDEX.md | This document | 1 page | Navigation |

---

**All design documents are committed to git and ready for team review.**

**Let's build Track A! 🚀**
