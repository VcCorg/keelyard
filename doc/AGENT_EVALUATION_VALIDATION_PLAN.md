# Agent Evaluation — Validation Plan

Validation plan for all code developed under the Agent Evaluation integration
(Phases 1–5) plus the multi-host meta-repo submodule work. The goal is to give a
reviewer a repeatable, mostly zero-dependency path to confirm correctness, plus
the manual steps that exercise the optional heavy dependencies (Ragas, Vertex
AI) and the live knowledge graph.

## 1. Scope of New Code

### Core evaluation library — `agentic_cli/evaluation/`

| Module | Purpose | Phase |
|--------|---------|-------|
| `frameworks/base.py` | `EvalFramework` ABC, `EvalRow`, `EvalScores` | 1 |
| `frameworks/builtin.py` | Native metrics + LLM-judge framework; custom-metric scoring | 1 / 4 |
| `frameworks/ragas_adapter.py` | `RagasFramework` (lazy ragas + Vertex AI) | 2 |
| `frameworks/__init__.py` | `get_framework`, `list_frameworks` (lazy optional deps) | 1 / 4 |
| `eval_config.py` | `EvaluationConfig` + YAML manager | 1 |
| `csv_dataset.py` | Ragas-schema CSV datasets + versioning | 1 |
| `agent_runner.py` | Async response collection + agent resolution | 1 |
| `results.py` | `EvalRunResult` + `EvalResultStore` | 3 |
| `reporting/compare.py` | Cross-agent / cross-version comparison | 3 |
| `reporting/html_report.py` | Self-contained interactive HTML report | 3 |
| `generation/sources.py` | Document sources (`local:`, placeholders) | 4 |
| `generation/question_gen.py` | Heuristic + Vertex AI question generators | 4 |
| `generation/golden.py` | Golden dataset registry | 4 |
| `custom_metrics.py` | Prompt-based custom metric definitions + manager | 4 |
| `domain_eval.py` | `kg:<domain>` source + meta-repo config storage | 5 |

### CLI — `agentic_cli/commands/eval.py`

New/extended commands under the `dva eval` group:

- `eval frameworks` — list frameworks and availability.
- `eval dataset register|versions|generate|golden` — CSV import, versioning,
  generation from sources/KG, golden marking.
- `eval create|list|describe|delete` — evaluation configs (with `--domain` to
  persist into the meta-repo).
- `eval run agent <spec> <eval>` — collect responses + score.
- `eval compare <eval>` — rank runs across agents/versions (+ optional HTML).
- `eval report generate <eval>` — interactive HTML report.
- `eval metric register|unregister|list` — custom prompt-based metrics.

### Meta-repo — `agentic_cli/meta_repo/`

- `git_utils.py` — host detection, default-branch detection, `add_submodule`
  (multi-host: Bitbucket/GitLab/GitHub; local-path CVE-2022-39253 workaround).
- `config.py` — `RepoConfig` gains `branch` + `host`.
- `scaffold.py`, `detector.py`, `commands/domain.py`, `commands/code.py` —
  use the host-agnostic submodule helper.

## 2. Automated Test Suite

All commands assume working dir `agentic-cli/` and the conda pytest-asyncio
workaround flags.

### 2.1 New/affected test files

- `tests/test_eval_phase1.py` — framework registry, builtin adapter, eval
  config manager, CSV versioning/register, response collector. (20 tests)
- `tests/test_eval_phase2_5.py` — results store, compare ranking, HTML report,
  local source, heuristic generator (counts + adversarial ratio), golden
  registry, custom metric manager + builtin custom-metric fallback, KG source
  spec resolution + mocked load, meta-repo config save/load. (14 tests)
- `tests/test_meta_repo_git_utils.py` — host detection, default-branch
  detection, `add_submodule` for local/remote with main/master/develop. (14 tests)

### 2.2 Commands

```bash
# New evaluation tests (P1–P5), zero optional deps:
python -m pytest tests/test_eval_phase1.py tests/test_eval_phase2_5.py \
  -p no:asyncio -p no:cacheprovider -o addopts="" -q

# Meta-repo multi-host submodule tests:
python -m pytest tests/test_meta_repo_git_utils.py \
  -p no:asyncio -p no:cacheprovider -o addopts="" -q
```

Expected: `48 passed` across the three files.

> Note: The conda `pytest_asyncio` plugin has a collection bug in this
> environment; the `-p no:asyncio` flag is required.

## 3. End-to-End CLI Smoke Tests

### 3.1 Phase 1 smoke — `smoke_eval_phase1.py`

```bash
python smoke_eval_phase1.py
```

Covers: register CSV v1 → create config → run `mock:simple` → response
collection (writes v2) → aggregate scores printed.

### 3.2 Phases 2–5 smoke — `scripts/dev/smoke_eval_phase2_5.py`

```bash
python scripts/dev/smoke_eval_phase2_5.py
```

Covers (against a temp store, no home pollution):

1. `dataset generate faq --source local:<docs> -n 6 --adversarial-ratio 0.34 --golden`
2. `create faq-eval faq -m accuracy,f1_score`
3. `run agent mock:simple faq-eval` and `run agent mock:helpful faq-eval`
4. `compare faq-eval -o cmp.html`
5. `report generate faq-eval -o rep.html`
6. `metric register|list|unregister empathy`

Expected final line: `SMOKE OK; html exists: True True`.

## 4. Manual Validation (Optional Dependencies)

These paths are lazy-loaded and are not covered by the zero-dep suite.

### 4.1 Ragas framework (Phase 2)

```bash
pip install 'agentic-cli[eval]'        # ragas, langchain-google-vertexai, pandas, datasets
# Configure Vertex AI project/location via dva config / KG config.
dva eval create rag-eval docs-qa -f ragas -m Faithfulness,AnswerCorrectness \
  --llm gemini-2.5-flash --embedding-model text-embedding-004
dva eval run agent mock:qa rag-eval
```

Validate: framework loads without ImportError, RAG metrics produce 0–1 scores,
results JSON saved.

Failure mode to confirm: with the extra **not** installed, `get_framework("ragas")`
raises a clear `ImportError` with the `pip install 'agentic-cli[eval]'` hint
(exercised indirectly by `eval frameworks` showing it as `optional`).

### 4.2 Vertex AI question generation (Phase 4)

```bash
dva eval dataset generate faq --source local:./docs -n 20 --ai
```

Validate: questions are LLM-generated; on any Vertex error the command logs a
warning and falls back to the heuristic generator (no crash).

### 4.3 LLM-judge custom metrics (Phase 4)

```bash
dva eval metric register empathy -p "Rate how empathetic the answer is (1-5)."
dva eval create cx-eval support-qa -m helpfulness,empathy -j vertex-ai
dva eval run agent my_pkg.agents:answer cx-eval
```

Validate: `empathy` scored 1–5 by the judge; with `-j none` it falls back to a
neutral `3.0` (covered by automated test).

### 4.4 Domain KG source + meta-repo config (Phase 5)

```bash
# Requires an ingested KG for the domain (dva kg ...).
dva eval dataset generate facility --source kg:cwow-facility -n 15 --adversarial-ratio 0.2
dva eval create facility-eval facility --domain cwow-facility
```

Validate: KG aspects become Q&A rows; config is written to
`<meta-repo>/.platform/config/eval/facility-eval.yaml` when a domain meta-repo
is detected, otherwise it saves locally with a warning (both paths covered by
automated tests via monkeypatch).

## 5. Regression / Backward-Compatibility Checks

- `python -c "import agentic_cli.commands.eval"` — import succeeds (no syntax or
  circular import errors).
- `dva eval --help`, `dva eval dataset --help`, `dva eval metric --help`,
  `dva eval compare --help`, `dva eval report --help` — all exit 0
  (verified via `typer.testing.CliRunner`).
- Existing `eval validate`, `eval run skill`, `eval metrics list`, and
  `eval dataset create|list|show` commands remain registered and unchanged.
- No new **required** dependencies were added; the `eval` extra in
  `pyproject.toml` is opt-in.

## 6. Risk Notes & Assumptions

- **Optional deps isolation**: Ragas/Vertex/Neo4j are imported inside functions;
  the zero-dep suite must never import them. Confirmed by running the suite in a
  clean interpreter.
- **Custom metrics without a judge** intentionally yield a neutral score rather
  than failing, to keep pipelines robust; reviewers should confirm this is the
  desired contract.
- **Golden registry** stores markers in `_golden.json` beside the CSVs; it does
  not mutate dataset files.
- **Meta-repo detection** relies on `detect_domain_meta_repo`; when no meta-repo
  exists, config storage degrades gracefully to local-only.
- **HTML reports** are self-contained (inline CSS/JS), safe to open offline.

## 7. Sign-off Checklist

- [ ] `48 passed` for the three test files.
- [ ] `smoke_eval_phase1.py` prints success.
- [ ] `scripts/dev/smoke_eval_phase2_5.py` prints `SMOKE OK; html exists: True True`.
- [ ] `dva eval` help commands all exit 0.
- [ ] (Optional) Ragas/Vertex/KG manual paths validated in a configured env.
