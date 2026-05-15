---
name: dva-manage-domains
description: >-
  Manage DVA products, domains, repos, and Confluence docs via DVA Central MCP.
  Use this skill to create domains, link repositories, track docs, and wire
  domain context into projects.
mcp_server: agentic
---

# DVA Domain Management

You have access to the Agentic Platform MCP server. Use these tools to manage the
organizational hierarchy: Products → Domains → Repos → Docs.

## Product Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `product_create` | Register a product (e.g., CWOW, IMTO) | `name`, `description?`, `tags?` |
| `product_list` | List all products | — |
| `product_get` | Get product details | `name` |

## Domain Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `domain_create` | Register a domain under a product | `domain`, `product`, `jira?`, `bb?`, `confluence?`, `description?` |
| `domain_list` | List domains (optionally by product) | `product?` |
| `domain_get` | Get domain details with linked repos/docs | `name` (slug) |
| `domain_link_repo` | Link a repo to a domain | `domain`, `repo_slug`, `clone_url?` |
| `domain_unlink_repo` | Unlink a repo from a domain | `domain`, `repo_slug` |
| `domain_add_doc` | Track a Confluence doc for a domain | `domain`, `page_id`, `space_key?`, `title?` |
| `domain_list_repos` | List repos linked to a domain | `domain` |
| `domain_list_docs` | List Confluence docs tracked for a domain | `domain` |

## Domain Slug Convention

Slugs are auto-generated as `<product>-<domain>` (lowercase):
- Product: `CWOW`, Domain: `Facility` → slug: `cwow-facility`
- Product: `IMTO`, Domain: `Imaging` → slug: `imto-imaging`

## Typical Workflow: Set Up a New Domain

```
1. product_create(name="CWOW", description="Clinical & Workforce Operations for the Web")
2. domain_create(domain="Facility", product="CWOW", jira="CWOW", bb="CGF", confluence="MTT")
3. domain_link_repo(domain="cwow-facility", repo_slug="cwow-facility-service")
4. domain_link_repo(domain="cwow-facility", repo_slug="cwow-facility-ui")
5. domain_add_doc(domain="cwow-facility", page_id="847844475", space_key="CWOV", title="Release 29")
```

## Typical Workflow: Onboard Domain Repos

After setting up a domain, onboard each linked repo:

```
1. repos = domain_list_repos(domain="cwow-facility")
2. For each repo:
   a. # Detect tech stack (file-system scan)
   b. # Match & install skills from registry
   c. repo_register(name=repo.slug, path=repo.path, ...)
```

## Domain Context Integration

When a domain is linked to repos and docs, the Agentic MCP automatically:
- Auto-generate `.skills/domain-context/SKILL.md` with KG-enriched business context
- Write `.domain-context.json` with machine-readable metadata
- Link the domain-context git repo as a submodule

## When to Use

- User asks to register a new product or domain
- User wants to link repos or Confluence pages to a domain
- User asks about domain structure (which repos belong to which domain)
- User wants to set up domain context for a team
- User asks to track or manage Confluence documentation

## Fallback (No MCP)

If the Agentic MCP server is not available, use the CLI:
```bash
dva product create CWOW
dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence MTT
dva domain link-repo cwow-facility cwow-facility-service
```
