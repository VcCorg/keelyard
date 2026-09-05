"""Governance across a product's domains: compare, then promote.

The rule the product meta-repo already declares — tighten freely, loosen only
with a recorded exception — had never been reported on or enforced across a
fleet. These tests pin the two halves of doing that: a classifier that refuses
to invent an ordering it does not have, and a promotion that refuses at plan
time rather than warning after the write.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentic_cli.meta_repo import governance_fleet as fleet
from agentic_cli.meta_repo import governance_promote as promote


def _meta(root: Path, name: str, governance: dict) -> Path:
    meta = root / name
    config = meta / ".platform" / "config"
    config.mkdir(parents=True, exist_ok=True)
    (config / "governance.yaml").write_text(
        yaml.safe_dump(governance, sort_keys=False), encoding="utf-8")
    return meta


class TestCompareField:
    @pytest.mark.parametrize("name,domain,floor,expected", [
        ("min_reviewers", 2, 1, fleet.STRICTER),
        ("min_reviewers", 1, 2, fleet.LOOSER),
        ("min_reviewers", 2, 2, fleet.SAME),
        ("test_coverage_min", 90.0, 80.0, fleet.STRICTER),
        ("test_coverage_min", 70.0, 80.0, fleet.LOOSER),
        ("require_tests", True, False, fleet.STRICTER),
        ("require_tests", False, True, fleet.LOOSER),
        ("build_governance", "enforce", "warn", fleet.STRICTER),
        ("build_governance", "off", "warn", fleet.LOOSER),
    ])
    def test_orderable_fields(self, name, domain, floor, expected):
        assert fleet.compare_field(name, domain, floor) == expected

    def test_unorderable_field_differs_rather_than_guessing(self):
        """Calling a different regex 'looser' would be a fabrication."""
        assert fleet.compare_field(
            "branch_pattern", "^feat/.*$", "^(feat|fix)/.*$") == fleet.DIFFERS

    def test_unset_domain_value_inherits_the_floor(self):
        assert fleet.compare_field("min_reviewers", None, 2) == fleet.UNSET

    def test_no_floor_means_nothing_to_be_looser_than(self):
        assert fleet.compare_field("min_reviewers", 1, None) == fleet.UNSET

    def test_uncomparable_types_do_not_crash(self):
        assert fleet.compare_field("min_reviewers", "abc", 2) == fleet.DIFFERS


class TestCompareDomain:
    def test_agreement_is_not_listed(self, tmp_path):
        """Listing every matching field would drown the exceptions."""
        floor = {"min_reviewers": 2, "test_coverage_min": 80.0}
        meta = _meta(tmp_path, "d-meta", dict(floor))
        result = fleet.compare_domain("d", meta, floor, [])
        assert result.verdicts == []
        assert result.status == "ok"

    def test_looser_without_exception_is_a_violation(self, tmp_path):
        meta = _meta(tmp_path, "d-meta", {"min_reviewers": 1})
        result = fleet.compare_domain("d", meta, {"min_reviewers": 2}, [])
        assert result.status == "violation"
        assert result.violations[0].field == "min_reviewers"

    def test_a_recorded_exception_waives_the_violation(self, tmp_path):
        from agentic_cli.meta_repo.config import ExceptionEntry

        meta = _meta(tmp_path, "d-meta", {"min_reviewers": 1})
        waiver = ExceptionEntry(id="EX-0001", rule="min_reviewers", reason="pilot",
                                scope="domain:d", owner="lead", status="active")
        result = fleet.compare_domain("d", meta, {"min_reviewers": 2}, [waiver])
        assert result.status == "waived"
        assert not result.violations
        assert result.waived[0].exception_id == "EX-0001"

    def test_an_exception_for_another_domain_does_not_apply(self, tmp_path):
        from agentic_cli.meta_repo.config import ExceptionEntry

        meta = _meta(tmp_path, "d-meta", {"min_reviewers": 1})
        waiver = ExceptionEntry(id="EX-1", rule="min_reviewers", reason="r",
                                scope="domain:other", owner="lead", status="active")
        assert fleet.compare_domain("d", meta, {"min_reviewers": 2}, [waiver]).violations

    def test_an_exception_for_another_rule_does_not_apply(self, tmp_path):
        from agentic_cli.meta_repo.config import ExceptionEntry

        meta = _meta(tmp_path, "d-meta", {"min_reviewers": 1})
        waiver = ExceptionEntry(id="EX-1", rule="test_coverage_min", reason="r",
                                scope="domain:d", owner="lead", status="active")
        assert fleet.compare_domain("d", meta, {"min_reviewers": 2}, [waiver]).violations

    def test_stricter_is_always_allowed(self, tmp_path):
        meta = _meta(tmp_path, "d-meta", {"min_reviewers": 3})
        result = fleet.compare_domain("d", meta, {"min_reviewers": 2}, [])
        assert result.status == "ok"
        assert result.stricter[0].verdict == fleet.STRICTER

    def test_missing_meta_repo(self):
        result = fleet.compare_domain("d", None, {"min_reviewers": 2}, [])
        assert result.status == "missing"
        assert not result.found


class TestPromotion:
    def test_parse_assignment(self):
        assert promote.parse_assignment("test_coverage_min=85") == ("test_coverage_min", 85.0)
        assert promote.parse_assignment("min_reviewers=2") == ("min_reviewers", 2)
        assert promote.parse_assignment("require_tests=true") == ("require_tests", True)

    def test_unknown_key_is_rejected(self):
        with pytest.raises(ValueError, match="not a promotable value"):
            promote.parse_assignment("banana=3")

    def test_malformed_assignment_is_rejected(self):
        with pytest.raises(ValueError, match="Expected"):
            promote.parse_assignment("test_coverage_min")

    def test_plan_reports_the_blast_radius(self, tmp_path, monkeypatch):
        product_meta = _meta(tmp_path, "p-meta", {"test_coverage_min": 80.0})
        metas = {
            "a": _meta(tmp_path, "a-meta", {"test_coverage_min": 70.0}),
            "b": _meta(tmp_path, "b-meta", {"test_coverage_min": 90.0}),
        }
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: metas.get(slug))

        p = promote.plan("P", ["a", "b"], "test_coverage_min", 85.0,
                         product_meta=product_meta)
        by_domain = {c.domain: c for c in p.changes}
        assert by_domain["a"].current == 70.0
        assert by_domain["b"].current == 90.0
        assert all(c.effect == fleet.STRICTER for c in p.changes)
        assert len(p.applicable) == 2

    def test_a_value_below_the_floor_is_refused_at_plan_time(self, tmp_path, monkeypatch):
        """Refusing before the write is the difference between a guard and a comment."""
        product_meta = _meta(tmp_path, "p-meta", {"test_coverage_min": 80.0})
        meta = _meta(tmp_path, "a-meta", {"test_coverage_min": 80.0})
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: meta)

        p = promote.plan("P", ["a"], "test_coverage_min", 60.0, product_meta=product_meta)
        assert p.blocked
        with pytest.raises(promote.PromotionRefused, match="looser than the product floor"):
            promote.apply(p)

        # Nothing was written.
        current = fleet.load_governance(meta)["test_coverage_min"]
        assert current == 80.0

    def test_force_does_not_bypass_the_floor(self, tmp_path, monkeypatch):
        product_meta = _meta(tmp_path, "p-meta", {"min_reviewers": 2})
        meta = _meta(tmp_path, "a-meta", {"min_reviewers": 2})
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: meta)

        p = promote.plan("P", ["a"], "min_reviewers", 1, product_meta=product_meta)
        promote.apply(p, force=True)
        # force only proceeds past blocked entries; it never writes one.
        assert fleet.load_governance(meta)["min_reviewers"] == 2

    def test_apply_writes_and_preserves_other_keys(self, tmp_path, monkeypatch):
        product_meta = _meta(tmp_path, "p-meta", {"test_coverage_min": 80.0})
        meta = _meta(tmp_path, "a-meta",
                     {"test_coverage_min": 80.0, "branch_pattern": "^feat/.*$"})
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: meta)

        p = promote.plan("P", ["a"], "test_coverage_min", 90.0, product_meta=product_meta)
        assert len(promote.apply(p)) == 1

        written = fleet.load_governance(meta)
        assert written["test_coverage_min"] == 90.0
        assert written["branch_pattern"] == "^feat/.*$"

    def test_a_domain_already_at_the_value_is_a_noop(self, tmp_path, monkeypatch):
        product_meta = _meta(tmp_path, "p-meta", {"min_reviewers": 1})
        meta = _meta(tmp_path, "a-meta", {"min_reviewers": 2})
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: meta)

        p = promote.plan("P", ["a"], "min_reviewers", 2, product_meta=product_meta)
        assert p.changes[0].is_noop
        assert not p.applicable

    def test_a_missing_meta_repo_is_reported_not_skipped(self, tmp_path, monkeypatch):
        product_meta = _meta(tmp_path, "p-meta", {"min_reviewers": 1})
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: None)

        p = promote.plan("P", ["gone"], "min_reviewers", 2, product_meta=product_meta)
        assert p.changes[0].writable is False
        assert "No meta-repo" in p.changes[0].note

    def test_a_change_clearing_the_floor_can_still_relax_a_domain(self, tmp_path, monkeypatch):
        """'Raise coverage to 85 everywhere' must not quietly relax the 90s."""
        product_meta = _meta(tmp_path, "p-meta", {"test_coverage_min": 80.0})
        metas = {
            "strict": _meta(tmp_path, "s-meta", {"test_coverage_min": 95.0}),
            "lax": _meta(tmp_path, "l-meta", {"test_coverage_min": 70.0}),
        }
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: metas.get(slug))

        p = promote.plan("P", ["strict", "lax"], "test_coverage_min", 85.0,
                         product_meta=product_meta)
        by_domain = {c.domain: c for c in p.changes}

        # Both clear the floor, so neither is blocked...
        assert not p.blocked
        assert all(c.effect == fleet.STRICTER for c in p.changes)
        # ...but only one of them is a step down for the domain itself.
        assert by_domain["strict"].relaxes_domain
        assert not by_domain["lax"].relaxes_domain
        assert [c.domain for c in p.relaxing] == ["strict"]

    def test_relaxation_does_not_block_the_write(self, tmp_path, monkeypatch):
        """It is allowed — it clears the floor — just never silent."""
        product_meta = _meta(tmp_path, "p-meta", {"test_coverage_min": 80.0})
        meta = _meta(tmp_path, "s-meta", {"test_coverage_min": 95.0})
        monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                            lambda slug, search_paths=None: meta)

        p = promote.plan("P", ["s"], "test_coverage_min", 85.0, product_meta=product_meta)
        assert len(promote.apply(p)) == 1
        assert fleet.load_governance(meta)["test_coverage_min"] == 85.0
