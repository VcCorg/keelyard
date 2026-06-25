"""Render an OKF bundle as an interactive graph (self-contained HTML).

Walks the bundle, builds nodes (one per concept, colored by type) and edges
(one per typed link in the markdown body), and emits a single `viz.html` that
loads Cytoscape.js from a CDN. No build step or server required — open the file
in a browser.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agentic_cli.kg.okf.model import Concept

_RESERVED = {"index.md", "log.md", "okf.schema.yaml", "nonconforming.md"}

# Stable palette by concept type (extras fall back to a neutral grey).
_TYPE_COLORS = {
    "Component": "#6366f1",
    "CodeModule": "#0ea5e9",
    "APIEndpoint": "#14b8a6",
    "DataModel": "#84cc16",
    "Feature": "#f59e0b",
    "Requirement": "#ec4899",
    "FREQ": "#ef4444",
    "UserStory": "#a855f7",
    "Code": "#22c55e",
    "Test": "#eab308",
    "Release": "#f97316",
    "Facility": "#06b6d4",
    "Patient": "#3b82f6",
    "Encounter": "#8b5cf6",
}
_DEFAULT_COLOR = "#94a3b8"


@dataclass
class GraphData:
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    type_counts: dict[str, int] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


def build_graph(bundle_root: Path) -> GraphData:
    """Read every concept in the bundle into a node/edge graph."""
    bundle_root = Path(bundle_root)
    g = GraphData()
    ids: set[str] = set()

    concepts: list[Concept] = []
    for p in sorted(bundle_root.rglob("*.md")):
        if p.name in _RESERVED:
            continue
        c = Concept.read(p, bundle_root)
        if c is None:
            continue
        concepts.append(c)

    for c in concepts:
        cid = c.id
        ids.add(cid)
        ctype = c.type or "Unknown"
        g.type_counts[ctype] = g.type_counts.get(ctype, 0) + 1
        g.nodes.append(
            {
                "data": {
                    "id": cid,
                    "label": c.title or cid,
                    "type": ctype,
                    "color": _TYPE_COLORS.get(ctype, _DEFAULT_COLOR),
                    "description": str(c.fm.get("description", "")),
                }
            }
        )

    # Edges: typed links whose target resolves to a known concept id.
    for c in concepts:
        src = c.id
        for link in c.links():
            target = link.target.lstrip("/")
            tgt_id = target[:-3] if target.endswith(".md") else target
            if tgt_id in ids and tgt_id != src:
                g.edges.append(
                    {
                        "data": {
                            "id": f"{src}->{tgt_id}:{link.role or 'ref'}",
                            "source": src,
                            "target": tgt_id,
                            "role": link.role or "references",
                        }
                    }
                )

    return g


def render_html(bundle_root: Path, title: str = "OKF Knowledge Graph") -> str:
    """Build the graph and return a self-contained HTML document string."""
    g = build_graph(bundle_root)
    elements = json.dumps(g.nodes + g.edges)
    legend = json.dumps(
        [
            {"type": t, "color": _TYPE_COLORS.get(t, _DEFAULT_COLOR), "count": n}
            for t, n in sorted(g.type_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
    )
    return _HTML_TEMPLATE.format(
        title=title,
        elements=elements,
        legend=legend,
        node_count=g.node_count,
        edge_count=g.edge_count,
    )


def write_html(bundle_root: Path, out: Path | None = None, title: str = "OKF Knowledge Graph") -> Path:
    """Render and write `viz.html` into the bundle (or to `out`). Returns the path."""
    bundle_root = Path(bundle_root)
    out_path = Path(out) if out else (bundle_root / "viz.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(bundle_root, title=title), encoding="utf-8")
    return out_path


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.2/cytoscape.min.js"></script>
<style>
  :root {{ --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --muted:#94a3b8; }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; height:100%; background:var(--bg); color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  #bar {{ padding:10px 16px; background:var(--panel); display:flex; gap:16px;
    align-items:center; border-bottom:1px solid #334155; flex-wrap:wrap; }}
  #bar h1 {{ font-size:15px; margin:0; font-weight:600; }}
  #bar .stat {{ color:var(--muted); font-size:13px; }}
  #bar input {{ background:#0f172a; border:1px solid #334155; color:var(--text);
    padding:6px 10px; border-radius:6px; font-size:13px; width:220px; }}
  #legend {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .lg {{ display:flex; align-items:center; gap:5px; font-size:12px; cursor:pointer;
    color:var(--muted); user-select:none; }}
  .lg .sw {{ width:11px; height:11px; border-radius:3px; display:inline-block; }}
  .lg.off {{ opacity:0.35; text-decoration:line-through; }}
  #cy {{ position:absolute; top:0; bottom:0; left:0; right:0; }}
  #wrap {{ position:absolute; top:0; bottom:0; left:0; right:0;
    display:flex; flex-direction:column; }}
  #graph {{ position:relative; flex:1; }}
  #info {{ position:absolute; right:12px; top:12px; width:300px; max-height:70%;
    overflow:auto; background:var(--panel); border:1px solid #334155;
    border-radius:8px; padding:14px; font-size:13px; display:none; }}
  #info h2 {{ margin:0 0 4px; font-size:15px; }}
  #info .t {{ color:var(--muted); font-size:12px; margin-bottom:8px; }}
  #info .x {{ float:right; cursor:pointer; color:var(--muted); }}
</style>
</head>
<body>
<div id="wrap">
  <div id="bar">
    <h1>{title}</h1>
    <span class="stat">{node_count} concepts &middot; {edge_count} links</span>
    <input id="search" placeholder="Filter concepts..." />
    <div id="legend"></div>
  </div>
  <div id="graph">
    <div id="cy"></div>
    <div id="info"></div>
  </div>
</div>
<script>
  const elements = {elements};
  const legendData = {legend};

  const cy = cytoscape({{
    container: document.getElementById('cy'),
    elements: elements,
    style: [
      {{ selector: 'node', style: {{
        'background-color': 'data(color)',
        'label': 'data(label)', 'color': '#e2e8f0', 'font-size': '10px',
        'text-valign': 'bottom', 'text-margin-y': 4, 'width': 26, 'height': 26,
        'text-wrap': 'wrap', 'text-max-width': '120px',
        'border-width': 1, 'border-color': '#0f172a'
      }}}},
      {{ selector: 'edge', style: {{
        'width': 1.4, 'line-color': '#475569', 'target-arrow-color': '#475569',
        'target-arrow-shape': 'triangle', 'curve-style': 'bezier',
        'label': 'data(role)', 'font-size': '8px', 'color': '#64748b',
        'text-rotation': 'autorotate', 'text-background-opacity': 0
      }}}},
      {{ selector: 'node.dim', style: {{ 'opacity': 0.12 }}}},
      {{ selector: 'edge.dim', style: {{ 'opacity': 0.05 }}}},
      {{ selector: 'node.hl', style: {{ 'border-width': 3, 'border-color': '#facc15' }}}}
    ],
    layout: {{ name: 'cose', animate: false, padding: 40, nodeRepulsion: 9000,
               idealEdgeLength: 90, gravity: 0.3 }}
  }});

  // Legend with toggle-by-type.
  const legendEl = document.getElementById('legend');
  const hidden = new Set();
  legendData.forEach(function(d) {{
    const el = document.createElement('span');
    el.className = 'lg';
    el.innerHTML = '<span class="sw" style="background:' + d.color + '"></span>' +
                   d.type + ' (' + d.count + ')';
    el.onclick = function() {{
      if (hidden.has(d.type)) {{ hidden.delete(d.type); el.classList.remove('off'); }}
      else {{ hidden.add(d.type); el.classList.add('off'); }}
      cy.nodes().forEach(function(n) {{
        n.style('display', hidden.has(n.data('type')) ? 'none' : 'element');
      }});
    }};
    legendEl.appendChild(el);
  }});

  // Click a node -> details + neighborhood highlight.
  const info = document.getElementById('info');
  cy.on('tap', 'node', function(evt) {{
    const n = evt.target;
    cy.elements().addClass('dim');
    const nb = n.closedNeighborhood();
    nb.removeClass('dim');
    cy.nodes().removeClass('hl'); n.addClass('hl');
    info.style.display = 'block';
    info.innerHTML = '<span class="x" onclick="document.getElementById(\\'info\\')' +
      '.style.display=\\'none\\';cy.elements().removeClass(\\'dim\\');cy.nodes().removeClass(\\'hl\\')">close</span>' +
      '<h2>' + n.data('label') + '</h2>' +
      '<div class="t">' + n.data('type') + ' &middot; ' + n.id() + '</div>' +
      '<div>' + (n.data('description') || '<i>no description</i>') + '</div>';
  }});
  cy.on('tap', function(evt) {{
    if (evt.target === cy) {{
      cy.elements().removeClass('dim'); cy.nodes().removeClass('hl');
      info.style.display = 'none';
    }}
  }});

  // Search filter.
  document.getElementById('search').addEventListener('input', function(e) {{
    const q = e.target.value.toLowerCase().trim();
    cy.nodes().forEach(function(n) {{
      if (hidden.has(n.data('type'))) return;
      const match = !q || (n.data('label') || '').toLowerCase().includes(q) ||
                    n.id().toLowerCase().includes(q);
      n.style('display', match ? 'element' : 'none');
    }});
  }});
</script>
</body>
</html>
"""
