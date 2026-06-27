# Methodology + Governance Integration — Design & Dev Action Plan

**Status:** Approved baseline — implementation in progress
**Source baseline:** `integration-design-baseline.docx` (Agentic Development Platform — Methodology + Governance Integration, v0.1)
**Scope:** Layer an automatic engineering-discipline methodology (inner loop) onto the
enterprise-governed agent platform (outer loop), generated automatically as part of
product/domain onboarding so every development session inherits both by default.

---

## 1. Thesis

Two complementary systems are fused as **nested loops**:

| Loop | Owned by | Responsibility |
|------|----------|----------------|
| **Inner loop** | Methodology Framework (superpowers) | *How* each task is built: spec-first, TDD, micro-tasks, two-stage review |
| **Outer loop** | Enterprise Brain Hub (platform) | *What* may ship and how: governance gates, environments, infra, issue tracking |

A change is **done** only when it passes both: engineering review (inner) **and** the
relevant environment/promotion gates (outer).

## 2. Three-Tier Layering

"Common" is two different things, so the model has three tiers, not two:

| Tier | Loop carried | Lives in | Varies by |
|------|--------------|----------|-----------|
| **Org baseline** | Inner loop (spec/TDD/review) | One org-wide methodology repo, **referenced (pinned)** | Nothing |
| **Product** (e.g. ABC) | Outer loop — *shared* (definition-of-done, promotion path `dev→qa→uat→prd`, pipeline standards) + **crosswalk** + **exceptions ledger** | `product-<abc>-meta` | Product |
| **Domain** (e.g. a1, a2) | Outer loop — *specific* (gates, Jira/BB mapping, SLAs, security, KG context) | `<domain>-domain-context` + `domain-<slug>-meta` | Domain |

### Decisions locked in

1. **Inner-loop home:** a single **org-wide repo, referenced** (not copied per domain).
   Improving it once improves it everywhere.
2. **Meta-repo shape:** **product meta-repo + separate domain repos** (extends the
   existing per-domain submodule pattern).
3. **Topology:** **flat fan-in** — a working repo pins all applicable layers directly
   (no deep submodule nesting), making methodology provenance auditable per commit.
4. **Composition:** mirror the existing domain-context dual pattern — a static composite
   skill (offline fallback) **plus** a live MCP path.
5. **Precedence cascade:** **domain > product > inner-loop baseline** (reuses the existing
   `skill_priority_order: [validated, customized, injected]` philosophy).
6. **Crosswalk home:** the **product meta-repo** (one product-wide checkpoint↔gate map).
7. **Override policy:** domains may **tighten** freely; **loosening requires a recorded,
   auditable exception** (the exceptions ledger), ideally with an expiry.

### Resulting submodule chain in a working repo (flat fan-in, all pinned)

```
org-methodology (inner loop)         ── pinned, tighten-only floor
product-<abc>-meta (outer shared)    ── DoD, promotion path, crosswalk, exceptions
<domain>-domain-context (outer spec) ── gates, Jira/BB, SLAs, KG context
        │ all pinned into ▼
<working-repo>  →  .skills/methodology/SKILL.md  (auto-triggered composite)
```

## 3. What Already Exists (do not rebuild)

| Design concept | Already implemented as | Location |
|----------------|------------------------|----------|
| Inner-loop baseline | superpowers skills auto-injected | `domain init-context` → `bootstrap_domain_skills` |
| Domain-context repo | `<domain>-domain-context` (KG + skills) | `domain init-context` |
| Domain meta-repo | `domain-<slug>-meta` (.platform/config, repos/, docs, Makefile, hooks) | `domain init-meta` → `meta_repo/scaffold.py` |
| Outer-loop gates | `governance.yaml` (`GovernanceConfig`) | `meta_repo/config.py` |
| Precedence cascade | `skill_priority_order` | `skills.yaml` / `SkillsConfig` |
| Working-repo composition | `code onboard --domain --domain-context-repo --use-domain-skills --link-meta-repo` | `commands/code.py` |
| Enforcement teeth (partial) | pre-push branch-name hook | `scaffold.py:_write_pre_push_hook` |
| Backend CLI invocation | two-lane proxy (library import + subprocess/SSE) | `dashboard/backend/src/services/*` |
| Onboarding UI | 5-step stepper (Domain→Repos→Docs→Skills→Scaffold) | `frontend/src/pages/DomainOnboarding.tsx` |

## 4. Gaps to Close

1. **Product tier has no generator** — `product` is CRUD-only. Need a product meta-repo
   holding shared outer-loop + crosswalk + exceptions ledger.
2. **Inner-loop is injected per-domain**, not referenced from one pinned org source.
3. **`governance.yaml` is static** — no promotion path, no inner↔outer crosswalk, no
   exceptions.
4. **No "loosen-requires-justification" enforcement.**

## 5. Implementation Plan (phased)

### Phase 1 — CLI core (product tier)
- `meta_repo/product_scaffold.py`: scaffold `product-<name>-meta` with
  `.platform/config/` (`product.yaml`, `governance.yaml` shared, `crosswalk.yaml`),
  `outer-loop/product/` (DoD, promotion-path, pipeline-standards), `exceptions/`,
  `docs/`, Makefile; reference org-methodology as a pinned submodule.
- Extend `GovernanceConfig` with `promotion_path` and `checkpoint_gate_map` (crosswalk).
- Add `ExceptionEntry` model + ledger read/write (`exceptions/<id>.yaml`:
  rule, reason, scope, owner, created_at, expires_at, status).
- New commands in `commands/product.py`:
  - `product init-meta <NAME> [--org-methodology <url>]`
  - `product exceptions add|list <NAME> ...`
- Thread `--product-meta <url>` into `domain init-meta` so domain meta references product.

### Phase 2 — Dashboard backend
- `domain_service.py`: add `stream_product_command()` (clone of `stream_domain_command`).
- `api/domain.py`: add SSE endpoints
  `/products/{name}/init-meta/stream`, `/products/{name}/exceptions/stream`.
- Read-lane GET endpoints: `/products/{name}/governance`, `/products/{name}/exceptions`
  (parse scaffolded YAML via `MetaRepoConfig`).
- `cli_service.py` already whitelists `product`; no change (init-meta is non-destructive).

### Phase 3 — Dashboard frontend
- Add **Product step 0** to the onboarding stepper (`Product → Domain → Repos → Docs →
  Skills → Scaffold`); product step scaffolds `product init-meta` and shows governance.
- Thread the product-meta URL into the domain Scaffold step (`--product-meta`).
- **Governance panel** — render `governance.yaml` + crosswalk as a read-only table.
- **Exceptions ledger panel** — file a waiver (rule/reason/scope/expiry) and list
  active/expired waivers with status badges.
- Visualize the submodule/governance chain so teams see what governs them.

### Phase 4 — Docs & enablement
- This design doc (done).
- UI training doc: `docs/guides/UI_ONBOARDING_GUIDE.md`.

## 6. Risk / Sequencing

| Item | Risk | Notes |
|------|------|-------|
| Product scaffolder | Medium | Mirrors existing domain scaffold |
| GovernanceConfig / ExceptionEntry | Low | Additive dataclasses |
| Backend proxy + endpoints | Low | Proxy pattern generalizes cleanly |
| Frontend product-first UX | Medium | New panels; reuses StreamConsole/StatusBadge/useSSE |
| Enforcement (exception-aware gate) | Medium | `code validate` / pre-push extension |

## 7. Open Items (post-MVP)

- Exception expiry enforcement automation (scheduled check / CI gate).
- `code validate` extension to reject loosened inner-loop rules without a live exception.
- Org-methodology versioning & bump workflow.
- Crosswalk-driven CI gate generation (emit pipeline config from `crosswalk.yaml`).
