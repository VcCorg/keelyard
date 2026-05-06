# Track A: Release-Aware Business Context - Complete Design

**Status**: ✅ Enhanced Design Complete  
**Date**: May 6, 2026  
**Enhancement**: Handle versioned documents across multiple releases

---

## The Real-World Scenario

Your Confluence structure (CWOV space) has:
- Multiple releases: Release 29, Release 28, Release 27, etc.
- Each release contains domain-specific documents
- Documents may be duplicated across releases with different versions
- Need to collect **all related documents** for a domain
- Need to pick **latest version** of each document type

### Example: Facility Domain
```
CWOV Space
├── Release 29 (Latest)
│   ├── Facility Domain Spec v2.1 ← LATEST
│   ├── Facility Integration Guide v1.5 ← LATEST
│   ├── Facility API Reference v2.0 ← LATEST
│   └── Facility SLA v3.0 ← LATEST
├── Release 28
│   ├── Facility Domain Spec v2.0
│   ├── Facility Integration Guide v1.4
│   ├── Facility API Reference v1.9
│   └── Facility SLA v2.9
├── Release 27
│   ├── Facility Domain Spec v1.9
│   ├── Facility Integration Guide v1.3
│   ├── Facility API Reference v1.8
│   └── Facility SLA v2.8
└── (older releases...)
```

---

## The Solution: Release-Aware Document Collector

### How It Works

```
1. Discover Releases
   └─ Find all releases in CWOV space
      └─ Release 29, 28, 27, 26, 25, ...

2. Find Domain Documents
   └─ For each release, find documents matching domain keywords
      └─ "Facility", "Facility Domain", "Facility Service"

3. Extract Metadata
   └─ For each document:
      ├─ Extract document type (spec, guide, integration, sla, reference)
      ├─ Extract version (2.1, 1.5, 2.0, etc.)
      ├─ Extract release number
      └─ Extract release date

4. Deduplicate by Version
   └─ Group documents by type
      └─ For each group, keep only LATEST version
         └─ Latest = highest version number OR most recent release

5. Extract Content
   └─ For deduplicated documents:
      ├─ Extract page content
      ├─ Download attachments
      └─ Extract PDF text

6. Extract Rules
   └─ From all collected documents:
      ├─ Extract business rules
      ├─ Categorize (SLA, Integration, Security, Performance)
      └─ Merge rules from multiple documents

7. Store & Integrate
   └─ Store in Memory MCP and KG
      └─ Ready for code onboarding
```

---

## CLI Usage

### Basic: Scan All Releases, Keep Latest Versions
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "latest"
```

**Output**:
```
✓ Releases scanned: 5 (Release 29, 28, 27, 26, 25)
✓ Documents found: 20
✓ After deduplication: 4 (latest versions only)
  - Facility Domain Spec v2.1 (Release 29)
  - Facility Integration Guide v1.5 (Release 29)
  - Facility API Reference v2.0 (Release 29)
  - Facility SLA v3.0 (Release 29)
✓ Rules extracted: 45
  - SLA: 8
  - Integration: 12
  - Security: 10
  - Performance: 8
  - Business: 7
✓ Stored in Memory MCP: ✓
✓ Stored in KG: ✓
```

### Advanced: Keep All Versions for Analysis
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "all" \
  --include-old-versions
```

**Output**:
```
✓ Releases scanned: 5
✓ Documents found: 20
✓ After deduplication: 20 (all versions kept)
  - Facility Domain Spec v2.1 (Release 29)
  - Facility Domain Spec v2.0 (Release 28)
  - Facility Domain Spec v1.9 (Release 27)
  - ... (all versions)
```

### Compare: Latest + Previous Version
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "compare"
```

**Output**:
```
✓ Releases scanned: 5
✓ Documents found: 20
✓ After deduplication: 8 (latest + previous)
  - Facility Domain Spec v2.1 (Release 29) - LATEST
  - Facility Domain Spec v2.0 (Release 28) - PREVIOUS
  - Facility Integration Guide v1.5 (Release 29) - LATEST
  - Facility Integration Guide v1.4 (Release 28) - PREVIOUS
  - ... (latest + previous for each type)
```

---

## 7 Implementation Phases

### Phase 1: Domain Registration Enhancement (2-3 days)
**Add release-aware options to domain create command**
- `--release-aware` - Enable release scanning
- `--domain-keywords` - Keywords to identify documents
- `--version-strategy` - "latest", "all", or "compare"
- `--include-old-versions` - Keep older versions

### Phase 2: Release Discovery & Document Identification (2-3 days)
**Discover releases and find domain documents**
- List all releases in Confluence space
- Sort by release number (descending)
- For each release, find documents matching domain keywords
- Extract document metadata (type, version, date)

### Phase 3: Version Deduplication & Content Extraction (2-3 days)
**Deduplicate documents and extract content**
- Group documents by type
- Compare versions and keep latest
- Extract page content
- Download and extract PDFs
- Handle attachments

### Phase 4: Rule Extraction & Categorization (2-3 days)
**Extract rules from all collected documents**
- Extract business rules using LLM
- Categorize (SLA, Integration, Security, Performance)
- Merge rules from multiple documents
- Handle conflicts and duplicates

### Phase 5: Memory MCP Storage (1-2 days)
**Store rules as queryable entities**
- Store SLA entities
- Store IntegrationSpec entities
- Store SecurityPolicy entities
- Store PerformanceRequirement entities

### Phase 6: Code Onboarding Integration (1-2 days)
**Query and use business context during analysis**
- Query business context for domain
- Include in understanding documents
- Reference in generated skills

### Phase 7: Query Interface & Reporting (1-2 days)
**Provide query interface and reporting**
- Query rules by domain
- Query rules by category
- Show version history
- Report on document collection

---

## Key Classes

### ReleaseDocumentCollector
```python
class ReleaseDocumentCollector:
    async def discover_releases(confluence_space) -> List[Release]
    async def find_domain_documents(release, domain_name, keywords) -> List[DomainDocument]
    async def collect_domain_context(...) -> DomainContextCollection
```

### DocumentDeduplicator
```python
class DocumentDeduplicator:
    async def deduplicate_documents(documents, strategy) -> List[DomainDocument]
    def _extract_document_type(title) -> str
    def _extract_version(title) -> str
    def _compare_versions(v1, v2) -> int
```

### VersionComparator
```python
class VersionComparator:
    def compare(v1: str, v2: str) -> int
    def is_newer(v1: str, v2: str) -> bool
    def parse_version(version: str) -> Tuple[int, int, int]
```

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
    domain_id TEXT,
    confluence_space TEXT,
    release_number INTEGER,
    release_title TEXT,
    release_date TIMESTAMP,
    page_id TEXT,
    url TEXT,
    scanned_at TIMESTAMP,
    created_at TIMESTAMP
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
    created_at TIMESTAMP
);

CREATE INDEX idx_domain_doc_type_version 
ON domain_documents_versioned(domain_context_id, document_type, version);
```

---

## Version Strategies

| Strategy | Use Case | Documents Kept | Example |
|----------|----------|-----------------|---------|
| **latest** | Production use | Only latest version of each document | v2.1, v1.5, v2.0, v3.0 |
| **all** | Analysis & comparison | All versions of all documents | v2.1, v2.0, v1.9, v1.5, v1.4, v1.3 |
| **compare** | Change analysis | Latest + previous version | v2.1+v2.0, v1.5+v1.4, v2.0+v1.9, v3.0+v2.9 |

---

## Benefits

### For Domain Owners
- ✅ Automatically collects all domain documents across releases
- ✅ Picks latest version automatically
- ✅ No manual version management
- ✅ Can compare versions if needed

### For Code Onboarding
- ✅ Uses latest documents for analysis
- ✅ Includes version history for context
- ✅ Better understanding of domain evolution
- ✅ Can reference previous versions if needed

### For Governance
- ✅ Tracks which version was used
- ✅ Can audit document usage
- ✅ Can compare versions to understand changes
- ✅ Maintains version history

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

## Files to Create

```
agentic-cli/src/agentic_cli/domain_context/
├── release_document_collector.py    # Release discovery & document collection
├── document_deduplicator.py         # Version deduplication logic
├── version_comparator.py            # Version comparison utilities
└── tests/
    └── test_release_documents.py
```

---

## Files to Modify

```
agentic-cli/src/agentic_cli/
├── commands/domain.py               # Add new CLI options
├── tracker.py                       # Add database tables
└── domain_context/business_context_manager.py  # Integrate collector
```

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
- [ ] Integration with code onboarding smooth
- [ ] Tests passing with real Confluence data

---

## Next Steps

1. **Review** this design with the team
2. **Approve** the release-aware approach
3. **Begin Phase 1** - Domain registration enhancement
4. **Follow phases 2-7** in sequence
5. **Test** with real CWOV space and releases

---

## Related Documents

- `docs/plans/TRACK_A_DOMAIN_CONTEXT_INTEGRATION.md` - Original design
- `docs/plans/TRACK_A_VERSIONED_RELEASE_DOCUMENTS.md` - Detailed strategy
- `docs/plans/TRACK_A_ENHANCEMENT_SUMMARY.md` - Executive summary
- `TRACK_A_DOMAIN_CONTEXT_READY.md` - Ready for implementation

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**Date Prepared**: May 6, 2026  
**Target Start**: May 7, 2026  
**Target Completion**: May 25, 2026 (12-18 days)

---

## Summary

Track A has been enhanced to handle the real-world scenario of versioned documents across multiple releases. The release-aware document collector will:

1. **Discover** all releases in your Confluence space
2. **Find** all domain-related documents across releases
3. **Deduplicate** by version (keeping latest)
4. **Extract** content from all documents
5. **Extract** rules from deduplicated documents
6. **Store** in Memory MCP and KG
7. **Integrate** with code onboarding

This handles your specific use case where:
- Multiple releases (Release 29, 28, 27, etc.)
- Each release has domain documents
- Documents may be duplicated across releases
- Need to pick **latest version** of each document

**Ready to build! 🚀**
