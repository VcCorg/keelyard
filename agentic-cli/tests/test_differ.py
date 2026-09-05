"""Tests for the semantic differ — what a source's change did to our instructions.

Two tests here are load-bearing and the rest is ordinary behaviour.

``test_a_negation_flip_is_caught_without_a_judge`` is the reason the lexical
tier strips negations before scoring: a reversed instruction has to score as a
near-perfect match so that it reaches the contradiction check at all.

``test_an_unverified_reword_never_settles`` is the reason ``checked`` exists.
Token overlap cannot tell agreement from contradiction, so without a judge the
differ must say "a human reads this", never "safe to fast-forward".
"""
from __future__ import annotations

import json

import pytest

from agentic_cli.onboarding import differ, extract, proposal


def _entry(text, kind=extract.SETUP, ref="svc/CONTRIBUTING.md", version="v1"):
    candidate = extract.Candidate(
        text=text, kind=kind, citation=extract.Citation("repo", ref, version))
    return proposal.Entry.from_candidate(candidate, proposal.ACCEPTED)


def _candidate(text, kind=extract.SETUP, ref="svc/CONTRIBUTING.md", version="v2"):
    return extract.Candidate(
        text=text, kind=kind, citation=extract.Citation("repo", ref, version))


class _Judge:
    """A provider in the shape ``answerability`` already uses."""

    def __init__(self, verdicts, name="test-judge"):
        self.verdicts = verdicts
        self.name = name
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return json.dumps([{"n": i + 1, "verdict": v, "why": "because"}
                           for i, v in enumerate(self.verdicts)])

    def get_name(self):
        return self.name


# ── lexical tier ────────────────────────────────────────────────────────────

class TestSimilarity:
    def test_reordering_is_not_a_different_instruction(self):
        """The case a sequence ratio alone gets wrong.

        Scores 0.40 on sequence order and 0.67 on token overlap; taking the
        better of the two is the whole reason similarity blends them.
        """
        score = differ.similarity(
            "Run keel doctor to verify the environment",
            "Verify the environment by running keel doctor")
        assert score >= differ.STRONG

    def test_unrelated_instructions_score_nothing(self):
        assert differ.similarity(
            "Run ./setup.sh before the first build",
            "Escalate incidents through the on-call rota") < differ.STRONG

    def test_negations_are_stripped_before_scoring(self):
        """On purpose: it is what makes a reversal look like a match.

        A reversed instruction has to score high to reach the contradiction
        check. If negations counted toward similarity it would look like an
        unrelated new instruction and pass silently as absent-plus-new.
        """
        assert differ.similarity("You must commit the lockfile",
                                 "You must not commit the lockfile") == 1.0
        assert differ.negation_profile("You must not commit the lockfile") != \
            differ.negation_profile("You must commit the lockfile")


# ── verdicts ────────────────────────────────────────────────────────────────

class TestVerdicts:
    def test_an_instruction_that_came_back_is_unchanged(self):
        entry = _entry("Run ./setup.sh before the first build")
        same = _candidate("Run ./setup.sh before the first build", version="v2")
        # The id excludes the citation version, so re-extraction matches it.
        report = differ.diff([entry], [same])
        assert report.counts == {differ.UNCHANGED: 1}
        assert report.verdicts[0].settled

    def test_a_reword_is_paired_with_its_replacement(self):
        entry = _entry("Run keel doctor to verify the environment")
        now = _candidate("Verify the environment by running keel doctor")
        [verdict] = differ.diff([entry], [now]).verdicts
        assert verdict.status == differ.REWORDED
        assert verdict.replacement == "Verify the environment by running keel doctor"

    def test_a_negation_flip_is_caught_without_a_judge(self):
        """The one contradiction reachable offline, and the one that matters."""
        entry = _entry("Check the license before adding a dependency")
        now = _candidate("Do not check the license before adding a dependency",
                         kind=extract.HAZARD)
        [verdict] = differ.diff([entry], [now]).verdicts
        assert verdict.status == differ.CONTRADICTED
        assert verdict.checked            # this one we do know
        assert verdict.actionable

    def test_a_flip_is_found_even_though_it_changes_the_instruction_kind(self):
        """Negating a step reclassifies it, so kind cannot gate the pairing.

        "do not" is a hazard marker, so the reversed form of a setup step
        extracts as a hazard. Requiring the kinds to match would report this as
        one absent step plus one unrelated new hazard — the contradiction made
        structurally invisible.
        """
        entry = _entry("Commit the lockfile", kind=extract.SETUP)
        now = _candidate("Do not commit the lockfile", kind=extract.HAZARD)
        [verdict] = differ.diff([entry], [now]).verdicts
        assert verdict.status == differ.CONTRADICTED

    def test_an_instruction_with_no_match_is_absent(self):
        entry = _entry("Export KEEL_GUARD_TERMS before running the guard script")
        other = _candidate("Escalate incidents through the on-call rota")
        [verdict] = differ.diff([entry], [other]).verdicts
        assert verdict.status == differ.ABSENT
        assert verdict.actionable

    def test_a_different_source_is_never_a_replacement(self):
        entry = _entry("Run ./setup.sh before the first build", ref="svc/A.md")
        elsewhere = _candidate("Run ./setup.sh before the first build",
                               ref="svc/B.md")
        # Same words, different file: the id differs, and pairing is per source.
        [verdict] = differ.diff([entry], [elsewhere]).verdicts
        assert verdict.status == differ.ABSENT


# ── the unverified split ────────────────────────────────────────────────────

class TestChecked:
    def test_an_unverified_reword_never_settles(self):
        """Lexical overlap says "about the same thing", not "still true"."""
        entry = _entry("Deploy with the blue-green script")
        now = _candidate("Deploy using the blue-green script only")
        [verdict] = differ.diff([entry], [now]).verdicts
        assert verdict.status == differ.REWORDED
        assert not verdict.checked
        assert verdict.actionable
        assert not verdict.settled

    def test_a_judge_can_settle_a_reword(self):
        entry = _entry("Deploy with the blue-green script")
        now = _candidate("Deploy using the blue-green script only")
        judge = _Judge([differ.AGREES])
        [verdict] = differ.diff([entry], [now], provider=judge).verdicts
        assert verdict.status == differ.REWORDED
        assert verdict.checked and verdict.settled

    def test_a_judge_can_see_a_contradiction_overlap_cannot(self):
        """The reason the judge tier exists at all."""
        entry = _entry("Run migrations before deploying")
        now = _candidate("Run migrations after deploying")
        assert differ.similarity(entry.text, now.text) >= differ.STRONG
        assert differ.negation_profile(entry.text) == differ.negation_profile(now.text)

        [offline] = differ.diff([entry], [now]).verdicts
        assert offline.status == differ.REWORDED and not offline.checked

        [judged] = differ.diff([entry], [now],
                               provider=_Judge([differ.CONTRADICTS])).verdicts
        assert judged.status == differ.CONTRADICTED

    def test_a_judge_that_fails_falls_back_rather_than_guessing(self):
        class Broken:
            def generate(self, prompt):
                raise RuntimeError("the judge is down")

            def get_name(self):
                return "broken"

        entry = _entry("Deploy with the blue-green script")
        now = _candidate("Deploy using the blue-green script only")
        [verdict] = differ.diff([entry], [now], provider=Broken()).verdicts
        assert verdict.status == differ.REWORDED
        assert not verdict.checked        # never silently marked as agreeing

    def test_an_unparseable_reply_is_not_a_verdict(self):
        class Rambling:
            def generate(self, prompt):
                return "I think they're probably fine?"

            def get_name(self):
                return "rambling"

        entry = _entry("Deploy with the blue-green script")
        now = _candidate("Deploy using the blue-green script only")
        [verdict] = differ.diff([entry], [now], provider=Rambling()).verdicts
        assert not verdict.checked


# ── assignment ──────────────────────────────────────────────────────────────

class TestPairing:
    def test_two_orphans_do_not_both_claim_one_replacement(self):
        """The failure that made ``merge`` refuse to guess in the first place."""
        a = _entry("Run the bootstrap target before the first build")
        b = _entry("Run the bootstrap target before the first deploy")
        only = _candidate("Run the bootstrap target with --clean before the "
                          "first build")
        report = differ.diff([a, b], [only])
        replacements = [v.replacement for v in report.verdicts if v.replacement]
        assert len(replacements) == 1
        assert len(report.of(differ.ABSENT)) == 1

    def test_the_best_pair_wins_not_the_first_one_seen(self):
        far = _entry("Run the bootstrap target before the first deploy")
        near = _entry("Run the bootstrap target with --clean before the build")
        now = _candidate("Run the bootstrap target with --clean before the "
                         "first build")
        report = differ.diff([far, near], [now])
        paired = [v for v in report.verdicts if v.replacement]
        assert [v.entry_id for v in paired] == [near.id]

    def test_a_surviving_twin_is_not_offered_for_its_deleted_sibling(self):
        """Near-identical templated instructions are the differ's worst case.

        Two instructions differing only in a credential name score 0.80 against
        each other. Removing the unchanged one from the pool is what keeps the
        survivor from being proposed as the deleted one's replacement.
        """
        deleted = _entry("Copy the token and paste it as BITBUCKET_TOKEN in .env")
        kept = _entry("Copy the token and paste it as JIRA_TOKEN in .env")
        assert differ.similarity(deleted.text, kept.text) >= differ.STRONG

        still_there = _candidate("Copy the token and paste it as JIRA_TOKEN in .env")
        report = differ.diff([deleted, kept], [still_there])
        by_id = {v.entry_id: v for v in report.verdicts}
        assert by_id[kept.id].status == differ.UNCHANGED
        assert by_id[deleted.id].status == differ.ABSENT
        assert not by_id[deleted.id].replacement

    def test_held_candidates_are_never_proposed_as_replacements(self):
        """Held text is never written, so it can never be a proposed_text."""
        from agentic_cli.onboarding import redaction

        entry = _entry("Ask the owner before changing the schema")
        # Risk-scanned the way `extract` scans, rather than asserted by hand.
        text = "Ask a.person@corp.example.net before changing the schema"
        risky = _candidate(text)
        risky.risks = tuple(redaction.scan(text))
        assert risky.held
        [verdict] = differ.diff([entry], [risky]).verdicts
        assert verdict.status == differ.ABSENT
        assert verdict.replacement == ""


# ── unknown ─────────────────────────────────────────────────────────────────

class TestUnknown:
    def test_an_unreadable_source_retracts_nothing(self):
        """Absent means the source dropped it. Unknown means we could not ask."""
        entries = [_entry("Run ./setup.sh"), _entry("Run keel doctor")]
        report = differ.unknown_for(entries, "repo:svc/CONTRIBUTING.md")
        assert report.counts == {differ.UNKNOWN: 2}
        assert not report.actionable      # nothing to act on; nothing learned
        assert not report.settled         # and nothing settled either
        assert report.unreadable == ["repo:svc/CONTRIBUTING.md"]


# ── the domain-level gather ─────────────────────────────────────────────────

class TestDiffDomain:
    @staticmethod
    def _domain(tmp_path, monkeypatch, body):
        from agentic_cli import persona_workspace as pw

        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        (repo / "CONTRIBUTING.md").write_text(body, encoding="utf-8")
        monkeypatch.setattr(pw, "store_repo_path", lambda slug: repo)
        return repo

    @staticmethod
    def _accepted(repo):
        from agentic_cli.onboarding import sources

        entries = []
        for doc in sources.repo_documents(repo, "svc"):
            for c in extract.extract(doc.text, doc.citation, "onboarding").candidates:
                entries.append(proposal.Entry.from_candidate(c, proposal.ACCEPTED))
        return proposal.Proposal(domain="d", entries=entries)

    def test_an_unchanged_source_is_not_re_extracted(self, tmp_path, monkeypatch):
        """The cheap gate. On a quiet domain this must cost one read and stop.

        It is what makes the differ safe to hang off a drift poll: the digest
        answers "did anything move" for free, and only a move pays for a diff.
        """
        body = "# Contributing\n\n- Run ./setup.sh before the first build\n"
        repo = self._domain(tmp_path, monkeypatch, body)
        review = self._accepted(repo)
        assert review.accepted

        from agentic_cli.commands.domain_onboarding import diff_domain
        from agentic_cli.onboarding import extract as ex

        calls = []
        monkeypatch.setattr(ex, "extract",
                            lambda *a, **k: calls.append(a) or pytest.fail(
                                "re-extracted an unchanged source"))
        assert diff_domain("d", review).verdicts == []

    def test_a_changed_source_is_ruled_on(self, tmp_path, monkeypatch):
        from agentic_cli.commands.domain_onboarding import diff_domain

        repo = self._domain(
            tmp_path, monkeypatch,
            "# Contributing\n\n- Run ./setup.sh before the first build\n"
            "- Check the license before adding a dependency\n")
        review = self._accepted(repo)

        (repo / "CONTRIBUTING.md").write_text(
            "# Contributing\n\n- Run ./setup.sh before the first build\n"
            "- Do not check the license before adding a dependency\n",
            encoding="utf-8")
        report = diff_domain("d", review)
        assert differ.CONTRADICTED in report.counts
        assert report.counts[differ.UNCHANGED] == 1

    def test_a_source_that_cannot_be_read_is_unknown(self, tmp_path, monkeypatch):
        from agentic_cli import persona_workspace as pw
        from agentic_cli.commands.domain_onboarding import diff_domain

        repo = self._domain(tmp_path, monkeypatch,
                            "# Contributing\n\n- Run ./setup.sh first\n")
        review = self._accepted(repo)
        # The clone goes away; the instructions drawn from it do not become false.
        monkeypatch.setattr(pw, "store_repo_path", lambda slug: tmp_path / "gone")
        report = diff_domain("d", review)
        assert set(report.counts) == {differ.UNKNOWN}
        assert report.unreadable
