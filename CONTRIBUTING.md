# Contributing to Keel

Thanks for your interest. This guide covers what you need to get a change landed.

## Getting set up

You need [`uv`](https://docs.astral.sh/uv/) (Python 3.12), Node 22 (see
`dashboard/frontend/.nvmrc`; the toolchain accepts `^20.19.0 || >=22.12.0`), and optionally
Docker for the MCP/KG stack.

```bash
git clone https://github.com/VcCorg/keelyard.git
cd keelyard
./setup.sh                 # installs the CLI, configures skills, runs preflight
source .venv/bin/activate
keel doctor                # verify your environment
```

Enable the commit guard once per clone:

```bash
git config core.hooksPath .githooks
```

Try it without configuring anything: Keel ships a **test mode** and supports local
models, so every workflow is runnable with no API keys. See the Models section of
the [README](README.md).

## Before you open a pull request

```bash
# Backend
cd dashboard/backend && python -m pytest tests/ -q

# CLI
cd agentic-cli && python -m pytest tests/ -q

# Frontend typecheck
cd dashboard/frontend && npx tsc --noEmit

# Secret / internal-data guard (also runs in CI)
bash scripts/check-no-company-data.sh --all
```

## What we look for

- **Match the surrounding code.** Comment density, naming, and idiom vary by
  module; follow whatever the file you're editing already does.
- **Explain *why* in the commit message**, not just what. The diff shows what
  changed; the message should say what problem it solves and what you ruled out.
- **Cover the failure you fixed with a test.** A bug fix without a regression
  test tends to come back.
- **Keep changes focused.** Unrelated cleanups in the same PR make review harder
  and revert riskier.

## Architecture notes worth knowing

- **Governance runs through seams, not sprinkled checks.** Agent sessions go
  through `execution.registry.create_session`; repository onboarding goes through
  `keel code onboard`. New execution paths should route through those rather than
  bypass them. Start with [`docs/GOVERNANCE_LAYERS.md`](docs/GOVERNANCE_LAYERS.md).
- **Vendor-neutrality is deliberate.** Code-assist tools, execution engines, and
  watcher triggers are all registry-driven. Add an adapter; don't add a branch to
  a dispatch chain.
- **The desktop app redistributes its dependency tree.** New Python or Node
  dependencies ship inside the installers, so their licenses bind our artifacts.
  Check the license before adding one, and see [`NOTICE`](NOTICE).

## Adding things

- **A watcher trigger** — implement `TriggerProtocol` in
  `agentic-cli/src/agentic_cli/watchers/triggers/`; `bitbucket_pr.py` is the
  reference implementation.
- **A skill** — add `skills/<name>/SKILL.md`. Skills are subject to the security
  scanner and persona policy.
- **An MCP server** — see `mcp-servers/`.

## Never commit

Secrets, internal hostnames, employer-specific identifiers, or real domain/KG
data. The pre-commit hook and CI both enforce this. If you need to scan for
site-specific terms locally, see the guard section in the [README](README.md).

## Reporting bugs

Open an issue with what you expected, what happened, and the smallest steps that
reproduce it. Include your OS and whether you're on the desktop app or the dev
workspace — a good number of issues are platform-specific.

For anything security-sensitive, do **not** open a public issue; see
[SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
