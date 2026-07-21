"""Tests for the headless Devin CLI execution engine."""

from agentic_cli.execution import ExecutionSpec, list_engines
from agentic_cli.execution.devin_cli_adapter import (
    DEFAULT_CLI_CMD, ENV_CLI_CMD, DevinCliEngine, parse_session_id,
)


def test_registered_as_cli_engine():
    infos = {i.name: i for i in list_engines()}
    assert "devin-cli" in infos
    assert infos["devin-cli"].kind == "cli"


def test_available_follows_cli_presence(monkeypatch):
    import agentic_cli.execution.devin_cli_adapter as mod
    monkeypatch.setattr(mod.shutil, "which", lambda _n: "/usr/bin/devin")
    assert DevinCliEngine().info().available is True
    monkeypatch.setattr(mod.shutil, "which", lambda _n: None)
    assert DevinCliEngine().info().available is False


def test_dry_run_renders_configured_command(monkeypatch):
    monkeypatch.setenv(ENV_CLI_CMD, "devin run --task {prompt} --ctx {bundle}")
    res = DevinCliEngine().create_session(ExecutionSpec(prompt="fix the bug", dry_run=True))
    assert res.dry_run is True and res.engine == "devin-cli"
    assert "devin run --task fix" in res.raw["command"]
    assert "--ctx" in res.raw["command"]


def test_default_command_used_when_unset(monkeypatch):
    monkeypatch.delenv(ENV_CLI_CMD, raising=False)
    res = DevinCliEngine().create_session(ExecutionSpec(prompt="x", dry_run=True))
    assert DEFAULT_CLI_CMD.split(" ")[0] in res.raw["command"]


def test_real_launch_requires_cli(monkeypatch):
    import agentic_cli.execution.devin_cli_adapter as mod
    monkeypatch.setattr(mod.shutil, "which", lambda _n: None)
    try:
        DevinCliEngine().create_session(ExecutionSpec(prompt="x", dry_run=False))
        assert False, "expected RuntimeError when devin CLI is absent"
    except RuntimeError as e:
        assert "devin" in str(e).lower()


def test_parse_session_id():
    assert parse_session_id("created session_id: sess-abc123") == "sess-abc123"
    assert parse_session_id("no id here") is None
