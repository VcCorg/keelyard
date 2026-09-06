"""Tracked sources by ref, and Hugging Face inference.

Two halves of the same idea. A tracked doc used to *be* a Confluence page id,
which is the only reason a Kaggle competition or a hub card could not be a
domain source — not anything about the pipeline downstream. Once a doc carries a
ref, the scheme picks the reader and extraction never learns the difference.

The inference tests use an injected client rather than the network: what is
worth pinning is the routing decision, the token-usage reporting the ledger
depends on, and the failure messages — not that httpx can POST.
"""
from __future__ import annotations

import pytest

from agentic_cli import retrieval
from agentic_cli.llm.models import ModelRegistry
from agentic_cli.llm.providers import huggingface as hf
from agentic_cli.onboarding import sources


# ── tracked sources are addressed by ref ────────────────────────────────────

class TestTrackedSourcesByRef:
    def test_a_row_without_a_ref_still_reads_as_confluence(self):
        """Rows written before v18 predate the column; the rule lives in code too."""
        from agentic_cli.tracker import doc_ref

        assert doc_ref({"source_page_id": "12345"}) == "confluence:12345"
        assert doc_ref({"source_page_id": "12345", "source_ref": ""}) == "confluence:12345"

    def test_an_explicit_ref_wins(self):
        from agentic_cli.tracker import doc_ref

        assert doc_ref({"source_page_id": "kaggle://competition/titanic",
                        "source_ref": "kaggle://competition/titanic"}) == \
            "kaggle://competition/titanic"

    def test_the_scheme_decides_the_reader(self, monkeypatch):
        """A non-Confluence ref must not be routed to Confluence."""
        asked = []

        def fake_fetch(ref, **kwargs):
            asked.append(ref)
            return retrieval.Fetched(ref=ref, scheme="kaggle",
                                     status=retrieval.RESOLVED,
                                     text="evaluationMetric: AUC",
                                     version="titanic", title="Titanic")

        monkeypatch.setattr(retrieval, "fetch", fake_fetch)
        doc = sources.fetch_source("kaggle://competition/titanic")

        assert asked == ["kaggle://competition/titanic"]
        assert doc is not None
        assert doc.citation.scheme == "kaggle"
        assert doc.citation.ref == "competition/titanic"
        assert doc.citation.version == "titanic"

    def test_confluence_reads_are_unchanged(self, monkeypatch):
        """The wrapper still exists because callers name pages, not refs."""
        seen = {}

        def fake_fetch(ref, **kwargs):
            seen["ref"] = ref
            return retrieval.Fetched(ref=ref, scheme="confluence",
                                     status=retrieval.RESOLVED, text="body",
                                     version="7")

        monkeypatch.setattr(retrieval, "fetch", fake_fetch)
        doc = sources.fetch_confluence("12345", "Onboarding")

        assert seen["ref"] == "confluence:12345"
        assert doc.citation == sources.Citation("confluence", "12345", "7")

    def test_unreadable_is_never_silently_tracked(self, monkeypatch):
        """UNAVAILABLE and MISSING both stop the read, and neither invents text."""
        for status in (retrieval.UNAVAILABLE, retrieval.MISSING):
            monkeypatch.setattr(
                retrieval, "fetch",
                lambda ref, _s=status, **kw: retrieval.Fetched(
                    ref=ref, scheme="kaggle", status=_s))
            assert sources.fetch_source("kaggle://competition/nope") is None


# ── model routing ───────────────────────────────────────────────────────────

class TestModelRouting:
    @pytest.mark.parametrize("name,provider", [
        ("hf:meta-llama/Llama-3.1-8B-Instruct", "huggingface"),
        ("huggingface:org/model", "huggingface"),
        ("local:llama3.2", "local"),
        ("ollama:qwen2.5", "local"),
        ("claude-3-5-sonnet", "anthropic"),
        ("gpt-4", "openai"),
    ])
    def test_prefixes_route_to_their_provider(self, name, provider):
        assert ModelRegistry.detect_provider(name) == provider

    def test_a_bare_repo_id_is_not_claimed(self):
        """"org/name" is also how local runtimes name models — a slash is not a signal."""
        assert ModelRegistry.detect_provider("meta-llama/Llama-3.1-8B") is None

    def test_the_org_half_survives_the_prefix_strip(self):
        """Stripping to the last segment would ask for a different model."""
        assert hf.strip_routing_prefix("hf:meta-llama/Llama-3.1-8B") == \
            "meta-llama/Llama-3.1-8B"


# ── inference ───────────────────────────────────────────────────────────────

class _Response:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("boom", request=None, response=self)


class _Client:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self._response


def _provider(response, **kwargs):
    return hf.HuggingFaceProvider(model_name="hf:org/model", api_key="",
                                  _client=_Client(response), **kwargs)


class TestHuggingFaceInference:
    def test_usage_is_recorded_from_the_response(self):
        """The reason a hosted provider is worth having beside the local one."""
        provider = _provider(_Response({
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 31, "completion_tokens": 4},
        }))
        assert provider.generate("hi") == "hello"

        usage = provider.last_usage()
        assert usage.input_tokens == 31
        assert usage.output_tokens == 4
        assert usage.admitted == 31
        assert usage.model == "org/model"

    def test_unreported_usage_is_none_not_zero(self):
        """Consumed nothing and did not say are different facts."""
        provider = _provider(_Response({"choices": [{"message": {"content": "x"}}]}))
        provider.generate("hi")
        assert provider.last_usage() is None

    def test_the_routing_prefix_never_reaches_the_wire(self):
        provider = _provider(_Response({"choices": [{"message": {"content": "x"}}]}))
        provider.generate("hi")
        assert provider._client.calls[0]["json"]["model"] == "org/model"

    def test_no_token_means_no_authorization_header(self):
        """The router serves some models anonymously; an empty bearer is not that."""
        provider = _provider(_Response({"choices": [{"message": {"content": "x"}}]}))
        provider.generate("hi")
        assert "Authorization" not in provider._client.calls[0]["headers"]

    def test_a_gated_model_says_so(self):
        provider = _provider(_Response({}, status=403))
        from agentic_cli.llm.base import ProviderError

        with pytest.raises(ProviderError) as excinfo:
            provider.generate("hi")
        assert "gated" in str(excinfo.value)

    def test_an_unserved_model_is_not_reported_as_a_broken_install(self):
        provider = _provider(_Response({}, status=404))
        from agentic_cli.llm.base import ProviderError

        with pytest.raises(ProviderError) as excinfo:
            provider.generate("hi")
        assert "not every hub model is served" in str(excinfo.value).lower()

    def test_a_model_is_required(self):
        from agentic_cli.llm.base import ProviderNotConfigured

        with pytest.raises(ProviderNotConfigured):
            hf.HuggingFaceProvider(model_name="hf:")

    def test_the_token_is_read_from_where_the_official_tooling_keeps_it(
        self, monkeypatch, tmp_path
    ):
        """Read at call time, never copied into Keel's own config."""
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        monkeypatch.setenv("HF_HOME", str(tmp_path))
        (tmp_path / "token").write_text("token-placeholder-not-a-secret\n")

        assert hf.read_token() == "token-placeholder-not-a-secret"
        assert hf.is_configured()

    def test_no_token_anywhere_is_not_an_error(self, monkeypatch, tmp_path):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        monkeypatch.setenv("HF_HOME", str(tmp_path / "absent"))
        assert hf.read_token() == ""
        assert not hf.is_configured()
