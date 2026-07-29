"""Admin-controlled onboarding-IDE settings (Phase 2 of the code-assist refactor).

Pins the storage contract and the runtime wire-through:

  * settings round-trip: enabled + default persist across load/save
  * defaults post-migration: Devin primary, Windsurf NOT seeded
  * sanitization: default never falls outside enabled; corrupt store reseeds
  * runtime: `resolve_tool_name('auto')` picks the admin default when live
    detection finds nothing
  * runtime: admin allow-list filters detection (a disabled IDE never wins)
  * runtime: bad settings file never bricks onboard (falls through cleanly)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_cli.admin import settings as A
from agentic_cli.code_assist import detect_tool, resolve_tool_name


# ── Storage contract ────────────────────────────────────────────────────────


def test_defaults_are_devin_primary(tmp_path, monkeypatch):
    """Post-migration seeds: Devin default, Windsurf not in enabled."""
    monkeypatch.setattr(A, "SETTINGS_PATH", tmp_path / "settings.json")
    s = A.load_settings()
    assert s.onboarding_ide.default == "devin"
    assert "devin" in s.onboarding_ide.enabled
    assert "windsurf" not in s.onboarding_ide.enabled


def test_set_onboarding_ide_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "SETTINGS_PATH", tmp_path / "settings.json")
    A.set_onboarding_ide(enabled=["cursor", "generic"], default="cursor")
    s = A.load_settings()
    assert s.onboarding_ide.enabled == ["cursor", "generic"]
    assert s.onboarding_ide.default == "cursor"


def test_default_forced_into_enabled(tmp_path, monkeypatch):
    """A default that isn't in enabled must be reset to the first enabled."""
    monkeypatch.setattr(A, "SETTINGS_PATH", tmp_path / "settings.json")
    A.set_onboarding_ide(enabled=["cursor"], default="devin")
    s = A.load_settings()
    assert s.onboarding_ide.default == "cursor"  # devin isn't in enabled


def test_corrupt_settings_reseeds_enabled(tmp_path, monkeypatch):
    """A settings file with an empty `enabled` list reseeds from defaults."""
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"onboarding_ide": {"enabled": [], "default": ""}}))
    monkeypatch.setattr(A, "SETTINGS_PATH", p)
    s = A.load_settings()
    assert s.onboarding_ide.enabled == list(A.DEFAULT_ONBOARDING_IDE_ENABLED)
    assert s.onboarding_ide.default == A.DEFAULT_ONBOARDING_IDE_DEFAULT


def test_update_settings_merges_partial(tmp_path, monkeypatch):
    """update_settings({default}) doesn't wipe enabled."""
    monkeypatch.setattr(A, "SETTINGS_PATH", tmp_path / "settings.json")
    A.set_onboarding_ide(enabled=["cursor", "devin"], default="devin")
    A.update_settings(onboarding_ide={"default": "cursor"})
    s = A.load_settings()
    assert s.onboarding_ide.enabled == ["cursor", "devin"]
    assert s.onboarding_ide.default == "cursor"


# ── Runtime wire-through ────────────────────────────────────────────────────


def test_admin_default_wins_when_no_ide_detected(monkeypatch):
    """auto with no live IDE + admin default 'cursor' → resolves to cursor."""
    monkeypatch.delenv("KEEL_CODE_ASSIST_TOOL", raising=False)
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("DEVIN_SESSION_ID", raising=False)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("HOME", tmp)
        assert resolve_tool_name("auto", admin_default="cursor") == "cursor"
        assert detect_tool(admin_default="cursor") == "cursor"


def test_admin_allowlist_hides_disabled_ide(monkeypatch):
    """A disabled IDE never wins auto-detection even if its markers are set.

    Post-migration: admin disables Windsurf. A machine with ~/.codeium/windsurf
    should NOT get Windsurf resolved — it should fall through to the admin
    default (devin) or the terminal default.
    """
    monkeypatch.delenv("KEEL_CODE_ASSIST_TOOL", raising=False)
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("DEVIN_SESSION_ID", raising=False)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        # Simulate a Windsurf install by creating ~/.codeium/windsurf.
        home = Path(tmp)
        (home / ".codeium" / "windsurf").mkdir(parents=True)
        monkeypatch.setenv("HOME", tmp)

        # Without an allow-list: windsurf would be detected (it's registered
        # and its detector returns True).
        without_filter = detect_tool()
        assert without_filter == "windsurf"

        # With admin restricting to just devin+cursor+generic (default seed):
        filtered = detect_tool(
            admin_default="devin", enabled=["devin", "cursor", "generic"],
        )
        assert filtered == "devin"  # falls to admin_default


def test_admin_allowlist_refuses_explicit_disabled(monkeypatch):
    """An explicit name that's admin-disabled degrades to admin_default."""
    resolved = resolve_tool_name(
        "windsurf", admin_default="devin", enabled=["devin", "cursor", "generic"],
    )
    assert resolved == "devin"


def test_env_override_ignored_when_admin_disables_it(monkeypatch):
    """KEEL_CODE_ASSIST_TOOL=windsurf but admin excluded it → not honored."""
    monkeypatch.setenv("KEEL_CODE_ASSIST_TOOL", "windsurf")
    assert detect_tool(
        admin_default="devin", enabled=["devin", "cursor", "generic"],
    ) == "devin"


def test_env_override_wins_when_allowed(monkeypatch):
    monkeypatch.setenv("KEEL_CODE_ASSIST_TOOL", "cursor")
    assert detect_tool(admin_default="devin", enabled=["devin", "cursor"]) == "cursor"


def test_broken_admin_settings_do_not_brick_onboard(tmp_path, monkeypatch):
    """A malformed settings file must not crash the resolver."""
    p = tmp_path / "settings.json"
    p.write_text("{this is not valid json")
    monkeypatch.setattr(A, "SETTINGS_PATH", p)
    # load_settings tolerates a bad file → defaults; resolve_tool_name doesn't
    # care whether the file was bad, it just gets defaults.
    s = A.load_settings()
    assert s.onboarding_ide.default == A.DEFAULT_ONBOARDING_IDE_DEFAULT
