"""KG-ingest progress extractor.

The CLI (`keel kg ingest submit ...`) emits Rich-styled log lines to stdout;
that's the only thing the streaming SSE endpoint sees. To surface a real
progress bar in the UI without touching the CLI, we scan those lines for
known markers and translate them into typed progress events:

    {phase, current, total, message, elapsed_ms}

The parser is deliberately narrow — it only fires on high-confidence signals
so a phrasing change downgrades us to "no progress bar" rather than to a
wrong one. All parsing lives here (single place to test / evolve).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional


# Phase labels are user-facing — keep them short and scannable.
PHASE_FETCH = "Fetching tracked docs"
PHASE_INGEST_DOCS = "Ingesting documents"
PHASE_INGEST_GENERIC = "Ingesting source"
PHASE_DONE = "Done"


@dataclass
class ProgressEvent:
    phase: str
    current: int = 0
    total: int = 0
    message: str = ""
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "elapsed_ms": self.elapsed_ms,
        }


# Rich color/style tags leak into stdout when NO_COLOR/TERM=dumb aren't enough;
# strip them before matching so patterns stay simple. Also strip the leading
# glyphs the CLI uses (✓ ✗ ⚠) — they carry no data past our regexes.
_RICH_TAG = re.compile(r"\[/?[a-z0-9 #]+\]", re.IGNORECASE)


def _clean(line: str) -> str:
    return _RICH_TAG.sub("", line).strip()


# ── Line matchers ────────────────────────────────────────────────────────────

# Domain flow: "Fetching tracked docs for domain 'X'..."
_FETCH_RE = re.compile(r"Fetching tracked docs for domain '([^']+)'")
# "Found N tracked docs, ingesting to Neo4j..."
_FOUND_RE = re.compile(r"Found\s+(\d+)\s+tracked docs")
# Per-doc success ("✓ <title>") or failure ("⚠ <title>: <err>").
# We don't rely on the checkmark glyph — Rich sometimes drops it under NO_COLOR
# — but the plain-text form "  ✓ <title>" leaves a checkmark ASCII we can miss.
# Instead we count lines that clearly represent one doc: our per-doc log line
# in `commands/kg.py` uses "  [green]✓[/green] <title>" / "  [yellow]⚠ <title>".
_DOC_OK_RE = re.compile(r"^\s*[✓v]\s+(.+)$")
_DOC_FAIL_RE = re.compile(r"^\s*[⚠!]\s+(.+?)(?::\s|$)")
# Final tally: "Documents processed: N/M"
_TALLY_RE = re.compile(r"Documents processed:\s*(\d+)\s*/\s*(\d+)")
# Neo4j path (non-domain): "Ingesting data from <src>..." — no total known yet.
_GENERIC_START_RE = re.compile(r"Ingesting data (?:into [\w]+ )?from\s+(.+?)\.{3}")
# Terminal successes: "Successfully ingested ..."
_DONE_RE = re.compile(r"Successfully ingested")


class ProgressParser:
    """Fold a stream of CLI stdout lines into ProgressEvent snapshots.

    Emits a snapshot whenever the phase or the current/total changes. Callers
    forward that snapshot as an SSE `progress` event alongside the raw `log`.
    """

    def __init__(self) -> None:
        self._start = time.monotonic()
        self._phase: str = ""
        self._current: int = 0
        self._total: int = 0
        self._message: str = ""

    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)

    def _snapshot(self) -> ProgressEvent:
        return ProgressEvent(
            phase=self._phase,
            current=self._current,
            total=self._total,
            message=self._message,
            elapsed_ms=self._elapsed_ms(),
        )

    def feed(self, raw: str) -> Optional[ProgressEvent]:
        """Return a ProgressEvent iff this line changed our state."""
        text = _clean(raw)
        if not text:
            return None

        prev = (self._phase, self._current, self._total, self._message)

        m = _FETCH_RE.search(text)
        if m:
            self._phase = PHASE_FETCH
            self._message = f"domain '{m.group(1)}'"
            self._current = 0
            self._total = 0
            return self._snapshot() if (self._phase, self._current, self._total, self._message) != prev else None

        m = _FOUND_RE.search(text)
        if m:
            self._phase = PHASE_INGEST_DOCS
            self._total = int(m.group(1))
            self._current = 0
            self._message = ""
            return self._snapshot() if (self._phase, self._current, self._total, self._message) != prev else None

        m = _GENERIC_START_RE.search(text)
        if m:
            # We know we started, but not how much work — leave total=0 so the
            # UI shows an indeterminate bar with the phase label.
            self._phase = PHASE_INGEST_GENERIC
            self._message = m.group(1)
            self._current = 0
            self._total = 0
            return self._snapshot() if (self._phase, self._current, self._total, self._message) != prev else None

        m = _TALLY_RE.search(text)
        if m:
            done, total = int(m.group(1)), int(m.group(2))
            self._current = done
            self._total = total
            return self._snapshot() if (self._phase, self._current, self._total, self._message) != prev else None

        # DONE is checked before the per-doc regex because the CLI's terminal
        # success line ("✓ Successfully ingested…") also starts with a
        # checkmark and would otherwise be miscounted as one more doc.
        if _DONE_RE.search(text):
            self._phase = PHASE_DONE
            if self._total:
                self._current = self._total
            self._message = "complete"
            return self._snapshot() if (self._phase, self._current, self._total, self._message) != prev else None

        if _DOC_OK_RE.match(text) or _DOC_FAIL_RE.match(text):
            if self._phase == PHASE_INGEST_DOCS:
                self._current = min(self._current + 1, self._total or self._current + 1)
                return self._snapshot()

        return None
