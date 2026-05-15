---
name: dva-skill-management
description: >-
  Manage AI coding skills across local registry, marketplace, and domain sources
  via DVA Central MCP. Install, resolve, validate, fork, and publish skills.
mcp_server: agentic
---

# DVA Skill Management

You have access to the Agentic Platform MCP server. Use these tools for unified
skill lifecycle management across all sources: local registry, example marketplace,
and domain-validated skills.

## Skill Resolution Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `skill_resolve` | Cascading resolution: domain → marketplace → local | `path`, `deps[]`, `files[]` |
| `skill_install` | Install a skill from any source | `path`, `skill_name`, `source?` |
| `skill_list_installed` | List skills installed in a project | `path` |
| `skill_available` | List all available skills across sources | `type?`, `category?` |
| `context_skill_gaps` | Detect gaps (installed vs available) | `path` |

## Marketplace Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `marketplace_list` | Fetch marketplace.json, list skills | `type?`, `category?` |
| `marketplace_pull` | Download .skill ZIP from GitLab Package Registry | `skill_name`, `version?` |

## Local Registry Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `registry_list` | List skills in local registry.json | — |

## Domain Skill Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `domain_skills_list` | List domain-validated skills | `domain` |
| `domain_skills_validate` | Record validation feedback | `domain`, `skill`, `feedback` |
| `domain_skills_fork` | Fork a skill for domain customization | `domain`, `skill`, `reason` |

## Skill Resolution Cascade

When `skill_resolve` is called, it checks sources in priority order:

```
1. Domain-validated skills    ← highest priority (team-approved)
2. Marketplace skills         ← enterprise-shared (marketplace.json)
3. Local registry skills      ← workspace registry (registry.json)
4. Bundled fallback           ← built-in templates (lowest)
```

A skill found at a higher tier is preferred over the same skill at a lower tier.

## Skill Sources

| Source | Location | How to Access |
|--------|----------|---------------|
| **Domain** | `<domain-context-repo>/.skills/` | `domain_skills_list(domain)` |
| **Marketplace** | `marketplace.json` → GitLab Package Registry | `marketplace_list()` |
| **Local** | `skills/registry.json` + `skills/skills/<name>/` | `registry_list()` |
| **Installed** | `<project>/.skills/<name>/SKILL.md` | `skill_list_installed(path)` |

## Typical Workflows

### Check what's installed vs available

```
installed = skill_list_installed(path="/path/to/repo")
gaps = context_skill_gaps(path="/path/to/repo")
```

### Install a specific skill from marketplace

```
marketplace_pull(skill_name="java-spring-boot", version="latest")
skill_install(path="/path/to/repo", skill_name="java-spring-boot", source="marketplace")
```

### Validate and fork a domain skill

```
# Team tried the skill and it works
domain_skills_validate(domain="cwow-facility", skill="pr-reviewer", feedback="works")

# Team needs customization
domain_skills_fork(domain="cwow-facility", skill="pr-reviewer", reason="Need domain-specific review checklist")
```

## When to Use

- User asks what skills are available or installed
- User wants to install a specific skill
- User asks about skill gaps or recommendations
- User wants to validate or customize a domain skill
- User asks to compare local vs marketplace skills
- User wants to pull the latest skills from the marketplace

## Fallback (No MCP)

If the Agentic MCP server is not running:
- Local skills: read `skills/registry.json` directly
- Marketplace: `dva skill marketplace list` (CLI)
- Domain: `dva domain list-skills <slug>` (CLI)
- Install: copy from `skills/skills/<name>/` to `<project>/.skills/<name>/`
