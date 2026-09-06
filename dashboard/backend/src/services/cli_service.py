"""Generic CLI runner — streams whitelisted `keel ...` commands over SSE.

This gives the dashboard broad access to the CLI surface without bespoke pages
for every command, while keeping a safety boundary: only known top-level
command groups may be invoked, and obviously destructive subcommands are
blocked.
"""


# One implementation, in cli_invocation: it knows about the frozen
# sidecar, where `-m` silently starts a second backend.
from src.services.cli_invocation import (  # noqa: F401
    resolve_cli_command,
    split_command,
)

# Top-level `keel` command groups that may be invoked from the dashboard.
ALLOWED_GROUPS = {
    "init", "project", "kg", "data", "mcp", "agent", "skill", "code",
    "domain", "product", "history", "agent-template", "agent-tool",
    "eval", "skill-registry",
}

# Subcommands blocked regardless of group (destructive / irreversible).
BLOCKED_SUBCOMMANDS = {"clear", "delete", "remove", "cleanup", "reset", "uninstall"}


class CommandNotAllowed(Exception):
    pass


def parse_and_validate(command: str, allow_destructive: bool = False) -> list[str]:
    """Split a raw command string and validate it against the whitelist.

    Accepts forms like "kg stats" or "keel kg stats" (the leading `keel` is
    stripped). Returns the argv list (without the `keel` prefix).

    When ``allow_destructive`` is True, the blocked-subcommand check is skipped
    (the dashboard "danger mode" toggle); the group whitelist still applies.
    """
    # Platform-aware: POSIX splitting eats Windows path separators,
    # which produced a command that ran fine against the wrong path.
    try:
        tokens = split_command(command.strip())
    except ValueError as e:
        # An unterminated quote. Caught here rather than in split_command so the
        # splitter stays a splitter — this is the layer that owns the 400.
        raise CommandNotAllowed(f"Could not parse the command: {e}") from e
    if not tokens:
        raise CommandNotAllowed("Empty command.")

    if tokens[0] in ("keel", "agentic-cli"):
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
    """Validate and return the full exec command list (incl. the keel binary)."""
    argv = parse_and_validate(command, allow_destructive=allow_destructive)
    return resolve_cli_command() + argv


def list_groups() -> list[str]:
    return sorted(ALLOWED_GROUPS)


def list_blocked_subcommands() -> list[str]:
    return sorted(BLOCKED_SUBCOMMANDS)
