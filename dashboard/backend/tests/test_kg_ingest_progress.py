"""Progress parser for KG ingest CLI output.

The UI depends on typed `progress` events to draw a real progress bar, so
we pin the behaviour of ProgressParser here — regex changes downstream can
silently downgrade the UX otherwise.
"""

from src.services.kg_ingest_progress import (
    PHASE_DONE,
    PHASE_FETCH,
    PHASE_INGEST_DOCS,
    PHASE_INGEST_GENERIC,
    ProgressParser,
)


def _feed_all(parser: ProgressParser, lines: list[str]):
    """Feed a batch and return the sequence of emitted events (skip Nones)."""
    events = []
    for line in lines:
        e = parser.feed(line)
        if e is not None:
            events.append(e)
    return events


def test_domain_flow_end_to_end():
    """The full domain flow: fetch → found N → per-doc ticks → tally → done."""
    parser = ProgressParser()
    events = _feed_all(parser, [
        "Fetching tracked docs for domain 'cwow-facility'...",
        "Found 3 tracked docs, ingesting to Neo4j...",
        "  ✓ Page One",
        "  ✓ Page Two",
        "  ⚠ Page Three: connection dropped",
        "Documents processed: 2/3",
        "✓ Successfully ingested domain docs",
    ])
    phases = [e.phase for e in events]
    assert PHASE_FETCH in phases
    assert PHASE_INGEST_DOCS in phases
    assert PHASE_DONE in phases

    # The last event should be the completion snapshot; DONE snaps current==total
    # so the UI's progress bar renders as 100% at the end.
    last = events[-1]
    assert last.phase == PHASE_DONE
    assert last.total == 3
    assert last.current == 3

    # The last INGEST_DOCS event reflects the CLI's tally line (2 succeeded,
    # 1 failed — the CLI reports 2/3 progress, not 3/3, so the progress bar
    # matches what the user sees mid-run).
    docs_events = [e for e in events if e.phase == PHASE_INGEST_DOCS]
    final_docs = docs_events[-1]
    assert final_docs.total == 3
    assert final_docs.current == 2


def test_generic_flow_indeterminate():
    """Non-domain ingest: we know the phase but not the total; total stays 0."""
    parser = ProgressParser()
    events = _feed_all(parser, [
        "Ingesting data from /tmp/data.pdf...",
    ])
    assert any(e.phase == PHASE_INGEST_GENERIC for e in events)
    for e in events:
        assert e.total == 0  # indeterminate — UI shows animated bar


def test_rich_tags_are_stripped():
    """Rich [color] tags leak through under some terminals; parser must handle."""
    parser = ProgressParser()
    e = parser.feed("[green]Found[/green] 7 tracked docs, ingesting to Neo4j...")
    assert e is not None
    assert e.total == 7
    assert e.phase == PHASE_INGEST_DOCS


def test_no_double_emit_when_state_unchanged():
    """Identical noise lines don't spam the UI with duplicate events."""
    parser = ProgressParser()
    e1 = parser.feed("Found 5 tracked docs, ingesting to Neo4j...")
    e2 = parser.feed("(some benign log line the parser ignores)")
    e3 = parser.feed("Found 5 tracked docs, ingesting to Neo4j...")
    assert e1 is not None and e1.total == 5
    assert e2 is None
    # Re-encountering the same "Found N" line without any state change
    # shouldn't produce a duplicate event.
    assert e3 is None


def test_elapsed_grows_monotonically():
    """elapsed_ms is monotonically non-decreasing across events."""
    parser = ProgressParser()
    e1 = parser.feed("Fetching tracked docs for domain 'x'...")
    e2 = parser.feed("Found 2 tracked docs, ingesting to Neo4j...")
    assert e1 is not None and e2 is not None
    assert e2.elapsed_ms >= e1.elapsed_ms
