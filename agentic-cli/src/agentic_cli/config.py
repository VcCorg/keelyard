"""CLI configuration and utilities."""

import os

# CLI name is configurable via AGENT_CLI_NAME env var (default: keel)
CLI_NAME = os.getenv("AGENT_CLI_NAME", "keel")
