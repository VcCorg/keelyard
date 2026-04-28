# Agent Development Guide

Complete reference for building, managing, and deploying AI agents with `agentic-cli`.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Code Onboarding System](#code-onboarding-system)
- [CLI Command Reference](#cli-command-reference)
- [PR Reviewer Agent](#pr-reviewer-agent)
- [Agent Skills (agentskills.io)](#agent-skills)
- [OpenCode Integration](#opencode-integration)
- [MCP Server Dependencies](#mcp-server-dependencies)
- [Template System Internals](#template-system-internals)
- [File Reference](#file-reference)

---

## Architecture Overview

```
agentic-cli/
├── src/dva_agentic_cli/
│   ├── main.py                          # CLI entry point (Typer app)
│   ├── commands/
│   │   ├── code.py                      # agent code {onboard,skills,validate,config}
│   │   ├── agent.py                     # agent agent {run,start,stop,status,logs,list,register}
│   │   ├── skill.py                     # agent skill {create,list,install,show}
│   │   ├── project.py                   # agent project {create,list-templates,info}
│   │   ├── project_extensions.py        # Agent discovery, interactive run, subprocess utils
│   │   ├── init.py                      # agent init vertex-ai
│   │   ├── kg.py                        # agent kg {check,init,ingest,query,...}
│   │   ├── data.py                      # agent data {init,create,list,...}
│   │   └── mcp.py                       # agent mcp {start,stop,...}
│   ├── analyzer/
│   │   ├── detector.py                  # Project analysis (language, framework, deps, structure)
│   │   └── matcher.py                   # Skill matching against registry + MCP detection
│   └── templates/
│       ├── enums.py                     # UseCase, Framework, Tool enums
│       ├── config.py                    # TemplateConfig dataclass
│       ├── generator.py                 # TemplateGenerator orchestrator
│       └── files/
│           ├── agents.py                # Agent class templates (base + PR reviewer)
│           ├── main.py                  # main.py entry point template
│           ├── config.py                # Settings template (pydantic-settings)
│           ├── env.py                   # .env.example template
│           ├── pr_reviewer.py           # PR reviewer files (mcp_client, watcher, reviewer, pr_state)
│           ├── opencode_agent.py        # OpenCode agent markdown template
│           ├── skill.py                 # Agent Skills SKILL.md template
│           ├── tools.py                 # Tool file templates
│           └── ...                      # pyproject, readme, docker, a2a, kg_mcp, etc.
```

### How `dva project create` works

1. User runs `dva project create my-bot --use-case pr-reviewer [--jira-mcp]`
2. `commands/project.py` validates inputs, builds a `TemplateConfig` object
3. `TemplateGenerator.generate()` calls per-file generators in sequence
4. For PR reviewer, it generates: core files → PR reviewer files → OpenCode agent → Agent Skill
5. Output is a self-contained Python project ready to run

---

## Code Onboarding System

Onboard any repository with AI code assist skills — auto-detect tech stack, parse dependencies, and install matching context skills so AI tools have full project understanding from the first prompt.

### Skills Registry (`skills/`)

Skills are maintained in a **separate repository** for independent versioning and easy updates:

```
skills/
├── registry.json              # Skill index with auto_detect rules + metadata
└── skills/
    ├── java-spring-boot/SKILL.md
    ├── python-fastapi/SKILL.md
    ├── testing-junit/SKILL.md
    ├── database-spanner/SKILL.md
    ├── jira/SKILL.md            # MCP skill — uses Jira MCP tools
    ├── bitbucket/SKILL.md       # MCP skill — uses Bitbucket MCP tools
    ├── docker/SKILL.md
    └── ...
```

**`registry.json`** contains skill metadata with auto-detection rules:
- `auto_detect.files` — Match if these files exist in the project
- `auto_detect.dependencies` — Match if these deps are found in dependency files
- `mcp.server` — MCP-backed skill; only installed if the MCP server is configured

### Project Analyzer (`analyzer/`)

| Module | Purpose |
|--------|---------|
| `analyzer/detector.py` | `analyze_project()` → `ProjectAnalysis` — scans for languages, frameworks, deps, structure |
| `analyzer/matcher.py` | `match_skills()` → matched skills from registry; `detect_mcp_servers()` → configured MCPs |

**Detection pipeline**: file presence → language extensions → parse deps (pom.xml, requirements.txt, package.json, build.gradle, go.mod, pyproject.toml) → framework/test/database/API/CI rules

### Onboarding Flow

```bash
# 1. Configure registry (once)
`agent code config --registry /path/to/skills

# 2. Onboard a project
`agent code onboard --path ./my-repo          # Local path
`agent code onboard --repo <git-url>          # Clone + onboard

# 3. Manage skills post-onboard
`agent code skills list --path ./my-repo
`agent code skills add security --path ./my-repo
`agent code skills remove testing-jest --path ./my-repo
`agent code skills available --tag mcp

# 4. Validate
`agent code validate --path ./my-repo
```

**What onboard generates**:
- `.skills/project-context/SKILL.md` — Auto-generated, project-specific (tech stack, module map, deps)
- `.skills/<matched-skill>/SKILL.md` — Copied from registry for each matched skill
- `.skills/onboard.json` — Analysis results + installed/suggested skills manifest

### MCP-Backed Skills

MCP skills (jira, bitbucket, pr-reviewer) are regular skills whose `SKILL.md` references MCP tools. They are auto-installed when `dva code onboard` detects the MCP server is configured in:
- `.windsurf/mcp_config.json` (Windsurf workspace)
- `~/.codeium/windsurf/mcp_config.json` (Windsurf global)
- `~/.config/opencode/config.json` (OpenCode)

---

## CLI Command Reference

### `dva code` — Code Onboarding

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `dva code onboard` | Clone/analyze repo, install skills | `--repo`, `--path`, `--target`, `--registry` |
| `dva code skills` | Manage installed skills | `list\|available\|add\|remove\|update`, `--path`, `--tag`, `--registry` |
| `dva code validate` | Show onboarding summary | `--path`, `--registry` |
| `dva code config` | Configure settings | `--registry`, `--show` |

**Config storage**: `~/.dva/config.json` (registry path/URL). Manifest: `.skills/onboard.json` per project.

### `dva agent` — Agent Lifecycle Management

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `dva agent run` | Run agent in foreground | `--path`, `--mode {interactive,daemon,once}`, `--review-mode`, `--poll-interval` |
| `dva agent start` | Start as background daemon | `--path`, `--name`, `--review-mode`, `--poll-interval` |
| `dva agent stop` | Stop a running agent | `--name`, `--all` |
| `dva agent status` | Show all tracked agents | — |
| `dva agent logs` | View agent logs | `--name`, `--tail` |
| `dva agent list` | List agents in a project | `--path` |
| `dva agent register` | Register agent with IDE | `--path`, `--target {opencode}`, `--jira/--no-jira`, `--name` |

**State tracking**: Running agents are tracked in `~/.dva/agents/running.json`. Logs go to `<project>/logs/agent.log`.

### `dva skill` — Agent Skills (agentskills.io)

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `dva skill create <name>` | Create a new skill | `--path`, `--description`, `--template {pr-reviewer}`, `--jira` |
| `dva skill list` | List installed skills | `--path` |
| `dva skill show <name>` | Show skill details/tree | `--path` |
| `dva skill install <source>` | Install from GitHub | `--path`, `--name` |

**Install format**: `dva skill install anthropics/skills/skills/mcp-builder` (uses git sparse checkout for subdirectories).

### `dva project create` — PR Reviewer Flags

```bash
`agent project create <name> --use-case pr-reviewer [OPTIONS]

Options:
  --jira-mcp                  Enable Jira MCP integration
  --bitbucket-mcp-url URL     Override Bitbucket MCP URL (default: http://localhost:8126/sse)
  --jira-mcp-url URL          Override Jira MCP URL (default: http://localhost:8128/sse)
  --poll-interval SECONDS     PR polling interval (default: 60)
  --force                     Overwrite existing project
```

---

## PR Reviewer Agent

### Generated Project Structure

```
my-pr-bot/
├── .opencode/agent/pr-reviewer.md    # OpenCode agent definition
├── .skills/pr-reviewer/
│   ├── SKILL.md                      # Agent Skills format (cross-platform)
│   ├── scripts/                      # Future: automation scripts
│   └── reference/                    # Future: reference docs
├── src/
│   ├── main.py                       # Entry point: --mode daemon|interactive|once
│   ├── config.py                     # Settings via pydantic-settings + .env
│   ├── agents/
│   │   ├── base.py                   # BaseAgent abstract class
│   │   └── pr_reviewer_agent.py      # PRReviewerAgent (interactive + daemon modes)
│   ├── mcp_client.py                 # MCPClient + BitbucketMCP (SSE transport)
│   ├── watcher.py                    # PRWatcher (polls for new PRs, processes reviews)
│   ├── reviewer.py                   # PRReviewer (Vertex AI / Gemini code review)
│   ├── pr_state.py                   # PRStateStore (JSON file for seen PRs)
│   └── tools/                        # Tool wrappers
├── .env.example                      # Environment variables template
├── pyproject.toml                    # Dependencies (mcp, httpx, google-cloud-aiplatform, etc.)
└── Makefile                          # install-dev, run, test targets
```

### Key Components

**`mcp_client.py`** — Connects to Bitbucket/Jira MCP servers over SSE:
- `MCPClient` — Generic MCP SSE client (connect, call tool, return text)
- `BitbucketMCP` — Convenience wrapper with methods like `get_pr_overview()`, `get_pr_diff()`, etc.
- `JiraMCP` (when `--jira-mcp`) — Wrapper for Jira MCP tools

**`watcher.py`** — `PRWatcher` class:
- Polls `list_my_prs` for open PRs assigned to the user as reviewer
- Tracks seen PRs via `PRStateStore` to avoid duplicate reviews
- For each new PR: fetches overview → diff → calls `PRReviewer` → executes actions
- Review modes: `notify` (log only), `review` (post comments), `auto-approve` (post + approve)
- Optional Jira enrichment: extracts ticket key from PR title/branch, fetches issue context

**`reviewer.py`** — `PRReviewer` class:
- Uses Vertex AI (Gemini) for AI-powered code review
- Builds structured prompt with PR overview + diff
- Parses JSON response with severity-categorized findings (critical, major, minor, suggestions)
- Returns structured review: summary, findings, recommendation

**`pr_state.py`** — `PRStateStore`:
- Simple JSON file (`~/.pr_reviewer_state.json`) tracking PR IDs that have been reviewed
- Methods: `is_seen()`, `mark_seen()`, `get_count()`, `reset()`

### Configuration

Environment variables (from `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BITBUCKET_MCP_URL` | `http://localhost:8126/sse` | Bitbucket MCP server SSE URL |
| `JIRA_MCP_URL` | `http://localhost:8128/sse` | Jira MCP server SSE URL (optional) |
| `POLL_INTERVAL` | `60` | Seconds between PR polls |
| `REVIEW_MODE` | `review` | `notify`, `review`, or `auto-approve` |
| `STATE_FILE` | `~/.pr_reviewer_state.json` | Path to state persistence file |
| `AUTO_APPROVE_RULES` | (empty) | JSON rules for auto-approval criteria |
| `GCP_PROJECT_ID` | — | Google Cloud project for Vertex AI |
| `GCP_LOCATION` | `us-central1` | Vertex AI region |

---

## Agent Skills

### What Are Skills?

[Agent Skills](https://agentskills.io) is an open standard by Anthropic for packaging reusable agent capabilities. Skills are **cross-platform** — the same SKILL.md works in Claude Code, OpenCode, VS Code Copilot, and any compatible agent.

### Skill Structure

```
.skills/<skill-name>/
├── SKILL.md          # Required: YAML frontmatter + markdown instructions
├── scripts/          # Optional: executable scripts the agent can run
├── reference/        # Optional: reference documents
└── assets/           # Optional: static files
```

### SKILL.md Format

```yaml
---
name: pr-reviewer
description: >-
  Review Bitbucket pull requests with AI-powered code analysis.
  Use this skill when the user asks to review a PR, check code changes,
  post review feedback, or approve/reject pull requests.
---

# PR Reviewer Skill

Instructions for the agent...
```

### Built-in Templates

- **`pr-reviewer`** — Full PR review skill with Bitbucket MCP tools, review process, and guidelines
- **Generic** — Empty scaffold for custom skills

### Installing External Skills

```bash
# From Anthropic's skill library
`agent skill install anthropics/skills/skills/mcp-builder
`agent skill install anthropics/skills/skills/pdf

# From any GitHub repo
`agent skill install org/repo/path/to/skill
```

---

## OpenCode Integration

### How It Works

OpenCode discovers custom agents from markdown files in these directories (searched via `Glob.scan("{agent,agents}/**/*.md")`):

1. `.opencode/agent/` ← **canonical location** (used by `opencode agent create` default)
2. `.opencode/agents/`
3. `agent/`
4. `agents/`

### Agent File Format

```yaml
---
description: >-
  Use this agent when you need to review pull requests on Bitbucket.
  ...
  examples:
    - user: "Review PR #1936 in CGP/cwow-patient-query-spanner"
      assistant: "I'll fetch the PR details and diff, then provide a thorough code review."
    ...
  instructions: >-
    Always use the pr-reviewer agent for PR review tasks.
mode: primary
tools:
  bash: true
  read: true
  write: false
  edit: false
  list: true
  glob: false
  grep: true
  webfetch: false
  task: false
  todowrite: false
  todoread: false
---

# System prompt content here...
```

### Key Details

- **`opencode agent list`** only shows built-in system agents (code, explore, general, plan, summary, title)
- **Custom agents are invoked via `@agent-name`** in the TUI (e.g., `@pr-reviewer review PR #42`)
- The agent leverages MCP servers already configured in `~/.config/opencode/config.json`
- No additional MCP config needed — Bitbucket, Jira, Glean, and Gateway are already registered

### Registration

```bash
# Auto-generated during project creation
`agent project create my-bot --use-case pr-reviewer

# Manual registration for existing projects
`agent agent register --path ./my-project --target opencode
`agent agent register --path ./my-project --target opencode --jira
```

---

## MCP Server Dependencies

### Required: Bitbucket MCP

- **URL**: `http://localhost:8126/sse`
- **Source**: `/Users/your-user/agentic-project/bitbucket-server-mcp/`
- **Docker**: `docker compose -f mcp-docker-compose.yml up -d bitbucket-mcp`
- **Tools**: `get_pr_overview`, `get_pr_diff`, `get_pr_files`, `get_pr_commits`, `get_pr_comments`, `get_pr_activities`, `get_file_content`, `review_pr`, `add_pr_comment`, `add_pr_inline_comment`, `list_my_prs`
- **Auth**: Bitbucket Personal Access Token (Bearer header)
- **Endpoint**: `https://bitbucket.example.com` REST API 1.0

### Optional: Jira MCP

- **URL**: `http://localhost:8128/sse`
- **Source**: `/Users/your-user/agentic-project/jira-server-mcp/`
- **Docker**: `docker compose -f mcp-docker-compose.yml up -d jira-mcp`
- **Tools**: `get_issue`, `search_issues`, `get_my_issues`, `get_comments`, `add_comment`, `get_transitions`, `transition_issue`, `assign_issue`, `list_projects`, `get_sprint_issues`, `get_jira_config`
- **Auth**: Jira Personal Access Token (Bearer header)
- **Endpoint**: `https://jira.example.com` REST API v2

### Optional: MCP Gateway

- **URL**: `http://localhost:9090/sse`
- **Source**: `/Users/your-user/agentic-project/mcp-gateway/`
- Proxies all upstream servers, namespaces tools as `bitbucket_*`, `jira_*`, `glean_*`
- 29 total tools + `gateway_status`, `gateway_refresh`

### Starting All Services

```bash
cd /Users/your-user/agentic-project
docker compose -f mcp-docker-compose.yml up -d bitbucket-mcp jira-mcp
# Or with gateway:
docker compose -f mcp-docker-compose.yml up -d bitbucket-mcp jira-mcp mcp-gateway
```

### Client Configurations

| Client | Config File | Format |
|--------|------------|--------|
| OpenCode | `~/.config/opencode/config.json` | `"mcp": { "bitbucket": { "type": "remote", "url": "..." } }` |
| Windsurf | `.windsurf/mcp_config.json` | `"mcpServers": { "bitbucket": { "transport": "sse", "url": "..." } }` |

---

## Template System Internals

### Adding a New Use Case

1. **Add enum** in `templates/enums.py`: `UseCase.MY_AGENT = "my-agent"`
2. **Create template files** in `templates/files/my_agent.py` with generator functions
3. **Wire into `TemplateGenerator`** in `templates/generator.py`:
   - Add condition in `generate()` method
   - Add `_generate_my_agent()` method
4. **Update `project.py`** command with any new CLI flags
5. **Add agent info** in `templates/files/agents.py` for discovery metadata
6. **Optionally**: Add OpenCode agent template in `templates/files/opencode_agent.py`
7. **Optionally**: Add skill template in `templates/files/skill.py`

### Template File Pattern

Each template file follows this pattern:
```python
def get_<component>_content(config: TemplateConfig) -> str:
    """Return the file content as a string."""
    return f'''...template with {config.project_name}...'''

def generate_<component>_files(target_dir: Path, config: TemplateConfig) -> None:
    """Write files to disk."""
    content = get_<component>_content(config)
    (target_dir / "filename.py").write_text(content)
```

### Key Config Fields (TemplateConfig)

| Field | Type | Description |
|-------|------|-------------|
| `project_name` | `str` | Project directory name |
| `use_case` | `UseCase` | `PR_REVIEWER`, `RAG`, `CHATBOT`, etc. |
| `framework` | `Framework` | `ADK`, `LANGGRAPH`, `CREWAI` |
| `tools` | `list[Tool]` | Selected tools |
| `include_jira_mcp` | `bool` | Enable Jira integration |
| `bitbucket_mcp_url` | `str` | Bitbucket MCP SSE URL |
| `jira_mcp_url` | `str` | Jira MCP SSE URL |
| `poll_interval` | `int` | PR polling interval |
| `include_tests` | `bool` | Generate test files |
| `include_docker` | `bool` | Generate Docker files |
| `include_a2a` | `bool` | Agent-to-Agent protocol |

---

## File Reference

### CLI Source Files

| File | Purpose |
|------|---------|
| `commands/agent.py` | Agent lifecycle: run, start, stop, status, logs, list, register |
| `commands/skill.py` | Agent Skills: create, list, install, show |
| `commands/project.py` | Project scaffolding with PR reviewer support |
| `commands/project_extensions.py` | Agent discovery, interactive run, subprocess helpers |

### Template Files

| File | Generates |
|------|-----------|
| `templates/files/pr_reviewer.py` | `mcp_client.py`, `watcher.py`, `reviewer.py`, `pr_state.py` |
| `templates/files/agents.py` | `agents/base.py`, `agents/pr_reviewer_agent.py` |
| `templates/files/main.py` | `main.py` entry point (argparse, mode selection) |
| `templates/files/config.py` | `config.py` (pydantic Settings) |
| `templates/files/env.py` | `.env.example` |
| `templates/files/opencode_agent.py` | `.opencode/agent/pr-reviewer.md` |
| `templates/files/skill.py` | `.skills/pr-reviewer/SKILL.md` |

### Generated Project Quick Start

```bash
# Create project
`agent project create my-pr-bot --use-case pr-reviewer

# Setup
cd my-pr-bot
uv venv && source .venv/bin/activate
uv pip install -e '.'

# Configure
cp .env.example .env
# Edit .env with your GCP project ID and API keys

# Ensure MCP servers are running
docker compose -f /path/to/mcp-docker-compose.yml up -d bitbucket-mcp

# Run
python src/main.py --mode interactive    # Interactive mode
python src/main.py --mode daemon         # Background polling
python src/main.py --mode once           # Single pass

# Or via agent CLI
`agent agent run --path . --mode interactive
`agent agent start --path . --review-mode auto-approve
```
