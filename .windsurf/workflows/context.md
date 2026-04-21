---
description: Bootstrap project context — read this workspace's skills, MCP config, and architecture before starting work
---

# Context Bootstrap Workflow

When starting a new session or resuming work on the DVA Agentic Platform:

1. **Read the platform skill** for full workspace context:
   - File: `.skills/dva-agentic-platform/SKILL.md`
   - Covers: all 4 repos, 9 CLI commands, 8 MCP servers, KG infra, port map, config files

2. **Check Docker services** are running:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep dva
   ```

3. **If services are down**, start them:
   ```bash
   cd dva-mcp-servers && docker compose up -d && cd ..
   cd dva-kg-infrastructure/neo4j && docker compose up -d && cd ../..
   ```

4. **Verify CLI**:
   ```bash
   dva --version
   ```

5. **Check git status** across all repos:
   ```bash
   for d in dva-agentic-cli dva-skills dva-mcp-servers dva-kg-infrastructure; do echo "=== $d ===" && cd $d && git status --short && git log --oneline -1 && cd ..; done
   ```

## Context Files by Tool

| AI Tool | Reads | File |
|---------|-------|------|
| **Any** (agentskills.io) | `.skills/` directory | `.skills/dva-agentic-platform/SKILL.md` |
| **Windsurf** | MCP config | `.windsurf/mcp_config.json` |
| **Windsurf** | Workflows | `.windsurf/workflows/*.md` |
| **OpenCode** | Agent + MCP | `.opencode/agent/dva-platform.md` + `.opencode/mcp.json` |
| **Claude Code** | CLAUDE.md | `CLAUDE.md` |
| **Cursor** | .cursorrules | `.cursorrules` |

## Operations Guide

For detailed setup, troubleshooting, and day-to-day workflow: `docs/LOCAL_DEV_OPS_GUIDE.md`
