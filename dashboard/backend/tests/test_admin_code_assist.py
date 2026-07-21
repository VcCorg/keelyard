"""Backend admin service: code_assist round-trips through get/update settings."""

from src.services import admin_service as svc


def test_get_settings_includes_code_assist(monkeypatch, tmp_path):
    import agentic_cli.admin.settings as S

    monkeypatch.setattr(S, "SETTINGS_PATH", tmp_path / "admin.json")
    m = svc.get_settings()
    assert m.code_assist.default == "devin"
    assert "local" in m.code_assist.enabled


def test_update_settings_persists_code_assist(monkeypatch, tmp_path):
    import agentic_cli.admin.settings as S

    monkeypatch.setattr(S, "SETTINGS_PATH", tmp_path / "admin.json")
    upd = svc.AdminSettingsUpdate(
        code_assist=svc.CodeAssistModel(enabled=["vscode-copilot", "local"], default="vscode-copilot"))
    m = svc.update_settings(upd, actor="admin@example.com")
    assert m.code_assist.default == "vscode-copilot"
    assert svc.get_settings().code_assist.enabled == ["vscode-copilot", "local"]
