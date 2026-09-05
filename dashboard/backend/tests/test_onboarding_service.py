"""Tests for the onboarding read models the wizard renders.

These exercise the shaping, not the extraction — ``agentic-cli`` owns that and
tests it. What matters here is that the dashboard never becomes a second way to
get held text out, and that drift stays readable when a signal is unavailable.
"""
from __future__ import annotations

import pytest

from agentic_cli.onboarding import extract, proposal, redaction


@pytest.fixture
def domain(tmp_path, monkeypatch):
    """A registered domain with a meta-repo and a proposal on disk."""
    monkeypatch.setenv("HOME", str(tmp_path))

    import importlib
    import agentic_cli.tracker as tracker
    importlib.reload(tracker)

    meta = tmp_path / "work" / "acme-facility" / "acme-facility-context-meta"
    (meta / ".platform" / "config").mkdir(parents=True, exist_ok=True)
    (meta / ".domain").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agent-cli-agentic").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agent-cli-agentic" / "config.json").write_text(
        f'{{"code_workspace": "{tmp_path / "work"}"}}', encoding="utf-8")

    tracker.register_domain("acme-facility", product="ACME", domain="Facility")

    citation = extract.Citation("confluence", "12345", "7")
    review = proposal.merge(proposal.Proposal(domain="acme-facility"), [
        extract.Candidate("Run the bootstrap target", extract.SETUP, citation, 0.7),
        extract.Candidate("Never migrate against prod", extract.HAZARD, citation, 0.8),
        extract.Candidate("Ask a person", extract.OWNERSHIP, citation, 0.4,
                          risks=(redaction.Risk(redaction.PERSON),)),
    ], "acme-facility")
    proposal.save(meta, review)

    import importlib as il
    from src.services import onboarding_service
    il.reload(onboarding_service)
    return "acme-facility", meta, onboarding_service


class TestProposalReadModel:
    def test_held_entries_expose_risks_but_no_text(self, domain):
        slug, _, svc = domain
        held = [e for e in svc.get_proposal(slug).entries if e.held]
        assert held
        assert held[0].text == ""
        assert held[0].risks == ["person"]

    def test_counts_reported(self, domain):
        slug, _, svc = domain
        assert svc.get_proposal(slug).counts[proposal.UNREVIEWED] == 3


class TestVerdicts:
    def test_accept_persists(self, domain):
        slug, meta, svc = domain
        entry = next(e for e in svc.get_proposal(slug).entries if not e.held)
        result = svc.record_verdicts(slug, svc.VerdictRequest(accept=[entry.id]))
        assert result.changed == 1
        assert proposal.load(meta, slug).accepted

    def test_a_held_entry_cannot_be_accepted_through_the_api(self, domain):
        """The dashboard must not become a second way to approve held text."""
        slug, meta, svc = domain
        held = next(e for e in svc.get_proposal(slug).entries if e.held)
        assert svc.record_verdicts(slug, svc.VerdictRequest(accept=[held.id])).changed == 0
        assert not proposal.load(meta, slug).accepted

    def test_unknown_id_is_ignored(self, domain):
        slug, _, svc = domain
        assert svc.record_verdicts(slug, svc.VerdictRequest(accept=["nope"])).changed == 0


class TestDrift:
    def test_every_signal_has_a_severity(self, domain):
        slug, _, svc = domain
        signals = svc.get_drift(slug)
        assert signals
        assert {s.severity for s in signals} <= {"ok", "warn", "fail"}

    def test_pending_instructions_surface_as_drift(self, domain):
        slug, _, svc = domain
        instructions = next(s for s in svc.get_drift(slug) if s.key == "instructions")
        assert instructions.count == 3

    def test_template_signal_degrades_rather_than_raising(self, domain):
        """A meta-repo with no baseline must not break the drift page."""
        slug, _, svc = domain
        template = next(s for s in svc.get_drift(slug) if s.key == "template")
        assert template.severity in ("ok", "warn", "fail")


class TestKnowledgeMap:
    def test_only_accepted_instructions_become_flows(self, domain):
        """An unreviewed instruction is not yet knowledge."""
        slug, _, svc = domain
        assert svc.get_knowledge_map(slug).flows == []

        entry = next(e for e in svc.get_proposal(slug).entries if not e.held)
        svc.record_verdicts(slug, svc.VerdictRequest(accept=[entry.id]))
        assert svc.get_knowledge_map(slug).flows

    def test_held_instructions_are_counted_but_never_labelled_with_text(self, domain):
        slug, _, svc = domain
        graph = svc.get_knowledge_map(slug)
        assert graph.totals["held"] == 1
        assert all("Ask a person" not in node.label for node in graph.nodes)

    def test_source_staleness_propagates_to_its_flows(self, domain, monkeypatch):
        """A source that moved upstream taints what was built from it."""
        slug, _, svc = domain
        import agentic_cli.tracker as tracker
        tracker.add_domain_doc(slug, "12345", title="Onboarding", source_version=7)
        tracker.set_domain_doc_live_version(slug, "12345", 9)

        entry = next(e for e in svc.get_proposal(slug).entries if not e.held)
        svc.record_verdicts(slug, svc.VerdictRequest(accept=[entry.id]))

        graph = svc.get_knowledge_map(slug)
        assert any(f.stale for f in graph.flows)
        assert any(n.stale for n in graph.nodes if n.group == "source")


class TestPortfolio:
    """The cross-domain readout: which of mine needs attention this morning."""

    def test_a_domain_without_a_meta_repo_is_listed_not_skipped(self, domain):
        """'Not set up yet' and 'set up and scoring badly' are different
        problems, and omitting the first is the more misleading choice."""
        slug, _, svc = domain
        import agentic_cli.tracker as tracker
        tracker.register_domain("acme-payments", product="ACME", domain="Payments")

        rows = svc.get_portfolio()
        by_domain = {r.domain: r for r in rows}
        assert set(by_domain) == {slug, "acme-payments"}
        assert by_domain["acme-payments"].overall is None
        assert by_domain["acme-payments"].note == "no meta-repo"
        assert not by_domain["acme-payments"].ready

    def test_worst_first(self, domain):
        """An unscorable domain sorts to the top — it is the most actionable row."""
        slug, _, svc = domain
        import agentic_cli.tracker as tracker
        tracker.register_domain("acme-payments", product="ACME", domain="Payments")

        assert svc.get_portfolio()[0].domain == "acme-payments"

    def test_scored_domain_reports_its_weakest_dimensions(self, domain):
        slug, _, svc = domain
        [row] = [r for r in svc.get_portfolio() if r.domain == slug]
        assert row.overall is not None
        assert row.grade
        assert row.note  # names the two lowest-scoring dimensions

    def test_product_filter(self, domain):
        slug, _, svc = domain
        import agentic_cli.tracker as tracker
        tracker.register_domain("other-thing", product="OTHER", domain="Thing")

        assert [r.domain for r in svc.get_portfolio(product="ACME")] == [slug]
        assert svc.get_portfolio(product="NOPE") == []
