---
description: Set up multi-repo domain context using git submodules and KG MCP
---

# Domain Context Git Reference — Onboarding Workflow

This workflow sets up shared domain context across multiple repositories
using a central domain-context repository referenced via git submodules.

## Prerequisites

- DVA CLI (`dva`) installed and on PATH
- Domain registered: `dva domain create <DOMAIN> --product <PRODUCT>`
- Repos linked: `dva domain link-repo <slug> <repo-slug>`
- (Optional) Knowledge Graph populated via `dva kg ingest`

## Step 1: Create the central domain context repository

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

## Step 2: Onboard each repo with domain context

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

## Step 3: Verify the setup

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

## Step 4: Use domain context in development

### Via MCP tools (runtime)

AI assistants can query domain context through the KG MCP server:

```
query_domain_context(domain="<slug>")          # Full context
get_domain_slas(domain="<slug>")               # SLA requirements
get_domain_integrations(domain="<slug>")       # Integration specs
get_domain_security_policies(domain="<slug>")  # Security policies
search_business_context(query="<task>")        # Semantic search
```

### Via embedded skills (static)

The `.skills/domain-context/SKILL.md` contains embedded KG context
that works even without MCP connectivity.

## Step 5: Update domain context

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
