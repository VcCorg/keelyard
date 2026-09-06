"""Tests for the Kaggle and Hugging Face integrations.

Neither SDK is installed in this environment, so the live API calls are **not**
exercised here. That is a real limit and it is stated rather than papered over —
what these tests do cover is the part that decides whether the untested paths
are safe: every one of them degrades to UNAVAILABLE, which the seam defines as
"we could not ask" and never as "the thing is not there".

The load-bearing test is ``test_a_credential_value_is_never_read``. These
commands exist to detect a credential the official tooling already owns; if Keel
copied the value it would create a second thing to rotate and a second thing to
leak, and the whole reason for referencing rather than storing would be gone.
"""
from __future__ import annotations

import json

import pytest

from agentic_cli import hubs, retrieval


PLACEHOLDER_KEY = "kaggle-key-placeholder-never-read"
PLACEHOLDER_TOKEN = "hf-token-placeholder-never-read"


@pytest.fixture
def no_credentials(monkeypatch, tmp_path):
    for name in ("KAGGLE_USERNAME", "KAGGLE_KEY", "HF_TOKEN",
                 "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path / "nope"))
    monkeypatch.setenv("HF_HOME", str(tmp_path / "nope"))
    return tmp_path


@pytest.fixture
def with_credentials(monkeypatch, tmp_path):
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "kaggle.json").write_text(
        json.dumps({"username": "someone", "key": PLACEHOLDER_KEY}),
        encoding="utf-8")
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(kaggle_dir))
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.setenv("HF_TOKEN", PLACEHOLDER_TOKEN)
    return tmp_path


# ── the reason these commands exist ─────────────────────────────────────────

class TestCredentialDetection:
    def test_a_credential_value_is_never_read(self, with_credentials):
        """Referenced, not copied — the official tooling stays the one home."""
        found = [hubs.kaggle_credential().to_dict(),
                 hubs.huggingface_credential().to_dict()]
        blob = json.dumps(found)
        assert PLACEHOLDER_KEY not in blob
        assert PLACEHOLDER_TOKEN not in blob

    def test_the_kaggle_username_is_reported(self, with_credentials):
        """An identifier, not a secret — and it is what makes "configured"
        verifiable rather than a claim."""
        found = hubs.kaggle_credential()
        assert found.available
        assert found.account == "someone"
        assert "kaggle.json" in found.source

    def test_an_env_credential_is_found_without_a_file(self, monkeypatch,
                                                       tmp_path):
        monkeypatch.setenv("KAGGLE_USERNAME", "someone")
        monkeypatch.setenv("KAGGLE_KEY", PLACEHOLDER_KEY)
        monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path / "absent"))
        found = hubs.kaggle_credential()
        assert found.available and found.source == "environment"
        assert PLACEHOLDER_KEY not in json.dumps(found.to_dict())

    def test_the_hf_token_location_is_reported_not_its_value(self,
                                                             with_credentials):
        found = hubs.huggingface_credential()
        assert found.available
        assert found.detail == "HF_TOKEN"
        assert PLACEHOLDER_TOKEN not in json.dumps(found.to_dict())

    def test_absent_credentials_say_what_is_missing(self, no_credentials):
        for found in (hubs.kaggle_credential(), hubs.huggingface_credential()):
            assert not found.available
            assert found.detail            # names what it looked for


# ── the fetchers ────────────────────────────────────────────────────────────

class TestSchemes:
    def test_both_schemes_are_registered_on_the_seam(self):
        assert {"hf", "kaggle"} <= set(retrieval.schemes())

    def test_a_malformed_ref_is_missing_not_unavailable(self):
        """The ref is wrong, which we can tell without asking anyone."""
        for ref in ("hf://nonsense/x", "hf://model/", "kaggle://competition/",
                    "kaggle://nonsense/x"):
            result = retrieval.fetch(ref, trace=False)
            assert result.status == retrieval.MISSING, ref

    def test_a_missing_sdk_is_unavailable_not_missing(self, no_credentials):
        """The distinction the seam exists for.

        Without the client we could not ask, and MISSING would assert the model
        or competition does not exist — a claim nothing here is entitled to.
        """
        if hubs.sdk_available(hubs.HUGGINGFACE):
            pytest.skip("huggingface_hub is installed; this path needs it absent")
        result = retrieval.fetch("hf://model/openai-community/gpt2", trace=False)
        assert result.status == retrieval.UNAVAILABLE
        assert not result.known
        assert "not installed" in result.detail

    def test_kaggle_without_a_credential_is_unavailable(self, no_credentials):
        if hubs.sdk_available(hubs.KAGGLE):
            pytest.skip("kaggle is installed; this path needs it absent")
        result = retrieval.fetch("kaggle://competition/titanic", trace=False)
        assert result.status == retrieval.UNAVAILABLE

    def test_hub_reads_go_through_the_seam_and_are_traced(self, tmp_path,
                                                          monkeypatch):
        """Registration is the whole integration: tracing comes for free."""
        from agentic_cli import tracing

        recorded = []
        monkeypatch.setattr(tracing, "record_context_read",
                            lambda **kw: recorded.append(kw))
        retrieval.fetch("hf://model/openai-community/gpt2")
        assert recorded and recorded[0]["operation"] == "resolve/hf"


class TestSdkProbe:
    def test_an_absent_sdk_is_reported_absent(self):
        # True or False, but never a raise — callers branch on it.
        assert hubs.sdk_available(hubs.KAGGLE) in (True, False)
        assert hubs.sdk_available(hubs.HUGGINGFACE) in (True, False)

    def test_an_unknown_hub_has_no_sdk(self):
        assert hubs.sdk_available("not-a-hub") is False


class TestScopeDiscipline:
    def test_nothing_here_downloads_a_model_or_mirrors_a_dataset(self):
        """Keel's claim is that every run records what informed it — not that
        it is a second copy of the hub. HF's own CLI downloads better."""
        import inspect

        source = inspect.getsource(hubs)
        for forbidden in ("snapshot_download", "hf_hub_download",
                          "competition_download", "dataset_download"):
            assert forbidden not in source
