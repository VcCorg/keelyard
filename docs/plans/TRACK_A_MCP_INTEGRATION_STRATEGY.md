# Track A: MCP Integration Strategy

**Date**: May 6, 2026  
**Status**: Design Complete  
**Scope**: How MCP fits into domain knowledge onboarding and code onboarding

---

## The Question

How does MCP play into the updated design? Is domain knowledge exposed as MCP for code onboarding, or is a different approach used?

---

## The Answer: Dual Integration Strategy

Domain knowledge is integrated into code onboarding through **two complementary approaches**:

### Approach 1: Memory MCP (For Agents)
**Purpose**: Expose domain knowledge as MCP tools for agents to query during execution

**How it works**:
```
Domain Knowledge (in KG)
    ↓
Memory MCP
├─ Tool: query_domain_rules(domain, category)
├─ Tool: search_rules(keyword)
├─ Tool: get_sla(domain)
├─ Tool: get_integration_specs(domain)
└─ Tool: get_security_policies(domain)
    ↓
Agents can query during execution
```

**Use case**: When an agent is executing code for a domain, it can query business rules in real-time

### Approach 2: Direct KG Query (For Code Onboarding)
**Purpose**: Directly query KG during code analysis to enrich understanding documents

**How it works**:
```
Code Onboarding Analysis
    ↓
Query KG directly
├─ Get SLAs for domain
├─ Get integration specs
├─ Get security policies
└─ Get performance requirements
    ↓
Include in understanding document
    ↓
Reference in generated skills
```

**Use case**: When onboarding code, include business context in understanding documents

---

## Architecture: Two Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                      Domain Knowledge                           │
│                     (Stored in KG)                              │
│                                                                 │
│  - SLAs                                                         │
│  - Integration Specs                                            │
│  - Security Policies                                            │
│  - Performance Requirements                                     │
│  - Business Rules                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
        ┌──────────────────┐  ┌──────────────────┐
        │   Memory MCP     │  │  Direct KG Query │
        │                  │  │                  │
        │ Exposes as tools │  │ Used during      │
        │ for agents       │  │ code onboarding  │
        │                  │  │                  │
        │ Tools:           │  │ Approach:        │
        │ - query_rules()  │  │ - Query KG       │
        │ - search_rules() │  │ - Enrich docs    │
        │ - get_sla()      │  │ - Reference      │
        │ - get_specs()    │  │   in skills      │
        └──────────────────┘  └──────────────────┘
                    ↓                   ↓
        ┌──────────────────┐  ┌──────────────────┐
        │  Agent Execution │  │ Code Onboarding  │
        │                  │  │                  │
        │ Agent queries    │  │ Understanding    │
        │ rules during     │  │ document includes│
        │ execution        │  │ business context │
        │                  │  │                  │
        │ Example:         │  │ Generated skills │
        │ "What's the SLA? │  │ reference        │
        │  for this API?"  │  │ business rules   │
        └──────────────────┘  └──────────────────┘
```

---

## Approach 1: Memory MCP (For Agents)

### What is Memory MCP?

Memory MCP is an existing MCP server that stores and retrieves entities and facts. It's designed for agents to query during execution.

### How Domain Knowledge Flows to Memory MCP

```
Step 1: KG Onboarding
├─ Scan Confluence
├─ Extract rules
└─ Store in KG
    ↓
Step 2: Sync to Memory MCP
├─ Read rules from KG
├─ Create entities in Memory MCP
│  ├─ SLA entities
│  ├─ IntegrationSpec entities
│  ├─ SecurityPolicy entities
│  └─ PerformanceRequirement entities
└─ Create relationships
    ↓
Step 3: Agent Execution
├─ Agent runs code for domain
├─ Agent queries Memory MCP
│  └─ "Get SLA for cwow-facility"
├─ Memory MCP returns rules
└─ Agent uses rules in decision-making
```

### Memory MCP Tools

```python
# In Memory MCP server

@server.call_tool
async def handle_call_tool(name: str, arguments: dict) -> Any:
    
    if name == "query_domain_rules":
        domain = arguments.get("domain")
        category = arguments.get("category")  # SLA, Integration, Security, Performance
        return await memory_client.query_rules(domain, category)
    
    elif name == "search_rules":
        keyword = arguments.get("keyword")
        return await memory_client.search_rules(keyword)
    
    elif name == "get_sla":
        domain = arguments.get("domain")
        return await memory_client.get_sla(domain)
    
    elif name == "get_integration_specs":
        domain = arguments.get("domain")
        return await memory_client.get_integration_specs(domain)
    
    elif name == "get_security_policies":
        domain = arguments.get("domain")
        return await memory_client.get_security_policies(domain)
    
    elif name == "get_performance_requirements":
        domain = arguments.get("domain")
        return await memory_client.get_performance_requirements(domain)
```

### Agent Usage Example

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
    # Violates SLA, log warning
    logger.warning(f"SLA violation: Response time {response_time}ms > 100ms")

# Query for integration specs
specs = await mcp_client.call_tool(
    "get_integration_specs",
    {"domain": "cwow-facility"}
)

# Agent sees: "Must integrate with FHIR API, use OAuth 2.0"
# Agent uses this in implementation
```

---

## Approach 2: Direct KG Query (For Code Onboarding)

### How Code Onboarding Uses Domain Knowledge

```
Step 1: Code Onboarding Analysis
├─ Analyze repository
├─ Detect tech stack
├─ Identify patterns
└─ Get domain name from CLI
    ↓
Step 2: Query KG for Domain Knowledge
├─ Query KG: Get SLAs for domain
├─ Query KG: Get integration specs
├─ Query KG: Get security policies
└─ Query KG: Get performance requirements
    ↓
Step 3: Enrich Understanding Document
├─ Add Business Context section
├─ List applicable SLAs
├─ List integration requirements
├─ List security requirements
└─ List performance requirements
    ↓
Step 4: Generate Skills
├─ Generate 8-15 domain-specific skills
├─ Skills aware of SLAs
├─ Skills aware of security requirements
└─ Skills include compliance checks
```

### Code Onboarding Integration

```python
# In codebase_analyzer.py

class CodebaseAnalyzer:
    def __init__(self, domain_name: str, kg_client):
        self.domain_name = domain_name
        self.kg = kg_client
    
    async def analyze(self, repo_path: str) -> AnalysisResult:
        # Step 1: Analyze code (existing)
        analysis = await self._analyze_code(repo_path)
        
        # Step 2: Query KG for domain knowledge (NEW)
        business_context = await self._get_business_context()
        
        # Step 3: Enrich analysis with business context
        analysis.business_context = business_context
        analysis.applicable_slas = business_context.get("slas", [])
        analysis.integration_requirements = business_context.get("integrations", [])
        analysis.security_requirements = business_context.get("security", [])
        analysis.performance_requirements = business_context.get("performance", [])
        
        return analysis
    
    async def _get_business_context(self) -> Dict:
        """Query KG for domain knowledge."""
        return await self.kg.query_domain_context(self.domain_name)
```

### Understanding Document Example

```markdown
# Facility Service - Codebase Understanding

## Business Context

### Applicable SLAs
- Response time < 100ms
- Availability > 99.9%
- Data consistency: Strong consistency required

### Integration Requirements
- Must integrate with FHIR API
- Use OAuth 2.0 for authentication
- Support HL7 v2 for legacy systems

### Security Requirements
- HIPAA compliant
- Encrypt data at rest (AES-256)
- Encrypt data in transit (TLS 1.2+)
- Audit logging required

### Performance Requirements
- Support 10K concurrent users
- Database query latency < 50ms
- Cache hit rate > 80%

## Architecture

...
```

---

## Comparison: Memory MCP vs Direct Query

| Aspect | Memory MCP | Direct KG Query |
|--------|-----------|-----------------|
| **Purpose** | Agents query during execution | Code onboarding enrichment |
| **When Used** | Runtime | Analysis time |
| **Who Uses** | Agents | Code onboarding process |
| **Latency** | Real-time (< 100ms) | Batch (during analysis) |
| **Use Case** | Agent decision-making | Document generation |
| **Example** | "What's the SLA?" | Include SLA in understanding |

---

## Implementation Strategy

### Phase 1: KG Onboarding (Already Designed)
```
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
    ↓
Stores domain knowledge in KG
```

### Phase 2: Sync KG to Memory MCP (NEW)
```
After KG onboarding completes:
    ↓
Read rules from KG
    ↓
Create entities in Memory MCP
    ↓
Agents can query Memory MCP
```

### Phase 3: Code Onboarding Integration (Already Designed)
```
keel code onboard https://github.com/company/facility-service --domain cwow-facility
    ↓
Query KG for domain knowledge
    ↓
Enrich understanding document
    ↓
Generate skills with business context
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Confluence Releases                          │
│                  (Release 29, 28, 27, ...)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  KG Onboarding      │
                    │  (keel kg onboard)   │
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
        │  MCP (NEW)       │  │  (Existing)      │
        └──────────────────┘  └──────────────────┘
                    ↓                   ↓
        ┌──────────────────┐  ┌──────────────────┐
        │  Memory MCP      │  │  Code Onboarding │
        │  (Agents query)  │  │  (Enrich docs)   │
        └──────────────────┘  └──────────────────┘
```

---

## New Phase: KG to Memory MCP Sync

### Phase 2.5: Sync KG to Memory MCP (1-2 days)

**What**: After KG onboarding, sync domain knowledge to Memory MCP

**How**:
```python
# After KG onboarding completes

async def sync_kg_to_memory_mcp(domain_name: str):
    """Sync domain knowledge from KG to Memory MCP."""
    
    # 1. Query KG for domain knowledge
    knowledge = await kg_client.query_domain_context(domain_name)
    
    # 2. Create entities in Memory MCP
    for sla in knowledge.get("slas", []):
        await memory_client.store_entity(
            entity_type="SLA",
            name=sla["title"],
            properties={
                "domain": domain_name,
                "content": sla["content"],
                "source": sla["source"],
            }
        )
    
    for spec in knowledge.get("integration_specs", []):
        await memory_client.store_entity(
            entity_type="IntegrationSpec",
            name=spec["title"],
            properties={
                "domain": domain_name,
                "content": spec["content"],
                "source": spec["source"],
            }
        )
    
    # ... similar for security policies, performance requirements
    
    # 3. Create relationships
    await memory_client.create_relationship(
        source_entity=f"Domain:{domain_name}",
        relationship="has_sla",
        target_entity=f"SLA:{sla['title']}"
    )
```

**When**: Automatically after KG onboarding completes

**Result**: Agents can query Memory MCP for domain knowledge

---

## Updated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1 | 0 days | Domain create (already done) |
| 2 | 3-5 days | KG onboarding command |
| 2.5 | 1-2 days | KG to Memory MCP sync (NEW) |
| 3 | 2-3 days | Async job system |
| 4 | 1-2 days | Code onboarding integration |
| **Total** | **7-12 days** | **Complete Track A with MCP** |

---

## Benefits of Dual Approach

### Memory MCP Benefits
- ✅ Agents can query business rules during execution
- ✅ Real-time access to domain knowledge
- ✅ Agents can make better decisions
- ✅ Agents aware of SLAs, security, integration requirements

### Direct KG Query Benefits
- ✅ Code onboarding enriched with business context
- ✅ Understanding documents include business rules
- ✅ Generated skills aware of business constraints
- ✅ No need to query Memory MCP during analysis

### Combined Benefits
- ✅ Business knowledge available everywhere
- ✅ Agents and code onboarding both benefit
- ✅ Single source of truth (KG)
- ✅ Multiple access patterns (MCP + direct query)

---

## Example: Complete Flow

### Step 1: Register Domain
```bash
$ keel domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
✓ Domain registered: cwow-facility
```

### Step 2: Onboard Knowledge
```bash
$ keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
✓ Knowledge onboarding complete
  - Stored in KG
  - Synced to Memory MCP
```

### Step 3: Code Onboarding
```bash
$ keel code onboard https://github.com/company/facility-service --domain cwow-facility
✓ Code onboarding complete
  - Understanding includes business context from KG
  - Generated skills reference business rules
```

### Step 4: Agent Execution
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

## Success Criteria

- [ ] KG onboarding working
- [ ] KG to Memory MCP sync working
- [ ] Memory MCP tools accessible to agents
- [ ] Code onboarding queries KG
- [ ] Understanding documents include business context
- [ ] Generated skills reference business rules
- [ ] Agents can query Memory MCP
- [ ] End-to-end flow working

---

**Status**: ✅ DESIGN COMPLETE  
**Approach**: Dual integration (Memory MCP + Direct KG Query)  
**Timeline**: 7-12 days

---

## Summary

Domain knowledge is integrated into code onboarding through **two complementary approaches**:

1. **Memory MCP** - Agents query during execution
   - Tools: `query_domain_rules()`, `get_sla()`, `get_integration_specs()`, etc.
   - Use case: Agent decision-making
   - Latency: Real-time

2. **Direct KG Query** - Code onboarding enrichment
   - Query KG during analysis
   - Include in understanding documents
   - Reference in generated skills
   - Use case: Document generation

Both approaches use the same source of truth (KG), but expose it in different ways for different use cases.
