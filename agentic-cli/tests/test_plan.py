"""The fan-out plan — F2.

The plan's whole value is that a reviewer can trust its three outcomes, so most
of these pin the boundaries rather than the happy path: an unreadable source
produces no plan rather than an empty one, a held instruction is not silently a
clean run, and nothing is written.

The load-bearing test is ``test_one_extraction_serves_every_domain``. The plan
fetches and extracts once for N domains, which is only sound because a
candidate's id excludes its citation version. If that ever changes, this catches
it — otherwise the plan would quietly report every instruction in a
version-lagging domain as changed.
"""
from __future__ import annotations

import pytest

from agentic_cli import retrieval
from agentic_cli.onboarding import differ, extract, fanout, plan, proposal


SOURCE = "repo:svc/CONTRIBUTING.md"

# The extractor reads instructional prose under a heading, so fixtures use the
# shape a real onboarding doc has rather than bare sentences.
TEXT = "# Setup\n\n- Run the bootstrap target before building\n"
REWORDED = "# Setup\n\n- Run the bootstrap target prior to building\n"
REPLACED = "# Setup\n\n- Install the toolchain from the vendor bundle\n"


def _entries(text: str, version: str = "v1",
             status: str = proposal.ACCEPTED) -> list[proposal.Entry]:
    """Approved entries as a real extraction would have produced them.

    Built by extracting rather than by hand: entry ids come from kind + source +
    text, so a handmade entry silently fails to match the candidate for the very
    same instruction and every test reads "absent".
    """
    from agentic_cli.onboarding import classify

    citation = extract.Citation("repo", "svc/CONTRIBUTING.md", version)
    result = extract.extract(text, citation, classify.ONBOARDING)
    assert result.candidates, "fixture text produced no candidates"
    return [proposal.Entry.from_candidate(c, status=status)
            for c in result.candidates]


@pytest.fixture
def wired(monkeypatch, tmp_path):
    """Wire the plan's four collaborators to fixtures, and record every call."""
    calls = {"fetch": [], "extract": 0}

    state: dict = {"domains": {}, "index": None, "fetched": None}

    def fake_build(product="", domains=None):
        return state["index"]

    def fake_fetch(ref, **kwargs):
        calls["fetch"].append(ref)
        return state["fetched"]

    real_extract = extract.extract

    def counting_extract(text, citation, doc_type):
        calls["extract"] += 1
        return real_extract(text, citation, doc_type)

    monkeypatch.setattr(fanout, "build", fake_build)
    monkeypatch.setattr(retrieval, "fetch", fake_fetch)
    monkeypatch.setattr(extract, "extract", counting_extract)
    monkeypatch.setattr(
        "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
        lambda name: tmp_path / name if name in state["domains"] else None)
    monkeypatch.setattr(
        proposal, "load",
        lambda meta, domain="": state["domains"].get(domain)
        or proposal.Proposal(domain=domain))
    return state, calls


def _index(*domains: str, versions: tuple[str, ...] = ("v1",)) -> fanout.Index:
    index = fanout.Index()
    out = fanout.SourceFanout(ref=SOURCE, scheme="repo")
    for name in domains:
        out.uses.append(fanout.SourceUse(domain=name, ref=SOURCE, scheme="repo",
                                         accepted=1, versions=versions))
    index.sources[SOURCE] = out
    return index


def _resolved(text: str = TEXT, version: str = "v2") -> retrieval.Fetched:
    return retrieval.Fetched(ref=SOURCE, scheme="repo", status=retrieval.RESOLVED,
                             text=text, version=version)


class TestPlanBoundaries:
    def test_an_unreadable_source_produces_no_plan_not_an_empty_one(self, wired):
        """An empty plan says "affects nobody" — the wrong thing to tell a pusher."""
        state, _ = wired
        state["index"] = _index("ledger")
        state["fetched"] = retrieval.Fetched(ref=SOURCE, scheme="repo",
                                             status=retrieval.UNAVAILABLE,
                                             detail="no checkout")

        result = plan.build(SOURCE)

        assert result.status == plan.UNREADABLE
        assert not result.planned
        assert result.outcomes == []
        assert "no checkout" in result.detail

    def test_an_uncited_source_is_its_own_answer(self, wired):
        state, calls = wired
        state["index"] = fanout.Index()

        result = plan.build(SOURCE)

        assert result.status == plan.UNUSED
        # Nothing was fetched: there was nobody to plan for.
        assert calls["fetch"] == []

    def test_an_unreadable_proposal_is_not_a_settled_domain(self, wired):
        state, _ = wired
        state["index"] = _index("ledger")
        state["fetched"] = _resolved()
        state["domains"] = {}          # detector returns None → unreadable

        result = plan.build(SOURCE)
        outcome = result.outcomes[0]

        assert not outcome.readable
        assert outcome.blocked
        assert not outcome.decidable
        assert result.settled_domains == []
        assert "ledger" in result.unreadable

    def test_a_held_instruction_is_counted_never_a_clean_run(self, wired):
        """Held entries carry no text, so nothing could be ruled on them."""
        state, _ = wired
        state["index"] = _index("payments")
        state["fetched"] = _resolved()
        held = _entries(TEXT)[0]
        held.risks = ["name"]
        held.text = ""
        state["domains"] = {"payments": proposal.Proposal(
            domain="payments", entries=[held])}

        result = plan.build(SOURCE)
        outcome = result.outcomes[0]

        assert outcome.held == 1
        assert not outcome.decidable
        assert outcome.blocked
        assert result.counts["held"] == 1


class TestPlanOutcomes:
    def test_an_unchanged_instruction_fast_forwards(self, wired):
        state, _ = wired
        state["index"] = _index("ledger")
        state["fetched"] = _resolved()
        state["domains"] = {"ledger": proposal.Proposal(
            domain="ledger", entries=_entries(TEXT))}

        result = plan.build(SOURCE)
        outcome = result.outcomes[0]

        assert [v.status for v in outcome.verdicts] == [differ.UNCHANGED]
        assert not outcome.blocked
        assert outcome.decidable
        assert result.counts["settled"] == 1

    def test_an_instruction_the_source_dropped_escalates(self, wired):
        state, _ = wired
        state["index"] = _index("ledger")
        state["fetched"] = _resolved(text=REPLACED)
        state["domains"] = {"ledger": proposal.Proposal(
            domain="ledger", entries=_entries(TEXT))}

        result = plan.build(SOURCE)
        outcome = result.outcomes[0]

        assert outcome.escalating
        assert outcome.blocked
        assert result.counts["escalations"] >= 1

    def test_an_unverified_reword_never_fast_forwards(self, wired):
        """No judge means nothing ruled on agreement — so a human does."""
        state, _ = wired
        state["index"] = _index("ledger")
        state["fetched"] = _resolved(text=REWORDED)
        state["domains"] = {"ledger": proposal.Proposal(
            domain="ledger", entries=_entries(TEXT))}

        result = plan.build(SOURCE, provider=None)
        outcome = result.outcomes[0]

        for verdict in outcome.verdicts:
            assert verdict.settled is (verdict.status == differ.UNCHANGED)
        assert all(not v.checked or v.status == differ.UNCHANGED
                   for v in outcome.verdicts)


class TestPlanEconomics:
    def test_one_extraction_serves_every_domain(self, wired):
        """The saving that makes a fan-out worth running before a push.

        Sound only because a candidate id excludes the citation version — so
        the domains here deliberately cite different ones.
        """
        state, calls = wired
        index = fanout.Index()
        out = fanout.SourceFanout(ref=SOURCE, scheme="repo")
        out.uses.append(fanout.SourceUse(domain="ledger", ref=SOURCE,
                                         scheme="repo", versions=("v1",)))
        out.uses.append(fanout.SourceUse(domain="payments", ref=SOURCE,
                                         scheme="repo", versions=("v2",)))
        index.sources[SOURCE] = out
        state["index"] = index
        state["fetched"] = _resolved(version="v3")
        state["domains"] = {
            "ledger": proposal.Proposal(domain="ledger",
                                        entries=_entries(TEXT, version="v1")),
            "payments": proposal.Proposal(domain="payments",
                                          entries=_entries(TEXT, version="v2")),
        }
        # The fixtures above extract too; only the plan's own calls are the
        # claim being made here.
        calls["extract"] = 0

        result = plan.build(SOURCE)

        assert calls["fetch"] == [SOURCE]
        assert calls["extract"] == 1
        assert len(result.outcomes) == 2
        # Both cited different versions, and both still recognise the
        # instruction as unchanged.
        for outcome in result.outcomes:
            assert [v.status for v in outcome.verdicts] == [differ.UNCHANGED]

    def test_version_skew_is_reported(self, wired):
        state, _ = wired
        index = fanout.Index()
        out = fanout.SourceFanout(ref=SOURCE, scheme="repo")
        out.uses.append(fanout.SourceUse(domain="a", ref=SOURCE, scheme="repo",
                                         versions=("v1",)))
        out.uses.append(fanout.SourceUse(domain="b", ref=SOURCE, scheme="repo",
                                         versions=("v2",)))
        index.sources[SOURCE] = out
        state["index"] = index
        state["fetched"] = _resolved()
        state["domains"] = {"a": proposal.Proposal(domain="a"),
                            "b": proposal.Proposal(domain="b")}

        assert plan.build(SOURCE).version_skew

    def test_the_plan_writes_nothing(self, wired, monkeypatch):
        """A dry run that saves is not a dry run."""
        state, _ = wired
        state["index"] = _index("ledger")
        state["fetched"] = _resolved()
        state["domains"] = {"ledger": proposal.Proposal(
            domain="ledger", entries=_entries(TEXT))}

        def refuse(*args, **kwargs):
            raise AssertionError("the plan wrote to the proposal")

        monkeypatch.setattr(proposal, "save", refuse)
        monkeypatch.setattr(proposal, "merge", refuse)

        assert plan.build(SOURCE).planned
