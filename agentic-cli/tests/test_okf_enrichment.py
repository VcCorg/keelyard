"""Tests for the OKF enrichment module (no LLM / no network required)."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_cli.kg.okf.enrichment.runner import EnrichmentRunner, regenerate_indexes
from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source
from agentic_cli.kg.okf.enrichment.sources.code import CodebaseSource
from agentic_cli.kg.okf.enrichment.sources.confluence import ConfluenceSource, _html_to_text
from agentic_cli.kg.okf.enrichment.tools.bundle_tools import (
    check_augmentation_guard,
    concept_id_to_relpath,
    read_existing_doc,
    write_concept_doc,
)
from agentic_cli.kg.okf.schema import OKFSchema


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
