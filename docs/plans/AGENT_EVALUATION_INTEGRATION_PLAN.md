# Agent Evaluation Integration Plan

**Status**: Design — ready for review
**Date**: 2026-06-02
**Reference**: `testpattern.txt` (Ragas-based evaluation feature from `test-agentic-cli`)
**Target**: `dva eval` command group in this agentic CLI

---

## 1. Executive Summary

The reference document describes a mature, **Ragas-based agent evaluation** pipeline:
generate datasets from knowledge sources, create reusable eval configs, run against
agents via the A2A protocol, compare across agents, and produce HTML reports.

Our CLI already has an `eval` command group, but it is **skill-impact focused** and
runs against **mock agents**. The goal is to **extend (not replace)** the existing
`eval` group to support full agent evaluation, reusing what we have and adding a
Ragas framework adapter and real agent response collection.

**Strategy**: Additive, phased integration that preserves existing `eval` subcommands.

---

## 2. Current State vs Reference

### 2.1 What we already have (`agentic_cli/evaluation/` + `commands/eval.py`)

| Component | File | Notes |
|-----------|------|-------|
| Dataset model + manager | `datasets.py` | JSON datasets, `input`/`expected_output` schema |
| Metrics registry | `metrics.py` | 12 metrics (quantitative/qualitative/boolean) |
| LLM judges | `llm_judges.py` | VertexAI / Anthropic / OpenAI judges |
| Skill validator | `validator.py` | SKILL.md structure/quality checks |
| Skill impact runner | `runner.py` | Baseline vs with-skill delta |
| Async skill evaluator | `skill_evaluator.py` | Parallel eval, reporter |
| Agent adapters | `agent_adapters.py` | **Mock agents only** |
| CLI commands | `commands/eval.py` | `dataset`, `validate`, `run`, `metrics`, `report` |

### 2.2 What the reference adds (gaps)

| Reference capability | Have? | Gap |
|----------------------|-------|-----|
| Dataset **generate** from sources (GCS/Confluence/GitHub/local) | ❌ | No AI Q&A generation |
| Dataset **register** from CSV | ⚠️ | We use JSON, not CSV (`user_input`/`reference_contexts`/`reference`) |
| **Golden** datasets | ❌ | No golden concept |
| **Adversarial** questions + **personas** | ❌ | Not supported |
| Reusable **evaluation config** (`eval create`) | ❌ | We run ad-hoc, no saved config |
| **Run against real agent** (A2A protocol) | ❌ | Mock agents only |
| **Ragas** metrics (faithfulness, context precision/recall, etc.) | ❌ | We have generic metrics, no Ragas |
| Custom **metric register** (prompt-based LLM-as-Judge) | ⚠️ | Have judges, no registration command |
| Cross-agent **compare** | ❌ | No compare command |
| **HTML report** | ⚠️ | Only `report list` |
| **Versioned** dataset runs | ❌ | No versioning |

---

## 3. Design Principles

1. **Extend the existing `eval` group** — keep `eval validate skill`, `eval run skill`, etc.
2. **Add an `agent` evaluation track** alongside the skill track.
3. **Pluggable frameworks** — introduce a framework abstraction (`builtin`, `ragas`, future `vertex-ai`) so Ragas is optional.
4. **Optional heavy deps** — `ragas`, `langchain-google-vertexai`, `pandas` go under a new `eval` extra; degrade gracefully if missing.
5. **Reuse Vertex AI** — we already depend on `google-cloud-aiplatform`.
6. **Domain-aware** — datasets can be generated from a domain's KG context (ties into meta-repo + domain-context work).

---

## 4. Proposed Command Surface

Extend `dva eval` with config, agent-run, compare, report, and dataset generation:

```bash
# --- Dataset (extend existing) ---
dva eval dataset generate <name> --source <storage|confluence|github|local>:<loc> \
    --num-questions 20 [--adversarial-ratio 0.2] [--persona-list personas.yaml] [--golden]
dva eval dataset register <name> <path.csv> [--golden]      # CSV (Ragas schema)
dva eval dataset list [--golden-only]
dva eval dataset status <name>                              # background gen progress

# --- Evaluation config (new) ---
dva eval create <name> <dataset> --metrics "Faithfulness,AnswerCorrectness" \
    [--framework ragas] [--llm gemini-2.5-flash] [--embedding-model gemini-embedding-001]
dva eval describe <name>
dva eval delete <name> [--force]

# --- Run against a real agent (new) ---
dva eval run agent <agent_name> <eval_name> [--batch-size 10] [--force-response-collection]

# --- Compare + report (new) ---
dva eval compare <eval_name> --agents a-v1,a-v2 [--metrics ...] [--compare-versions]
dva eval report <eval_name> [--output report.html]

# --- Metrics (extend) ---
dva eval metrics list
dva eval metric register <name> --prompt prompt.md [--schema schema.json]
dva eval metric unregister <name>
```

> Note: existing `dva eval run skill ...` stays as-is; we add `dva eval run agent ...`.

---

## 5. Module Plan

```
agentic_cli/evaluation/
├── frameworks/                  # NEW — pluggable framework adapters
│   ├── __init__.py              # registry: get_framework("ragas"|"builtin")
│   ├── base.py                  # EvalFramework ABC (evaluate(dataset, metrics, llm))
│   ├── builtin.py               # wraps existing metrics.py + llm_judges.py
│   └── ragas_adapter.py         # NEW — Ragas + Vertex AI (optional import)
├── config.py                    # NEW — EvaluationConfig (saved YAML), results, versioning
├── generation/                  # NEW — dataset generation
│   ├── __init__.py
│   ├── sources.py               # local/gcs/confluence/github loaders (reuse kg loaders)
│   ├── question_gen.py          # AI Q&A generation (Vertex AI), personas, adversarial
│   └── golden.py                # golden dataset management
├── agent_runner/                # NEW — real agent response collection
│   ├── __init__.py
│   ├── a2a_client.py            # A2A protocol: subprocess + HTTP streaming
│   └── batch.py                 # parallel batch collection (batch-size)
├── reporting/                   # NEW — HTML reports + comparison
│   ├── __init__.py
│   ├── html_report.py           # interactive HTML (charts, per-row drill-down)
│   └── compare.py               # cross-agent + version comparison
├── csv_dataset.py               # NEW — CSV (Ragas schema) read/write + versioning
└── (existing files unchanged)
```

CSV schema (Ragas-compatible): `user_input`, `reference_contexts`, `reference`, `response`.

---

## 6. Framework Abstraction (key design)

```python
# frameworks/base.py
class EvalFramework(ABC):
    name: str
    @abstractmethod
    def supported_metrics(self) -> list[str]: ...
    @abstractmethod
    def evaluate(
        self, df, metrics: list[str], *, llm_model: str, embedding_model: str
    ) -> EvalScores: ...   # per-row + aggregate

# frameworks/ragas_adapter.py  (optional import — only if `ragas` installed)
class RagasFramework(EvalFramework):
    name = "ragas"
    def evaluate(self, df, metrics, *, llm_model, embedding_model):
        from ragas import evaluate
        from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
        # map metric names -> ragas metric objects; run with 3 retries/backoff
```

This lets `dva eval create --framework builtin` work today with zero new deps, and
`--framework ragas` unlock the full RAG metric suite when the `eval` extra is installed.

---

## 7. Dependencies (new optional extra)

```toml
# pyproject.toml
[project.optional-dependencies]
eval = [
    "ragas>=0.2.0",
    "langchain-google-vertexai>=2.0.0",
    "pandas>=2.0.0",
    "datasets>=2.0.0",        # ragas dataset format
]
```

Install: `pip install 'agentic-cli[eval]'`. All Ragas imports are lazy + guarded with a
clear error: *"Ragas not installed — run `pip install 'agentic-cli[eval]'`"*.

---

## 8. A2A Agent Runner (response collection)

The reference collects responses by starting the agent as a subprocess and streaming
over HTTP (A2A). We already start agents via `dva agent start/run` (subprocess). Plan:

1. `a2a_client.py` starts the agent project (reuse `commands/agent.py` start logic).
2. Sends each `user_input` via HTTP streaming, collects `response` + `retrieved_contexts`.
3. `batch.py` runs N requests in parallel (`--batch-size`, clamp 2–20).
4. Writes a **versioned** CSV (`<dataset>_v1.csv`, `_v2.csv`) per agent run.
5. Skips collection if `response` column present unless `--force-response-collection`.

---

## 9. Phased Implementation Roadmap

| Phase | Scope | Deps | Outcome |
|-------|-------|------|---------|
| **P1** | Framework abstraction + `builtin` adapter; `eval create/describe/delete`; CSV dataset + versioning; `eval run agent` with **existing** judges | none new | Saved eval configs + real-agent runs on current metrics |
| **P2** | `ragas_adapter` + `eval` extra; map 15 RAG + 8 safety metrics; lazy imports | `eval` extra | Full Ragas metric suite |
| **P3** | `eval compare` (cross-agent + versions) + `eval report` (HTML) | none new | Comparison + interactive reports |
| **P4** | `eval dataset generate` (sources, personas, adversarial, golden) + `metric register` | reuse KG loaders | AI dataset generation + custom metrics |
| **P5** | Domain/meta-repo tie-in: generate datasets from domain KG; store eval configs in meta-repo `.platform/config/` | — | Domain-aware evaluation |

Recommended start: **P1** (highest leverage, zero new deps, unblocks real-agent eval).

---

## 10. Integration with Domain / Meta-Repo Work

- **Dataset generation from domain KG**: `--source kg:<domain>` reuses `query_domain_kg`
  to build Q&A grounded in domain requirements.
- **Eval configs as governance artifacts**: store `eval/*.yaml` under the domain
  meta-repo `.platform/config/` so evaluations are versioned with the domain.
- **Onboarding hook**: `dva code onboard --domain <d>` could optionally scaffold a
  baseline eval config for the repo's agent.

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Heavy deps (ragas/langchain) bloat install | Optional `eval` extra; lazy guarded imports |
| Ragas score scale (1–5) vs our 0–1 metrics | Normalize in `EvalScores`; framework declares ranges |
| A2A protocol specifics vary per agent | Adapter interface; start with HTTP streaming, allow custom adapters |
| Vertex AI cost during generation/eval | `--num-questions` caps; `--batch-size` clamp; dry-run mode |
| CSV vs existing JSON datasets | Support both; CSV for agent eval, JSON stays for skill eval |

---

## 12. Success Criteria

- **P1**: `dva eval create` + `dva eval run agent` produce versioned results using builtin metrics, no new deps.
- **P2**: `--framework ragas` computes Faithfulness/ContextPrecision on a sample dataset.
- **P3**: `dva eval compare` ranks 2 agents; `dva eval report` opens an HTML report.
- **P4**: `dva eval dataset generate --source local:./docs` yields a valid CSV with personas/adversarial mix.

---

## 13. Open Questions

1. **A2A transport** — does our ADK agent expose an HTTP streaming endpoint we can target, or do we need a thin server wrapper in `agent_runner`?
2. **Result storage** — per-project YAML (reference style) vs our `tracker.db`? Proposal: YAML configs + summary rows in `tracker.db` for history.
3. **Golden dataset scope** — per-project or per-domain?
4. **Vertex AI region/model defaults** — read from existing CLI config or a new eval config block?

---

## 14. Recommended Next Step

Implement **Phase 1** (framework abstraction + `eval create` + CSV/versioning +
`eval run agent` on builtin metrics). This delivers real-agent evaluation with zero new
dependencies and establishes the seams for Ragas (P2) and reporting (P3).
