# Ideate v2 — Guided Wizard with Agent Tool Loop, Injected Agents, and Rich Jira Cards

**Date:** 2026-07-08
**Status:** Approved design (pre-implementation)

## 1. Problem & Goals

The current `Ideate` feature (`dashboard/frontend/src/pages/Ideate.tsx`,
`dashboard/backend/src/api/ideate.py`, `dashboard/backend/src/services/ideate_service.py`)
is a fixed 3-step form: gather requirements → one-shot LLM draft → push to Jira.

Three problems / opportunities were identified:

1. **No agent/chat experience.** Users want a Glean/Devin-style agent window where
   integrations (Glean, Confluence, Jira) and MCP servers are usable as tools.
2. **Built/imported agents are not reusable here.** Agents produced by the agent
   builder (`keel agent`, `agent_service`) cannot participate in Ideate.
3. **Jira stories render as flat "lines."** Drafted stories lack real Jira fields
   (issue type, epic link, editable acceptance criteria, points, assignee) and on
   push the acceptance criteria are concatenated into the description instead of
   mapped to real fields.

### Goals
- Rebuild Ideate as a **5-step guided wizard** (chosen over pure chat).
- Add a **provider-agnostic tool-calling agent** whose actions stream to a
  collapsible **agent window**.
- Allow **injecting built/imported agents as tools** (agents-as-tools).
- Produce **rich, editable Jira action-item cards** with real field mapping.
- **Audit every mutating action** (Jira create, Confluence/resource create, mutating
  MCP tools) using the existing tracker.

### Non-goals
- Native provider SDK function-calling (text-only provider layer stays as-is).
- Persisting wizard session state in a database (backend stays stateless for
  wizard state; audit is the only persistence).
- Free-roaming chat outside the wizard.

## 2. Decisions (from brainstorming)

| Topic | Decision |
|---|---|
| UX model | **B — Guided wizard** (5 steps) |
| Steps | Scope → Gather → Draft → Review → Push |
| Agent engine | **Hybrid**: built-in tool loop + injected agents |
| Engine implementation | **ReAct-style JSON tool loop** over existing text-only `LLMProvider` (provider-agnostic) |
| Injected agents | **Registered as tools** the loop can call |
| Jira cards | **All** fields/actions: issue type, epic/parent, editable AC, points, assignee/component, per-card agent refine, split/duplicate, push individually |
| Wizard state | **Stateless backend** (frontend owns state, posts per call) |
| Audit | **Required for all mutating actions**, via existing `record_activity()` |
| Agent window | **Collapsible**, hidden by default |
| Phasing | **Phase by value**, each phase ships a working Ideate |

## 3. Architecture

```
Wizard step
  → POST /api/ideate/agent/run (SSE)
      → ideate_agent.run_agent()  [ReAct loop]
          → ideate_tools.call_tool()  [registry]
              → integration tools (Glean / Confluence / Jira / MCP)
              → agent tools (built/imported agents' answer())
          → streamed trace events (thinking / tool_call / tool_result / stories / final)
  → Step 4 rich action-item cards (edit / refine / split)
  → POST /api/ideate/push  → jira_service (createmeta-driven field mapping)
      → ideate_audit.record_action() per created issue
```

### Engine rationale
The `LLMProvider` protocol (`agentic_cli/llm/base.py`) exposes only `generate` /
`generate_async` / `generate_streaming` (text in → text out) across Vertex AI,
Anthropic, OpenAI. Native function-calling would require per-provider rework and
only Vertex is wired org-wide. A **ReAct JSON loop** — the model emits
`{"action": {"tool": ..., "args": {...}}}` or `{"final": {...}}`, the backend
executes and feeds back an observation — works with all providers unchanged and is
trivial to trace/stream.

## 4. Backend Components

### 4.1 `services/ideate_agent.py` (new)
- `async run_agent(task, context, tools, model=None, max_iters=6) -> AsyncGenerator[AgentEvent]`
- Builds a system prompt containing the tool catalog + JSON action protocol.
- Loop: call `provider.generate()` → parse JSON action → if `tool`, dispatch via
  `ideate_tools.call_tool()` and append observation; if `final`, parse stories and stop.
- Robustness: iteration cap; malformed JSON → one reprompt, then fall back to
  `ideate_service.draft_stories()`; tool errors returned as `tool_result{error}` and
  the loop continues.
- Yields `AgentEvent`s for SSE.

### 4.2 `services/ideate_tools.py` (new)
- `ToolSpec { name, kind: "integration"|"agent", description, params(JSON schema), mutating: bool, run }`.
- `list_tools(ctx) -> list[ToolSpec]`: enabled integration tools + agent tools for the scope.
- `call_tool(name, args, ctx)`: dispatch; **if `mutating` → auto-audit** via `ideate_audit`.
- Integration tools (P2): `glean_search`, `confluence_search`, `jira_search` (reuse
  `ideate_service.search_source` + `jira_service`), plus discovered **MCP** server tools.
- Agent tools (P3): each built/imported agent wrapped to call its `answer()` using the
  runner pattern from `agent_service.test_agent`.

### 4.3 `services/ideate_service.py` (extend)
- Keep `draft_stories()` / heuristic fallback / `search_source`.
- Add `push_stories(project_key, stories, jira_meta)` with **real field mapping**
  (see §6), replacing the AC-into-description concatenation.

### 4.4 `services/jira_service.py` (extend)
- `get_create_meta(project_key)` → `/rest/api/2/issue/createmeta` (available fields).
- `list_issue_types(project_key)`, `list_epics(project_key)`.
- `create_issue()` extended to accept mapped fields (epic link, points, assignee,
  components) guarded by createmeta availability.

### 4.5 `services/ideate_audit.py` (new, thin wrapper)
- `record_action(action, target, request, result, actor)` →
  `record_activity(command="ideate", subcommand=action, args=request, details=result,
  entity_type=..., entity_id=...)` in `agentic_cli/tracker.py`.
- Actor resolved from the forwarded SSO user token (email/id) when present, else
  `"service"`.
- Only **mutating** actions are audited (reads/searches/drafting are not).

### 4.6 `api/ideate.py` (extend)
- `GET  /api/ideate/agents` — selectable built/imported agents.
- `GET  /api/ideate/tools?project=` — enabled tool catalog for scope.
- `GET  /api/ideate/jira-meta?project=` — issue types, epics, available fields.
- `POST /api/ideate/agent/run` — **SSE** trace + final stories.
- `POST /api/ideate/push` — rich field mapping, per-card or batch; audits each create.
- `GET  /api/ideate/audit?limit=` — recent Ideate actions for the Activity panel.

## 5. Data Model (Pydantic)

- **`Story`** (extend): `title`, `description`, `acceptance_criteria: list[str]`,
  `priority`, `labels`, **+ `issue_type="Story"`, `epic_key?`, `story_points?`,
  `assignee?`, `components: list[str]`**.
- **`AgentEvent`** (new): `{ type: "thinking"|"tool_call"|"tool_result"|"stories"|"final"|"error",
  text?, tool?, args?, result?, stories? }`.
- **`ToolSpec`** (new): `{ name, kind, description, params, mutating }`.
- **`WizardState`** (frontend-owned, posted per call): `{ scope, context, stories,
  model, selected_agents, enabled_tools }`. No DB table.

## 6. Jira Field Mapping & Graceful Degradation

1. Call `get_create_meta(project)` when entering Step 4/5.
2. Card renders and sends **only fields the project's create screen supports**.
3. Acceptance criteria → configured AC custom field if present; otherwise appended to
   description as a checklist.
4. Epic link / story points / assignee / components omitted silently when unavailable.
5. Issue type + epic pickers populated from `list_issue_types()` / `list_epics()`.
6. Push may be **per-card** or **batch**; each create produces one audit record
   (success and failure), so partial batches are fully traceable.

## 7. Frontend Components

- **`Ideate.tsx`** → shell: owns `WizardState`, renders stepper + current step + nav;
  allows jumping back to completed steps; confirmation dialogs gate mutations.
- **Step components** (new): `StepScope`, `StepGather`, `StepDraft`, `StepReview`, `StepPush`.
- **`AgentWindow.tsx`** (new): consumes `/agent/run` SSE; renders event stream;
  **collapsible, hidden by default**.
- **`StoryCard.tsx`** (extracted + upgraded): rich Jira action-item card with editable
  AC checklist and per-card actions.
- **`ActivityPanel.tsx`** (new): audit feed on Step 5 from `GET /api/ideate/audit`.
- Reuse existing SSE/`LogViewer` patterns and `lib/api` client.

## 8. Phasing

### P1 — Wizard shell + Jira fix + audit (no new agent engine)
- 5-step wizard shell + navigation.
- Upgraded action-item `StoryCard` + `createmeta`-driven field mapping.
- Real `push_stories()` field mapping; per-story audit on create.
- Uses current `draft_stories()` for drafting.
- **Ships the #3 fix and the audit requirement first.**

### P2 — Tool loop + agent window
- `ideate_agent.py` ReAct loop; `ideate_tools.py` integration tools (Glean/Confluence/Jira/MCP).
- SSE `/agent/run`; collapsible `AgentWindow`.
- Mutating-tool auditing via `call_tool()`.

### P3 — Agents-as-tools
- Register built/imported agents as tools; drafting-agent picker.
- Per-card agent-refine, split/duplicate assisted by agents.

## 9. Error Handling
- Agent loop: iteration cap; malformed action → reprompt then heuristic fallback;
  tool errors surfaced as `tool_result{error}`, loop continues.
- Jira: `createmeta`/push failures reported per story; partial batches fully audited.
- SSE: heartbeat + graceful client disconnect (mirror `api/agents.py`).
- All mutations gated by confirmation dialogs.

## 10. Testing
- **Backend unit:** ReAct JSON parser; tool registry dispatch + mutating auto-audit;
  Jira field mapping + degradation; audit rows written on create (success + failure).
  Mock Jira/MCP/providers.
- **Frontend:** step navigation/guards; SSE event rendering; card edit + field-degrade
  behavior; confirmation gating.
- **Manual smoke:** end-to-end draft → review → push against a test Jira project;
  verify audit entries.

## 11. Reuse Summary
- `agentic_cli.tracker.record_activity` — audit spine.
- `agentic_cli.llm.factory.get_llm_provider` — drafting + ReAct loop.
- `ideate_service.search_source` — integration search tools.
- `jira_service` — createmeta, epics, issue types, create.
- `agent_service.test_agent` / `discover_agent_projects` — agents-as-tools.
- SSE pattern from `api/agents.py`; `LogViewer`/SSE hooks on the frontend.
