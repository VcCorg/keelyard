"""Tests for the reusable ``agentic_cli.devin`` package (config, sessions,
knowledge) plus back-compat re-exports from ``agentic_cli.kg.okf.devin``."""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from agentic_cli.devin import (
    SessionSpec,
    SessionResult,
    create_session,
    get_session,
    list_local,
)
from agentic_cli.devin import config as devin_config
from agentic_cli.devin import sessions as devin_sessions
from agentic_cli.devin import knowledge as devin_knowledge


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def local_store(tmp_path, monkeypatch):
    """Redirect the session store to a temp file."""
    store_dir = tmp_path / "devin"
    store_file = store_dir / "sessions.json"
    monkeypatch.setattr(devin_sessions, "STORE_DIR", store_dir)
    monkeypatch.setattr(devin_sessions, "STORE_FILE", store_file)
    return store_file


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """Redirect the shared CLI config to a temp file."""
    cfg_dir = tmp_path / ".agent-cli-agentic"
    cfg_file = cfg_dir / "config.json"
    monkeypatch.setattr(devin_config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(devin_config, "CONFIG_FILE", cfg_file)
    return cfg_file


@contextmanager
def _fake_client_cm(client):
    yield client


def _patch_get_client(monkeypatch, module, client):
    monkeypatch.setattr(module, "get_client", lambda *a, **k: _fake_client_cm(client))


# ---------------------------------------------------------------------------
# SessionSpec
# ---------------------------------------------------------------------------

def test_session_spec_payload_omits_empty_fields():
    spec = SessionSpec(prompt="do the thing")
    payload = spec.to_payload()
    assert payload == {"prompt": "do the thing"}


def test_session_spec_payload_includes_set_fields():
    spec = SessionSpec(
        prompt="p",
        title="T",
        snapshot_id="snap-1",
        playbook_id="pb-1",
        knowledge_ids=["k1", "k2"],
        tags=["dva", "cwow"],
        idempotent=True,
        max_acu_limit=5,
        unlisted=True,
    )
    payload = spec.to_payload()
    assert payload["title"] == "T"
    assert payload["snapshot_id"] == "snap-1"
    assert payload["playbook_id"] == "pb-1"
    assert payload["knowledge_ids"] == ["k1", "k2"]
    assert payload["tags"] == ["dva", "cwow"]
    assert payload["idempotent"] is True
    assert payload["max_acu_limit"] == 5
    assert payload["unlisted"] is True


def test_prompt_hash_is_stable_and_tag_order_independent():
    a = SessionSpec(prompt="x", tags=["b", "a"])
    b = SessionSpec(prompt="x", tags=["a", "b"])
    assert a.prompt_hash() == b.prompt_hash()
    c = SessionSpec(prompt="y", tags=["a", "b"])
    assert a.prompt_hash() != c.prompt_hash()


# ---------------------------------------------------------------------------
# Local store
# ---------------------------------------------------------------------------

def test_create_session_dry_run_does_not_touch_store(local_store):
    res = create_session(SessionSpec(prompt="hi"), dry_run=True)
    assert res.dry_run is True
    assert res.payload["prompt"] == "hi"
    # The default ACU budget is applied before the dry-run short-circuit.
    assert res.payload["max_acu_limit"] == devin_config.DEFAULT_MAX_ACU
    assert not local_store.exists()


def test_create_session_records_locally(local_store, monkeypatch):
    client = MagicMock()
    client.create_session.return_value = {
        "session_id": "sess-123",
        "url": "https://app.devin.ai/sessions/sess-123",
        "status": "running",
        "is_new_session": True,
    }
    _patch_get_client(monkeypatch, devin_sessions, client)

    spec = SessionSpec(prompt="build a feature", domain="cwow-facility", jira="CWOW-1")
    res = create_session(spec, api_key="key")

    assert res.session_id == "sess-123"
    assert res.status == "running"
    stored = json.loads(local_store.read_text())["sessions"]["sess-123"]
    assert stored["domain"] == "cwow-facility"
    assert stored["jira"] == "CWOW-1"
    assert list_local()[0]["session_id"] == "sess-123"


def test_idempotent_reuses_live_local_session(local_store, monkeypatch):
    client = MagicMock()
    client.create_session.return_value = {"session_id": "sess-1", "status": "running"}
    _patch_get_client(monkeypatch, devin_sessions, client)

    spec = SessionSpec(prompt="same prompt", idempotent=True)
    first = create_session(spec, api_key="key")
    assert first.session_id == "sess-1"

    # Second create with the same spec should reuse, not call the API again.
    client.create_session.reset_mock()
    second = create_session(SessionSpec(prompt="same prompt", idempotent=True), api_key="key")
    assert second.reused_local is True
    assert second.is_new is False
    assert second.session_id == "sess-1"
    client.create_session.assert_not_called()


def test_idempotent_does_not_reuse_terminal_session(local_store, monkeypatch):
    client = MagicMock()
    client.create_session.return_value = {"session_id": "sess-1", "status": "finished"}
    _patch_get_client(monkeypatch, devin_sessions, client)
    spec = SessionSpec(prompt="p", idempotent=True)
    create_session(spec, api_key="key")

    # Mark stored session terminal -> a new spec should spawn again.
    client.create_session.return_value = {"session_id": "sess-2", "status": "running"}
    res = create_session(SessionSpec(prompt="p", idempotent=True), api_key="key")
    assert res.session_id == "sess-2"


def test_get_session_updates_status(local_store, monkeypatch):
    create_client = MagicMock()
    create_client.create_session.return_value = {"session_id": "sess-9", "status": "running"}
    _patch_get_client(monkeypatch, devin_sessions, create_client)
    create_session(SessionSpec(prompt="p"), api_key="key")

    get_client_mock = MagicMock()
    get_client_mock.get_session.return_value = {
        "status_enum": "finished",
        "url": "u",
        "structured_output": {"pr": 1},
    }
    _patch_get_client(monkeypatch, devin_sessions, get_client_mock)
    res = get_session("sess-9", api_key="key")

    assert isinstance(res, SessionResult)
    assert res.status == "finished"
    assert res.structured_output == {"pr": 1}
    stored = json.loads(local_store.read_text())["sessions"]["sess-9"]
    assert stored["last_status"] == "finished"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_round_trip(config_file):
    cfg = devin_config.DevinConfig(data={})
    cfg.base_url = "https://example/v1"
    cfg.default_max_acu = 25
    cfg.set_domain("cwow-facility", snapshot_id="snap-x", knowledge_folder="cwow-facility-okf")
    cfg.save()

    reloaded = devin_config.DevinConfig.load()
    assert reloaded.base_url == "https://example/v1"
    assert reloaded.default_max_acu == 25
    assert reloaded.domain("cwow-facility")["snapshot_id"] == "snap-x"
    assert reloaded.domain("cwow-facility")["knowledge_folder"] == "cwow-facility-okf"


def test_config_defaults_when_unset(config_file):
    cfg = devin_config.DevinConfig(data={})
    assert cfg.base_url == devin_config.DEVIN_API_BASE
    assert cfg.default_max_acu == devin_config.DEFAULT_MAX_ACU
    assert cfg.domain("missing") == {}


def test_resolve_api_key_precedence(monkeypatch):
    monkeypatch.delenv(devin_config.DEVIN_API_KEY_ENV, raising=False)
    assert devin_config.resolve_api_key() is None
    assert devin_config.has_api_key() is False
    monkeypatch.setenv(devin_config.DEVIN_API_KEY_ENV, "env-key")
    assert devin_config.resolve_api_key() == "env-key"
    assert devin_config.resolve_api_key("explicit") == "explicit"
    assert devin_config.has_api_key() is True


def test_resolve_verify_env(monkeypatch):
    monkeypatch.delenv(devin_config.DEVIN_CA_BUNDLE_ENV, raising=False)
    monkeypatch.setenv(devin_config.DEVIN_VERIFY_SSL_ENV, "false")
    assert devin_config.resolve_verify() is False
    monkeypatch.setenv(devin_config.DEVIN_VERIFY_SSL_ENV, "true")
    assert devin_config.resolve_verify() is True
    monkeypatch.setenv(devin_config.DEVIN_CA_BUNDLE_ENV, "/etc/ca.pem")
    assert devin_config.resolve_verify() == "/etc/ca.pem"


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------

def test_list_entries(monkeypatch):
    client = MagicMock()
    client.list_knowledge.return_value = {"knowledge": [{"id": "k1"}], "folders": []}
    _patch_get_client(monkeypatch, devin_knowledge, client)
    out = devin_knowledge.list_entries(api_key="key")
    assert out["knowledge"][0]["id"] == "k1"


def test_delete_entries_reports_failures(monkeypatch):
    client = MagicMock()
    client.delete.side_effect = [None, Exception("boom")]
    _patch_get_client(monkeypatch, devin_knowledge, client)
    deleted, failed = devin_knowledge.delete_entries(["k1", "k2"], api_key="key")
    assert deleted == ["k1"]
    assert failed[0][0] == "k2"


def test_update_entry_merges_fields(monkeypatch):
    client = MagicMock()
    client.list_knowledge.return_value = {
        "knowledge": [{"id": "k1", "name": "Old", "body": "B", "trigger_description": "T"}]
    }
    client.update.return_value = {"id": "k1"}
    _patch_get_client(monkeypatch, devin_knowledge, client)
    devin_knowledge.update_entry("k1", {"name": "New"}, api_key="key")
    sent = client.update.call_args.args[1]
    assert sent["name"] == "New"
    assert sent["body"] == "B"
    assert sent["trigger_description"] == "T"


def test_update_entry_missing_raises(monkeypatch):
    from agentic_cli.devin.errors import DevinError

    client = MagicMock()
    client.list_knowledge.return_value = {"knowledge": []}
    _patch_get_client(monkeypatch, devin_knowledge, client)
    with pytest.raises(DevinError):
        devin_knowledge.update_entry("nope", {"name": "X"}, api_key="key")


# ---------------------------------------------------------------------------
# Back-compat re-exports
# ---------------------------------------------------------------------------

def test_okf_devin_reexports_point_to_package():
    from agentic_cli.kg.okf import devin as okf_devin
    from agentic_cli.devin.client import DevinClient

    # Transport + generic CRUD are re-exported as the SAME objects.
    assert okf_devin.DevinClient is DevinClient
    assert okf_devin.list_entries is devin_knowledge.list_entries
    assert okf_devin.delete_entries is devin_knowledge.delete_entries
    assert okf_devin.update_entry is devin_knowledge.update_entry
    assert okf_devin.move_entry is devin_knowledge.move_entry
    assert okf_devin.DEVIN_API_BASE == devin_config.DEVIN_API_BASE
