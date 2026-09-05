"""Tests for the retrieval seam — one ref in, current content and version out.

The load-bearing tests here are the ones about *which kind of nothing* a fetch
returned. Three call sites used to answer "fetch what this ref points at"
independently and all three collapsed "we could not ask" into "there is nothing
there". That distinction decides whether an approved instruction gets flagged as
absent, so it is the thing this module exists to keep, and the thing worth
pinning down.
"""
from __future__ import annotations

import pytest

from agentic_cli import retrieval


# ── ref parsing ─────────────────────────────────────────────────────────────

class TestParseRef:
    """Two spellings, one address. Both already exist in the codebase."""

    def test_url_style(self):
        ref = retrieval.parse_ref("domain://acme/setup.md")
        assert (ref.scheme, ref.path, ref.version) == ("domain", "acme/setup.md", "")

    def test_citation_style_carries_a_version(self):
        ref = retrieval.parse_ref("repo:svc/CONTRIBUTING.md@9f2c1a")
        assert (ref.scheme, ref.path, ref.version) == (
            "repo", "svc/CONTRIBUTING.md", "9f2c1a")

    def test_a_ref_without_a_scheme_is_not_an_error(self):
        """It is a source Keel does not mediate, which is worth recording."""
        ref = retrieval.parse_ref("some-external-thing")
        assert ref.scheme == ""
        assert ref.path == "some-external-thing"

    def test_round_trips_to_what_was_asked_for(self):
        for raw in ("domain://acme/setup.md", "repo:svc/X.md@abc", "plain"):
            assert str(retrieval.parse_ref(raw)) == raw


# ── registry ────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_builtin_schemes_are_registered(self):
        assert {"domain", "okf", "repo", "confluence", "governance"} <= set(
            retrieval.schemes())

    def test_a_new_source_is_a_registration_not_a_branch(self, monkeypatch):
        monkeypatch.setitem(
            retrieval._FETCHERS, "jira",
            lambda ref: retrieval.Fetched(ref=str(ref), scheme="jira",
                                          status=retrieval.RESOLVED,
                                          text="ticket body", version="7"))
        result = retrieval.fetch("jira:PROJ-1", trace=False)
        assert result.resolved and result.text == "ticket body"

    def test_an_unregistered_scheme_is_unsupported_not_a_crash(self):
        result = retrieval.fetch("nosuchscheme:thing", trace=False)
        assert result.status == retrieval.UNSUPPORTED
        assert not result.known

    def test_a_fetcher_that_raises_becomes_unavailable(self, monkeypatch):
        """Callers are context assembly, a drift poll and a dashboard page.

        None of them should fail because one source is misconfigured.
        """
        def boom(ref):
            raise RuntimeError("upstream is on fire")

        monkeypatch.setitem(retrieval._FETCHERS, "boom", boom)
        result = retrieval.fetch("boom:x", trace=False)
        assert result.status == retrieval.UNAVAILABLE
        assert not result.known
        assert "upstream is on fire" not in result.detail  # type, not message


# ── the five outcomes ───────────────────────────────────────────────────────

@pytest.fixture
def domain_meta(tmp_path, monkeypatch):
    meta = tmp_path / "acme-context-meta"
    (meta / ".domain").mkdir(parents=True)
    monkeypatch.setattr(
        "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
        lambda slug, search_paths=None: meta if slug == "acme" else None)
    return meta


class TestOutcomes:
    def test_resolved_carries_text_and_a_version(self, domain_meta):
        (domain_meta / ".domain" / "setup.md").write_text(
            "---\nprovenance: repo:x\n---\n# Setup\n\n- Run bootstrap\n",
            encoding="utf-8")
        result = retrieval.fetch("domain://acme/setup.md", trace=False)
        assert result.status == retrieval.RESOLVED
        assert "provenance" not in result.text     # frontmatter is metadata
        assert "Run bootstrap" in result.text
        assert result.version                      # the differ needs this half

    def test_missing_when_the_source_answered_and_had_nothing(self, domain_meta):
        result = retrieval.fetch("domain://acme/absent.md", trace=False)
        assert result.status == retrieval.MISSING
        assert result.known                        # we learned something

    def test_unavailable_when_we_could_not_ask(self, domain_meta):
        """A domain with no meta-repo is unknown, not empty.

        This is the distinction the whole module is for: reporting it as empty
        would let an instruction be flagged absent because a checkout was
        missing.
        """
        result = retrieval.fetch("domain://nosuchdomain/setup.md", trace=False)
        assert result.status == retrieval.UNAVAILABLE
        assert not result.known

    def test_refused_when_we_found_content_and_declined(self, domain_meta):
        """Scaffold filler is a decision, not an absence."""
        (domain_meta / ".domain" / "architecture.md").write_text(
            "# Architecture\n\n_Architecture details will be populated from the "
            "Knowledge Graph._\n", encoding="utf-8")
        result = retrieval.fetch("domain://acme/architecture.md", trace=False)
        assert result.status == retrieval.REFUSED
        assert result.text == ""
        assert "placeholder" in result.detail.lower()

    def test_a_ref_cannot_escape_its_root(self, domain_meta):
        """A ref is caller-supplied; '../../.ssh/id_rsa' is a context ref too."""
        (domain_meta.parent / "secret.txt").write_text("do not read me",
                                                       encoding="utf-8")
        result = retrieval.fetch("domain://acme/../../secret.txt", trace=False)
        assert result.status == retrieval.REFUSED
        assert "do not read me" not in result.text


# ── staleness ───────────────────────────────────────────────────────────────

class TestStaleness:
    @staticmethod
    def _repo(tmp_path, monkeypatch, body="original\n"):
        from agentic_cli import persona_workspace as pw

        (tmp_path / "svc").mkdir(exist_ok=True)
        (tmp_path / "svc" / "CONTRIBUTING.md").write_text(body, encoding="utf-8")
        monkeypatch.setattr(pw, "store_repo_path", lambda slug: tmp_path / slug)
        return tmp_path / "svc" / "CONTRIBUTING.md"

    def test_unchanged_source_is_not_stale(self, tmp_path, monkeypatch):
        from agentic_cli.onboarding import sources

        self._repo(tmp_path, monkeypatch)
        cited = sources.content_version("original\n")
        assert retrieval.is_stale("repo:svc/CONTRIBUTING.md", cited) is False

    def test_the_version_can_ride_on_the_ref(self, tmp_path, monkeypatch):
        """A Citation serialises to scheme:ref@version — accept it whole."""
        from agentic_cli.onboarding import sources

        path = self._repo(tmp_path, monkeypatch)
        cited = sources.content_version("original\n")
        path.write_text("changed\n", encoding="utf-8")
        assert retrieval.is_stale(f"repo:svc/CONTRIBUTING.md@{cited}") is True

    def test_no_cited_version_is_unknown(self, tmp_path, monkeypatch):
        self._repo(tmp_path, monkeypatch)
        assert retrieval.is_stale("repo:svc/CONTRIBUTING.md", "") is None

    def test_an_unreachable_source_is_unknown_not_stale(self, tmp_path, monkeypatch):
        from agentic_cli import persona_workspace as pw

        monkeypatch.setattr(pw, "store_repo_path", lambda slug: tmp_path / slug)
        assert retrieval.is_stale("repo:gone/CONTRIBUTING.md", "abc123") is None

    def test_a_scheme_with_no_version_is_unknown_rather_than_fresh(
            self, monkeypatch):
        monkeypatch.setitem(
            retrieval._FETCHERS, "versionless",
            lambda ref: retrieval.Fetched(ref=str(ref), scheme="versionless",
                                          status=retrieval.RESOLVED, text="body"))
        assert retrieval.is_stale("versionless:x", "abc") is None

    def test_a_staleness_check_does_not_write_to_the_ledger(
            self, tmp_path, monkeypatch):
        """Bookkeeping reads serve no context, and the pollers run constantly."""
        from agentic_cli import tracing
        from agentic_cli.onboarding import sources

        self._repo(tmp_path, monkeypatch)
        recorded = []
        monkeypatch.setattr(tracing, "record_context_read",
                            lambda **kw: recorded.append(kw))
        retrieval.is_stale("repo:svc/CONTRIBUTING.md",
                           sources.content_version("original\n"))
        assert recorded == []


# ── tracing ─────────────────────────────────────────────────────────────────

class TestTracing:
    def test_one_row_per_fetch_naming_the_scheme(self, monkeypatch, domain_meta):
        from agentic_cli import tracing

        (domain_meta / ".domain" / "setup.md").write_text("body\n", encoding="utf-8")
        recorded = []
        monkeypatch.setattr(tracing, "record_context_read",
                            lambda **kw: recorded.append(kw))

        retrieval.fetch("domain://acme/setup.md")
        assert len(recorded) == 1
        assert recorded[0]["operation"] == "resolve/domain"
        assert recorded[0]["source"] == retrieval.CONTEXT_SOURCE

    def test_the_caller_names_the_ledger_family(self, monkeypatch, domain_meta):
        """An extraction read is not context put in front of an agent.

        Filing it under ``context`` would put every page `domain extract` reads
        into the eval feed's idea of what a coding session was given.
        """
        from agentic_cli import tracing

        recorded = []
        monkeypatch.setattr(tracing, "record_context_read",
                            lambda **kw: recorded.append(kw))
        retrieval.fetch("domain://acme/setup.md",
                        source=retrieval.ONBOARDING_SOURCE,
                        operation_prefix="read")
        assert recorded[0]["source"] == retrieval.ONBOARDING_SOURCE
        assert recorded[0]["operation"] == "read/domain"

    def test_a_failure_to_record_never_breaks_the_fetch(
            self, monkeypatch, domain_meta):
        from agentic_cli import tracing

        (domain_meta / ".domain" / "setup.md").write_text("body\n", encoding="utf-8")

        def explode(**kw):
            raise RuntimeError("ledger is down")

        monkeypatch.setattr(tracing, "record_context_read", explode)
        with pytest.raises(RuntimeError):
            tracing.record_context_read()          # the stub really does raise
        # ...and the fetch still returns its content.
        assert retrieval.fetch("domain://acme/setup.md").resolved
