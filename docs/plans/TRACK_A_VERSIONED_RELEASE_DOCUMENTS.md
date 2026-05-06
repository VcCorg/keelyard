# Track A: Versioned Release Documents Strategy

**Date**: May 6, 2026  
**Status**: Enhanced Design  
**Scope**: Handle domain-specific documents across multiple releases with version management

---

## The Real-World Challenge

Your Confluence structure has:
- Multiple releases (Release 29, Release 28, etc.)
- Each release has domain-specific documents (Facility, Patient, etc.)
- Documents may be duplicated across releases
- Need to pick **latest version** of each document
- Need to collect **all related documents** for a domain

### Example Structure
```
CWOV Space
├── Release 29
│   ├── Facility Domain Spec v2.1
│   ├── Facility Integration Guide v1.5
│   ├── Patient Domain Spec v1.0
│   └── ...
├── Release 28
│   ├── Facility Domain Spec v2.0
│   ├── Facility Integration Guide v1.4
│   ├── Patient Domain Spec v0.9
│   └── ...
└── Release 27
    ├── Facility Domain Spec v1.9
    ├── Facility Integration Guide v1.3
    └── ...
```

### Challenge
When building context for **Facility domain**, we need to:
1. ✅ Find all releases in CWOV space
2. ✅ For each release, find Facility-related documents
3. ✅ Collect all versions of each document type
4. ✅ Pick the **latest version** (by release date or version number)
5. ✅ Deduplicate and merge into single context

---

## Enhanced Design: Release-Aware Document Collection

### New CLI Command
```bash
# Collect all facility documents from all releases
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service"
```

### New Options
```python
--release-aware              # Scan all releases for documents
--domain-keywords "..."      # Keywords to identify domain documents
--include-old-versions       # Include older versions for comparison
--version-strategy "latest"  # Strategy: latest, all, compare
```

---

## Architecture: Release-Aware Document Collector

### Phase 1: Release Discovery
```python
class ReleaseDocumentCollector:
    """Collect domain documents across multiple releases."""
    
    async def discover_releases(
        self,
        confluence_space: str,
    ) -> List[Release]:
        """
        Discover all releases in a Confluence space.
        
        Looks for:
        - Pages with "Release" in title
        - Numbered releases (Release 29, Release 28, etc.)
        - Sorted by release number (descending)
        
        Returns: [Release(number=29, page_id=..., created_date=...), ...]
        """
        pass

@dataclass
class Release:
    number: int              # Release 29 → 29
    page_id: str
    title: str              # "Release 29"
    created_date: datetime
    url: str
```

### Phase 2: Domain Document Identification
```python
async def find_domain_documents(
    self,
    release: Release,
    domain_name: str,
    domain_keywords: List[str],
) -> List[DomainDocument]:
    """
    Find all documents in a release related to a domain.
    
    Strategy:
    1. List all pages in release
    2. Filter by domain keywords (Facility, Facility Domain, etc.)
    3. Extract document metadata
    4. Return list of domain documents
    
    Returns: [DomainDocument(...), ...]
    """
    pass

@dataclass
class DomainDocument:
    release_number: int
    release_date: datetime
    page_id: str
    title: str              # "Facility Domain Spec v2.1"
    document_type: str      # "spec", "guide", "integration", etc.
    version: str            # "2.1"
    url: str
    attachments: List[Attachment]
```

### Phase 3: Version Deduplication
```python
async def deduplicate_documents(
    self,
    documents: List[DomainDocument],
    strategy: str = "latest",
) -> List[DomainDocument]:
    """
    Deduplicate documents across releases, keeping latest version.
    
    Strategy: "latest"
    - Group by document type (spec, guide, integration, etc.)
    - For each group, keep only the latest version
    - Latest = highest version number OR most recent release
    
    Strategy: "all"
    - Keep all versions for comparison
    - Useful for understanding evolution
    
    Strategy: "compare"
    - Keep latest + previous version
    - Useful for understanding changes
    
    Returns: Deduplicated list
    """
    pass

def _extract_document_type(title: str) -> str:
    """
    Extract document type from title.
    
    Examples:
    - "Facility Domain Spec v2.1" → "spec"
    - "Facility Integration Guide v1.5" → "integration"
    - "Facility API Reference v1.0" → "reference"
    - "Facility SLA v3.0" → "sla"
    """
    pass

def _extract_version(title: str) -> str:
    """
    Extract version from title.
    
    Examples:
    - "Facility Domain Spec v2.1" → "2.1"
    - "Facility Integration Guide v1.5" → "1.5"
    """
    pass

def _compare_versions(v1: str, v2: str) -> int:
    """
    Compare two versions.
    
    Returns:
    - -1 if v1 < v2
    - 0 if v1 == v2
    - 1 if v1 > v2
    
    Examples:
    - "2.1" > "2.0" → 1
    - "1.5" > "1.4" → 1
    - "1.0" == "1.0" → 0
    """
    pass
```

### Phase 4: Document Collection & Extraction
```python
async def collect_domain_context(
    self,
    confluence_space: str,
    domain_name: str,
    domain_keywords: List[str],
    release_aware: bool = True,
    version_strategy: str = "latest",
) -> DomainContextCollection:
    """
    Collect all domain documents from all releases.
    
    Flow:
    1. Discover all releases
    2. For each release, find domain documents
    3. Deduplicate by version
    4. Extract content from documents
    5. Extract PDFs and attachments
    6. Return organized collection
    """
    
    # Step 1: Discover releases
    releases = await self.discover_releases(confluence_space)
    
    # Step 2: Find domain documents in each release
    all_documents = []
    for release in releases:
        docs = await self.find_domain_documents(
            release=release,
            domain_name=domain_name,
            domain_keywords=domain_keywords,
        )
        all_documents.extend(docs)
    
    # Step 3: Deduplicate
    deduplicated = await self.deduplicate_documents(
        all_documents,
        strategy=version_strategy,
    )
    
    # Step 4: Extract content
    for doc in deduplicated:
        # Extract page content
        doc.content = await self.confluence.get_page_content(doc.page_id)
        
        # Extract attachments
        doc.attachments = await self.confluence.list_page_attachments(doc.page_id)
        
        # Extract PDF text
        for attachment in doc.attachments:
            pdf_bytes = await self.confluence.download_attachment(attachment.url)
            attachment.text = await self.confluence.extract_pdf_text(pdf_bytes)
    
    return DomainContextCollection(
        domain_name=domain_name,
        confluence_space=confluence_space,
        releases_scanned=len(releases),
        documents_found=len(all_documents),
        documents_after_dedup=len(deduplicated),
        documents=deduplicated,
        collected_at=datetime.now(),
    )

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

## Data Models

### Enhanced DomainDocument
```python
@dataclass
class DomainDocument:
    # Identity
    page_id: str
    title: str
    
    # Version Info
    release_number: int
    release_date: datetime
    version: str              # "2.1"
    document_type: str        # "spec", "guide", "integration", "sla", "reference"
    
    # Content
    content: str              # Page content
    attachments: List[Attachment]
    
    # Metadata
    url: str
    created_date: datetime
    updated_date: datetime
    author: str
    
    # Deduplication Info
    is_latest: bool           # True if this is the latest version
    supersedes: Optional[str] # Version it supersedes
    superseded_by: Optional[str] # Version that supersedes it

@dataclass
class Attachment:
    id: str
    title: str
    url: str
    size_bytes: int
    created: datetime
    text: Optional[str]       # Extracted text from PDF
```

---

## CLI Usage Examples

### Collect Latest Documents Only
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "latest"

# Output:
# ✓ Releases scanned: 5 (Release 29, 28, 27, 26, 25)
# ✓ Documents found: 12
# ✓ After deduplication: 4 (latest versions)
#   - Facility Domain Spec v2.1 (Release 29)
#   - Facility Integration Guide v1.5 (Release 29)
#   - Facility API Reference v2.0 (Release 28)
#   - Facility SLA v3.0 (Release 29)
```

### Collect All Versions for Comparison
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "all" \
  --include-old-versions

# Output:
# ✓ Releases scanned: 5
# ✓ Documents found: 12
# ✓ After deduplication: 12 (all versions kept)
#   - Facility Domain Spec v2.1 (Release 29)
#   - Facility Domain Spec v2.0 (Release 28)
#   - Facility Domain Spec v1.9 (Release 27)
#   - ... (all versions)
```

### Collect Latest + Previous for Change Analysis
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "compare"

# Output:
# ✓ Releases scanned: 5
# ✓ Documents found: 12
# ✓ After deduplication: 8 (latest + previous versions)
#   - Facility Domain Spec v2.1 (Release 29) - LATEST
#   - Facility Domain Spec v2.0 (Release 28) - PREVIOUS
#   - Facility Integration Guide v1.5 (Release 29) - LATEST
#   - Facility Integration Guide v1.4 (Release 28) - PREVIOUS
#   - ... (latest + previous for each document type)
```

---

## Database Schema Updates

### New Table: domain_releases
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

### New Table: domain_documents_versioned
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

### New Table: domain_document_attachments_versioned
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

## Implementation Strategy

### Phase A1: Enhanced Domain Registration (2-3 days)
**Add new CLI options**:
- `--release-aware` - Enable release scanning
- `--domain-keywords` - Keywords to identify domain documents
- `--version-strategy` - "latest", "all", or "compare"
- `--include-old-versions` - Keep older versions

### Phase A2: Release Discovery (2-3 days)
**Implement ReleaseDocumentCollector**:
- Discover releases in Confluence space
- Sort by release number (descending)
- Extract release metadata

### Phase A3: Domain Document Identification (2-3 days)
**Find domain documents in each release**:
- List pages in each release
- Filter by domain keywords
- Extract document type and version
- Build document metadata

### Phase A4: Version Deduplication (2-3 days)
**Implement deduplication logic**:
- Group documents by type
- Compare versions
- Keep latest (or all, or latest+previous)
- Track supersession relationships

### Phase A5: Content Extraction (1-2 days)
**Extract content from deduplicated documents**:
- Get page content
- Download attachments
- Extract PDF text
- Organize by document type

### Phase A6: Rule Extraction & Categorization (2-3 days)
**Extract rules from all collected documents**:
- Extract rules from latest versions
- Categorize (SLA, Integration, Security, Performance)
- Merge rules from multiple documents
- Handle conflicts/duplicates

### Phase A7: Storage & Integration (1-2 days)
**Store in Memory MCP and KG**:
- Store deduplicated documents
- Store version history
- Store rules with source tracking
- Integrate with code onboarding

---

## Example: Facility Domain Collection

### Input
```bash
dva domain create Facility --product CWOW \
  --jira CWOW --bb CGF --confluence CWOV \
  --ingest-business-context \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service"
```

### Process
```
1. Discover releases:
   - Release 29 (2026-05-01)
   - Release 28 (2026-04-01)
   - Release 27 (2026-03-01)
   - Release 26 (2026-02-01)
   - Release 25 (2026-01-01)

2. Find Facility documents in each release:
   Release 29:
   - Facility Domain Spec v2.1
   - Facility Integration Guide v1.5
   - Facility API Reference v2.0
   - Facility SLA v3.0
   
   Release 28:
   - Facility Domain Spec v2.0
   - Facility Integration Guide v1.4
   - Facility API Reference v1.9
   - Facility SLA v2.9
   
   Release 27:
   - Facility Domain Spec v1.9
   - Facility Integration Guide v1.3
   - Facility API Reference v1.8
   - Facility SLA v2.8
   
   (and so on...)

3. Deduplicate (keep latest):
   - Facility Domain Spec v2.1 (Release 29)
   - Facility Integration Guide v1.5 (Release 29)
   - Facility API Reference v2.0 (Release 29)
   - Facility SLA v3.0 (Release 29)

4. Extract content:
   - Extract page content
   - Download attachments
   - Extract PDF text

5. Extract rules:
   - From Facility Domain Spec: Architecture, patterns
   - From Facility Integration Guide: Integration requirements
   - From Facility API Reference: API specifications
   - From Facility SLA: SLAs, performance requirements

6. Store:
   - In Memory MCP as entities
   - In KG for semantic search
   - In database with version history
```

### Output
```
✓ Domain: cwow-facility
✓ Releases scanned: 5
✓ Documents found: 20
✓ After deduplication: 4 (latest versions)
✓ Rules extracted: 45
  - SLA: 8
  - Integration: 12
  - Security: 10
  - Performance: 8
  - Business: 7
✓ Stored in Memory MCP: ✓
✓ Stored in KG: ✓
✓ Ready for code onboarding: ✓
```

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
- ✅ Tracks which version was used for which domain
- ✅ Can audit document usage
- ✅ Can compare versions to understand changes
- ✅ Maintains version history

---

## Version Strategy Comparison

| Strategy | Use Case | Documents Kept |
|----------|----------|-----------------|
| **latest** | Production use | Only latest version of each document |
| **all** | Analysis & comparison | All versions of all documents |
| **compare** | Change analysis | Latest + previous version |

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| A1 | 2-3 days | Enhanced domain registration |
| A2 | 2-3 days | Release discovery |
| A3 | 2-3 days | Domain document identification |
| A4 | 2-3 days | Version deduplication |
| A5 | 1-2 days | Content extraction |
| A6 | 2-3 days | Rule extraction & categorization |
| A7 | 1-2 days | Storage & integration |
| **Total** | **14-20 days** | **Full release-aware context building** |

---

## Files to Create/Modify

### New Files
```
agentic-cli/src/agentic_cli/domain_context/
├── release_document_collector.py (NEW)
├── document_deduplicator.py (NEW)
└── version_comparator.py (NEW)
```

### Modified Files
```
agentic-cli/src/agentic_cli/
├── commands/domain.py (add new options)
├── tracker.py (add new tables)
└── domain_context/business_context_manager.py (integrate collector)
```

---

## Success Criteria

- [ ] Release discovery working
- [ ] Domain document identification accurate
- [ ] Version deduplication correct
- [ ] Content extraction complete
- [ ] Rule extraction from all documents
- [ ] Version strategy working (latest, all, compare)
- [ ] Storage and retrieval working
- [ ] Integration with code onboarding smooth
- [ ] Tests passing with real Confluence data

---

**Document Status**: Ready for Implementation  
**Last Updated**: May 6, 2026  
**Next Step**: Integrate into Phase A1 design
