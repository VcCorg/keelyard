# OKF CLI Integration Map
## Where OKF, KG, Jira/Confluence, and Devin Knowledge fit in the CLI

---

## 1. CLI Command Topology

```
keel
├── product create/list/show
├── domain create/update/show/list/link-repo/fetch-repos/add-docs
│   └── (stores Jira/BB/Confluence keys in tracker.db)
├── code onboard / list / validate / skills
│   └── (project-level AI context setup)
├── kg init / check / ingest / query / okf
│   ├── ingest submit  ← ingests docs/Confluence/git into Neo4j or LightRAG
│   └── okf init / export / validate / trace / push-devin / devin list/prune/delete
├── skill list / add / marketplace
└── mcp / data / agent / eval / history
```

---

## 2. Layer Definitions

| Layer | Where it lives | Role | Persistence |
|---|---|---|---|
| **OKF bundle** | Git repo (`knowledge-export/<domain>/`) | Schema-governed markdown; source of truth for stable requirements | Git-native, versioned |
| **Knowledge Graph (KG)** | Neo4j / LightRAG (live services) | Queryable projection compiled from OKF + Confluence ingest; traversal + semantic search | Service (outside git) |
| **Jira / Confluence** | SaaS (via anchor MCP) | Live project artifacts: issues, specs, docs | Upstream SaaS |
| **Devin Knowledge** | Devin Cloud API | Trigger-injected runtime guidance for the AI agent | Cloud API |

---

## 3. Exact CLI Integration Points — Today

### 3.1 OKF Commands (`keel kg okf`)

| Command | What it does | Precondition |
|---|---|---|
| `keel kg okf init --domain <slug>` | Scaffold OKF bundle + `okf.schema.yaml` + `index.md` at `skills/domains/<slug>/knowledge/` | None (standalone) |
| `keel kg okf export --domain <slug>` | Read Neo4j domain subgraph → write spec-conformant OKF bundle (feature-grouped) | Neo4j ingested |
| `keel kg okf validate <dir>` | Validate bundle against `okf.schema.yaml` (required frontmatter, triples, uniqueness) | Bundle exists |
| `keel kg okf trace <dir> [--gaps]` | FREQ dev/QA traceability report; `--gaps` exits non-zero for CI | Bundle exists |
| `keel kg okf push-devin --domain <slug>` | Push STABLE concepts (FREQ, Requirement) to Devin Cloud Knowledge, idempotent | Bundle validated, `$DEVIN_API_KEY` |
| `keel kg okf devin list/prune/delete` | Manage Devin Knowledge entries lifecycle | `$DEVIN_API_KEY` |

**OKF is NOT called by `keel code onboard` today.** It is a separate domain-lifecycle operation.

---

### 3.2 Knowledge Graph — CLI Touchpoints

| CLI Step | Command / Option | What happens |
|---|---|---|
| Configure KG | `keel kg init --provider neo4j/lightrag` | Saves connection config to `~/.agent-cli-agentic/kg-config.json` |
| Ingest Confluence | `keel domain add-docs <slug>` → `keel kg ingest submit --domain <slug>` | Fetches tracked Confluence pages via MCP → ingests into KG |
| Ingest git repo | `keel kg ingest submit --path <repo>` | Code context → KG |
| Onboard with KG context | `keel code onboard --path <repo> --domain <slug>` | Step 9c: `query_domain_kg(domain)` → 6 KG aspects → `domain-context` SKILL.md |
| Onboard + code→KG | `keel code onboard --path <repo> --kg` | Step 9d: builds `kg-code-context.md`, registers data source, ingests |
| Link code to requirements | `keel code onboard --domain <slug> --kg --link-kg` | LLM links code entities → KG requirement nodes |
| Export KG → OKF | `keel kg okf export --domain <slug>` | Neo4j → OKF markdown bundle (no re-ingestion) |

---

### 3.3 Jira / Confluence — CLI Touchpoints

| CLI Step | Command | Layer used |
|---|---|---|
| Register domain coordinates | `keel domain create --jira <key> --confluence <space> --bb <key>` | tracker.db (metadata store) |
| Discover repos | `keel domain fetch-repos <slug>` | **Bitbucket MCP** live call |
| Discover/track Confluence pages | `keel domain add-docs <slug>` | **Confluence MCP** live call |
| Ingest tracked Confluence into KG | `keel kg ingest submit --domain <slug>` | Uses stored page IDs → Confluence MCP → Neo4j/LightRAG |
| FREQ live status | `keel kg okf trace --hydrate` | **Jira MCP** at runtime |
| AI agent runtime | (any task) | anchor MCP (Jira + BB + Confluence) injected via `project-context` SKILL.md |

**Key insight**: Jira/Confluence are **never queried during `keel code onboard` itself**. They are:
1. Referenced as MCP endpoints in the generated `project-context` SKILL.md
2. Called live by the AI agent at task time via the anchor MCP server

---

### 3.4 Devin Knowledge — CLI Touchpoints

| CLI Step | Command | What it does |
|---|---|---|
| Push STABLE concepts | `keel kg okf push-devin --domain <slug>` | OKF bundle → Devin API (idempotent) |
| Per-feature push | `keel kg okf push-devin --folder-by-feature` | Each FREQ in its own `<domain>-<freq>` folder |
| Dry-run preview | `keel kg okf push-devin --dry-run` | Renders JSON payloads without calling API |
| Lifecycle management | `keel kg okf devin list/prune/delete` | Audit/clean up stale entries |

**Devin Knowledge is NOT triggered by `keel code onboard`.** The flow is:
`OKF bundle (validated) → push-devin → Devin Cloud → injected at AI agent session start`

---

## 4. `keel code onboard` Step-by-Step Mapping

```
keel code onboard --path <repo> [--domain <slug>] [--kg] [--link-kg] [--graphify] [--use-domain-skills]
```

| Step | Code location | Layer(s) used |
|---|---|---|
| 1. Clone repo | `subprocess git clone` | None |
| 2. Ensure skills registry | `_ensure_registry()` | Local skills registry |
| 3. Analyze project | `analyze_project()` | Local (AST, file detection) |
| 3b. Run graphify | `_run_graphify_update()` | graphify (local AST graph) |
| 4. Detect MCP servers | `detect_mcp_servers()` | Reads `.mcp_config.json`, `.opencode/mcp.json` |
| 5. Match/install skills | `match_skills()` | Local skills registry |
| 6. Generate `project-context` | `generate_project_context_skill_content()` | **Writes MCP references**: graphify, keel-kg-mcp, anchor (Jira+BB+Confluence), glean |
| 7b. Install domain-validated skills | `load_domain_skills()` | Domain-context repo `.domain/` folder |
| 9a. Agent skill gap detection | `run_onboard_pipeline()` | Optional Vertex AI |
| 9b. Register repo | `register_repo()` | tracker.db |
| **9c. Domain context** | `query_domain_kg(domain)` | **KG (Neo4j/LightRAG)** — generates `domain-context` SKILL.md |
| 9c. Git submodule | `add_submodule()` | Git — adds domain-context repo |
| **9d. KG code context** | `run_kg_context_pipeline()` | **KG** — builds `kg-code-context.md`, registers source, ingests |
| 9d. Link code→requirements | `link_code_to_requirements()` | **KG** — LLM links code to requirement nodes |
| 9e. Record activity | `record_activity()` | tracker.db |

**OKF has no step in `keel code onboard` today.**

---

## 5. What OKF Should Add to `keel code onboard`

### Gap: Step 9c queries Neo4j directly
`query_domain_kg(domain)` hits Neo4j to get domain context. If Neo4j is down/not ingested, domain context is empty.

**Proposed enhancement**: Add `--okf-bundle <dir>` flag so Step 9c reads the OKF bundle instead.

```
keel code onboard --path <repo> --domain cwow-facility --okf-bundle knowledge-export/cwow-facility
```

What changes in `code.py` Step 9c:
- If `--okf-bundle` is provided → load `Bundle`, extract Requirements + FREQs + Features → build `domain-context` SKILL.md from OKF structure
- Benefit: works **without Neo4j running**, from git-native source of truth
- OKF validates in CI, so bundle integrity is guaranteed

### Gap: `project-context` SKILL.md doesn't reference OKF path
Step 6 writes `project-context/SKILL.md` with `keel-kg-mcp` and `anchor` MCP references but no OKF bundle path.

**Proposed enhancement**: When `--domain` is provided and an OKF bundle exists at the conventional path, add an OKF reference to the SKILL.md:

```yaml
okf_bundle: skills/domains/cwow-facility/knowledge
okf_features:
  - features/authentication/
  - features/scheduling/
```

This lets the AI agent navigate OKF files directly via the codebase without querying the KG.

---

## 6. CI/CD Integration Map

```
git push → CI pipeline
  ├── keel kg okf validate <bundle>        ← OKF schema conformance gate
  ├── keel kg okf trace --gaps             ← FREQ coverage gate (fails if DEV/QA gap)
  ├── keel kg okf export --no-validate     ← optional: re-export from Neo4j (post-ingest)
  └── keel kg okf push-devin --dry-run     ← optional: preview Devin payloads without pushing
```

Devin push should be a **manual or scheduled** step, not in hot CI, because:
- Devin API has rate limits
- Folder creation requires manual Devin UI action first
- `--dry-run` preview is safe in CI; live push belongs in release pipeline

---

## 7. Authoritative Layer Routing Table

| Query type | Use layer | CLI entrypoint |
|---|---|---|
| "What are the requirements for FREQ CWOW-301456?" | **OKF bundle** (git, offline) | Read `features/<slug>/CWOW-301456.md` directly |
| "What FREQs have no test coverage?" | **OKF trace** | `keel kg okf trace --gaps` |
| "What Jira tickets are IN PROGRESS right now?" | **Jira MCP** (live) | AI agent via anchor MCP at runtime |
| "Show me all requirements across features" | **KG** (traversal) | `keel kg query` / KG MCP |
| "What business rules apply to scheduling?" | **KG / LightRAG** (semantic) | KG MCP `search_business_context` |
| "What code file implements FREQ X?" | **OKF trace + graphify** | `keel kg okf trace --freq X` + graphify |
| "Inject FREQ X guidance into Devin session" | **Devin Knowledge** (trigger) | Push via `keel kg okf push-devin` |
| "What Confluence docs exist for this domain?" | **Confluence MCP** (live) | AI agent via anchor MCP |
| "Which repos belong to this domain?" | **tracker.db** | `keel domain repos <slug>` |

---

## 8. Recommended `keel code onboard` Enhancement — Minimal Change

Add one new optional step **9c-okf** between the existing 9c and 9d:

```python
# Step 9c-okf: OKF bundle enrichment (optional — no Neo4j required)
if okf_bundle:
    from agentic_cli.kg.okf.bundle import Bundle
    from agentic_cli.kg.okf.onboard import build_okf_domain_context
    bundle = Bundle.load(Path(okf_bundle))
    okf_skill_content = build_okf_domain_context(bundle, domain)
    (skill_dir / "SKILL.md").write_text(okf_skill_content)
    console.print(f"✓ OKF domain context installed from bundle: {okf_bundle}")
```

New flag on `keel code onboard`:
```
--okf-bundle <dir>     Read OKF bundle for domain context (no Neo4j required)
```

The new `build_okf_domain_context()` function in `agentic_cli/kg/okf/onboard.py`:
- Loads Bundle concepts
- Groups by feature (using path segments)  
- Renders `domain-context` SKILL.md with feature index + FREQ list per feature
- References OKF file paths so AI can read concepts directly from git

This adds **zero runtime dependencies** — OKF is just markdown files in git.
