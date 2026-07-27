# Keel — Agentic Platform

Keel is the workbench for building governed agent workflows. It ships as a **desktop
app** (macOS `.dmg`, Windows `.exe`) for zero-setup use, and as a **web dashboard +
CLI** for local development. The same backend powers both.

Under one roof:

- **Knowledge Graph** — ingest, browse, and generate OKFs over your code and domain.
- **Agent Builder** — quickstart, canvas, projects, skills, and a **Watchers** module
  for event-driven agents.
- **Build Sessions** — hand a task to Devin (Cloud or CLI) or open it in a code-assist
  IDE (VS Code, Cursor, …) through the vendor-neutral engine seam.
- **Governance** — one policy path across the inner (build) and outer (session/onboard)
  loops, enforced at the `execution.registry.create_session` and `code onboard` seams.
- **MCP servers** — Bitbucket, Jira, Confluence, Glean, KG, and Memory available as
  data sources, with per-server health and a Docker stack.
- **Models** — Vertex/Anthropic/OpenAI, any OpenAI-compatible **local** model
  (Ollama, LM Studio, llama.cpp, vLLM), a **built-in tiny model** downloadable on
  first use, and a clearly-labeled **test mode** so a fresh install is demoable with
  zero config.

## Two ways to run

### 1. Desktop app (recommended — no Python, no `uv`, no setup)

The Electron shell picks a free port, spawns the frozen FastAPI+CLI sidecar
(PyInstaller onedir), and opens the dashboard on `http://127.0.0.1:<port>/`. See
[`desktop/README.md`](desktop/README.md) for the full flow.

- **Install:** download the `.dmg` (macOS) or `.exe` (Windows) from the CI release
  artifacts (`.github/workflows/desktop-build.yml`).
- **Build locally:** Node 22 (nvm) + Python 3.12; then
  `cd desktop && npm install && npm run package:mac` (or `package:win`).
- **First run:** creates `~/.keel/` (env store, admin settings, role/persona data);
  the tracker SQLite DB is initialized on demand. Landing page is the Setup panel
  when provider keys are missing.
- **CLI inside the app:** the sidecar drops a `keel` wrapper into `~/.keel/bin` and
  prepends it to `PATH`, so terminals opened inside the app run `keel …` with no
  system Python.

### 2. Dev workspace (CLI + web dashboard)

Prereqs: [`uv`](https://docs.astral.sh/uv/) (Python 3.12), Node 22, and Docker
(optional — only if you want the MCP stack running locally).

```bash
git clone <your-fork-or-repo-url> agentic-project
cd agentic-project

# One-shot setup: installs the CLI, configures skills registry,
# bootstraps mcp-servers/.env, and runs preflight diagnostics.
./setup.sh                 # add --with-mcp to also start the MCP Docker stack

source .venv/bin/activate

# Configure integration credentials in mcp-servers/.env
# (set *_SERVER_URL and *_PERSONAL_ACCESS_TOKEN for Bitbucket/Jira/Confluence)

keel doctor                 # verify environment (add --probe for host reachability)
keel code onboard --path ./some-project   # onboard any project

# Dashboard
./start-backend.sh          # backend on :8000
./start-frontend.sh         # Vite dev server on :5173
```

Manual, step-by-step alternative:

```bash
./install-agentic-cli.sh --project --native-tls   # install CLI into ./.venv
source .venv/bin/activate
keel code config --registry ./skills                # configure skills registry
cp mcp-servers/.env.example mcp-servers/.env       # then edit with your URLs/tokens
cd mcp-servers && docker compose up -d && cd ..    # start MCP servers
keel doctor                                         # validate
```

> All base URLs are configuration-driven. Set `BITBUCKET_SERVER_URL`,
> `JIRA_SERVER_URL`, and `CONFLUENCE_SERVER_URL` (with matching
> `*_PERSONAL_ACCESS_TOKEN`s) via `mcp-servers/.env` — there are no
> vendor-specific defaults baked into the code.

## What's inside (nav tour)

The dashboard is organized as a lifecycle — govern → know → ideate → build → track.

| Group | Highlights |
|---|---|
| **Overview** | Dashboard, Activity, Audit History (lead+) |
| **Governance** | Domain onboarding, Workspaces, Persona Skills, Marketplace |
| **Knowledge** | KG dashboard, Data Sources, KG Ingest, OKF Generation (admin), unified Graph, KG Onboarding wizard |
| **Work Items** | Jira-backed work items and assignments |
| **Ideate** | Requirements capture |
| **Build** | Repository (`keel code onboard`), Skills, Build Sessions (Devin cloud/CLI), Execution & Context, Snapshots |
| **Agent Builder** | Quickstart, Agent Projects, Project Canvas, Agents, **Watchers**, Components (Models, Tools, Retrievers, Databases, Data Sources, MCP, Skills) |
| **Quality** | Skill Trials, Evaluation (QA persona) |
| **Platform** | MCP Servers, Deployments, CLI Console + Setup |
| **Admin** | Administration, Identity & Access, People, Shared Agents, Shared KG |

### Watchers — event-driven agents

Turn agents from request/response into event-driven. A **Watcher** binds a trigger
(e.g. Bitbucket "PR review requested") to an agent handler; the runtime polls the
source on a schedule, catches up on missed events on app open (3-day window),
dedups by event id, and hits the same governance seam (`execution.registry.
create_session`, `origin: watcher/<name>`) that manual runs use.

- Specs and state live under `~/.keel/watchers/` (YAML per watcher + `state.json`).
- The UI is at `/watchers` with per-agent triggers surfaced on the Agents page.
- Add a new source by dropping a `TriggerProtocol` under
  `agentic-cli/src/agentic_cli/watchers/triggers/`.

### Governance layers

One policy path across two loops — start with
[`docs/GOVERNANCE_LAYERS.md`](docs/GOVERNANCE_LAYERS.md) for the one-page overview,
then the deep dives:

- [`docs/BUILD_GOVERNANCE.md`](docs/BUILD_GOVERNANCE.md) — outer loop (session +
  onboard), enforced at `execution.registry.create_session` and `keel code onboard`.
- [`docs/PERSONA_SKILL_GOVERNANCE.md`](docs/PERSONA_SKILL_GOVERNANCE.md) — persona →
  skill policy across inner + outer loops, with admin-toggle enforcement.
- [`docs/DOMAIN_ONBOARDING_GOVERNANCE_DEMO.md`](docs/DOMAIN_ONBOARDING_GOVERNANCE_DEMO.md)
  — end-to-end walkthrough.

### Models — cloud, local, built-in, and test mode

The provider chain makes the app usable the moment it's installed:

1. **Cloud** — Vertex AI (`keel init vertex-ai`), Anthropic, or OpenAI.
2. **Local models** — anything with an OpenAI-compatible API (Ollama by default,
   LM Studio, llama.cpp server, vLLM):
   ```bash
   keel init local-model --model llama3.2                     # Ollama
   keel init local-model --model qwen2.5 --url http://localhost:1234/v1  # LM Studio
   keel init local-model --model llama3.2 --default           # route ALL LLM calls locally
   ```
3. **Built-in tiny model** (one-time ~400 MB pull of Qwen2.5-0.5B-Instruct into
   `~/.keel/models`, runs in-process via llama.cpp):
   `keel init builtin-model` (or the Setup panel's Download button).
4. **Test mode** — deterministic, clearly-labeled provider that answers when
   nothing above is configured, so every workflow is demoable. Disable with
   `KEEL_DISABLE_TEST_MODE=1`.

Fallback order: **cloud → local → built-in → test mode.**

## Repos

| Local Dir | Description |
|-----------|-------------|
| `agentic-cli/` | CLI — `keel` — agent, skill, code onboard, kg, mcp, project, watchers, admin |
| `dashboard/` | Web app — React frontend + FastAPI backend |
| `desktop/` | Electron desktop app — bundles the dashboard + backend for zero-setup distribution ([README](desktop/README.md)) |
| `skills/` | Skills registry — skill definitions and AI evaluation framework |
| `mcp-servers/` | MCP servers — multiple protocol implementations + docker-compose |
| `kg-infrastructure/` | KG infra — knowledge graph server, Neo4j, LightRAG, sample data, docs |

## Preventing internal/company data in commits

This repo ships a guard that blocks commits containing company-specific data
(internal hostnames, usernames), real domain/KG data files, and secret formats.

Enable the version-controlled hook once per clone:

```bash
git config core.hooksPath .githooks
```

- Manual scan of the whole tree (also used in CI): `bash scripts/check-no-company-data.sh --all`
- The pre-commit hook scans only staged changes automatically.
- Real domain data (`skills/domains/cwow-*/`, `kg-infrastructure/docs/CWOW_*|SNF_*`,
  `graphify-out/`, `knowledge-export/`) is git-ignored and stays local.
- Emergency bypass (discouraged): `ALLOW_COMPANY_DATA=1 git commit ...`

## Development

### Project virtual environment

Single project-level `uv` venv at `.venv` (Python 3.12) for all Python components
(agentic-cli, dashboard/backend).

```bash
source .venv/bin/activate
```

### Running the dashboard

```bash
./start-backend.sh          # http://localhost:8000
./start-frontend.sh         # http://localhost:5173
```

Windows equivalents: `start-backend.ps1`, `start-frontend.ps1`, `start-dashboard.ps1`.

### Desktop dev loop

```bash
./start-backend.sh                              # terminal 1
npm --prefix dashboard/frontend run dev         # terminal 2 (Vite proxy for /api)
cd desktop && npm run dev                       # terminal 3 (Electron on the dev server)
```

`KEEL_DEV=1` makes Electron load the Vite dev server instead of spawning the sidecar.

## Dependencies between repos

```
agentic-cli ──uses──→ skills (skills registry)
agentic-cli ──uses──→ mcp-servers (MCP tools for agents)
agentic-cli ──uses──→ kg-infrastructure (kg commands)
dashboard   ──imports──→ agentic-cli (single-process backend)
desktop     ──bundles──→ dashboard (frozen FastAPI + agentic_cli sidecar)
mcp-servers ──refs──→ kg-infrastructure (kg-mcp in compose)
skills      ────no deps────
```

## Docs

Component docs live alongside code; cross-cutting docs are under
[`docs/`](docs/README.md):

- Governance — start with [`docs/GOVERNANCE_LAYERS.md`](docs/GOVERNANCE_LAYERS.md).
- Guides — [`docs/guides/`](docs/README.md#guides) (development, evaluation, code
  onboarding, meta-repo quick start).
- Plans & specs — [`docs/plans/`](docs/README.md#plans) and
  [`docs/specs/`](docs/README.md#specs).
- Desktop — [`desktop/README.md`](desktop/README.md).
- Dashboard — [`dashboard/README.md`](dashboard/README.md).
