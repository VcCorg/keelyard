"""Domain drift trigger — ``keel.drift.detected``.

Turns drift from something a page renders into something an agent is woken by.
The detectors already existed; nothing had ever fanned them out, so a template
change or a moved onboarding page waited for a human to open the right screen.

**This is a state trigger, not an event stream.** Drift has no source
timestamp — a doc that moved upstream last Tuesday is equally drifted now — so
``since`` passes trivially and dedup does the real work. The event id encodes
the *shape* of the drift (domain, signal, severity, count), which gives the
semantics we want: the same unresolved drift stays quiet, and re-fires only
when it changes or gets worse. A domain that is drifting and ignored does not
generate a poll's worth of noise every five minutes.

One event per signal rather than one per domain: a watcher filtered to template
drift should not wake for a stale Confluence page, and a handler's prompt reads
better when it has one problem in it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from agentic_cli.onboarding import drift as drift_core

from ..registry import register_trigger
from ..types import TriggerEvent, TriggerInfo

logger = logging.getLogger(__name__)

FILTER_SCHEMA: dict[str, dict[str, Any]] = {
    "domain": {
        "type": "string",
        "label": "Domain slug",
        "required": True,
        "help": "Which domain to watch for drift (e.g. acme-facility).",
    },
    "min_severity": {
        "type": "string",
        "label": "Minimum severity",
        "required": False,
        "help": "warn = anything actionable; fail = only what needs a decision "
                "now. Default: fail.",
    },
    "signals": {
        "type": "string",
        "label": "Signals",
        "required": False,
        "help": "Comma-separated detector keys to watch "
                f"({', '.join(drift_core.detector_keys())}). Blank = all.",
    },
}


class DomainDriftTrigger:
    """Emits one event per actionable drift signal for a domain."""

    info = TriggerInfo(
        name="keel.drift.detected",
        label="Domain drift detected",
        description="Template, tracked docs, repo sources, or the review "
                    "backlog moved for a watched domain.",
        source_mcp="",  # reads local state, not an MCP server
        filter_schema=FILTER_SCHEMA,
        # Drift changes at human speed. Polling it every five minutes would
        # re-run a template render for no benefit.
        default_poll_seconds=1800,
    )

    async def fetch(
        self,
        filter: dict[str, Any],
        since: datetime,
        limit: int = 200,
    ) -> list[TriggerEvent]:
        slug = str((filter or {}).get("domain") or "").strip()
        if not slug:
            return []

        minimum = str((filter or {}).get("min_severity") or drift_core.FAIL).strip().lower()
        if minimum not in drift_core.SEVERITY_ORDER:
            minimum = drift_core.FAIL

        raw_signals = str((filter or {}).get("signals") or "").strip()
        keys = [k.strip() for k in raw_signals.split(",") if k.strip()] or None

        try:
            signals = drift_core.detect(slug, keys)
        except Exception as exc:  # noqa: BLE001 - a poll must not raise
            logger.debug("drift fetch failed for %s: %s", slug, exc)
            return []

        now = datetime.now(timezone.utc)
        events = [
            TriggerEvent(
                type=self.info.name,
                event_id=_event_id(slug, signal),
                ts=now,
                data={
                    "domain": slug,
                    "signal": signal.key,
                    "label": signal.label,
                    "severity": signal.severity,
                    "count": signal.count,
                    "total": signal.total,
                    "detail": signal.detail,
                    "fix": signal.fix,
                },
            )
            for signal in signals
            if signal.at_least(minimum)
        ]
        return events[:limit]


def _event_id(slug: str, signal: drift_core.DriftSignal) -> str:
    """Stable while the drift is unchanged; new when it moves.

    Including the count is deliberate: two files drifting is a different fact
    from one, and a handler that already reported "1 conflict" should be woken
    when it becomes three. Excluding it would make the trigger fire once and
    then stay silent while the problem grew.
    """
    return f"drift:{slug}:{signal.key}:{signal.severity}:{signal.count}"


register_trigger(DomainDriftTrigger())
