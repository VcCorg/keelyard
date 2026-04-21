# DVA Agentic Project — Workspace

Multi-repo workspace for the DVA Agentic platform. Each component lives in its own Bitbucket repo.

## Repos

| Local Dir | Bitbucket Repo | Description |
|-----------|---------------|-------------|
| `dva-agentic-cli/` | [dva-agentic-cli](https://bitbucket.example.com/users/your-user/repos/dva-agentic-cli) | CLI tool — agent, skill, code onboard, kg, mcp, project commands |
| `dva-skills/` | [dva-agent-skills](https://bitbucket.example.com/users/your-user/repos/dva-agent-skills) | Skills registry — 26 SKILL.md files for AI code assist onboarding |
| `dva-mcp-servers/` | [dva-agent-mcp-servers](https://bitbucket.example.com/users/your-user/repos/dva-agent-mcp-servers) | MCP servers — Bitbucket, Jira, Glean, Gateway, Proxy + docker-compose |
| `dva-kg-infrastructure/` | [dva-agent-kg-infra](https://bitbucket.example.com/users/your-user/repos/dva-agent-kg-infra) | KG infra — KG MCP server, Neo4j, LightRAG, sample data, docs |

## Workspace Layout

```
dva-agentic-project/           ← This workspace (not a repo itself)
├── dva-agentic-cli/           ← Repo 1: CLI tool
├── dva-skills/                ← Repo 2: Skills registry
├── dva-mcp-servers/           ← Repo 3: MCP servers (consolidated)
├── dva-kg-infrastructure/     ← Repo 4: KG infrastructure (consolidated)
├── .windsurf/                 ← Local IDE config (not in any repo)
└── README.md                  ← This file
```

## Quick Start

```bash
# Clone all repos into workspace
mkdir dva-agentic-project && cd dva-agentic-project
git clone https://bitbucket.example.com/scm/~your-user/dva-agentic-cli.git
git clone https://bitbucket.example.com/scm/~your-user/dva-agent-skills.git dva-skills
git clone https://bitbucket.example.com/scm/~your-user/dva-agent-mcp-servers.git dva-mcp-servers
git clone https://bitbucket.example.com/scm/~your-user/dva-agent-kg-infra.git dva-kg-infrastructure

# Install CLI
cd dva-agentic-cli && uv pip install -e '.' && cd ..

# Configure skills registry
dva code config --registry ./dva-skills

# Start MCP servers
cd dva-mcp-servers && cp .env.example .env && docker compose up -d && cd ..

# Onboard any project
dva code onboard --path ./some-project
```

## Dependencies Between Repos

```
dva-agentic-cli ──uses──→ dva-skills (skills registry)
dva-agentic-cli ──uses──→ dva-mcp-servers (MCP tools for agents)
dva-agentic-cli ──uses──→ dva-kg-infrastructure (kg commands)
dva-mcp-servers ──refs──→ dva-kg-infrastructure (kg-mcp in compose)
dva-skills ────no deps────
```
