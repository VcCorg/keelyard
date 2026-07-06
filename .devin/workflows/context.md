---
description: Bootstrap project context — read this workspace's skills, MCP config, and architecture before starting work
---

# Context Bootstrap Workflow

When starting a new session or resuming work on the Agentic Platform:

1. **Read the platform skill** for full workspace context:
   - File: `.skills/keel-agentic-platform/SKILL.md`
   - Covers: all 4 repos, 9 CLI commands, 8 MCP servers, KG infra, port map, config files

2. **Check Docker services** are running:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep keel
   ```

3. **If services are down**, start them:
   ```bash
   cd mcp-servers && docker compose up -d && cd ..
   cd kg-infrastructure/neo4j && docker compose up -d && cd ../..
   ```

4. **Verify CLI**:
   ```bash
   agent --version
   ```

5. **Check git status** across all repos:
   ```bash
   for d in agentic-cli skills mcp-servers kg-infrastructure; do echo "=== $d ===" && cd $d && git status --short && git log --oneline -1 && cd ..; done
   ```

## Step 6: Agentic Platform MCP Context (if available)

If the Agentic Platform MCP server (`agentic`) is configured, use it for aggregated context:

```text
activity_summary()  # Platform overview: repos, domains, products
```

This returns tech stack + domain metadata + KG business context + installed skills
in one call. Use this instead of reading individual files when MCP is available.

Additional MCP queries for deeper context:

```text
repo_list()                               # All onboarded repos
domain_list()                             # All registered domains
kg_search(query="<what you need>")        # Search business context
activity_recent(limit=10)                 # Recent activity
```

## Context Files by Tool

| AI Tool | Reads | File |
|---------|-------|------|
| **Any** (agentskills.io) | `.skills/` directory | `.skills/keel-agentic-platform/SKILL.md` |
| **Any** (MCP) | Agentic Platform MCP | `activity_summary()` |
| **Windsurf** | MCP config | `.windsurf/mcp_config.json` |
| **Windsurf** | Workflows | `.windsurf/workflows/*.md` |
| **OpenCode** | Agent + MCP | `.opencode/agent/keel-platform.md` + `.opencode/mcp.json` |
| **Claude Code** | CLAUDE.md | `CLAUDE.md` |
| **Cursor** | .cursorrules | `.cursorrules` |

## Agentic MCP Meta-Skills

These skills teach AI assistants how to use Agentic Platform MCP tools:

| Skill | What It Teaches |
|-------|-----------------|
| `keel-onboard` | Repository onboarding via MCP |
| `keel-manage-domains` | Product and domain management via MCP |
| `keel-kg-context` | Knowledge Graph search and context via MCP |
| `keel-skill-management` | Skill resolution and lifecycle via MCP |

## Operations Guide

For detailed setup, troubleshooting, and day-to-day workflow: `docs/guides/LOCAL_DEV_OPS_GUIDE.md`
