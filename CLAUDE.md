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

- `agentic-cli` — 1186 pass, **28 fail**
- `dashboard/backend` — 181 pass, **6 fail**

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

[`docs/KEELTRACE.md`](docs/KEELTRACE.md) — what has shipped, what is next, and
the open decision blocking it.
