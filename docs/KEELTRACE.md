# KeelTrace — session context provenance

**Record what enters an agent's context, so it can be shown to a human and
scored by a machine.**

That was the original claim, and it is now the smaller half. The ledger also
answers what a source change *did* to the instructions drawn from it, and what
a project spent — in tokens, and in money where someone has said what tokens
cost. P1–P7 below are merged; the backlog at the end is what is genuinely left.

## Why

The tracker recorded what the platform *did* — commands run, sessions created,
repos onboarded — but never what an agent *read*. Retrieval was invisible.

That made two things impossible:

1. **Provenance.** Answering "why did the agent say that?" by pointing at the
   sources that produced the claim.
2. **Context-aware evaluation.** `EvalRow.retrieved_contexts` is defined in
   `agentic-cli/src/agentic_cli/evaluation/frameworks/base.py` and consumed by
   `ragas_adapter.py` — but nothing populated it. Every Ragas metric needing
   retrieved context (Faithfulness, ContextPrecision, ContextRecall) was
   silently scoring against an empty list.

Both are downstream of one missing sensor. The eval framework was never
incomplete; it was **starved**.

## Shipped

### P1 — sensors (merged)

`agentic-cli/src/agentic_cli/tracing.py`

- Session identity reuses the tracker's existing indexed `correlation_id`. No
  schema migration.
- The id travels in a `ContextVar` rather than through ~18 call signatures.
- `record_context_read()` writes one row per retrieval: source, operation,
  entity, bytes, latency, status.
- `call_mcp_tool` is instrumented at the sync funnel all 14 MCP helpers route
  through — records success *and* failure.
- `create_session` mints and binds the trace id **before** the engine runs, so
  context read on the way in is attributed rather than orphaned.
- `keel context trace <session>` prints the ledger.

### P2 — the read side (merged)

- `tracing.list_sessions()` / `session_context()` / `session_summary()`
- `GET /api/trace/sessions` and `/api/trace/sessions/{id}`
- **Context Trace** page under Quality, beside Evaluation.

## The thread trap — read this before touching the sensors

**ContextVars do not propagate across `threading.Thread`.**

`mcp_tool_client._run_async` spawns a worker thread when a loop is already
running — which is exactly what the FastAPI dashboard does. A sensor that
reads the ContextVar *inside* the coroutine works perfectly from the CLI and
**silently records nothing from the dashboard**, which reads as a flake rather
than a bug.

So sensors read the session id on the **caller's** thread and pass it down
explicitly. `test_contextvar_does_not_cross_a_thread_boundary` in
`agentic-cli/tests/test_tracing.py` pins the constraint so it cannot quietly
stop holding.

## Storage tiers

**Tier one (shipped)** — metadata in the tracker: cheap, queryable, safe to
retain. Tool arguments are **digested, never stored** — they routinely carry
tokens. A test asserts a bearer token cannot reach the ledger.

**Tier two (built, off by default)** — the retrieved *text*, which Ragas needs.
`agentic_cli/payload_store.py`, hanging off the `payload_ref` seam. Nothing is
stored unless `KEEL_PAYLOAD_STORE` selects a backend: writing document bodies to
disk is a decision for whoever runs Keel, not for whoever imports the module.

- `memory` — process-local, never touches disk. Serves run-and-score in one
  flow (the ablation playground). It cannot serve `keel eval` over an earlier
  session, which is a separate process.
- `sqlite` — a **separate** `payloads.db` beside the tracker. Separate because
  `tracker.db` is the audit trail and is safe to hand to someone debugging an
  issue; a file holding document bodies is not, and nothing in the code would
  flag the change if they shared one.

Three rules the code enforces rather than documents:

| Rule | Why |
|---|---|
| **Drop, never truncate** | A chunk cut mid-sentence makes Faithfulness score the agent against a mutilated version of what it saw — a wrong number, not a missing one. Over the cap, the row records `payload: omitted (size …)`. |
| **Mask in place, and report it** | Identifiers become typed markers (`<email>`, `<person>`) rather than being deleted, so a correct claim about a value the text still contains does not read as unfaithful. The row carries `payload_masked`, so a score over altered text stays identifiable. |
| **Expiry erases** | `DELETE` frees SQLite pages without zeroing them, so expired bodies stay readable in the file until a `VACUUM`. `secure_delete` is on and the sweep vacuums. |

`keel context payloads` inspects, sweeps and purges it.

### Still open

The tier-two question that used to head this section is settled: both backends
are built and the store stays off until an operator names one, which puts the
decision with whoever runs Keel rather than whoever imports the module. Two
narrower decisions remain, and both are cheaper now because a separate file can
be dropped and rebuilt:

- **Read-back authorization.** `GET /api/trace/sessions/{id}` needs none today
  because it returns metadata. The moment it can return bodies, it does.
- **Desktop redistribution.** The app ships `~/.keel/` on real machines, where a
  payload store syncs to backups and lands in any support bundle. The repo guard
  only scans staged files and does not reach there.

Defaults are deliberately conservative — 64 KiB per payload, 7-day TTL — and
should be re-set from measurement once the memory backend has run for a while,
rather than argued about in advance.

## The loop, closed

P1 and P2 made retrieval visible. P3 onward turn that visibility into something
that acts: scored, ablated, diffed against its sources, and costed. Everything in
this section is merged.

**P3 — eval feed (shipped).** `agentic_cli/evaluation/session_feed.py` builds an
`EvalRow` from a session, with `retrieved_contexts` populated from the tier-two
store, and `keel eval session <id>` runs it through the existing Ragas adapter.

Building it corrected a claim made here. Two of the three metrics named below
need a **reference answer**, which a live session by definition does not have:

| Metric | Reference needed | Usable on a session |
|---|---|---|
| Faithfulness | no | yes |
| ResponseRelevancy | no | yes |
| ContextPrecision *without reference* | no | yes — added to the adapter |
| ContextRecall | **yes** | no — only for dataset-driven evaluation |

So the session default is the reference-free set, and `--reference` widens it
when ground truth exists. Asking for ContextRecall on a bare session would score
it against an empty reference and return a confident zero, which is worse than
declining.

Two gaps closed on the way:

- **`ask()` never bound a trace id.** `create_session` minted one before the
  engine ran; `ask` did not, so the one flow that has both a question and an
  answer had its retrieval orphaned from the answer it produced.
- **The question and answer were not stored anywhere.** They now go to the
  tier-two store rather than the audit row: both are free text with the same
  disclosure profile as a retrieved document, so they belong under the same cap,
  mask and TTL rather than in a second at-rest path with its own rules.

A session that cannot be scored says which of several reasons applies — store
disabled, no answer recorded, nothing retrieved — because they have different
fixes and one exception would flatten them into one.

The payoff is the split diagnosis a single score cannot express:

| Signal | Means | Fix lives in |
|---|---|---|
| ContextPrecision low | retrieved junk | retriever / KG query |
| ContextRecall low | missed the right source | ingestion coverage |
| Faithfulness low | had it, ignored it | prompt or skill |

**P4 — Context Playground (shipped).**
`agentic_cli/evaluation/playground.py`, `keel eval playground <session>`, and a
panel under the ledger on the Context Trace page.

Switch a source off, re-run the same question, watch the scores move. A score
says a session went badly; only removing a source and re-running says *that
source was why* — which is the difference between a report and an instrument.

**This is the replay core**, not a one-off surface. Holding the model fixed and
varying the context is ablation; holding the context fixed and varying the model
is the model-fit question in the backlog below. Both are `replay()` with a
different argument, so neither needs its own harness — and a drift replay ("did
this context change alter past answers?") is the same call again.

Two properties worth keeping:

- **A variant is filed as a session in its own right**, with its own trace id
  and payloads, so `session_feed` cannot tell it from an original. Scoring a
  replay through a parallel path would have let the two drift apart.
- **Re-running and scoring degrade separately.** Replay needs a provider;
  scoring needs Ragas and a judge. Without a judge the answers still change,
  which is often the finding — seeing an answer lose a fact when the KG is
  switched off tells you what the KG was contributing.

One variant per switched-off source rather than one with all of them removed, so
each source's contribution is attributable on its own. And a metric the baseline
could not score is omitted from the deltas rather than shown as a drop: "we
could not measure this before" and "this got worse" must not render the same.

**P5 — the retrieval seam (shipped).** `agentic_cli/retrieval.py`.

Three call sites answered "fetch what this ref points at" independently:
`context/resolve.py` walked an `if okf: … elif domain: …` chain,
`onboarding/sources.py` read Confluence and repo docs, and `stale_repo_entries`
re-read files a third time to compare a digest. One of the three traced. Fetchers now
register against a scheme (`domain`, `okf`, `repo`, `confluence`, `governance`),
and `search()` is the same seam for query-shaped reads — a KG or Glean query
answers a question with many hits rather than resolving an address, so it does
not pretend to be a `fetch`.

The reason this went in before the differ rather than alongside it: the differ
asks exactly this question of a source, and without a seam it would have grown a
fourth fetcher.

Two things it fixed that nothing had noticed. `keel domain extract` was pulling
every tracked page from upstream and leaving **no ledger row at all**. And the
KG, LightRAG, Neo4j and Glean clients recorded nothing whatsoever — a session
answered entirely from the knowledge graph showed as having read nothing, which
made this document's central claim false for those paths.

Five outcomes replace `None`. `fetch_confluence` already carried the comment that
an unreachable source must not look like a source with nothing to say; returning
`None` for both made that impossible to honour. `UNAVAILABLE` (we could not ask)
must never collapse into `MISSING` (nothing is there), because that difference
decides whether an approved instruction is flagged absent.

**P6 — semantic drift (shipped).** `agentic_cli/onboarding/differ.py`,
`keel domain diff`.

Digest drift says a file moved. A typo fix moves it exactly as far as a reversed
step does, so the reviewer got the same undifferentiated pile either way. This
says what the move *did*: unchanged, reworded, contradicted, or no longer
supported there.

Similarity is deterministic; agreement is not. Token overlap cannot tell
*"always run migrations before deploy"* from *"never run migrations before
deploy"* — they are the same sentence. So the lexical tier only decides which new
instruction is talking about the same thing, and without a judge a pair is
`REWORDED` with `checked` false: the source still speaks to the instruction,
which is not the same as still supporting it.

Negations are stripped before scoring **on purpose**, so a reversed instruction
scores near-perfectly and reaches the contradiction check instead of passing as
an unrelated new candidate. That makes the one contradiction that matters
catchable with no model at all.

The threshold is measured, not guessed: 0.60 admits 3 of 544 real non-matching
pairs from this repository's own corpus, and dropping to 0.50 more than doubles
that while buying no additional true reword.

**P7 — token accounting and cost (shipped).** `tokens.py`, `usage.py`,
`pricing.py`, `keel domain usage`.

This is the "context budget" item from the backlog below, built. Ledger rows
carried a session id but nothing saying which *project* a session was for, so
"what did this competition cost me against that one" could not be asked at all.

Four meters, split because one total cannot tell a project three days into
onboarding from one running daily off finished context: **built** (the one-off
investment), **served** (what recurs per session), **tools**, and **model calls**.
The split falls out of a distinction P5 made for a different reason — extraction
reads record under `onboarding`, not `context`, because a page read to *derive*
instructions was never put in front of an agent.

Rules the readouts enforce:

| Rule | Why |
|---|---|
| **A count carries its basis** | No vendor tokenizer is bundled, so most counts are estimates. A total mixing measured and estimated is neither, and says so. |
| **Uncounted is never zero** | A read that contributed no token count reports `uncounted` or `partial (2/3)`, and a total containing one is prefixed `≥`. A cost table is exactly where a zero is read as "free". |
| **Retrieval is never priced** | Nobody bills for reading a file. Context becomes money when a model reads it, which is the generation row — so cost is a separate table, not another column. |
| **Cost is computed, never stored** | A cost frozen at record time can never be corrected when rates change. The ledger keeps tokens. |
| **An unpriced model is counted, not free** | A total that silently omits a model reads as a cheaper project — the error nobody goes looking for. |

**Keel ships no prices.** A rate card is loaded from configuration or costing
stays off, because a wrong price is worse than no price: rates change, and a
number baked into a release keeps being produced long after it stopped being
true. `rates.example.yaml` is dated data an operator adopts deliberately, and a
card over 180 days old — or undated — reports stale.

## Related backlog

- **Pluggable retrieval backends.** The *recording* half of this shipped as P5:
  LightRAG, Neo4j and Glean go through `retrieval.search` and land in the
  ledger, so there is one sensor rather than none. What has **not** shipped is
  the part this bullet originally described — `BaseRetriever` / `BaseIngestor`
  protocols making FAISS, FTS and PGVector interchangeable. `retrievers.py`
  still only registers named indexes; nothing executes against them.

  Worth keeping straight, because the vocabulary invites confusion and the
  glossary now pins it: a **fetcher** resolves one address to one document, a
  **retriever** answers a question with many hits. P5 built the seam both read
  *through*; it did not make the backends swappable.
  - Open question, unchanged: how graph traversal survives a non-graph backend.
    Working proposal — ingestion emits chunks+embeddings to the vector store and
    typed entity edges to an edge store, chunks carrying entity ids; graph
    retrieval becomes vector search for candidates then expansion over edges
    joined by entity id. Neo4j stops being special.
- **Model fit.** The context-budget half of this shipped as P7; what remains is
  the second question it was paired with: *given the same context, which model
  does best?*

  The three gaps this bullet used to list are now one and a half:

  - ~~No model is recorded on a session.~~ Recorded per call, with requested and
    served kept apart — a request can be ignored, substituted, or fall back, and
    attributing a result to the request measures the wrong thing.
  - ~~Bytes are not tokens.~~ `tokens` and `tokens_out` are indexed columns, each
    row carrying whether the count was measured or estimated.
  - **Read is still not sent — for vendor engines.** Where Keel calls the model
    itself, `usage.admitted` is what the model actually read and the readout
    shows it beside what was served. Where a hosted engine assembles the prompt,
    we still never see it. The reporting stays two labelled numbers, and the
    readout names the gap without asserting its direction: a prompt can be
    smaller than what was retrieved (truncation, a cache hit) or larger (system
    instructions, the question, history), and claiming either would be a
    statement about engine internals we cannot see.

  Comparing models on identical context is still the **transpose of P4**: the
  Playground holds the model fixed and varies the sources; this holds the sources
  fixed and varies the model. Same replay core, and the same primitive a
  drift-replay would need — build it once with three consumers.

  Still unbuilt, and now cheap: giving `onboarding/readiness.py` a dimension for
  whether the finalized instruction set fits the target model's window with room
  left to work. The token count it needs exists.

- **Streaming and async generation are uninstrumented.** `_MeteredProvider`
  wraps `generate()` only. A streamed reply has no usage until the final chunk,
  so filing a measured zero would be worse than a visible gap — but it does mean
  any engine that streams produces no cost row today. This is the largest hole
  left in P7 and it is deliberate, not forgotten.

- **Competition-style work: many projects, many contexts.** Kaggle and
  hackathons are the same shape as the enterprise case with the labels changed —
  a competition maps to a domain, a portfolio of them to a product — and most of
  what that needs already exists. Doc typing is exactly the problem a competition
  poses (a data dictionary, the metric definition, the rules, and a thousand
  forum threads are not the same kind of document). Drift is real rather than
  theoretical: organisers revise data, clarify metrics, and post leakage
  warnings mid-competition, and a solution built on the old wording is wrong in
  a way nothing currently notices.

  **The interesting part is the replay core.** `replay(session, exclude=...,
  model=...)` already varies one dimension and re-scores. Competition work
  varies a different dimension — a feature set, a fold split, a hyperparameter —
  and its outcome is a number from outside the system. Generalising *what
  varies* to an arbitrary variant dimension, and letting a variant carry an
  externally supplied score, turns the ablation harness into an experiment
  tracker without a second engine.

  **What would differentiate it is not the tracking.** MLflow and Weights &
  Biases record parameters and metrics well, and we should integrate with one
  rather than rebuild it. What none of them record is *the context the agent
  read when it wrote the run* — so "which forum insight led to the feature that
  gained 0.003?" is unanswerable today, and it is exactly the join the ledger
  already makes for coding sessions.

  Two concrete gaps, both small:

  - **No run-with-outcome object.** Nothing in the codebase models an experiment
    with a numeric result. `Variant` is the closest and is one field short. This
    is now the only one of the two still open, and the next thing to build here.
  - ~~No cross-domain readiness view.~~ `domain score --all` ships the portfolio
    readout, worst-first, and a domain with no meta-repo is listed rather than
    skipped — "not set up yet" and "set up and scoring badly" are different
    problems. `keel domain usage --all` is its cost counterpart.

  **Where it does not fit, and should not be forced.** Keel scores *context*
  quality; a leaderboard scores *model* performance, and that number is ground
  truth arriving from outside. Do not grow a metric tracker inside this. The
  claim worth making is narrower and defensible: every run records what informed
  it.

- **Test CI.** Wired — `.github/workflows/tests.yml` blocks on the suites, with
  the eight still-failing files excluded by name. Triage took `agentic-cli` from
  47 failures to 28 by fixing three causes rather than individual tests (a
  missing `pytest-asyncio`, a `CLI_NAME` NameError in the tool generator, and a
  suite invoking `python` from `PATH` rather than `sys.executable`). The
  remaining exclusions are listed in [`CLAUDE.md`](../CLAUDE.md); each is a debt
  entry with a name attached, and the job is honest rather than
  `continue-on-error`.

  One correction to that claim: the `dashboard/frontend` job in the same
  workflow had **never passed**, on any commit including the one that added it.
  It asked `setup-node` to cache npm against `package-lock.json` and then ran
  `npm ci` — and this repo gitignores every lockfile, so both requests were for
  something the repo's own policy guarantees is absent. It died in six seconds,
  before running the typecheck or the build it exists to run. A CI job that has
  never once succeeded is not a gate; it is a red light everybody learns to
  ignore, which is worse than no job at all.

## Next after KeelTrace

**KeelGuard** — an Agent Bill of Materials. KeelTrace answers *what an agent
did reach*; KeelGuard answers *what it can reach* — skills, MCP servers and
their credentials, model egress, execution engine — composed into a risk
verdict gated at `create_session`. Evidence and policy, reading the same
ledger.
