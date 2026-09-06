"""Floor arithmetic — G3, the composition G1 and G2 deliberately refused.

The rule the whole phase turns on is ``test_unruled_is_never_a_pass``. Every
layer underneath kept "we could not ask" apart from "there is nothing there"
specifically so this one would not have to invent the difference, and a
governance check that certifies what it never examined is worse than no check.

``test_a_domain_cannot_pass_by_loosening_its_own_floor`` is the other: judging a
session against a policy its owner had no authority to set makes the check
editable by the thing being checked.
"""
from __future__ import annotations

import pytest
import yaml

from agentic_cli import guard_findings, guard_floor


def _finding(code: str, component: str = "jira") -> guard_findings.Finding:
    return guard_findings.Finding(component=component, kind="mcp", code=code,
                                  statement=f"{code} on {component}")


def _findings(*codes, unruled=()) -> guard_findings.Findings:
    return guard_findings.Findings(
        findings=[_finding(c) for c in codes], unruled=list(unruled))


@pytest.fixture
def repos(tmp_path):
    """A product meta-repo and a domain one, both writable per test."""
    def write(root: str, governance: dict) -> object:
        path = tmp_path / root
        config = path / ".platform" / "config"
        config.mkdir(parents=True, exist_ok=True)
        (config / "governance.yaml").write_text(yaml.safe_dump(governance))
        return path

    return write


def _exception(product, **fields):
    ledger = product / "exceptions"
    ledger.mkdir(parents=True, exist_ok=True)
    entry = {"id": "EX-1", "rule": "forbid_external_egress", "reason": "vendor "
             "under contract", "scope": "domain:acme", "owner": "ada@example.com",
             "status": "active", "expires_at": ""}
    entry.update(fields)
    (ledger / f"{entry['id']}.yaml").write_text(yaml.safe_dump(entry))
    return entry


class TestTheHonestyRule:
    def test_unruled_is_never_a_pass(self, repos):
        """A section G2 could not enumerate makes the session undetermined."""
        product = repos("product", {"forbid_external_egress": False})
        domain = repos("acme", {})

        judgement = guard_floor.compose(
            _findings("egress-local", unruled=["mcp servers (not enumerated)"]),
            "acme", product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.UNDETERMINED
        assert judgement.violations == []

    def test_an_unestablished_egress_is_undetermined_not_allowed(self, repos):
        product = repos("product", {"forbid_external_egress": False})
        domain = repos("acme", {})

        judgement = guard_floor.compose(_findings("egress-unknown"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.UNDETERMINED
        assert [r.outcome for r in judgement.rulings] == [guard_floor.INDETERMINATE]

    def test_no_floor_is_undetermined_not_a_pass(self, tmp_path, repos):
        domain = repos("acme", {})
        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=tmp_path / "absent",
                                        domain_meta=domain)

        assert not judgement.floor_found
        assert judgement.verdict == guard_floor.UNDETERMINED
        assert "nothing to judge against" in judgement.detail

    def test_a_definite_violation_outranks_an_unknown(self, repos):
        """Already failing; more uncertainty does not change what to do."""
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {})

        judgement = guard_floor.compose(
            _findings("egress-external", unruled=["skills (not enumerated)"]),
            "acme", product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL


class TestFloorArithmetic:
    def test_a_permitted_finding_passes(self, repos):
        product = repos("product", {"forbid_external_egress": False})
        domain = repos("acme", {})

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.PASS
        assert [r.outcome for r in judgement.rulings] == [guard_floor.ALLOWED]

    def test_a_forbidden_finding_fails(self, repos):
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {})

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL
        assert judgement.violations[0].rule == "forbid_external_egress"

    def test_a_domain_may_tighten_freely(self, repos):
        """The product permits egress; this domain does not. No waiver needed."""
        product = repos("product", {"forbid_external_egress": False})
        domain = repos("acme", {"forbid_external_egress": True})

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL
        assert judgement.violations[0].in_force is True
        assert not judgement.violations[0].disregarded_domain_value

    def test_a_domain_cannot_pass_by_loosening_its_own_floor(self, repos):
        """Otherwise the check is editable by the thing being checked."""
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {"forbid_external_egress": False})

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL
        ruling = judgement.violations[0]
        assert ruling.in_force is True              # the floor's value applied
        assert ruling.disregarded_domain_value

    def test_a_recorded_exception_permits_the_loosening(self, repos):
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {"forbid_external_egress": False})
        _exception(product)

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.PASS
        waived = judgement.waived
        assert len(waived) == 1
        # Permission from a waiver is not the same fact as permission from
        # policy — an audit that cannot tell them apart cannot review waivers.
        assert waived[0].outcome == guard_floor.WAIVED
        assert waived[0].exception_id == "EX-1"

    def test_an_expired_exception_permits_nothing(self, repos):
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {"forbid_external_egress": False})
        _exception(product, expires_at="2020-01-01")

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL
        assert judgement.violations[0].disregarded_domain_value

    def test_a_revoked_exception_permits_nothing(self, repos):
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {"forbid_external_egress": False})
        _exception(product, status="revoked")

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL

    def test_an_exception_for_another_domain_does_not_apply(self, repos):
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {"forbid_external_egress": False})
        _exception(product, scope="domain:other")

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL

    def test_an_exception_for_another_rule_does_not_apply(self, repos):
        product = repos("product", {"forbid_external_egress": True})
        domain = repos("acme", {"forbid_external_egress": False})
        _exception(product, rule="forbid_shared_credentials")

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL


class TestSilence:
    def test_a_floor_that_says_nothing_neither_passes_nor_blocks(self, repos):
        """A gap in their policy, not a gap in our knowledge."""
        product = repos("product", {"require_tests": True})   # says nothing here
        domain = repos("acme", {})

        judgement = guard_floor.compose(_findings("egress-external"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.PASS
        assert len(judgement.ungoverned) == 1
        assert judgement.violations == []

    def test_a_finding_with_no_rule_is_never_a_violation(self, repos):
        """`credential-idle` is hygiene; no floor rule addresses it."""
        product = repos("product", {"forbid_external_egress": True,
                                    "forbid_shared_credentials": True})
        domain = repos("acme", {})

        judgement = guard_floor.compose(_findings("credential-idle",
                                                  "egress-local"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.PASS
        assert len(judgement.ungoverned) == 2

    def test_an_unreadable_floor_and_a_silent_one_read_differently(self, tmp_path,
                                                                   repos):
        silent = repos("product", {"require_tests": True})
        domain = repos("acme", {})

        said_nothing = guard_floor.compose(_findings("egress-external"), "acme",
                                           product_meta=silent, domain_meta=domain)
        unreadable = guard_floor.compose(_findings("egress-external"), "acme",
                                         product_meta=tmp_path / "absent",
                                         domain_meta=domain)

        assert said_nothing.verdict == guard_floor.PASS
        assert unreadable.verdict == guard_floor.UNDETERMINED
        assert "No floor could be read" in unreadable.rulings[0].detail


class TestSharedCredentials:
    def test_the_second_rule_is_wired_the_same_way(self, repos):
        product = repos("product", {"forbid_shared_credentials": True})
        domain = repos("acme", {})

        judgement = guard_floor.compose(_findings("credential-shared"), "acme",
                                        product_meta=product, domain_meta=domain)

        assert judgement.verdict == guard_floor.FAIL
        assert judgement.violations[0].rule == "forbid_shared_credentials"
