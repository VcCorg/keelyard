"""Tests for the OKF enrichment module (no LLM / no network required)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_cli.kg.okf.enrichment.runner import EnrichmentRunner, regenerate_indexes
from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source
from agentic_cli.kg.okf.enrichment.sources.code import CodebaseSource
from agentic_cli.kg.okf.enrichment.sources.confluence import ConfluenceSource, _html_to_text
from agentic_cli.kg.okf.enrichment.sources.graphify import (
    GraphifyCodeSource,
    MultiGraphifyCodeSource,
    ensure_graph,
)
from agentic_cli.kg.okf.enrichment.tools.bundle_tools import (
    check_augmentation_guard,
    concept_id_to_relpath,
    read_existing_doc,
    write_concept_doc,
)
from agentic_cli.kg.okf.schema import OKFSchema
from agentic_cli.kg.okf.validate import validate_bundle


# --------------------------------------------------------------------------- #
# bundle_tools
# --------------------------------------------------------------------------- #
def test_concept_id_to_relpath():
    assert concept_id_to_relpath("modules/auth") == "/modules/auth.md"
    assert concept_id_to_relpath("/modules/auth.md") == "/modules/auth.md"


def test_write_and_read_concept(tmp_path: Path):
    res = write_concept_doc(
        tmp_path, "modules/auth",
        {"type": "CodeModule", "title": "Auth"},
        "# Overview\nAuth module.\n",
    )
    assert "path" in res and res["bytes"] > 0
    got = read_existing_doc(tmp_path, "modules/auth")
    assert got is not None
    assert got["frontmatter"]["type"] == "CodeModule"
    assert "Auth module" in got["body"]
    # timestamp auto-added
    assert "timestamp" in got["frontmatter"]


def test_write_requires_type(tmp_path: Path):
    res = write_concept_doc(tmp_path, "x/y", {"title": "no type"}, "body")
    assert "error" in res


def test_augmentation_guard_blocks_schema_shrink():
    old = "# Schema\n| `user_id` | `email` |\n"
    new = "# Schema\n| `user_id` |\n"
    err = check_augmentation_guard(old, new)
    assert err is not None and "email" in err


def test_augmentation_guard_allows_growth():
    old = "# Schema\n| `user_id` |\n"
    new = "# Schema\n| `user_id` | `email` |\n"
    assert check_augmentation_guard(old, new) is None


def test_write_guard_enforced(tmp_path: Path):
    write_concept_doc(
        tmp_path, "modules/auth",
        {"type": "CodeModule", "title": "Auth"},
        "# Overview\nAuth.\n\n# Schema\n| `user_id` |\n",
    )
    blocked = write_concept_doc(
        tmp_path, "modules/auth",
        {"type": "CodeModule", "title": "Auth"},
        "# Overview\nshrunk\n",
        enforce_guard=True,
    )
    assert "error" in blocked
    grown = write_concept_doc(
        tmp_path, "modules/auth",
        {"type": "CodeModule", "title": "Auth"},
        "# Overview\nAuth.\n\n# Schema\n| `user_id` | `email` |\n",
        enforce_guard=True,
    )
    assert "path" in grown


# --------------------------------------------------------------------------- #
# CodebaseSource
# --------------------------------------------------------------------------- #
def test_codebase_source_lists_concepts(tmp_path: Path):
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "service.py").write_text("def login(): ...\n")
    (tmp_path / "src" / "billing").mkdir(parents=True)
    (tmp_path / "src" / "billing" / "charge.py").write_text("def charge(): ...\n")
    (tmp_path / "README.md").write_text("# Demo\nA demo repo.\n")

    src = CodebaseSource(tmp_path)
    refs = src.list_concepts()
    types = {r.type for r in refs}
    assert "Component" in types  # repo overview
    assert "CodeModule" in types
    ids = {r.id_str for r in refs}
    assert any(i.startswith("modules/") for i in ids)

    # read a module concept
    mod = next(r for r in refs if r.type == "CodeModule")
    data = src.read_concept(mod)
    assert data["kind"] == "code-module"
    assert "files" in data


def test_codebase_source_missing_path():
    with pytest.raises(ValueError):
        CodebaseSource(Path("/nonexistent/path/xyz"))


# --------------------------------------------------------------------------- #
# ConfluenceSource
# --------------------------------------------------------------------------- #
def test_html_to_text():
    html = "<h1>Title</h1><p>Hello&nbsp;<b>world</b></p>"
    text = _html_to_text(html)
    assert "Title" in text and "world" in text and "<" not in text


def test_confluence_source_from_docs():
    docs = [
        {"source_page_id": "123", "title": "Eligibility Rules"},
        {"source_page_id": "456", "title": "Care Plan Spec"},
    ]
    src = ConfluenceSource.from_domain_docs(docs)
    assert src.page_ids == ["123", "456"]
    refs = src.list_concepts()
    assert all(r.id[0] == "references" for r in refs)


# --------------------------------------------------------------------------- #
# index regeneration
# --------------------------------------------------------------------------- #
def test_regenerate_indexes(tmp_path: Path):
    OKFSchema.canonical(domain="demo", product="Demo").dump(tmp_path / "okf.schema.yaml")
    write_concept_doc(tmp_path, "modules/auth", {"type": "CodeModule", "title": "Auth"}, "# Overview\nA.\n")
    write_concept_doc(tmp_path, "apis/demo-api", {"type": "APIEndpoint", "title": "Demo API"}, "# Overview\nB.\n")
    n = regenerate_indexes(tmp_path)
    assert n >= 1
    root = (tmp_path / "index.md").read_text()
    assert "okf_version" in root  # root index carries okf_version only
    # subdir index has NO frontmatter
    sub = (tmp_path / "modules" / "index.md").read_text()
    assert not sub.startswith("---")


# --------------------------------------------------------------------------- #
# Runner with a fake model (no Vertex AI)
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModel:
    """Returns canned JSON for structural prompts."""

    def generate_content(self, prompt):
        return _FakeResp(
            '{"title": "Generated", "description": "d", "tags": ["t"], '
            '"body": "# Overview\\nGenerated body.\\n"}'
        )


class _TwoConceptSource(Source):
    name = "fake"

    def list_concepts(self):
        return [
            ConceptRef(id=("modules", "auth"), type="CodeModule", resource="/x/auth"),
            ConceptRef(id=("components", "app"), type="Component", resource="/x"),
        ]

    def read_concept(self, ref):
        return {"name": ref.id_str, "type": ref.type}


def test_runner_structural_pass(tmp_path: Path):
    OKFSchema.canonical(domain="demo", product="Demo").dump(tmp_path / "okf.schema.yaml")
    runner = EnrichmentRunner(
        source=_TwoConceptSource(),
        bundle_root=tmp_path,
        model=_FakeModel(),
    )
    result = runner.enrich_all()
    assert result.concepts_written == 2
    assert (tmp_path / "modules" / "auth.md").exists()
    assert (tmp_path / "components" / "app.md").exists()
    got = read_existing_doc(tmp_path, "modules/auth")
    assert "Generated body" in got["body"]


def test_runner_dry_run(tmp_path: Path):
    runner = EnrichmentRunner(
        source=_TwoConceptSource(),
        bundle_root=tmp_path,
        model=_FakeModel(),
        dry_run=True,
    )
    result = runner.enrich_all()
    assert result.concepts_written == 0
    assert len(result.planned) == 2
    assert not (tmp_path / "modules" / "auth.md").exists()


# --------------------------------------------------------------------------- #
# GraphifyCodeSource (deterministic, no LLM)
# --------------------------------------------------------------------------- #
def _write_graph(repo: Path) -> None:
    """Write a minimal graphify NetworkX node-link graph.json fixture."""
    graph = {
        "directed": True,
        "multigraph": False,
        "graph": {},
        "nodes": [
            {"id": "src_main_py", "label": "main.py", "file_type": "code",
             "source_file": "src/main.py", "source_location": "L1"},
            {"id": "src_main_run", "label": "run()", "file_type": "code",
             "source_file": "src/main.py", "source_location": "L3"},
            {"id": "src_auth_login_py", "label": "login.py", "file_type": "code",
             "source_file": "src/auth/login.py", "source_location": "L1"},
            {"id": "auth_login_authenticate", "label": "authenticate()", "file_type": "code",
             "source_file": "src/auth/login.py", "source_location": "L1"},
            {"id": "readme_md", "label": "README.md", "file_type": "document",
             "source_file": "README.md", "source_location": "L1"},
        ],
        "links": [
            {"relation": "contains", "source": "src_main_py", "target": "src_main_run"},
            {"relation": "contains", "source": "src_auth_login_py", "target": "auth_login_authenticate"},
            {"relation": "calls", "source": "src_main_run", "target": "auth_login_authenticate"},
        ],
        "hyperedges": [],
    }
    out = repo / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "graph.json").write_text(json.dumps(graph), encoding="utf-8")


def test_graphify_available(tmp_path: Path):
    assert GraphifyCodeSource.available(tmp_path) is False
    _write_graph(tmp_path)
    assert GraphifyCodeSource.available(tmp_path) is True


def test_graphify_lists_concepts(tmp_path: Path):
    _write_graph(tmp_path)
    src = GraphifyCodeSource(tmp_path)
    refs = src.list_concepts()
    types = {r.type for r in refs}
    assert {"Component", "CodeModule", "Code"} <= types
    ids = {r.id_str for r in refs}
    assert any(i.startswith("components/") for i in ids)
    assert any(i.startswith("modules/") for i in ids)
    assert any(i.startswith("code/") for i in ids)
    # documents are not advertised as code concepts
    assert not any("readme" in i for i in ids)


def test_graphify_render_is_deterministic_and_typed(tmp_path: Path):
    _write_graph(tmp_path)
    src = GraphifyCodeSource(tmp_path)
    refs = {r.id_str: r for r in src.list_concepts()}
    # The cross-file call produces a Code -[depends-on]-> Code typed link.
    main = next(r for r in refs.values() if r.type == "Code" and "main" in r.id_str)
    out = src.render_concept(main, src.read_concept(main))
    assert out is not None
    assert "depends-on" in out["body"]
    assert "graphify" in out["tags"]
    # Code concepts carry a resource (required by schema for type Code).
    assert main.resource


def test_graphify_deterministic_runner_validates(tmp_path: Path):
    """Full no-LLM structural pass produces a schema-valid bundle (model=None)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_graph(repo)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    OKFSchema.canonical(domain="demo", product="Demo").dump(bundle / "okf.schema.yaml")

    runner = EnrichmentRunner(
        source=GraphifyCodeSource(repo),
        bundle_root=bundle,
        model=None,  # must never be needed in deterministic mode
        structural_mode="deterministic",
    )
    result = runner.run_structural()
    assert result.errors == []
    assert result.concepts_written >= 3  # Component + module(s) + code file(s)

    rep = validate_bundle(bundle)
    assert rep.ok, rep.errors
    assert rep.typed_links >= 1  # at least the contains/depends-on edges


def test_graphify_namespaced_ids_and_links(tmp_path: Path):
    _write_graph(tmp_path)
    src = GraphifyCodeSource(tmp_path, namespace="alpha")
    ids = {r.id_str for r in src.list_concepts()}
    assert any(i.startswith("modules/alpha/") for i in ids)
    assert any(i.startswith("code/alpha/") for i in ids)
    assert "components/alpha" in ids
    # rendered internal links point at the namespaced paths
    comp = next(r for r in src.list_concepts() if r.type == "Component")
    body = src.render_concept(comp, src.read_concept(comp))["body"]
    assert "/modules/alpha/" in body


def test_multi_graphify_no_collision_and_validates(tmp_path: Path):
    """Two repos that share module/file names aggregate without colliding."""
    repo_a = tmp_path / "alpha"
    repo_b = tmp_path / "beta"
    repo_a.mkdir()
    repo_b.mkdir()
    _write_graph(repo_a)
    _write_graph(repo_b)  # identical structure -> would collide if not namespaced

    multi = MultiGraphifyCodeSource([repo_a, repo_b])
    ids = [r.id_str for r in multi.list_concepts()]
    # both repo components present, no duplicate concept IDs
    assert "components/alpha" in ids
    assert "components/beta" in ids
    assert len(ids) == len(set(ids)), "concept IDs collided across repos"

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    OKFSchema.canonical(domain="demo", product="Demo").dump(bundle / "okf.schema.yaml")
    runner = EnrichmentRunner(
        source=multi, bundle_root=bundle, model=None, structural_mode="deterministic"
    )
    result = runner.run_structural()
    assert result.errors == []
    rep = validate_bundle(bundle)
    assert rep.ok, rep.errors


def test_ensure_graph_existing(tmp_path: Path):
    _write_graph(tmp_path)
    ok, status = ensure_graph(tmp_path, generate=False)
    assert ok and status == "existing"


def test_ensure_graph_missing_no_generate(tmp_path: Path):
    ok, status = ensure_graph(tmp_path, generate=False)
    assert not ok and status == "missing"


def test_provenance_roundtrip_and_freshness(tmp_path: Path):
    from agentic_cli.kg.okf.provenance import (
        check_freshness,
        graph_hash,
        read_provenance,
        write_provenance,
    )

    repo = tmp_path / "svc"
    repo.mkdir()
    _write_graph(repo)
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    out = write_provenance(bundle, [repo], code_source="graphify", source="both")
    assert out.exists()
    prov = read_provenance(bundle)
    assert prov and prov["schema"] == "okf-provenance/v1"
    assert prov["repos"][0]["graph_hash"] == graph_hash(repo)

    # unchanged -> fresh
    rep = check_freshness(bundle, [repo])
    assert rep.has_provenance and not rep.stale
    assert all(r.status == "fresh" for r in rep.repos)

    # change the graph -> stale
    gp = repo / "graphify-out" / "graph.json"
    data = json.loads(gp.read_text())
    data["nodes"].append({"id": "x", "label": "x.py", "file_type": "code",
                          "source_file": "src/x.py", "source_location": "L1"})
    gp.write_text(json.dumps(data))
    rep2 = check_freshness(bundle, [repo])
    assert rep2.stale
    assert rep2.repos[0].status == "stale"
    assert "svc" in rep2.stale_repos


def test_freshness_no_provenance_is_stale(tmp_path: Path):
    from agentic_cli.kg.okf.provenance import check_freshness

    repo = tmp_path / "svc"
    repo.mkdir()
    _write_graph(repo)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    rep = check_freshness(bundle, [repo])
    assert not rep.has_provenance
    assert rep.stale  # nothing recorded yet -> treat as needing enrich


def test_freshness_new_and_removed_repos(tmp_path: Path):
    from agentic_cli.kg.okf.provenance import check_freshness, write_provenance

    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _write_graph(a)
    _write_graph(b)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    # enrich recorded only repo a
    write_provenance(bundle, [a])
    # now repos are b (new) — a removed
    rep = check_freshness(bundle, [b])
    statuses = {r.repo: r.status for r in rep.repos}
    assert statuses["b"] == "new"
    assert statuses["a"] == "removed"
    assert rep.stale


def test_domain_lock_busy_and_release(tmp_path: Path, monkeypatch):
    from agentic_cli.kg.okf import locking

    # Isolate lock files under tmp so the test never touches the real temp dir.
    monkeypatch.setattr(locking.tempfile, "gettempdir", lambda: str(tmp_path))

    assert not locking.is_locked("dom1", "okf")
    with locking.domain_lock("dom1", scope="okf"):
        assert locking.is_locked("dom1", "okf")
        # A second acquisition of the same key is non-blocking and must fail.
        with pytest.raises(locking.DomainLockBusy):
            with locking.domain_lock("dom1", scope="okf"):
                pass
        # A different domain is independent.
        with locking.domain_lock("dom2", scope="okf"):
            assert locking.is_locked("dom2", "okf")
    # Released after the context exits.
    assert not locking.is_locked("dom1", "okf")


def test_base_source_render_concept_returns_none():
    """The default Source.render_concept declines (forces LLM fallback)."""

    class _S(Source):
        def list_concepts(self):
            return []

        def read_concept(self, ref):
            return {}

    assert _S().render_concept(ConceptRef(id=("x",), type="Code"), {}) is None


# --------------------------------------------------------------------------- #
# visualize
# --------------------------------------------------------------------------- #
def test_visualize_build_graph(tmp_path: Path):
    from agentic_cli.kg.okf.visualize import build_graph, render_html, write_html

    write_concept_doc(
        tmp_path, "components/app", {"type": "Component", "title": "App"},
        "# Overview\nApp.\n",
    )
    write_concept_doc(
        tmp_path, "modules/auth", {"type": "CodeModule", "title": "Auth"},
        "# Overview\nAuth, part of [App](/components/app.md).\n",
    )
    g = build_graph(tmp_path)
    assert g.node_count == 2
    assert g.edge_count == 1
    assert g.edges[0]["data"]["source"] == "modules/auth"
    assert g.edges[0]["data"]["target"] == "components/app"

    html = render_html(tmp_path, title="T")
    assert "cytoscape" in html and "modules/auth" in html

    out = write_html(tmp_path)
    assert out.exists() and out.name == "viz.html"


def test_visualize_dangling_links_excluded(tmp_path: Path):
    from agentic_cli.kg.okf.visualize import build_graph

    write_concept_doc(
        tmp_path, "modules/auth", {"type": "CodeModule", "title": "Auth"},
        "# Overview\nLinks to [missing](/does/not/exist.md).\n",
    )
    g = build_graph(tmp_path)
    assert g.node_count == 1
    assert g.edge_count == 0  # dangling link not rendered
