"""Activity service — reads from the dva-agentic-cli tracker database.

Direct import from agentic_cli.tracker for reads.
"""

import json
from typing import Optional

from pydantic import BaseModel


class ActivityEntry(BaseModel):
    """Single activity log entry."""
    id: int
    timestamp: str
    command: str
    subcommand: Optional[str] = None
    status: str = "success"
    duration_ms: Optional[int] = None
    args: Optional[dict] = None
    details: Optional[dict] = None
    repo_path: Optional[str] = None


class ActivityStats(BaseModel):
    """Aggregate activity stats."""
    total_commands: int = 0
    total_errors: int = 0
    commands_by_type: dict[str, int] = {}
    last_activity: Optional[str] = None


def get_activity(
    command: Optional[str] = None,
    subcommand: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    since: Optional[str] = None,
) -> list[ActivityEntry]:
    """Query the activity log."""
    try:
        from agentic_cli.tracker import get_activity as _get_activity
        rows = _get_activity(
            command=command,
            subcommand=subcommand,
            status=status,
            limit=limit,
            since=since,
        )
        entries = []
        for row in rows:
            args = None
            if row.get("args"):
                try:
                    args = json.loads(row["args"]) if isinstance(row["args"], str) else row["args"]
                except (json.JSONDecodeError, TypeError):
                    pass

            details = None
            if row.get("details"):
                try:
                    details = json.loads(row["details"]) if isinstance(row["details"], str) else row["details"]
                except (json.JSONDecodeError, TypeError):
                    pass

            entries.append(ActivityEntry(
                id=row["id"],
                timestamp=row["timestamp"],
                command=row["command"],
                subcommand=row.get("subcommand"),
                status=row.get("status", "success"),
                duration_ms=row.get("duration_ms"),
                args=args,
                details=details,
                repo_path=row.get("repo_path"),
            ))
        return entries
    except ImportError:
        return []


def get_activity_stats() -> ActivityStats:
    """Get aggregate activity stats."""
    try:
        from agentic_cli.tracker import get_activity_summary
        summary = get_activity_summary()
        return ActivityStats(
            total_commands=summary.get("total", 0),
            total_errors=summary.get("errors", 0),
            commands_by_type=summary.get("commands", {}),
            last_activity=summary.get("last_activity"),
        )
    except ImportError:
        return ActivityStats()
