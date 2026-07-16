"""Tests for the download-on-first-use built-in model."""

import sys
import types

import httpx
import pytest

from agentic_cli.llm import builtin_model as bm
from agentic_cli.llm import factory
from agentic_cli.llm.base import ProviderError, ProviderNotConfigured
from agentic_cli.llm.models import ModelRegistry
from agentic_cli.llm.providers.test_mode import TestModeProvider

MB = 1024 * 1024


@pytest.fixture()
def tmp_models_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(bm, "MODELS_DIR", tmp_path / "models")
    monkeypatch.delenv(bm.ENV_URL, raising=False)
    monkeypatch.delenv(bm.ENV_FILE, raising=False)
    return tmp_path / "models"


def _client_serving(payload: bytes):
    def handler(request):
        return httpx.Response(200, content=payload,
                              headers={"content-length": str(len(payload))})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_download_writes_model_and_reports_progress(tmp_models_dir, monkeypatch):
    monkeypatch.setattr(bm, "_MIN_VALID_BYTES", 1 * MB)
    payload = b"g" * (2 * MB)
    seen = []
    path = bm.download(progress=lambda d, t: seen.append((d, t)),
                       _client=_client_serving(payload))
    assert path == bm.model_path() and path.is_file()
    assert path.stat().st_size == 2 * MB
    assert bm.is_downloaded()
    assert seen and seen[-1][0] == 2 * MB and seen[-1][1] == 2 * MB
    # No stray .part left behind.
    assert not list(tmp_models_dir.glob("*.part"))


def test_download_rejects_truncated_payloads(tmp_models_dir, monkeypatch):
    monkeypatch.setattr(bm, "_MIN_VALID_BYTES", 1 * MB)
    with pytest.raises(ProviderError, match="too small"):
        bm.download(_client=_client_serving(b"tiny"))
    assert not bm.is_downloaded()
    assert not list(tmp_models_dir.glob("*.part"))


def test_download_skips_when_present_and_force_redownloads(tmp_models_dir, monkeypatch):
    monkeypatch.setattr(bm, "_MIN_VALID_BYTES", 1 * MB)
    bm.download(_client=_client_serving(b"a" * (2 * MB)))
    first = bm.model_path().read_bytes()[:1]
    # Without force: untouched even though the "server" now returns different bytes.
    bm.download(_client=_client_serving(b"b" * (2 * MB)))
    assert bm.model_path().read_bytes()[:1] == first
    bm.download(force=True, _client=_client_serving(b"b" * (2 * MB)))
    assert bm.model_path().read_bytes()[:1] == b"b"


def test_remove(tmp_models_dir, monkeypatch):
    monkeypatch.setattr(bm, "_MIN_VALID_BYTES", 1 * MB)
    bm.download(_client=_client_serving(b"a" * (2 * MB)))
    assert bm.remove() is True
    assert bm.remove() is False
    assert not bm.is_downloaded()


# ── provider ────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_llama(monkeypatch):
    """A fake llama_cpp module whose Llama echoes a canned completion."""
    mod = types.ModuleType("llama_cpp")

    class Llama:  # noqa: D401 - test double
        def __init__(self, model_path, n_ctx=0, verbose=False):
            self.model_path = model_path

        def create_chat_completion(self, messages, temperature=0.0):
            user = messages[-1]["content"]
            return {"choices": [{"message": {"content": f"echo:{user}"}}]}

    mod.Llama = Llama
    monkeypatch.setitem(sys.modules, "llama_cpp", mod)
    # Reset the class-level cache so each test loads fresh.
    monkeypatch.setattr(bm.BuiltinProvider, "_llm", None)
    monkeypatch.setattr(bm.BuiltinProvider, "_llm_path", None)
    return mod


def test_builtin_provider_generates(tmp_models_dir, monkeypatch, fake_llama):
    monkeypatch.setattr(bm, "_MIN_VALID_BYTES", 1 * MB)
    bm.download(_client=_client_serving(b"a" * (2 * MB)))
    p = bm.BuiltinProvider(system_instruction="be brief")
    assert p.generate("hello") == "echo:hello"
    assert p.get_name().startswith("builtin/")


def test_builtin_provider_requires_download(tmp_models_dir, fake_llama):
    with pytest.raises(ProviderNotConfigured, match="not downloaded"):
        bm.BuiltinProvider()


# ── factory chain ───────────────────────────────────────────────────────────

@pytest.fixture()
def clean_llm_env(monkeypatch):
    for var in ("KEEL_LLM_PROVIDER", "KEEL_LOCAL_LLM_MODEL", "KEEL_LOCAL_LLM_URL",
                "KEEL_DISABLE_TEST_MODE"):
        monkeypatch.delenv(var, raising=False)
    import agentic_cli.kg.config as kg_config

    monkeypatch.setattr(kg_config.KGConfig, "load",
                        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no config"))))
    return monkeypatch


def test_registry_routes_builtin():
    assert ModelRegistry.detect_provider("builtin") == "builtin"
    assert ModelRegistry.detect_provider("test-mode") == "test-mode"


def test_chain_prefers_downloaded_builtin_over_test_mode(
        clean_llm_env, tmp_models_dir, monkeypatch, fake_llama):
    monkeypatch.setattr(bm, "_MIN_VALID_BYTES", 1 * MB)
    bm.download(_client=_client_serving(b"a" * (2 * MB)))
    provider = factory.get_llm_provider()
    assert isinstance(provider, bm.BuiltinProvider)


def test_chain_skips_builtin_when_not_downloaded(clean_llm_env, tmp_models_dir, fake_llama):
    provider = factory.get_llm_provider()
    assert isinstance(provider, TestModeProvider)
