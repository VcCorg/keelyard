---
description: Set up multi-repo domain context using git submodules and KG MCP
---

# Domain Context Git Reference — Onboarding Workflow

This workflow sets up shared domain context across multiple repositories
using a central domain-context repository referenced via git submodules.

**Related skills**: `dva-manage-domains`, `dva-kg-context`

## Prerequisites

**If Agentic Platform MCP is available** (preferred):
- MCP server `agentic` configured in `.windsurf/mcp_config.json`
- Use MCP tools: `domain_create`, `domain_link_repo`, `kg_ingest`

**If using CLI fallback**:
- DVA CLI (`dva`) installed and on PATH
- Domain registered: `dva domain create <DOMAIN> --product <PRODUCT>`
- Repos linked: `dva domain link-repo <slug> <repo-slug>`
- (Optional) Knowledge Graph populated via `dva kg ingest`

## Step 1: Ingest Confluence docs into the Knowledge Graph

```bash
# Ingest tracked domain docs + specific release pages into LightRAG
dva kg ingest submit --domain <domain-slug>

# Or with explicit Confluence page URLs (crawls child pages):
dva kg ingest submit --domain <domain-slug> \
  --path https://confluence.example.com/spaces/CWOV/pages/847844475/Release+29

# Control child-page crawl depth:
dva kg ingest submit --domain <domain-slug> --path <page-url> --depth 4
```

This will:
- Fetch tracked domain docs from Confluence (via `domain add-docs`)
- Crawl child pages recursively (e.g. Release 29 sub-pages)
- Convert Confluence HTML to clean markdown
- Ingest into LightRAG (workspace defaults to domain slug)
- Tag all documents with domain/product metadata

## Step 2: Create the central domain context repository

```bash
dva domain init-context <domain-slug> \
  --git-remote <git-url-for-domain-context-repo>
```

This will:
- Query the Knowledge Graph for domain business context (SLAs, integrations, security, architecture)
- Scaffold the repo: `.domain/kg-context.md`, `.skills/shared/`, `README.md`
- Initialize git and set the remote

Then push:

```bash
cd <domain-slug>-domain-context
git push -u origin main
```

## Step 3: Onboard each repo with domain context

For each repository in the domain:

```bash
dva code onboard \
  --path ./<repo-path> \
  --domain <domain-slug> \
  --domain-context-repo <git-url-for-domain-context-repo> \
  --kg
```

This will:
- Analyze the project and install skills
- Query KG for domain context and generate `.skills/domain-context/SKILL.md`
- Write `.domain-context.json` metadata
- Add the domain-context repo as a git submodule at `.domain-context/`
- Prepare and ingest project context into the Knowledge Graph

## Step 4: Verify the setup

After onboarding, each repo should have:

```
<repo>/
├── .domain-context/          ← git submodule → central domain context repo
│   ├── .domain/
│   │   ├── kg-context.md
│   │   ├── domain-metadata.json
│   │   └── architecture.md
│   └── .skills/shared/
├── .skills/
│   ├── project-context/      ← repo-specific context
│   │   ├── SKILL.md
│   │   └── kg-context.md
│   └── domain-context/       ← domain context skill
│       └── SKILL.md
├── .domain-context.json      ← metadata pointing to domain context
└── .gitmodules               ← submodule configuration
```

## Step 5: Use domain context in development

### Via Agentic Platform MCP tools (runtime)

AI assistants can query domain context through the Agentic Platform MCP server:

```text
kg_domain_context(domain="<slug>")                        # Full context
kg_domain_context(domain="<slug>", aspect="slas")         # SLA requirements
kg_domain_context(domain="<slug>", aspect="integrations") # Integration specs
kg_domain_context(domain="<slug>", aspect="security")     # Security policies
kg_search(query="<task>")                                 # Semantic search
domain_get(slug="<slug>")                                 # Aggregated: metadata + repos + docs
```

Legacy KG MCP tools (`query_domain_context`, `search_business_context`) still work
if using the standalone KG MCP server (`:8131`).

### Via embedded skills (static)

The `.skills/domain-context/SKILL.md` contains embedded KG context
that works even without MCP connectivity.

## Step 6: Update domain context

When domain knowledge changes:

1. Update files in the central domain-context repo
2. Commit and push
3. In each repo, pull the update:

```bash
git submodule update --remote
git add .domain-context
git commit -m "Update domain context"
```

Or regenerate from KG:

```bash
dva domain init-context <domain-slug> --output <existing-repo-path>
```
