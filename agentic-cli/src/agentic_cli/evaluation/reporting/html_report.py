"""Self-contained interactive HTML reports for evaluation runs.

Produces a single HTML file with no external dependencies (inline CSS + a small
amount of vanilla JS). Supports a single-run report (aggregate + per-row
drill-down) and an optional comparison section across multiple runs.
"""

import html
import json
from pathlib import Path
from typing import List, Optional

from agentic_cli.evaluation.results import EvalRunResult
from agentic_cli.evaluation.reporting.compare import Comparison


def _bar(value: float, low: float, high: float) -> str:
    """Return a 0-100 width percentage for a score bar."""
    if high == low:
        pct = 0.0
    else:
        pct = max(0.0, min(1.0, (value - low) / (high - low))) * 100
    return f"{pct:.1f}"


def render_single_run(run: EvalRunResult) -> str:
    """Render a single evaluation run as an HTML fragment."""
    rows_html = []
    for name, value in run.aggregate.items():
        rng = run.metric_ranges.get(name, [0.0, 1.0])
        width = _bar(value, rng[0], rng[1])
        rows_html.append(
            f"<tr><td>{html.escape(name)}</td>"
            f"<td class='num'>{value:.3f}</td>"
            f"<td class='range'>{rng[0]}–{rng[1]}</td>"
            f"<td class='barcell'><div class='bar' style='width:{width}%'></div></td></tr>"
        )

    per_row_json = json.dumps(run.per_row)
    errors_html = ""
    if run.errors:
        items = "".join(f"<li>{html.escape(str(e))}</li>" for e in run.errors)
        errors_html = f"<div class='errors'><h4>Errors</h4><ul>{items}</ul></div>"

    return f"""
    <section class="run">
      <h2>{html.escape(run.eval_name)} — {html.escape(run.agent)}</h2>
      <div class="meta">
        <span><b>Framework:</b> {html.escape(run.framework)}</span>
        <span><b>Judge:</b> {html.escape(run.judge)}</span>
        <span><b>Dataset:</b> {html.escape(run.dataset)} v{run.dataset_version}</span>
        <span><b>Rows:</b> {run.num_rows}</span>
        <span><b>Overall:</b> {run.overall_score():.3f}</span>
        <span><b>Time:</b> {html.escape(run.timestamp[:19])}</span>
      </div>
      <table class="scores">
        <thead><tr><th>Metric</th><th>Score</th><th>Range</th><th>Level</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
      {errors_html}
      <details class="drill">
        <summary>Per-row scores ({len(run.per_row)} rows)</summary>
        <div class="perrow" data-rows='{html.escape(per_row_json)}'></div>
      </details>
    </section>
    """


def render_comparison(comp: Comparison) -> str:
    """Render a comparison section as an HTML fragment."""
    if not comp.labels:
        return ""

    header = "".join(f"<th>{html.escape(l)}</th>" for l in comp.labels)
    body = []
    for row in comp.rows:
        cells = []
        for label in comp.labels:
            score = row.scores.get(label)
            cls = "win" if label == row.best_label and score is not None else ""
            cells.append(
                f"<td class='num {cls}'>{score:.3f}</td>" if score is not None else "<td class='num'>—</td>"
            )
        body.append(f"<tr><td>{html.escape(row.metric)}</td>{''.join(cells)}</tr>")

    overall_cells = "".join(
        f"<td class='num'>{comp.overall.get(l, 0):.3f}</td>" for l in comp.labels
    )
    ranking = " &gt; ".join(html.escape(l) for l in comp.ranking)

    return f"""
    <section class="comparison">
      <h2>Comparison</h2>
      <p class="ranking"><b>Ranking:</b> {ranking}</p>
      <table class="scores">
        <thead><tr><th>Metric</th>{header}</tr></thead>
        <tbody>
          {''.join(body)}
          <tr class="overall"><td><b>Overall (normalized)</b></td>{overall_cells}</tr>
        </tbody>
      </table>
    </section>
    """


_CSS = """
:root { --bg:#0f172a; --card:#1e293b; --fg:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; --win:#22c55e; }
* { box-sizing: border-box; }
body { margin:0; font-family:-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--fg); padding:2rem; }
h1 { margin:0 0 .25rem; } h2 { color:var(--accent); border-bottom:1px solid #334155; padding-bottom:.35rem; }
.subtitle { color:var(--muted); margin-bottom:2rem; }
section { background:var(--card); border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,.4); }
.meta { display:flex; flex-wrap:wrap; gap:1rem; color:var(--muted); font-size:.9rem; margin:.5rem 0 1rem; }
table.scores { width:100%; border-collapse:collapse; }
table.scores th, table.scores td { text-align:left; padding:.5rem .6rem; border-bottom:1px solid #334155; }
td.num { text-align:right; font-variant-numeric:tabular-nums; } td.range { color:var(--muted); }
.barcell { width:40%; } .bar { height:10px; background:linear-gradient(90deg,#38bdf8,#22c55e); border-radius:6px; }
.win { color:var(--win); font-weight:700; } tr.overall td { border-top:2px solid #475569; }
.ranking { color:var(--fg); } .errors { color:#fca5a5; } .drill summary { cursor:pointer; color:var(--accent); margin-top:.75rem; }
.perrow table { width:100%; border-collapse:collapse; margin-top:.5rem; font-size:.85rem; }
.perrow th, .perrow td { border-bottom:1px solid #334155; padding:.3rem .5rem; text-align:right; } .perrow th:first-child, .perrow td:first-child { text-align:left; }
"""

_JS = """
document.querySelectorAll('.perrow').forEach(function(el){
  var rows = JSON.parse(el.getAttribute('data-rows') || '[]');
  if (!rows.length) { el.innerHTML = '<p>No per-row data.</p>'; return; }
  var metrics = Object.keys(rows[0]);
  var thead = '<tr><th>#</th>' + metrics.map(function(m){return '<th>'+m+'</th>';}).join('') + '</tr>';
  var body = rows.map(function(r, i){
    return '<tr><td>'+(i+1)+'</td>' + metrics.map(function(m){
      var v = r[m]; return '<td>'+(v==null?'—':Number(v).toFixed(3))+'</td>';
    }).join('') + '</tr>';
  }).join('');
  el.innerHTML = '<table><thead>'+thead+'</thead><tbody>'+body+'</tbody></table>';
});
"""


def build_html_report(
    title: str,
    runs: List[EvalRunResult],
    comparison: Optional[Comparison] = None,
) -> str:
    """Build a complete, self-contained HTML report document.

    Args:
        title: Report title.
        runs: Runs to include as individual sections.
        comparison: Optional comparison section to render first.

    Returns:
        The full HTML document as a string.
    """
    parts = [render_comparison(comparison)] if comparison else []
    parts.extend(render_single_run(r) for r in runs)
    body = "\n".join(p for p in parts if p)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>{_CSS}</style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="subtitle">Agentic CLI — Agent Evaluation Report</p>
  {body}
  <script>{_JS}</script>
</body>
</html>
"""


def write_html_report(
    output_path: Path,
    title: str,
    runs: List[EvalRunResult],
    comparison: Optional[Comparison] = None,
) -> Path:
    """Write an HTML report to disk and return its path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_report(title, runs, comparison), encoding="utf-8")
    return output_path
