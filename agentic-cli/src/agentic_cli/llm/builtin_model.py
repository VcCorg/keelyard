"""Built-in tiny model — downloaded on first use, served in-process.

The installer stays lean: no weights ship in the package. `keel init
builtin-model` (or the Setup panel button) downloads a small Apache-2.0 GGUF
into ``~/.keel/models`` once, and :class:`BuiltinProvider` then serves real
local inference through ``llama-cpp-python`` — no Ollama, no cloud, no keys.

Default model: Qwen2.5-0.5B-Instruct (Q4_K_M, ~400MB). Overridable via env:
    KEEL_BUILTIN_MODEL_URL    full download URL of a .gguf
    KEEL_BUILTIN_MODEL_FILE   filename under ~/.keel/models to load

Everything here is optional at runtime: if the model isn't downloaded (or
llama-cpp-python isn't installed) the provider raises and the factory's
fallback chain moves on to test-mode.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

from agentic_cli.llm.base import (
    MissingProviderSDK,
    ProviderError,
    ProviderNotConfigured,
)

MODELS_DIR = Path.home() / ".keel" / "models"

DEFAULT_MODEL_FILE = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF"
    "/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
)
DEFAULT_MODEL_LABEL = "Qwen2.5-0.5B-Instruct Q4_K_M (~400MB, Apache-2.0)"

ENV_URL = "KEEL_BUILTIN_MODEL_URL"
ENV_FILE = "KEEL_BUILTIN_MODEL_FILE"

# A GGUF this small can't be valid — guards truncated/failed downloads.
_MIN_VALID_BYTES = 10 * 1024 * 1024


def model_file() -> str:
    return os.getenv(ENV_FILE) or DEFAULT_MODEL_FILE


def model_url() -> str:
    return os.getenv(ENV_URL) or DEFAULT_MODEL_URL


def model_path() -> Path:
    return MODELS_DIR / model_file()


def is_downloaded() -> bool:
    """True when the built-in model file exists and looks complete."""
    p = model_path()
    try:
        return p.is_file() and p.stat().st_size >= _MIN_VALID_BYTES
    except OSError:
        return False


def sdk_available() -> bool:
    """True when llama-cpp-python is importable (bundled in desktop builds)."""
    try:
        import llama_cpp  # noqa: F401

        return True
    except Exception:  # noqa: BLE001 - includes native-lib load failures
        return False


def is_ready() -> bool:
    """Model on disk AND runtime importable — the fallback chain's gate."""
    return is_downloaded() and sdk_available()


def download(progress: Optional[Callable[[int, int], None]] = None,
             force: bool = False, _client=None) -> Path:
    """Download the built-in model into ~/.keel/models (streaming).

    Writes to a ``.part`` file and renames on success so a failed/interrupted
    download never masquerades as a working model. ``progress(done, total)``
    is called as bytes arrive (total may be 0 when the server omits length).
    """
    import httpx

    dest = model_path()
    if dest.exists() and not force:
        if is_downloaded():
            return dest
        dest.unlink(missing_ok=True)  # broken partial from a previous attempt

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    url = model_url()

    client = _client or httpx.Client(follow_redirects=True, timeout=60.0)
    try:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or 0)
            done = 0
            with open(part, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
        if part.stat().st_size < _MIN_VALID_BYTES:
            part.unlink(missing_ok=True)
            raise ProviderError(
                f"Downloaded file is too small to be a valid model "
                f"({part.name}); the URL may be wrong: {url}")
        part.replace(dest)
        return dest
    except ProviderError:
        raise
    except Exception as e:  # noqa: BLE001 - network/disk
        part.unlink(missing_ok=True)
        raise ProviderError(f"Model download failed: {e}") from e
    finally:
        if _client is None:
            client.close()


def remove() -> bool:
    """Delete the downloaded model; True if something was removed."""
    p = model_path()
    if p.exists():
        p.unlink()
        return True
    return False


class BuiltinProvider:
    """In-process inference over the downloaded GGUF via llama-cpp-python."""

    _llm = None          # cached llama_cpp.Llama across instances
    _llm_path = None     # path the cache was loaded from

    def __init__(self, model_name: Optional[str] = None,
                 system_instruction: Optional[str] = None,
                 n_ctx: int = 4096):
        self.system_instruction = system_instruction
        self.n_ctx = n_ctx
        self.model_name = model_file()
        if not is_downloaded():
            raise ProviderNotConfigured(
                "Built-in model is not downloaded. Run: keel init builtin-model")

    def _load(self):
        try:
            from llama_cpp import Llama
        except Exception as e:  # noqa: BLE001
            raise MissingProviderSDK(
                "llama-cpp-python is not available in this install "
                f"(pip install llama-cpp-python): {e}") from e
        path = str(model_path())
        cls = type(self)
        if cls._llm is None or cls._llm_path != path:
            # verbose=False keeps llama.cpp's banner out of server logs.
            cls._llm = Llama(model_path=path, n_ctx=self.n_ctx, verbose=False)
            cls._llm_path = path
        return cls._llm

    def _messages(self, prompt: str) -> list[dict]:
        msgs = []
        if self.system_instruction:
            msgs.append({"role": "system", "content": self.system_instruction})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def generate(self, prompt: str) -> str:
        llm = self._load()
        try:
            out = llm.create_chat_completion(messages=self._messages(prompt),
                                             temperature=0.2)
            return out["choices"][0]["message"]["content"] or ""
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Built-in model inference failed: {e}") from e

    async def generate_async(self, prompt: str) -> str:
        import asyncio

        return await asyncio.to_thread(self.generate, prompt)

    async def generate_streaming(self, prompt: str) -> AsyncGenerator[str, None]:
        # llama-cpp streams synchronously; chunk the full result instead of
        # blocking the event loop per-token.
        text = await self.generate_async(prompt)
        for i in range(0, len(text), 64):
            yield text[i:i + 64]

    def get_name(self) -> str:
        return f"builtin/{self.model_name}"
