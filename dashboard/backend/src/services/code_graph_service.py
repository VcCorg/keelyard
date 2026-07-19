"""Code graph service — read graphify's ``graph.json`` for frontend review.

`keel code onboard --graphify` writes a structural code graph to
``<repo>/graphify-out/graph.json``. It powers CLI queries but was never
viewable — this service lists onboarded repos that have a graph and normalizes
the graph into the ``{nodes, links}`` shape the dashboard's force-graph renders,
so a lead/dev can visually validate what was captured before it feeds the KG.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

GRAPHIFY_REL = ("graphify-out", "graph.json")
_MAX_NODES = 1500  # keep the browser force-graph responsive


class CodeRepo(BaseModel):
    name: str
    path: str
    exists: bool = False
    has_graph: bool = False
    languages: List[str] = []
    domain: Optional[str] = None


class CodeGraphNode(BaseModel):
    id: str
    label: str
    kind: str = "node"        # file | function | class | module | …
    group: str = ""           # for coloring (kind or top-level dir)


class CodeGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str = "references"


class CodeGraph(BaseModel):
    repo: str
    nodes: List[CodeGraphNode] = []
    edges: List[CodeGraphEdge] = []
    truncated: bool = False
    node_total: int = 0
    edge_total: int = 0


def _graph_path(repo_path: str) -> Path:
    return Path(repo_path).expanduser() / GRAPHIFY_REL[0] / GRAPHIFY_REL[1]


def list_code_repos() -> List[CodeRepo]:
    """Onboarded repos, flagged with whether a graphify graph exists on disk."""
    try:
        from agentic_cli.tracker import get_repos

        rows = get_repos(check_exists=True)
    except Exception:  # noqa: BLE001
        rows = []
    out: List[CodeRepo] = []
    for r in rows:
        path = r.get("path", "")
        langs = r.get("languages") or []
        if isinstance(langs, str):
            langs = [langs]
        out.append(CodeRepo(
            name=r.get("name") or Path(path).name, path=path,
            exists=bool(r.get("exists")),
            has_graph=_graph_path(path).is_file() if path else False,
            languages=langs, domain=r.get("domain")))
    return out


def _node_id(raw: Any, idx: int) -> str:
    if isinstance(raw, dict):
        return str(raw.get("id") or raw.get("name") or raw.get("path") or raw.get("label") or idx)
    return str(raw)


def _norm_nodes(data: Dict[str, Any]) -> tuple[List[CodeGraphNode], set]:
    raw_nodes = data.get("nodes") or data.get("vertices") or []
    nodes: List[CodeGraphNode] = []
    ids: set = set()
    for i, n in enumerate(raw_nodes):
        if isinstance(n, dict):
            nid = str(n.get("id") or n.get("name") or n.get("path") or i)
            label = str(n.get("label") or n.get("name") or n.get("path") or nid)
            kind = str(n.get("kind") or n.get("type") or n.get("category") or "node")
            # Group by top-level directory when a path is available, else kind.
            path = str(n.get("path") or "")
            group = path.split("/")[0] if "/" in path else kind
        else:
            nid = label = str(n)
            kind, group = "node", "node"
        if nid in ids:
            continue
        ids.add(nid)
        nodes.append(CodeGraphNode(id=nid, label=label.split("/")[-1][:60] or nid,
                                   kind=kind, group=group))
    return nodes, ids


def _norm_edges(data: Dict[str, Any], valid_ids: set) -> List[CodeGraphEdge]:
    raw_edges = data.get("edges") or data.get("links") or data.get("relationships") or []
    edges: List[CodeGraphEdge] = []
    for e in raw_edges:
        if not isinstance(e, dict):
            continue
        s = e.get("source") or e.get("from") or e.get("src")
        t = e.get("target") or e.get("to") or e.get("dst")
        if isinstance(s, dict):
            s = s.get("id") or s.get("name")
        if isinstance(t, dict):
            t = t.get("id") or t.get("name")
        s, t = str(s) if s is not None else "", str(t) if t is not None else ""
        if not s or not t or s not in valid_ids or t not in valid_ids:
            continue
        rel = str(e.get("relationship") or e.get("type") or e.get("label") or "references")
        edges.append(CodeGraphEdge(source=s, target=t, relationship=rel))
    return edges


def load_code_graph(repo_path: str) -> CodeGraph:
    """Read + normalize a repo's graphify graph (truncated for the browser)."""
    gp = _graph_path(repo_path)
    if not gp.is_file():
        raise FileNotFoundError(
            f"No graphify graph at {gp}. Onboard with --graphify (or run "
            "`graphify update` in the repo) to generate one.")
    try:
        data = json.loads(gp.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        raise ValueError(f"graph.json is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ValueError("graph.json has an unexpected shape (expected an object)")

    nodes, ids = _norm_nodes(data)
    edges = _norm_edges(data, ids)
    node_total, edge_total = len(nodes), len(edges)
    truncated = node_total > _MAX_NODES
    if truncated:
        # Keep the most-connected nodes so the view stays meaningful.
        degree: Dict[str, int] = {}
        for e in edges:
            degree[e.source] = degree.get(e.source, 0) + 1
            degree[e.target] = degree.get(e.target, 0) + 1
        keep = {n.id for n in sorted(nodes, key=lambda n: degree.get(n.id, 0),
                                     reverse=True)[:_MAX_NODES]}
        nodes = [n for n in nodes if n.id in keep]
        edges = [e for e in edges if e.source in keep and e.target in keep]

    return CodeGraph(repo=Path(repo_path).name, nodes=nodes, edges=edges,
                     truncated=truncated, node_total=node_total, edge_total=edge_total)
