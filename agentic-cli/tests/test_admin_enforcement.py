"""Tests for the admin skill-enforcement setting."""

from pathlib import Path

from agentic_cli.admin import (
    enforcement_enabled,
    load_settings,
    set_skill_enforcement,
    update_settings,
)


def test_enforcement_defaults_off(tmp_path):
    path = tmp_path / "admin-settings.json"
    assert load_settings(path).skill_enforcement == "off"
    assert enforcement_enabled(path) is False


def test_set_enforcement_toggles(tmp_path):
    path = tmp_path / "admin-settings.json"
    set_skill_enforcement("enforce", path)
    assert load_settings(path).skill_enforcement == "enforce"
    assert enforcement_enabled(path) is True
    set_skill_enforcement("off", path)
    assert enforcement_enabled(path) is False


def test_unknown_mode_coerced_to_off(tmp_path):
    path = tmp_path / "admin-settings.json"
    set_skill_enforcement("enforce", path)
    set_skill_enforcement("banana", path)
    assert load_settings(path).skill_enforcement == "off"


def test_update_settings_threads_enforcement(tmp_path):
    path = tmp_path / "admin-settings.json"
    update_settings(skill_enforcement="enforce", path=path)
    assert load_settings(path).skill_enforcement == "enforce"
    # A branding-only update must not clobber enforcement.
    update_settings(branding={"app_title": "X"}, path=path)
    assert load_settings(path).skill_enforcement == "enforce"


def test_enforcement_persisted_in_dict(tmp_path):
    path = tmp_path / "admin-settings.json"
    set_skill_enforcement("enforce", path)
    assert load_settings(path).to_dict()["skill_enforcement"] == "enforce"
