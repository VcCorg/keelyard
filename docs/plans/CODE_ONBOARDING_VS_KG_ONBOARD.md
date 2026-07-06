# Code Onboarding vs KG Onboard - Clarification

**Date**: May 6, 2026  
**Question**: How is `code onboard --kg` different from `kg onboard`? Do we need full entity extraction?  
**Goal**: Map code context to business requirements context

---

## The Two Commands

### Command 1: `keel kg onboard`
```bash
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
```

**Purpose**: Onboard domain knowledge into the Knowledge Graph

**What it does**:
1. Scan Confluence space
2. Discover all releases
3. Find domain documents
4. Deduplicate by version
5. Extract rules
6. **Store in KG** (Neo4j + LightRAG)
7. **Sync to Memory MCP**

**Output**: Domain knowledge in KG (SLAs, integration specs, security policies, performance requirements)

**Timeline**: 5-10 minutes

**When to use**: 
- ✅ When you need to build domain knowledge base
- ✅ When you need to refresh KG with latest documents
- ✅ When you need to onboard a new domain

---

### Command 2: `keel code onboard --kg`
```bash
keel code onboard --path ./facility-service --kg
```

**Purpose**: Onboard a codebase and map it to business context

**What it does**:
1. Analyze project structure
2. Generate GitIngest digest
3. Generate Graphify analysis
4. **Query KG for domain knowledge** (if domain specified)
5. Build hybrid kg-context.md
6. **Ingest into LightRAG** (light mode)
7. Generate domain-aware skills

**Output**: 
- kg-context.md (hybrid context)
- Domain-aware skills
- Project context in LightRAG

**Timeline**: 5-10 minutes

**When to use**:
- ✅ When you're onboarding a new codebase
- ✅ When you want to map code to business requirements
- ✅ When you want to generate domain-aware skills

---

## Key Differences

| Aspect | `kg onboard` | `code onboard --kg` |
|--------|-------------|-------------------|
| **Input** | Confluence space | Code repository |
| **Purpose** | Build domain knowledge | Map code to business context |
| **Analyzes** | Documents | Code structure |
| **Queries KG** | No | Yes (if domain specified) |
| **Generates** | Business rules | Domain-aware skills |
| **Output** | KG entities | Code context + skills |
| **Goal** | Knowledge base | Code understanding |

---

## Your Goal: Map Code Context to Business Requirements

Your goal is: **Map code context to business requirements context**

### Which command helps?

**`keel code onboard --kg`** is the right command for your goal!

Here's why:

```
Code Repository
    ↓
Code Onboarding Analysis
├─ Analyze code structure (Graphify)
├─ Analyze repository (GitIngest)
└─ Query KG for business requirements ← THIS IS KEY
    ↓
kg-context.md (Hybrid Context)
├─ Code structure (from Graphify)
├─ Business requirements (from KG)
└─ Repository overview (from GitIngest)
    ↓
Result: Code context MAPPED to business requirements
```

---

## The Entity Extraction Question

### What is Entity Extraction?

Entity extraction is the process of identifying and extracting specific entities from documents:

```
Input: kg-context.md
├─ "Response time must be < 100ms"
├─ "Must implement FHIR API"
├─ "HIPAA compliance required"
└─ "Support 10K concurrent users"
    ↓
Entity Extraction
├─ Entity: SLA
│  └─ Property: response_time = 100ms
├─ Entity: Integration
│  └─ Property: api_type = FHIR
├─ Entity: Security
│  └─ Property: compliance = HIPAA
└─ Entity: Performance
   └─ Property: concurrent_users = 10K
    ↓
Structured Entities in KG
```

### Do You Need Full Entity Extraction for Your Goal?

**Short Answer**: NO, you don't need full entity extraction.

**Why**:
- Your goal is to **map code context to business requirements**
- You need the **hybrid context** (code + business requirements)
- You don't need to extract and structure entities
- You just need the **information available** in kg-context.md

---

## Two Modes of `code onboard --kg`

### Mode 1: Light Mode (Default)
```bash
keel code onboard --path ./facility-service --kg
```

**What it does**:
1. Analyze code (Graphify + GitIngest)
2. Query KG for domain knowledge
3. Build kg-context.md (hybrid context)
4. **Ingest into LightRAG** (light mode)
5. Generate skills

**Ingestion**: Direct ingestion without entity extraction

**Result**: 
- kg-context.md available
- Searchable in LightRAG
- Skills generated

**Timeline**: 5-10 minutes

**Good for**: Your goal ✅

### Mode 2: Full Mode (With Entity Extraction)
```bash
keel code onboard --path ./facility-service --kg --extract-entities
```

**What it does**:
1. Analyze code (Graphify + GitIngest)
2. Query KG for domain knowledge
3. Build kg-context.md (hybrid context)
4. **Run full KG ingestion pipeline**
   - Parse documents
   - **Extract entities** (SLAs, integrations, security, performance)
   - **Build relationships** between entities
   - Index in KG
5. Generate skills

**Ingestion**: Full ingestion with entity extraction and relationship building

**Result**:
- kg-context.md available
- Structured entities in KG
- Relationships between entities
- Skills generated

**Timeline**: 10-15 minutes

**Good for**: When you need structured entity queries

---

## Do You Need Entity Extraction?

### You DON'T need entity extraction if:
- ✅ Your goal is to map code context to business requirements
- ✅ You just need the information available in kg-context.md
- ✅ You want to generate domain-aware skills
- ✅ You want fast code onboarding (5-10 minutes)
- ✅ You don't need to query entities programmatically

### You DO need entity extraction if:
- ❌ You need to query SLAs programmatically
- ❌ You need to query integration specs programmatically
- ❌ You need to build relationships between entities
- ❌ You need structured entity graphs
- ❌ You need to analyze entity relationships

---

## Recommended Approach for Your Goal

### Step 1: Onboard Domain Knowledge (One-time)
```bash
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
```

**Result**: Domain knowledge in KG (SLAs, integration specs, security policies, performance requirements)

**Timeline**: 5-10 minutes

### Step 2: Onboard Code with Business Context (For each codebase)
```bash
keel code onboard --path ./facility-service --kg
```

**Result**: 
- kg-context.md with code + business requirements
- Domain-aware skills
- Code context mapped to business requirements

**Timeline**: 5-10 minutes

### Step 3: (Optional) Generate Skills with Full Context
```bash
keel code onboard --path ./facility-service --kg --graphify
```

**Result**: 
- kg-context.md with Graphify analysis
- Better code structure understanding
- Better skill generation

**Timeline**: 5-10 minutes

---

## Example: Facility Service

### Step 1: Onboard Domain Knowledge
```bash
$ keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

✓ Knowledge onboarding complete
  Releases scanned: 5
  Documents found: 20
  After deduplication: 4
  Rules extracted: 45
  Stored in KG: ✓
```

**Result**: KG now has:
- SLAs: Response time < 100ms, Availability > 99.9%
- Integration: FHIR API, OAuth 2.0
- Security: HIPAA compliance, AES-256 encryption
- Performance: 10K concurrent users, DB latency < 50ms

### Step 2: Onboard Code with Business Context
```bash
$ keel code onboard --path ./facility-service --kg

✓ Project Onboarded
  Project: facility-service
  Language: Python
  Framework: FastAPI
  Dependencies: 25 found
  Skills Installed: 8
  KG Context: Prepared
  KG Ingested: LightRAG
```

**Result**: kg-context.md contains:

```markdown
# Facility Service - Codebase Understanding

## Business Context (From KG)
- Response time < 100ms
- FHIR API integration
- HIPAA compliance
- 10K concurrent users

## Code Structure (From Graphify)
- 45 code nodes
- 5 code modules
- FacilityService is highly connected

## Repository Overview (From GitIngest)
- Python 3.9+ with FastAPI
- PostgreSQL database
- 120 files, 25 dependencies
```

**Result**: Code context is now MAPPED to business requirements ✅

---

## What Each Command Does for Your Goal

### `keel kg onboard`
```
Confluence Documents
    ↓
Extract Business Requirements
    ↓
Store in KG
    ↓
Result: Business requirements available in KG
```

**Helps your goal**: ✅ YES (provides business requirements)

### `keel code onboard --kg`
```
Code Repository
    ↓
Analyze Code Structure
    ↓
Query KG for Business Requirements
    ↓
Build Hybrid Context (Code + Business)
    ↓
Result: Code context MAPPED to business requirements
```

**Helps your goal**: ✅ YES (maps code to business requirements)

### `keel code onboard --kg --extract-entities`
```
Code Repository
    ↓
Analyze Code Structure
    ↓
Query KG for Business Requirements
    ↓
Build Hybrid Context (Code + Business)
    ↓
Extract and Structure Entities
    ↓
Result: Code context mapped + structured entities
```

**Helps your goal**: ✅ YES (but overkill for your goal)

---

## Recommendation

For your goal of **mapping code context to business requirements context**:

### Use this workflow:

```bash
# Step 1: One-time setup - Onboard domain knowledge
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Step 2: For each codebase - Map code to business requirements
keel code onboard --path ./facility-service --kg

# Step 3: (Optional) Add Graphify for better code structure
keel code onboard --path ./facility-service --kg --graphify
```

### Why this approach:

1. **`kg onboard`** builds the domain knowledge base (one-time)
2. **`code onboard --kg`** maps code to business requirements (for each codebase)
3. **`--graphify`** adds code structure analysis (optional, for better understanding)
4. **NO `--extract-entities`** needed (overkill for your goal)

### Result:

✅ Code context mapped to business requirements  
✅ Domain-aware skills generated  
✅ Fast execution (5-10 minutes per codebase)  
✅ No unnecessary entity extraction overhead  

---

## Summary

| Question | Answer |
|----------|--------|
| **Is `code onboard --kg` different from `kg onboard`?** | YES - different inputs and purposes |
| **Do you need full entity extraction?** | NO - not for your goal |
| **Which command helps your goal?** | `code onboard --kg` |
| **Should you use `--extract-entities`?** | NO - it's overkill |
| **What's the recommended workflow?** | `kg onboard` (once) + `code onboard --kg` (per codebase) |

**Your goal is achieved with `keel code onboard --kg`** - no entity extraction needed!
