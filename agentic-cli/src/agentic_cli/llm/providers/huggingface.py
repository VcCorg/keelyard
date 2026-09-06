"""Hugging Face Inference — OpenAI-compatible chat completions over HTTP.

Models are addressed by hub repo id with an explicit routing prefix:
``hf:meta-llama/Llama-3.1-8B-Instruct``. The prefix is what makes routing a
registry lookup rather than a guess — a bare ``meta-llama/…`` is indistinguishable
from a local runtime's model name, and inferring the provider from a slash would
be exactly the kind of hardcoded branch this codebase has already removed once.

**No SDK.** The router speaks the OpenAI chat API, so this uses ``httpx`` — a
core dependency — rather than ``huggingface_hub``. The hub SDK is still what the
``hf://`` *fetcher* needs (cards, revisions, dataset info); inference does not
need it, and requiring it would have put a redistributable dependency in the
path of a feature that does not use it (see NOTICE).

**The token is read, not copied.** ``keel init huggingface`` records only where
the credential lives, deliberately (see :mod:`agentic_cli.hubs`). Inference has
to actually send it, so it is read from the same places the official tooling
reads, at call time, and never written anywhere by Keel.

**Usage is reported.** The router returns OpenAI-shaped ``usage``, so a call
through here lands in the ledger with real input and output token counts rather
than an estimate — which is the whole reason a hosted provider is worth having
beside the local one.

Configuration (env):
    HF_TOKEN / HUGGING_FACE_HUB_TOKEN   access token (or `huggingface-cli login`)
    KEEL_HF_BASE_URL                    override the router base URL
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from agentic_cli.llm.base import ProviderError, ProviderNotConfigured, Usage

#: The hub's OpenAI-compatible inference router.
DEFAULT_BASE_URL = "https://router.huggingface.co/v1"

ENV_BASE_URL = "KEEL_HF_BASE_URL"

_ROUTING_PREFIXES = ("hf:", "huggingface:")


def strip_routing_prefix(model_name: str) -> str:
    """Drop the ``hf:``/``huggingface:`` prefix, leaving the hub repo id.

    Only the prefix goes. ``hf:meta-llama/Llama-3.1-8B-Instruct`` addresses the
    repo ``meta-llama/Llama-3.1-8B-Instruct``, and the org half is part of the
    id — stripping to the last path segment would silently ask for a different
    model that may well exist under another org.
    """
    lower = (model_name or "").lower()
    for prefix in _ROUTING_PREFIXES:
        if lower.startswith(prefix):
            return model_name[len(prefix):]
    return model_name


def read_token() -> str:
    """The access token, from wherever the official tooling keeps it.

    Order matches ``huggingface_hub``'s own: environment first, then the cached
    login. Returns an empty string rather than raising — some router models
    serve anonymously, and refusing to try would report a configuration problem
    where there is none.
    """
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        value = os.getenv(name)
        if value:
            return value.strip()

    home = os.getenv("HF_HOME") or str(Path.home() / ".cache" / "huggingface")
    path = Path(home).expanduser() / "token"
    try:
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    except OSError:
        return ""


def is_configured() -> bool:
    """True when a token is available. Not required, but it is what usually gates access."""
    return bool(read_token())


def _usage_from(data: dict, model: str) -> Optional[Usage]:
    """The reported usage, or None when the router omitted it.

    None rather than a zeroed :class:`Usage`: a call that consumed nothing and a
    call whose cost went unreported are different facts, and the ledger records
    them differently — one as zero, the other as an estimate from the text.
    """
    raw = (data or {}).get("usage")
    if not isinstance(raw, dict):
        return None
    return Usage(
        input_tokens=int(raw.get("prompt_tokens") or 0),
        output_tokens=int(raw.get("completion_tokens") or 0),
        model=model,
    )


class HuggingFaceProvider:
    """Chat completions against the Hugging Face inference router."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        system_instruction: Optional[str] = None,
        timeout: float = 120.0,
        _client=None,
    ):
        model = strip_routing_prefix(model_name or "")
        if not model:
            raise ProviderNotConfigured(
                "No Hugging Face model named. Pass one as hf:<org>/<name>, e.g. "
                "hf:meta-llama/Llama-3.1-8B-Instruct"
            )
        self.model_name = model
        self.base_url = (base_url or os.getenv(ENV_BASE_URL)
                         or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else read_token()
        self.system_instruction = system_instruction
        self.timeout = timeout
        self._client = _client  # test seam: injected httpx.Client
        self._last_usage: Optional[Usage] = None

    # ── internals ────────────────────────────────────────────────────────────
    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _messages(self, prompt: str) -> list[dict]:
        msgs = []
        if self.system_instruction:
            msgs.append({"role": "system", "content": self.system_instruction})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def _payload(self, prompt: str, stream: bool = False) -> dict:
        return {"model": self.model_name, "messages": self._messages(prompt),
                "stream": stream}

    def _extract(self, data: dict) -> str:
        self._last_usage = _usage_from(data, self.model_name)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                f"Unexpected response shape from the Hugging Face router: {exc}"
            )

    def _explain(self, exc) -> ProviderError:
        """Turn an HTTP failure into something a user can act on.

        401/403 is the one worth naming: the router serves plenty of models
        anonymously, so an unauthenticated call fails only on the gated ones,
        and "not authorized" without that context reads as a broken install.
        """
        status = getattr(getattr(exc, "response", None), "status_code", 0)
        if status in (401, 403):
            return ProviderError(
                f"Hugging Face refused the request for '{self.model_name}' "
                f"(HTTP {status}). The model is gated or the token lacks "
                f"inference access — check `keel init huggingface`, and accept "
                f"the model's licence on its hub page if it has one."
            )
        if status == 404:
            return ProviderError(
                f"The router has no inference endpoint for '{self.model_name}'. "
                f"Not every hub model is served — check the model page for a "
                f"deployed provider."
            )
        return ProviderError(f"Hugging Face inference failed: {exc}")

    # ── LLMProvider protocol ─────────────────────────────────────────────────
    def generate(self, prompt: str) -> str:
        import httpx

        url = f"{self.base_url}/chat/completions"
        try:
            if self._client is not None:
                resp = self._client.post(url, json=self._payload(prompt),
                                         headers=self._headers())
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=self._payload(prompt),
                                       headers=self._headers())
            resp.raise_for_status()
            return self._extract(resp.json())
        except httpx.HTTPStatusError as exc:
            raise self._explain(exc)
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Cannot reach the Hugging Face router at {self.base_url}: {exc}"
            )

    async def generate_async(self, prompt: str) -> str:
        import httpx

        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=self._payload(prompt),
                                         headers=self._headers())
            resp.raise_for_status()
            return self._extract(resp.json())
        except httpx.HTTPStatusError as exc:
            raise self._explain(exc)
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Cannot reach the Hugging Face router at {self.base_url}: {exc}"
            )

    async def generate_streaming(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream deltas. Usage arrives only on the final chunk, if at all."""
        import httpx

        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url,
                                         json=self._payload(prompt, stream=True),
                                         headers=self._headers()) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        body = line[5:].strip()
                        if not body or body == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(body)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(chunk.get("usage"), dict):
                            self._last_usage = _usage_from(chunk, self.model_name)
                        delta = ((chunk.get("choices") or [{}])[0]
                                 .get("delta") or {}).get("content")
                        if delta:
                            yield delta
        except httpx.HTTPStatusError as exc:
            raise self._explain(exc)
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Cannot reach the Hugging Face router at {self.base_url}: {exc}"
            )

    def get_name(self) -> str:
        return f"huggingface/{self.model_name}"

    def last_usage(self) -> Optional[Usage]:
        """What the last call consumed, as the router reported it."""
        return self._last_usage


__all__ = ["HuggingFaceProvider", "DEFAULT_BASE_URL", "strip_routing_prefix",
           "read_token", "is_configured"]
