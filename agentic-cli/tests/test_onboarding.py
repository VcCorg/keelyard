"""Tests for domain onboarding: classify → extract → review → finalize → score.

The load-bearing test in this file is
``test_held_candidate_text_never_reaches_disk``. The review proposal is committed
to the meta-repo, so a candidate carrying a name, a credential or a guard term
must never have its text serialised — the reviewer gets the risk kinds and the
citation and reads the source. Everything else here is ordinary behaviour; that
one is the reason the extraction contract is shaped the way it is.
"""
from __future__ import annotations

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
        card = readiness.score(readiness.Inputs(domain="d"))
        assert all(d.score is not None for d in card.scored)
        assert len(card.scored) == len(card.dimensions) - 1

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
