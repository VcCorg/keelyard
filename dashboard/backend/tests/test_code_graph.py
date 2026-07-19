"""Tests for the graphify code-graph reader/normalizer."""

import json

import pytest

from src.services import code_graph_service as svc


def _write_graph(tmp_path, data):
    gdir = tmp_path / "graphify-out"
    gdir.mkdir()
    (gdir / "graph.json").write_text(json.dumps(data), encoding="utf-8")
    return str(tmp_path)


def test_normalizes_nodes_and_edges(tmp_path):
    repo = _write_graph(tmp_path, {
        "nodes": [
            {"id": "a", "name": "auth.py", "type": "file", "path": "src/auth.py"},
            {"id": "b", "name": "login", "type": "function", "path": "src/auth.py"},
        ],
        "edges": [{"source": "a", "target": "b", "type": "DEFINES"}],
    })
    g = svc.load_code_graph(repo)
    assert g.node_total == 2 and g.edge_total == 1
    assert {n.id for n in g.nodes} == {"a", "b"}
    assert g.nodes[0].group == "src"          # top-level dir grouping
    assert g.edges[0].relationship == "DEFINES"
    assert g.truncated is False


def test_handles_links_key_and_node_objects_in_edges(tmp_path):
    repo = _write_graph(tmp_path, {
        "nodes": [{"id": "x"}, {"id": "y"}],
        "links": [{"from": {"id": "x"}, "to": {"id": "y"}, "label": "calls"}],
    })
    g = svc.load_code_graph(repo)
    assert g.edge_total == 1
    assert g.edges[0].source == "x" and g.edges[0].target == "y"
    assert g.edges[0].relationship == "calls"


def test_drops_dangling_edges(tmp_path):
    repo = _write_graph(tmp_path, {
        "nodes": [{"id": "a"}],
        "edges": [{"source": "a", "target": "ghost"}],
    })
    g = svc.load_code_graph(repo)
    assert g.edge_total == 0                   # edge to non-existent node dropped


def test_missing_graph_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="graphify"):
        svc.load_code_graph(str(tmp_path))


def test_bad_json_raises_value_error(tmp_path):
    gdir = tmp_path / "graphify-out"
    gdir.mkdir()
    (gdir / "graph.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(ValueError):
        svc.load_code_graph(str(tmp_path))


def test_truncation_keeps_most_connected(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "_MAX_NODES", 2)
    nodes = [{"id": str(i)} for i in range(5)]
    # node "0" is a hub connected to everyone; others are leaves.
    edges = [{"source": "0", "target": str(i)} for i in range(1, 5)]
    repo = _write_graph(tmp_path, {"nodes": nodes, "edges": edges})
    g = svc.load_code_graph(repo)
    assert g.truncated is True
    assert g.node_total == 5 and len(g.nodes) == 2
    assert "0" in {n.id for n in g.nodes}      # the hub survives


def test_list_code_repos_flags_graph(tmp_path, monkeypatch):
    repo = _write_graph(tmp_path, {"nodes": [{"id": "a"}], "edges": []})
    import agentic_cli.tracker as tracker

    monkeypatch.setattr(tracker, "get_repos", lambda **_k: [
        {"name": "with-graph", "path": repo, "languages": ["python"], "exists": True},
        {"name": "no-graph", "path": str(tmp_path / "nope"), "languages": [], "exists": False},
    ])
    rows = svc.list_code_repos()
    by_name = {r.name: r for r in rows}
    assert by_name["with-graph"].has_graph is True
    assert by_name["no-graph"].has_graph is False
