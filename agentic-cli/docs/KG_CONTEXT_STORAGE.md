# KG Context Storage & Retrieval

How project context flows from `keel code onboard` into the Knowledge Graph and
back to coding agents.

---

## Overview

When you run `keel code onboard --path ./repo --kg`, the onboard pipeline adds
three extra steps after the standard skill installation:

1. **Build** a rich context document (`kg-context.md`) from the project analysis
2. **Register** the project as a data source in `~/.keel-agentic/config.json`
3. **Ingest** the context into LightRAG for semantic search

The coding agent is then instructed (via `SKILL.md`) to query the Knowledge
Graph before acting on any coding task.

---

## Storage Locations

```
~/.keel-agentic/
├── config.json                        ← Global config: data sources registry
│   └── data.sources[]                 ← Contains "onboard-<project>" entries
├── kg-config.json                     ← KG provider config (LightRAG URL, etc.)
├── tracker.db                         ← SQLite: onboarded repos, activities
└── lightrag-workspaces/               ← LightRAG semantic index data

<project>/
└── .skills/
    ├── onboard.json                   ← Manifest: full analysis + installed skills
    └── project-context/
        ├── SKILL.md                   ← Agent instructions (patched with KG workflow)
        └── kg-context.md              ← Rich context document for KG ingestion
```

### What Each File Contains

| File | Purpose | Created By | Consumed By |
|------|---------|------------|-------------|
| `kg-context.md` | Rich markdown with tech stack, architecture, deps, patterns, integrations | `context_builder.save_kg_context()` | LightRAG (ingested), humans (readable) |
| `SKILL.md` | Agent instructions including "Context-First Workflow" section | `_generate_project_context_skill()` + `patch_skill_md_with_kg_instructions()` | IDE agents (Windsurf, Claude, Cursor, OpenCode) |
| `onboard.json` | Full `ProjectAnalysis.to_dict()` + installed/suggested skills | `_save_onboard_manifest()` | `keel code validate`, programmatic access |
| `config.json` → `data.sources[]` | Data source registration for `keel kg ingest` | `register_kg_data_source()` | `keel kg ingest submit --source onboard-<project>` |

---

## Two Ingestion Modes

### Light Mode (`--kg`)

```bash
`agent code onboard --path ./repo --kg
```

- Generates `kg-context.md` from `ProjectAnalysis`
- Registers as data source: `onboard-<project-name>`
- Inserts text directly into LightRAG via `client.insert()`
- **No entity extraction** — fast (~2-3 seconds)
- **No Vertex AI dependency** — LightRAG handles its own embeddings
- Context available via `search_business_context("architecture of project X")`

### Full Mode (`--kg --extract-entities`)

```bash
`agent code onboard --path ./repo --kg --extract-entities
```

- Everything in light mode, **plus**:
- Runs the full `keel kg ingest` pipeline on `.skills/project-context/`
- Entity extraction via Vertex AI (Framework, Database, API entities)
- Relationship building → `USES`, `DEPENDS_ON`, `CONTAINS` edges in Neo4j
- Enables structured queries: `get_entity_details("PatientService")`
- **Slower** — requires Vertex AI and Neo4j

---

## How to Fetch Context

### From Files (always available, no infra needed)

```python
from pathlib import Path
import json

project = Path("./my-repo")

# Rich context document
kg_context = (project / ".skills/project-context/kg-context.md").read_text()

# Full analysis data
manifest = json.loads((project / ".skills/onboard.json").read_text())
analysis = manifest["analysis"]

# Agent instructions
skill_md = (project / ".skills/project-context/SKILL.md").read_text()
```

### From Data Source Registry

```bash
# List all registered sources
`agent data list

# Show details for a project's context source
`agent data show onboard-my-repo

# Re-ingest after changes
`agent kg ingest submit --source onboard-my-repo
```

### From Knowledge Graph (via KG MCP tools)

These are the tools a coding agent calls:

```
# High-level project overview (sources, stats, summary)
get_project_context(project="my-repo")

# Semantic search for specific context
search_business_context(query="how does authentication work in this project")

# Structured query (full mode only, requires Neo4j)
query_knowledge_graph(query="what databases does my-repo use", mode="natural")

# Entity details (full mode only)
get_entity_details(entity_name="PatientService")
```

### From CLI

```bash
# Query the KG directly
`agent kg query "architecture of my-repo"

# Semantic search
`agent kg search "database patterns" --semantic

# Check what's in the KG
`agent kg stats
```

---

## Validation

### Check if KG context exists

```bash
# Verify onboarding + KG context
`agent code validate --path ./my-repo
# → Shows "KG Context: ✓ Prepared" if kg-context.md exists

# Check data source registration
`agent data show onboard-my-repo

# Check LightRAG availability
`agent kg check --provider lightrag
```

### Verify ingestion

```bash
# Search for ingested content
`agent kg search "my-repo tech stack"

# Check KG stats
`agent kg stats
```

---

## Context-First Workflow for Coding Agents

When `--kg` is used, the `SKILL.md` is automatically patched with instructions
that tell any coding agent to query the KG before starting work:

```markdown
## Context-First Workflow (Knowledge Graph)

Before starting any coding task:
1. Call `get_project_context(project="my-repo")`
2. Call `search_business_context(query="<your task description>")`
3. Review results before writing or modifying code
4. When unsure about patterns, call `search_business_context(query="conventions for <topic>")`
```

This works across all IDEs that read `.skills/*/SKILL.md`:
- **Windsurf** — reads skills automatically
- **Claude Code** — reads skills automatically
- **OpenCode** — reads skills automatically
- **Cursor** — reads `.cursorrules` (copy instructions there)

---

## Data Flow Diagram

```
`agent code onboard --path ./repo --kg
         │
         ├─ Step 3: analyze_project()
         │           → ProjectAnalysis object
         │
         ├─ Step 6: _generate_project_context_skill()
         │           → .skills/project-context/SKILL.md
         │
         ├─ Step 9: _save_onboard_manifest()
         │           → .skills/onboard.json
         │
         └─ Step 9c: run_kg_context_pipeline()
                  │
                  ├─ build_kg_context_document()
                  │    → .skills/project-context/kg-context.md
                  │
                  ├─ patch_skill_md_with_kg_instructions()
                  │    → SKILL.md updated with "Context-First Workflow"
                  │
                  ├─ register_kg_data_source()
                  │    → ~/.keel-agentic/config.json data.sources[]
                  │
                  └─ ingest_context_to_lightrag()  (light mode)
                       → LightRAG semantic index
                            │
                            ▼
                  KG MCP → search_business_context()
                         → get_project_context()
                            │
                            ▼
                  Coding agent queries context before coding
```

---

## Re-onboarding & Idempotency

Running `keel code onboard --path ./repo --kg` again is safe:

- `kg-context.md` is **overwritten** with fresh content
- Data source registration is **idempotent** (same name → overwrites)
- `SKILL.md` KG instructions are **appended only once** (marker check)
- LightRAG insert adds a new document (older versions remain searchable)

To clean up and re-ingest:

```bash
# Remove data source
`agent data delete onboard-my-repo --yes

# Clear LightRAG data (caution: clears entire workspace)
`agent kg workspace clear default
```

---

## Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/agentic_cli/kg/context_builder.py` | ~310 | Context builder module: build, save, register, ingest, pipeline |
| `src/agentic_cli/commands/code.py` | +55 | `--kg` / `--extract-entities` flags + step 9c integration |
| `tests/test_context_builder.py` | ~410 | 29 unit tests covering all functions |
| `docs/KG_CONTEXT_STORAGE.md` | this file | Storage architecture documentation |

---

## Dependencies

- **Light mode** (`--kg`): Only needs `httpx` (for LightRAG client) + running LightRAG server
- **Full mode** (`--kg --extract-entities`): Also needs `google-cloud-aiplatform` + Neo4j
- **No KG** (default): No additional dependencies — standard onboarding works as before
