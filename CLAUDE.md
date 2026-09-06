# Keel — orientation for AI assistants

**Keel** is the product and the CLI (`keel`). **keelyard** is this repository —
one git repo holding the CLI, dashboard, desktop app, skills registry, MCP
servers, and KG infrastructure.

Start with [`README.md`](README.md) for what the product does, and
[`CONTRIBUTING.md`](CONTRIBUTING.md) for how to work in it. This file covers
what is easy to get wrong.

## Layout

| Path | What |
|---|---|
| `agentic-cli/` | The `keel` CLI and the bulk of the domain logic |
| `dashboard/backend/` | FastAPI app; imports `agentic_cli` directly |
| `dashboard/frontend/` | React + Vite SPA |
| `desktop/` | Electron shell; freezes the backend into a sidecar |
| `skills/` | Skills registry — `skills/<name>/SKILL.md` |
| `mcp-servers/` | MCP servers + docker-compose |
| `kg-infrastructure/` | Neo4j, LightRAG, Postgres graph |

## Glossary

This vocabulary is dense and mostly unguessable — *domain*, *product*, *meta-repo*
and *context-meta repo* are four different things, and three of them are git
repositories. Written as a definition list so `keel domain extract` can lift it
into the domain's own glossary; keep that shape if you add to it.

**Keel** — the product and the CLI (`keel`).

**keelyard** — this repository: one git repo holding the CLI, dashboard, desktop
app, skills registry, MCP servers and KG infrastructure.

**Product** — the top registration tier. Groups domains and owns the governance
floor they are measured against.

**Domain** — a scoped area within a product, tying together a Jira project, a
Bitbucket project, a Confluence space and selected repositories.

**Context-meta repo** — the per-domain git repository created by `keel domain
init`, holding both the context (`.domain/`) and the meta layer (`.platform/`
governance, `.agents/` personas, `repos/` submodules).

**OKF** — Open Knowledge Format, the Markdown-native knowledge bundle format the
KG exports to and reads from.

**Skill** — a packaged instruction set at `skills/<name>/SKILL.md`, injected into
a repo so a coding agent picks it up.

**Persona** — a role (dev, tech-lead, QA, SM, BA) that skills and workspaces are
generated for.

**Watcher** — a binding from a trigger to an agent handler. The runtime polls the
source and dispatches through the same governance seam a manual run uses.

**Trigger** — an adapter that emits events for a watcher. Registered against a
protocol, never added as a branch in a dispatch chain.

**Engine** — an execution backend (Devin, Devin CLI, local, an IDE) selected
through `execution.registry`, which is the single build-governance seam.

**Fetcher** — an adapter in `retrieval.py` that resolves one *reference* to the
content and version behind it. Registered against a scheme (`domain`, `repo`,
`confluence`, `okf`, `governance`), never branched on.

**Tracked source** — one row in a domain's `domain_docs`, addressed by a
retrieval *ref* rather than a Confluence page id. The scheme picks the fetcher,
so a Kaggle competition and a Confluence page reach extraction identically.

**Retriever** — a named search index (FAISS, FTS, KG) an agent binds to and
queries, registered in `retrievers.py`. Distinct from a fetcher: a retriever
answers "what is relevant to this question" and returns many hits; a fetcher
answers "what is at this address" and returns one document.

**Context read** — one row in the KeelTrace ledger: source, operation, entity,
bytes, latency, status. Tier one, and safe to retain.

**Payload** — the retrieved text behind a context read. Tier two, written only
when `KEEL_PAYLOAD_STORE` names a backend, masked and capped when it is.

**Provenance stamp** — the `provenance:` and `reviewed:` frontmatter on a
`.domain/` file, saying where its content came from and whether a human approved
it.

**Placeholder** — filler `domain init` writes when the KG returns nothing. Never
served as context, because an agent handed it reads it as a domain fact.

**Held instruction** — an extracted instruction carrying a name, an email or a
credential. Its text is never written: the review file records only the kinds of
identifier found, plus a citation pointing at the source.

**Drift** — any signal that context has moved away from what it was drawn from:
a page revised upstream, a repo file edited, a template advanced, an approved
instruction whose source no longer yields it.

**Template drift** — the three-way comparison of a meta-repo file against its
generation baseline and a fresh render of the current template, which is what
separates a template change from a local edit.

**Semantic drift** — what a source's change *did* to the instructions drawn from
it: unchanged, reworded, contradicted, or no longer supported there. A digest
says a file moved; only this says whether the move mattered. `keel domain diff`.

**Unverified reword** — a source that says an approved instruction again, in
different words, with nothing having ruled on whether the two still agree. Token
overlap cannot tell agreement from contradiction, so this asks a human and never
fast-forwards.

**Fan-out plan** — a dry run of one source's change across every domain drawing
on it: which domains it lands in unattended, which owe a human a decision, and
which could not be ruled on. `keel domain plan`.

**Review queue** — the escalations from a fan-out plan, addressed to the owner
recorded in each domain's own `domain.yaml`. One owner gets one queue across
every domain and source; a domain recording no owner is reported, never
assigned. `keel domain queue`.

**Finding** — one statement about one component's own surface (a shared
credential, model egress), carrying what it does *not* claim. Never composed
into a session-level judgement; that composition is the governance floor's.

**Readiness score** — the eight-dimension answer to "could a competent new
teammate ship from this domain?", produced by `keel domain score`.

**Governance floor** — the product-level governance values a domain may tighten
freely and may not loosen without a recorded exception.

**Exception** — an auditable waiver in the product meta-repo's `exceptions/`
ledger, permitting one domain to sit below the floor for a stated reason.

**Guard terms** — site-specific strings supplied through `$KEEL_GUARD_TERMS` or a
git-ignored `.guardterms`. Never committed: a guard list in the repository would
disclose exactly what it protects.

## Commands

```bash
./setup.sh && source .venv/bin/activate     # first time
keel doctor                                 # verify the environment

# Tests
cd agentic-cli      && python -m pytest tests/ -q
cd dashboard/backend && python -m pytest tests/ -q
cd dashboard/frontend && npx tsc --noEmit

bash scripts/check-no-company-data.sh --all # guardrail; also runs in CI
```

### The test suites are not fully green, and CI knows which parts

As of September 2026, on a **pristine checkout of `main`**:

- `agentic-cli` — 1433 pass, **28 fail**
- `dashboard/backend` — 193 pass, **4 fail** (all `test_neo4j_preflight`, which
  needs a live Neo4j — they pass nowhere without one, including CI, which is why
  that file is excluded there)

Down from 47 and 6. The triage that got there fixed three causes rather than
individual tests: `pytest-asyncio` was missing from the `dev` extra, so fourteen
async tests reported "async def functions are not natively supported" and counted
as failures; `kg/tool_generator.py` referenced `CLI_NAME` in an f-string template
without importing it, so generating any tool raised; and one suite shelled out to
whatever `python` was on `PATH` instead of `sys.executable`.

**There is now a blocking CI workflow** (`.github/workflows/tests.yml`). It
excludes the eight files that still fail, by name, so the rest can gate a pull
request honestly. Excluding a file is a visible debt entry; marking the whole job
`continue-on-error` would have hidden every future regression alongside the known
ones, which is worse than having no CI.

Still excluded, and why, for whoever picks this up: `test_context_builder`,
`test_domain_context`, `test_eval_commands`, `test_kg` (data-source and pipeline
integration), `test_external_registries` and `test_project_commands` (need
registry files discoverable from the working directory), `test_skill_evaluator`
(wants a judge credential), and `test_version` (expects an installed console
script under an older package name).

**Before concluding you broke something, measure against a clean worktree:**

```bash
git worktree add --detach /tmp/pristine origin/main
cd /tmp/pristine/agentic-cli && python -m pytest tests/ -q   # compare counts
git worktree remove /tmp/pristine --force
```

## Invariants worth not violating

**Governance runs through seams, not scattered checks.** Agent sessions go
through `execution.registry.create_session`; repository onboarding through
`keel code onboard`. New execution paths route through those rather than
around them. See [`docs/GOVERNANCE_LAYERS.md`](docs/GOVERNANCE_LAYERS.md).

**Vendor neutrality is registry-driven.** Code-assist tools, execution
engines, and watcher triggers are all registries. Add an adapter; do not add a
branch to a dispatch chain. Sixteen hardcoded branches were removed once
already — do not reintroduce the pattern.

**The desktop app redistributes its dependency tree.** New Python or Node
dependencies ship inside the installers, so their licenses bind the artifacts.
Check the license before adding one; see [`NOTICE`](NOTICE).

**Context reads are traced.** Retrieval goes through sensors that record what
an agent read (`agentic_cli/tracing.py`). If you add a retrieval path, it
should record. See [`docs/KEELTRACE.md`](docs/KEELTRACE.md) — particularly the
ContextVar/thread constraint, which is subtle and only fails from the
dashboard.

**Fetching a ref goes through the seam.** `retrieval.fetch()` is the one place
a reference becomes content, and it records the read for you. Add a fetcher for
a new scheme; do not add a fourth place that knows how to read a source. Its
five outcomes are not decorative — `UNAVAILABLE` (we could not ask) must never
collapse into `MISSING` (nothing is there), because that difference decides
whether an approved instruction gets flagged absent.

**Never commit** secrets, internal hostnames, employer-specific identifiers,
or real domain/KG data. The pre-commit hook and CI enforce this. Site-specific
terms are injected via `$KEEL_GUARD_TERMS` or a git-ignored `.guardterms` —
never hardcoded, because the guard file itself would then disclose them.

## Conventions

- Match the surrounding code's comment density, naming, and idiom.
- Commit messages explain **why**, and what was ruled out. The diff shows what.
- A bug fix without a regression test tends to come back.
- Telemetry is never load-bearing: a tracing failure must not break the
  operation it observes.

## Current work

[`docs/KEELTRACE.md`](docs/KEELTRACE.md) — what has shipped (P1–P7: sensors,
the read side, the eval feed, the playground, the retrieval seam, semantic
drift, token accounting and cost) and what is genuinely left.

Nothing is blocked on a decision now — the tier-two storage question that used
to sit here was settled by building both backends and leaving the store off
until an operator names one.
