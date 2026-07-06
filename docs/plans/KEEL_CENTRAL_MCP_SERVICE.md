# KEEL Central MCP Service — Architecture Design

> **Goal**: Consolidate all KEEL platform capabilities — domain management, project tracking,
> code onboarding, skill management, and KG context — into a single central MCP service
> that any IDE can consume through workflows and skills, preserving the original CLI intent.

## The Problem

Today KEEL has **fragmented state and access**:

```text
┌──────────────────────────────────────────────────────────────────┐
│                     CURRENT STATE (Fragmented)                    │
│                                                                  │
│  Developer A (CLI user)         Developer B (IDE-only)           │
│  ~/.agent-cli-agentic/          Has no access to:                │
│    tracker.db ← local SQLite      - Domain registry              │
│    ├── activity_log                - Onboarded repos              │
│    ├── repos                       - Project tracking             │
│    ├── projects                    - Skill proposals              │
│    ├── products                    - Activity history             │
│    ├── domains                     - KG source registry           │
│    ├── domain_repos                                               │
│    └── domain_docs              Can only use:                     │
│                                   - .skills/ files (static)      │
│  KG MCP (port 8131)               - Windsurf workflows           │
│    ├── LightRAG                    - Anchor MCP (Bitbucket/etc)   │
│    └── Neo4j                                                      │
│    (separate, no link to tracker)                                 │
│                                                                  │
│  Skills Registry                                                  │
│    skills/registry.json ← local   Marketplace                    │
│    No sync with marketplace        marketplace.json ← remote     │
│                                    No sync with local             │
└──────────────────────────────────────────────────────────────────┘
```

**What's broken**:
1. **Tracker is local** — `~/.agent-cli-agentic/tracker.db` is per-developer SQLite. No team visibility.
2. **KG MCP is isolated** — has domain tools but no access to the tracker's domain/project registry.
3. **Skills are disconnected** — local registry.json, marketplace.json, and domain skills are three separate systems.
4. **Workflows can't track** — the `/onboard-repo` workflow installs skills but can't record to the central tracker.
5. **No IDE path to domain management** — creating domains, linking repos requires CLI.

---

## The Solution: KEEL Central MCP

One MCP server that **wraps the tracker.py data model**, **integrates the KG**, and **bridges the marketplace** — making every KEEL capability accessible from any IDE.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                      PROPOSED STATE (Centralized)                        │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Windsurf │  │  Cursor  │  │  Claude  │  │ VS Code  │               │
│  │workflows │  │.cursor   │  │CLAUDE.md │  │example-ai │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │              │                     │
│       ▼              ▼              ▼              ▼                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   KEEL CENTRAL MCP (:8132)                        │   │
│  │                                                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │   │
│  │  │  Domain & Track  │  │  Skills & Market │  │  KG & Context   │ │   │
│  │  │                  │  │                  │  │                  │ │   │
│  │  │ keel_product_*    │  │ keel_skill_*      │  │ keel_kg_*        │ │   │
│  │  │ keel_domain_*     │  │ keel_marketplace_*│  │ keel_context_*   │ │   │
│  │  │ keel_onboard_*    │  │ keel_registry_*   │  │ keel_ingest_*    │ │   │
│  │  │ keel_project_*    │  │                  │  │                  │ │   │
│  │  │ keel_activity_*   │  │                  │  │                  │ │   │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │   │
│  │           │                     │                     │           │   │
│  └───────────┼─────────────────────┼─────────────────────┼───────────┘   │
│              │                     │                     │               │
│              ▼                     ▼                     ▼               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  SQLite Tracker   │  │  marketplace.json │  │  Neo4j + LightRAG│      │
│  │  (shared volume)  │  │  + GitLab Pkg Reg │  │  (existing KG)   │      │
│  │                   │  │  + local registry  │  │                  │      │
│  │  products         │  │                    │  │  Entities        │      │
│  │  domains          │  │  Federated skill   │  │  Business rules  │      │
│  │  repos            │  │  resolution:       │  │  Domain context  │      │
│  │  projects         │  │  domain → market   │  │                  │      │
│  │  activity_log     │  │  → local → bundled │  │                  │      │
│  │  domain_repos     │  │                    │  │                  │      │
│  │  domain_docs      │  │                    │  │                  │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Backend** | Same SQLite `tracker.db` | Zero migration, CLI and MCP share the same data |
| **KG integration** | Absorb KG MCP into KEEL MCP | One server instead of two, shared domain context |
| **Transport** | SSE (Docker) + stdio (local) | Same pattern as existing KG MCP |
| **Port** | `:8132` | Next available in the stack |
| **Auth** | None (local network) | Same as existing MCP servers |
| **Skills resolution** | Cascade: domain → marketplace → local → bundled | Unified, not three separate paths |

---

## Tool Catalog

### Group 1: Domain & Product Management

These replace `keel product *` and `keel domain *` CLI commands.

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `keel_product_create` | `name, description?, tags?` | Register a product (e.g., CWOW) |
| `keel_product_list` | — | List all products |
| `keel_product_get` | `name` | Get product details |
| `keel_domain_create` | `domain, product, jira?, bb?, confluence?` | Register a domain under a product |
| `keel_domain_list` | `product?` | List domains, optionally by product |
| `keel_domain_get` | `name` | Get domain details with linked repos/docs |
| `keel_domain_link_repo` | `domain, repo_slug, clone_url?` | Link a repo to a domain |
| `keel_domain_unlink_repo` | `domain, repo_slug` | Unlink a repo |
| `keel_domain_add_doc` | `domain, page_id, space_key?, title?` | Track a Confluence doc for a domain |
| `keel_domain_list_repos` | `domain` | List repos linked to a domain |
| `keel_domain_list_docs` | `domain` | List Confluence docs tracked for a domain |

### Group 2: Code Onboarding & Project Tracking

These replace `keel code onboard`, `keel project *`, and `keel history *`.

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `keel_onboard_detect` | `path` | Analyze project: languages, frameworks, deps, build tools |
| `keel_onboard_match` | `path, analysis` | Match skills from registry for a project analysis |
| `keel_onboard_install` | `path, skills[]` | Install matched skills into `.skills/` |
| `keel_onboard_register` | `name, path, analysis, skills[]` | Register onboarded repo in central tracker |
| `keel_project_create` | `name, path, use_case?, framework?` | Register an agent project |
| `keel_project_list` | — | List all registered projects |
| `keel_project_get` | `name` | Get project details |
| `keel_activity_log` | `command?, limit?, since?` | Query activity history |
| `keel_activity_summary` | — | Aggregate stats (total actions, errors, commands) |
| `keel_repos_list` | `name?` | List onboarded repos |
| `keel_repos_get` | `path` | Get repo details (tech stack, skills, etc.) |

### Group 3: Skill Management

Unified skill resolution across all sources.

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `keel_skill_resolve` | `path, deps[], files[]` | Cascading resolution: domain → marketplace → local |
| `keel_skill_list_installed` | `path` | List skills installed in a project |
| `keel_skill_install` | `path, skill_name, source?` | Install a skill (source: marketplace\|local\|domain) |
| `keel_skill_available` | `type?, category?` | List available skills across all sources |
| `keel_marketplace_list` | `type?, category?` | Fetch marketplace.json, list skills |
| `keel_marketplace_pull` | `skill_name, version?` | Download .skill ZIP from GitLab Package Registry |
| `keel_registry_list` | — | List skills in local registry.json |
| `keel_domain_skills_list` | `domain` | List domain-validated skills |
| `keel_domain_skills_validate` | `domain, skill, feedback` | Record validation feedback |
| `keel_domain_skills_fork` | `domain, skill, reason` | Fork a skill for domain customization |

### Group 4: Knowledge Graph & Context (absorbed from KG MCP)

All existing KG MCP tools, now co-located with domain/project context.

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `keel_kg_search` | `query, project?, limit?` | Search business context (LightRAG + Neo4j) |
| `keel_kg_project_context` | `project` | Get project overview from KG |
| `keel_kg_domain_context` | `domain, aspect?` | Get domain context (SLAs, integrations, security) |
| `keel_kg_query` | `query, provider?` | Raw KG query (lightrag/neo4j) |
| `keel_kg_entity` | `entity_name` | Get entity details from Neo4j |
| `keel_kg_ingest` | `source_name, extract_entities?` | Ingest registered source into KG |
| `keel_kg_sources` | — | List registered knowledge sources |
| `keel_kg_projects` | — | List knowledge projects |

### Group 5: Context Aggregation (NEW)

Cross-cutting tools that combine tracker + KG + skills into unified context.

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `keel_context_full` | `path` | Full context for a repo: tech stack + domain + KG + skills |
| `keel_context_domain` | `domain` | Full domain context: metadata + repos + docs + KG + skills |
| `keel_context_onboard_plan` | `path, domain?` | Generate an onboarding plan for a new repo |
| `keel_context_skill_gaps` | `path` | Detect skill gaps (installed vs available vs marketplace) |

---

## How Workflows Change

### Before: Workflow → File system only

```text
/onboard-repo
  1. Scan files           → read file system
  2. Match skills         → read registry.json
  3. Install skills       → copy to .skills/
  4. Generate manifest    → write onboard.json
  5. ❌ No central tracking
  6. ❌ No domain awareness
  7. ❌ No marketplace resolution
```

### After: Workflow → KEEL Central MCP

```text
/onboard-repo
  1. keel_onboard_detect(path)        → MCP returns analysis JSON
  2. keel_skill_resolve(path, ...)    → MCP cascades: domain → marketplace → local
  3. keel_onboard_install(path, [...])→ MCP installs skills + writes manifest
  4. keel_onboard_register(...)       → MCP records to central tracker
  5. keel_context_full(path)          → MCP returns combined context
```

The workflow becomes **thinner** — it orchestrates MCP tool calls instead of reimplementing
detection and matching logic. The MCP server holds the logic, the workflow holds the UX.

### Updated `/onboard-repo` Workflow (with KEEL MCP)

```markdown
## Step 1: Detect Tech Stack
Call `keel_onboard_detect` with the project path.
The MCP server analyzes the project and returns structured analysis.

## Step 2: Resolve Skills
Call `keel_skill_resolve` with the detected deps and files.
The MCP server resolves skills using cascade: domain → marketplace → local.

## Step 3: Install Skills
Call `keel_onboard_install` with the path and resolved skill list.
The MCP server copies skills to .skills/ and generates project-context.

## Step 4: Register Centrally
Call `keel_onboard_register` with the project details.
The MCP server records the onboarding in the central tracker (tracker.db).

## Step 5: Attach Domain Context (optional)
If a domain is known, call `keel_kg_domain_context` to enrich with KG.
Call `keel_domain_link_repo` to link the repo to the domain.

## Step 6: Report Results
Display the analysis, installed skills, and suggested next steps.
```

---

## How This Preserves CLI Intent

The KEEL MCP server **does not replace the CLI**. It wraps the same Python modules:

```text
┌────────────────────────────────────────────────────────────────┐
│                    SHARED PYTHON MODULES                        │
│                                                                │
│  agentic_cli/                                                  │
│  ├── tracker.py           ← SQLite CRUD                       │
│  ├── analyzer/                                                 │
│  │   ├── detector.py      ← analyze_project()                 │
│  │   └── matcher.py       ← match_skills(), load_registry()   │
│  ├── marketplace/                                              │
│  │   ├── client.py        ← fetch_manifest(), pull_skill()    │
│  │   └── models.py        ← MarketplaceManifest               │
│  ├── kg/                                                       │
│  │   ├── lightrag_client  ← LightRAG queries                  │
│  │   ├── neo4j_client     ← Neo4j queries                     │
│  │   ├── domain_context   ← domain KG context                 │
│  │   ├── domain_skills    ← domain skill management           │
│  │   └── context_builder  ← KG context pipeline               │
│  └── skill_generator.py   ← domain persona skills             │
│                                                                │
│              ┌──────────┐          ┌──────────┐               │
│              │  CLI      │          │ KEEL MCP  │               │
│              │ (typer)   │          │ (FastMCP)│               │
│              │           │          │          │               │
│              │ keel code  │          │ Tools    │               │
│              │ keel domain│   ══════ │ wrap the │               │
│              │ keel skill │  same    │ same     │               │
│              │ keel kg    │  modules │ modules  │               │
│              │ keel project│         │          │               │
│              └──────────┘          └──────────┘               │
│                   │                      │                     │
│                   ▼                      ▼                     │
│              ┌──────────────────────────────────┐             │
│              │    tracker.db (shared SQLite)      │             │
│              │    Neo4j + LightRAG (shared KG)    │             │
│              │    registry.json (shared skills)    │             │
│              │    marketplace.json (remote)         │             │
│              └──────────────────────────────────┘             │
└────────────────────────────────────────────────────────────────┘
```

**CLI** → for power users, CI/CD, scripts, terminal workflows
**KEEL MCP** → for IDE users via workflows, skills, and AI assistants

Both read/write the same `tracker.db`. A domain created via CLI is immediately
visible via MCP. An onboarding done via workflow is tracked in the same activity log.

---

## KG MCP Absorption

Today: two separate MCP servers
- `kg-mcp` (:8131) — KG search, domain context, ingest
- `keel-mcp` (:8132) — proposed new KEEL tools

**Proposal**: Absorb `kg-mcp` into `keel-mcp`:

| Reason | Detail |
|--------|--------|
| **Shared domain model** | KG domain tools need tracker's domain registry. Today they're disconnected. |
| **Fewer containers** | One server instead of two. Simpler docker-compose. |
| **Unified namespace** | `keel_kg_search` instead of separate `search_business_context` tool |
| **Shared context** | `keel_context_full` can combine tracker + KG in one call |

The KG Python clients (`lightrag_client.py`, `neo4j_client.py`) would be imported directly
into the KEEL MCP server, same as the CLI does today.

**Migration path**:
1. Phase 1: KEEL MCP launches with tracker tools only. KG MCP runs separately.
2. Phase 2: KEEL MCP absorbs KG tools. KG MCP container deprecated.
3. Phase 3: Gateway routes `keel_kg_*` tools to KEEL MCP.

---

## Docker Integration

```yaml
# mcp-servers/docker-compose.yml — new service
keel-mcp:
  build:
    context: ./keel
    dockerfile: Dockerfile
  container_name: keel-mcp
  ports:
    - "8132:8132"
  environment:
    MCP_TRANSPORT: sse
    MCP_PORT: 8132
    # Tracker DB is volume-mounted for CLI ↔ MCP sharing
    KEEL_TRACKER_DB: /data/tracker.db
    # KG backends (Phase 2)
    NEO4J_URI: bolt://neo4j:7687
    LIGHTRAG_URL: http://lightrag:9621
    # Marketplace
    MARKETPLACE_MANIFEST_URL: https://gitlab.example.com/ai/model-context/agent-skills/-/raw/master/marketplace.json
    GITLAB_TOKEN: ${GITLAB_TOKEN}
    # Skills registry
    SKILLS_REGISTRY_PATH: /skills/registry.json
  volumes:
    - keel-data:/data                    # tracker.db persistence
    - ../skills:/skills:ro              # local skills registry (read-only)
  networks:
    - mcp-net

volumes:
  keel-data:
```

The key insight: `tracker.db` is mounted as a Docker volume. The CLI writes to
`~/.agent-cli-agentic/tracker.db` locally; the MCP server writes to `/data/tracker.db`
in Docker. To share state, either:

**Option A**: Symlink `~/.agent-cli-agentic/tracker.db` → Docker volume mount
**Option B**: CLI reads `KEEL_TRACKER_DB` env var to point at the shared location
**Option C**: KEEL MCP server exposes read/write tools; CLI delegates to MCP when Docker is running

Recommendation: **Option B** — add `KEEL_TRACKER_DB` env var support to `tracker.py`.
This is a one-line change to the existing `DB_PATH` initialization.

---

## Skills Distribution via Workflows

The original ask: can the KG module and other KEEL features use the same workflow/skill
distribution mechanism? **Yes** — here's how:

### Skills as Runbooks for KEEL Features

Each KEEL capability gets a **meta-skill** (a SKILL.md file) that teaches the AI how to
use the corresponding MCP tools:

```text
.skills/
├── keel-onboard-repo/SKILL.md       ← teaches AI to use keel_onboard_* tools
├── keel-manage-domains/SKILL.md     ← teaches AI to use keel_domain_* tools
├── keel-manage-skills/SKILL.md      ← teaches AI to use keel_skill_* tools
├── keel-kg-search/SKILL.md          ← teaches AI to use keel_kg_* tools
├── keel-context-bootstrap/SKILL.md  ← teaches AI to use keel_context_* tools
├── keel-publish-skill/SKILL.md      ← teaches AI marketplace push workflow
```

### Workflows as Orchestrators for KEEL Features

Each KEEL workflow calls MCP tools in sequence:

```text
.windsurf/workflows/
├── onboard-repo.md          ← keel_onboard_* + keel_skill_resolve
├── domain-context.md        ← keel_domain_* + keel_kg_domain_context
├── context.md               ← keel_context_full
├── publish-skills.md        ← keel_marketplace_push + keel_skill_validate
├── kg-ingest.md     (NEW)   ← keel_kg_ingest + keel_domain_add_doc
├── manage-domain.md (NEW)   ← keel_domain_create + keel_domain_link_repo
```

### Same Distribution for KG Module

The KG module capabilities become skills + workflows:

| KG Capability | Meta-Skill | Workflow | MCP Tool |
|---------------|------------|----------|----------|
| Search context | `keel-kg-search` | — (inline) | `keel_kg_search` |
| Domain context | `keel-kg-domain` | `/domain-context` | `keel_kg_domain_context` |
| Ingest docs | `keel-kg-ingest` | `/kg-ingest` (NEW) | `keel_kg_ingest` |
| Entity lookup | — | — | `keel_kg_entity` |
| Project context | `keel-context-bootstrap` | `/context` | `keel_kg_project_context` |

The pattern is consistent:
- **Skill** = static runbook (works in any IDE, no MCP required)
- **Workflow** = Windsurf-specific orchestration (calls MCP tools)
- **MCP Tool** = deterministic, parameterized operation (works in any MCP client)

---

## Implementation Roadmap

### Phase 1: KEEL MCP Core (Week 1-2)

Create the MCP server with tracker tools:

```text
mcp-servers/keel/
├── Dockerfile
├── pyproject.toml
└── src/keel_mcp/
    ├── server.py           ← FastMCP server + tool definitions
    ├── tracker_tools.py    ← Domain, product, repo, project, activity tools
    ├── onboard_tools.py    ← Detect, match, install, register tools
    └── config.py           ← KEEL MCP configuration
```

Dependencies: `agentic_cli` (imported as library for tracker.py, analyzer, matcher)

### Phase 2: Skills Resolution (Week 2-3)

Add skill management tools:

```text
└── src/keel_mcp/
    ├── skill_tools.py      ← Unified skill resolution
    └── marketplace_tools.py ← marketplace.json fetch + GitLab Pkg Registry
```

### Phase 3: KG Absorption (Week 3-4)

Absorb KG MCP tools into KEEL MCP:

```text
└── src/keel_mcp/
    ├── kg_tools.py         ← Moved from kg-mcp/server.py
    └── context_tools.py    ← Cross-cutting aggregation tools
```

Deprecate standalone `kg-mcp` container.

### Phase 4: Workflows + Meta-Skills (Week 4)

Create/update:
- Meta-skills: `keel-onboard-repo`, `keel-manage-domains`, `keel-kg-search`
- Workflows: update `/onboard-repo`, create `/manage-domain`, `/kg-ingest`
- Publish all to marketplace

### Phase 5: CLI Integration (Week 4-5)

- Add `KEEL_TRACKER_DB` env var to `tracker.py`
- CLI auto-detects if KEEL MCP is running; delegates where possible
- `keel status` command shows MCP server status + tracker summary

---

## Port Map (Updated)

| Service | Port | Status |
|---------|------|--------|
| Bitbucket MCP | 8126 | Existing |
| Glean MCP | 8127 | Existing |
| Jira MCP | 8128 | Existing |
| Confluence MCP | 8129 | Existing |
| Memory MCP | 8130 | Existing |
| KG MCP | 8131 | Existing → absorbed into KEEL MCP in Phase 3 |
| **KEEL Central MCP** | **8132** | **NEW** |
| MCP Gateway | 9090 | Existing (routes to all above) |

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Central tracking adoption** | 100% of onboardings tracked | `keel_activity_log` query |
| **Workflow→MCP migration** | All workflows use MCP tools | Workflow file audit |
| **IDE-only onboarding** | Possible without CLI | Test with new developer |
| **Domain operations via IDE** | Create domain, link repos | Test via Windsurf workflow |
| **KG queries via KEEL MCP** | All KG tools accessible | Tool catalog parity check |
| **CLI ↔ MCP data sharing** | tracker.db shared | Cross-verify: CLI create → MCP read |
| **Skill resolution cascade** | domain → marketplace → local | `keel_skill_resolve` test |

---

## Open Questions

1. **SQLite concurrency** — Can CLI and KEEL MCP write to the same `tracker.db` simultaneously?
   SQLite supports WAL mode for concurrent reads. Write contention is low (seconds apart).
   Mitigation: use WAL mode + retry logic.

2. **Docker volume sharing** — How to share `tracker.db` between host CLI and Docker container?
   Options: bind mount, symlink, or KEEL MCP as the single writer (CLI delegates).

3. **Gateway routing** — Should KEEL MCP register through the existing MCP gateway (:9090)?
   Recommended: yes, so all IDEs get KEEL tools through one SSE endpoint.

4. **Marketplace auth in Docker** — GitLab token needs to be injected as env var.
   Same pattern as existing MCP servers (via `.env` file or Docker secrets).

5. **KG absorption timing** — Should KG tools move to KEEL MCP immediately or run parallel?
   Recommended: parallel in Phase 1-2, absorb in Phase 3, deprecate KG MCP in Phase 4.
