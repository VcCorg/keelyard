"""Tests for product meta-repo semantic validation."""

from pathlib import Path

import yaml

from agentic_cli.meta_repo.product_validation import (
    validate_product_meta,
    FAIL,
    WARN,
    OK,
)


def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            yaml.dump(data, f, sort_keys=False)


def _scaffold(meta: Path, *, gov=None, crosswalk=None, personas=None, product=None) -> None:
    cfg = meta / ".platform" / "config"
    (meta / "exceptions").mkdir(parents=True, exist_ok=True)
    _write(cfg / "product.yaml", product or {"product": "TEST", "org_methodology_url": "https://x/y.git"})
    default_gov = {
        "promotion_path": ["dev", "qa", "uat", "prd"],
        "checkpoint_gate_map": [
            {"checkpoint": "spec-approved", "gate": "dev", "blocking": True},
        ],
        "min_reviewers": 1,
        "test_coverage_min": 80.0,
        "require_code_review": True,
    }
    gov = gov if gov is not None else default_gov
    _write(cfg / "governance.yaml", gov)
    _write(cfg / "crosswalk.yaml", crosswalk if crosswalk is not None else {
        "promotion_path": gov.get("promotion_path"),
        "checkpoint_gate_map": gov.get("checkpoint_gate_map"),
    })
    _write(cfg / "personas.yaml", personas if personas is not None else {
        "version": 1, "defaults_enabled": ["domain", "dev", "qa", "sm", "ba"], "personas": [],
    })


def _status(report, name):
    for c in report.checks:
        if c.name == name:
            return c.status
    return None


def test_valid_product_passes(tmp_path: Path):
    meta = tmp_path / "product-test-meta"
    _scaffold(meta)
    report = validate_product_meta(meta)
    assert not report.failed
    assert _status(report, "checkpoint_gate_map gates ⊆ promotion_path") == OK
    assert _status(report, "crosswalk ↔ governance consistency") == OK


def test_missing_meta_repo_fails(tmp_path: Path):
    report = validate_product_meta(tmp_path / "does-not-exist")
    assert report.failed


def test_gate_not_in_promotion_path_fails(tmp_path: Path):
    meta = tmp_path / "product-test-meta"
    _scaffold(meta, gov={
        "promotion_path": ["dev", "qa"],
        "checkpoint_gate_map": [{"checkpoint": "x", "gate": "prd", "blocking": True}],
        "min_reviewers": 1, "test_coverage_min": 80.0, "require_code_review": True,
    })
    report = validate_product_meta(meta)
    assert report.failed
    assert _status(report, "checkpoint_gate_map gates ⊆ promotion_path") == FAIL


def test_crosswalk_drift_warns(tmp_path: Path):
    meta = tmp_path / "product-test-meta"
    _scaffold(meta, crosswalk={
        "promotion_path": ["dev", "qa", "uat"],  # differs from governance
        "checkpoint_gate_map": [],
    })
    report = validate_product_meta(meta)
    assert _status(report, "crosswalk ↔ governance consistency") == WARN


def test_unknown_builtin_persona_fails(tmp_path: Path):
    meta = tmp_path / "product-test-meta"
    _scaffold(meta, personas={
        "version": 1, "defaults_enabled": ["dev", "wizard"], "personas": [],
    })
    report = validate_product_meta(meta)
    assert report.failed
    assert _status(report, "personas.defaults_enabled ⊆ built-ins") == FAIL


def test_bad_persona_id_fails(tmp_path: Path):
    meta = tmp_path / "product-test-meta"
    _scaffold(meta, personas={
        "version": 1, "defaults_enabled": ["dev"],
        "personas": [{"id": "Tech Lead", "label": "Tech Lead"}],
    })
    report = validate_product_meta(meta)
    assert report.failed
    assert _status(report, "personas[].id kebab-case") == FAIL


def test_coverage_out_of_range_fails(tmp_path: Path):
    meta = tmp_path / "product-test-meta"
    _scaffold(meta, gov={
        "promotion_path": ["dev", "qa", "uat", "prd"],
        "checkpoint_gate_map": [{"checkpoint": "spec-approved", "gate": "dev", "blocking": True}],
        "min_reviewers": 1, "test_coverage_min": 150.0, "require_code_review": True,
    })
    report = validate_product_meta(meta)
    assert report.failed
