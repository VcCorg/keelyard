---
description: Onboard a repository with AI coding skills — auto-detect tech stack and install matching SKILL.md files without requiring dva CLI
---

# Repository Onboarding Workflow

Onboard any repository with AI-aware coding skills. Uses the **DVA Central MCP**
when available for centralized tracking and cascading skill resolution.
Falls back to direct file-system operations when MCP is not running.

**Related skill**: Read `skills/skills/dva-onboard/SKILL.md` for the full MCP tool reference.

## Prerequisites

Check if the Agentic Platform MCP server is available by looking for `agentic` in the
MCP server configuration (`.windsurf/mcp_config.json` or `~/.codeium/mcp_config.json`).

- **MCP available** → use Path A (MCP-first) — centralized, tracked, marketplace-aware
- **MCP not available** → use Path B (file-system) — local-only, still fully functional

---

## Path A: MCP-First Onboarding (Recommended)

When the Agentic Platform MCP server (`agentic`) is configured, use MCP tools directly.
This provides central tracking, marketplace skill resolution, and domain integration.

### Step A1: Identify Target Project

Ask the user which project to onboard. Default to current workspace root.

If the project already has `.skills/onboard.json`, ask if they want to re-onboard.

### Step A2: Detect & Resolve (2 MCP calls)

```text
analysis = repo_register(path="<project-path>")
skills   = registry_list(path="<project-path>", deps=analysis.dependencies, files=analysis.project_files)
```

`repo_register` returns: languages, frameworks, build tools, dependencies, databases,
CI/CD, Docker status, module structure, entry points.

`registry_list` uses the priority cascade:
1. Domain-validated skills (if domain specified)
2. Marketplace skills (marketplace.json)
3. Local registry skills (registry.json)
4. Bundled fallback

### Step A3: Install Skills (1 MCP call)

```text
result = skill_available(path="<project-path>", skills=skills.matched)
```

This installs all matched skills to `.skills/`, generates `project-context/SKILL.md`,
and writes `onboard.json`.

### Step A4: Register Centrally (1 MCP call)

```text
repo_register(
  name="<project-name>",
  path="<project-path>",
  analysis=analysis,
  skills=result.installed
)
```

This records the onboarding in the central tracker (`tracker.db`) so it's visible
to the team via `repo_list` or `dva history repos`.

### Step A5: Domain Context (Optional — 2 MCP calls)

If the user specifies a domain:

```text
domain_link_repo(domain="<domain-slug>", repo_slug="<project-name>")
context = kg_domain_context(domain="<domain-slug>")
```

This links the repo to the domain and enriches it with KG business context,
generating `.skills/domain-context/SKILL.md`.

### Step A6: Full Context Check (Optional — 1 MCP call)

```text
full = context_full(path="<project-path>")
```

Returns the aggregated context: tech stack + domain + KG + installed skills.
Use this to verify everything was wired correctly.

### Step A7: Report Results

Display a summary showing detected stack, installed skills (with source), and next steps.

```text
✓ Project Onboarded: <project-name>  [tracked centrally]

  Language:    Java, Python
  Framework:   Spring Boot
  Build Tool:  Maven
  Docker:      Yes
  CI/CD:       Jenkins

  Skills Installed: 9
    ✓ project-context       (auto-generated)
    ✓ java-spring-boot      (marketplace — v2.1.0)
    ✓ java-maven            (local registry)
    ✓ python-fastapi        (marketplace — v1.3.0)
    ✓ database-postgres     (local registry)
    ✓ docker                (local registry)
    ✓ ci-jenkins            (local registry)
    ✓ bitbucket             (MCP server configured)
    ✓ domain-context        (KG — cwow-facility)

  Suggested:
    • testing-junit         — Related tags: java
    • api-rest              — Related tags: spring, web

  Next Steps:
    1. Review: ls .skills/*/SKILL.md
    2. Domain context: /domain-context workflow
    3. Check gaps: context_skill_gaps(path="<project-path>")
    4. KG search: kg_search(query="<your question>")
```

---

## Path B: File-System Fallback

When the Agentic Platform MCP is not available, fall back to direct file operations.
This mode is fully functional but does NOT track centrally or resolve from marketplace.

### Step B1: Identify Target Project

Same as Step A1.

### Step B2: Detect Tech Stack

Scan the project root for build/config files:

| File | Language | Build Tool |
|------|----------|------------|
| `pom.xml` | Java | Maven |
| `build.gradle` / `build.gradle.kts` | Java | Gradle |
| `package.json` | JavaScript/TypeScript | npm/yarn |
| `tsconfig.json` | TypeScript | tsc |
| `requirements.txt` | Python | pip |
| `pyproject.toml` | Python | pip/poetry/hatch |
| `go.mod` | Go | go modules |
| `Cargo.toml` | Rust | cargo |
| `Dockerfile` / `docker-compose.yml` | — | Docker |
| `Jenkinsfile` | — | Jenkins CI |
| `.github/workflows/` | — | GitHub Actions |
| `.gitlab-ci.yml` | — | GitLab CI |

Scan file extensions (up to 500 files, skip `node_modules/`, `.venv/`, `target/`, `build/`, `.git/`):

- `.java` → Java, `.py` → Python, `.ts/.tsx` → TypeScript, `.js/.jsx` → JavaScript
- `.go` → Go, `.rs` → Rust, `.kt/.kts` → Kotlin, `.cs` → C#, `.rb` → Ruby

### Step B3: Parse Dependencies

- **Python**: `requirements.txt` (before `==`/`>=`), `pyproject.toml` (`[project.dependencies]`)
- **JavaScript**: `package.json` (`dependencies` + `devDependencies` keys)
- **Java**: `pom.xml` (`<artifactId>` in `<dependencies>`), `build.gradle` (`implementation` blocks)
- **Go**: `go.mod` (`require` block), **Rust**: `Cargo.toml` (`[dependencies]` keys)

### Step B4: Match Skills from Registry

Load `skills/registry.json` (local) or `.skills/dva/registry.json` (submodule).

For each skill:
- **MCP skills** (`"mcp"` field): match if server is in `.windsurf/mcp_config.json`
- **Auto-detect skills**: match if `files` or `dependencies` or `dependencies_all` match
- A skill matches if EITHER a file or dependency match is found

### Step B5: Install Matched Skills

For each matched skill:
1. Copy from `skills/skills/<skill-name>/` to `<project>/.skills/<skill-name>/`
2. Generate `.skills/project-context/SKILL.md` from analysis
3. Write `.skills/onboard.json` manifest

### Step B6: Report Results

Same format as Step A7 but without `[tracked centrally]` and without marketplace sources.

---

## Workflow Selection Logic

```text
IF "agentic" in MCP servers config:
  → Path A (MCP-first): detect → resolve → install → register → domain → report
ELSE:
  → Path B (file-system): scan files → parse deps → match registry → copy skills → report
```

Both paths produce the same output (`.skills/` directory + `onboard.json`).
Path A additionally provides: central tracking, marketplace resolution, domain/KG integration.

## Related Workflows

- `/domain-context` — Set up domain context with KG integration
- `/manage-domain` — Register products, domains, and link repos
- `/kg-ingest` — Ingest Confluence docs into the Knowledge Graph
- `/context` — Bootstrap full project context

## Related Skills

- `dva-onboard` — MCP tool reference for onboarding
- `dva-skill-management` — Skill resolution and management
- `dva-kg-context` — KG search and domain context
- `dva-manage-domains` — Domain and product management
