# Domain onboarding readiness — gap analysis and plan

**A domain is ready to build on when a competent new teammate could ship from it.
Score it the way you'd score a team's onboarding guide, and use that score as the
gate.**

## Why this framing

Every team already maintains the artifact we are trying to synthesise: the
onboarding documentation they hand a new joiner. It is curated, kept current by
the pain of new hires hitting stale steps, and organised around what someone
actually needs before their first commit.

Keel today reads that material — when it reads it at all — as undifferentiated
Confluence pages, and measures the result by counting non-empty strings. Two
things follow:

1. **The highest-signal source in the org is ingested at the same weight as a
   meeting note.**
2. **"Onboarded" is not a claim about sufficiency.** A domain can finish
   `keel domain init` green with placeholder text in every context file.

The fix is one idea applied twice: *use the teammate onboarding corpus as a
first-class context source, and use the teammate readiness question as the
scoring rubric.*

## What we have today

The pipeline, and where each stage stands:

| Stage | Command / module | State |
|---|---|---|
| Register a domain | `keel domain create` | Solid. Records product, Jira/Bitbucket/Confluence coordinates. |
| Link repos | `domain link-repo`, `fetch-repos` | Solid, with an interactive picker. |
| Track docs | `domain add-docs` (`commands/domain.py:832`) | Better than it looks — walks a space or a page tree, and auto-discovers cross-space links by parsing `<ri:page>` macros, resolving each through CQL in a bounded thread pool. |
| Republish docs | `domain sync-docs` | Copies tracked pages into a managed `KEEL-<SLUG>` space; records `source_version`. |
| Build context | `domain init` (`commands/domain.py:1456`) | Queries the KG for six fixed aspects, scaffolds `.domain/`, injects skills, scaffolds the meta layer, bridges to the IDE. |
| Enrich to OKF | `kg okf enrich` | Pluggable `Source` ABC (`kg/okf/enrichment/source.py`) with three implementations: `code`, `confluence`, `graphify`. |
| Assemble workspace | `domain sync` | Federated graph refs, per-domain `flock`, persona skill. |
| Freshness | `kg/okf/provenance.py` | Deterministic bundle staleness from `graph.json` hashes — but only for **code**, not docs. |
| Governance | `.platform/config/governance.yaml`, `meta_repo/config.py:117` | Rich per-domain config: `promotion_path`, `checkpoint_gate_map`, `inner_loop_floor`, `build_governance`. |
| Template lifecycle | `meta_repo/template_{manifest,drift,upgrade,promote}.py` | Genuinely strong. 3-way hash classification, automated fast-forward, reviewed promotion back to a shared overlay. |
| Validation | `meta_repo/product_validation.py` | Structural checks over the **product** meta-repo, with a `Check`/`ValidationReport` shape worth reusing. |

## What is missing

### G1 — Tracked docs have no type

`domain_docs` (`tracker.py:127`) stores `source_page_id`, `source_space_key`,
`title`, `managed_page_id`, `source_version`, `synced_at`. There is no `doc_type`.

Downstream, `ConfluenceSource.list_concepts` (`kg/okf/enrichment/sources/confluence.py`)
maps **every** page to `type="Requirement"` under `references/<slug>`. An
onboarding runbook, an ADR, a retro, and a lunch-and-learn page produce
identical concept refs. Nothing can weight, route, or prioritise them.

### G2 — The six aspects are an invented taxonomy

`query_domain_kg` (`kg/domain_context.py:44`) asks for `business_context`, `slas`,
`integrations`, `security`, `performance`, `architecture`.

No team's onboarding guide is organised that way. Real ones answer: *how do I get
it running, who owns what, what's the deploy path, what breaks in production,
what does this word mean here, who do I ask.* The operational half — the half a
new joiner needs first — has no slot in the taxonomy, so even when the source
material is present it has nowhere to land.

### G3 — Repo-local onboarding docs are invisible

`CodebaseSource` (`kg/okf/enrichment/sources/code.py`) takes a **1500-character
README excerpt** and stops. `CONTRIBUTING.md`, `docs/`, ADR directories,
runbooks, `.github/` templates, Makefile targets — none are read.

These are the *better* corpus in one specific way: they are version-controlled,
reviewed, and diffable, so drift over them is detectable with machinery we
already have. Confluence is not.

### G4 — There is no readiness score, anywhere

`validate_product_meta` is the only validator in `meta_repo/`, it targets the
product tier, and it checks structure (does the YAML parse, do gates cross-
reference) rather than sufficiency. There is no `validate_domain_meta`, and
nothing in the codebase evaluates whether a domain's context can actually answer
anything.

The only quality signal emitted by the entire onboarding pipeline is this line
from `domain init`:

```
✓ KG domain context retrieved (3/6 aspects)
```

That is a count of non-empty strings.

### G5 — Placeholder fallback is silent and unmarked

If the KG query times out (`--kg-timeout`, default 20s) or returns nothing,
`scaffold_domain_context_repo` writes:

```
_Architecture details will be populated from the Knowledge Graph._
```

into `.domain/architecture.md`, and `init` proceeds to a green success panel.
Nothing downstream — not the skills, not the personas, not the Devin blueprint —
distinguishes placeholder from real content. **A fully "onboarded" domain can
contain zero context, and agents will build on it.** This is the most dangerous
gap in the list, and the cheapest to close.

### G6 — Doc freshness is recorded and never read

`source_version` is written by `add-docs` and `sync-docs`, and displayed in the
`domain docs` table. It is never compared against the live Confluence version.
The data to answer *"9 of your 40 tracked docs changed upstream since your
context was built"* is already in the database; nothing asks the question.

### G7 — Governance promotes as files, not as values

`template_promote` pushes an improved **file** into the shared overlay, from
where every other domain's next `template upgrade` fast-forwards it. That
machinery is good and it is done.

But governance is *values* in `governance.yaml`, and those have no equivalent
path. There is no way to raise `test_coverage_min` to 85 across eleven domains,
and — more importantly — no way to see which domains have drifted **below** the
product floor. `inner_loop_floor` is documented as "may only be tightened, never
loosened without a recorded exception" and nothing anywhere enforces or reports
that across the fleet.

## The rubric

Borrowed from what a good teammate onboarding guide is judged on, and mapped to
signals we can compute:

| Dimension | The teammate question | Computable signal |
|---|---|---|
| **Orientation** | What is this domain, and what words does it use? | Glossary concept coverage; entity terms in the KG resolvable to a definition. |
| **Runnable** | Can I get it running today? | Setup/build/test steps present, per linked repo, and *dated*. |
| **Ownership** | Where is ownership recorded? | A resolvable *pointer* per repo and concept (`CODEOWNERS`, a team handle, a rota) — never a person's name; unowned load-bearing concepts. |
| **Path to prod** | How does my change reach users? | `promotion_path` populated, gates mapped, deploy runbook linked. |
| **Hazards** | What will bite me? | Incident/runbook/gotcha docs present; known-issue concepts. |
| **Answerability** | Could I answer the questions a new joiner asks in week one? | Generate persona questions from the domain, retrieve, judge coverage. |
| **Groundedness** | Has a human stood behind this? | Three-state share: reviewed-and-finalized / auto-extracted / placeholder. |
| **Freshness** | Is it still true? | Upstream doc version delta (G6) + `graph.json` staleness (provenance). |

**Answerability** is the load-bearing one and it needs no golden dataset: the
personas already exist (`persona_catalog.py`, rendered into
`.agents/skills/personas/`), so their questions can be generated, retrieved
against, and judged.

## Plan

### Phase 0 — Stop lying about readiness — **shipped**

- Add `doc_type` to `domain_docs` and classify on ingest — `onboarding`,
  `runbook`, `adr`, `reference`, `requirement`, `other`. Heuristics on title and
  space first (cheap, auditable); LLM classification only as a fallback.
- Mark placeholder content. A `provenance:` frontmatter key on every generated
  `.domain/` file — `kg`, `doc:<page-id>`, `repo:<path>`, or `placeholder` — plus
  a `reviewed:` key carrying `no` until a human finalizes it (Phase 1).
  Nothing else in the plan works without this: every score below is a share of
  real content over total, and today those are indistinguishable.
- `domain init` reports placeholder count in its summary panel, and exits
  non-zero under `--require-context`.

*Deliverable:* a domain can no longer claim to be onboarded while empty.

### Phase 1 — Extract intent, review it, then finalize — **shipped**

**We capture the *intent* of an onboarding doc, never its text.** Bodies are read
in memory, reduced to instruction candidates, and discarded. Nothing raw is
written to disk, so this path needs no payload store, no retention policy, and no
redaction-at-rest design.

Two new sources feed the extractor, both behind the existing `Source` ABC:

- **`OnboardingDocsSource`** — pages classified `onboarding`/`runbook`, mapped to
  *operational* concept types (`Setup`, `Runbook`, `Glossary`, `Ownership`,
  `Hazard`) rather than the blanket `Requirement`.
- **`RepoDocsSource`** — `CONTRIBUTING.md`, `docs/`, `adr/`, `runbooks/`,
  `.github/`, Makefile targets. Version-controlled, so every concept carries a
  commit sha and is drift-checkable.

Extend the aspect taxonomy in `query_domain_kg` with the operational half:
`setup`, `ownership`, `deploy_path`, `hazards`, `glossary`.

#### The extraction contract

Each candidate is an abstracted imperative — *"run the bootstrap target before
the first build"* — carrying a type, a **citation as a pointer** (page id +
version, or path + sha; never content), a confidence, and a residual-risk list.

An instruction points at where a live value lives; it never carries the value.
*"Staging connection details are in the team's vault entry"* — not the string.
This is the same discipline as `template_overlay.plan_promotion`, which reports
every substitution it made **and** every residual it could not tokenize, for a
human to decide. Reuse that reporting shape rather than inventing one.

Two consequences worth stating plainly:

- **Guard terms are checked before the review file is written**, not after. The
  review artifact is git-visible, so a candidate carrying a `$KEEL_GUARD_TERMS`
  match is held and flagged, never auto-written — the same reasoning that keeps
  the guard file itself from hardcoding terms.
- **Dropping names makes the artifact more correct, not merely safer.** A person's
  name is the fastest-decaying fact in any onboarding doc. *"Ownership is recorded
  in `CODEOWNERS`"* stays true across three reorgs; *"ask the tech lead by name"*
  is wrong within a quarter.

#### The review step

Finalization is an onboarding step, not an audit afterthought:

```
keel domain add-docs      # track pages                      (exists)
keel domain extract       # in-memory read → review proposal (new)
      ← the domain's own team reviews and edits
keel domain finalize      # accept the reviewed set into .domain/
```

The proposal is a git-visible file in the meta-repo, every candidate defaulting
to **unreviewed** so nothing lands silently. The file is the source of truth; the
dashboard screen and a CLI picker (the `_interactive_doc_picker` pattern already
in `commands/domain.py`) are editors over it. Reviewing it as a PR is the natural
default — the team that owns the domain reviews its own instructions, exactly as
they would their onboarding guide.

`finalize` flips `reviewed: yes` and records the reviewer and timestamp **in the
tracker**, which already carries actor attribution — not in the git-visible
context file, which stays free of personal identifiers by construction.

#### Why the gate earns its keep

An unreviewed domain scores lower on groundedness (Phase 2). That is the
incentive that makes review actually happen, rather than a checkbox teams route
around.

It also changes what drift *means*. When a tracked page's version moves (G6), the
instructions citing it are flagged **stale-pending-review** rather than silently
re-extracted: the next `extract` proposes a diff against the finalized text and a
human accepts or rejects it. Same shape as `template upgrade` — fast-forward the
uncontested, escalate the rest.

### Phase 2 — `keel domain score` — **shipped, except answerability**

A `ValidationReport`-shaped scorecard (reuse the `Check`/`OK`/`WARN`/`FAIL`
pattern from `product_validation.py`) over the eight rubric dimensions, emitting
a per-dimension score, an overall grade, and a JSON artifact for the dashboard.

- Structural dimensions (ownership, path-to-prod, freshness, groundedness) are
  deterministic — no model call, no credential.
- Answerability needs a judge credential, so it degrades to `SKIPPED` rather
  than failing closed in test mode.
- Write the scorecard to `.platform/readiness.json` and surface a badge in the
  meta-repo README.

*Then the gate:* `create_session` consults the scorecard. Under
`build_governance: enforce`, a domain below threshold refuses to start build
sessions — the same seam that already carries governance, reading one more
signal.

### Phase 3 — Governance across the fleet — *not started*

- `keel governance status --all` — every domain's `governance.yaml` against the
  product floor, in one table. Which are stricter, which are looser, which
  looser ones lack a recorded exception. Read-only, deterministic, no new
  storage.
- `keel governance promote <key>=<value>` — the values analogue of
  `template promote`. Stages a per-domain PR, dry-runs the blast radius first,
  and refuses to *loosen* below `inner_loop_floor` without an `ExceptionEntry`.
- Feed both into the drift bus so a floor change fans out as events rather than
  a manual sweep.

## Sequencing rationale

Phase 0 is a prerequisite for honest measurement, not a nice-to-have: every
score in Phase 2 is a ratio whose denominator is currently unknowable. Phase 1
supplies the material those scores measure. Phase 3 is independent of 1–2 and
can run in parallel by a second pair.

## Open decisions

1. **Where does the scorecard live?** `.platform/readiness.json` in the
   meta-repo (git-visible, diffable, reviewable) versus the tracker (queryable
   across domains, but invisible to the team that owns the domain). Leaning
   git-visible with a tracker mirror for fleet views.
2. **Does a low score block or warn by default?** Proposal: warn at `warn`,
   block at `enforce`, matching the existing `build_governance` dial rather than
   inventing a second one.
3. ~~**How do we ingest human-written docs without persisting names, internal
   hostnames, and credentials-adjacent detail?**~~ **Settled** — we capture the
   *intent* of an instruction and discard the source text, with a human review
   step to finalize (Phase 1). Bodies never reach disk, so this no longer needs
   to be settled alongside the KeelTrace tier-two payload-store decision; that
   one stays open on its own, scoped to the eval feed.


## What shipped

| Piece | Where |
|---|---|
| Doc typing + freshness columns | `tracker.py` v14; `onboarding/classify.py` |
| Intent extraction, bodies discarded | `onboarding/extract.py`, `onboarding/sources.py` |
| Residual-risk scan, held candidates | `onboarding/redaction.py` |
| Review proposal, verdicts preserved | `onboarding/proposal.py` |
| Provenance + reviewed frontmatter | `onboarding/provenance.py` |
| Eight-dimension scorecard | `onboarding/readiness.py` |
| `classify-docs / extract / review / finalize / score` | `commands/domain_onboarding.py` |
| Read models, drift, knowledge map | `dashboard/backend/src/services/onboarding_service.py` |
| Review + Readiness wizard steps | `dashboard/frontend/src/components/Domain{Review,Readiness}Panel.tsx` |
| Knowledge flow visualisation | `dashboard/frontend/src/components/KnowledgeFlowMap.tsx` |

Verified end to end on a fixture domain: a `CONTRIBUTING.md` yielded eight
instructions and held the one naming a person and an email; review and finalize
moved the domain from 25 (F) to 78 (C).

## What is left

Tier 0 is done: answerability now scores, repo sources report staleness, and
`create_session` records the model it ran.

**Phase 3** (governance across the fleet) is untouched. Note that
`template_drift`'s three-hash classifier does not transfer to `governance.yaml`
— a scalar has no "fresh render" to compare against, so the fleet view needs its
own axes: unchanged / tightened locally / loosened below `inner_loop_floor` /
covered by a recorded exception.

**The drift bus.** `get_drift` is a synchronous read model, not an event
stream. `watchers/types.py:TriggerProtocol` and `watchers/registry.py` are the
seam, and nothing registers drift against them.

**A context-file sensor for KeelTrace.** Sensors sit on MCP, KG and retriever
calls, so an agent reading the `.domain/*.md` files this pipeline generates
records nothing. Until that exists, "which context is actually read?" cannot be
answered about the context we now produce.

**Retrieval quality is a separate question.** Answerability asks whether the
finalized context *contains* the answers. Whether retrieval surfaces them is
ContextPrecision/ContextRecall, and conflating the two yields a number nobody
can act on — you would not know whether to write more context or fix the
retriever.
