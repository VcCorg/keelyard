# DVA Platform — Hybrid Distribution Plan (v2)

> **Goal**: Make all DVA CLI functionality accessible to any team member using any AI IDE,
> without requiring CLI installation, with skills flowing from local development through
> the **Example AI Artifact Marketplace** for enterprise-wide reuse.

## What Changed in v2

- **NEW Layer 0**: Example AI Artifact Marketplace — federated `marketplace.json` manifest
  system backed by GitLab Package Registry. Two consumers: web app + example-ai IDE extension
- **Skill Lifecycle**: Local → Validated → Published (via MR to agent-skills repo) → Consumed
- **Code Onboarding Revised**: Now resolves skills from marketplace.json first, local-fallback
- **New CLI commands**: `dva skill marketplace list/pull/push/sync/diff/info`
- **New workflow**: `/publish-skills` for Windsurf users
- **Publishing model**: Git-based CI (not REST API). `dva skill marketplace push` creates a
  merge request to `ai/model-context/agent-skills`. CI auto-versions + packages on merge

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                      CONSUMER LAYER (Any IDE)                        │
├──────────────┬──────────────┬───────────────┬────────────────────────┤
│   Windsurf   │    Cursor    │  Claude Code  │  VS Code / Codex       │
│  workflows/  │  .cursorrules│   CLAUDE.md   │  .agents/skills/       │
│  mcp_config  │  mcp config  │   MCP config  │  .github/copilot       │
└──────┬───────┴──────┬───────┴───────┬───────┴────────┬───────────────┘
       │              │               │                │
       ▼              ▼               ▼                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Layer 0: MARKETPLACE (marketplace.example.com)       │
│           ┌─────────────────────────────────────────────┐            │
│           │  Federated marketplace.json + GitLab Pkg Reg │            │
│           │  Source: ai/model-context/agent-skills repo   │            │
│           │  CI: merge → version → package → publish      │            │
│           │  Web app (Next.js) + example-ai IDE extension  │            │
│           └─────────────────────────────────────────────┘            │
│           Enterprise skill sharing, versioned, CI-driven             │
│           Auth: GitLab PAT + whitelisted-publishers                  │
│                                                                      │
│  Layer 1: SKILLS (.skills/*.md)           ← Universal, static        │
│           Tech stack knowledge, coding patterns, PR review            │
│           Works in ALL IDEs, zero dependencies                        │
│                                                                      │
│  Layer 2: META-SKILLS (.skills/dva-*/*.md) ← Universal, runbook      │
│           Teach AI HOW to perform onboarding tasks                    │
│           Cross-IDE, no CLI needed, AI-interpreted                    │
│                                                                      │
│  Layer 3: WORKFLOWS (.windsurf/workflows/) ← Windsurf-only           │
│           Multi-step orchestration with /slash commands                │
│           Calls MCP tools directly, deterministic steps               │
│                                                                      │
│  Layer 4: DVA MCP SERVER (dva-mcp:8132)    ← Cross-IDE, live         │
│           Wraps CLI logic as MCP tools                                │
│           Deterministic, parameterized, full power                    │
│                                                                      │
│  Layer 5: CLI (dva)                        ← Power users, CI/CD      │
│           Full Python CLI, scripting, automation                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
       │              │               │                │
       ▼              ▼               ▼                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       BACKEND SERVICES                                │
│  Bitbucket MCP :8126  │ Jira MCP :8128    │ Confluence MCP :8129      │
│  Memory MCP :8130     │ KG MCP :8131      │ Gateway :9090             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Skill Lifecycle: Local to Remote

The fundamental shift: skills are no longer just files checked into repos. They have a
**lifecycle** that flows from local authoring through validation to enterprise publishing.

```text
┌──────────┐     ┌───────────┐     ┌───────────┐     ┌──────────────┐
│  Author   │────►│  Validate  │────►│  Publish   │────►│  Marketplace │
│  (local)  │     │  (domain)  │     │  (push)    │     │  (remote)    │
└──────────┘     └───────────┘     └───────────┘     └──────┬───────┘
     ▲                                                       │
     │                        ┌──────────┐                   │
     └────────────────────────│  Consume  │◄──────────────────┘
                              │  (pull)   │
                              └──────────┘
```

### Skill States

| State | Where | Description |
| ----- | ----- | ----------- |
| **draft** | `.skills/<name>/` (local) | Author is writing/iterating |
| **validated** | `skills-manifest.json` | Tested against real tasks, feedback recorded |
| **published** | Marketplace API | Available to all teams enterprise-wide |
| **installed** | `.skills/<name>/` (consumer repo) | Pulled from marketplace into a project |
| **forked** | `.skills/<name>-domain/` | Domain-customized variant, can be re-published |

### Skill Metadata for Marketplace

Each SKILL.md gains optional marketplace metadata in its frontmatter:

```yaml
---
name: java-spring-boot
description: >-
  Spring Boot 3.x conventions, annotations, DI, REST patterns.
version: 1.2.0
author: dva-platform-team
tags: [java, spring, spring-boot, web, framework]
marketplace:
  artifact_type: skill
  category: frameworks
  visibility: organization          # organization | team | public
  auto_detect:
    files: [pom.xml, build.gradle]
    dependencies: [spring-boot-starter]
---
```

---

## Layer 0: Example AI Artifact Marketplace — NEW

### Access Points

| Medium | URL | Purpose |
| ------ | --- | ------- |
| **Web App** | `https://marketplace.example.com/` | Browser-based discovery, download, install |
| **IDE Extension** | `example-ai` VSIX (GitLab Package Registry) | In-IDE browse, install, connect to agents |
| **Raw manifest** | `gitlab.example.com/…/-/raw/master/marketplace.json` | Programmatic access for CLI/CI |

**Spec**: Confluence AISE space, page 1202192542

### How It Actually Works (Federated marketplace.json)

The marketplace is **not a REST API**. It is a **federated manifest system**:

1. Artifacts live in **GitLab source repos** (`agent-skills`, `vibe-coding-extensions`)
2. On merge to master, **CI auto-versions, packages, and uploads** to GitLab Package Registry
3. CI **regenerates `marketplace.json`** and commits it back to master
4. The **Context Marketplace web app** (Next.js / Cloud Run) aggregates `marketplace.json`
   files from multiple repos into a single browsable UI
5. The **example-ai IDE extension** reads the same `marketplace.json` files for in-IDE install

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         Source Repositories                          │
│                                                                      │
│  ┌────────────────────────────┐    ┌────────────────────────────────┐│
│  │    agent-skills repo       │    │  vibe-coding-extensions repo   ││
│  │    (ai/model-context/      │    │  (ai/model-context/            ││
│  │     agent-skills)          │    │   vibe-coding-extensions)      ││
│  │                            │    │                                ││
│  │  skills/                   │    │  extensions/                   ││
│  │    <skill-name>/           │    │    example-ai/                  ││
│  │      SKILL.md              │    │      package.json              ││
│  │      VERSION               │    │      src/ (TypeScript)         ││
│  │  whitelisted-publishers    │    │                                ││
│  │  marketplace.json ← gen'd │    │  marketplace.json ← generated ││
│  └────────────────────────────┘    └────────────────────────────────┘│
└──────────────────────────┬───────────────────────────────────────────┘
                           │  On merge to master:
                           │  CI → bump version → package → upload
                           │  → regenerate marketplace.json
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      GitLab Package Registry                         │
│                                                                      │
│  generic/skills/<skill-name>/<version>/<name>-v<ver>.skill           │
│  generic/extensions/example-ai/<name>-<version>.vsix/<file>.vsix      │
└──────────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────────┐
              ▼                             ▼
┌───────────────────────────┐  ┌────────────────────────────────────┐
│  Context Marketplace      │  │  example-ai VS Code Extension       │
│  (Next.js / Cloud Run)    │  │  (in-IDE marketplace client)       │
│                           │  │                                    │
│  • Browse all artifacts   │  │  • Browse skills, MCPs, extensions │
│  • Filter by category     │  │  • Install to global/workspace     │
│  • Download .skill ZIPs   │  │  • Connect to ACP agent runtimes   │
│  • Install to disk        │  │  • Download/install .vsix          │
│  • Tracks usage (BQ)      │  │                                    │
└───────────────────────────┘  └────────────────────────────────────┘
```

### Key Concepts

- **`marketplace.json`** — The single source of truth. Machine-readable manifest listing
  all artifacts with versions, download URLs, and metadata. Generated by CI, committed to
  master. Any tool can fetch and parse it directly.
- **GitLab Package Registry** — Where packaged artifacts (`.skill` ZIPs, `.vsix` files)
  are stored. Skills are uploaded as `generic/skills/<name>/<version>/<name>-v<ver>.skill`.
- **`whitelisted-publishers`** — Controls who can publish skills to the agent-skills repo.
- **Conventional commits** — CI uses commit messages to auto-detect which artifacts
  changed and what version bump to apply.
- **Two registries**: Example Marketplace (`marketplace.json`) for internal artifacts +
  ACP Agent Registry (`cdn.agentclientprotocol.com`) for public agent runtimes.

### Artifact Types

| Artifact Type | Source Repo | Package Format | Registry Path |
| ------------- | ----------- | -------------- | ------------- |
| **Agent Skills** | `ai/model-context/agent-skills` | `.skill` ZIP | `generic/skills/<name>/<ver>/` |
| **IDE Extensions** | `ai/model-context/vibe-coding-extensions` | `.vsix` | `generic/extensions/<name>/` |
| **MCP Servers** | (future) | TBD | TBD |
| **Agent Templates** | (future) | TBD | TBD |

### What This Enables

1. **Zero-config discovery** — any tool reads `marketplace.json` via HTTP GET, no auth for the manifest
2. **CI-driven publishing** — merge to master = auto-version + package + publish, no manual steps
3. **Two install paths** — web app (File System Access API) or IDE extension (in-IDE panel)
4. **Federated** — multiple source repos, one aggregated marketplace view
5. **Versioned** — every artifact has a `VERSION` file, CI bumps semver on merge
6. **Programmatic** — CLI, IDE extensions, and CI jobs can all fetch `marketplace.json` directly

---

## Layer 1: Skills (Static Knowledge) — ENHANCED

**What**: 60+ SKILL.md files covering Java, Python, TypeScript, databases, CI/CD, etc.

**Distribution** (REVISED — marketplace-first):

| Priority | Source | When Used |
| -------- | ------ | --------- |
| 1 | **Marketplace** (remote) | Default for all onboarding — always latest |
| 2 | **Domain-validated** (local) | Domain-specific customizations take precedence |
| 3 | **Local registry** (git) | Fallback when offline or marketplace unavailable |
| 4 | **Bundled in repo** (`.skills/`) | Already onboarded repos — use what's there |

**Existing**: `skills/registry.json` + `skills/skills/*/SKILL.md`

**Enhancement**: Each skill in `registry.json` gains a `marketplace_id` field linking to
the remote artifact.

---

## Layer 2: Meta-Skills (AI Runbooks) — NEW

Meta-skills teach the AI assistant HOW to perform platform tasks. They work without CLI,
without MCP, in any IDE.

| Meta-Skill | Replaces CLI Command | What It Teaches |
| ---------- | -------------------- | --------------- |
| `dva-onboard-repo` | `dva code onboard` | Detect tech stack, pull skills from marketplace, install |
| `dva-domain-setup` | `dva domain create` + `init-context` | Register domain, scaffold context repo |
| `dva-pr-review` | `dva agent run` (PR reviewer) | Review a PR using Bitbucket MCP tools |
| `dva-kg-query` | `dva kg query` | Query knowledge graph for business context |
| `dva-skill-manage` | `dva code skills add/remove` | Add/remove/update skills locally + push to marketplace |
| `dva-publish-skill` | `dva skill publish` | Package and publish a skill to the marketplace |

---

## Layer 3: Windsurf Workflows — EXTEND

| Workflow | Slash Command | Replaces |
| -------- | ------------- | -------- |
| `onboard-repo.md` | `/onboard-repo` | `dva code onboard` (now marketplace-aware) |
| `onboard-domain.md` | `/onboard-domain` | `scripts/onboard_domain.py` |
| `pr-review.md` | `/pr-review` | `dva agent run` (PR reviewer) |
| `kg-ingest.md` | `/kg-ingest` | `dva kg ingest submit` |
| `skill-manage.md` | `/skill-manage` | `dva code skills add/remove/list` |
| `domain-skills.md` | `/domain-skills` | `dva domain validate-skills/fork-skill` |
| `publish-skills.md` | `/publish-skills` | **NEW** — push validated skills to marketplace |

---

## Layer 4: DVA MCP Server — NEW

```text
┌──────────────────────────────────────────────────────┐
│                  dva-mcp (:8132)                      │
│                                                       │
│  Onboard Tools:                                       │
│  ├── dva_onboard_repo(path, domain?, source?)         │
│  ├── dva_detect_stack(path)                           │
│  ├── dva_list_skills(path?)                           │
│  ├── dva_add_skill(path, skill_name, source?)         │
│  ├── dva_remove_skill(path, skill_name)               │
│                                                       │
│  Marketplace Tools:               ← NEW               │
│  ├── dva_marketplace_list(type?, category?)           │
│  │     Fetches marketplace.json, filters artifacts    │
│  ├── dva_marketplace_pull(skill_name, version?)       │
│  │     Downloads .skill ZIP from GitLab Pkg Registry  │
│  ├── dva_marketplace_push(path)                       │
│  │     Commits skill to agent-skills repo → CI publishes│
│  ├── dva_marketplace_versions(skill_name)             │
│                                                       │
│  Domain Tools:                                        │
│  ├── dva_create_domain(name, product, ...)            │
│  ├── dva_domain_init_context(slug, ...)               │
│  ├── dva_domain_fetch_repos(slug)                     │
│  ├── dva_domain_list_skills(slug)                     │
│  ├── dva_domain_validate_skill(slug, skill)           │
│  ├── dva_domain_fork_skill(slug, skill)               │
│                                                       │
│  KG Tools:                                            │
│  ├── dva_kg_ingest(domain, source?)                   │
│  └── dva_kg_query(query, domain?)                     │
└──────────────────────────────────────────────────────┘
```

---

## Layer 5: CLI — ENHANCED

New CLI commands for marketplace integration:

```bash
# List skills available on marketplace (fetches marketplace.json)
dva skill marketplace list
dva skill marketplace list --type skills --category frameworks

# Pull a skill from marketplace (downloads .skill ZIP from GitLab Pkg Registry)
dva skill marketplace pull <name> --path ./my-repo
dva skill marketplace pull <name> --version 1.2.0

# Push a skill to marketplace (commits to agent-skills repo → CI auto-publishes)
dva skill marketplace push <name> \
  --repo git@gitlab.example.com:ai/model-context/agent-skills.git

# Sync local skills with marketplace
dva skill marketplace sync --direction push   # push all validated skills
dva skill marketplace sync --direction pull   # update local from marketplace

# Check what's changed in marketplace since last sync
dva skill marketplace diff --since 7d

# Show marketplace.json manifest details for a skill
dva skill marketplace info <name>
```

### Publishing Flow (How It Actually Works)

Publishing is **not a direct API call**. It follows the git-based CI pipeline:

```text
dva skill marketplace push <name>
  │
  ▼
1. Validate SKILL.md structure + VERSION file
2. Clone/fork the agent-skills repo (ai/model-context/agent-skills)
3. Copy skill to skills/<name>/ in the repo
4. Create a conventional commit: "feat(skills): add <name> v1.0.0"
5. Push branch + create merge request
6. On merge → CI auto-versions, packages .skill ZIP, uploads to
   GitLab Package Registry, regenerates marketplace.json
```

This means `dva skill marketplace push` creates a **merge request**, not an instant
publish. The actual publishing happens when the MR is merged and CI runs.

---

## Revised Code Onboarding Workflow

This is the core question: **how does `dva code onboard` change with the marketplace?**

### Before (Local-Only)

```text
dva code onboard --path ./my-repo
       │
       ▼
  1. Scan project files (pom.xml, package.json, etc.)
  2. Parse dependencies
  3. Match against LOCAL registry.json
  4. Copy SKILL.md from LOCAL skills/skills/<name>/
  5. Generate project-context SKILL.md
  6. Done — all skills are local copies
```

### After (Marketplace-First)

```text
dva code onboard --path ./my-repo [--domain <slug>] [--source marketplace|local|auto]
       │
       ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 1: DETECT TECH STACK (unchanged)                       │
  │   Scan pom.xml, package.json, pyproject.toml, go.mod, etc. │
  │   Parse dependency names                                    │
  └─────────────┬───────────────────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 2: RESOLVE SKILLS (NEW — cascading resolution)         │
  │                                                             │
  │   For each detected dependency/file:                        │
  │                                                             │
  │   2a. Check MARKETPLACE first (if online)                   │
  │       Fetch marketplace.json from agent-skills repo         │
  │       Match skills by tags, auto_detect, dependencies       │
  │       → Download .skill ZIP from GitLab Package Registry    │
  │                                                             │
  │   2b. Check DOMAIN SKILLS (if --domain provided)            │
  │       Load domain-context/.skills/ + skills-manifest.json   │
  │       → Domain-validated skills override marketplace        │
  │                                                             │
  │   2c. Fall back to LOCAL REGISTRY                           │
  │       Match against skills/registry.json                    │
  │       → Used when offline or marketplace has no match       │
  │                                                             │
  │   Resolution priority:                                      │
  │     domain-validated > marketplace > local-registry         │
  └─────────────┬───────────────────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 3: INSTALL SKILLS (enhanced)                           │
  │                                                             │
  │   For each resolved skill:                                  │
  │   a. Download SKILL.md (from marketplace URL or local path) │
  │   b. Write to .skills/<name>/SKILL.md                       │
  │   c. Write .skills/<name>/.source.json with provenance:     │
  │      {                                                      │
  │        "source": "marketplace",                             │
  │        "artifact_id": "abc-123",                            │
  │        "version": "1.2.0",                                  │
  │        "installed_at": "2026-05-11T20:30:00Z",              │
  │        "resolved_by": "auto_detect.dependencies"            │
  │      }                                                      │
  └─────────────┬───────────────────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 4: GENERATE PROJECT CONTEXT (unchanged)                │
  │   .skills/project-context/SKILL.md                          │
  └─────────────┬───────────────────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 5: MCP SKILLS (unchanged)                              │
  │   Detect MCP servers, install jira/bitbucket/kg skills      │
  └─────────────┬───────────────────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 6: WRITE LOCKFILE (NEW)                                │
  │   .skills/skills.lock.json                                  │
  │   {                                                         │
  │     "resolved_at": "2026-05-11T20:30:00Z",                 │
  │     "source_preference": "marketplace",                     │
  │     "skills": {                                             │
  │       "java-spring-boot": {                                 │
  │         "version": "1.2.0",                                 │
  │         "source": "marketplace",                            │
  │         "artifact_id": "abc-123",                           │
  │         "checksum": "sha256:..."                            │
  │       },                                                    │
  │       "pr-reviewer-cwow": {                                 │
  │         "version": "2.0.1",                                 │
  │         "source": "domain",                                 │
  │         "domain": "cwow-facility"                           │
  │       },                                                    │
  │       "database-spanner": {                                 │
  │         "version": "1.0.0",                                 │
  │         "source": "local-registry"                          │
  │       }                                                     │
  │     }                                                       │
  │   }                                                         │
  └─────────────┬───────────────────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 7: REPORT (enhanced)                                   │
  │                                                             │
  │   ┌─────────────────────────────────────────────────┐       │
  │   │ Onboarding Complete                              │       │
  │   │                                                  │       │
  │   │ Skills installed: 8                              │       │
  │   │   From marketplace:     5  (latest versions)     │       │
  │   │   From domain context:  1  (cwow-facility)       │       │
  │   │   From local registry:  2  (offline fallback)    │       │
  │   │                                                  │       │
  │   │ Lockfile: .skills/skills.lock.json               │       │
  │   │                                                  │       │
  │   │ Run `dva skill update` to check for newer        │       │
  │   │ versions from marketplace.                       │       │
  │   └─────────────────────────────────────────────────┘       │
  └─────────────────────────────────────────────────────────────┘
```

### Key Differences

| Aspect | Before (v1) | After (v2 — Marketplace) |
| ------ | ----------- | ------------------------ |
| **Skill source** | Local `skills/` directory only | Marketplace → Domain → Local (cascade) |
| **Versioning** | None (copy at point-in-time) | Semantic versions, lockfile tracks installed |
| **Updates** | Manual `dva code skills update` | `dva skill update` checks marketplace for newer |
| **Provenance** | Unknown — just a file | `.source.json` tracks where each skill came from |
| **Offline** | Always works | Falls back to local registry gracefully |
| **Publishing** | N/A | `dva skill publish` pushes to marketplace |
| **Discovery** | Browse registry.json | `dva skill search` queries marketplace API |
| **Team sharing** | Git submodule or copy | Marketplace — zero-config consumption |

---

## Publish-as-You-Work Flow

This is the push-side workflow: how skills flow **from** your team **to** the marketplace.

```text
Developer creates/improves a skill
       │
       ▼
  1. dva skill generate                    ← AI-assisted authoring
     OR edit .skills/<name>/SKILL.md       ← manual authoring
       │
       ▼
  2. dva skill validate <name>             ← lint, structure check
       │
       ▼
  3. dva domain validate-skills <slug>     ← test against real tasks
     --skill <name> --feedback works
       │
       ▼
  4. dva skill marketplace push <name>     ← create MR to agent-skills repo
       │
       ▼
  5. MR reviewed + merged                  ← team approval gate
       │
       ▼
  6. CI auto-runs:                         ← fully automated from here
     a. Detect changed skills (conventional commits)
     b. Bump VERSION (semver)
     c. Package <name>-v<ver>.skill ZIP
     d. Upload to GitLab Package Registry
     e. Regenerate marketplace.json
     f. Commit marketplace.json back to master
       │
       ▼
  7. Other teams' next `dva code onboard`
     fetches updated marketplace.json
     and picks up the new skill automatically
```

### CI/CD Integration

Publishing is **CI-native** — the `agent-skills` repo already has the pipeline. Your
team just needs to get skills *into* that repo. Two paths:

**Path A: Manual MR** — Engineer pushes directly to `ai/model-context/agent-skills`

**Path B: CLI-assisted MR** — `dva skill marketplace push` automates the MR creation

```yaml
# .gitlab-ci.yml in agent-skills repo (already exists)
# On merge to master:
#   - Detects which skills/ changed
#   - Bumps VERSION using conventional commits
#   - Packages .skill ZIP
#   - Uploads to GitLab Package Registry (generic/skills/<name>/<ver>/)
#   - Regenerates marketplace.json
#   - Commits marketplace.json to master

# For YOUR repo's CI — validate skills before pushing upstream:
stages:
  - validate

validate-skills:
  stage: validate
  script:
    - pip install agentic-cli
    - |
      for skill_dir in .skills/*/; do
        name=$(basename $skill_dir)
        dva skill validate $name --path .
      done
  rules:
    - changes:
        - ".skills/*/SKILL.md"
```

---

## Distribution Matrix (Revised)

| Capability | Marketplace (L0) | Skills (L1) | Meta-Skills (L2) | Workflows (L3) | DVA MCP (L4) | CLI (L5) |
| ---------- | :--------------: | :---------: | :--------------: | :------------: | :----------: | :------: |
| **Onboard repo** | Source of truth | Fallback | Full flow | Full flow | Deterministic | Full |
| **Domain setup** | Publish target | -- | Full flow | Full flow | Deterministic | Full |
| **PR review** | Distribute | Guidelines | Full flow | Full flow | Deterministic | Full |
| **KG ingest** | -- | -- | Instructions | Orchestrated | Deterministic | Full |
| **Skill publish** | Endpoint | -- | Instructions | Orchestrated | Deterministic | Full |
| **Skill search** | Endpoint | -- | Instructions | -- | Tool | Full |
| **Works offline** | No | Yes | Yes | Partially | No | Yes |
| **IDE support** | All (via pull) | All | All | Windsurf | All MCP | Terminal |
| **Deterministic** | Yes (API) | N/A | No | Partial | Yes | Yes |
| **Install required** | None (HTTP) | git clone | git clone | In repo | Docker | pip |

---

## Implementation Roadmap (Revised)

### Phase 1: Marketplace Client Library (Week 1)

**Effort**: Medium — Python client for marketplace.json + GitLab Package Registry
**Impact**: Foundation for everything else

1. Create `agentic_cli/marketplace/client.py`:
   - `MarketplaceClient` class:
     - `fetch_manifest(repo_url)` — HTTP GET `marketplace.json` from GitLab raw
     - `list_skills(type?, category?)` — parse manifest, filter artifacts
     - `pull_skill(name, version?)` — download `.skill` ZIP from GitLab Package Registry
     - `push_skill(name, path)` — clone agent-skills repo, add skill, create MR via GitLab API
   - Auth: GitLab personal access token (for Package Registry downloads + MR creation)
2. Create `agentic_cli/marketplace/models.py`:
   - `MarketplaceManifest`, `SkillArtifact`, `ArtifactVersion` (matching marketplace.json schema)
3. Create `agentic_cli/marketplace/config.py`:
   - Default manifest URLs: `gitlab.example.com/ai/model-context/agent-skills/-/raw/master/marketplace.json`
   - GitLab API base: `gitlab.example.com/api/v4`
4. Unit tests with mocked marketplace.json responses + mocked GitLab API

### Phase 2: CLI Marketplace Commands (Week 1-2)

**Effort**: Medium — New `dva skill` subcommands
**Impact**: Power users can publish/pull immediately

1. `dva skill marketplace list` — fetch marketplace.json, display available skills
2. `dva skill marketplace pull <name>` — download .skill ZIP, extract to `.skills/`
3. `dva skill marketplace push <name>` — create MR to agent-skills repo via GitLab API
4. `dva skill marketplace sync` — bulk push/pull based on skills.lock.json
5. `dva skill marketplace diff` — compare local lockfile against current marketplace.json
6. `dva skill marketplace info <name>` — show manifest details for a skill
7. Update `dva skill install` to check marketplace.json before GitHub

### Phase 3: Onboard Integration (Week 2)

**Effort**: Medium — Modify `dva code onboard` resolution logic
**Impact**: All onboarding now marketplace-aware

1. Add `--source marketplace|local|auto` flag to `dva code onboard`
2. Implement cascading resolution: marketplace → domain → local
3. Generate `.skills/.source.json` provenance files
4. Generate `.skills/skills.lock.json` lockfile
5. Add `dva skill update` to check lockfile against marketplace
6. Graceful offline fallback to local registry

### Phase 4: Meta-Skills + Workflows (Week 2-3)

**Effort**: Low — Markdown files updated for marketplace awareness
**Impact**: Cross-IDE access to marketplace workflows

1. Create/update 6 meta-skills (marketplace-aware instructions)
2. Create 7 Windsurf workflows (including `/publish-skills`)
3. Meta-skills reference marketplace API for skill resolution
4. Workflows include marketplace search/pull steps

### Phase 5: DVA MCP Server (Week 3-4)

**Effort**: Medium — MCP tools wrapping marketplace + CLI logic
**Impact**: Deterministic cross-IDE marketplace access

1. Create `mcp-servers/dva/` with MCP server
2. Include `dva_marketplace_search`, `dva_marketplace_pull`, `dva_marketplace_publish`
3. Include all onboard/domain/KG tools from original plan
4. Add to Docker Compose + gateway

### Phase 6: CI/CD + Team Rollout (Week 4)

**Effort**: Low-Medium — Pipeline configs + docs
**Impact**: Automated skill publishing, team adoption

1. CI pipeline template for auto-publishing skills on merge
2. IDE config templates (Windsurf, Cursor, Claude Code, VS Code, Codex)
3. Team onboarding guide
4. `/setup-ide` workflow

---

## User Experience by Persona (Revised)

### Persona A: New Developer (No CLI, No Setup)

```text
1. Clone repo → open in any IDE
2. IDE reads .skills/ → AI has full project context (skills pre-installed)
3. If .skills/ is empty:
   a. AI reads dva-onboard-repo meta-skill
   b. Detects tech stack
   c. Pulls matching skills from marketplace (HTTP, no CLI)
   d. Writes .skills/<name>/SKILL.md
4. Developer starts coding with full context
```

### Persona B: Domain Lead (Windsurf)

```text
1. /onboard-domain → guided domain setup
2. /domain-skills → validate skills against real tasks
3. /publish-skills → push validated skills to marketplace
4. Other domains auto-receive these skills on next onboard
```

### Persona C: Platform Engineer (CLI + CI)

```text
1. dva skill generate → AI-assisted skill authoring
2. dva skill validate → lint and structure check
3. dva skill publish → push to marketplace
4. CI pipeline auto-publishes on merge to main
5. dva skill sync --direction push → bulk publish
```

### Persona D: Cursor/Claude Code/Codex User

```text
1. AI reads .skills/dva-onboard-repo/SKILL.md
2. Follows instructions to detect stack
3. Pulls skills via marketplace HTTP API (no CLI needed)
4. If offline, falls back to local .skills/ or bundled skills
```

---

## File Structure (New/Modified)

```text
myAgentPG/
├── agentic-cli/src/agentic_cli/
│   ├── marketplace/                    ← NEW: marketplace client
│   │   ├── __init__.py
│   │   ├── client.py                  ← MarketplaceClient (fetch manifest/pull/push MR)
│   │   ├── models.py                  ← MarketplaceManifest, SkillArtifact models
│   │   └── config.py                  ← Manifest URLs, GitLab API config
│   └── commands/
│       └── skill.py                   ← MODIFIED: add publish/pull/search/sync
│       └── code.py                    ← MODIFIED: marketplace-first resolution
│
├── skills/
│   ├── registry.json                  ← MODIFIED: add marketplace_id per skill
│   └── skills/
│       ├── java-spring-boot/SKILL.md  ← EXISTING (now also on marketplace)
│       ├── dva-onboard-repo/SKILL.md  ← NEW meta-skill (marketplace-aware)
│       ├── dva-publish-skill/SKILL.md ← NEW meta-skill
│       └── ...
│
├── .windsurf/workflows/
│   ├── publish-skills.md              ← NEW workflow
│   ├── onboard-repo.md               ← NEW (marketplace-aware)
│   └── ...
│
├── mcp-servers/
│   └── dva/                           ← NEW MCP server (with marketplace tools)
│
├── ide-configs/                       ← NEW: shareable IDE configs
│
└── docs/plans/HYBRID_DISTRIBUTION_PLAN.md  ← THIS DOCUMENT (v2)
```

### Per-Project Structure After Onboard (NEW)

```text
<any-project>/
├── .skills/
│   ├── java-spring-boot/
│   │   ├── SKILL.md                   ← from marketplace v1.2.0
│   │   └── .source.json              ← provenance: marketplace, version, timestamp
│   ├── pr-reviewer-cwow/
│   │   ├── SKILL.md                   ← from domain (cwow-facility)
│   │   └── .source.json              ← provenance: domain, slug, version
│   ├── project-context/
│   │   └── SKILL.md                   ← auto-generated
│   └── skills.lock.json              ← lockfile: all resolved skills + versions
├── .domain-context.json               ← (if domain-linked)
└── .gitmodules                        ← (if domain submodule)
```

---

## Key Decisions (Revised)

| Decision | Recommendation | Rationale |
| -------- | -------------- | --------- |
| **Primary skill source** | marketplace.json (remote-first) | Single manifest, versioned, federated |
| **Offline fallback** | Local registry.json + bundled .skills/ | Must work disconnected from network |
| **Provenance tracking** | `.source.json` per skill | Know where each skill came from, when, which version |
| **Lockfile** | `skills.lock.json` | Reproducible installs, diff-friendly updates |
| **Publishing model** | Git MR to agent-skills repo → CI auto-publishes | Aligns with existing marketplace CI pipeline |
| **Publishing auth** | GitLab PAT + whitelisted-publishers | Same auth model as existing marketplace contributors |
| **Version strategy** | Semver via conventional commits | CI auto-bumps, consistent with marketplace |
| **Auto-publish** | CI on merge to master of agent-skills repo | Skills stay current without manual effort |
| **Resolution order** | domain-validated → marketplace → local | Domain customization wins, marketplace is default |

---

## Success Metrics (Revised)

| Metric | Target | How to Measure |
| ------ | ------ | -------------- |
| **Skills on marketplace** | 60+ (all current skills) | Marketplace artifact count |
| **Onboard pulls from marketplace** | 80%+ of skill installs | `.source.json` analysis |
| **Time to first skill** | < 30 seconds (marketplace pull) | Onboard timing logs |
| **Publish turnaround** | < 1 minute per skill | CLI timing |
| **Team adoption** | 80%+ developers | `.skills/` presence in repos |
| **Cross-domain reuse** | 5+ skills shared across 3+ domains | Marketplace download stats |
| **Stale skill rate** | < 10% | `dva skill diff` across repos |
| **Offline resilience** | 100% onboard success | Test with marketplace down |

---

## Resolved Answers (from Marketplace Spec)

| Question | Answer |
| -------- | ------ |
| **API model** | Not REST — federated `marketplace.json` manifest + GitLab Package Registry |
| **Auth for publishing** | GitLab PAT (for git push + MR creation). `whitelisted-publishers` file controls access |
| **Auth for consuming** | marketplace.json on master is readable; Package Registry may need GitLab token |
| **Artifact schema** | `marketplace.json` manifest (generated by CI). Skills have `SKILL.md` + `VERSION` file |
| **Versioning** | Semver via conventional commits. CI auto-bumps VERSION on merge |
| **Publishing trigger** | Merge to master → CI auto-packages, uploads, regenerates manifest |
| **Content format** | `.skill` ZIP (packaged by CI) in GitLab Package Registry |
| **Discovery** | Context Marketplace web app + example-ai IDE extension, both read marketplace.json |

## Remaining Open Questions

1. **marketplace.json schema** — What are the exact fields per artifact entry? Need to
   fetch the actual file to build Pydantic models
2. **whitelisted-publishers format** — How do we get our team added for publishing?
3. **GitLab Package Registry auth** — Is a GitLab PAT sufficient to download `.skill` ZIPs,
   or is there a read-only token?
4. **Skill packaging format** — What's inside a `.skill` ZIP? Just `SKILL.md` + `VERSION`,
   or additional resources (scripts/, reference/)?
5. **example-ai extension integration** — Can our DVA MCP server register as a source in
   the extension's marketplace panel?
6. **ACP Agent Registry** — Should we register DVA agents (PR reviewer, etc.) in the
   ACP registry at `cdn.agentclientprotocol.com`?

---

## Next Steps

1. ~~Get marketplace API spec~~ ✅ **Done** — spec obtained from Confluence AISE page 1202192542
2. **Fetch actual marketplace.json** — from `ai/model-context/agent-skills` repo to model the schema
3. **Get whitelisted as publisher** — request access in `whitelisted-publishers` file
4. **Phase 1**: Build marketplace.json client library (~3 days)
5. **Phase 2**: Add `dva skill marketplace` CLI subcommands (~3 days)
6. **Phase 3**: Integrate marketplace into `dva code onboard` (~3 days)
7. **Phase 4**: Create marketplace-aware meta-skills + workflows (~2 days)
8. **Phase 5**: Build DVA MCP server with marketplace tools (~1 week)
9. **Phase 6**: CI/CD pipeline + team rollout (~3 days)
10. **Bulk publish**: Push all 60+ existing skills as MRs to agent-skills repo
