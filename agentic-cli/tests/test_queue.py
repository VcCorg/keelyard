"""Whose review queue an escalation lands in — F4.

The rule is "the domain owner". Every test here is a consequence of refusing to
soften it when the answer is inconvenient.

Three carry the design. ``test_an_unowned_domain_is_never_assigned_to_anyone``
is the one the whole module exists to guarantee: the tempting fallbacks all hand
one team's decision to somebody who never agreed to make it.
``test_a_blocked_domain_with_no_escalations_still_reaches_its_owner`` closes the
gap where an owner sees an empty queue and concludes nothing was needed.
``test_one_owner_gets_one_queue`` is the consolidation that makes the answer
useful rather than a column in the plan.
"""
from __future__ import annotations

import pytest

from agentic_cli.onboarding import differ, plan, queue


REF = "repo:svc/CONTRIBUTING.md"
OTHER_REF = "repo:svc/DEPLOY.md"


def _verdict(entry_id: str, status: str = differ.CONTRADICTED) -> differ.Verdict:
    return differ.Verdict(entry_id=entry_id, status=status, checked=True,
                          detail="The source now says the opposite.")


def _outcome(domain: str, *, escalating: int = 0, held: int = 0,
             readable: bool = True, version: str = "v1") -> plan.DomainOutcome:
    outcome = plan.DomainOutcome(domain=domain, readable=readable, held=held,
                                 cited_versions=(version,))
    outcome.verdicts = [_verdict(f"{domain}-{i}") for i in range(escalating)]
    if not readable:
        outcome.detail = "Proposal could not be read — nothing was ruled on."
    return outcome


def _plan(*outcomes, ref: str = REF) -> plan.Plan:
    return plan.Plan(ref=ref, version="v2", outcomes=list(outcomes))


@pytest.fixture
def owners(monkeypatch):
    """Wire ownership lookup to a fixture table, and product contacts to another."""
    table: dict = {}
    contacts: dict = {}

    def fake_owner_of(domain):
        return table.get(domain, ("", queue.UNKNOWN_OWNER))

    monkeypatch.setattr(queue, "owner_of", fake_owner_of)
    monkeypatch.setattr(queue, "_product_contact",
                        lambda domain: contacts.get(domain, ""))
    return table, contacts


class TestRoutingRule:
    def test_an_escalation_goes_to_the_domain_owner(self, owners):
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)

        routing = queue.route(_plan(_outcome("ledger", escalating=2)))

        assert [q.owner for q in routing.queues] == ["ada@example.com"]
        assert len(routing.queues[0].escalations) == 2
        assert routing.complete

    def test_one_owner_gets_one_queue(self, owners):
        """Three domains and two sources are still one person's worklist."""
        table, _ = owners
        for name in ("ledger", "payments", "reporting"):
            table[name] = ("ada@example.com", queue.OWNED)

        routing = queue.route([
            _plan(_outcome("ledger", escalating=1),
                  _outcome("payments", escalating=1)),
            _plan(_outcome("reporting", escalating=2), ref=OTHER_REF),
        ])

        assert len(routing.queues) == 1
        entry = routing.queues[0]
        assert entry.domains == ["ledger", "payments", "reporting"]
        assert entry.refs == sorted([REF, OTHER_REF])
        assert len(entry.items) == 4

    def test_two_owners_are_two_queues(self, owners):
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)
        table["payments"] = ("grace@example.com", queue.OWNED)

        routing = queue.route(_plan(_outcome("ledger", escalating=1),
                                    _outcome("payments", escalating=1)))

        assert [q.owner for q in routing.queues] == ["ada@example.com",
                                                     "grace@example.com"]

    def test_a_settled_domain_queues_nothing(self, owners):
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)

        routing = queue.route(_plan(_outcome("ledger")))

        assert routing.queues == []
        assert routing.complete

    def test_ownership_is_resolved_once_per_domain(self, monkeypatch):
        """Nine escalations are one ownership question, not nine."""
        calls: list[str] = []

        def counting(domain):
            calls.append(domain)
            return ("ada@example.com", queue.OWNED)

        monkeypatch.setattr(queue, "owner_of", counting)
        queue.route(_plan(_outcome("ledger", escalating=9)))

        assert calls == ["ledger"]


class TestUnroutable:
    def test_an_unowned_domain_is_never_assigned_to_anyone(self, owners):
        """No default owner. Not the product owner, not whoever ran this."""
        table, contacts = owners
        table["ledger"] = ("", queue.UNOWNED)
        contacts["ledger"] = "product-lead@example.com"

        routing = queue.route(_plan(_outcome("ledger", escalating=1)))

        assert routing.queues == []
        assert len(routing.unowned) == 1
        assert not routing.complete
        # The product owner is named as somebody to ask...
        assert routing.fallback_contacts == {"ledger": "product-lead@example.com"}
        # ...and has emphatically not been given the work.
        assert routing.for_owner("product-lead@example.com") is None

    def test_unowned_and_unknown_are_kept_apart(self, owners):
        """"records no owner" and "we could not read the config" differ.

        The first is a gap a team closes in a minute; the second may be a
        missing checkout, and telling somebody to set `owner:` would be wrong.
        """
        table, _ = owners
        table["ledger"] = ("", queue.UNOWNED)
        table["payments"] = ("", queue.UNKNOWN_OWNER)

        routing = queue.route(_plan(_outcome("ledger", escalating=1),
                                    _outcome("payments", escalating=1)))

        assert [i.domain for i in routing.unowned] == ["ledger"]
        assert [i.domain for i in routing.unknown] == ["payments"]
        assert routing.unrouted == 2

    def test_nothing_is_dropped(self, owners):
        """Every item is either routed or reported. There is no third path."""
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)
        table["payments"] = ("", queue.UNOWNED)
        table["reporting"] = ("", queue.UNKNOWN_OWNER)

        routing = queue.route(_plan(_outcome("ledger", escalating=2),
                                    _outcome("payments", escalating=1),
                                    _outcome("reporting", escalating=3)))

        assert routing.routed + routing.unrouted == 6


class TestEmptyIsNotExamined:
    def test_a_blocked_domain_with_no_escalations_still_reaches_its_owner(self, owners):
        """An unreadable proposal must not read as "nothing needed"."""
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)

        routing = queue.route(_plan(_outcome("ledger", readable=False)))
        entry = routing.queues[0]

        assert entry.escalations == []
        assert len(entry.unruled) == 1
        assert "could not be read" in entry.unruled[0].detail

    def test_a_held_only_domain_says_why_nothing_was_ruled(self, owners):
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)

        routing = queue.route(_plan(_outcome("ledger", held=3)))
        item = routing.queues[0].unruled[0]

        assert item.reason == queue.UNRULED
        assert "held instruction" in item.detail

    def test_the_approved_version_travels_with_the_item(self, owners):
        """Under version skew a reviewer must see which revision they approved."""
        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)

        routing = queue.route(_plan(_outcome("ledger", escalating=1, version="v1")))

        assert routing.queues[0].items[0].cited_version == "v1"


class TestScopeDiscipline:
    def test_routing_decides_nothing(self, owners, monkeypatch):
        """It says whose decision it is. It does not make it."""
        from agentic_cli.onboarding import proposal

        table, _ = owners
        table["ledger"] = ("ada@example.com", queue.OWNED)

        def refuse(*args, **kwargs):
            raise AssertionError("routing wrote to a proposal")

        monkeypatch.setattr(proposal, "save", refuse)
        monkeypatch.setattr(proposal, "merge", refuse)

        routing = queue.route(_plan(_outcome("ledger", escalating=1)))
        blob = str(routing.to_dict())

        assert routing.queues
        for word in ("severity", "priority", "due", "sla", "approved"):
            assert word not in blob.lower(), f"{word} leaked into routing"


class TestOwnerLookup:
    """The real lookup, unmocked — the three statuses come from real files."""

    def _meta(self, tmp_path, monkeypatch, contents=None):
        meta = tmp_path / "acme-context-meta"
        config = meta / ".platform" / "config"
        config.mkdir(parents=True)
        if contents is not None:
            (config / "domain.yaml").write_text(contents)
        monkeypatch.setattr(
            "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
            lambda domain: meta)
        return meta

    def test_a_recorded_owner_is_found(self, tmp_path, monkeypatch):
        self._meta(tmp_path, monkeypatch,
                   "domain: acme\nproduct: p\nowner: ada@example.com\n")
        assert queue.owner_of("acme") == ("ada@example.com", queue.OWNED)

    def test_a_config_naming_no_owner_is_unowned(self, tmp_path, monkeypatch):
        self._meta(tmp_path, monkeypatch, "domain: acme\nproduct: p\n")
        assert queue.owner_of("acme") == ("", queue.UNOWNED)

    def test_a_blank_owner_is_unowned_not_owned_by_blank(self, tmp_path, monkeypatch):
        self._meta(tmp_path, monkeypatch,
                   'domain: acme\nproduct: p\nowner: "   "\n')
        assert queue.owner_of("acme") == ("", queue.UNOWNED)

    def test_a_missing_config_is_unknown_not_unowned(self, tmp_path, monkeypatch):
        """MetaRepoConfig returns None for both; this must not."""
        self._meta(tmp_path, monkeypatch, contents=None)
        assert queue.owner_of("acme") == ("", queue.UNKNOWN_OWNER)

    def test_an_unparsable_config_is_unknown(self, tmp_path, monkeypatch):
        self._meta(tmp_path, monkeypatch, "owner: [unclosed\n  - broken: :\n")
        assert queue.owner_of("acme")[1] == queue.UNKNOWN_OWNER

    def test_no_meta_repo_is_unknown(self, monkeypatch):
        monkeypatch.setattr(
            "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
            lambda domain: None)
        assert queue.owner_of("acme") == ("", queue.UNKNOWN_OWNER)
