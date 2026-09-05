"""Tests for per-project token attribution — L0 (domain) and L1 (tokens).

Three tests here carry the design and the rest is ordinary behaviour.

``test_a_token_count_never_arrives_without_its_basis`` is the whole point of the
``token_basis`` column: most models have no tokenizer we can run, so most counts
are estimates, and a ledger that cannot say which is which can only be quoted
carelessly.

``test_unattributed_work_is_counted_not_dropped`` — work that belongs to no
project is real spend, and hiding it makes the totals disagree with the ledger.

``test_building_and_serving_are_separate_meters`` — one total cannot tell a
project three days into onboarding from one running daily off finished context.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from agentic_cli import tokens, usage


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    from agentic_cli import tracker

    db_dir = tmp_path / ".keel-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    tracker._ensure_db()
    yield db_dir


def _read(domain, source, text, operation="resolve/domain"):
    from agentic_cli import tracing

    tracing.record_context_read(
        source=source, operation=operation, entity_id="ref",
        size_bytes=len(text.encode()), payload=text, domain=domain)


# ── the token counter ───────────────────────────────────────────────────────

class TestTokens:
    def test_a_count_always_says_how_it_was_reached(self):
        counted = tokens.count("Run ./setup.sh before your first build")
        assert counted.tokens > 0
        assert counted.basis in (tokens.MEASURED, tokens.ESTIMATED)

    def test_an_unknown_model_estimates_rather_than_failing(self):
        counted = tokens.count("hello world", "some-model-we-cannot-tokenize")
        assert counted.basis == tokens.ESTIMATED
        assert not counted.measured

    def test_the_estimate_does_not_collapse_on_short_tokens(self):
        """A runbook is mostly flags and paths, where chars/4 undercounts badly."""
        listy = "- --clean\n- --no-cache\n- -v\n- -x\n- --dry-run\n"
        assert tokens.estimate(listy) >= len(listy.split())

    def test_empty_text_is_zero_and_that_is_measured(self):
        counted = tokens.count("")
        assert counted.tokens == 0 and counted.measured

    def test_a_mixed_total_says_so(self):
        note = tokens.summarise({tokens.MEASURED: 3, tokens.ESTIMATED: 7})
        assert "not a bill" in note


# ── the ledger columns ──────────────────────────────────────────────────────

class TestLedger:
    def test_a_read_records_its_project_and_token_count(self, temp_db):
        from agentic_cli import tracker

        _read("titanic", "context", "Run ./setup.sh before your first build")
        conn = sqlite3.connect(str(tracker.DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT domain, bytes, tokens, token_basis FROM activity_log"
        ).fetchone()
        assert row["domain"] == "titanic"
        assert row["bytes"] > 0 and row["tokens"] > 0
        assert row["token_basis"] == tokens.ESTIMATED

    def test_a_token_count_never_arrives_without_its_basis(self, temp_db):
        """A number whose provenance was dropped can only be quoted carelessly."""
        from agentic_cli import tracker

        tracker.record_activity("context", "resolve/domain", entity_type="context",
                                tokens=500, token_basis=None)
        conn = sqlite3.connect(str(tracker.DB_PATH))
        assert conn.execute("SELECT tokens FROM activity_log").fetchone()[0] is None

    def test_the_bound_project_attributes_reads_made_further_down(self, temp_db):
        """Nothing on the way down has to pass the project name.

        The read that matters happens inside a fetcher, several frames from the
        command that knows which project this is.
        """
        from agentic_cli import tracker, tracing

        with tracing.session_scope(domain="house-prices"):
            _read(None, "context", "Impute Age before modelling")
        conn = sqlite3.connect(str(tracker.DB_PATH))
        assert conn.execute("SELECT domain FROM activity_log").fetchone()[0] == \
            "house-prices"

    def test_size_without_text_gets_no_token_count(self, temp_db):
        """Bytes-to-tokens would stack a second estimate on the first."""
        from agentic_cli import tracker, tracing

        tracing.record_context_read(source="mcp", operation="jira/get_issue",
                                    size_bytes=4096, domain="titanic")
        conn = sqlite3.connect(str(tracker.DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT bytes, tokens FROM activity_log").fetchone()
        assert row["bytes"] == 4096
        assert row["tokens"] is None

    def test_the_binding_does_not_leak_past_its_block(self, temp_db):
        from agentic_cli import tracing

        with tracing.session_scope(domain="titanic"):
            assert tracing.current_domain() == "titanic"
        assert tracing.current_domain() is None


# ── the migration ───────────────────────────────────────────────────────────

class TestMigration:
    def test_historical_bytes_are_backfilled_from_the_details_json(self, tmp_path,
                                                                   monkeypatch):
        """Otherwise the first report understates history by all of it."""
        from agentic_cli import tracker

        db = tmp_path / "old.db"
        conn = sqlite3.connect(str(db))
        conn.executescript("""
            CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
            CREATE TABLE activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                command TEXT NOT NULL, subcommand TEXT,
                status TEXT NOT NULL DEFAULT 'success', duration_ms INTEGER,
                args TEXT, details TEXT, repo_path TEXT, correlation_id TEXT,
                entity_type TEXT, entity_id TEXT, source TEXT DEFAULT 'cli',
                actor TEXT);
            INSERT INTO schema_version VALUES (14);
        """)
        conn.execute("INSERT INTO activity_log (timestamp, command, details)"
                     " VALUES ('2026-01-01T00:00:00Z','context',?)",
                     (json.dumps({"bytes": 1200}),))
        # Unparseable details must survive rather than take the migration down.
        conn.execute("INSERT INTO activity_log (timestamp, command, details)"
                     " VALUES ('2026-01-02T00:00:00Z','kg','not json')")
        conn.commit()
        conn.close()

        monkeypatch.setattr(tracker, "DB_DIR", tmp_path)
        monkeypatch.setattr(tracker, "DB_PATH", db)
        tracker._ensure_db()

        conn = sqlite3.connect(str(db))
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] \
            == tracker._SCHEMA_VERSION
        rows = conn.execute("SELECT command, bytes FROM activity_log "
                            "ORDER BY id").fetchall()
        assert rows == [("context", 1200), ("kg", None)]

    def test_a_fresh_install_has_the_indexes_the_migrations_create(self, temp_db):
        """A fresh install skips the whole migration chain.

        It stamps the current version and runs none of the scripts, so every
        index added since v13 was missing on exactly the installs most likely to
        grow large — including the one the portfolio query was added for. They
        are created after the chain now, which is the one point where every
        column exists on every path.
        """
        import sqlite3

        from agentic_cli import tracker

        conn = sqlite3.connect(str(tracker.DB_PATH))
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        assert {"idx_activity_domain", "idx_activity_domain_entity",
                "idx_activity_generation", "idx_domain_docs_type",
                "idx_activity_actor"} <= indexes

    def test_a_fresh_install_has_the_same_columns_as_a_migrated_one(self, temp_db):
        from agentic_cli import tracker

        conn = sqlite3.connect(str(tracker.DB_PATH))
        columns = {r[1] for r in conn.execute("PRAGMA table_info(activity_log)")}
        assert {"domain", "bytes", "tokens", "token_basis"} <= columns


# ── the rollup ──────────────────────────────────────────────────────────────

class TestRollup:
    def test_building_and_serving_are_separate_meters(self, temp_db):
        """Identical totals, opposite situations — only the split tells them apart."""
        _read("titanic", "onboarding", "x" * 400, operation="read/repo")
        _read("titanic", "context", "y" * 100)
        [project] = usage.by_project(domain="titanic")
        assert project.meter(usage.BUILD).tokens > project.meter(usage.SERVE).tokens
        assert 0 < project.build_share < 1

    def test_projects_sort_by_spend(self, temp_db):
        _read("titanic", "context", "y" * 4000)
        _read("house-prices", "context", "y" * 100)
        assert [p.domain for p in usage.by_project()] == ["titanic", "house-prices"]

    def test_unattributed_work_is_counted_not_dropped(self, temp_db):
        """Hiding it makes the totals disagree with the ledger they came from."""
        _read("titanic", "context", "y" * 100)
        _read(None, "context", "y" * 100)
        projects = usage.by_project()
        assert "" in {p.domain for p in projects}
        assert next(p for p in projects if not p.domain).named == "(unattributed)"

    def test_a_project_that_has_spent_nothing_has_no_build_ratio(self):
        """0% would read as 'all of this was serve cost' — a claim about nothing."""
        assert usage.ProjectUsage(domain="new").build_share is None

    def test_an_unclassified_source_is_misfiled_rather_than_lost(self, temp_db):
        """An under-reported cost is the failure mode that goes unnoticed."""
        _read("titanic", "some-future-retrieval-path", "y" * 100)
        [project] = usage.by_project(domain="titanic")
        assert project.tokens > 0
        assert usage.TOOLS in project.meters

    def test_the_portfolio_note_names_the_basis(self, temp_db):
        _read("titanic", "context", "y" * 100)
        assert "estimated" in usage.compare(usage.by_project())["basis_note"]


# ── tool and search coverage ────────────────────────────────────────────────

class TestToolCoverage:
    """Tool reads used to record a size and no tokens, so the meter read zero.

    A cost table is exactly where a zero is taken to mean "free", and the tools
    meter is where the largest single read in a session usually lands.
    """

    def test_a_tool_result_is_counted_in_tokens(self, temp_db):
        from agentic_cli import tracing

        with tracing.session_scope(domain="titanic"):
            tracing.record_context_read(
                source="mcp", operation="jira/get_issue", size_bytes=4096,
                payload="ticket body " * 340)
        [project] = usage.by_project(domain="titanic")
        meter = project.meter(usage.TOOLS)
        assert meter.tokens > 0
        assert meter.complete

    def test_an_uncounted_read_is_not_reported_as_free(self, temp_db):
        from agentic_cli import tracing

        with tracing.session_scope(domain="titanic"):
            tracing.record_context_read(source="mcp", operation="confluence/get_page",
                                        size_bytes=9000)
        [project] = usage.by_project(domain="titanic")
        meter = project.meter(usage.TOOLS)
        assert meter.uncounted == 1
        assert not meter.complete
        assert meter.basis == "uncounted"
        assert not project.complete

    def test_partial_coverage_says_how_partial(self, temp_db):
        from agentic_cli import tracing

        with tracing.session_scope(domain="titanic"):
            tracing.record_context_read(source="mcp", operation="a", size_bytes=10,
                                        payload="counted text here")
            tracing.record_context_read(source="mcp", operation="b", size_bytes=10)
        [project] = usage.by_project(domain="titanic")
        assert project.meter(usage.TOOLS).basis == "partial (1/2)"

    def test_the_portfolio_note_leads_with_incomplete_coverage(self, temp_db):
        """Incomplete coverage outranks how the counted part was reached."""
        from agentic_cli import tracing

        with tracing.session_scope(domain="titanic"):
            tracing.record_context_read(source="mcp", operation="a", size_bytes=10)
        note = usage.compare(usage.by_project())["basis_note"]
        assert note.startswith("1 read(s) contributed no token count")
        assert "floor" in note


class TestAsText:
    def test_a_dict_result_becomes_the_text_an_agent_would_see(self):
        from agentic_cli import tracing

        assert tracing.as_text({"body": "hello"}) == '{"body": "hello"}'

    def test_a_string_passes_through(self):
        from agentic_cli import tracing

        assert tracing.as_text("plain") == "plain"

    def test_an_unserialisable_value_counts_as_no_text(self):
        """Which records as uncounted, not as zero."""
        from agentic_cli import tracing

        class Hostile:
            def __repr__(self):
                raise RuntimeError("no")

        assert tracing.as_text(Hostile()) == ""


class TestSearchSeam:
    """KG, LightRAG, Neo4j and Glean recorded nothing at all before this."""

    def test_a_search_is_recorded_and_its_result_returned(self, temp_db):
        from agentic_cli import retrieval, tracing

        with tracing.session_scope(domain="titanic"):
            out = retrieval.search("lightrag", "query/hybrid",
                                   lambda: {"results": [{"text": "chunk " * 50}]},
                                   query="how do I deploy")
        assert out["results"]
        [project] = usage.by_project(domain="titanic")
        assert project.meter(usage.TOOLS).tokens > 0

    def test_the_query_text_is_fingerprinted_never_stored(self, temp_db):
        """A search string has the same disclosure profile as tool arguments."""
        import sqlite3

        from agentic_cli import retrieval, tracker, tracing

        secret = "why did acmecorp-internal-host reject my token"
        with tracing.session_scope(domain="titanic"):
            retrieval.search("glean", "search", lambda: [], query=secret)
        conn = sqlite3.connect(str(tracker.DB_PATH))
        blob = " ".join(str(v) for row in conn.execute(
            "SELECT * FROM activity_log") for v in row)
        assert "acmecorp-internal-host" not in blob

    def test_a_failed_search_is_recorded_then_re_raised(self, temp_db):
        """A search that failed still cost a round trip."""
        import sqlite3

        from agentic_cli import retrieval, tracker, tracing

        def boom():
            raise RuntimeError("the index is down")

        with tracing.session_scope(domain="titanic"):
            with pytest.raises(RuntimeError):
                retrieval.search("lightrag", "query/hybrid", boom)
        conn = sqlite3.connect(str(tracker.DB_PATH))
        assert conn.execute(
            "SELECT status FROM activity_log").fetchone()[0] == "error"

    def test_hits_are_recorded_beside_the_size(self, temp_db):
        """Bytes say what it cost; hits say whether it found anything."""
        import json as _json
        import sqlite3

        from agentic_cli import retrieval, tracker, tracing

        with tracing.session_scope(domain="titanic"):
            retrieval.search("lightrag", "search",
                             lambda: {"results": [1, 2, 3]}, query="q")
        conn = sqlite3.connect(str(tracker.DB_PATH))
        details = _json.loads(conn.execute(
            "SELECT details FROM activity_log").fetchone()[0])
        assert details["hits"] == 3

    def test_a_renderer_decides_what_text_is_counted(self, temp_db):
        """A client returning parsed objects must not be counted on their repr."""
        from agentic_cli import retrieval, tracing

        class Hit:
            def as_text(self):
                return "the body an agent actually receives " * 20

        with tracing.session_scope(domain="titanic"):
            retrieval.search(
                "glean", "search", lambda: [Hit(), Hit()], query="q",
                text_of=lambda hits: "\n\n".join(h.as_text() for h in hits))
        [project] = usage.by_project(domain="titanic")
        assert project.meter(usage.TOOLS).tokens > 100

    def test_a_broken_renderer_falls_back_rather_than_failing_the_search(
            self, temp_db):
        from agentic_cli import retrieval, tracing

        def bad(_):
            raise ValueError("renderer is wrong")

        with tracing.session_scope(domain="titanic"):
            out = retrieval.search("glean", "search", lambda: [{"a": 1}],
                                   query="q", text_of=bad)
        assert out == [{"a": 1}]
        [project] = usage.by_project(domain="titanic")
        assert project.meter(usage.TOOLS).reads == 1


class TestIngestionIsNotARead:
    def test_graph_writes_are_not_filed_as_context_reads(self):
        """Ingestion is text going *into* the graph, not context served from it.

        Tracing both would double-count the same knowledge on the way in and the
        way out, and inflate a project's serve cost with the cost of building it.
        """
        import inspect

        from agentic_cli.kg import neo4j_client

        source = inspect.getsource(neo4j_client.Neo4jClient)
        assert "retrieval.search" in source            # the read path is traced
        for writer in ("create_node", "create_relationship"):
            body = inspect.getsource(getattr(neo4j_client.Neo4jClient, writer))
            assert "retrieval.search" not in body


# ── generation (L2) ─────────────────────────────────────────────────────────

class _Reporting:
    """A provider whose SDK hands back usage, as the real ones do."""

    def __init__(self, usage=None):
        from agentic_cli.llm.base import Usage

        self._usage = usage if usage is not None else Usage(
            input_tokens=900, output_tokens=1400, cache_read_tokens=4000,
            model="claude-sonnet-5")

    def generate(self, prompt):
        return "the reply " * 40

    def get_name(self):
        return "claude-sonnet-5"

    def last_usage(self):
        return self._usage


class _Silent:
    """A provider that cannot report — a local model, a stub."""

    def generate(self, prompt):
        return "a local reply " * 20

    def get_name(self):
        return "local/tiny"


class TestGeneration:
    def test_reported_usage_is_recorded_as_measured(self, temp_db):
        from agentic_cli import tracing
        from agentic_cli.llm.factory import _MeteredProvider

        with tracing.session_scope(domain="titanic"):
            _MeteredProvider(_Reporting()).generate("prompt " * 50)
        [project] = usage.by_project(domain="titanic")
        meter = project.meter(usage.GENERATE)
        assert meter.tokens == 4900        # 900 input + 4000 cache read
        assert meter.tokens_out == 1400
        assert meter.basis == "measured"

    def test_cached_input_counts_toward_what_the_model_read(self, temp_db):
        """A cached token was still read. Excluding it understates the context.

        The split is kept in the details for pricing, where a cache read is
        billed at a fraction — but "how much did the model see" is the sum.
        """
        from agentic_cli.llm.base import Usage

        u = Usage(input_tokens=100, output_tokens=10, cache_read_tokens=5000)
        assert u.admitted == 5100

    def test_a_provider_that_cannot_report_still_shows_as_spend(self, temp_db):
        """A meter reading zero for a run that plainly did work is the failure."""
        from agentic_cli import tracing
        from agentic_cli.llm.factory import _MeteredProvider

        with tracing.session_scope(domain="titanic"):
            _MeteredProvider(_Silent()).generate("prompt " * 50)
        [project] = usage.by_project(domain="titanic")
        meter = project.meter(usage.GENERATE)
        assert meter.tokens > 0 and meter.tokens_out > 0
        assert meter.basis == "estimated"   # and it says so

    def test_a_failed_call_is_recorded_then_re_raised(self, temp_db):
        """A flaky provider must not look like an unused one."""
        import sqlite3

        from agentic_cli import tracing, tracker
        from agentic_cli.llm.factory import _MeteredProvider

        class Broken:
            def generate(self, prompt):
                raise RuntimeError("rate limited")

            def get_name(self):
                return "claude-sonnet-5"

        with tracing.session_scope(domain="titanic"):
            with pytest.raises(RuntimeError):
                _MeteredProvider(Broken()).generate("prompt")
        conn = sqlite3.connect(str(tracker.DB_PATH))
        assert conn.execute("SELECT status FROM activity_log "
                            "WHERE entity_type='generation'").fetchone()[0] == "error"

    def test_generation_never_lands_in_the_context_ledger(self, temp_db):
        """Adding served context and prompt tokens double-counts the same text."""
        from agentic_cli import tracing
        from agentic_cli.llm.factory import _MeteredProvider

        with tracing.session_scope(domain="titanic"):
            tracing.record_context_read(source="context", operation="resolve/domain",
                                        size_bytes=100, payload="x" * 100)
            _MeteredProvider(_Reporting()).generate("prompt")
        import sqlite3

        from agentic_cli import tracker

        conn = sqlite3.connect(str(tracker.DB_PATH))
        kinds = {r[0] for r in conn.execute(
            "SELECT DISTINCT entity_type FROM activity_log")}
        assert kinds == {"context", "generation"}

        project = usage.by_project(domain="titanic")[0]
        assert project.meter(usage.SERVE).tokens > 0
        assert project.meter(usage.GENERATE).tokens > 0
        # Separate meters, so nothing sums them into one "context" figure.
        assert project.admitted == project.meter(usage.GENERATE).tokens

    def test_the_wrapper_is_transparent(self, temp_db):
        """A caller sees the provider it asked for, sensor or no sensor."""
        from agentic_cli.llm.factory import _MeteredProvider

        inner = _Reporting()
        wrapped = _MeteredProvider(inner)
        assert wrapped.get_name() == inner.get_name()
        assert wrapped.last_usage() == inner.last_usage()

    def test_build_share_ignores_model_calls(self, temp_db):
        """A prompt is largely the served context again; folding it in
        double-counts and shrinks the ratio for purely arithmetic reasons."""
        from agentic_cli import tracing
        from agentic_cli.llm.factory import _MeteredProvider

        with tracing.session_scope(domain="titanic"):
            tracing.record_context_read(source="onboarding", operation="read/repo",
                                        size_bytes=400, payload="d" * 400)
            tracing.record_context_read(source="context", operation="resolve/domain",
                                        size_bytes=400, payload="c" * 400)
            before = usage.by_project(domain="titanic")[0].build_share
            _MeteredProvider(_Reporting()).generate("prompt " * 500)
        after = usage.by_project(domain="titanic")[0].build_share
        assert before == after


# ── pricing (L3) ────────────────────────────────────────────────────────────

class TestRateCard:
    """Keel ships no prices. A wrong price is worse than no price."""

    def test_no_card_configured_means_costing_is_off(self, tmp_path, monkeypatch):
        from agentic_cli import pricing

        monkeypatch.setenv(pricing.ENV_RATE_CARD, str(tmp_path / "absent.yaml"))
        card = pricing.load()
        assert not card.configured
        assert card.stale                  # undated, so never quotable

    def test_the_shipped_example_is_data_not_a_default(self, tmp_path, monkeypatch):
        """It exists, it is dated — and it is not what `load()` picks up."""
        from agentic_cli import pricing

        monkeypatch.setenv(pricing.ENV_RATE_CARD, str(tmp_path / "absent.yaml"))
        assert not pricing.load().configured
        example = pricing.load(pricing.example_path())
        assert example.configured and example.as_of is not None

    def test_an_undated_card_is_stale(self, tmp_path):
        """Undated is not fresh — it is a card nobody can reason about."""
        from agentic_cli import pricing

        path = tmp_path / "rates.yaml"
        path.write_text("models:\n  m:\n    input_per_mtok: 1.0\n", encoding="utf-8")
        assert pricing.load(path).stale

    def test_an_old_card_is_stale(self, tmp_path):
        from datetime import date, timedelta

        from agentic_cli import pricing

        old = (date.today() - timedelta(days=pricing.STALE_AFTER_DAYS + 1))
        path = tmp_path / "rates.yaml"
        path.write_text(f"as_of: {old.isoformat()}\nmodels:\n  m:\n"
                        f"    input_per_mtok: 1.0\n", encoding="utf-8")
        assert pricing.load(path).stale

    def test_unreadable_yaml_yields_no_card_not_a_partial_one(self, tmp_path):
        """A card that silently dropped a model prices that model at nothing."""
        from agentic_cli import pricing

        path = tmp_path / "rates.yaml"
        path.write_text("models: [this is not: a mapping\n", encoding="utf-8")
        assert not pricing.load(path).configured

    def test_a_malformed_entry_is_left_out_rather_than_zeroed(self, tmp_path):
        from agentic_cli import pricing

        path = tmp_path / "rates.yaml"
        path.write_text(
            "as_of: 2026-06-24\nmodels:\n"
            "  good:\n    input_per_mtok: 1.0\n    output_per_mtok: 2.0\n"
            "  bad:\n    input_per_mtok: not-a-number\n", encoding="utf-8")
        card = pricing.load(path)
        assert card.rate_for("good") is not None
        assert card.rate_for("bad") is None      # unpriced, never free


class TestRateMatching:
    @staticmethod
    def _card():
        from agentic_cli import pricing

        return pricing.load(pricing.example_path())

    def test_a_provider_prefix_still_matches(self):
        """get_name() returns whatever the provider calls itself."""
        assert self._card().rate_for("anthropic/claude-sonnet-5").model == \
            "claude-sonnet-5"

    def test_a_date_suffix_still_matches(self):
        assert self._card().rate_for("claude-opus-5-20260401").model == \
            "claude-opus-5"

    def test_the_longest_configured_id_wins(self, tmp_path):
        """With both a family and a specific id, the specific one must price it."""
        from agentic_cli import pricing

        path = tmp_path / "rates.yaml"
        path.write_text(
            "as_of: 2026-06-24\nmodels:\n"
            "  claude-opus:\n    input_per_mtok: 99.0\n"
            "  claude-opus-5:\n    input_per_mtok: 5.0\n", encoding="utf-8")
        assert pricing.load(path).rate_for("claude-opus-5").input_per_mtok == 5.0

    def test_an_unknown_model_has_no_rate(self):
        assert self._card().rate_for("some-local-model") is None


class TestCostArithmetic:
    def test_cache_reads_and_writes_are_priced_apart_from_fresh_input(self):
        """A cost off the admitted total alone is wrong in both directions."""
        from agentic_cli import pricing

        rate = pricing.ModelRate("m", input_per_mtok=10.0, output_per_mtok=50.0)
        # Defaults: read at a tenth, write at a premium.
        assert rate.cache_read == 1.0
        assert rate.cache_write == 12.5
        cost = rate.cost(input_tokens=1_000_000, cache_read_tokens=1_000_000,
                         cache_write_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == pytest.approx(10.0 + 1.0 + 12.5 + 50.0)

    def test_an_explicit_cache_rate_beats_the_multiplier(self):
        """Multipliers are fallbacks — a model can price reads far below a tenth."""
        from agentic_cli import pricing

        rate = pricing.ModelRate("m", input_per_mtok=10.0,
                                 cache_read_per_mtok=0.25)
        assert rate.cache_read == 0.25

    def test_an_unpriced_model_is_counted_not_costed_at_zero(self):
        """A total that silently omits a model reads as a cheaper project."""
        from agentic_cli import pricing

        card = pricing.load(pricing.example_path())
        priced = pricing.price([
            {"model": "claude-opus-5", "calls": 1, "input_tokens": 1_000_000},
            {"model": "mystery-model", "calls": 3, "input_tokens": 9_000_000},
        ], card)
        assert priced.cost == pytest.approx(5.0)
        assert priced.unpriced_calls == 3
        assert priced.unpriced_models == ("mystery-model",)
        assert not priced.complete


class TestPhaseSplit:
    """Building a context and working with it both spend real money."""

    @staticmethod
    def _call(domain, phase, model="claude-opus-5"):
        from agentic_cli import tracing
        from agentic_cli.llm.base import Usage
        from agentic_cli.llm.factory import _MeteredProvider

        class P:
            def generate(self, prompt):
                return "reply " * 20

            def get_name(self):
                return model

            def last_usage(self):
                return Usage(input_tokens=1000, output_tokens=500,
                             cache_read_tokens=4000, model=model)

        with tracing.session_scope(domain=domain, phase=phase):
            _MeteredProvider(P()).generate("prompt")

    def test_build_and_develop_are_costed_separately(self, temp_db):
        from agentic_cli import pricing, tracing

        self._call("titanic", tracing.BUILD)
        for _ in range(3):
            self._call("titanic", tracing.DEVELOP)

        report = usage.cost_by_project(
            domain="titanic", card=pricing.load(pricing.example_path()))
        phases = {p.phase: p for p in report["projects"]["titanic"]}
        assert phases["build"].calls == 1
        assert phases["develop"].calls == 3
        assert phases["develop"].cost > phases["build"].cost

    def test_the_cache_split_survives_to_the_cost_query(self, temp_db):
        """Recorded apart, aggregated apart — the whole reason for the columns."""
        from agentic_cli import tracing
        from agentic_cli.tracker import generation_by_model

        self._call("titanic", tracing.DEVELOP)
        [row] = generation_by_model(domain="titanic")
        assert row["cache_read_tokens"] == 4000
        assert row["input_tokens"] == 1000        # admitted minus the cached part
        assert row["output_tokens"] == 500

    def test_retrieval_is_never_priced(self, temp_db):
        """Nobody bills for reading a file. Context becomes money when a model
        reads it, which is the generation row."""
        from agentic_cli import pricing, tracing

        with tracing.session_scope(domain="titanic", phase=tracing.DEVELOP):
            tracing.record_context_read(source="context", operation="resolve/domain",
                                        size_bytes=4000, payload="x" * 4000)
        report = usage.cost_by_project(
            domain="titanic", card=pricing.load(pricing.example_path()))
        assert report["projects"] == {}       # tokens recorded, nothing billable

    def test_cost_is_not_stored_so_a_new_card_reprices_history(self, temp_db):
        """Rates change. A cost frozen at record time can never be corrected."""
        import sqlite3

        from agentic_cli import pricing, tracing, tracker

        self._call("titanic", tracing.DEVELOP)
        conn = sqlite3.connect(str(tracker.DB_PATH))
        columns = {r[1] for r in conn.execute("PRAGMA table_info(activity_log)")}
        assert "cost" not in columns

        cheap = pricing.RateCard(models={"claude-opus-5": pricing.ModelRate(
            "claude-opus-5", input_per_mtok=1.0, output_per_mtok=1.0)})
        dear = pricing.RateCard(models={"claude-opus-5": pricing.ModelRate(
            "claude-opus-5", input_per_mtok=100.0, output_per_mtok=100.0)})
        low = usage.cost_by_project(domain="titanic", card=cheap)
        high = usage.cost_by_project(domain="titanic", card=dear)
        assert high["projects"]["titanic"][0].cost > \
            low["projects"]["titanic"][0].cost * 50
