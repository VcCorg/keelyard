# Persona-Scoped Skill Governance

Impose governance on skills **based on the user's profile**. A signed-in user
resolves to a *persona*; the domain's `skills.yaml` declares which skills each
persona may load and use; the profiler reports and gates on it.

This closes the loop between three things Keel already had but never connected:

| Layer | Source of truth | What it knew |
|-------|-----------------|--------------|
| Identity → role | SSO groups + `KEEL_ROLE_MAP` | who you are, what you may *do* |
| Personas | `personas.yaml` | role-based guidance docs (content only) |
| Skills | `make init` / skills profiler | which skills are loaded, by tier |

The missing link was **persona → skill policy**. That now lives in
`.platform/config/skills.yaml`.

## 1. The policy (`skills.yaml`)

```yaml
personas:
  default:                                    # any unlisted persona
    allow: [persona, domain-validated]
    deny: []
  dev:
    allow: ['*']
    deny: []
  qa:
    allow: [persona, domain-validated, 'testing-*']
    deny: ['*']                               # allow-list only
  ba:  { allow: [persona, domain-validated], deny: ['*'] }
  sm:  { allow: [persona, domain-validated], deny: ['*'] }
  domain: { allow: ['*'], deny: [] }
```

**Tokens** (used in `allow`/`deny`):

- tier names — `persona`, `agent-skill`, `domain-validated`, `linked:<repo>`, `local`
- `persona:self` (that persona's own SKILL) / `persona:<id>`
- skill-name globs — `testing-*`, `prod-deploy`
- `*` — everything

**Resolution per skill** — deny is split so an allow-list still works:

- a **specific** (non-`*`) deny always wins → `denied`
- else if any `allow` matches → `permitted`
- else → `out-of-policy` (not granted, but not a violation)

`deny: ['*']` is just the least-privilege *baseline*: it makes a persona
allow-list only. It does **not** by itself fail anything — only an explicit
(non-`*`) deny on a loaded skill is a hard violation.

## 2. User profile → persona

`persona_for(principal)` (in `agentic_cli.auth.persona`) resolves identity to a
persona, highest precedence first:

1. **explicit assignment** — `~/.keel/persona-assignments.json` (admin-controlled)
2. **SSO group map** — `KEEL_PERSONA_MAP='eng:dev,qa-team:qa'`
3. **role default** — `developer/maintainer/admin → dev`, `viewer → ba`
4. **fallback** — `ba` (least-privilege reader)

This mirrors how roles resolve, so the same SSO login that grants a role also
determines the persona that skill policy is evaluated against.

## 3. Where it's enforced

**Reporting + validate gate** (shipped):

```bash
make skills PERSONA=qa      # advisory: what QA is granted vs out-of-policy
make validate PERSONA=dev   # gate: exits non-zero if a loaded skill is DENIED
```

The profiler (`.platform/scripts/profile_skills.py`) is stdlib-only, so this
runs on any clone without installing Keel.

**Onboard enforcement** (optional, admin-toggled): when enabled, `keel code
onboard` installs only the skills the acting persona is permitted; denied and
out-of-policy skills are skipped and recorded in the onboard manifest. This
turns the advisory profile into physical access control.

Enforcement is **off by default** and controlled from the **Admin → Skill
governance** toggle (or the CLI):

```bash
keel admin set-enforcement enforce     # hard-block (admins only)
keel admin set-enforcement off         # advisory only (default)

# onboard resolves the acting persona from your profile; override with --persona
keel code onboard --path ./repo --domain cwow-facility --use-domain-skills --persona qa
keel code onboard --path ./repo --enforce-skills        # force on for one run
```

Precedence for the persona at onboard time: `--persona` > the profile resolved
by `persona_for(current_principal())`. Precedence for whether enforcement is on:
`--enforce-skills/--no-enforce-skills` > the admin `skill_enforcement` setting.
The policy is loaded from the domain meta-repo's `skills.yaml` when found, else
the built-in least-privilege default — so enforcement always has a rule set.

Because the default policy grants `domain-validated` skills to every persona, a
plain enforced onboard blocks nothing until a domain authors a real deny, or a
restricted persona (qa/ba/sm) pulls a non-validated skill — matching the
"green out of the box" posture.

## Design posture

- **Least-privilege default** — an unlisted persona gets only shared guidance +
  domain-validated skills; everything else is out-of-policy.
- **Green out of the box** — a fresh scaffold has no violations for any builtin
  persona. Hard failures happen only when a domain team authors a real deny
  (e.g. `dev` must never touch `prod-deploy`), which is exactly when governance
  should bite.
- **Derived, not authored** — `.platform/skills-manifest.json` is regenerated on
  every `make init`; the policy is the authored artifact, the manifest is the
  index it's evaluated against.
