# KeelTrace — session context provenance

**Record what enters an agent's context, so it can be shown to a human and
scored by a machine.**

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

## Storage tiers, and the open decision

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

Enabling a backend does not settle everything. Two decisions remain, and both
are cheaper now because a separate file can be dropped and rebuilt:

- **Read-back authorization.** `GET /api/trace/sessions/{id}` needs none today
  because it returns metadata. The moment it can return bodies, it does.
- **Desktop redistribution.** The app ships `~/.keel/` on real machines, where a
  payload store syncs to backups and lands in any support bundle. The repo guard
  only scans staged files and does not reach there.

Defaults are deliberately conservative — 64 KiB per payload, 7-day TTL — and
should be re-set from measurement once the memory backend has run for a while,
rather than argued about in advance.

## Next

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

## Related backlog

- **Retriever seam.** Direct engine calls are being replaced by
  `BaseRetriever` / `BaseIngestor` protocols so FAISS, FTS and PGVector become
  pluggable. 15 files currently talk to Neo4j directly, bypassing MCP — once
  they route through the seam there is **one** sensor rather than two, and it
  is the better placement: retrievers return chunk text and relevance scores
  already shaped the way Ragas wants.
  - Open question: how graph traversal survives a non-graph backend. Working
    proposal — ingestion emits chunks+embeddings to the vector store and typed
    entity edges to an edge store, chunks carrying entity ids; graph retrieval
    becomes vector search for candidates then expansion over edges joined by
    entity id. Neo4j stops being special.
- **Context budget, and model fit.** Two questions the platform cannot answer
  today: *what exactly went into this coding session's context, and how long was
  it?* — and *given that same context, which model does best?* The second is an
  evaluation feature; the first is its prerequisite, and is also what tells us
  whether a domain's context is the right size at all.

  Half of it already exists. `record_context_read` stores `bytes` per read,
  `session_summary` rolls up totals and a per-source breakdown (its docstring
  already anticipates a "context-budget readout"), and `create_session` binds
  the trace id *before* the engine runs, so reads on the way in are attributed.
  Three things are genuinely missing:

  - **No model is recorded on a session.** `execution.registry.create_session`
    records the *engine* (Devin, local, IDE), never the model inside it. Without
    that there is nothing to group a comparison by. One column, and by far the
    cheapest first step — do this one regardless of whether the rest happens.
  - **Bytes are not tokens, and tokens are model-specific.** Every model
    tokenizes differently, so "context length" is only meaningful per model.
    `bytes` also lives in the details JSON rather than an indexed column, which
    is fine for one session's ledger and wrong for aggregating across a fleet.
  - **Read is not sent.** The ledger records what was *retrieved*. The prompt is
    what the engine *assembled* — after dedup, truncation, reordering and
    caching — and for a vendor engine we may never see it. So the honest
    reporting is two numbers, retrieved and admitted, each labelled: quoting one
    as if it were the other makes every downstream comparison meaningless.

  Comparing models on identical context is the **transpose of P4**: the Context
  Playground holds the model fixed and varies the sources; this holds the
  sources fixed and varies the model. Same replay core, and the same primitive a
  drift-replay ("did this context change alter past answers?") would need — so
  build the replay engine once with three consumers rather than three times.

  The payoff for domain context is the part that is easy to miss: a token count
  per invocation turns *"is our domain context the right size?"* from taste into
  a number, and gives `onboarding/readiness.py` a further dimension — does the
  finalized instruction set fit the target model's window with room left to
  actually work?

- **Test CI.** Not wired, because `main` has pre-existing failures (see
  [`CLAUDE.md`](../CLAUDE.md)). Triage first, then add the workflow.

## Next after KeelTrace

**KeelGuard** — an Agent Bill of Materials. KeelTrace answers *what an agent
did reach*; KeelGuard answers *what it can reach* — skills, MCP servers and
their credentials, model egress, execution engine — composed into a risk
verdict gated at `create_session`. Evidence and policy, reading the same
ledger.
