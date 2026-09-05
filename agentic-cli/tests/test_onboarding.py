"""Tests for domain onboarding: classify → extract → review → finalize → score.

The load-bearing test in this file is
``test_held_candidate_text_never_reaches_disk``. The review proposal is committed
to the meta-repo, so a candidate carrying a name, a credential or a guard term
must never have its text serialised — the reviewer gets the risk kinds and the
citation and reads the source. Everything else here is ordinary behaviour; that
one is the reason the extraction contract is shaped the way it is.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agentic_cli.onboarding import classify, extract, provenance, proposal, readiness
from agentic_cli.onboarding import redaction


# ── redaction ───────────────────────────────────────────────────────────────

class TestRedaction:
    def test_risk_carries_no_matched_text(self):
        """A Risk names a kind and a count — never the span it matched.

        Anything else would relocate the disclosure into the review file.
        """
        risks = redaction.scan("email me at jane.doe@internal.example.org")
        assert risks
        for risk in risks:
            assert "jane" not in repr(risk).lower()
            assert not hasattr(risk, "span")
            assert not hasattr(risk, "match")

    def test_detects_email(self):
        assert any(r.kind == redaction.EMAIL
                   for r in redaction.scan("ping a.person@corp.example.net"))

    def test_detects_person_after_addressing_verb(self):
        assert any(r.kind == redaction.PERSON
                   for r in redaction.scan("Ask Jane Doe for access"))

    def test_ignores_capitalised_words_that_are_not_names(self):
        """'Use Docker Compose' must not read as a personal name."""
        assert not any(r.kind == redaction.PERSON
                       for r in redaction.scan("Use Docker Compose to start"))

    def test_secret_pattern_but_placeholder_is_safe(self):
        # Assembled at runtime, never written as a literal: a credential-shaped
        # string in this file would trip scripts/check-no-company-data.sh, which
        # scans the diff. Do not "simplify" these back into one string.
        credential = "api_key=" + ("A1b2C3d4" * 4)
        assert any(r.kind == redaction.SECRET for r in redaction.scan(credential))
        assert not any(r.kind == redaction.SECRET
                       for r in redaction.scan("api_key=your-key-here"))

    def test_public_docs_host_is_not_internal(self):
        assert redaction.is_safe("See https://docs.python.org/3/library/os.html")
        assert any(r.kind == redaction.INTERNAL_HOST
                   for r in redaction.scan("Open https://wiki.corp.internal/x"))

    def test_guard_terms_come_from_env(self, monkeypatch):
        redaction.guard_terms.cache_clear()
        monkeypatch.setenv("KEEL_GUARD_TERMS", "widgetco,jdoe")
        try:
            risks = redaction.scan("Deploy to the WidgetCo cluster")
            assert any(r.kind == redaction.GUARD_TERM for r in risks)
        finally:
            redaction.guard_terms.cache_clear()

    def test_clean_text_is_safe(self):
        assert redaction.is_safe("Run the bootstrap target before the first build")


# ── classify ────────────────────────────────────────────────────────────────

class TestClassify:
    @pytest.mark.parametrize("title,expected", [
        ("Team Onboarding — Week 1", classify.ONBOARDING),
        ("Getting Started", classify.ONBOARDING),
        ("New Joiner Setup", classify.ONBOARDING),
        ("Deployment Runbook", classify.RUNBOOK),
        ("On-Call Handbook", classify.RUNBOOK),
        ("ADR-014: Event Sourcing", classify.ADR),
        ("Facility Glossary", classify.REFERENCE),
        ("Functional Requirements", classify.REQUIREMENT),
        ("Sprint 42 Retrospective", classify.OTHER),
    ])
    def test_titles(self, title, expected):
        assert classify.classify(title).doc_type == expected

    def test_verdict_names_the_rule_that_fired(self):
        """A wrong call should be a rule to fix, not a model to re-prompt."""
        assert classify.classify("Team Onboarding").rule

    def test_space_key_is_a_fallback(self):
        result = classify.classify("Misc Page", space_key="TEAMONBOARDING")
        assert result.doc_type == classify.ONBOARDING
        assert result.confidence < 0.75  # weaker evidence than a title

    def test_body_evidence_scores_below_title_evidence(self):
        by_title = classify.classify("Onboarding Guide")
        by_body = classify.classify("Untitled", body_excerpt="onboarding steps here")
        assert by_body.doc_type == by_title.doc_type
        assert by_body.confidence < by_title.confidence

    def test_operational_types(self):
        assert classify.classify("Onboarding").operational
        assert classify.classify("Runbook").operational
        assert not classify.classify("ADR-1: Something").operational


# ── extract ─────────────────────────────────────────────────────────────────

CITATION = extract.Citation("confluence", "12345", "7")


class TestExtract:
    def test_harvests_imperative_steps(self):
        text = "# Setup\n\n- Run the bootstrap target before building\n- Nice weather today\n"
        result = extract.extract(text, CITATION)
        texts = [c.text for c in result.candidates]
        assert any("bootstrap" in t for t in texts)
        assert not any("weather" in t for t in texts)

    def test_code_fences_are_skipped(self):
        """A command block is exactly where hosts and credentials live."""
        # Assembled rather than written literally — see the note in
        # TestRedaction.test_secret_pattern_but_placeholder_is_safe.
        fenced = "export DB_PASSWORD=" + ("z9Y8x7W6" * 3)
        text = f"# Setup\n\n- Run the bootstrap target\n\n```\n{fenced}\n```\n"
        result = extract.extract(text, CITATION)
        assert all("DB_PASSWORD" not in c.text for c in result.candidates)
        assert result.candidates, "the prose around the fence should still yield a step"

    def test_hazards_are_recognised(self):
        result = extract.extract("- Never run migrations against prod directly\n", CITATION)
        assert any(c.kind == extract.HAZARD for c in result.candidates)

    def test_ownership_is_pointerized_not_named(self):
        """Names decay fastest; the durable pointer is what we keep."""
        text = "- Ask Jane Doe or the platform team for access\n"
        result = extract.extract(text, CITATION)
        owners = [c for c in result.candidates if c.kind == extract.OWNERSHIP]
        assert owners, "expected a pointerized ownership candidate"
        assert "Jane" not in owners[0].text
        assert "platform team" in owners[0].text.lower()
        assert owners[0].abstracted

    def test_ownership_without_a_pointer_is_held(self):
        text = "- Ask Jane Doe for access\n"
        result = extract.extract(text, CITATION)
        assert not [c for c in result.candidates if c.kind == extract.OWNERSHIP]
        assert any(c.kind == extract.OWNERSHIP for c in result.held)

    def test_glossary_only_under_a_glossary_heading(self):
        under = extract.extract("## Glossary\n\nFacility: a physical care site\n", CITATION)
        assert any(c.kind == extract.GLOSSARY for c in under.candidates)
        outside = extract.extract("Facility: a physical care site\n", CITATION)
        assert not any(c.kind == extract.GLOSSARY for c in outside.candidates)

    def test_risky_candidate_is_held_not_returned(self):
        text = "- Configure the client against https://svc.corp.internal/api\n"
        result = extract.extract(text, CITATION)
        assert result.held
        assert not result.candidates

    def test_candidate_id_is_stable(self):
        one = extract.extract("- Run the bootstrap target\n", CITATION)
        two = extract.extract("- Run the bootstrap target\n", CITATION)
        assert one.candidates[0].id == two.candidates[0].id

    def test_citation_round_trip(self):
        assert extract.Citation.parse(str(CITATION)) == CITATION

    def test_empty_body(self):
        assert extract.extract("", CITATION).candidates == []


# ── the invariant ───────────────────────────────────────────────────────────

def test_held_candidate_text_never_reaches_disk(tmp_path):
    """A held candidate's text must not be serialised, at any layer.

    The proposal is committed to the meta-repo. If held text could be written,
    extraction would relocate the disclosure it exists to prevent rather than
    stopping it — so this is pinned end to end: candidate → entry → YAML on disk.
    """
    secret_line = "- Ask Jane Doe at jane.doe@corp.example.net for the token\n"
    result = extract.extract(secret_line, CITATION)
    assert result.held, "expected this line to be held"

    held = result.held[0]
    assert "text" not in held.to_dict()
    assert held.to_dict()["risks"]

    review = proposal.merge(proposal.Proposal(domain="d"), result.held, "d")
    path = proposal.save(tmp_path, review)

    written = path.read_text(encoding="utf-8")
    for leaked in ("Jane", "jane.doe", "corp.example.net", "token"):
        assert leaked not in written, f"{leaked!r} leaked into the review file"


# ── proposal ────────────────────────────────────────────────────────────────

def _candidate(text: str, version: str = "7", kind: str = extract.SETUP) -> extract.Candidate:
    return extract.Candidate(text, kind, extract.Citation("confluence", "12345", version), 0.7)


class TestProposal:
    def test_new_candidates_default_to_unreviewed(self, tmp_path):
        review = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Run the bootstrap target")], "d")
        assert review.entries[0].status == proposal.UNREVIEWED
        assert not review.accepted

    def test_round_trip(self, tmp_path):
        review = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Run the bootstrap target")], "d")
        proposal.save(tmp_path, review)
        assert proposal.load(tmp_path, "d").entries[0].text == "Run the bootstrap target"

    def test_accepted_verdict_survives_reextraction(self, tmp_path):
        first = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Run the bootstrap target")], "d")
        first.entries[0].status = proposal.ACCEPTED
        second = proposal.merge(first, [_candidate("Run the bootstrap target")], "d")
        assert second.entries[0].status == proposal.ACCEPTED

    def test_source_moving_makes_an_approved_entry_stale_with_a_diff(self, tmp_path):
        """Drift proposes a change; it never silently overwrites an approval."""
        first = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Run the bootstrap target")], "d")
        first.entries[0].status = proposal.ACCEPTED

        moved = proposal.merge(first, [_candidate("Run the bootstrap target with --clean", version="8")], "d")
        entry = moved.entries[0]
        assert entry.status == proposal.STALE
        assert entry.text == "Run the bootstrap target"          # what was approved
        assert entry.proposed_text.endswith("--clean")            # what is proposed
        assert entry.pending

    def test_approved_entry_absent_from_source_is_flagged_not_dropped(self, tmp_path):
        first = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Run the bootstrap target")], "d")
        first.entries[0].status = proposal.ACCEPTED
        second = proposal.merge(first, [], "d")
        assert second.entries[0].source_absent
        assert second.entries[0].status == proposal.ACCEPTED

    def test_rejections_are_remembered(self):
        first = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Nice weather today")], "d")
        first.entries[0].status = proposal.REJECTED
        assert proposal.merge(first, [], "d").entries[0].status == proposal.REJECTED

    def test_saved_file_is_valid_yaml_with_schema(self, tmp_path):
        review = proposal.merge(proposal.Proposal(domain="d"), [_candidate("Run the bootstrap target")], "d")
        data = yaml.safe_load(proposal.save(tmp_path, review).read_text(encoding="utf-8"))
        assert data["schema"] == proposal.SCHEMA
        assert data["domain"] == "d"

    def test_pending_entries_sort_first(self):
        review = proposal.merge(
            proposal.Proposal(domain="d"),
            [_candidate("Run the bootstrap target"), _candidate("Install the toolchain")],
            "d",
        )
        review.entries[0].status = proposal.ACCEPTED
        ordered = review.to_dict()["entries"]
        assert ordered[0]["status"] == proposal.UNREVIEWED


# ── provenance ──────────────────────────────────────────────────────────────

class TestProvenance:
    def test_stamp_and_read_round_trip(self, tmp_path):
        path = tmp_path / "kg-context.md"
        path.write_text("# Context\n\nReal content here.\n", encoding="utf-8")
        provenance.stamp(path, "doc:12345", reviewed=True)
        stamp = provenance.read(path)
        assert (stamp.provenance, stamp.source, stamp.reviewed) == ("doc", "12345", True)
        assert stamp.real and stamp.grounded

    def test_stamping_preserves_the_body(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_text("# Heading\n\nBody.\n", encoding="utf-8")
        provenance.stamp(path, "kg")
        assert "# Heading" in path.read_text(encoding="utf-8")

    def test_restamping_does_not_stack_frontmatter(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_text("Body.\n", encoding="utf-8")
        provenance.stamp(path, "kg")
        provenance.stamp(path, "doc:9", reviewed=True)
        assert path.read_text(encoding="utf-8").count("---") == 2
        assert provenance.read(path).source == "9"

    def test_legacy_placeholder_is_detected_without_frontmatter(self, tmp_path):
        """An unstamped file that reads like filler *is* filler — no migration."""
        path = tmp_path / "architecture.md"
        path.write_text(
            "# Arch\n\n_Architecture details will be populated from the "
            "Knowledge Graph._\n", encoding="utf-8")
        stamp = provenance.read(path)
        assert stamp.provenance == provenance.PLACEHOLDER
        assert not stamp.real

    def test_empty_file_is_placeholder(self, tmp_path):
        path = tmp_path / "empty.md"
        path.write_text("", encoding="utf-8")
        assert provenance.read(path).provenance == provenance.PLACEHOLDER

    def test_unstamped_real_content_is_unknown_not_placeholder(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_text("# Arch\n\nCQRS with an event store.\n", encoding="utf-8")
        assert provenance.read(path).provenance == provenance.UNKNOWN

    def test_summarize(self, tmp_path):
        (tmp_path / "a.md").write_text("Real.\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("", encoding="utf-8")
        provenance.stamp(tmp_path / "a.md", "kg")
        summary = provenance.summarize(provenance.scan(tmp_path))
        assert summary == {"total": 2, "real": 1, "placeholder": 1,
                           "unknown": 0, "reviewed": 0, "grounded": 0}


# ── readiness ───────────────────────────────────────────────────────────────

def _reviewed(entries: list[tuple[str, str]]) -> proposal.Proposal:
    """Build an all-accepted proposal from ``(kind, text)`` pairs."""
    review = proposal.Proposal(domain="d")
    for index, (kind, text) in enumerate(entries):
        review.entries.append(proposal.Entry(
            id=f"e{index}", kind=kind, citation="confluence:1@1",
            status=proposal.ACCEPTED, text=text,
        ))
    return review


class TestReadiness:
    def test_empty_domain_fails(self):
        card = readiness.score(readiness.Inputs(domain="d"))
        assert not card.ready()
        assert card.failed
        assert card.grade == "F"

    def test_answerability_skips_without_a_judge(self):
        """A missing credential must not look like an unready domain."""
        card = readiness.score(readiness.Inputs(domain="d", judge_available=False))
        answerability = next(d for d in card.dimensions if d.key == "answerability")
        assert answerability.status == readiness.SKIPPED
        assert answerability.score is None

    def test_skipped_dimensions_are_excluded_from_the_mean(self):
        """An empty domain skips both answerability and freshness."""
        card = readiness.score(readiness.Inputs(domain="d"))
        assert all(d.score is not None for d in card.scored)
        assert len(card.scored) == len(card.dimensions) - 2

    def test_freshness_skips_when_there_is_nothing_to_assess(self):
        """Absent evidence is unknown, not failure."""
        card = readiness.score(readiness.Inputs(domain="d"))
        freshness = next(d for d in card.dimensions if d.key == "freshness")
        assert freshness.status == readiness.SKIPPED
        assert freshness.score is None

    def test_a_well_stocked_domain_is_ready(self, tmp_path):
        for name in ("kg-context.md", "architecture.md"):
            path = tmp_path / name
            path.write_text("Real content.\n", encoding="utf-8")
            provenance.stamp(path, "doc:1", reviewed=True)

        review = _reviewed(
            [(extract.GLOSSARY, f"Term{i}: meaning") for i in range(10)]
            + [(extract.SETUP, f"Run step {i}") for i in range(4)]
            + [(extract.OWNERSHIP, "Ownership is recorded in: CODEOWNERS")]
            + [(extract.HAZARD, f"Never do {i}") for i in range(5)]
        )
        card = readiness.score(readiness.Inputs(
            domain="d",
            repos=[{"slug": "svc", "has_codeowners": True}],
            review=review,
            stamps=provenance.scan(tmp_path),
            governance={"promotion_path": ["dev", "stage", "prod"],
                        "checkpoint_gate_map": [{"checkpoint": "spec", "gate": "dev"}]},
            docs=[{"source_page_id": "1"}],
        ))
        assert card.ready(), card.to_dict()
        assert card.grade in ("A", "B")

    def test_pending_review_lowers_freshness(self):
        base = readiness.Inputs(domain="d", docs=[{"source_page_id": "1"}])
        clean = readiness.score(base)
        pending_review = proposal.Proposal(domain="d", entries=[
            proposal.Entry(id=f"e{i}", kind=extract.SETUP, citation="confluence:1@1",
                           status=proposal.UNREVIEWED, text=f"Step {i}")
            for i in range(5)
        ])
        dirty = readiness.score(readiness.Inputs(
            domain="d", docs=[{"source_page_id": "1"}], review=pending_review))

        def freshness(card):
            return next(d for d in card.dimensions if d.key == "freshness").score

        assert freshness(dirty) < freshness(clean)

    def test_stale_docs_lower_freshness(self):
        docs = [{"source_page_id": str(i)} for i in range(10)]
        fresh = readiness.score(readiness.Inputs(domain="d", docs=docs, stale_docs=0))
        stale = readiness.score(readiness.Inputs(domain="d", docs=docs, stale_docs=5))

        def freshness(card):
            return next(d for d in card.dimensions if d.key == "freshness").score

        assert freshness(stale) < freshness(fresh)

    def test_scorecard_serialises(self):
        data = readiness.score(readiness.Inputs(domain="d")).to_dict()
        assert data["schema"] == "keel-domain-readiness/v1"
        assert len(data["dimensions"]) == 8


# ── tracker migration ───────────────────────────────────────────────────────

class TestDocTypeMigration:
    """v14 must reach an existing database, not only a fresh one."""

    def _tracker(self, home: Path):
        import importlib
        import os

        os.environ["HOME"] = str(home)
        import agentic_cli.tracker as tracker
        return importlib.reload(tracker)

    def test_fresh_database_has_the_columns(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        tracker = self._tracker(tmp_path)
        tracker._ensure_db()
        import sqlite3
        with sqlite3.connect(str(tracker.DB_PATH)) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(domain_docs)")}
        assert {"doc_type", "doc_type_confidence", "live_version", "checked_at"} <= cols

    def test_existing_database_is_upgraded(self, tmp_path, monkeypatch):
        """A v13 database gains the columns rather than being left behind."""
        import sqlite3

        monkeypatch.setenv("HOME", str(tmp_path))
        tracker = self._tracker(tmp_path)
        tracker._ensure_db()

        # Rewind to v13 and drop the v14 columns, simulating an older install.
        with sqlite3.connect(str(tracker.DB_PATH)) as conn:
            conn.execute("DROP INDEX IF EXISTS idx_domain_docs_type")
            for col in ("doc_type", "doc_type_confidence", "live_version", "checked_at"):
                conn.execute(f"ALTER TABLE domain_docs DROP COLUMN {col}")
            conn.execute("UPDATE schema_version SET version = 13")

        tracker._ensure_db()

        with sqlite3.connect(str(tracker.DB_PATH)) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(domain_docs)")}
            version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        assert version == 14
        assert {"doc_type", "doc_type_confidence", "live_version", "checked_at"} <= cols

    def test_stale_docs_needs_a_live_version(self, tmp_path, monkeypatch):
        """An unchecked doc is unknown, not fresh — and never counted as stale."""
        monkeypatch.setenv("HOME", str(tmp_path))
        tracker = self._tracker(tmp_path)
        tracker.register_domain("d", product="P", domain="D")
        tracker.add_domain_doc("d", "1", title="Onboarding", source_version=3)

        assert tracker.stale_domain_docs("d") == []
        tracker.set_domain_doc_live_version("d", "1", 5)
        assert len(tracker.stale_domain_docs("d")) == 1

    def test_resync_preserves_a_reviewer_correction(self, tmp_path, monkeypatch):
        """Re-syncing a doc must not discard a hand-fixed classification."""
        monkeypatch.setenv("HOME", str(tmp_path))
        tracker = self._tracker(tmp_path)
        tracker.register_domain("d", product="P", domain="D")
        tracker.add_domain_doc("d", "1", title="Misc", source_version=1)
        tracker.set_domain_doc_type("d", "1", classify.ONBOARDING, 1.0)

        tracker.add_domain_doc("d", "1", title="Misc", source_version=2)

        doc = tracker.get_domain_docs("d")[0]
        assert doc["doc_type"] == classify.ONBOARDING


class TestPointerRegex:
    """A pointer must be a whole token, not a substring of a longer word."""

    def test_ownership_word_does_not_yield_a_phantom_owners_pointer(self):
        text = "- Ownership for each package is recorded in CODEOWNERS\n"
        result = extract.extract(text, CITATION)
        owners = [c for c in result.candidates if c.kind == extract.OWNERSHIP]
        assert owners
        assert owners[0].text == "Ownership is recorded in: CODEOWNERS"

    def test_pointers_dedupe_case_insensitively(self):
        text = "- Owner is in CODEOWNERS; see codeowners for the current list\n"
        result = extract.extract(text, CITATION)
        owners = [c for c in result.candidates if c.kind == extract.OWNERSHIP]
        assert owners
        assert owners[0].text.lower().count("codeowners") == 1


# ── repo-source staleness ───────────────────────────────────────────────────

class TestRepoStaleness:
    """A repo citation is a digest of the file's own content, not a commit sha.

    Citing HEAD would mark every repo-sourced instruction stale the moment
    anyone committed an unrelated file, which is why this is content-addressed.
    """

    def test_version_tracks_content_not_the_repository(self, tmp_path):
        from agentic_cli.onboarding import sources

        path = tmp_path / "CONTRIBUTING.md"
        path.write_text("- Run the bootstrap target before your first build\n",
                        encoding="utf-8")
        [doc] = sources.repo_documents(tmp_path, "svc")
        first = doc.citation.version
        assert first

        # An unrelated file appearing does not touch this citation's version.
        (tmp_path / "UNRELATED.md").write_text("noise\n", encoding="utf-8")
        [again] = [d for d in sources.repo_documents(tmp_path, "svc")
                   if d.citation.ref.endswith("CONTRIBUTING.md")]
        assert again.citation.version == first

    def test_editing_the_file_changes_the_version(self, tmp_path):
        from agentic_cli.onboarding import sources

        path = tmp_path / "CONTRIBUTING.md"
        path.write_text("- Run the bootstrap target\n", encoding="utf-8")
        before = sources.repo_documents(tmp_path, "svc")[0].citation.version

        path.write_text("- Run the bootstrap target with --clean\n", encoding="utf-8")
        after = sources.repo_documents(tmp_path, "svc")[0].citation.version
        assert before != after

    def test_stale_check(self, tmp_path):
        from agentic_cli.onboarding import sources

        path = tmp_path / "CONTRIBUTING.md"
        path.write_text("original\n", encoding="utf-8")
        cited = sources.content_version("original\n")

        assert sources.is_repo_citation_stale(tmp_path, "CONTRIBUTING.md", cited) is False
        path.write_text("changed\n", encoding="utf-8")
        assert sources.is_repo_citation_stale(tmp_path, "CONTRIBUTING.md", cited) is True

    def test_unreadable_source_is_unknown_not_stale(self, tmp_path):
        """Unknown is never reported as fresh and never as stale."""
        from agentic_cli.onboarding import sources

        assert sources.is_repo_citation_stale(tmp_path, "missing.md", "abc123") is None
        assert sources.is_repo_citation_stale(tmp_path, "missing.md", "") is None

    def test_stale_instructions_lower_freshness(self):
        accepted = proposal.Proposal(domain="d", entries=[
            proposal.Entry(id=f"e{i}", kind=extract.SETUP, citation="repo:svc/X.md@abc",
                           status=proposal.ACCEPTED, text=f"Step {i}")
            for i in range(4)
        ])

        def freshness(stale):
            card = readiness.score(readiness.Inputs(
                domain="d", docs=[{"source_page_id": "1"}],
                review=accepted, stale_instructions=stale))
            return next(d for d in card.dimensions if d.key == "freshness").score

        assert freshness(2) < freshness(0)


class TestSessionModel:
    """create_session recorded the engine and never the model."""

    def test_requested_and_served_are_kept_apart(self, tmp_path, monkeypatch):
        import importlib

        monkeypatch.setenv("HOME", str(tmp_path))
        import agentic_cli.tracker as tracker
        tracker = importlib.reload(tracker)
        import agentic_cli.tracing as tracing
        tracing = importlib.reload(tracing)

        trace_id = tracker.new_correlation_id()
        tracker.record_action(
            "execution", "create_session", entity_type="session", entity_id="s1",
            correlation_id=trace_id,
            details={"engine": "local", "model_requested": "big-model",
                     "model_served": "fallback-model"},
        )
        assert tracing.session_engine(trace_id) == {
            "engine": "local",
            "model_requested": "big-model",
            "model_served": "fallback-model",
        }

    def test_unknown_model_reports_empty_not_a_guess(self, tmp_path, monkeypatch):
        """A hosted engine that never reports back leaves this empty."""
        import importlib

        monkeypatch.setenv("HOME", str(tmp_path))
        import agentic_cli.tracker as tracker
        tracker = importlib.reload(tracker)
        import agentic_cli.tracing as tracing
        tracing = importlib.reload(tracing)

        trace_id = tracker.new_correlation_id()
        tracker.record_action(
            "execution", "create_session", entity_type="session", entity_id="s2",
            correlation_id=trace_id, details={"engine": "devin"},
        )
        engine = tracing.session_engine(trace_id)
        assert engine["engine"] == "devin"
        assert engine["model_served"] == ""


# ── answerability ───────────────────────────────────────────────────────────

class _FakeProvider:
    def __init__(self, reply, name="fake/judge-1"):
        self._reply, self._name = reply, name

    def generate(self, prompt):
        if isinstance(self._reply, Exception):
            raise self._reply
        self.prompt = prompt
        return self._reply

    def get_name(self):
        return self._name


class TestAnswerability:
    def _questions(self):
        from agentic_cli.onboarding import answerability
        return answerability.build_questions("acme-facility", "ACME",
                                             [{"slug": "svc-a"}, {"slug": "svc-b"}])

    def test_questions_are_deterministic(self):
        """A generated exam would drift for reasons unrelated to the context."""
        from agentic_cli.onboarding import answerability

        first = answerability.build_questions("d", "P", [{"slug": "r"}])
        second = answerability.build_questions("d", "P", [{"slug": "r"}])
        assert [q.text for q in first] == [q.text for q in second]

    def test_repo_questions_are_capped(self):
        """The exam must not get harder just because a domain has more repos."""
        from agentic_cli.onboarding import answerability

        many = answerability.build_questions(
            "d", "P", [{"slug": f"r{i}"} for i in range(20)])
        repo_questions = [q for q in many if q.key.startswith("repo-setup")]
        assert len(repo_questions) == answerability.MAX_REPO_QUESTIONS

    def test_scores_a_clean_json_reply(self):
        from agentic_cli.onboarding import answerability

        questions = self._questions()
        reply = json.dumps([
            {"n": i + 1, "verdict": "answered" if i % 2 == 0 else "missing", "why": "x"}
            for i in range(len(questions))
        ])
        report = answerability.judge(questions, "some context", _FakeProvider(reply))
        assert report is not None
        assert 40 < report.score < 60
        assert report.model == "fake/judge-1"

    def test_tolerates_a_fenced_reply(self):
        from agentic_cli.onboarding import answerability

        questions = self._questions()
        body = json.dumps([{"n": i + 1, "verdict": "answered"} for i in range(len(questions))])
        report = answerability.judge(questions, "ctx", _FakeProvider(f"Sure!\n```json\n{body}\n```"))
        assert report is not None and report.score == 100.0

    def test_unparseable_reply_is_unknown_not_zero(self):
        """A model having a bad day must not look like an unready domain."""
        from agentic_cli.onboarding import answerability

        assert answerability.judge(self._questions(), "ctx", _FakeProvider("no idea, sorry")) is None

    def test_provider_failure_is_unknown(self):
        from agentic_cli.onboarding import answerability

        assert answerability.judge(
            self._questions(), "ctx", _FakeProvider(RuntimeError("429"))) is None

    def test_empty_context_is_unknown(self):
        from agentic_cli.onboarding import answerability

        assert answerability.judge(self._questions(), "   ", _FakeProvider("[]")) is None

    def test_a_question_the_judge_skipped_counts_as_missing(self):
        """Silence about a question is not evidence the context answers it."""
        from agentic_cli.onboarding import answerability

        questions = self._questions()
        reply = json.dumps([{"n": 1, "verdict": "answered"}])
        report = answerability.judge(questions, "ctx", _FakeProvider(reply))
        assert report is not None
        assert report.answered == 1
        assert len(report.gaps) == len(questions) - 1

    def test_scorecard_uses_the_report(self):
        from agentic_cli.onboarding import answerability

        questions = self._questions()
        report = answerability.Report(
            verdicts=[answerability.Verdict(q, answerability.ANSWERED) for q in questions],
            model="fake/judge-1")
        card = readiness.score(readiness.Inputs(
            domain="d", judge_available=True, answerability=report))
        dimension = next(d for d in card.dimensions if d.key == "answerability")
        assert dimension.status == readiness.OK
        assert dimension.score == 100.0

    def test_scorecard_skips_when_the_judge_could_not_be_read(self):
        card = readiness.score(readiness.Inputs(
            domain="d", judge_available=True, answerability=None))
        dimension = next(d for d in card.dimensions if d.key == "answerability")
        assert dimension.status == readiness.SKIPPED
        assert "could not be read" in dimension.detail


class TestMergeAmbiguity:
    """Regression: one document yielding several instructions of a kind.

    The first implementation keyed the "what did this replace?" lookup on
    (kind, source) alone, so three setup steps from one file collapsed into a
    single entry. Every re-extraction then paired each new candidate with an
    arbitrary survivor and showed the reviewer a diff that never happened —
    and because the instruction id included the source's *version*, identical
    text was re-identified on every edit, so no verdict could survive at all.
    """

    def _file_candidates(self, texts, version):
        citation = extract.Citation("repo", "svc/CONTRIBUTING.md", version)
        return [extract.Candidate(t, extract.SETUP, citation, 0.7) for t in texts]

    def test_identical_text_survives_a_change_elsewhere_in_the_file(self):
        texts = ["Run the bootstrap target", "Install the toolchain",
                 "Configure the local database"]
        first = proposal.merge(proposal.Proposal(domain="d"),
                               self._file_candidates(texts, "v1"), "d")
        for entry in first.entries:
            entry.status = proposal.ACCEPTED

        # One step edited; the file's digest changes for all of them.
        edited = ["Run the bootstrap target with --clean", "Install the toolchain",
                  "Configure the local database"]
        second = proposal.merge(first, self._file_candidates(edited, "v2"), "d")

        by_text = {e.text: e for e in second.entries}
        assert by_text["Install the toolchain"].status == proposal.ACCEPTED
        assert by_text["Configure the local database"].status == proposal.ACCEPTED

    def test_ambiguous_replacement_is_not_invented(self):
        """With several candidates from one source, no false 'was → now' pairing."""
        first = proposal.merge(
            proposal.Proposal(domain="d"),
            self._file_candidates(["Step one", "Step two"], "v1"), "d")
        for entry in first.entries:
            entry.status = proposal.ACCEPTED

        second = proposal.merge(
            first, self._file_candidates(["Totally different A", "Totally different B"], "v2"), "d")

        for entry in second.entries:
            if entry.proposed_text:
                assert entry.text != entry.proposed_text
                raise AssertionError("no pairing should have been invented here")
        assert {e.text for e in second.entries if e.status == proposal.UNREVIEWED} == {
            "Totally different A", "Totally different B"}
        assert all(e.source_absent for e in second.entries
                   if e.text in {"Step one", "Step two"})

    def test_unambiguous_replacement_still_pairs(self):
        """The 1:1 case keeps the diff a reviewer wants to see."""
        first = proposal.merge(proposal.Proposal(domain="d"),
                               self._file_candidates(["Step one"], "v1"), "d")
        first.entries[0].status = proposal.ACCEPTED

        second = proposal.merge(first, self._file_candidates(["Step one, revised"], "v2"), "d")
        [entry] = second.entries
        assert entry.status == proposal.STALE
        assert entry.text == "Step one"
        assert entry.proposed_text == "Step one, revised"

    def test_id_ignores_the_source_version(self):
        citation_v1 = extract.Citation("repo", "svc/X.md", "v1")
        citation_v2 = extract.Citation("repo", "svc/X.md", "v2")
        one = extract.Candidate("Same words", extract.SETUP, citation_v1, 0.7)
        two = extract.Candidate("Same words", extract.SETUP, citation_v2, 0.7)
        assert one.id == two.id

    def test_id_still_separates_different_sources(self):
        one = extract.Candidate("Same words", extract.SETUP,
                                extract.Citation("repo", "a/X.md", "v1"), 0.7)
        two = extract.Candidate("Same words", extract.SETUP,
                                extract.Citation("repo", "b/X.md", "v1"), 0.7)
        assert one.id != two.id
