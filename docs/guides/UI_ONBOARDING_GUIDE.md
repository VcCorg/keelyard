# UI Onboarding Guide — Onboard a Product or Domain from the Dashboard

**Audience:** Engineers and team leads onboarding a new product or domain.
**Where:** The Agent Playground dashboard → **Domain Onboarding** page.
**What this gives you:** Every development session in the onboarded repos inherits
both the **inner loop** (engineering discipline — spec-first, TDD, review) and the
**outer loop** (governance — gates, environments, issue tracking) automatically.

> The dashboard is a thin proxy. Every button runs the real `dva` CLI underneath,
> so the UI and CLI always do the same thing. CLI equivalents are shown for each step.

---

## Mental model (read this first)

Work is organized in three tiers. You onboard top-down:

```
Product (e.g. ABC)            ← shared governance, crosswalk, exceptions ledger
  └── Domain (e.g. ABC-A1)    ← domain gates, Jira/Bitbucket, SLAs, KG context
        └── Repos             ← your actual code; inherits both tiers
```

- The **inner loop** (engineering methodology) lives once, org-wide, and is *referenced*.
- The **product tier** holds what all its domains share.
- The **domain tier** holds what is specific to one domain.
- A repo, once onboarded, **pins all applicable tiers** so you can always tell which
  rules governed any given commit.

The onboarding page is a **6-step stepper**:

| Step | What you do |
|------|-------------|
| 1. Product | Register the product, scaffold its meta-repo, review governance, file exceptions |
| 2. Domain | Create/select the domain under the product |
| 3. Repos | Link the domain's repositories |
| 4. Docs | Track Confluence pages for the domain |
| 5. Skills | Generate domain skills |
| 6. Scaffold | Create the context + meta repos (and link the product tier) |

---

## Step 1 — Product

This is the new top tier. Do it once per product.

1. **Register a product**
   - Enter a product name (e.g. `ABC`) and an optional description → **Create**.
   - *CLI:* `dva product create ABC --description "..."`

2. **Select the product**
   - Click the product chip. The governance and exceptions panels appear below.

3. **Scaffold the product meta-repo**
   - Click **Init product meta**. This creates `product-abc-meta` containing:
     - `governance.yaml` — shared gates (CI, review, tests, coverage)
     - `crosswalk.yaml` — the inner↔outer checkpoint→gate map
     - `outer-loop/product/` — definition-of-done, promotion path, pipeline standards
     - `exceptions/` — the governance waiver ledger
     - `inner-loop/` — submodule pinned to the org-wide methodology
   - Watch the CLI output stream in the console.
   - *CLI:* `dva product init-meta ABC`

4. **Review governance**
   - The **Governance (product tier)** panel shows the gates, the promotion path
     (`dev → qa → uat → prd`), and the crosswalk table (which engineering checkpoint
     maps to which promotion gate).

5. **File exceptions (only if needed)** — see [Exceptions](#filing-an-exception) below.

6. Click **Continue to Domain →**.

---

## Step 2 — Domain

1. Pick the product, then **create a new domain** (name + Jira/Bitbucket/Confluence
   links) or **select an existing one**.
   - A Bitbucket project key *or* URL is required.
   - The slug is auto-generated as `<product>-<domain>` (e.g. `abc-a1`).
   - *CLI:* `dva domain create A1 --product ABC --jira ABC --bb ABCX --confluence ABCSPACE`

2. Selecting/creating a domain advances you to **Repos**.

---

## Step 3 — Repos

1. The page previews repositories in the domain's Bitbucket project.
2. Select the repos that belong to this domain and link them.
   - *CLI:* `dva domain link-repo abc-a1 abc-a1-service`
3. Use **fetch-repos** (streamed) to bulk-pull from Bitbucket if needed.

---

## Step 4 — Docs

1. The page previews Confluence pages from the domain's space/URL.
2. Select the pages that hold domain requirements and track them.
   - *CLI:* `dva domain add-docs abc-a1 --all`
3. These docs feed the Knowledge Graph that powers domain context.

---

## Step 5 — Skills

1. Click to generate domain skills from the tracked context.
   - *CLI:* `dva domain gen-skills abc-a1`

---

## Step 6 — Scaffold

This produces the per-domain repos and **links the product tier**.

1. **Init context repo** — creates `abc-a1-domain-context` (KG business context +
   baseline methodology skills).
   - *CLI:* `dva domain init-context abc-a1`

2. **Link product meta-repo** checkbox — leave it **on** (it auto-detects the
   `product-abc-meta` you scaffolded in Step 1). This is what threads the shared
   outer-loop governance, crosswalk, and exceptions into the domain.
   - If the checkbox shows *"no product meta"*, go back to Step 1 and scaffold it.

3. **Init meta repo** — creates `domain-abc-a1-meta`, referencing the product meta
   as a submodule.
   - *CLI:* `dva domain init-meta abc-a1 --product-meta <path-or-url>`

4. Finally, onboard each working repo so it picks up the chain:
   - *CLI:* `dva code onboard --path ./abc-a1-service --domain abc-a1 --link-meta-repo --use-domain-skills`

---

## Filing an exception

Governance is **tighten-freely, loosen-with-justification**. If a domain or repo
needs to relax an inner-loop rule (e.g. skip TDD for a time-boxed spike), record it:

1. In **Step 1 → Exceptions ledger**, fill in:
   - **Rule** — what you're relaxing (e.g. `tdd`, `spec-first`)
   - **Scope** — `domain:abc-a1` or `repo:abc-a1-service`
   - **Reason** — the justification
   - **Owner** — your email
   - **Expires** — a date (strongly recommended; waivers should not be permanent)
2. Click **File waiver**. It appears in the ledger with an **active/expired** status.
   - *CLI:* `dva product exceptions add ABC --rule tdd --reason "spike" --scope domain:abc-a1 --owner you@example.com --expires 2026-07-27`
3. Review existing waivers any time in the same panel.
   - *CLI:* `dva product exceptions list ABC`

> Waivers are auditable: each is recorded in `product-abc-meta/exceptions/EX-*.yaml`,
> committed to git. Combined with pinned submodules, any commit can answer
> "what governed this, and what was deliberately waived?"

---

## Verifying the result

After onboarding, a working repo should contain (flat fan-in, all pinned):

```
<repo>/
├── .skills/
│   ├── domain-context/      ← domain business context (outer-loop specific)
│   └── methodology/         ← composite inner+outer guidance (auto-triggered)
├── repos/                   ← (in the domain meta) submodules:
│   ├── domain-context       ← <domain>-domain-context
│   └── product-meta         ← product-<product>-meta (shared outer loop)
└── .gitmodules
```

Provenance check:
```bash
git submodule status     # shows the exact pinned methodology/governance versions
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "no product meta" in Step 6 | Scaffold the product meta in Step 1 first |
| Governance panel says "No product meta-repo yet" | Run **Init product meta** in Step 1 |
| Exception won't save (404) | The product meta-repo doesn't exist yet — scaffold it |
| Bitbucket/Confluence previews empty | Check the domain's Bitbucket project key / Confluence space in Step 2 |
| Stepper steps greyed out | Steps 3–6 require an active domain; complete Step 2 first |

---

## Reference

- Design & architecture: [`docs/plans/METHODOLOGY_GOVERNANCE_INTEGRATION.md`](../plans/METHODOLOGY_GOVERNANCE_INTEGRATION.md)
- Domain context approach: [`docs/plans/DOMAIN_CONTEXT_GIT_REFERENCE_APPROACH.md`](../plans/DOMAIN_CONTEXT_GIT_REFERENCE_APPROACH.md)
- CLI command reference: `dva product --help`, `dva domain --help`, `dva code --help`
