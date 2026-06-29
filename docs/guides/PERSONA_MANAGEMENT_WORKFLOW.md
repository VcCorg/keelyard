# Persona Management Workflow

How role-based **persona skills** are defined, generated, and extended across
products and domains.

A *persona* is a role-scoped `SKILL.md` document that AI assistants consume to
work a domain from a specific viewpoint (Developer, QA, Scrum Master, etc.).
Personas are **data-driven**: built-in defaults ship with the platform, and each
product team can add its own (e.g. Tech Lead, Product Owner) without code
changes.

---

## Tiers

| Tier | Source | Purpose |
|------|--------|---------|
| **Built-in defaults** | `agentic_cli/skill_generator.py` | Baseline personas every domain gets: `domain`, `dev`, `qa`, `sm`, `ba` |
| **Product catalog** | `product-<slug>-meta/.platform/config/personas.yaml` | Per-product customization: toggle built-ins + add product-specific personas |
| **Domain output** | `domain-<slug>-meta/.agents/skills/personas/<id>/SKILL.md` | The rendered persona skills, versioned with the domain meta-repo |

**Effective catalog** = built-ins filtered by `defaults_enabled` + the product's
custom `personas` (a custom persona whose `id` matches a built-in overrides it).

---

## Content engine (hybrid)

- Every persona is always rendered from a **deterministic skeleton** (front
  matter + declared `sections` + a shared domain-context appendix). Works fully
  offline and is reproducible.
- A custom persona may set `ai_enrich: true`. When generation is run with
  `--enrich` **and** a model is available, its content is enriched via the
  onboard agent. If no model is configured, it **silently falls back** to the
  skeleton — generation never fails.
- Built-in personas use the platform's rich generators (unchanged output).

---

## `personas.yaml` schema

Location: `product-<slug>-meta/.platform/config/personas.yaml`

```yaml
version: 1
defaults_enabled: [domain, dev, qa, sm, ba]   # which built-ins to generate
personas:                                       # product-specific additions
  - id: tech-lead
    label: Tech Lead
    description: Architecture direction, ADRs, review standards
    ai_enrich: true
    sections:
      - title: Responsibilities
        body: |
          - Own technical design and ADRs
          - Set and uphold the code-review bar
      - title: Review Standards
        body: |
          - Require tests for all behavior changes
          - Block on security and data-migration risks
  - id: product-owner
    label: Product Owner
    description: Backlog ownership, prioritization, acceptance
    sections:
      - title: Responsibilities
        body: |
          - Own and prioritize the backlog
          - Define acceptance criteria
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Kebab-case; becomes the folder name and `role` in front matter |
| `label` | yes | Human-readable title |
| `description` | no | One-line summary |
| `sections[].title` / `sections[].body` | no | Markdown content blocks |
| `ai_enrich` | no | Enrich via LLM when run with `--enrich` (default `false`) |

A starter `personas.yaml` (all built-ins enabled, commented examples) is written
automatically by `dva product init-meta`.

---

## Workflows

### 1. New product — get default personas

```bash
dva product create CWOW
dva product init-meta CWOW          # writes .platform/config/personas.yaml (defaults)
```

### 2. New domain — personas generated during scaffolding

```bash
dva domain create Facility --product CWOW
dva domain init-meta cwow-facility  # renders personas into .agents/skills/personas/
```

`init-meta` resolves the effective catalog from the product meta-repo and
generates each persona automatically — **no separate step required**.

### 3. Add a product-specific persona (e.g. Tech Lead)

Add it to the product catalog via the CLI (covers the common case):

```bash
dva product persona add CWOW --id tech-lead --label "Tech Lead" \
    --description "Architecture direction" \
    --section "Responsibilities::- Own ADRs" \
    --section "Review Standards::- Require tests for behavior changes" \
    --ai-enrich
dva product persona list CWOW            # show effective catalog
dva product persona remove CWOW tech-lead
```

For rich, multi-line content, edit `personas.yaml` directly (see schema above).

Then regenerate into a domain meta-repo:

```bash
dva domain regen-personas cwow-facility            # all personas
dva domain regen-personas cwow-facility -p tech-lead   # just one
dva domain regen-personas cwow-facility --enrich       # AI-enrich ai_enrich personas
```

`regen-personas` is safe to re-run; it overwrites existing persona files.

### 4. Disable a built-in for a product

Remove it from `defaults_enabled` in the product's `personas.yaml`, then run
`dva domain regen-personas <domain>`.

---

## Dashboard (UI)

Persona skills are managed through a single **role-aware** component,
`PersonaSkillsPanel` (`dashboard/frontend/src/components/PersonaSkillsPanel.tsx`),
surfaced in two places:

| Entry point | Who | Capabilities |
|-------------|-----|--------------|
| **Domain Onboarding → Skills step** (`/onboarding`) | Admin only (page is `minRole: admin`) | Full panel, including product-level controls |
| **Persona Skills page** (`/skills/personas`) | All team members | Pick a domain, then review + recreate repo-level skills |

The panel renders three sections, gated by `useUser().role`:

**1. Review generated persona skills (all users)**
Lists every `SKILL.md` under `domain-<slug>-meta/.agents/skills/personas/`, with
its source (built-in vs product) and a **View** action to read the rendered
content. Backed by `GET /api/domains/{slug}/personas` and
`GET /api/domains/{slug}/personas/{id}`.

**2. Recreate repo-level skills (all users)**
Regenerates personas into the selected domain's meta-repo — all of them or a
checkbox-selected subset, with an optional **AI-enrich** toggle. Streams
`dva domain regen-personas <slug>` over SSE
(`GET /api/domains/{slug}/regen-personas/stream`).

**3. Product-level persona catalog (admin only)**
Shows the effective catalog and lets admins **add/remove** product-specific
personas and **regenerate across all domains** in the product. Non-admins see a
read-only notice. Backed by `GET/POST/DELETE /api/domains/products/{name}/personas`
and `GET /api/domains/products/{name}/regen-personas/stream`.

> Access model follows the existing dashboard pattern: roles live in
> `UserContext` and controls are gated in the UI. Product/domain creation stays
> admin-only; repo-level skill regeneration is open to all via the standalone
> Persona Skills page.

---

## Reference — key modules

| File | Responsibility |
|------|----------------|
| `agentic_cli/meta_repo/config.py` | `PersonaSpec`, `PersonaSection`, `PersonasConfig`, `BUILTIN_PERSONA_IDS` |
| `agentic_cli/persona_catalog.py` | `resolve_personas()`, `load_product_personas()`, `add_product_persona()`, `remove_product_persona()` |
| `agentic_cli/commands/product.py` | `product persona add` / `list` / `remove` |
| `agentic_cli/skill_generator.py` | `builtin_persona_specs()`, `render_persona()`, `generate_personas()` |
| `agentic_cli/meta_repo/scaffold.py` | Generates personas during `scaffold_domain_meta_repo` |
| `agentic_cli/meta_repo/product_scaffold.py` | Writes starter `personas.yaml` on `product init-meta` |
| `agentic_cli/commands/domain.py` | `domain init-meta`, `domain regen-personas`, `domain gen-skills` |

---

## Design notes

- **Output lives in the meta-repo** (`.agents/skills/personas/<id>/SKILL.md`),
  versioned alongside the domain — not in a global skills tree.
- **Backward compatible**: with no `personas.yaml`, only the 5 built-ins are
  generated (deterministic, no behavior change).
- **Extensible**: new roles are pure data (`personas.yaml`) — adding Tech Lead or
  Product Owner requires no Python changes.
