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

### The test suites are not green, and that is expected

As of August 2026, on a **pristine checkout of `main`**:

- `agentic-cli` — 937 pass, **47 fail**
- `dashboard/backend` — 163 pass, **6 fail**

These are pre-existing (several look environmental — `pytest-asyncio` not
configured, `test_version` expecting an installed console script). There is
deliberately **no CI workflow running the Python suites**, because a blocking
job would go red on arrival; see the backlog note in `docs/KEELTRACE.md`.

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
