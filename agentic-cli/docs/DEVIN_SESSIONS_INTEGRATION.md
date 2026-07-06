# Devin Sessions Integration — Design Doc

Status: **Draft / for review** · Owner: agentic-cli · Last updated: 2026-06-23

This document specifies how the KEEL Agentic CLI will **trigger and manage remote
Devin sessions** from the command line, grounded in the domain knowledge the CLI
already publishes to Devin. No code is committed yet — this is the contract and
phased plan for review.

---

## 1. Goal & non-goals

### Goal
Let a developer kick off a **fully context-loaded Devin coding session** from the
CLI with one command — automatically attaching the relevant OKF knowledge,
pinning the correct repo, and seeding a domain/ticket-scoped prompt — then track
and follow that session.

### Non-goals (v1)
- Replacing the Devin web UI for live session interaction.
- Running Devin sessions locally / self-hosting.
- Bi-directional sync of session transcripts into the KG (future).
- Auto-merging Devin PRs (out of scope; review stays human).

---

## 2. Background — what already exists

The CLI already integrates the **Devin Knowledge API** today:

| Piece | Location |
|---|---|
| HTTP client (auth, TLS/proxy, error surfacing) | `DevinClient` in `src/agentic_cli/kg/okf/devin.py` |
| API key resolution | `resolve_api_key()` → `$DEVIN_API_KEY` |
| TLS for corporate proxies | `resolve_verify()` → `$DEVIN_CA_BUNDLE` / `$DEVIN_VERIFY_SSL` |
| Knowledge push (idempotent, versioned) | `push_bundle()` |
| Concept → knowledge id map | `.devin-sync.json` (`load_sync`/`save_sync`) |
| Prompt-building primitives | `build_knowledge_entries`, `_trigger_for`, `_render_body`, `_repo_slug`, `_feature_of` |
| Command surface | `keel kg okf devin {list,prune,delete}` + `keel kg okf push-devin` |

**Key insight:** `.devin-sync.json` already maps `concept_id → knowledge_id`.
A CLI-triggered session can therefore attach *exactly* the right `knowledge_ids`
— this is the differentiator over a raw `POST /sessions` call.

```
Neo4j / OKF ──export──▶ bundle ──push-devin──▶ Devin Knowledge ──[THIS DOC]──▶ Devin Session
                                               (.devin-sync.json)             grounded + scoped
```

---

## 3. Devin Sessions API contract

Base URL `https://api.devin.ai/v1` · Auth `Authorization: Bearer <DEVIN_API_KEY>`
(same as the Knowledge API). **Field names below must be re-verified against
docs.devin.ai for the active org plan before implementation.**

### 3.1 Create session — `POST /v1/sessions`
Request body:

| Field | Type | Req | Notes |
|---|---|:--:|---|
| `prompt` | string | ✓ | The task. We compose this from OKF + Jira. |
| `title` | string | | Human label; we set `<DOMAIN> · <FREQ> · <area>`. |
| `snapshot_id` | string | | Machine snapshot (pre-installed deps). Per-domain config. |
| `playbook_id` | string | | Devin playbook to follow. Per-domain config. |
| `knowledge_ids` | string[] | | **Attach from `.devin-sync.json`.** |
| `secret_ids` | string[] | | Reference Devin-stored secrets; never inline. |
| `tags` | string[] | | `["keel", domain, freq_id]` for querying/idempotency. |
| `idempotent` | bool | | Reuse a session for the same prompt/tag instead of dup. |
| `max_acu_limit` | int | | Cost ceiling. Always set (config default). |
| `unlisted` | bool | | Visibility control. |

Response (shape):
```json
{ "session_id": "devin-xxxx", "url": "https://app.devin.ai/sessions/xxxx", "is_new_session": true }
```

### 3.2 Get session — `GET /v1/sessions/{session_id}`
Returns status + output. Fields we rely on:
- `status_enum` — one of `working` | `blocked` | `finished` | `expired` (confirm exact set).
- `structured_output` — JSON the session emits (e.g. PR URL, summary).
- `messages` — transcript entries.

### 3.3 Send message — `POST /v1/sessions/{session_id}/messages`
Body `{ "message": "..." }`. Used for follow-ups / unblocking.

### 3.4 List sessions — `GET /v1/sessions`
Supports filtering (e.g. by tag) — confirm query params. Used by `session list`.

### 3.5 Attachments — `POST /v1/attachments` (optional, v2)
Upload a file (e.g. a failing log, a spec PDF) and reference its URL in `prompt`.

---

## 4. Proposed CLI surface

Mirror the existing `devin_app` sub-typer under `keel kg okf devin`, adding a
`session` group. (A top-level `keel devin` alias can be added later.)

```
keel kg okf devin session create   --prompt "<text>" | --domain <slug> [--jira KEY]
                                   [--repo <slug>] [--knowledge-from-sync]
                                   [--knowledge-id ID ...] [--playbook ID] [--snapshot ID]
                                   [--tag T ...] [--max-acu N] [--idempotent]
                                   [--watch] [--dry-run] [--api-key ...]
keel kg okf devin session list      [--tag T] [--state working|finished|...]
keel kg okf devin session status    <session_id> [--watch] [--json]
keel kg okf devin session message   <session_id> "<text>"
keel kg okf devin from-jira         <ISSUE-KEY> [--domain <slug>] [--comment-back] [--watch]
```

### Behaviors
- **`--dry-run`** prints the composed prompt + payload (incl. resolved
  `knowledge_ids`, `pinned_repo`) without calling the API — mirrors `push-devin`.
- **`--watch`** polls `GET /sessions/{id}` until terminal state, rendering a live
  status line; prints `structured_output` (e.g. PR URL) on completion.
- **`--knowledge-from-sync`** loads the domain's `.devin-sync.json` and attaches
  every `knowledge_id` (optionally filtered by `--jira`/feature).
- **`from-jira`** = fetch ticket (Jira MCP) → resolve domain/FREQ concept →
  compose prompt → create session → optionally post the session URL back as a
  Jira comment (`--comment-back`).

---

## 5. Architecture

### 5.1 Client layer — extend `DevinClient`
Add to `src/agentic_cli/kg/okf/devin.py` (reuses auth/TLS/error handling):

```python
def create_session(self, payload: dict) -> dict:
    return self._request("POST", "/sessions", json=payload).json()

def get_session(self, session_id: str) -> dict:
    return self._request("GET", f"/sessions/{session_id}").json()

def send_message(self, session_id: str, message: str) -> dict:
    return self._request("POST", f"/sessions/{session_id}/messages",
                         json={"message": message}).json()

def list_sessions(self, params: dict | None = None) -> dict:
    return self._request("GET", "/sessions", params=params or {}).json()
```

### 5.2 Orchestration module — `kg/devin/sessions.py` (new)
Pure-logic, testable, no Typer:
- `build_session_prompt(bundle, concept_id|jira, ...) -> SessionSpec`
- `resolve_knowledge_ids(root, feature=None) -> list[str]` (reads `.devin-sync.json`)
- `resolve_pinned_repo(bundle, concept_id) -> str | None` (reuse `_repo_slug` + `implements` edge)
- `create_session(spec, api_key, dry_run, watch) -> SessionResult`
- `poll_session(session_id, ...) -> SessionResult`

### 5.3 Prompt composition (highest-value logic)
A composed prompt is assembled from existing primitives:
```
[Task]            <- Jira summary / concept title
[Context]         <- OKF concept body (_render_body, links cleaned)
[Acceptance]      <- Jira acceptance criteria / concept "# Acceptance Criteria"
[Constraints]     <- domain SLAs / security policies (KG MCP, optional)
[Repo]            <- pinned_repo (implements edge)
[Knowledge]       <- attached as knowledge_ids (not inlined)
```

### 5.4 Local session tracking — `.devin-sessions.json`
Parallel to `.devin-sync.json`, stored in the bundle root (or `~/.keel/devin/`):
```json
{
  "sessions": {
    "devin-xxxx": {
      "prompt_hash": "…", "domain": "cwow-facility", "jira": "CWOW-27901",
      "tags": ["keel","cwow-facility","CWOW-27901"], "url": "https://app.devin.ai/…",
      "created_at": "…", "last_status": "working"
    }
  }
}
```
Enables idempotency (skip if a live session exists for the same `prompt_hash`/tag)
and `keel agent status` integration.

### 5.5 Reuse matrix

| Concern | Reuse |
|---|---|
| HTTP/auth/TLS/errors | `DevinClient`, `resolve_api_key`, `resolve_verify`, `DevinError` |
| Knowledge grounding | `.devin-sync.json` via `load_sync` |
| Prompt building | `_render_body`, `_trigger_for`, `build_knowledge_entries` |
| Repo pinning | `_repo_slug`, `implements` edges |
| Bundle resolution | `_resolve_bundle` (kg_okf.py) |
| Per-domain config (playbook/snapshot/ACU) | `config.json` + `KGConfig` pattern |
| Activity tracking | `record_activity` |
| Jira/repo context | existing Jira/Bitbucket MCP clients |

---

## 6. Configuration

Per-domain defaults stored in CLI config (`~/.agent-cli-agentic/config.json` or
`KGConfig`):

```json
{
  "devin": {
    "default_max_acu": 10,
    "domains": {
      "cwow-facility": {
        "snapshot_id": "snap-…",
        "playbook_id": "playbook-…",
        "knowledge_folder": "cwow-facility-okf"
      }
    }
  }
}
```

Env vars (consistent with existing client):
`DEVIN_API_KEY`, `DEVIN_CA_BUNDLE`, `DEVIN_VERIFY_SSL`.

---

## 7. Security & cost considerations

- **API key** — never logged; resolved via `resolve_api_key`. `--dry-run` needs no key.
- **Secrets** — only `secret_ids` referencing Devin-stored secrets; never inline credentials in prompts.
- **PHI/PII** — prompts may include domain context; gate `from-jira` to avoid
  pasting raw PHI. Reuse the `security-reviewer` posture: redact ticket bodies of
  obvious PII before sending. **(Open question — see §10.)**
- **ACU cost** — always set `max_acu_limit`; surface the configured ceiling in the
  create confirmation. Consider `--yes` to skip confirm in CI.
- **Idempotency** — `idempotent: true` + `.devin-sessions.json` prevent duplicate
  spend on re-runs.
- **Enterprise gating** — session creation may require seats/approval; surface
  Devin's 4xx body via `DevinError` (already implemented).

---

## 8. Phased implementation plan

### Phase 1 — Foundation + MVP (smallest shippable)
- Extend `DevinClient` with `create_session`/`get_session`/`send_message`/`list_sessions`.
- `kg/devin/sessions.py`: `create_session`, `poll_session`, `.devin-sessions.json` I/O.
- Commands: `session create --prompt`, `session status [--watch]`, `session list`, `session message`.
- `--dry-run` + `record_activity`.
- Tests: prompt/payload building, dry-run, sync-file I/O, client (mocked httpx).

### Phase 2 — Domain/Jira grounding (high value)
- `--domain` + `--knowledge-from-sync` + repo pinning + prompt composition.
- `from-jira <KEY>` with `--comment-back`.
- Idempotency via tags + `prompt_hash`.

### Phase 3 — Workflow hooks
- `keel code onboard --devin-session` (remote familiarization / remote OKF gen).
- `keel agent status` shows remote Devin sessions beside local/imported agents.
- Optional: attachments (`POST /attachments`), structured-output → KG ingest.

---

## 9. Testing strategy
- **Unit (no network):** prompt composition, `knowledge_ids` resolution from a
  fixture `.devin-sync.json`, payload shape, idempotency hash, dry-run output.
- **Client:** mock `httpx` to assert method/path/body and error surfacing.
- **CLI:** Typer `CliRunner` for `--help`, `--dry-run`, arg validation.
- Follow existing conda quirk: run with `-p no:asyncio -p no:cacheprovider -o addopts=""`.

---

## 10. Open questions (need answers before Phase 1)
1. **Exact session field names/enums** — confirm `knowledge_ids`, `tags`,
   `idempotent`, `status_enum` values against docs.devin.ai for our plan.
2. **Plan entitlements** — does the org's Devin plan expose the Sessions API and
   how many concurrent sessions / ACU budget?
3. **PHI policy** — is it acceptable to send Jira ticket bodies (which may contain
   patient context) to Devin? Required redaction level?
4. **Command home** — keep under `keel kg okf devin session …`, or promote to a
   top-level `keel devin …` group?
5. **Session store location** — bundle-local `.devin-sessions.json` vs. a global
   `~/.keel/devin/sessions.json` (cross-domain `agent status`)?

---

## 11. Example end-state UX

```bash
# Trigger a grounded session straight from a Jira ticket
$ keel kg okf devin from-jira CWOW-27901 --domain cwow-facility --comment-back --watch
  ✓ Loaded FREQ CWOW-27901 from bundle (features/cwow-27901/...)
  ✓ Attached 6 knowledge entries from .devin-sync.json
  ✓ Pinned repo: cwow-facility-watercheck
  ▸ Creating Devin session (max 10 ACU)...
  ✓ Session devin-ab12  https://app.devin.ai/sessions/ab12
  ✓ Commented session link on CWOW-27901
  ⏳ working… working… finished
  ✓ Output: PR https://bitbucket.example.com/.../pull-requests/482
```
