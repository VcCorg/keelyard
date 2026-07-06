---
name: keel-agent-dev
description: >-
  Use this skill to quickly understand the agentic-cli agent development system.
  Read this before starting any work on agent commands, PR reviewer templates,
  OpenCode integration, Agent Skills, or MCP server configuration.
  This provides full project context so you don't need to explore the codebase from scratch.
---

# KEEL Agent Development Context

You are working on `agentic-cli`, a Python CLI tool (Typer + Rich) for scaffolding and managing AI agents. Read `docs/AGENT_DEVELOPMENT.md` for the full reference. Below is the essential context to get productive immediately.

## Project Location

- **CLI source**: `/Users/your-user/agentic-project/agentic-cli/`
- **Package**: `src/agentic_cli/`
- **Entry point**: `src/agentic_cli/main.py` → registers all Typer sub-apps
- **Installed as**: `keel` (editable install via `uv pip install -e '.'`)

## Command Groups

| Group | File | Purpose |
|-------|------|---------|
| `keel code` | `commands/code.py` | Onboard repos with AI code assist skills (onboard, skills, validate, config) |
| `keel agent` | `commands/agent.py` | Run, start/stop daemon, status, logs, list, register agents |
| `keel skill` | `commands/skill.py` | Create, list, install, show Agent Skills (agentskills.io) |
| `keel project` | `commands/project.py` | Scaffold new projects from templates |
| `keel init` | `commands/init.py` | Configure Vertex AI, auth |
| `keel kg` | `commands/kg.py` | Knowledge graph operations |
| `keel data` | `commands/data.py` | Data source management |
| `keel mcp` | `commands/mcp.py` | MCP server management |

## Code Onboarding System (keel code)

Auto-detect tech stack and install matching context skills for any repo.

- **Registry**: `skills/` — separate repo with `registry.json` + `skills/<name>/SKILL.md`
- **Analyzer**: `src/agentic_cli/analyzer/detector.py` — detects language, framework, deps, structure
- **Matcher**: `src/agentic_cli/analyzer/matcher.py` — matches analysis → registry skills + MCP detection
- **Commands**: `src/agentic_cli/commands/code.py`

### Key commands

```bash
`agent code config --registry /path/to/skills   # Set registry path (or git URL)
`agent code onboard --path <project>                 # Analyze + install skills
`agent code onboard --repo <git-url>                 # Clone + analyze + install
`agent code skills list --path <project>             # List installed skills
`agent code skills available                         # Show all skills in registry
`agent code skills available --tag mcp               # Filter by tag
`agent code skills add jira --path <project>         # Add a skill
`agent code skills remove testing-junit --path <project>  # Remove
`agent code skills update --path <project>           # Update from latest registry
`agent code validate --path <project>                # Summary report
```

### How onboarding works

1. Clone repo (if `--repo`) or use local path
2. Analyze: scan files, parse deps (pom.xml, requirements.txt, package.json, build.gradle, go.mod)
3. Match: compare analysis against `registry.json` auto_detect rules
4. MCP skills: auto-install if MCP server is configured in Windsurf/OpenCode config
5. Generate `.skills/project-context/SKILL.md` (always, project-specific)
6. Install matched skills from registry → `.skills/<name>/`
7. Save `.skills/onboard.json` manifest

## Template System

Templates live in `src/agentic_cli/templates/`:

- **`enums.py`** — `UseCase` (PR_REVIEWER, RAG, CHATBOT, etc.), `Framework` (ADK, LANGGRAPH), `Tool` enums
- **`config.py`** — `TemplateConfig` dataclass passed to all generators
- **`generator.py`** — `TemplateGenerator` orchestrates file generation; `generate()` calls per-file methods
- **`files/*.py`** — Individual file generators, each returns content strings or writes files

### Adding a new feature to templates

1. Add enum value in `enums.py` if needed
2. Create or edit template in `files/<name>.py`
3. Wire into `generator.py` with a new `_generate_*` method
4. Update `commands/project.py` for any new CLI flags

## PR Reviewer Agent (key use case)

### Template files that generate PR reviewer projects

| Template | Generates | Key Classes/Functions |
|----------|-----------|----------------------|
| `files/pr_reviewer.py` | `mcp_client.py`, `watcher.py`, `reviewer.py`, `pr_state.py` | `MCPClient`, `BitbucketMCP`, `PRWatcher`, `PRReviewer`, `PRStateStore` |
| `files/agents.py` | `agents/base.py`, `agents/pr_reviewer_agent.py` | `BaseAgent`, `PRReviewerAgent` |
| `files/main.py` | `main.py` | argparse entry point with `--mode daemon\|interactive\|once` |
| `files/config.py` | `config.py` | pydantic `Settings` class with env vars |
| `files/env.py` | `.env.example` | BITBUCKET_MCP_URL, POLL_INTERVAL, REVIEW_MODE, etc. |
| `files/opencode_agent.py` | `.opencode/agent/pr-reviewer.md` | OpenCode agent definition |
| `files/skill.py` | `.skills/pr-reviewer/SKILL.md` | Agent Skills format |

### Important template patterns

- Templates use f-strings; literal `{` in generated code must be `{{` (double-escaped)
- Jira integration is conditional on `config.include_jira_mcp`
- The `_enrich_with_jira` method in `watcher.py` had escaping bugs (regex `\d+` needs `\\d+` in f-string)

## OpenCode Integration

- Agents are markdown files with YAML frontmatter placed in `.opencode/agent/`
- OpenCode scans: `.opencode/agent/`, `.opencode/agents/`, `agent/`, `agents/` (glob `{agent,agents}/**/*.md`)
- `opencode agent list` CLI only shows built-in agents; custom agents invoked via `@agent-name`
- `@pr-reviewer` confirmed working in OpenCode TUI
- Config: `~/.config/opencode/config.json` has MCP servers under `"mcp"` key
- Binary at: `/usr/local/Cellar/opencode/1.3.0/libexec/lib/node_modules/opencode-ai/`

## Agent Skills (agentskills.io)

- Open standard by Anthropic for portable agent capabilities
- Structure: `.skills/<name>/SKILL.md` + optional `scripts/`, `reference/`, `assets/`
- Cross-platform: works in Claude Code, OpenCode, VS Code Copilot
- `keel skill install <org/repo/path>` uses git sparse checkout

## MCP Servers (Docker)

All managed via `/Users/your-user/agentic-project/mcp-docker-compose.yml`:

| Server | Port | SSE URL | Source |
|--------|------|---------|--------|
| bitbucket-mcp | 8126 | `http://localhost:8126/sse` | `bitbucket-server-mcp/` |
| glean-mcp | 8127 | `http://localhost:8127/sse` | — |
| jira-mcp | 8128 | `http://localhost:8128/sse` | `jira-server-mcp/` |
| mcp-gateway | 9090 | `http://localhost:9090/sse` | `mcp-gateway/` |

Start: `docker compose -f mcp-docker-compose.yml up -d bitbucket-mcp jira-mcp`

## Key Files to Read First

When resuming work on agent features, read these files in order:

1. `docs/AGENT_DEVELOPMENT.md` — Full reference
2. `src/agentic_cli/commands/agent.py` — Agent CLI commands
3. `src/agentic_cli/commands/skill.py` — Skill CLI commands
4. `src/agentic_cli/templates/generator.py` — Template orchestration
5. `src/agentic_cli/templates/files/pr_reviewer.py` — PR reviewer templates
6. `src/agentic_cli/templates/files/opencode_agent.py` — OpenCode integration
7. `src/agentic_cli/templates/files/skill.py` — Skill template

## Testing

```bash
cd /Users/your-user/agentic-project/agentic-cli
source .venv/bin/activate

# Verify CLI
`agent --version
`agent agent --help
`agent skill --help

# Create test project
`agent project create test-bot --use-case pr-reviewer --force
`agent agent list --path ./test-bot
`agent skill list --path ./test-bot

# With Jira
`agent project create test-bot-jira --use-case pr-reviewer --jira-mcp --force

# Clean up
rm -rf test-bot test-bot-jira
```

## Windsurf Workflow

The `/agents` workflow at `.windsurf/workflows/agents.md` documents all agent and skill commands for quick reference inside Windsurf/Cascade.
