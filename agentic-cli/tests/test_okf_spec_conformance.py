"""OKF v0.1 spec conformance + feature-grouped layout (no Neo4j required).

Exercises the pure assembly path (``_assemble_and_write``) with synthetic nodes,
then validates the on-disk bundle against the spec and the Devin push mapping.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_cli.kg.okf.exporter import (
    ExportResult,
    _Node,
    _assemble_and_write,
    _assign_features,
    _finalize_paths,
)
from agentic_cli.kg.okf.schema import OKFSchema
from agentic_cli.kg.okf.bundle import Bundle
from agentic_cli.kg.okf.model import Concept
from agentic_cli.kg.okf import devin

DOMAIN = "cwow-facility"


def _make_nodes() -> tuple[list[_Node], list[_Node]]:
    """Two features + a shared (unreachable) concept.

    freq A -> req1 -> assessment1 (reachable from A)
    freq B -> req2                (reachable from B)
    orphan                        (no edges -> shared)
    """
    freq_a = _Node("freq:CWOW-100", "FREQ", True, "freq-cwow-100",
                   {"type": "FREQ", "title": "CWOW-100", "freq_id": "CWOW-100",
                    "jira": "https://jira/CWOW-100", "resource": "https://jira/CWOW-100",
                    "domain": DOMAIN}, "FREQ A excerpt.")
    freq_b = _Node("freq:CWOW-200", "FREQ", True, "freq-cwow-200",
                   {"type": "FREQ", "title": "CWOW-200", "freq_id": "CWOW-200",
                    "jira": "https://jira/CWOW-200", "resource": "https://jira/CWOW-200",
                    "domain": DOMAIN}, "FREQ B excerpt.")
    req1 = _Node("req1", "Requirement", True, "requirement-login",
                 {"type": "Requirement", "title": "Login", "description": "Login flow.",
                  "domain": DOMAIN}, "Login requirement.")
    req2 = _Node("req2", "Requirement", True, "requirement-export",
                 {"type": "Requirement", "title": "Export", "description": "Export flow.",
                  "domain": DOMAIN}, "Export requirement.")
    assess1 = _Node("a1", "Assessment", True, "assessment-pwd",
                    {"type": "Assessment", "title": "Password rule", "domain": DOMAIN},
                    "Password complexity.")
    orphan = _Node("o1", "Assessment", True, "assessment-orphan",
                   {"type": "Assessment", "title": "Orphan", "domain": DOMAIN}, "No edges.")

    # links store destination *ids* (role, dst_id, dst_title)
    freq_a.links.append(("part-of", "req1", "Login"))
    freq_b.links.append(("part-of", "req2", "Export"))
    req1.links.append(("relates-to", "a1", "Password rule"))

    all_nodes = [freq_a, freq_b, req1, req2, assess1, orphan]
    freq_nodes = [freq_a, freq_b]
    return all_nodes, freq_nodes


def _build_bundle(tmp_path: Path) -> Path:
    all_nodes, freq_nodes = _make_nodes()
    schema = OKFSchema.canonical(domain=DOMAIN, product="CWOW")
    schema.rules["require_citations_for"] = []
    schema.rules["resource_required_for"] = []
    result = ExportResult(domain=DOMAIN, out_dir=tmp_path)
    _assemble_and_write(tmp_path, DOMAIN, "CWOW", schema, all_nodes, freq_nodes, result)
    return tmp_path


# ── Feature assignment ───────────────────────────────────────────────────────

def test_bfs_feature_assignment():
    all_nodes, freq_nodes = _make_nodes()
    by_id = {n.node_id: n for n in all_nodes}
    owner = _assign_features(all_nodes, freq_nodes, by_id)
    assert owner["req1"] == "CWOW-100"
    assert owner["a1"] == "CWOW-100"        # reachable A -> req1 -> a1
    assert owner["req2"] == "CWOW-200"
    assert "o1" not in owner                # orphan -> shared


def test_finalize_paths_layout():
    all_nodes, freq_nodes = _make_nodes()
    by_id = {n.node_id: n for n in all_nodes}
    owner = _assign_features(all_nodes, freq_nodes, by_id)
    _finalize_paths(all_nodes, owner)
    paths = {n.node_id: n.rel_path for n in all_nodes}
    assert paths["freq:CWOW-100"] == "/features/cwow-100/freq-cwow-100.md"
    assert paths["a1"].startswith("/features/cwow-100/")
    assert paths["o1"].startswith("/shared/")


# ── Spec §6 / §9 conformance ─────────────────────────────────────────────────

def test_root_index_frontmatter_only_okf_version(tmp_path):
    root = _build_bundle(tmp_path)
    text = (root / "index.md").read_text()
    assert text.startswith("---\n")
    fm_block = text.split("---\n")[1]
    assert "okf_version: '0.1'" in fm_block or 'okf_version: "0.1"' in fm_block or "okf_version: 0.1" in fm_block
    # the ONLY permitted key in an index frontmatter
    for forbidden in ("type:", "title:", "id:", "domain:"):
        assert forbidden not in fm_block, f"index.md frontmatter must not contain {forbidden}"
    assert "* [features/](features/)" in text
    assert "* [shared/](shared/)" in text


def test_subdir_index_files_have_no_frontmatter(tmp_path):
    root = _build_bundle(tmp_path)
    for idx in [root / "features" / "index.md",
                root / "features" / "cwow-100" / "index.md",
                root / "shared" / "index.md"]:
        assert idx.exists(), f"missing {idx}"
        assert not idx.read_text().startswith("---"), f"{idx} must have no frontmatter"
    # features/index.md links to each feature subdir
    assert "(cwow-100/)" in (root / "features" / "index.md").read_text()


def test_concepts_are_spec_conformant(tmp_path):
    root = _build_bundle(tmp_path)
    # concept docs live under features/ and shared/; index.md is reserved and
    # nonconforming-report.md is a producer report (not a concept).
    md_files = [
        p for p in root.rglob("*.md")
        if p.name != "index.md" and ("features" in p.parts or "shared" in p.parts)
    ]
    assert md_files
    for p in md_files:
        c = Concept.read(p, root)
        assert c is not None, f"unparseable frontmatter: {p}"
        assert c.fm.get("type"), f"missing required 'type': {p}"       # §9.2
        assert "id" not in c.fm, f"non-spec 'id' frontmatter present: {p}"  # §2
        assert c.fm.get("timestamp"), f"missing timestamp: {p}"


def test_concept_id_derived_from_path(tmp_path):
    root = _build_bundle(tmp_path)
    freq = Concept.read(root / "features" / "cwow-100" / "freq-cwow-100.md", root)
    assert freq.id == "features/cwow-100/freq-cwow-100"             # §2: path minus .md


# ── Bundle round-trip + Devin mapping ────────────────────────────────────────

def test_bundle_loads_and_devin_entries_carry_feature(tmp_path):
    root = _build_bundle(tmp_path)
    bundle = Bundle.load(root)
    entries = devin.build_knowledge_entries(bundle, types=("FREQ", "Requirement"))
    by_cid = {e.concept_id: e for e in entries}

    freq = by_cid["features/cwow-100/freq-cwow-100"]
    assert freq.feature == "cwow-100"
    assert "OKF: features/cwow-100/freq-cwow-100" in freq.trigger_description
    assert "Feature: cwow-100" in freq.trigger_description

    # per-feature folder naming
    assert devin.feature_folder_name(DOMAIN, freq.feature) == "cwow-facility-cwow-100"
    assert devin.feature_folder_name(DOMAIN, "") == "cwow-facility-shared"


def test_dry_run_push_feature_folders(tmp_path):
    root = _build_bundle(tmp_path)
    res = devin.push_bundle(root, types=("FREQ", "Requirement"), dry_run=True,
                            folder_by_feature=True, validate_first=False)
    folders = {e.folder_name for e in res.entries}
    assert "cwow-facility-cwow-100" in folders
    assert "cwow-facility-cwow-200" in folders
    # payload files written with path-safe names
    assert res.out_dir and any(res.out_dir.glob("features__*.json"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider", "-o", "addopts="]))
