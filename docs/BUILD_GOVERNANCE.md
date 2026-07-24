# Per-Domain Build Governance

> New here? Start with [`GOVERNANCE_LAYERS.md`](./GOVERNANCE_LAYERS.md) for the
> one-page inner-vs-outer-loop overview; this doc is the deep-dive on the
> `build_governance` dial that runs the two outer-loop seams (session start +
> `keel code onboard`).

Makes the governance phase **binding** for the build phase: whether `keel code
onboard` and engine sessions (Devin, local, any future adapter) must follow the
governed, meta-repo-driven workflow — decided **per domain**, for adoption.

## The dial

Each domain's meta-repo carries it in `.platform/config/governance.yaml`:

```yaml
build_governance: warn        # off | warn | enforce
```

| Level | Meaning |
|-------|---------|
| `off` | Sandbox — anything runs silently (still audited/attributed). |
| `warn` | Ungoverned actions run but are **tagged** in the audit trail and CLI output. *(default)* |
| `enforce` | Ungoverned actions are **refused** at the seams. |

Work with **no domain at all** can't consult a domain's dial, so the
platform-wide admin default applies: **Admin → Skill governance → Build
governance (domain-less default)**, or `keel admin set-build-governance
<off|warn|enforce>`. Default: `warn`.

**A sandbox is just a domain set to `off`** — experiments still run under a
domain, so the audit trail never has holes and nothing needs a bypass flag.

## What "governed" means at each seam

- **Sessions** (`agentic_cli.execution.registry.create_session` — the single
  chokepoint for every engine): the spec must carry a `domain` whose meta-repo
  exists. Violations under `warn` are recorded in the session's audit details
  (`governance_level`, `governance_violations`); under `enforce` the launch
  raises `GovernanceViolation` (dashboard surfaces **403**).
- **Onboard** (`keel code onboard`): requires `--domain` with a meta-repo, and —
  when the domain registers repos in `repos.yaml` — the repo must be one of
  them. Same warn/enforce semantics; warnings print inline and tag the
  activity record.

## Rollout posture

1. Ship with `warn` everywhere: nothing breaks, and the audit trail starts
   measuring how much ungoverned build activity exists (filter on
   `governance_violations`).
2. Domain teams flip their own `governance.yaml` to `enforce` when ready.
3. PROD posture: admin default `enforce`, so even domain-less work is refused.

New meta-repos scaffold with `build_governance: warn` automatically
(`GovernanceConfig` default).
