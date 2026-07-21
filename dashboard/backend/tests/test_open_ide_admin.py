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
