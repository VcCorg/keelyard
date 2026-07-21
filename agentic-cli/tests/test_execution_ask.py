"""Tests for the vendor-neutral ask() capability + the IDE handoff engine."""

from agentic_cli.execution import (
    AskResult,
    ExecutionSpec,
    ask,
    list_engines,
    register,
)
from agentic_cli.execution.ide_adapter import VSCodeCopilotEngine


def test_registry_includes_ide_engine_with_capabilities():
    infos = {i.name: i for i in list_engines()}
    assert {"devin", "local", "vscode-copilot"} <= set(infos)
    assert infos["vscode-copilot"].kind == "ide"
    # The local engine can answer; the IDE handoff cannot (headless).
    assert infos["local"].supports_ask is True
    assert infos["vscode-copilot"].supports_ask is False


def test_ask_unsupported_engine_is_not_authoritative():
    r = ask(ExecutionSpec(prompt="what is this?"), engine="vscode-copilot")
    assert isinstance(r, AskResult)
    assert r.engine == "vscode-copilot"
    assert r.authoritative is False
    assert "ask" in r.answer.lower() or "open" in r.answer.lower()


def test_ask_routes_to_engine():
    class FakeEngine:
        name = "fake-ask"

        def info(self):  # pragma: no cover - unused here
            ...

        def ask(self, spec):
            return AskResult(engine=self.name, answer=f"echo:{spec.prompt}", authoritative=True)

    register("fake-ask", lambda: FakeEngine())
    r = ask(ExecutionSpec(prompt="hello"), engine="fake-ask")
    assert r.answer == "echo:hello" and r.authoritative is True


def test_local_ask_uses_llm_and_flags_test_mode(monkeypatch):
    import agentic_cli.llm.factory as factory

    class P:
        def generate(self, prompt):
            return "grounded answer"

        def get_name(self):
            return "test-mode-deterministic"

    monkeypatch.setattr(factory, "get_llm_provider", lambda **k: P())
    from agentic_cli.execution.local_adapter import LocalContextEngine

    r = LocalContextEngine().ask(ExecutionSpec(prompt="q", domain=""))
    assert r.engine == "local" and r.answer == "grounded answer"
    # test-mode provider → non-authoritative.
    assert r.authoritative is False


def test_vscode_handoff_prepares_context_and_instructions():
    r = VSCodeCopilotEngine().create_session(ExecutionSpec(prompt="build x", dry_run=True))
    assert r.engine == "vscode-copilot"
    assert r.raw.get("handoff") == "vscode-copilot"
    assert "instructions" in r.raw and r.raw["instructions"]
    assert r.dry_run is True
