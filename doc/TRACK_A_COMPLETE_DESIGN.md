# Track A: Complete Design - Domain-Driven Business Context with Release Awareness

**Status**: ✅ COMPLETE & READY FOR IMPLEMENTATION  
**Date**: May 6, 2026  
**Scope**: Full design for extracting versioned business context from Confluence releases

---

## Overview

Track A has been completely designed to handle your real-world scenario:

1. **Domain Registration** - Register domains with Confluence space links
2. **Release-Aware Collection** - Scan all releases for domain documents
3. **Version Management** - Deduplicate and keep latest versions
4. **Content Extraction** - Extract content and PDFs
5. **Rule Extraction** - Extract and categorize business rules
6. **Storage** - Store in Memory MCP and KG
7. **Integration** - Use in code onboarding

---

## The Complete Flow

```
User Command
    ↓
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "latest"
    ↓
Phase 1: Domain Registration Enhancement
├─ Add CLI options
├─ Create ReleaseDocumentCollector
└─ Integrate with domain create
    ↓
Phase 2: Release Discovery & Document Identification
├─ Discover all releases (Release 29, 28, 27, ...)
├─ Find domain documents in each release
├─ Extract document type and version
└─ Build document metadata
    ↓
Phase 3: Version Deduplication & Content Extraction
├─ Group documents by type
├─ Compare versions and keep latest
├─ Extract page content
├─ Download and extract PDFs
└─ Handle attachments
    ↓
Phase 4: Rule Extraction & Categorization
├─ Extract rules from all documents
├─ Categorize (SLA, Integration, Security, Performance)
├─ Merge rules from multiple documents
└─ Handle conflicts and duplicates
    ↓
Phase 5: Memory MCP Storage
├─ Store SLA entities
├─ Store IntegrationSpec entities
├─ Store SecurityPolicy entities
└─ Store PerformanceRequirement entities
    ↓
Phase 6: Code Onboarding Integration
├─ Query business context for domain
├─ Include in understanding documents
└─ Reference in generated skills
    ↓
Phase 7: Query Interface & Reporting
├─ Query rules by domain
├─ Query rules by category
├─ Show version history
└─ Report on document collection
    ↓
Output
├─ Business context stored in Memory MCP ✓
├─ Business context stored in KG ✓
├─ Ready for code onboarding ✓
└─ Version history tracked ✓
```

---

## 7 Implementation Phases

### Phase 1: Domain Registration Enhancement (2-3 days)
**Goal**: Add release-aware options to domain create command

**New CLI Options**:
```bash
--release-aware              # Enable release scanning
--domain-keywords "..."      # Keywords to identify documents
--version-strategy "latest"  # Strategy: latest, all, compare
--include-old-versions       # Keep older versions
```

**New Classes**:
- `ReleaseDocumentCollector` - Orchestrate collection
- `DocumentDeduplicator` - Deduplication logic
- `VersionComparator` - Version comparison

**Files**:
- `domain_context/release_document_collector.py` (NEW)
- `domain_context/document_deduplicator.py` (NEW)
- `domain_context/version_comparator.py` (NEW)
- `commands/domain.py` (MODIFY)

---

### Phase 2: Release Discovery & Document Identification (2-3 days)
**Goal**: Discover releases and find domain documents

**Tasks**:
1. Discover all releases in Confluence space
   - List pages with "Release" in title
   - Sort by release number (descending)
   - Extract release metadata

2. Find domain documents in each release
   - List pages in each release
   - Filter by domain keywords
   - Extract document type and version
   - Build document metadata

**Key Methods**:
```python
async def discover_releases(confluence_space) -> List[Release]
async def find_domain_documents(release, domain_name, keywords) -> List[DomainDocument]
```

---

### Phase 3: Version Deduplication & Content Extraction (2-3 days)
**Goal**: Deduplicate documents and extract content

**Tasks**:
1. Deduplicate documents
   - Group by document type
   - Compare versions
   - Keep latest (or all, or latest+previous)
   - Track supersession relationships

2. Extract content
   - Get page content
   - Download attachments
   - Extract PDF text
   - Organize by document type

**Key Methods**:
```python
async def deduplicate_documents(documents, strategy) -> List[DomainDocument]
async def extract_content(documents) -> List[DomainDocument]
```

---

### Phase 4: Rule Extraction & Categorization (2-3 days)
**Goal**: Extract rules from all collected documents

**Tasks**:
1. Extract rules using LLM
   - Analyze document content
   - Identify business rules
   - Extract SLAs, integration specs, security policies, performance requirements

2. Categorize rules
   - SLA (Response time, Availability, Uptime)
   - Integration (APIs, Endpoints, Protocols)
   - Security (Authentication, Authorization, Encryption)
   - Performance (Latency, Throughput, Capacity)
   - Business (General business rules)
   - Compliance (Regulatory requirements)

3. Merge rules
   - Combine rules from multiple documents
   - Handle conflicts and duplicates
   - Track source document

**Key Methods**:
```python
async def extract_rules(documents) -> List[ExtractedRule]
async def categorize_rule(title, content) -> RuleCategory
```

---

### Phase 5: Memory MCP Storage (1-2 days)
**Goal**: Store rules as queryable entities

**Entity Types**:
- `SLA` - Service level agreements
- `IntegrationSpec` - Integration specifications
- `SecurityPolicy` - Security policies
- `PerformanceRequirement` - Performance requirements
- `BusinessRule` - General business rules

**Tasks**:
1. Store entities in Memory MCP
2. Create relationships
3. Enable semantic search
4. Track source document and version

**Key Methods**:
```python
async def store_in_memory_mcp(rules) -> Dict[str, str]
async def query_rules_by_domain(domain_name) -> List[Rule]
async def query_rules_by_category(category) -> List[Rule]
```

---

### Phase 6: Code Onboarding Integration (1-2 days)
**Goal**: Query and use business context during code analysis

**Tasks**:
1. Query business context during analysis
   - Get SLAs for domain
   - Get integration specs
   - Get security policies
   - Get performance requirements

2. Include in understanding documents
   - Add Business Context section
   - List applicable SLAs
   - List integration requirements
   - List security requirements
   - List performance requirements

3. Reference in generated skills
   - Skills aware of SLAs
   - Skills aware of security requirements
   - Skills include compliance checks
   - Skills reference integration patterns

**Key Methods**:
```python
async def query_business_context(domain_name) -> BusinessContext
def include_in_understanding(analysis, context) -> str
def reference_in_skills(skills, context) -> List[Skill]
```

---

### Phase 7: Query Interface & Reporting (1-2 days)
**Goal**: Provide query interface and reporting

**New Commands**:
```bash
dva domain show-context cwow-facility
dva domain search-rules --domain cwow-facility --category SLA
dva domain search-rules --category Integration
dva domain search-rules --keyword "authentication"
dva domain list-documents --domain cwow-facility
dva domain show-document-versions --domain cwow-facility --type "spec"
```

**Reports**:
- Document collection summary
- Version history
- Rule extraction summary
- Integration status

---

## Data Models

### Release
```python
@dataclass
class Release:
    number: int              # 29, 28, 27, ...
    page_id: str
    title: str              # "Release 29"
    created_date: datetime
    url: str
```

### DomainDocument
```python
@dataclass
class DomainDocument:
    release_number: int
    release_date: datetime
    page_id: str
    title: str              # "Facility Domain Spec v2.1"
    document_type: str      # "spec", "guide", "integration", "sla", "reference"
    version: str            # "2.1"
    content: str
    attachments: List[Attachment]
    url: str
    is_latest: bool
    supersedes: Optional[str]
    superseded_by: Optional[str]
```

### DomainContextCollection
```python
@dataclass
class DomainContextCollection:
    domain_name: str
    confluence_space: str
    releases_scanned: int
    documents_found: int
    documents_after_dedup: int
    documents: List[DomainDocument]
    collected_at: datetime
```

---

## Database Schema

### domain_releases
```sql
CREATE TABLE domain_releases (
    id INTEGER PRIMARY KEY,
    domain_id TEXT NOT NULL,
    confluence_space TEXT,
    release_number INTEGER,
    release_title TEXT,
    release_date TIMESTAMP,
    page_id TEXT,
    url TEXT,
    scanned_at TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

### domain_documents_versioned
```sql
CREATE TABLE domain_documents_versioned (
    id INTEGER PRIMARY KEY,
    domain_context_id INTEGER,
    release_number INTEGER,
    release_date TIMESTAMP,
    page_id TEXT,
    title TEXT,
    document_type TEXT,  -- spec, guide, integration, sla, reference
    version TEXT,        -- "2.1", "1.5", etc.
    content TEXT,
    url TEXT,
    is_latest BOOLEAN,
    supersedes TEXT,
    superseded_by TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (domain_context_id) REFERENCES domain_business_context(id)
);

CREATE INDEX idx_domain_doc_type_version 
ON domain_documents_versioned(domain_context_id, document_type, version);
```

### domain_document_attachments_versioned
```sql
CREATE TABLE domain_document_attachments_versioned (
    id INTEGER PRIMARY KEY,
    domain_document_id INTEGER,
    attachment_id TEXT,
    title TEXT,
    url TEXT,
    size_bytes INTEGER,
    extracted_text TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (domain_document_id) REFERENCES domain_documents_versioned(id)
);
```

---

## CLI Examples

### Basic: Latest Versions Only
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "latest"
```

### Advanced: All Versions
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "all" \
  --include-old-versions
```

### Compare: Latest + Previous
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "compare"
```

### Query Business Context
```bash
dva domain show-context cwow-facility
dva domain search-rules --domain cwow-facility --category SLA
dva domain search-rules --category Integration
dva domain list-documents --domain cwow-facility
```

---

## Files to Create

```
agentic-cli/src/agentic_cli/domain_context/
├── __init__.py
├── business_context_manager.py      # Orchestrate extraction
├── release_document_collector.py    # Release-aware collection
├── document_deduplicator.py         # Version deduplication
├── version_comparator.py            # Version comparison
├── rule_extractor.py                # Rule extraction
└── tests/
    ├── test_domain_context.py
    └── test_release_documents.py
```

---

## Files to Modify

```
agentic-cli/src/agentic_cli/
├── commands/domain.py               # Add new CLI options
├── tracker.py                       # Add database tables
├── analysis/codebase_analyzer.py    # Query business context
└── analysis/understanding_generator.py  # Include in doc

mcp-servers/confluence/src/confluence_mcp/
├── confluence_client.py             # PDF methods
└── server.py                        # MCP tools
```

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1 | 2-3 days | Domain registration enhancement |
| 2 | 2-3 days | Release discovery & document identification |
| 3 | 2-3 days | Version deduplication & content extraction |
| 4 | 2-3 days | Rule extraction & categorization |
| 5 | 1-2 days | Memory MCP storage |
| 6 | 1-2 days | Code onboarding integration |
| 7 | 1-2 days | Query interface & reporting |
| **Total** | **12-18 days** | **Full release-aware business context** |

---

## Success Criteria

- [ ] Release discovery working
- [ ] Domain document identification accurate
- [ ] Version extraction correct
- [ ] Version deduplication correct
- [ ] Content extraction complete
- [ ] Rule extraction from all documents
- [ ] Version strategies working (latest, all, compare)
- [ ] Storage and retrieval working
- [ ] Code onboarding integration smooth
- [ ] Query interface working
- [ ] Tests passing with real Confluence data

---

## Next Steps

1. **Review** this complete design
2. **Approve** the approach
3. **Begin Phase 1** on May 7, 2026
4. **Follow phases 2-7** in sequence
5. **Daily standups** to track progress
6. **Weekly syncs** to verify integration

---

## Related Documents

- `docs/plans/TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md` - Original design
- `docs/plans/TRACK_A_VERSIONED_RELEASE_DOCUMENTS.md` - Detailed strategy
- `docs/plans/TRACK_A_ENHANCEMENT_SUMMARY.md` - Executive summary
- `TRACK_A_DOMAIN_CONTEXT_READY.md` - Ready for implementation
- `TRACK_A_RELEASE_AWARE_SUMMARY.md` - Release-aware summary

---

**Status**: ✅ COMPLETE & READY FOR IMPLEMENTATION  
**Date Prepared**: May 6, 2026  
**Target Start**: May 7, 2026  
**Target Completion**: May 25, 2026 (12-18 days)

---

## Summary

Track A is now completely designed with full support for:

✅ **Domain-driven approach** - Leverage domain registration infrastructure  
✅ **Release awareness** - Scan all releases for documents  
✅ **Version management** - Deduplicate and keep latest versions  
✅ **Content extraction** - Extract pages, PDFs, and attachments  
✅ **Rule extraction** - Extract and categorize business rules  
✅ **Storage** - Store in Memory MCP and KG  
✅ **Integration** - Use in code onboarding  
✅ **Query interface** - Query rules and documents  

This handles your real-world scenario where:
- Multiple releases (Release 29, 28, 27, etc.)
- Each release has domain documents
- Documents duplicated across releases
- Need to pick **latest version** of each document

**Ready to implement! 🚀**
