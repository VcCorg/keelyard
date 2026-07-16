"""Tests for local model support + the built-in test-mode fallback."""

import json

import httpx
import pytest

from agentic_cli.llm import factory
from agentic_cli.llm.base import ProviderError, ProviderNotConfigured
from agentic_cli.llm.models import ModelRegistry
from agentic_cli.llm.providers.local import LocalProvider, strip_routing_prefix
from agentic_cli.llm.providers.test_mode import MARKER, TestModeProvider


# ── routing ──────────────────────────────────────────────────────────────────

def test_model_registry_routes_local_and_test_mode():
    assert ModelRegistry.detect_provider("local:llama3.2") == "local"
    assert ModelRegistry.detect_provider("ollama:qwen2.5") == "local"
    assert ModelRegistry.detect_provider("test-mode") == "test-mode"
    assert ModelRegistry.detect_provider("gemini-2.5-flash") == "vertex-ai"
    assert ModelRegistry.detect_provider("gpt-4") == "openai"


def test_strip_routing_prefix():
    assert strip_routing_prefix("local:llama3.2") == "llama3.2"
    assert strip_routing_prefix("ollama:qwen2.5") == "qwen2.5"
    assert strip_routing_prefix("llama3.2") == "llama3.2"


# ── LocalProvider ────────────────────────────────────────────────────────────

def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_local_provider_generates_via_openai_api(monkeypatch):
    monkeypatch.delenv("KEEL_LOCAL_LLM_MODEL", raising=False)
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "hello from llama"}}]})

    p = LocalProvider(model_name="local:llama3.2", base_url="http://box:11434/v1",
                      system_instruction="be brief", _client=_mock_client(handler))
    out = p.generate("hi")
    assert out == "hello from llama"
    assert seen["url"] == "http://box:11434/v1/chat/completions"
    assert seen["body"]["model"] == "llama3.2"          # prefix stripped
    assert seen["body"]["messages"][0]["role"] == "system"
    assert p.get_name() == "local/llama3.2"


def test_local_provider_requires_a_model(monkeypatch):
    monkeypatch.delenv("KEEL_LOCAL_LLM_MODEL", raising=False)
    with pytest.raises(ProviderNotConfigured):
        LocalProvider(model_name=None)


def test_local_provider_wraps_http_errors(monkeypatch):
    monkeypatch.delenv("KEEL_LOCAL_LLM_MODEL", raising=False)

    def handler(request):
        return httpx.Response(500, text="boom")

    p = LocalProvider(model_name="llama3.2", _client=_mock_client(handler))
    with pytest.raises(ProviderError, match="500"):
        p.generate("hi")


# ── TestModeProvider ─────────────────────────────────────────────────────────

STORY_PROMPT = (
    "You are a product analyst. From the requirements below, write up to 3 "
    'concise Jira user stories. Return ONLY a JSON array; each item must be an '
    'object with keys: "title", "description", "acceptance_criteria", '
    '"priority", "labels".\n\nRequirements:\nUsers need offline exports and '
    "audit logging for compliance reviews.\n"
)


def test_test_mode_emits_schema_compliant_stories():
    out = TestModeProvider().generate(STORY_PROMPT)
    stories = json.loads(out)
    assert isinstance(stories, list) and 1 <= len(stories) <= 3
    for s in stories:
        assert {"title", "description", "acceptance_criteria", "priority",
                "labels"} <= set(s)
        assert MARKER in s["title"]                      # clearly labeled

    # Deterministic: same prompt, same output.
    assert TestModeProvider().generate(STORY_PROMPT) == out


def test_test_mode_plain_text_is_labeled():
    out = TestModeProvider().generate("Summarize the roadmap for the team")
    assert MARKER in out


# ── factory fallback chain ───────────────────────────────────────────────────

@pytest.fixture()
def clean_llm_env(monkeypatch):
    for var in ("KEEL_LLM_PROVIDER", "KEEL_LOCAL_LLM_MODEL", "KEEL_LOCAL_LLM_URL",
                "KEEL_LOCAL_LLM_API_KEY", "KEEL_DISABLE_TEST_MODE"):
        monkeypatch.delenv(var, raising=False)
    # Force the "no Vertex configured" path regardless of the host machine.
    import agentic_cli.kg.config as kg_config

    monkeypatch.setattr(kg_config.KGConfig, "load",
                        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no config"))))
    return monkeypatch


def test_factory_falls_back_to_test_mode(clean_llm_env):
    provider = factory.get_llm_provider()
    assert isinstance(provider, TestModeProvider)
    assert provider.get_name().startswith(MARKER)


def test_factory_prefers_local_when_configured(clean_llm_env):
    clean_llm_env.setenv("KEEL_LOCAL_LLM_MODEL", "llama3.2")
    provider = factory.get_llm_provider()
    assert isinstance(provider, LocalProvider)
    assert provider.model_name == "llama3.2"


def test_factory_env_default_provider_routes_local(clean_llm_env):
    clean_llm_env.setenv("KEEL_LOCAL_LLM_MODEL", "qwen2.5")
    clean_llm_env.setenv("KEEL_LLM_PROVIDER", "local")
    provider = factory.get_llm_provider()
    assert isinstance(provider, LocalProvider)


def test_factory_disable_test_mode_is_strict(clean_llm_env):
    clean_llm_env.setenv("KEEL_DISABLE_TEST_MODE", "1")
    with pytest.raises(ProviderNotConfigured):
        factory.get_llm_provider()


def test_factory_model_prefix_routes_local(clean_llm_env):
    provider = factory.get_llm_provider(model_name="local:llama3.2")
    assert isinstance(provider, LocalProvider)
    assert provider.model_name == "llama3.2"


def test_factory_pinned_vertex_still_raises(clean_llm_env):
    # Explicitly asking for a gemini model without config must NOT silently
    # degrade to test-mode — misconfiguration should surface.
    with pytest.raises(ProviderNotConfigured):
        factory.get_llm_provider(model_name="gemini-2.5-flash")
