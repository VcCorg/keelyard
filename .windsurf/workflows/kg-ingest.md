---
description: Ingest Confluence docs and project files into the Knowledge Graph using Agentic Platform MCP
---

# Knowledge Graph Ingestion Workflow

Ingest Confluence documentation and project files into the Knowledge Graph
so AI assistants can search business context, domain rules, and requirements.

**Related skill**: Read `skills/skills/dva-kg-context/SKILL.md` for the full MCP tool reference.

## Prerequisites

- Agentic Platform MCP server (`agentic`) configured in MCP settings
- KG backends running: LightRAG (`:9621`) and/or Neo4j (`:7687`)
- For Confluence ingestion: `CONFLUENCE_PERSONAL_ACCESS_TOKEN` set in MCP env

## Step 1: Check KG Status

Verify the Knowledge Graph backends are accessible:

```text
kg_sources()    # List registered sources
kg_projects()   # List knowledge projects
```

## Step 2: Register Domain Docs (if not already tracked)

If the domain has Confluence docs that aren't tracked yet, add them:

```text
domain_add_doc(domain_slug="cwow-facility", page_id="847844475", space_key="CWOV", title="Release 29")
domain_add_doc(domain_slug="cwow-facility", page_id="847844500", space_key="MTT", title="Facility Data Model")
```

## Step 3: Ingest Domain Docs

Ingest tracked Confluence docs into the Knowledge Graph:

```text
kg_ingest(source_name="cwow-facility-docs", extract_entities=true)
```

This will:
- Fetch pages from Confluence via REST API
- Convert HTML to clean markdown text
- Ingest into LightRAG for semantic search
- Extract entities and relationships (if `extract_entities=true`)
- Tag documents with domain and product metadata

## Step 4: Ingest Project Files (Optional)

For code-level context, ingest project documentation:

```text
kg_ingest(source_name="cwow-facility-service-docs", extract_entities=true)
```

Supported file types: `.md`, `.txt`, `.pdf`, `.json`, `.csv`

## Step 5: Verify Ingestion

Search the KG to verify content was ingested:

```text
kg_search(query="facility transfer rules", project="cwow-facility")
```

Check domain context is available:

```text
kg_domain_context(domain="cwow-facility", aspect="business_rules")
kg_domain_context(domain="cwow-facility", aspect="slas")
```

## Step 6: Generate Domain Context Skill

After ingestion, the domain context can be embedded into a skill:

```text
context = kg_domain_context(domain="cwow-facility", aspect="all")
```

Use this context to generate or update `.skills/domain-context/SKILL.md` in each
domain repo (the `/onboard-repo` workflow does this automatically with `--domain`).

## CLI Fallback

If Agentic MCP is not available:

```bash
# Ingest tracked domain docs
dva kg ingest submit --domain cwow-facility

# Ingest specific Confluence pages
dva kg ingest submit --domain cwow-facility \
  --path https://confluence.example.com/spaces/CWOV/pages/847844475/Release+29

# Query KG
dva kg query "facility transfer rules" --domain cwow-facility
```

## Related Workflows

- `/manage-domain` — Register products, domains, and link repos/docs
- `/domain-context` — Set up domain context with git submodules
- `/onboard-repo` — Onboard a repo with skills + domain context
