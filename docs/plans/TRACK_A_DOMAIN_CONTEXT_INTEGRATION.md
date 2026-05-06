# Track A: Domain-Driven Business Context Integration

**Date**: May 6, 2026  
**Status**: Enhanced Design  
**Scope**: Integrate MCP business context with domain registration system

---

## Overview

Enhance Track A to leverage the existing `domain register` command infrastructure. When a domain is registered with Confluence space links, automatically extract and internalize business context from those spaces into the Memory MCP.

### Current Domain Registration
```bash
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT"
```

### Enhanced with Business Context
```bash
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT" \
  --ingest-business-context  # NEW: Auto-extract and store business rules
```

---

## Architecture

### Current Flow
```
domain register
├─ Store domain metadata (Jira, Bitbucket, Confluence)
└─ Link repos to domain
```

### Enhanced Flow
```
domain register
├─ Store domain metadata (Jira, Bitbucket, Confluence)
├─ [NEW] Extract business context from Confluence
│  ├─ List pages in Confluence space
│  ├─ Find PDFs and documentation
│  ├─ Extract business rules, SLAs, integration specs
│  └─ Store in Memory MCP
├─ Link repos to domain
└─ [NEW] Query business context during code onboarding
```

---

## Implementation Plan

### Phase A1: Extend Domain Registration (2-3 days)

#### 1.1 Add Business Context Options to Domain Create
```python
# In commands/domain.py

@domain_app.command()
def create(
    domain: str,
    product: str,
    # ... existing options ...
    confluence_space: str = None,
    confluence_url: str = None,
    
    # NEW OPTIONS
    ingest_business_context: bool = typer.Option(
        False,
        "--ingest-business-context",
        help="Auto-extract and store business context from Confluence"
    ),
    business_context_pages: str = typer.Option(
        None,
        "--context-pages",
        help="Comma-separated Confluence page titles to extract (e.g., 'Business Rules,SLA,Integration Specs')"
    ),
    auto_categorize: bool = typer.Option(
        True,
        "--auto-categorize",
        help="Auto-categorize extracted rules (SLA, Integration, Security, Performance)"
    ),
) -> None:
    """
    Register a new domain under a product.
    
    Optionally extract business context from Confluence space and store
    in Memory MCP for use during code onboarding.
    
    Examples:
        # Basic domain registration
        dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT
        
        # With business context extraction
        dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT \
          --ingest-business-context --context-pages "Business Rules,SLA,Integration Specs"
        
        # Auto-extract all documentation pages
        dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT \
          --ingest-business-context
    """
```

#### 1.2 Create Domain Business Context Manager
```python
# NEW FILE: agentic_cli/domain_context/business_context_manager.py

from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

@dataclass
class BusinessContext:
    domain_id: str
    domain_name: str
    confluence_space: str
    confluence_url: str
    extracted_at: datetime
    
    # Extracted content
    business_rules: List[Dict]  # [{"title": "...", "content": "...", "category": "SLA"}]
    integration_specs: List[Dict]
    slas: List[Dict]
    security_policies: List[Dict]
    performance_requirements: List[Dict]
    
    # Metadata
    pages_extracted: int
    pdfs_extracted: int
    total_rules: int
    
class DomainBusinessContextManager:
    """Manage business context extraction and storage for domains."""
    
    def __init__(self, confluence_client, memory_client, kg_client):
        self.confluence = confluence_client
        self.memory = memory_client
        self.kg = kg_client
    
    async def extract_from_confluence(
        self,
        domain_name: str,
        confluence_space: str,
        confluence_url: str,
        page_titles: Optional[List[str]] = None,
        auto_categorize: bool = True,
    ) -> BusinessContext:
        """
        Extract business context from Confluence space.
        
        Steps:
        1. List all pages in space
        2. Filter by page titles (if provided)
        3. Extract PDFs from pages
        4. Extract text from PDFs
        5. Categorize rules (SLA, Integration, Security, Performance)
        6. Return structured context
        """
        pass
    
    async def store_in_memory_mcp(
        self,
        context: BusinessContext,
    ) -> Dict[str, str]:
        """
        Store extracted business context in Memory MCP.
        
        Creates entities:
        - BusinessRule (title, content, category, domain)
        - IntegrationSpec (name, spec, domain)
        - SLA (name, requirement, domain)
        - SecurityPolicy (name, policy, domain)
        - PerformanceRequirement (name, requirement, domain)
        
        Returns: {entity_type: entity_id}
        """
        pass
    
    async def store_in_kg(
        self,
        context: BusinessContext,
    ) -> None:
        """
        Store business context in KG for semantic queries.
        
        Creates KG entities:
        - Domain node
        - BusinessRule nodes
        - Relationships: domain -> has_rule, rule -> category
        """
        pass
    
    async def query_by_domain(
        self,
        domain_name: str,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """Query business rules for a domain."""
        pass
    
    async def query_by_category(
        self,
        category: str,  # SLA, Integration, Security, Performance
    ) -> List[Dict]:
        """Query rules by category across all domains."""
        pass
```

#### 1.3 Integrate with Domain Create Command
```python
# In commands/domain.py - enhance create() function

async def create(...):
    # ... existing domain registration code ...
    
    # NEW: Extract business context if requested
    if ingest_business_context and confluence_space and confluence_url:
        console.print("\n[cyan]Extracting business context from Confluence...[/cyan]")
        
        context_manager = DomainBusinessContextManager(
            confluence_client=get_confluence_client(),
            memory_client=get_memory_client(),
            kg_client=get_kg_client(),
        )
        
        # Parse page titles
        pages = [p.strip() for p in business_context_pages.split(",")] if business_context_pages else None
        
        # Extract context
        context = await context_manager.extract_from_confluence(
            domain_name=name,
            confluence_space=confluence_space,
            confluence_url=confluence_url,
            page_titles=pages,
            auto_categorize=auto_categorize,
        )
        
        # Store in Memory MCP
        console.print(f"[cyan]Storing {context.total_rules} rules in Memory MCP...[/cyan]")
        await context_manager.store_in_memory_mcp(context)
        
        # Store in KG
        console.print("[cyan]Indexing in Knowledge Graph...[/cyan]")
        await context_manager.store_in_kg(context)
        
        # Show summary
        console.print(Panel(
            f"[green]✓ Business context extracted and stored[/green]\n"
            f"Pages: {context.pages_extracted}\n"
            f"PDFs: {context.pdfs_extracted}\n"
            f"Rules: {context.total_rules}",
            title="Business Context"
        ))
```

### Phase A2: Confluence PDF Extraction (2-3 days)

#### 2.1 Extend Confluence MCP
```python
# In mcp-servers/confluence/src/confluence_mcp/confluence_client.py

class ConfluenceClient:
    
    def list_page_attachments(
        self,
        page_id: str,
        file_type: str = "pdf"
    ) -> List[Dict]:
        """List attachments on a Confluence page."""
        url = f"{self.config.server_url}/rest/api/content/{page_id}/child/attachment"
        params = {"limit": 100, "expand": "details"}
        response = self._request("GET", url, params=params)
        
        attachments = []
        for item in response.get("results", []):
            if file_type and not item["title"].endswith(f".{file_type}"):
                continue
            attachments.append({
                "id": item["id"],
                "title": item["title"],
                "url": item["_links"]["download"],
                "size_bytes": item["extensions"].get("fileSize", 0),
                "created": item["metadata"]["created"],
            })
        return attachments
    
    def download_attachment(self, attachment_url: str) -> bytes:
        """Download attachment content (PDF, etc.)."""
        # Construct full URL if relative
        if attachment_url.startswith("/"):
            attachment_url = f"{self.config.server_url}{attachment_url}"
        
        response = self._request("GET", attachment_url, raw=True)
        return response.content
    
    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        import PyPDF2
        from io import BytesIO
        
        pdf_file = BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    
    def list_space_pages(
        self,
        space_key: str,
        limit: int = 100,
    ) -> List[Dict]:
        """List all pages in a Confluence space."""
        url = f"{self.config.server_url}/rest/api/content"
        params = {
            "spaceKey": space_key,
            "type": "page",
            "limit": limit,
            "expand": "body.storage,metadata.labels"
        }
        response = self._request("GET", url, params=params)
        
        pages = []
        for item in response.get("results", []):
            pages.append({
                "id": item["id"],
                "title": item["title"],
                "url": item["_links"]["webui"],
                "created": item["metadata"]["created"],
                "labels": [l["name"] for l in item.get("metadata", {}).get("labels", {}).get("results", [])],
            })
        return pages
```

#### 2.2 Add MCP Tools
```python
# In mcp-servers/confluence/src/confluence_mcp/server.py

@server.call_tool
async def handle_call_tool(name: str, arguments: dict) -> Any:
    # ... existing tools ...
    
    if name == "confluence_list_space_pages":
        space_key = arguments.get("space_key")
        pages = client.list_space_pages(space_key)
        return json.dumps(pages)
    
    elif name == "confluence_list_attachments":
        page_id = arguments.get("page_id")
        attachments = client.list_page_attachments(page_id)
        return json.dumps(attachments)
    
    elif name == "confluence_download_attachment":
        attachment_url = arguments.get("attachment_url")
        pdf_bytes = client.download_attachment(attachment_url)
        return base64.b64encode(pdf_bytes).decode()
    
    elif name == "confluence_extract_pdf_text":
        pdf_base64 = arguments.get("pdf_base64")
        pdf_bytes = base64.b64decode(pdf_base64)
        text = client.extract_pdf_text(pdf_bytes)
        return text
```

### Phase A3: Business Rule Extraction & Categorization (2-3 days)

#### 3.1 Create Rule Extractor
```python
# NEW FILE: agentic_cli/domain_context/rule_extractor.py

from enum import Enum
from typing import List, Dict
from dataclasses import dataclass

class RuleCategory(Enum):
    SLA = "SLA"
    INTEGRATION = "Integration"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    BUSINESS = "Business"
    COMPLIANCE = "Compliance"
    OTHER = "Other"

@dataclass
class ExtractedRule:
    title: str
    content: str
    category: RuleCategory
    source_page: str
    confidence: float  # 0-1, how confident we are about categorization

class RuleExtractor:
    """Extract and categorize business rules from text."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def extract_rules(
        self,
        text: str,
        source_page: str,
        auto_categorize: bool = True,
    ) -> List[ExtractedRule]:
        """
        Extract rules from text using LLM.
        
        Prompt: "Extract business rules, SLAs, integration specs, security policies,
        and performance requirements from the following text. For each rule, provide:
        1. Title (short name)
        2. Content (full rule text)
        3. Category (SLA, Integration, Security, Performance, Business, Compliance)
        4. Confidence (0-1)"
        """
        pass
    
    async def categorize_rule(
        self,
        title: str,
        content: str,
    ) -> RuleCategory:
        """Categorize a single rule using LLM."""
        pass
    
    def extract_rules_regex(
        self,
        text: str,
        source_page: str,
    ) -> List[ExtractedRule]:
        """
        Extract rules using regex patterns.
        
        Patterns:
        - SLA: "SLA:", "Response time:", "Availability:", "Uptime:"
        - Integration: "Integration:", "API:", "Endpoint:", "Protocol:"
        - Security: "Security:", "Authentication:", "Authorization:", "Encryption:"
        - Performance: "Performance:", "Latency:", "Throughput:", "Capacity:"
        """
        pass
```

#### 3.2 Integrate Rule Extraction
```python
# In domain_context_manager.py

async def extract_from_confluence(...) -> BusinessContext:
    # 1. List pages in space
    pages = self.confluence.list_space_pages(confluence_space)
    
    # 2. Filter by titles if provided
    if page_titles:
        pages = [p for p in pages if p["title"] in page_titles]
    
    # 3. Extract content from each page
    business_rules = []
    integration_specs = []
    slas = []
    security_policies = []
    performance_requirements = []
    
    rule_extractor = RuleExtractor(self.llm)
    
    for page in pages:
        # Get page content
        page_content = self.confluence.get_page_content(page["id"])
        
        # Extract attachments (PDFs)
        attachments = self.confluence.list_page_attachments(page["id"])
        
        for attachment in attachments:
            # Download and extract PDF
            pdf_bytes = self.confluence.download_attachment(attachment["url"])
            pdf_text = self.confluence.extract_pdf_text(pdf_bytes)
            
            # Extract rules from PDF
            rules = await rule_extractor.extract_rules(
                text=pdf_text,
                source_page=page["title"],
                auto_categorize=auto_categorize,
            )
            
            # Categorize and store
            for rule in rules:
                if rule.category == RuleCategory.SLA:
                    slas.append(rule)
                elif rule.category == RuleCategory.INTEGRATION:
                    integration_specs.append(rule)
                elif rule.category == RuleCategory.SECURITY:
                    security_policies.append(rule)
                elif rule.category == RuleCategory.PERFORMANCE:
                    performance_requirements.append(rule)
                else:
                    business_rules.append(rule)
    
    return BusinessContext(
        domain_id=domain_name,
        domain_name=domain_name,
        confluence_space=confluence_space,
        confluence_url=confluence_url,
        extracted_at=datetime.now(),
        business_rules=business_rules,
        integration_specs=integration_specs,
        slas=slas,
        security_policies=security_policies,
        performance_requirements=performance_requirements,
        pages_extracted=len(pages),
        pdfs_extracted=sum(len(self.confluence.list_page_attachments(p["id"])) for p in pages),
        total_rules=sum([
            len(business_rules), len(integration_specs), len(slas),
            len(security_policies), len(performance_requirements)
        ]),
    )
```

### Phase A4: Memory MCP Storage (1-2 days)

#### 4.1 Store in Memory MCP
```python
# In domain_context_manager.py

async def store_in_memory_mcp(self, context: BusinessContext) -> Dict[str, str]:
    """Store extracted business context in Memory MCP."""
    
    entity_ids = {}
    
    # Store SLAs
    for sla in context.slas:
        entity_id = await self.memory.store_entity(
            entity_type="SLA",
            name=sla.title,
            properties={
                "content": sla.content,
                "domain": context.domain_name,
                "source_page": sla.source_page,
                "confidence": sla.confidence,
            }
        )
        entity_ids[f"sla_{sla.title}"] = entity_id
    
    # Store Integration Specs
    for spec in context.integration_specs:
        entity_id = await self.memory.store_entity(
            entity_type="IntegrationSpec",
            name=spec.title,
            properties={
                "content": spec.content,
                "domain": context.domain_name,
                "source_page": spec.source_page,
                "confidence": spec.confidence,
            }
        )
        entity_ids[f"integration_{spec.title}"] = entity_id
    
    # Store Security Policies
    for policy in context.security_policies:
        entity_id = await self.memory.store_entity(
            entity_type="SecurityPolicy",
            name=policy.title,
            properties={
                "content": policy.content,
                "domain": context.domain_name,
                "source_page": policy.source_page,
                "confidence": policy.confidence,
            }
        )
        entity_ids[f"security_{policy.title}"] = entity_id
    
    # Store Performance Requirements
    for req in context.performance_requirements:
        entity_id = await self.memory.store_entity(
            entity_type="PerformanceRequirement",
            name=req.title,
            properties={
                "content": req.content,
                "domain": context.domain_name,
                "source_page": req.source_page,
                "confidence": req.confidence,
            }
        )
        entity_ids[f"performance_{req.title}"] = entity_id
    
    return entity_ids
```

### Phase A5: Integration with Code Onboarding (1-2 days)

#### 5.1 Query Business Context During Onboarding
```python
# In analysis/codebase_analyzer.py

class CodebaseAnalyzer:
    def __init__(self, domain_name: str, memory_client):
        self.domain_name = domain_name
        self.memory = memory_client
    
    async def analyze(self, repo_path: str) -> AnalysisResult:
        # ... existing analysis code ...
        
        # NEW: Query business context for this domain
        business_context = await self._get_business_context()
        
        # Include in analysis
        analysis_result.business_context = business_context
        analysis_result.applicable_slas = business_context.get("slas", [])
        analysis_result.integration_requirements = business_context.get("integrations", [])
        analysis_result.security_requirements = business_context.get("security", [])
        analysis_result.performance_requirements = business_context.get("performance", [])
        
        return analysis_result
    
    async def _get_business_context(self) -> Dict:
        """Query Memory MCP for business context."""
        return await self.memory.query_by_domain(self.domain_name)
```

#### 5.2 Include in Understanding Document
```python
# In analysis/understanding_generator.py

def generate(analysis: AnalysisResult) -> str:
    doc = f"""
    # {analysis.repository.name} - Codebase Understanding
    
    ## Business Context
    
    ### SLAs
    {self._format_slas(analysis.applicable_slas)}
    
    ### Integration Requirements
    {self._format_integrations(analysis.integration_requirements)}
    
    ### Security Requirements
    {self._format_security(analysis.security_requirements)}
    
    ### Performance Requirements
    {self._format_performance(analysis.performance_requirements)}
    
    ## Architecture
    ...
    """
    return doc
```

---

## Database Schema Updates

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

## CLI Usage Examples

### Basic Domain Registration
```bash
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence MTT \
  --confluence-url "https://confluence.company.com/spaces/MTT"
```

### With Business Context Extraction
```bash
# Extract all documentation
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
```

---

## Success Criteria

### Phase A1: Domain Registration Enhancement
- [ ] New CLI options added
- [ ] DomainBusinessContextManager created
- [ ] Integration with domain create command
- [ ] Tests passing

### Phase A2: Confluence PDF Extraction
- [ ] PDF extraction working
- [ ] MCP tools added
- [ ] Tests with real PDFs
- [ ] Error handling for corrupted PDFs

### Phase A3: Rule Extraction & Categorization
- [ ] Rule extractor working
- [ ] LLM-based categorization accurate
- [ ] Regex fallback working
- [ ] Tests with real documents

### Phase A4: Memory MCP Storage
- [ ] Entities stored correctly
- [ ] Queries working
- [ ] Relationships established
- [ ] Tests passing

### Phase A5: Code Onboarding Integration
- [ ] Business context queried during analysis
- [ ] Included in understanding document
- [ ] Skills reference business rules
- [ ] End-to-end test passing

---

## Benefits

### For Domain Owners
- ✅ Business context automatically extracted when domain registered
- ✅ No manual data entry
- ✅ Rules always up-to-date with Confluence

### For Code Onboarding
- ✅ Codebase understanding includes business context
- ✅ Generated skills aware of business constraints
- ✅ SLAs and security requirements documented

### For Agents
- ✅ Agents know business rules before coding
- ✅ Can query business context during execution
- ✅ Better compliance and governance

---

## Timeline

- **Phase A1**: 2-3 days (Domain registration enhancement)
- **Phase A2**: 2-3 days (Confluence PDF extraction)
- **Phase A3**: 2-3 days (Rule extraction & categorization)
- **Phase A4**: 1-2 days (Memory MCP storage)
- **Phase A5**: 1-2 days (Code onboarding integration)

**Total**: 8-13 days (slightly longer than original estimate due to added value)

---

## Files to Create/Modify

### New Files
- `agentic-cli/src/agentic_cli/domain_context/__init__.py`
- `agentic-cli/src/agentic_cli/domain_context/business_context_manager.py`
- `agentic-cli/src/agentic_cli/domain_context/rule_extractor.py`
- `agentic-cli/tests/test_domain_context.py`

### Modified Files
- `agentic-cli/src/agentic_cli/commands/domain.py` (add new options and integration)
- `agentic-cli/src/agentic_cli/tracker.py` (add domain_business_context tables)
- `mcp-servers/confluence/src/confluence_mcp/confluence_client.py` (add PDF methods)
- `mcp-servers/confluence/src/confluence_mcp/server.py` (add MCP tools)
- `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py` (query business context)
- `agentic-cli/src/agentic_cli/analysis/understanding_generator.py` (include in doc)

---

**Document Status**: Ready for Implementation  
**Last Updated**: May 6, 2026  
**Next Step**: Begin Phase A1 implementation
