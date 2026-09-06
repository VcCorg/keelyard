"""Tests for the source → domains reverse index.

The load-bearing test is ``test_an_unreadable_domain_is_not_counted_as_absent``.
Under-reporting a blast radius is the direction that gets someone hurt: a domain
we could not read might well cite the file being changed, and counting it as a
non-user makes the edit look safer than it is.
"""
from __future__ import annotations

import pytest

from agentic_cli.onboarding import extract, fanout, proposal


def _meta(tmp_path, slug):
    meta = tmp_path / f"{slug}-context-meta"
    (meta / ".platform" / "config").mkdir(parents=True, exist_ok=True)
    return meta


def _domain(tmp_path, slug, cites, status=proposal.ACCEPTED):
    """Write a proposal citing (ref, version, count) triples."""
    entries = []
    for i, (ref, version, count) in enumerate(cites):
        scheme, path = ref.split(":", 1)
        for j in range(count):
            candidate = extract.Candidate(
                text=f"Instruction {i}{j} for {slug}", kind=extract.SETUP,
                citation=extract.Citation(scheme, path, version))
            entries.append(proposal.Entry.from_candidate(candidate, status))
    meta = _meta(tmp_path, slug)
    proposal.save(meta, proposal.Proposal(domain=slug, entries=entries))
    return meta


@pytest.fixture
def fleet(tmp_path, monkeypatch):
    """Three domains; two share a source at one version, one lags behind."""
    import agentic_cli.meta_repo.detector as detector
    from agentic_cli import tracker

    _domain(tmp_path, "payments", [("repo:platform/CONTRIBUTING.md", "9f2c1a", 4),
                                   ("repo:payments/README.md", "aa11bb", 3)])
    _domain(tmp_path, "ledger", [("repo:platform/CONTRIBUTING.md", "9f2c1a", 2)])
    _domain(tmp_path, "reporting", [("repo:platform/CONTRIBUTING.md", "3d0e77", 3)])

    monkeypatch.setattr(
        detector, "detect_domain_meta_repo",
        lambda slug, search_paths=None: (
            tmp_path / f"{slug}-context-meta"
            if (tmp_path / f"{slug}-context-meta").is_dir() else None))
    monkeypatch.setattr(
        tracker, "get_domains",
        lambda product=None: [{"name": s, "product": "acme"}
                              for s in ("payments", "ledger", "reporting")])
    return tmp_path


class TestIndex:
    def test_a_shared_source_names_every_domain_drawing_on_it(self, fleet):
        found = fanout.for_source("repo:platform/CONTRIBUTING.md")
        assert found.domains == ["ledger", "payments", "reporting"]
        assert found.shared
        assert found.accepted == 9

    def test_a_single_domain_source_is_not_shared(self, fleet):
        found = fanout.for_source("repo:payments/README.md")
        assert found.domains == ["payments"]
        assert not found.shared

    def test_shared_sorts_by_blast_radius(self, fleet):
        index = fanout.build()
        assert [s.ref for s in index.shared] == ["repo:platform/CONTRIBUTING.md"]

    def test_an_uncited_source_is_absent_rather_than_empty(self, fleet):
        assert fanout.for_source("repo:nobody/uses-this.md") is None

    def test_affected_by_answers_for_a_whole_commit(self, fleet):
        """A commit changes several files; the union is what a reviewer wants."""
        found = fanout.affected_by(["repo:platform/CONTRIBUTING.md",
                                    "repo:payments/README.md",
                                    "repo:untouched/file.md"])
        assert found["repo:platform/CONTRIBUTING.md"] == \
            ["ledger", "payments", "reporting"]
        assert found["repo:payments/README.md"] == ["payments"]
        assert found["repo:untouched/file.md"] == []


class TestVersionSkew:
    def test_domains_citing_different_versions_are_flagged(self, fleet):
        """One extracted before a change the other absorbed."""
        found = fanout.for_source("repo:platform/CONTRIBUTING.md")
        assert found.version_skew
        assert set(found.cited_versions) == {"9f2c1a", "3d0e77"}

    def test_agreement_is_not_skew(self, fleet):
        assert not fanout.for_source("repo:payments/README.md").version_skew


class TestUnknownIsNotAbsent:
    def test_an_unreadable_domain_is_not_counted_as_absent(self, fleet,
                                                           monkeypatch):
        """Under-reporting a blast radius is the dangerous direction."""
        from agentic_cli.onboarding import proposal as prop

        real_load = prop.load

        def explode(meta, domain=""):
            if "ledger" in str(meta):
                raise OSError("meta-repo is not checked out")
            return real_load(meta, domain)

        monkeypatch.setattr(prop, "load", explode)
        index = fanout.build()

        assert index.unreadable == ["ledger"]
        assert not index.complete
        # And it is genuinely left out of the counts rather than silently zeroed.
        assert index.by_ref("repo:platform/CONTRIBUTING.md").domains == \
            ["payments", "reporting"]

    def test_no_meta_repo_is_a_real_answer_not_an_unknown(self, fleet, monkeypatch):
        """A domain with nothing set up cites nothing — that we do know."""
        from agentic_cli import tracker

        monkeypatch.setattr(
            tracker, "get_domains",
            lambda product=None: [{"name": s} for s in
                                  ("payments", "ledger", "reporting", "unstarted")])
        index = fanout.build()
        assert index.complete            # not an unknown
        assert "unstarted" not in index.by_ref("repo:platform/CONTRIBUTING.md").domains


class TestPendingAndHeld:
    def test_pending_entries_are_counted_separately(self, tmp_path, monkeypatch):
        import agentic_cli.meta_repo.detector as detector
        from agentic_cli import tracker

        _domain(tmp_path, "solo", [("repo:x/A.md", "v1", 2)],
                status=proposal.UNREVIEWED)
        monkeypatch.setattr(detector, "detect_domain_meta_repo",
                            lambda slug, search_paths=None: tmp_path / "solo-context-meta")
        monkeypatch.setattr(tracker, "get_domains",
                            lambda product=None: [{"name": "solo"}])
        found = fanout.for_source("repo:x/A.md")
        assert found.pending == 2
        assert found.accepted == 0
        # Still a tie to the source: an un-reviewed instruction is still a reason
        # this domain cares about the file changing.
        assert found.domains == ["solo"]
