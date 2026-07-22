"""Open-in-IDE editor options derive from the admin code-assist config."""

from src.services import workspace_service as svc


def test_enabled_editors_filters_to_admin_and_installed(monkeypatch):
    # All editors "installed"; admin enables only vscode-copilot (+ local, which
    # has no editor mapping) → only VS Code ('code') is offered.
    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin", "windsurf", "cursor", "code"])

    class CA:
        enabled = ["vscode-copilot", "local"]
        default = "vscode-copilot"

    monkeypatch.setattr(svc, "_code_assist", lambda: CA())
    assert svc.enabled_editors() == ["code"]


def test_enabled_editors_orders_default_first(monkeypatch):
    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin", "code"])

    class CA:
        enabled = ["vscode-copilot", "devin"]
        default = "devin"

    monkeypatch.setattr(svc, "_code_assist", lambda: CA())
    # Default engine (devin) first, then vscode-copilot → code.
    assert svc.enabled_editors() == ["devin", "code"]


def test_enabled_editors_drops_uninstalled(monkeypatch):
    # Admin enables VS Code but it isn't installed → nothing offered (no dropdown).
    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin"])

    class CA:
        enabled = ["vscode-copilot"]
        default = "vscode-copilot"

    monkeypatch.setattr(svc, "_code_assist", lambda: CA())
    assert svc.enabled_editors() == []


def test_enabled_editors_falls_back_when_no_admin_config(monkeypatch):
    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin", "code"])
    monkeypatch.setattr(svc, "_code_assist", lambda: None)
    assert svc.enabled_editors() == ["devin", "code"]


def test_devin_cli_maps_to_devin_editor(monkeypatch):
    """Selecting Devin CLI as default should still open the Devin app to review."""
    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin", "code"])

    class CA:
        enabled = ["devin", "devin-cli"]
        default = "devin-cli"

    monkeypatch.setattr(svc, "_code_assist", lambda: CA())
    assert svc.enabled_editors() == ["devin"]


def test_open_refuses_silent_vendor_substitution(monkeypatch, tmp_path):
    """VS Code is org default but not installed → refuse rather than opening Devin."""
    from pathlib import Path as P

    # Only Devin installed; org default is VS Code (no `code` CLI, no .app).
    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin"])
    monkeypatch.setattr(svc, "_editor_app_available", lambda _e: False)

    class CA:
        enabled = ["vscode-copilot", "devin"]
        default = "vscode-copilot"

    monkeypatch.setattr(svc, "_code_assist", lambda: CA())

    d = tmp_path / "work"
    d.mkdir()
    try:
        svc.open_in_ide(str(d))
        assert False, "expected refusal when VS Code isn't installed"
    except ValueError as e:
        assert "VS Code" in str(e) or "code" in str(e).lower()
        assert "Admin" in str(e)


def test_open_uses_vscode_app_fallback_on_macos(monkeypatch, tmp_path):
    """VS Code .app is installed but `code` CLI isn't — use `open -a` instead of
    silently substituting a different vendor."""
    import subprocess as _sp

    monkeypatch.setattr(svc, "detect_editors", lambda: ["devin"])
    # Simulate macOS with only VS Code .app present.
    monkeypatch.setattr(svc.sys, "platform", "darwin")
    monkeypatch.setattr(svc, "_editor_app_available", lambda e: e == "code")
    monkeypatch.setattr(svc.shutil, "which", lambda _n: None)

    class CA:
        enabled = ["vscode-copilot", "devin"]
        default = "vscode-copilot"

    monkeypatch.setattr(svc, "_code_assist", lambda: CA())

    launched: dict = {}
    def fake_popen(cmd, **_kw):
        launched["cmd"] = cmd
        class P:
            def poll(self): return None
        return P()
    monkeypatch.setattr(svc.subprocess, "Popen", fake_popen)

    d = tmp_path / "work"
    d.mkdir()
    res = svc.open_in_ide(str(d))
    # Opened via `open -a "Visual Studio Code"` — not Devin.
    assert launched["cmd"][:3] == ["open", "-a", "Visual Studio Code"]
    assert res.editor == "code"
