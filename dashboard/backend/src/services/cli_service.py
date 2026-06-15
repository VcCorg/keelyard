"""Generic CLI runner — streams whitelisted `dva ...` commands over SSE.

This gives the dashboard broad access to the CLI surface without bespoke pages
for every command, while keeping a safety boundary: only known top-level
command groups may be invoked, and obviously destructive subcommands are
blocked.
"""

import shlex
import shutil
import sys

# Top-level `dva` command groups that may be invoked from the dashboard.
ALLOWED_GROUPS = {
    "init", "project", "kg", "data", "mcp", "agent", "skill", "code",
    "domain", "product", "history", "agent-template", "agent-tool",
    "eval", "skill-registry",
}

# Subcommands blocked regardless of group (destructive / irreversible).
BLOCKED_SUBCOMMANDS = {"clear", "delete", "remove", "cleanup", "reset", "uninstall"}


class CommandNotAllowed(Exception):
    pass


def resolve_cli_command() -> list[str]:
    dva = shutil.which("dva")
    if dva:
        return [dva]
    return [sys.executable, "-m", "agentic_cli.main"]


def parse_and_validate(command: str, allow_destructive: bool = False) -> list[str]:
    """Split a raw command string and validate it against the whitelist.

    Accepts forms like "kg stats" or "dva kg stats" (the leading `dva` is
    stripped). Returns the argv list (without the `dva` prefix).

    When ``allow_destructive`` is True, the blocked-subcommand check is skipped
    (the dashboard "danger mode" toggle); the group whitelist still applies.
    """
    tokens = shlex.split(command.strip())
    if not tokens:
        raise CommandNotAllowed("Empty command.")

    if tokens[0] in ("dva", "agentic-cli"):
        tokens = tokens[1:]
    if not tokens:
        raise CommandNotAllowed("No command group specified.")

    group = tokens[0]
    if group not in ALLOWED_GROUPS:
        raise CommandNotAllowed(
            f"Command group '{group}' is not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_GROUPS))}."
        )

    if not allow_destructive:
        for tok in tokens[1:]:
            if tok in BLOCKED_SUBCOMMANDS:
                raise CommandNotAllowed(
                    f"Subcommand '{tok}' is blocked. Enable danger mode to run "
                    f"destructive commands ({', '.join(sorted(BLOCKED_SUBCOMMANDS))})."
                )
    return tokens


def build_command(command: str, allow_destructive: bool = False) -> list[str]:
    """Validate and return the full exec command list (incl. the dva binary)."""
    argv = parse_and_validate(command, allow_destructive=allow_destructive)
    return resolve_cli_command() + argv


def list_groups() -> list[str]:
    return sorted(ALLOWED_GROUPS)


def list_blocked_subcommands() -> list[str]:
    return sorted(BLOCKED_SUBCOMMANDS)
