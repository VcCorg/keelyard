---
name: dva-onboard
description: >-
  Onboard any repository with AI coding skills using the DVA Central MCP.
  Auto-detects tech stack, resolves skills from marketplace/local/domain,
  installs them, and registers the repo centrally for tracking.
mcp_server: agentic
---

# DVA Repository Onboarding

You have access to the Agentic Platform MCP server. Use these tools to onboard repositories
with AI coding skills, track onboarding activity, and manage project context.

## Onboarding Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `repo_register` | Register repo in central tracker | `name`, `path`, `languages[]`, `skills_installed[]` |
| `registry_list` | List all skills in registry | — |
| `skill_available` | Check if a skill exists | `skill_name` |
| `activity_log` | Record onboarding activity | `command`, `subcommand`, `details` |
| `activity_summary` | Platform usage summary | — |

## Tracking Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `repo_list` | List all onboarded repos | — |
| `repo_get` | Get repo details (stack, skills) | `path` |
| `activity_recent` | Recent activity history | `limit?` |
| `activity_summary` | Aggregate stats | — |

## Onboarding Workflow

### Quick Onboard (3 calls)

```
1. skills = registry_list()                           # see what's available
2. info = skill_available(skill_name="java-spring-boot") # check specific skill
3. # Install skills via file-system (copy SKILL.md to .skills/)
```

### Full Onboard (with tracking + domain)

```
1. # Detect tech stack (file-system scan in workflow)
2. # Match and install skills (copy from registry)
3. repo_register(name="my-repo", path="/path/to/repo", languages=["Java"], skills_installed=["java-spring-boot"])
4. domain_link_repo(domain_slug="cwow-facility", repo_slug="my-repo")  # if domain known
5. activity_log(command="onboard", subcommand="install", details={"skills": 5})
```

## Skill Resolution Order

When resolving skills, the platform uses this priority cascade:

1. **Domain-validated skills** (highest) — from domain-context repo
2. **Marketplace skills** — from marketplace.json + GitLab Package Registry
3. **Local registry skills** — from skills/registry.json
4. **Bundled fallback** — built-in skill templates

## What Gets Installed

After onboarding, the project will have:

```
<repo>/
├── .skills/
│   ├── project-context/SKILL.md   ← auto-generated tech stack summary
│   ├── java-spring-boot/SKILL.md  ← matched from registry
│   ├── java-maven/SKILL.md        ← matched from registry
│   ├── docker/SKILL.md            ← matched from registry
│   ├── bitbucket/SKILL.md         ← MCP-backed skill
│   ├── domain-context/SKILL.md    ← from KG (if domain specified)
│   └── onboard.json               ← manifest with analysis + installed skills
```

## When to Use

- User asks to onboard or set up a new repository
- User wants to detect what tech stack a project uses
- User asks what skills are available or installed
- User wants to check onboarding status or history
- User asks to re-onboard or update skills for a repo

## Fallback (No MCP)

If the Agentic MCP server is not running, use the `/onboard-repo` Windsurf workflow
which performs the same steps using file system operations directly.
