---
description: Register products and domains, link repos and docs, and wire domain context using Agentic Platform MCP
---

# Domain Management Workflow

Register products and domains, link repositories and Confluence docs,
and wire domain context across repos using the Agentic Platform MCP server.

**Related skill**: Read `skills/skills/dva-manage-domains/SKILL.md` for the full MCP tool reference.

## Prerequisites

- Agentic Platform MCP server (`agentic`) must be configured in MCP settings
- For CLI fallback, install: `pip install -e agentic-cli`

## Step 1: Register a Product

Every domain belongs to a product. Register the product first if it doesn't exist.

```text
product_create(name="CWOW", description="Clinical & Workforce Operations for the Web")
```

Check existing products:

```text
product_list()
```

## Step 2: Register a Domain

Create a domain under the product with Jira, Bitbucket, and Confluence links.

```text
domain_create(
  domain="Facility",
  product="CWOW",
  jira="CWOW",
  bb="CGF",
  confluence="MTT",
  description="Facility management domain"
)
```

The slug is auto-generated as `cwow-facility`.

## Step 3: Link Repositories

Link each repo that belongs to this domain:

```text
domain_link_repo(domain_slug="cwow-facility", repo_slug="cwow-facility-service", clone_url="https://bitbucket.example.com/...")
domain_link_repo(domain_slug="cwow-facility", repo_slug="cwow-facility-ui")
```

Verify linked repos:

```text
domain_list_repos(domain_slug="cwow-facility")
```

## Step 4: Track Confluence Docs

Add Confluence pages that contain domain requirements and specs:

```text
domain_add_doc(domain_slug="cwow-facility", page_id="847844475", space_key="CWOV", title="Release 29")
domain_add_doc(domain_slug="cwow-facility", page_id="847844500", space_key="MTT", title="Facility Data Model")
```

Verify tracked docs:

```text
domain_list_docs(domain_slug="cwow-facility")
```

## Step 5: Onboard Domain Repos

For each linked repo, run the onboarding workflow:

```text
# For each repo in domain_list_repos(domain_slug="cwow-facility"):
#   1. Detect tech stack (file scan)
#   2. Match & install skills from registry
#   3. Register centrally:
repo_register(name="cwow-facility-service", path="/path/to/cwow-facility-service", languages=["Java"], ...)
```

Or use the `/onboard-repo` workflow for each repo.

## Step 6: Enrich with Knowledge Graph (Optional)

If KG backends are running, enrich the domain with business context:

```text
# Ingest tracked docs into KG
kg_ingest(source_name="cwow-facility-docs")

# Get domain context
context = kg_domain_context(domain="cwow-facility")
```

Or use the `/kg-ingest` workflow.

## Step 7: Verify Domain Setup

Review the full domain context:

```text
domain_get(slug="cwow-facility")
```

This returns: product metadata, linked repos (with onboard status), tracked docs,
KG business context, and installed domain skills.

## CLI Fallback

If Agentic MCP is not available, use the CLI:

```bash
dva product create CWOW --description "Clinical & Workforce Operations"
dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT
dva domain link-repo cwow-facility cwow-facility-service
dva domain add-doc cwow-facility --page-id 847844475 --space CWOV --title "Release 29"
dva code onboard --path ./cwow-facility-service --domain cwow-facility
```

## Related Workflows

- `/onboard-repo` — Onboard a single repo with skills
- `/domain-context` — Set up domain context with git submodules and KG
- `/kg-ingest` — Ingest Confluence docs into the Knowledge Graph
