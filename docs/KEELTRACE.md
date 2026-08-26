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

**Tier two (not built)** — the retrieved *text*, which Ragas needs.
Deliberately absent: it means proprietary document bodies at rest, which needs
size caps, a retention policy, and redaction before anything is written.
`payload_ref` in the details column is the seam it will hang from.

> **This is the decision blocking P3.** Settle caps / TTL / redaction before
> writing code — retrofitting a payload store after three consumers exist is
> painful.

## Next

**P3 — eval feed.** Build `EvalRow` from a session with `retrieved_contexts`
populated, then run the existing Ragas adapter. No new metric code needed —
`Faithfulness`, `ContextPrecision`, `ContextRecall` already resolve. Needs an
LLM judge credential; test mode cannot compute these.

The payoff is the split diagnosis a single score cannot express:

| Signal | Means | Fix lives in |
|---|---|---|
| ContextPrecision low | retrieved junk | retriever / KG query |
| ContextRecall low | missed the right source | ingestion coverage |
| Faithfulness low | had it, ignored it | prompt or skill |

**P4 — Context Playground.** One surface: run a task, watch the ledger stream,
score it, then **toggle a source off and re-run to watch the scores move**.
Ablation is what makes it an instrument rather than a report.

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
- **Test CI.** Not wired, because `main` has pre-existing failures (see
  [`CLAUDE.md`](../CLAUDE.md)). Triage first, then add the workflow.

## Next after KeelTrace

**KeelGuard** — an Agent Bill of Materials. KeelTrace answers *what an agent
did reach*; KeelGuard answers *what it can reach* — skills, MCP servers and
their credentials, model egress, execution engine — composed into a risk
verdict gated at `create_session`. Evidence and policy, reading the same
ledger.
