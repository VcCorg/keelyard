# AGENTS.md Agents — Declarative Agent Spec (Design Doc)

**Status:** Draft / RFC
**Owner:** Build → Agents
**Related code:**
- `agentic-cli/src/agentic_cli/commands/agent.py` (`agent add`, `agent register`, `agent import`, `agent list`)
- `agentic-cli/src/agentic_cli/templates/files/opencode_agent.py` (existing markdown-agent generator)
- `agentic-cli/src/agentic_cli/templates/scaffolds.py` (`AGENT_TYPES` — framework runtime)
- `agentic-cli/src/agentic_cli/commands/project_extensions.py` (`discover_agents` — framework discovery)
- `dashboard/backend/src/services/agent_service.py`, `dashboard/backend/src/api/agents.py`
- Persona skills: `persona_workspace.render_dev_skill` / `render_tech_lead_skill` (SKILL.md frontmatter precedent)

---

## 1. Motivation

Today an agent must be a **framework project**: `dva project create` → `dva agent add --type <T>`
scaffolds Python (`src/agents/*.py`, tools, `main.py`) and runs as a daemon. This is powerful but
heavy — minutes of setup + code for what is often just *a prompt + a few MCP tools + a domain scope*.

We already have the seed of a lighter pattern: `dva agent register --target opencode` emits a
**Markdown agent file** with YAML frontmatter. This RFC generalizes that into a first-class,
**tool-agnostic declarative agent** defined by a single `AGENTS.md`-style file — no build step —
that can be discovered, run, and exported to Devin, Windsurf, and OpenCode.

**Non-goals (this doc):** UI design, and changing the framework runtime. Framework agents stay as-is;
this defines a *second, coexisting runtime*.

---

## 2. Two runtimes (explicit contract)

| | `framework` (existing) | `markdown` (this spec) |
|---|---|---|
| Definition | Python project (`src/agents/*.py`) | Single `.md` + frontmatter |
| Discovery | `discover_agents()` via AST scan | `discover_markdown_agents()` (new) |
| Run | `dva agent start` (daemon, PID-tracked) | `dva agent run <name>` (MCP-tool loop) or IDE-native |
| Best for | Custom logic, stateful loops, ETL | Prompt-driven review / triage / Q&A |
| Portability | Repo-bound | Drop-in for Devin / Windsurf / OpenCode |

A `runtime:` field in frontmatter (default `markdown`) disambiguates. Both appear in the same
`Agents` list, tagged by runtime.

---

## 3. File location & discovery

Canonical source of truth lives in the repo/meta-repo under `.agents/`:

```
<root>/.agents/<agent-name>.md          # one agent per file
<root>/.agents/                          # scanned recursively (1 level)
```

**Discovery order (first match wins for a given name):**
1. Project/worktree `.agents/*.md`
2. Domain meta-repo `.agents/*.md`
3. Imported/global registry (`~/.dva/agents-imported/…`, reusing the `agent import` mechanism)

`.agents/` is chosen (not root `AGENTS.md`) because root `AGENTS.md` is the *repo-wide* instructions
file that Devin/Cursor/Windsurf already read; per-agent definitions need their own namespace.
On **export** we render into each tool's expected location (see §6).

---

## 4. Schema

Front matter is YAML; the body is the system prompt / instructions (Markdown).

### 4.1 Required fields

| Field | Type | Notes |
|---|---|---|
| `name` | string (kebab-case) | Unique within a scope. Matches filename stem. |
| `description` | string | One-to-few sentences. Used for pickers + tool routing. |

### 4.2 Core optional fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `runtime` | `markdown` \| `framework` | `markdown` | Selects the runner. |
| `mode` | `primary` \| `subagent` | `subagent` | OpenCode-compatible; `subagent` = invoked on demand. |
| `model` | string | inherit | e.g. `gemini-2.5-flash`. Falls back to project/global config. |
| `persona` | `dev` \| `tech-lead` \| `solutions-architect` | — | Aligns with workspace tiers. |
| `domain` | string (slug) | — | e.g. `cwow-facility`. Scopes KG/MCP context. |
| `product` | string | — | e.g. `CWOW`. |
| `tools` | list\<string\> \| map\<string,bool\> | `[]` | MCP servers/capabilities. Two forms — see §4.3. |
| `mcp` | map | — | Explicit MCP server config overrides (server → {enabled, args}). |
| `triggers` | list\<string\> | `[manual]` | `manual`, `poll:<seconds>`, `on-pr`, `on-issue`. |
| `permissions` | map | safe defaults | `write`, `edit`, `bash` booleans (OpenCode `tools:` map compatible). |
| `tags` | list\<string\> | `[]` | For registry/marketplace filtering. |
| `version` | string | `1` | Spec/author version. |
| `generated_at` | ISO-8601 | auto | Matches SKILL.md convention. |

### 4.3 `tools` — two accepted forms

Authoring form (concise):
```yaml
tools: [bitbucket, jira]
```
Compiled/OpenCode form (capability booleans) is produced on export:
```yaml
tools:
  bash: true
  read: true
  write: false
  grep: true
```
The named form maps to **MCP servers** (from the KG/MCP config); the boolean form maps to **built-in
IDE capabilities**. The loader normalizes both into a single internal `ResolvedTools` object.

---

## 5. Runtime model (`markdown` runtime)

`dva agent run <name>` (proposed) executes a minimal loop:
1. **Resolve** the `.md` (discovery §3) and parse frontmatter + body.
2. **Assemble context**: inject domain/product context from the KG MCP (`get_project_context`,
   `query_domain_context`) when `domain`/`persona` set.
3. **Attach MCP tools**: start/connect the servers named in `tools:` using existing MCP client config.
4. **Model call**: system prompt = body; tool schemas = attached MCP tools; run until stop/`triggers`.
5. **Track**: register in the same agent state used by `agent_service` so it shows up as an instance.

For `triggers: [poll:300]` / `on-pr`, the same daemon wrapper that framework agents use hosts the loop
(PID-tracked in `agent_service`), so start/stop/logs work identically in the dashboard.

---

## 6. Registration / export (cross-tool)

One source `.agents/<name>.md` → rendered into each target on `dva agent register --target <t>`:

| Target | Output location | Transform |
|---|---|---|
| **opencode** | `.opencode/agent/<name>.md` | frontmatter → `mode` + `tools:` bool map (as today) |
| **devin** | `.devin/skills/<name>/SKILL.md` | frontmatter → SKILL.md fields (`name`, `description`, `domain`, `persona`) |
| **windsurf** | `.windsurf/workflows/<name>.md` or rules | body → workflow steps; `tools` noted (currently stubbed — this unblocks it) |
| **generic** | keep `.agents/<name>.md` | no-op (source is already portable) |

Export is **lossy-forward** only (source `.agents/*.md` remains canonical); re-running regenerates targets.
This finishes the `agent register --target windsurf` TODO at `agent.py:1015`.

---

## 7. Tracker & API surface (proposed, for later phases)

CLI:
- `dva agent new <name> [--domain --persona --tools --model --from-template <t>]` → writes `.agents/<name>.md`
- `dva agent run <name>` → markdown runtime loop
- `dva agent register --target devin|windsurf|opencode|generic` → export (§6)
- `dva agent list` → already lists project agents; extend to include markdown agents + runtime column

Dashboard API (new, fills the current gap — `api/agents.py` has no create):
- `POST /api/agents/declarative` → body `{name, description, domain, persona, tools, model, prompt}` → writes `.md`, returns `AgentInfo`
- `GET  /api/agents/declarative` → list discovered markdown agents
- `POST /api/agents/{name}/register?target=` → export
- (later) `POST /api/agents/scaffold` → wraps framework `agent add`

`agent_service.discover_agent_projects` gains a sibling `discover_markdown_agents(root)` and both feed the
existing `list_agents` shape with an `agent_type`/`runtime` discriminator.

---

## 8. Validation rules

- `name` kebab-case, unique in scope, == filename stem.
- `runtime` ∈ {markdown, framework}; `mode` ∈ {primary, subagent}.
- `tools` names must resolve to a configured MCP server **or** a known builtin capability; unknown → warning (not fatal).
- `domain`/`product` (if set) must exist in the tracker (soft-validate; warn if missing).
- Body must be non-empty for `runtime: markdown`.
- Reuse the SKILL.md validator patterns (`test_skill_validator.py`) for frontmatter linting.

---

## 9. Example

`.agents/pr-triage.md`:
```markdown
---
name: pr-triage
description: Triage and label incoming PRs for the facility domain, flag risky diffs.
runtime: markdown
mode: subagent
persona: dev
domain: cwow-facility
product: CWOW
model: gemini-2.5-flash
tools: [bitbucket, jira]
triggers: [manual, on-pr]
permissions:
  write: false
  edit: false
tags: [review, triage]
version: "1"
---
You are a PR triage agent for the CWOW facility domain.

When a PR opens (or on request):
1. Use `bitbucket.get_pr_overview` + `get_pr_diff` to understand scope.
2. Cross-reference the branch/title Jira key via `jira.get_issue`.
3. Post a summary comment with a risk label (low/medium/high) using `add_pr_comment`.
Never approve/decline without explicit user confirmation.
```

---

## 10. Open questions

1. **Location**: `.agents/*.md` per-agent vs. multiple agents in one `AGENTS.md` (H2-delimited)? (Leaning per-file.)
2. **Named-tools registry**: where is the canonical `tool-name → MCP server` mapping? (Likely the existing KG/MCP config — needs a lookup helper.)
3. **Daemon vs. IDE-native**: for `triggers: manual`, do we run in-process (dashboard) or hand off to the IDE (Devin/Windsurf)? Both? 
4. **Promotion**: `dva agent promote <name>` to scaffold a framework project seeded from the markdown — in scope later?
5. **Secrets**: MCP servers needing creds — reuse existing MCP auth, or per-agent env?

---

## 11. Phased implementation (proposed)

- **P1 (spec + loader)**: finalize this schema; implement parser + `discover_markdown_agents()` + validator (no UI).
- **P2 (run + register)**: `dva agent run` markdown loop; generalize `agent register` to devin/windsurf/generic (§6).
- **P3 (API)**: `POST/GET /api/agents/declarative` + register endpoint.
- **P4 (UI)**: "New Agent" (declarative) create page + list runtime column.
- **P5**: templates gallery + `promote` bridge.

---

## 12. Decisions needed before P1

- [ ] Confirm `.agents/<name>.md` location and per-file model.
- [ ] Confirm `tools` dual-form (named MCP + boolean builtin) and the name→server registry source.
- [ ] Confirm frontmatter field names align with SKILL.md (so devin export is a rename, not a remap).
- [ ] Confirm `runtime` default = `markdown`.
