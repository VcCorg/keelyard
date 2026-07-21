"""Tests for the code-assist admin setting (enabled engines + default)."""

from agentic_cli.admin import settings as S


def test_default_code_assist(tmp_path):
    path = tmp_path / "admin.json"
    s = S.load_settings(path)
    assert s.code_assist.default == "devin"
    assert "local" in s.code_assist.enabled


def test_set_code_assist_persists_and_sanitizes(tmp_path):
    path = tmp_path / "admin.json"
    s = S.set_code_assist(enabled=["vscode-copilot", "local"], default="local", path=path)
    assert s.code_assist.enabled == ["vscode-copilot", "local"]
    assert s.code_assist.default == "local"
    # Reload from disk.
    assert S.load_settings(path).code_assist.default == "local"


def test_default_forced_into_enabled(tmp_path):
    path = tmp_path / "admin.json"
    # default not in enabled → coerced to the first enabled engine.
    s = S.set_code_assist(enabled=["local"], default="devin", path=path)
    assert s.code_assist.default == "local"


def test_empty_enabled_falls_back_to_defaults(tmp_path):
    path = tmp_path / "admin.json"
    s = S.set_code_assist(enabled=[], default="", path=path)
    assert s.code_assist.enabled  # never empty
    assert s.code_assist.default in s.code_assist.enabled


def test_partial_update_default_only(tmp_path):
    path = tmp_path / "admin.json"
    S.set_code_assist(enabled=["devin", "local", "vscode-copilot"], default="devin", path=path)
    s = S.update_settings(code_assist={"default": "vscode-copilot"}, path=path)
    assert s.code_assist.default == "vscode-copilot"
    assert "local" in s.code_assist.enabled  # enabled preserved


def test_code_assist_survives_other_updates(tmp_path):
    path = tmp_path / "admin.json"
    S.set_code_assist(enabled=["local"], default="local", path=path)
    s = S.set_skill_enforcement("enforce", path=path)
    assert s.code_assist.default == "local"  # unrelated update didn't reset it
