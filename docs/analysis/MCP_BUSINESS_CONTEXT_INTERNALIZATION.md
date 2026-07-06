# MCP-Driven Business Context Internalization

## Architecture Overview

Use MCP services to **automatically extract PDFs from Confluence and internalize as queryable business context**:

```
Confluence Pages (with PDF attachments)
    ↓
[Confluence MCP] - Find pages in space
    ↓
[PDF Extraction] - Download + parse PDFs from attachments
    ↓
[Memory MCP] - Store as entities + facts + preferences
    ↓
[Code Onboarding] - Query Memory MCP for business context
    ↓
[LightRAG] - Combine code context + business knowledge
    ↓
✅ Unified codebase understanding with business rules
```

## The Three-MCP System

You have three MCP services that can work together:

```
┌─────────────────────┐
│  Confluence MCP     │  port 8129
│  ───────────────    │
│ • search pages      │
│ • get page content  │
│ • list spaces       │  [EXTEND] Add PDF attachment tools
└────────┬────────────┘
         │
         ├─→ Find documentation pages
         │   (e.g., "Business Rules", "SLA", "Integration Specs")
         │
         ↓
┌─────────────────────┐
│  Memory MCP         │  port 8130
│  ───────────────    │
│ • store entities    │
│ • store facts       │
│ • store preferences │  [USE] Persist business context
│ • semantic search   │
└────────┬────────────┘
         │
         ├─→ Store extracted rules as entities
         │   (e.g., BusinessRule, IntegrationSpec, SLA)
         │
         ↓
┌─────────────────────┐
│  KG MCP             │  port 8131
│  ───────────────    │
│ • query graph       │
│ • get context       │
│ • search entities   │  [USE] Link business + code
└─────────────────────┘
         │
         └─→ Query for context during onboarding
```

## Implementation Strategy

### Phase 1: Add PDF Attachment Support to Confluence MCP

**Extend** `confluence/src/confluence_mcp/confluence_client.py` with:

```python
def list_page_attachments(
    self,
    page_id: str,
    file_type: str = "pdf"  # Filter by extension
) → List[Dict]:
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


def download_attachment(
    self,
    attachment_url: str
) → bytes:
    """Download attachment content (PDF, etc.)."""
    # Construct full URL if relative
    if attachment_url.startswith("/"):
        url = self.config.server_url + attachment_url
    else:
        url = attachment_url
    
    response = self._request("GET", url)
    return response.content  # Raw bytes
```

**Then expose via new MCP tools:**

```python
@mcp.tool()
def list_confluence_attachments(
    page_id: str,
    file_type: str = "pdf",
) → str:
    """List PDF attachments on a Confluence page."""
    with _get_client() as client:
        attachments = client.list_page_attachments(page_id, file_type)
    return json.dumps(attachments, indent=2, default=str)


@mcp.tool()
def download_confluence_attachment(
    page_id: str,
    attachment_id: str,
    output_path: str,
) → str:
    """Download a PDF attachment from Confluence."""
    with _get_client() as client:
        attachments = client.list_page_attachments(page_id)
        attachment = next(
            (a for a in attachments if a["id"] == attachment_id),
            None
        )
        if not attachment:
            return json.dumps({"error": "Attachment not found"})
        
        content = client.download_attachment(attachment["url"])
        Path(output_path).write_bytes(content)
    
    return json.dumps({
        "status": "downloaded",
        "path": output_path,
        "size_bytes": len(content),
        "attachment_id": attachment_id,
    })
```

---

### Phase 2: Create Business Context Extraction Workflow

**New file:** `agentic_cli/kg/business_context_extractor.py`

```python
"""Extract business context from Confluence PDFs and internalize in Memory MCP."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from agentic_cli.clients.mcp_client import MCPClient
from agentic_cli.kg.parsers import parse_pdf


class BusinessContextExtractor:
    """Extract and internalize business context from Confluence PDFs."""
    
    def __init__(self, confluence_mcp: MCPClient, memory_mcp: MCPClient):
        """
        Args:
            confluence_mcp: Client to Confluence MCP (for fetching PDFs)
            memory_mcp: Client to Memory MCP (for storing context)
        """
        self.confluence = confluence_mcp
        self.memory = memory_mcp
    
    async def extract_from_space(
        self,
        space_key: str,
        search_terms: List[str] = None,
    ) → Dict[str, Any]:
        """Extract business context from all PDFs in a Confluence space.
        
        Args:
            space_key: Confluence space key (e.g., "BACKEND", "API")
            search_terms: Keywords to find relevant pages
                         (e.g., ["business rules", "SLA", "integration"])
        
        Returns:
            Dictionary with extraction statistics
        """
        
        search_terms = search_terms or [
            "business rules",
            "requirements",
            "SLA",
            "integration",
            "API specification",
            "data contract",
        ]
        
        stats = {
            "pages_found": 0,
            "pdfs_extracted": 0,
            "entities_stored": 0,
            "facts_stored": 0,
            "errors": [],
        }
        
        # Step 1: Find relevant pages in space
        for term in search_terms:
            pages = await self._search_space(space_key, term)
            stats["pages_found"] += len(pages)
            
            # Step 2: For each page, extract PDFs
            for page in pages:
                try:
                    attachments = await self._list_attachments(
                        page["id"],
                        file_type="pdf"
                    )
                    
                    for attachment in attachments:
                        # Step 3: Download PDF
                        pdf_content = await self._download_pdf(
                            page["id"],
                            attachment["id"]
                        )
                        
                        # Step 4: Parse PDF
                        text = await self._parse_pdf(pdf_content)
                        
                        # Step 5: Extract structured context
                        context = await self._extract_context(
                            text,
                            page["title"],
                            attachment["title"]
                        )
                        
                        # Step 6: Store in Memory MCP
                        await self._store_context(context)
                        
                        stats["pdfs_extracted"] += 1
                        stats["entities_stored"] += len(context.get("entities", []))
                        stats["facts_stored"] += len(context.get("facts", []))
                
                except Exception as e:
                    stats["errors"].append({
                        "page": page["title"],
                        "error": str(e)
                    })
        
        return stats
    
    async def _search_space(self, space_key: str, query: str) → List[Dict]:
        """Search for pages in space."""
        result = await self.confluence.call_tool(
            "search_confluence_cql",
            cql=f'space={space_key} AND text~"{query}"',
            limit=20
        )
        return json.loads(result).get("results", [])
    
    async def _list_attachments(self, page_id: str, file_type: str) → List[Dict]:
        """List PDF attachments on page."""
        result = await self.confluence.call_tool(
            "list_confluence_attachments",
            page_id=page_id,
            file_type=file_type,
        )
        return json.loads(result)
    
    async def _download_pdf(self, page_id: str, attachment_id: str) → bytes:
        """Download PDF from Confluence."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name
        
        result = await self.confluence.call_tool(
            "download_confluence_attachment",
            page_id=page_id,
            attachment_id=attachment_id,
            output_path=output_path,
        )
        
        # Read downloaded file
        return Path(output_path).read_bytes()
    
    async def _parse_pdf(self, pdf_content: bytes) → str:
        """Parse PDF to text."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_content)
            pdf_path = tmp.name
        
        documents = parse_pdf(pdf_path)
        
        # Concatenate all pages
        full_text = "\n\n".join([doc["content"] for doc in documents])
        return full_text
    
    async def _extract_context(
        self,
        text: str,
        page_title: str,
        attachment_title: str,
    ) → Dict[str, Any]:
        """Extract structured context from PDF text.
        
        Uses LLM to identify:
        - Business rules
        - Integration requirements
        - SLA/performance targets
        - Data contracts
        - Domain entities
        """
        
        prompt = f"""
Extract structured business context from this document:

Page: {page_title}
Document: {attachment_title}

Content:
{text[:5000]}  # First 5000 chars to avoid token limits

Return JSON with:
{{
    "entities": [
        {{
            "type": "BusinessRule|IntegrationSpec|SLA|DataContract|DomainEntity",
            "name": "Entity name",
            "description": "What this is",
            "properties": {{"key": "value"}}
        }}
    ],
    "facts": [
        {{
            "subject": "Entity or concept",
            "predicate": "relates_to|requires|restricts|measures",
            "object": "Entity or value",
            "confidence": 0.9
        }}
    ],
    "preferences": [
        {{
            "key": "preferred_approach|constraint|standard",
            "value": "Description",
            "applies_to": "module or scope"
        }}
    ]
}}
"""
        
        # Call LLM (your existing LLM client)
        from agentic_cli.llm import call_llm
        
        response = await call_llm(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return {
                "entities": [{
                    "type": "Document",
                    "name": attachment_title,
                    "description": text[:200]
                }],
                "facts": [],
                "preferences": []
            }
    
    async def _store_context(self, context: Dict[str, Any]) → None:
        """Store extracted context in Memory MCP."""
        
        # Store entities (Business Rules, Specs, etc.)
        for entity in context.get("entities", []):
            await self.memory.call_tool(
                "memory_add_entity",
                entity_name=entity["name"],
                entity_type=entity["type"],
                properties=entity.get("properties", {})
            )
        
        # Store facts (relationships between entities)
        for fact in context.get("facts", []):
            await self.memory.call_tool(
                "memory_add_fact",
                subject=fact["subject"],
                predicate=fact["predicate"],
                object=fact["object"],
                metadata={"confidence": fact.get("confidence", 1.0)}
            )
        
        # Store preferences (engineering standards, constraints)
        for pref in context.get("preferences", []):
            await self.memory.call_tool(
                "memory_add_preference",
                key=pref["key"],
                value=pref["value"],
                context=pref.get("applies_to", "global")
            )
```

---

### Phase 3: Integrate with Code Onboarding

**Modify:** `agentic_cli/commands/code.py`

```python
async def onboard_code(
    repo_url: str,
    output_dir: Path,
    with_business_context: bool = False,  # ← NEW parameter
    confluence_space: str = None,          # ← NEW parameter
):
    """Onboard code with optional business context from Confluence."""
    
    # Step 1: Standard code analysis
    analysis = await analyze_project(repo_url)
    
    # Step 2: [NEW] Extract business context from Confluence
    if with_business_context and confluence_space:
        console.print("[dim]Extracting business context from Confluence...[/dim]")
        
        # Initialize MCP clients
        confluence_mcp = MCPClient("confluence", port=8129)
        memory_mcp = MCPClient("memory", port=8130)
        
        # Extract PDFs from Confluence
        extractor = BusinessContextExtractor(confluence_mcp, memory_mcp)
        stats = await extractor.extract_from_space(confluence_space)
        
        console.print(f"[green]✓ Extracted {stats['pdfs_extracted']} PDFs[/green]")
        console.print(f"[green]✓ Stored {stats['entities_stored']} entities[/green]")
    
    # Step 3: Generate understanding doc with business context
    context_doc = await build_understanding_doc(
        analysis,
        use_business_context=with_business_context
    )
    
    # Step 4: Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "codebase-understanding.md").write_text(context_doc)
```

**New CLI command:**

```bash
# Extract business context from Confluence BEFORE code analysis
agent code onboard https://github.com/myteam/backend \
    --with-business-context \
    --confluence-space BACKEND

# Or just refresh business context
agent code extract-business-context \
    --confluence-space BACKEND \
    --search-terms "business rules,SLA,integration"
```

---

### Phase 4: Query Business Context During Development

**New tool:** `agentic_cli/commands/context.py`

```bash
# Query business context stored in Memory MCP
agent context search "payment authorization rules"
# Returns: Entities, facts, preferences from PDFs

agent context get-entity BusinessRule:OrderApproval
# Returns: Detailed entity + relationships

agent context list-entities --type IntegrationSpec
# Returns: All integration specs extracted from Confluence
```

---

## Complete Workflow Example

```bash
# 1. Extract business context from Confluence (one-time setup)
$ agent code extract-business-context \
    --confluence-space ORDER-API \
    --search-terms "business rules,SLA,integration,data contract"

✓ Found 12 pages
✓ Extracted 23 PDFs
✓ Stored 47 business entities
✓ Stored 156 facts
✓ Stored 34 preferences

# 2. Onboard code project (with business context already loaded)
$ agent code onboard https://github.com/myteam/order-api \
    --with-business-context

🔄 Phase 1: Repository Analysis
✓ Detected: FastAPI, PostgreSQL, async/await

🔄 Phase 2: Business Context Lookup
✓ Found in Memory: "Order Approval Rules"
✓ Found in Memory: "Payment Integration SLA"
✓ Found in Memory: "Inventory Data Contract"

🔄 Phase 3: Understanding Generation
✓ Merged code analysis + business context
✓ Generated .keel/codebase-understanding.md

# 3. During skill generation, skills reference business context
$ agent skill generate fastapi-endpoint-skill \
    --project ./order-api

Generated skill includes:
- Function signatures (from code)
- Business rules (from Confluence)
- Integration requirements (from Confluence)
- SLA constraints (from Confluence)
- Example implementations (from similar projects)

# 4. Query business context anytime
$ agent context search "payment authorization"

Results:
- Entity: PaymentAuthorizationRule
  Description: "All payments > $10k require manual approval"
  Source: order-api-business-rules.pdf
  Confidence: 0.95

- Fact: PaymentService RESTRICTS Order.total > 10000
  From: integration-spec.pdf
```

---

## Benefits of MCP-Based Approach

### 1. **Automated PDF Extraction**
- No manual document parsing
- Confluence attachments auto-discovered
- Scales to many documents

### 2. **Structured Business Context**
- PDFs parsed into entities + facts
- Business rules become queryable
- Relationships preserved

### 3. **Context-Aware Skills**
- Skills know business rules
- Integration specs embedded
- SLA constraints enforced

### 4. **Semantic Search**
- "Payment authorization rules"
- "PostgreSQL integration specs"
- "High-value order handling"

### 5. **Reusable Across Projects**
- Extract once from Confluence
- Use with all future projects
- Learn from business patterns

---

## Implementation Steps

### Week 1: Extend Confluence MCP
1. [ ] Add `list_page_attachments()` to ConfluenceClient
2. [ ] Add `download_attachment()` method
3. [ ] Expose as MCP tools: `list_confluence_attachments`, `download_confluence_attachment`
4. [ ] Test with real Confluence space

### Week 2: Business Context Extractor
1. [ ] Create `BusinessContextExtractor` class
2. [ ] Implement PDF parsing workflow
3. [ ] LLM-based entity/fact extraction
4. [ ] Memory MCP storage integration
5. [ ] Test extraction on sample PDFs

### Week 3: Code Onboarding Integration
1. [ ] Add `--with-business-context` flag to `agent code onboard`
2. [ ] Integrate Memory MCP queries
3. [ ] Merge business context into understanding doc
4. [ ] Test with real projects

### Week 4: Query Interface
1. [ ] Create `agent context` command group
2. [ ] Implement search, list, get-entity operations
3. [ ] Add to Agent Playground dashboard
4. [ ] Documentation + examples

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│              Agent Playground Dashboard              │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Projects │  │  Skills  │  │ Business Context │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└──────────┬──────────────────────────────┬────────────┘
           │                              │
           ▼                              ▼
    agent code onboard          agent context search
           │                              │
           ├──────────────────┬───────────┤
           │                  │           │
           ▼                  ▼           ▼
   ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
   │ Code Analyzer │  │ Confluence   │  │ Memory MCP   │
   │ (detector,    │  │ MCP (search, │  │ (search,     │
   │  gitingest)   │  │  download)   │  │  retrieve)   │
   └───────────────┘  └──────────────┘  └──────────────┘
           │                  │                  │
           │                  ▼                  │
           │          ┌──────────────────┐      │
           │          │ PDF Extraction   │◄─────┘
           │          │ & LLM Processing │
           │          └──────────────────┘
           │                  │
           └──────────┬───────┘
                      ▼
            ┌───────────────────┐
            │  LightRAG + KG    │
            │  Unified Context  │
            └───────────────────┘
                      │
                      ▼
            ┌───────────────────┐
            │ AI-Ready Context  │
            │ (for code skills) │
            └───────────────────┘
```

---

## Configuration

```bash
# .env or mcp-servers/.env

# Confluence MCP
CONFLUENCE_SERVER_URL=https://company.atlassian.net
CONFLUENCE_PERSONAL_ACCESS_TOKEN=xxx

# Memory MCP (already running via Neo4j)
NEO4J_URI=bolt://keel-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxx

# KG MCP
KG_NEO4J_URI=bolt://keel-neo4j:7687
KG_LIGHTRAG_URL=http://keel-lightrag:8001

# LLM for entity extraction
OPENAI_API_KEY=xxx  # or VERTEX_AI_PROJECT, etc.
```

This transforms **scattered Confluence PDFs** into **queryable, structured business knowledge** integrated with your code analysis pipeline.
