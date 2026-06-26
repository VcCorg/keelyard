"""End-to-end smoke test for eval Phases 2-5 (zero-dep paths).

Runs the CLI against temporary storage:
  generate -> create -> run agent x2 -> compare -> report -> custom metric.
"""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

import agentic_cli.commands.eval as ev
from agentic_cli.evaluation.eval_config import EvalConfigManager
from agentic_cli.evaluation.csv_dataset import CsvDatasetManager
from agentic_cli.evaluation.results import EvalResultStore
from agentic_cli.evaluation.custom_metrics import CustomMetricManager
from agentic_cli.evaluation.generation import GoldenRegistry


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    ev.EVAL_CONFIGS_DIR = tmp / "cfg"
    ev.CSV_DATASETS_DIR = tmp / "csv"
    ev.EVALS_DIR = tmp / "ev"
    ev.CUSTOM_METRICS_DIR = tmp / "cm"
    ev.config_manager = EvalConfigManager(ev.EVAL_CONFIGS_DIR)
    ev.csv_manager = CsvDatasetManager(ev.CSV_DATASETS_DIR)
    ev.result_store = EvalResultStore(ev.EVALS_DIR)
    ev.custom_metric_manager = CustomMetricManager(ev.CUSTOM_METRICS_DIR)
    ev.golden_registry = GoldenRegistry(ev.CSV_DATASETS_DIR)

    docs = tmp / "docs"
    docs.mkdir()
    (docs / "faq.md").write_text(
        "# Eligibility\n\nPatients qualify if they meet criteria.\n\n"
        "# Billing\n\nClaims within 30 days."
    )

    r = CliRunner()

    def run(args):
        res = r.invoke(ev.eval_app, args)
        print(">", " ".join(args), "=>", res.exit_code)
        if res.exit_code != 0:
            print(res.output)
            raise SystemExit(1)

    run(["dataset", "generate", "faq", "--source", f"local:{docs}",
         "-n", "6", "--adversarial-ratio", "0.34", "--golden"])
    run(["create", "faq-eval", "faq", "-m", "accuracy,f1_score"])
    run(["run", "agent", "mock:simple", "faq-eval"])
    run(["run", "agent", "mock:helpful", "faq-eval"])
    run(["compare", "faq-eval", "-o", str(tmp / "cmp.html")])
    run(["report", "generate", "faq-eval", "-o", str(tmp / "rep.html")])
    run(["metric", "register", "empathy", "-p", "Rate empathy 1-5."])
    run(["metric", "list"])
    run(["metric", "unregister", "empathy"])

    print("SMOKE OK; html exists:",
          (tmp / "cmp.html").exists(), (tmp / "rep.html").exists())


if __name__ == "__main__":
    main()
