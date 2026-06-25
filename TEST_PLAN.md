# Agentic Platform — Ground-Zero Test Plan

End-to-end validation plan for the Agentic Platform (CLI `dva` + dashboard backend/frontend),
designed to be run **from a clean slate**. Work top-to-bottom: set up prerequisites, reset to
ground zero, then execute the scenarios in order (each builds on the previous).

- **CLI**: `agentic-cli` (`dva`)
- **Backend**: `dashboard/backend` (FastAPI, `/api/*`)
- **Frontend**: `dashboard/frontend` (React/Vite)

---

## 1. Scope

### In scope (functionally backed)

| Area | Frontend page | Backend router | CLI |
|------|---------------|----------------|-----|
| Overview | `Dashboard` | `/api/overview`, `/api/health` | — |
| Activity | `ActivityFeed` | `/api/activity` | `dva history` |
| Domain Onboarding | `DomainOnboarding` | `/api/domains` | `dva product`, `dva domain` |
| Code Onboard | `CodeOnboard` | `/api/code` | `dva code` |
| Skills | `Skills` | `/api/skills` (+ `validate-with-devin`, `targets`) | `dva skill` |
| Deployments | `Deployments` | `/api/deployments` | deploy flow |
| MCP Servers | `MCPServers` | `/api/mcp` | `dva mcp` |
| Evaluation | `Eval` | `/api/eval` | `dva eval` |
| KG Context / Domain | `KGContext`, `KGDomain` | `/api/kg` | `dva kg` |
| KG Ingest | `KGIngest` | `/api/kg/ingest/*` | `dva kg ingest submit` |
| OKF Generation | `OKFGeneration` | `/api/kg/okf/*` | `dva kg okf` |
| Data Sources | `DataSources` | `/api/data` | `dva data` |
| Agents | `Agents` | `/api/agents` | `dva agent` |
| Agent Projects | `Projects` | `/api/agents` (projects) | `dva project` |
| Chat | `Chat` | `/api/chat` | — |
| Devin Sessions | `Devin` | `/api/devin` (+ `/knowledge`) | `dva devin` |
| Terminal | `Terminal` | `/api/terminal` | — |
| CLI Console | `CLIRunner` | `/api/cli` | — |
| Run streaming (SSE) | (consoles) | `/api/runs` | — |
| Integration status | status bar | `/api/integrations` | — |

### Out of scope (mockups / placeholders — visual only)

`Tasks`, `Assignments`, `Sessions (Fleet)`, `People`, `Shared Agents`, `Shared KG`,
and `Marketplace` (external link-out). These render static/sample data and have **no backend**.
Validate only that they render and navigate.

---

## 2. Prerequisites & Dependencies

### 2.1 Toolchain
- [ ] Python env for `agentic-cli` installed (`dva --help` works)
- [ ] Backend deps installed (`dashboard/backend`)
- [ ] Frontend deps installed (`dashboard/frontend`, `npm install`)

### 2.2 External services / credentials (per feature)
| Dependency | Needed for | Env / config |
|------------|-----------|--------------|
| Devin API key | Skills validate-with-Devin, Devin Sessions, OKF push-devin | `DEVIN_API_KEY` |
| Anchor MCP (Jira/Confluence/Bitbucket) | Domain Onboarding doc/repo tracking, KG Confluence ingest | MCP config |
| KG provider (Neo4j / LightRAG / Postgres / Weaviate) | KG ingest/query/clear, OKF export | `dva kg config` |
| Gemini / Vertex AI | Chat, entity extraction, OKF enrich | provider config |
| gcloud auth | Vertex-backed features | `gcloud auth` |

> Capture which dependencies are available in your environment before starting; skip or mark
> **BLOCKED** any scenario whose dependency is missing (don't fail it).

### 2.3 Start services
- [ ] Backend: run FastAPI app; `GET /api/health` returns `{"status":"ok"}`
- [ ] Frontend: `npm run dev`; app loads at the Vite URL
- [ ] Status bar shows integration probes (Devin/gcloud/Gemini/MCP)

---

## 3. Ground-Zero Reset (clean slate)

> ⚠️ **Destructive.** This wipes local platform state. Devin sessions are **remote** and cannot
> be bulk-wiped — delete/ignore them manually in Devin. Run a dry inspection first where possible.

There is currently **no single reset command** — perform these steps in order:

1. **Wipe the knowledge graph** (all providers):
   ```bash
   dva kg clear --provider both --yes
   ```
2. **Clear async ingest jobs**:
   ```bash
   dva kg async cleanup --days 0 --force
   ```
3. **Reset the tracker DB** (products, domains, repos, docs, projects, activity):
   ```bash
   # Back up first if desired:
   cp ~/.agent-cli-agentic/tracker.db ~/.agent-cli-agentic/tracker.db.bak
   rm ~/.agent-cli-agentic/tracker.db
   # Recreated with fresh schema on next `dva` command / backend startup
   ```
4. **(Optional) Reset CLI config** (workspaces + LLM providers — requires re-init afterward):
   ```bash
   dva init reset --confirm
   ```
5. **Remove local artifacts**:
   - `knowledge-export/`, generated OKF bundles
   - Installed skills in test repos (`.windsurf/`, `.devin/`)
   - Scratch agent project directories

**Post-reset verification**
- [ ] `GET /api/overview` shows 0 products / 0 domains / 0 projects
- [ ] Dashboard home shows empty state
- [ ] `dva kg query "test"` returns empty / no graph
- [ ] Activity feed is empty (or only the reset commands)

> **Gap / TODO:** a guarded one-shot `dva reset` (`--all/--kg/--tracker/--config/--artifacts/--dry-run/--yes`)
> and an admin-only "Factory Reset" dashboard action would replace steps 1–5. Tracked as a follow-up.

---

## 4. End-to-End Scenarios (run in order)

Each scenario lists **preconditions → steps → expected**, and the **surface** (CLI / dashboard).

### S1 — Bootstrap & health
- **Pre:** clean slate, services up
- **Steps:** open dashboard; check status bar; `GET /api/health`, `/api/overview`
- **Expected:** app loads; health ok; empty overview; integration probes reflect real availability
- **Surface:** dashboard

### S2 — Create a Product
- **Pre:** S1
- **Steps:** create product (e.g. `CWOW`) via Domain Onboarding **and/or** `dva product create`
- **Expected:** product appears in `GET /api/domains/products` and onboarding UI
- **Surface:** dashboard + CLI

### S3 — Create a Domain under the Product
- **Pre:** S2
- **Steps:** create domain (e.g. `cwow-facility`) tied to `CWOW`; set Jira/Bitbucket/Confluence refs
- **Expected:** domain listed under product; carries product association
- **Surface:** dashboard + CLI (`dva domain create`)

### S4 — Link repos & track docs (depends on Anchor MCP)
- **Pre:** S3, Anchor MCP available
- **Steps:** link Bitbucket repos; track Confluence doc pages to the domain
- **Expected:** `repo_count` / `doc_count` increment on the domain; visible in KG Ingest domain cards
- **Surface:** dashboard + CLI

### S5 — Code Onboard a repository
- **Pre:** S3
- **Steps:** run Code Onboard on a target repo (auto-detect stack, install SKILL.md)
- **Expected:** streaming console completes; skills installed; repo registered
- **Surface:** dashboard (`/code-onboard`) + `dva code`

### S6 — Register a Data Source
- **Pre:** S2
- **Steps:** create a data source (doc dir / Confluence / git) via Data Sources / `dva data create`
- **Expected:** source listed; selectable in KG Ingest
- **Surface:** dashboard + CLI

### S7 — KG Ingest: Domain mode
- **Pre:** S4, KG provider configured
- **Steps:** from KG Ingest, ingest the domain (depth/top as needed)
- **Expected:** SSE log streams; job recorded; nodes tagged with `domain` + derived `product`
- **Surface:** dashboard + `dva kg ingest submit --domain <slug>`

### S8 — KG Ingest: Path/URL mode (product mandatory)
- **Pre:** S2, KG provider configured
- **Steps:** ingest a path/URL; **verify Ingest is blocked until a Product is selected**; pick optional domain
- **Expected:** submit blocked without product; on submit, nodes/job tagged with product (+ optional domain)
- **Negative:** call `/api/kg/ingest/submit/stream` with no `domain` and no `product` → **HTTP 400**
- **Surface:** dashboard + `dva kg ingest submit --path ... --product ...`

### S9 — KG Ingest: Registered Source mode (product mandatory)
- **Pre:** S6, KG provider configured
- **Steps:** ingest the registered source; product required, domain optional
- **Expected:** same product-tagging + 400 guard as S8
- **Surface:** dashboard + `dva kg ingest submit --source ... --product ...`

### S10 — KG Query / Context
- **Pre:** S7 (or S8/S9)
- **Steps:** open KG Context / KG Domain; run a query
- **Expected:** entities/relationships returned; domain view shows ingested content
- **Surface:** dashboard + `dva kg query`

### S11 — OKF Generation (depends on KG + Vertex)
- **Pre:** S7, Vertex available
- **Steps:** init/export/enrich an OKF bundle for the domain; (optional) visualize
- **Expected:** bundle created; concepts present; viz renders
- **Surface:** dashboard (`/kg/okf`) + `dva kg okf`

### S12 — Skills: browse & install
- **Pre:** S1
- **Steps:** open Skills; install a skill into a target repo
- **Expected:** install console completes; skill present in target
- **Surface:** dashboard + `dva skill`

### S13 — Skills: Validate with Devin (depends on Devin key)
- **Pre:** S12, `DEVIN_API_KEY` set
- **Steps:** Skills → Validate with Devin (optional target repo + extra instructions)
- **Expected:** live session created; **auto-redirect to `/devin?session=<id>`**; session opens with verdict card + transcript
- **Negative:** no Devin key → dry-run preview toast, **no navigation**
- **Surface:** dashboard

### S14 — Skills: Add to Devin Knowledge (admin-only)
- **Pre:** S12, role = admin, Devin key
- **Steps:** Skills → Add to Devin Knowledge
- **Expected:** button visible only to admin; knowledge entry `skill:<name>` pushed
- **Negative:** non-admin role → button hidden
- **Surface:** dashboard + `/api/devin/knowledge`

### S15 — Devin Sessions
- **Pre:** Devin key
- **Steps:** create a session; open detail; send a follow-up message; review verdict card + transcript
- **Expected:** session lists/polls; transcript renders from `raw.messages`; messages send
- **Surface:** dashboard + `dva devin`

### S16 — Agents & Agent Projects
- **Pre:** S1
- **Steps:** create/list agents; scaffold/validate an agent project
- **Expected:** agent appears; project validation score reflects file checks
- **Surface:** dashboard + `dva agent`, `dva project`

### S17 — Chat (depends on LLM provider)
- **Pre:** provider configured
- **Steps:** send a chat message
- **Expected:** streamed response
- **Surface:** dashboard

### S18 — MCP Servers health
- **Pre:** MCP configured
- **Steps:** open MCP Servers; trigger health check
- **Expected:** per-server healthy/unhealthy status
- **Surface:** dashboard + `dva mcp`

### S19 — Evaluation
- **Pre:** S16
- **Steps:** run an eval
- **Expected:** eval executes; results shown
- **Surface:** dashboard + `dva eval`

### S20 — Terminal & CLI Console
- **Pre:** S1
- **Steps:** run a command in Terminal; run a `dva` command in CLI Console
- **Expected:** output streams; exit handled
- **Surface:** dashboard

### S21 — Activity feed reflects history
- **Pre:** after running prior scenarios
- **Steps:** open Activity
- **Expected:** prior CLI/dashboard actions recorded with command/subcommand/args
- **Surface:** dashboard + `dva history`

### S22 — Navigation & RBAC / lens
- **Pre:** S1
- **Steps:** toggle workspace (Mine/Team) and role (member/lead/admin)
- **Expected:** **Knowledge** is its own top-level group right after **Platform**; admin-only items
  (Domain Onboarding, OKF, Admin group, Add-to-Knowledge) appear only for the right role/lens;
  placeholder pages render

### S23 — Mockup pages render
- **Steps:** open Tasks, Assignments, Sessions, People, Shared Agents, Shared KG, Marketplace
- **Expected:** render without error; marked out-of-scope (no backend assertions)

---

## 5. Per-Feature Functional Checklists

### KG Ingest (product/domain binding — recently changed)
- [ ] Domain mode tags nodes with derived product
- [ ] Path/URL mode requires product (UI button disabled until selected)
- [ ] Registered Source mode requires product
- [ ] Domain selector is scoped to the chosen product and is optional
- [ ] Backend returns 400 when neither domain nor product is supplied
- [ ] `dva kg ingest submit --product CWOW --path ...` tags job + node metadata
- [ ] Jobs table shows the ingest (and source/domain)

### Skills ↔ Devin
- [ ] Install mode unaffected
- [ ] Validate mode creates live session + redirects to Devin detail
- [ ] Dry-run when no Devin key (toast only)
- [ ] Verdict card renders PASS/FAIL/PARTIAL (+ falls back to JSON)
- [ ] Transcript renders from `raw.messages`
- [ ] Add-to-Knowledge visible to admin only

---

## 6. Known Gaps / Follow-ups
- No one-shot `dva reset` / dashboard Factory Reset (manual steps in §3).
- Devin sessions cannot be bulk-wiped (remote).
- Mockup pages (§1 out-of-scope) need backends before functional testing.
- Recent Ingest Jobs table does not yet surface a dedicated **Product** column.

---

## 7. Sign-off

| Scenario | Result (Pass/Fail/Blocked) | Notes | Date/Tester |
|----------|----------------------------|-------|-------------|
| S1 | | | |
| S2 | | | |
| S3 | | | |
| S4 | | | |
| S5 | | | |
| S6 | | | |
| S7 | | | |
| S8 | | | |
| S9 | | | |
| S10 | | | |
| S11 | | | |
| S12 | | | |
| S13 | | | |
| S14 | | | |
| S15 | | | |
| S16 | | | |
| S17 | | | |
| S18 | | | |
| S19 | | | |
| S20 | | | |
| S21 | | | |
| S22 | | | |
| S23 | | | |
