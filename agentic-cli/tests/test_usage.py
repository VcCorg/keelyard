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
