"""Bitbucket PR trigger — ``bitbucket.pr.review_requested``.

Polls the Bitbucket MCP server (the same one already registered under the
Work Items experience) for PRs where the acting user is an assigned
reviewer and the PR is still OPEN. Emits one :class:`TriggerEvent` per
matching PR the first time we see it (subsequent updates re-emit only when
the review-request sequence bumps).

Data source is the MCP server — not a fresh Bitbucket API client — so:
  * auth already lives in ~/.keel/.env alongside every other MCP,
  * the trigger degrades gracefully when the MCP is offline (returns []),
  * a future switch from Bitbucket to GitHub is a new adapter, not a rewrite.

The registry patches the fetcher for tests via ``_client_factory``.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from ..registry import register_trigger
from ..types import TriggerEvent, TriggerInfo

logger = logging.getLogger(__name__)


# ── Filter schema (drives the UI form) ──────────────────────────────────────

FILTER_SCHEMA: dict[str, dict[str, Any]] = {
    "project": {
        "type": "string",
        "label": "Project key",
        "required": False,
        "help": "Only PRs under this project. Blank = all projects the user can see.",
    },
    "repo": {
        "type": "string",
        "label": "Repo slug",
        "required": False,
        "help": "Restrict to a single repo. Blank = every repo in the project.",
    },
    "age_hours_gt": {
        "type": "int",
        "label": "Older than N hours",
        "required": False,
        "help": "Only fire on review requests waiting this many hours or more.",
    },
    "title_matches": {
        "type": "regex",
        "label": "Title matches (regex)",
        "required": False,
        "help": "Only PRs whose title matches this Python regex. Blank = no filter.",
    },
    "reviewer_is_me": {
        "type": "bool",
        "label": "Only when I'm a reviewer",
        "required": False,
        "help": "Default true. Turn off to fire on ANY PR needing review in scope.",
    },
}


# ── Client factory (mockable for tests) ─────────────────────────────────────


_ClientFactory = Callable[[], Any]


def _default_client_factory() -> Any:
    """Return the shared Bitbucket MCP client, or None if the MCP is unavailable.

    Deliberately lazy — importing the MCP client at module load would drag in
    httpx / an event loop at CLI start-up. The runtime calls the factory once
    per poll instead.
    """
    try:
        from agentic_cli.mcp.clients import bitbucket_client  # type: ignore

        return bitbucket_client()
    except Exception as e:  # noqa: BLE001 — never brick the runtime on MCP init
        logger.debug(f"Bitbucket MCP client unavailable: {e}")
        return None


_client_factory: _ClientFactory = _default_client_factory


def set_client_factory(factory: _ClientFactory) -> None:
    """Test hook — swap in a fake client to drive the adapter deterministically."""
    global _client_factory
    _client_factory = factory


# ── The adapter ─────────────────────────────────────────────────────────────


class BitbucketPRReviewRequestedTrigger:
    """Bitbucket PR waiting for the acting user's review."""

    info = TriggerInfo(
        name="bitbucket.pr.review_requested",
        label="Bitbucket PR — review requested",
        description=(
            "Fires when a Bitbucket PR is waiting for the acting user's "
            "review. Uses the registered Bitbucket MCP server."
        ),
        source_mcp="bitbucket-mcp",
        filter_schema=FILTER_SCHEMA,
        default_poll_seconds=300,
    )

    async def fetch(
        self,
        filter: dict[str, Any],
        since: datetime,
        limit: int = 200,
    ) -> list[TriggerEvent]:
        client = _client_factory()
        if client is None:
            return []
        try:
            prs = await _list_open_prs_for_reviewer(
                client,
                project=str(filter.get("project", "") or "").strip() or None,
                repo=str(filter.get("repo", "") or "").strip() or None,
                reviewer_is_me=bool(filter.get("reviewer_is_me", True)),
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001 — never brick a poll on MCP error
            logger.info(f"bitbucket.pr.review_requested fetch failed: {e}")
            return []

        # Apply filters we can't push into the MCP query.
        title_regex = None
        raw_title = str(filter.get("title_matches", "") or "").strip()
        if raw_title:
            try:
                title_regex = re.compile(raw_title)
            except re.error as e:
                logger.warning(f"bad title_matches regex '{raw_title}': {e}")
                title_regex = None
        age_hours_gt = int(filter.get("age_hours_gt", 0) or 0)
        now = datetime.now(timezone.utc)
        min_age = timedelta(hours=age_hours_gt) if age_hours_gt > 0 else None

        events: list[TriggerEvent] = []
        for pr in prs:
            ts = _parse_ts(pr.get("updated_at") or pr.get("created_at"))
            if ts is None or ts < since:
                continue
            if title_regex and not title_regex.search(str(pr.get("title", ""))):
                continue
            if min_age and (now - ts) < min_age:
                continue
            events.append(
                TriggerEvent(
                    type=self.info.name,
                    event_id=_event_id(pr),
                    ts=ts,
                    data={"pr": pr},
                )
            )
        # Newest first — UI test-run + audit reads more naturally.
        events.sort(key=lambda e: e.ts, reverse=True)
        return events[:limit]


async def _list_open_prs_for_reviewer(
    client: Any,
    project: Optional[str],
    repo: Optional[str],
    reviewer_is_me: bool,
    limit: int,
) -> list[dict[str, Any]]:
    """Adapter around the MCP client — kept tiny so tests can swap it out easily."""
    method = getattr(client, "list_open_prs", None)
    if method is None:
        return []
    result = method(project=project, repo=repo, reviewer_is_me=reviewer_is_me, limit=limit)
    # Support both sync and async client implementations.
    if hasattr(result, "__await__"):
        result = await result
    if not isinstance(result, list):
        return []
    return [x for x in result if isinstance(x, dict)]


def _event_id(pr: dict[str, Any]) -> str:
    """Stable id — PR key + activity seq (or updated_at)."""
    pr_id = pr.get("id") or pr.get("pull_request_id") or pr.get("key") or ""
    seq = pr.get("review_request_seq") or pr.get("activity_seq") or pr.get("updated_at") or ""
    return f"bb-pr:{pr_id}:{seq}"


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


register_trigger(BitbucketPRReviewRequestedTrigger())
