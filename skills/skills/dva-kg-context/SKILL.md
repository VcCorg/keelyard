---
name: dva-kg-context
description: >-
  Search and query the DVA Knowledge Graph for business context, domain rules,
  SLAs, integrations, and security policies via DVA Central MCP. Use this skill
  when you need to understand business requirements while writing or reviewing code.
mcp_server: agentic
---

# DVA Knowledge Graph & Context

You have access to the Agentic Platform MCP server which integrates the Knowledge Graph.
Use these tools to search business context, query domain knowledge, and ingest
new content into the KG.

## Search & Query Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `kg_search` | Semantic search across all domain knowledge | `query`, `project?`, `limit?` |
| `kg_project_context` | High-level project overview from KG | `project` |
| `kg_domain_context` | Domain context (SLAs, integrations, security, architecture) | `domain`, `aspect?` |
| `kg_query` | Raw KG query (lightrag or neo4j) | `query`, `provider?` |
| `kg_entity` | Get entity details from Neo4j | `entity_name` |

## Ingestion Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `kg_ingest` | Ingest a registered source into KG | `source_name`, `extract_entities?` |
| `kg_sources` | List registered knowledge sources | — |
| `kg_projects` | List knowledge projects | — |

## Context Aggregation Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `context_full` | Full context: tech stack + domain + KG + skills | `path` |
| `context_domain` | Full domain context: metadata + repos + docs + KG | `domain` |
| `context_skill_gaps` | Detect gaps between installed and available skills | `path` |

## Domain Context Aspects

When calling `kg_domain_context`, the `aspect` parameter filters results:

| Aspect | What It Returns |
|--------|----------------|
| `all` | Everything (default) |
| `business_rules` | Business rules and domain logic |
| `slas` | SLA requirements and performance targets |
| `integrations` | Integration specs and external system dependencies |
| `security` | Security policies and compliance requirements |
| `architecture` | Architecture decisions and patterns |
| `data_model` | Data model and entity relationships |

## Typical Usage

### When writing code — search for business rules

```
result = kg_search(query="patient eligibility rules for facility transfer")
```

### When reviewing a PR — get domain context

```
context = kg_domain_context(domain="cwow-facility", aspect="business_rules")
```

### When onboarding — get full project context

```
full = context_full(path="/path/to/repo")
# Returns: tech stack + domain metadata + KG business context + installed skills
```

### When starting a new feature — check SLAs and integrations

```
slas = kg_domain_context(domain="cwow-facility", aspect="slas")
integrations = kg_domain_context(domain="cwow-facility", aspect="integrations")
```

## KG Backends

The Agentic MCP queries two backends:
- **LightRAG** — semantic/RAG search, best for natural language queries
- **Neo4j** — structured graph queries, best for entity relationships

Both are queried automatically; results are merged and ranked.

## When to Use

- User asks about business rules or domain requirements
- User needs SLA or performance requirements for a feature
- User asks about integrations with external systems
- User needs security or compliance context
- User wants to understand the data model or architecture
- User asks "what do I need to know about X domain"

## Fallback (No MCP)

If the Agentic MCP server is not running:
1. Check `.skills/domain-context/SKILL.md` for embedded domain context
2. Use the CLI: `dva kg query "your question" --domain <slug>`
3. Query LightRAG directly if running: `curl http://localhost:9621/query`
