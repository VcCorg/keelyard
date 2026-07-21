"""Tests for the vendor-neutral session-launch + ask endpoints."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_launch_session_local_dry_run():
    r = client.post("/api/execution/session", json={
        "prompt": "do the thing", "engine": "local", "dry_run": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "local" and body["dry_run"] is True


def test_launch_defaults_to_admin_engine(monkeypatch, tmp_path):
    import agentic_cli.admin.settings as S
    monkeypatch.setattr(S, "SETTINGS_PATH", tmp_path / "admin.json")
    S.set_code_assist(enabled=["local"], default="local", path=tmp_path / "admin.json")

    r = client.post("/api/execution/session", json={"prompt": "x", "dry_run": True})
    assert r.status_code == 200
    assert r.json()["engine"] == "local"


def test_launch_requires_prompt():
    r = client.post("/api/execution/session", json={"prompt": "  ", "engine": "local"})
    assert r.status_code == 400


def test_ask_local_engine_returns_answer():
    r = client.post("/api/execution/ask", json={"prompt": "what is this repo?", "engine": "local"})
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "local"
    assert "answer" in body


def test_engines_expose_supports_ask():
    r = client.get("/api/execution/engines")
    assert r.status_code == 200
    by = {e["name"]: e for e in r.json()}
    assert by["local"]["supports_ask"] is True
    assert by["vscode-copilot"]["supports_ask"] is False
