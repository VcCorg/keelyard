# Agentic Platform

Read `.skills/agentic-platform/SKILL.md` for full project context before starting any work.

## Quick Reference

This is a **multi-repo workspace** with 4 repos building an enterprise AI agent platform:

- **agentic-cli/** — Python CLI (`agent` command): 9 command groups (code, kg, data, mcp, project, agent, skill, init, history)
- **skills/** — Skills registry with AI evaluation framework and team sharing via Git
- **mcp-servers/** — 8 Docker MCP servers: Bitbucket, Jira, Glean, Confluence, Memory, KG, Gateway, Proxy
- **kg-infrastructure/** — Knowledge graph: Neo4j + LightRAG + KG MCP

## MCP Servers Available

All are Docker containers on shared network. Start with `cd mcp-servers && docker compose up -d`.

| Server | Port | SSE URL | Tools |
|--------|------|---------|-------|
| bitbucket-mcp | 8126 | http://localhost:8126/sse | 15 (PR review, diff, approve, merge) |
| glean-mcp | 8127 | http://localhost:8127/sse | 6 (enterprise search) |
| jira-mcp | 8128 | http://localhost:8128/sse | 11 (issues, sprints, transitions) |
| confluence-mcp | 8129 | http://localhost:8129/sse | 10 (pages, CQL, spaces) |
| memory-mcp | 8130 | http://localhost:8130/sse | 16 (short/long-term memory, reasoning traces) |
| kg-mcp | 8131 | http://localhost:8131/sse | 8 (knowledge graph, business context) |

## Rules

- This workspace is NOT a git repo. Each subdirectory is its own repo.
- All repos are on Git under appropriate locations. Local dir names are generic for development.
- Neo4j is shared between memory-mcp and kg. All KG data is scoped with `_source='agentic_kg'`.
- MCP servers use dual transport: `stdio` for local dev, `sse` for Docker.
- Tokens live in `mcp-servers/.env` (git-ignored). Never commit secrets.
- CLI installs globally via `uv tool install --force ./agentic-cli`.
- Full operations guide: `docs/LOCAL_DEV_OPS_GUIDE.md`.
