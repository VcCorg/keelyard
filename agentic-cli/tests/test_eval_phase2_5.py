"""Tests for agent-evaluation Phases 2-5 (zero-dependency paths).

Covers:
  - Phase 3: EvalResultStore + compare_runs + HTML report generation.
  - Phase 4: generation (sources, heuristic question gen, golden registry) and
    custom prompt-based metrics (builtin framework scoring + manager).
  - Phase 5: KG source spec resolution and meta-repo config persistence.

All tests avoid optional heavy dependencies (ragas, vertexai, neo4j) by using
the heuristic generator, the neutral-judge fallback, and local fixtures.
"""

import json
from pathlib import Path

import pytest

from agentic_cli.evaluation.csv_dataset import CsvRow
from agentic_cli.evaluation.eval_config import EvaluationConfig


# ---------------------------------------------------------------------------
# Phase 3: results + compare + report
# ---------------------------------------------------------------------------

def _write_run(evals_dir: Path, eval_id: str, eval_name: str, agent: str,
               aggregate: dict, ranges: dict, version: int = 1) -> None:
    data = {
        "eval_id": eval_id,
        "eval_name": eval_name,
        "agent": agent,
        "dataset": "ds",
        "dataset_version": version,
        "framework": "builtin",
        "judge": "none",
        "metrics": list(aggregate.keys()),
        "timestamp": f"2026-01-0{version}T00:00:00+00:00",
        "num_rows": 3,
        "scores": {"aggregate": aggregate, "metric_ranges": ranges,
                   "per_row": [], "errors": []},
    }
    (evals_dir / f"{eval_id}.json").write_text(json.dumps(data))


def test_result_store_latest_per_agent(tmp_path):
    from agentic_cli.evaluation.results import EvalResultStore

    _write_run(tmp_path, "r1", "ev", "mock:simple", {"accuracy": 0.5},
               {"accuracy": [0, 1]}, version=1)
    _write_run(tmp_path, "r2", "ev", "mock:simple", {"accuracy": 0.8},
               {"accuracy": [0, 1]}, version=2)
    _write_run(tmp_path, "r3", "ev", "mock:helpful", {"accuracy": 0.6},
               {"accuracy": [0, 1]}, version=1)

    store = EvalResultStore(tmp_path)
    assert len(store.for_eval("ev")) == 3
    latest = store.latest_per_agent("ev")
    assert set(latest.keys()) == {"mock:simple", "mock:helpful"}
    # Newest mock:simple run (v2 / later timestamp) should win.
    assert latest["mock:simple"].aggregate["accuracy"] == 0.8


def test_compare_runs_ranks_best(tmp_path):
    from agentic_cli.evaluation.results import EvalResultStore
    from agentic_cli.evaluation.reporting import compare_runs

    _write_run(tmp_path, "a", "ev", "mock:simple", {"accuracy": 0.4},
               {"accuracy": [0, 1]})
    _write_run(tmp_path, "b", "ev", "mock:helpful", {"accuracy": 0.9},
               {"accuracy": [0, 1]})
    store = EvalResultStore(tmp_path)
    runs = list(store.latest_per_agent("ev").values())

    comp = compare_runs(runs)
    assert "mock:helpful" in comp.labels and "mock:simple" in comp.labels
    # Best label for accuracy row is the higher score.
    acc_row = next(r for r in comp.rows if r.metric == "accuracy")
    assert acc_row.best_label == "mock:helpful"
    # Ranking puts the higher overall first.
    assert comp.ranking[0] == "mock:helpful"


def test_html_report_self_contained(tmp_path):
    from agentic_cli.evaluation.results import EvalResultStore
    from agentic_cli.evaluation.reporting import write_html_report, compare_runs

    _write_run(tmp_path, "a", "ev", "mock:simple", {"accuracy": 0.4},
               {"accuracy": [0, 1]})
    _write_run(tmp_path, "b", "ev", "mock:helpful", {"accuracy": 0.9},
               {"accuracy": [0, 1]})
    store = EvalResultStore(tmp_path)
    runs = list(store.latest_per_agent("ev").values())

    out = tmp_path / "report.html"
    written = write_html_report(out, title="Test", runs=runs,
                                comparison=compare_runs(runs))
    html = Path(written).read_text()
    assert "<html" in html.lower()
    assert "Test" in html
    assert "accuracy" in html


# ---------------------------------------------------------------------------
# Phase 4: generation
# ---------------------------------------------------------------------------

def test_local_source_chunks(tmp_path):
    from agentic_cli.evaluation.generation.sources import get_source

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# Topic A\n\nParagraph one about A.\n\nParagraph two.")
    (docs / "b.txt").write_text("Plain text about B.")

    source = get_source(f"local:{docs}")
    chunks = source.load_chunks()
    assert chunks
    assert any("Topic A" in c.text for c in chunks)


def test_local_source_missing_path(tmp_path):
    from agentic_cli.evaluation.generation.sources import get_source

    source = get_source(f"local:{tmp_path / 'nope'}")
    with pytest.raises(FileNotFoundError):
        source.load_chunks()


def test_unsupported_source_raises(tmp_path):
    from agentic_cli.evaluation.generation.sources import get_source

    source = get_source("confluence:SPACE")
    with pytest.raises(NotImplementedError):
        source.load_chunks()


def test_heuristic_generator_counts_and_adversarial():
    from agentic_cli.evaluation.generation import get_generator, GenerationConfig
    from agentic_cli.evaluation.generation.sources import DocumentChunk

    chunks = [
        DocumentChunk(text="# Eligibility\n\nPatients must meet criteria X and Y."),
        DocumentChunk(text="# Billing\n\nClaims are submitted within 30 days."),
    ]
    gen = get_generator(use_ai=False)
    cfg = GenerationConfig(num_questions=10, adversarial_ratio=0.4)
    rows = gen.generate(chunks, cfg)

    assert len(rows) == 10
    # 40% adversarial -> 4 adversarial rows with the safety-oriented reference.
    adversarial = [r for r in rows if "documented facts" in r.reference]
    assert len(adversarial) == 4
    # Every row carries a question and a context.
    assert all(r.user_input for r in rows)
    assert all(r.reference_contexts for r in rows)


def test_golden_registry(tmp_path):
    from agentic_cli.evaluation.generation import GoldenRegistry

    reg = GoldenRegistry(tmp_path)
    assert reg.get("ds") is None
    reg.mark("ds", 3, note="reviewed")
    entry = reg.get("ds")
    assert entry and entry.version == 3 and entry.note == "reviewed"
    assert reg.is_golden("ds", 3)
    assert not reg.is_golden("ds", 2)
    assert reg.unmark("ds") is True
    assert reg.get("ds") is None


# ---------------------------------------------------------------------------
# Phase 4: custom metrics
# ---------------------------------------------------------------------------

def test_custom_metric_manager_roundtrip(tmp_path):
    from agentic_cli.evaluation.custom_metrics import CustomMetric, CustomMetricManager

    mgr = CustomMetricManager(tmp_path)
    assert not mgr.exists("empathy")
    mgr.register(CustomMetric(name="empathy", prompt="Rate empathy 1-5.", description="warmth"))
    assert mgr.exists("empathy")
    loaded = mgr.load("empathy")
    assert loaded.prompt == "Rate empathy 1-5."
    assert mgr.as_prompt_map() == {"empathy": "Rate empathy 1-5."}
    assert mgr.unregister("empathy") is True
    assert not mgr.exists("empathy")


def test_builtin_framework_scores_custom_metric_neutral_fallback():
    from agentic_cli.evaluation.frameworks import get_framework
    from agentic_cli.evaluation.frameworks.base import EvalRow

    fw = get_framework(
        "builtin",
        judge_type="none",
        custom_metrics={"empathy": "Rate empathy 1-5."},
    )
    assert "empathy" in fw.supported_metrics()
    rows = [EvalRow(input_text="q", reference="ref", response="ans")]
    scores = fw.evaluate(rows, ["empathy"])
    # No judge available -> neutral 3.0 on the 1-5 scale, range recorded.
    assert scores.aggregate["empathy"] == 3.0
    assert scores.metric_ranges["empathy"] == [1.0, 5.0]


# ---------------------------------------------------------------------------
# Phase 5: domain eval
# ---------------------------------------------------------------------------

def test_kg_source_spec_resolution():
    from agentic_cli.evaluation.domain_eval import get_kg_source, resolve_source
    from agentic_cli.evaluation.domain_eval import KgDomainSource

    src = get_kg_source("kg:cwow-facility")
    assert isinstance(src, KgDomainSource)
    assert src.domain == "cwow-facility"
    # resolve_source should route kg: to the KG source.
    assert isinstance(resolve_source("kg:cwow-patient"), KgDomainSource)

    with pytest.raises(ValueError):
        get_kg_source("kg:")


def test_kg_source_load_chunks_uses_query(monkeypatch):
    from agentic_cli.evaluation import domain_eval

    def fake_query(domain, aspects=None):
        return {"slas": "Response within 2s.", "security": "", "integrations": "API uses OAuth."}

    monkeypatch.setattr(
        "agentic_cli.kg.domain_context.query_domain_kg", fake_query, raising=True
    )
    src = domain_eval.KgDomainSource("cwow-facility")
    chunks = src.load_chunks()
    # Empty aspect text is filtered out.
    assert len(chunks) == 2
    aspects = {c.metadata["aspect"] for c in chunks}
    assert aspects == {"slas", "integrations"}


def test_save_and_load_config_to_meta_repo(tmp_path, monkeypatch):
    from agentic_cli.evaluation import domain_eval

    # Simulate a detected meta-repo at tmp_path with .platform/config present.
    (tmp_path / ".platform" / "config").mkdir(parents=True)

    def fake_detect(slug, search_paths=None):
        return tmp_path

    monkeypatch.setattr(
        "agentic_cli.meta_repo.detector.detect_domain_meta_repo", fake_detect, raising=True
    )

    cfg = EvaluationConfig(name="facility-eval", dataset="facility-qa",
                           metrics=["accuracy"], framework="builtin")
    out = domain_eval.save_config_to_meta_repo(cfg, "cwow-facility")
    assert out is not None and out.exists()
    assert out.parent == tmp_path / ".platform" / "config" / "eval"

    loaded = domain_eval.load_configs_from_meta_repo("cwow-facility")
    assert len(loaded) == 1
    assert loaded[0].name == "facility-eval"
    assert loaded[0].dataset == "facility-qa"


def test_save_config_no_meta_repo_returns_none(monkeypatch):
    from agentic_cli.evaluation import domain_eval

    monkeypatch.setattr(
        "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
        lambda slug, search_paths=None: None,
        raising=True,
    )
    cfg = EvaluationConfig(name="x", dataset="y")
    assert domain_eval.save_config_to_meta_repo(cfg, "nope") is None
