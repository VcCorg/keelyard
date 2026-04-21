---
description: List, register, and manage PR reviewer agents created with dva-agentic-cli
---

# Agent Management Workflow

## Code Onboarding (dva code)

Onboard any repo with AI code assist skills — auto-detect tech stack and install matching context.

1. **Configure registry**: `dva code config --registry /path/to/dva-skills` (or git URL)
2. **Onboard a repo**: `dva code onboard --path <project-path>` or `dva code onboard --repo <git-url>`
3. **Manage skills**: `dva code skills list|available|add|remove|update --path <project-path>`
4. **Validate**: `dva code validate --path <project-path>`

Skills registry: `dva-skills/` — separate repo with `registry.json` + `skills/<name>/SKILL.md`.
MCP-backed skills (jira, bitbucket) auto-install when MCP servers are configured.

## List available agents in a project

1. Run `dva agent list --path <project-path>` to discover agents in a dva project.
2. If no path is given, default to the current working directory.

## Register an agent with OpenCode

1. Run `dva agent register --path <project-path> --target opencode` to generate the OpenCode agent definition.
2. Add `--jira` flag if the project uses Jira MCP integration.
3. The agent file is created at `<project>/.opencode/agent/pr-reviewer.md`.
4. In OpenCode TUI, use `@pr-reviewer` to invoke the agent.

## Create a new PR reviewer project with agent

1. Run `dva project create <name> --use-case pr-reviewer` to scaffold the project.
   - Add `--jira-mcp` for Jira integration.
   - Add `--bitbucket-mcp-url <url>` to override the default Bitbucket MCP URL.
2. The project auto-generates an OpenCode agent at `.opencode/agent/pr-reviewer.md`.
3. Key files:
   - `src/agents/pr_reviewer_agent.py` — Agent class (interactive + daemon modes)
   - `src/watcher.py` — Polls Bitbucket for new PRs
   - `src/reviewer.py` — AI code review via Vertex AI
   - `src/mcp_client.py` — MCP client for Bitbucket/Jira SSE
   - `src/main.py` — Entry point (`--mode daemon|interactive|once`)

## Run an agent

1. Interactive: `dva agent run --path <project-path>`
2. Background daemon: `dva agent start --path <project-path> --review-mode auto-approve`
3. Check status: `dva agent status`
4. View logs: `dva agent logs --name <agent-name>`
5. Stop: `dva agent stop --name <agent-name>`

## Agent Skills (agentskills.io)

Skills are a portable, open format that works across Claude Code, OpenCode, VS Code Copilot, and more.

1. `dva skill create <name>` — Scaffold a new custom skill
2. `dva skill create pr-reviewer --template pr-reviewer` — Use the built-in PR reviewer template
3. `dva skill list --path <project-path>` — List installed skills
4. `dva skill show <name> --path <project-path>` — Show skill details
5. `dva skill install anthropics/skills/skills/mcp-builder` — Install from GitHub
6. Skills are auto-generated at `.skills/pr-reviewer/SKILL.md` during `dva project create --use-case pr-reviewer`

## Context Bootstrapping

To get up to speed on the agent system without running multiple commands:

1. Read the skill: `dva skill show dva-agent-dev --path dva-agentic-cli`
2. Or directly read: `dva-agentic-cli/.skills/dva-agent-dev/SKILL.md`
3. Full reference: `dva-agentic-cli/docs/AGENT_DEVELOPMENT.md`

The `dva-agent-dev` skill contains all project context: architecture, commands, template system, MCP servers, OpenCode integration, and key files to read first.

## MCP servers required

- **Bitbucket MCP** (required): `http://localhost:8126/sse`
- **Jira MCP** (optional): `http://localhost:8128/sse`
- Start with: `docker compose -f mcp-docker-compose.yml up -d bitbucket-mcp jira-mcp`