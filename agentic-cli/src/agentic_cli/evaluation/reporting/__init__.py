"""Reporting and comparison for agent evaluation runs."""

from agentic_cli.evaluation.reporting.compare import (
    Comparison,
    ComparisonRow,
    compare_runs,
)
from agentic_cli.evaluation.reporting.html_report import (
    build_html_report,
    write_html_report,
)

__all__ = [
    "Comparison",
    "ComparisonRow",
    "compare_runs",
    "build_html_report",
    "write_html_report",
]
