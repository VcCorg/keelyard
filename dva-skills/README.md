# DVA Skills Registry

Curated skills for AI code assistants. Used by `dva code onboard` to auto-detect project tech stack and install matching context skills.

## What Are Skills?

Skills are markdown files following the [Agent Skills](https://agentskills.io) open standard. Each skill provides domain-specific context, conventions, and guidelines that AI code assistants (Windsurf, Claude Code, OpenCode, VS Code Copilot) use to understand your project better.

## Structure

```
dva-skills/
├── registry.json              # Skill index with auto-detection rules
└── skills/
    ├── <skill-name>/
    │   └── SKILL.md           # Skill definition (YAML frontmatter + markdown)
    └── ...
```

## Available Skills

### Languages & Frameworks

| Skill | Description |
|-------|-------------|
| `java-spring-boot` | Spring Boot 3.x conventions, annotations, DI, REST patterns |
| `java-gradle` | Gradle build system, tasks, dependency management |
| `java-maven` | Maven POM structure, plugins, lifecycle |
| `python-fastapi` | FastAPI patterns, Pydantic models, async endpoints |
| `python-django` | Django ORM, views, migrations, REST framework |
| `python-flask` | Flask blueprints, extensions, app factory |
| `typescript-react` | React + TypeScript components, hooks, state management |
| `typescript-nextjs` | Next.js App Router, server components, API routes |
| `typescript-node` | Node.js backend, Express/Fastify, async patterns |
| `go-standard` | Go project layout, error handling, interfaces, concurrency |

### Testing

| Skill | Description |
|-------|-------------|
| `testing-junit` | JUnit 5, Mockito, Spring Boot test slices |
| `testing-pytest` | pytest fixtures, parametrize, async testing |
| `testing-jest` | Jest mocking, snapshot testing, React Testing Library |

### Databases

| Skill | Description |
|-------|-------------|
| `database-spanner` | Cloud Spanner schema, interleaved tables, mutations |
| `database-postgres` | PostgreSQL indexing, JSONB, query optimization |
| `database-mongodb` | MongoDB document design, aggregation, indexing |

### API

| Skill | Description |
|-------|-------------|
| `api-rest` | REST design, status codes, pagination, error handling |
| `api-grpc` | Protobuf definitions, streaming, error codes |

### DevOps & Cloud

| Skill | Description |
|-------|-------------|
| `docker` | Dockerfile best practices, multi-stage builds, compose |
| `ci-jenkins` | Jenkinsfile pipelines, stages, shared libraries |
| `ci-github-actions` | GitHub Actions workflows, matrix strategy |
| `gcp` | GCP services, IAM, gcloud CLI |

### MCP-Backed Skills

These skills require a running MCP server and are auto-installed when the server is detected.

| Skill | MCP Server | Description |
|-------|-----------|-------------|
| `jira` | jira | Fetch/manage Jira issues, sprints, transitions |
| `bitbucket` | bitbucket | PR operations, code review, file browsing |
| `pr-reviewer` | bitbucket | AI-powered PR code review with inline comments |

### General

| Skill | Description |
|-------|-------------|
| `security` | Secret management, auth patterns, OWASP guidelines |

## Usage with dva CLI

```bash
# Configure this registry
dva code config --registry /path/to/dva-skills

# Onboard a project (auto-detects and installs matching skills)
dva code onboard --path ./my-repo

# Browse available skills
dva code skills available
dva code skills available --tag database

# Add/remove skills manually
dva code skills add security --path ./my-repo
dva code skills remove testing-jest --path ./my-repo

# Update skills from latest registry
dva code skills update --path ./my-repo

# Validate onboarding
dva code validate --path ./my-repo
```

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
description: >-
  Brief description of what this skill provides.
  Include when/why an AI assistant should use this skill.
---

# Skill Title

## Instructions, patterns, guidelines...
```

2. Add entry to `registry.json`:

```json
{
  "name": "my-skill",
  "description": "Brief description",
  "tags": ["relevant", "tags"],
  "auto_detect": {
    "files": ["config-file-that-indicates-this-tech"],
    "dependencies": ["package-name-in-dependency-files"]
  }
}
```

3. For MCP-backed skills, use `mcp` instead of `auto_detect`:

```json
{
  "name": "my-mcp-skill",
  "description": "Uses My MCP server tools",
  "tags": ["mcp"],
  "mcp": {
    "server": "my-server",
    "required_tools": ["tool_name"],
    "config_hint": "Requires My MCP server at http://localhost:XXXX/sse"
  }
}
```

## Auto-Detection Rules

The `auto_detect` field in `registry.json` determines when a skill is automatically installed during `dva code onboard`:

- **`files`** — Skill matches if any of these files exist in the project root
- **`dependencies`** — Skill matches if any of these strings appear in parsed dependency files (pom.xml, package.json, requirements.txt, build.gradle, go.mod, pyproject.toml)

A skill matches if **either** a file or dependency rule matches.

MCP skills match only if the MCP server name is found in the user's Windsurf or OpenCode config.
