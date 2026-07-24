"""Registry-driven code-assist tool selection.

Pins the contract every dispatch site depends on:

  * builtin tools are registered on import (devin, cursor, generic, windsurf)
  * windsurf is marked deprecated (post-migration) but still resolvable
  * layout strategies (skills_dir / graphify / persona_context) match what
    the old hardcoded dispatch produced — proves the refactor didn't
    silently change on-disk paths
  * only tools that need a user-level bridge declare one (Windsurf today)
  * `resolve_tool_name('auto')` triggers detection; unknown names degrade
    to generic instead of raising
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agentic_cli.code_assist import (
    CodeAssistTool,
    ToolNotFoundError,
    detect_tool,
    get_tool,
    list_tools,
    register_tool,
    resolve_tool_name,
)


# ── Registration invariants ────────────────────────────────────────────────


def test_builtin_tools_registered():
    """devin / cursor / generic / windsurf are always registered."""
    names = {t.name for t in list_tools()}
    assert {"devin", "cursor", "generic", "windsurf"} <= names


def test_windsurf_is_deprecated_but_resolvable():
    """Post-migration Windsurf keeps working; new installs shouldn't prefer it."""
    tool = get_tool("windsurf")
    assert tool.deprecated is True
    # Non-deprecated tools come first in list_tools(); deprecated last.
    order = [t.name for t in list_tools()]
    assert order.index("windsurf") == len(order) - 1 or all(
        list_tools()[i].deprecated for i in range(order.index("windsurf"), len(order))
    )


def test_get_tool_raises_on_unknown():
    with pytest.raises(ToolNotFoundError):
        get_tool("does-not-exist")


# ── Layout parity with the old hardcoded dispatch ──────────────────────────


def test_skills_dir_matches_pre_refactor():
    """`skills_dir(project)` must resolve to the same paths the old branches did."""
    p = Path("/tmp/proj")
    assert get_tool("cursor").skills_dir(p) == p / ".cursorrules"
    assert get_tool("devin").skills_dir(p) == p / ".devin" / "skills"
    assert get_tool("generic").skills_dir(p) == p / ".skills"
    assert get_tool("windsurf").skills_dir(p) == p / ".skills"


def test_graphify_layout_matches_pre_refactor():
    """Per-tool graphify dest + frontmatter shape matches the pre-refactor branches."""
    p = Path("/tmp/proj")
    assert get_tool("devin").graphify_layout(p) == (
        p / ".devin" / "skills" / "graphify" / "SKILL.md", "name",
    )
    assert get_tool("cursor").graphify_layout(p) == (
        p / ".cursor" / "rules" / "graphify.md", "description-only",
    )
    assert get_tool("generic").graphify_layout(p) == (
        p / ".skills" / "graphify" / "SKILL.md", "name",
    )
    assert get_tool("windsurf").graphify_layout(p) == (
        p / ".skills" / "graphify" / "SKILL.md", "name",
    )


def test_persona_context_path_matches_pre_refactor():
    """Persona context files land at the pre-refactor per-tool locations."""
    root = Path("/tmp/proj")
    name = "dev-context"
    assert get_tool("devin").persona_context_path(root, name) == (
        root / ".devin" / "skills" / name / "SKILL.md"
    )
    assert get_tool("cursor").persona_context_path(root, name) == (
        root / ".cursor" / "rules" / f"{name}.md"
    )
    assert get_tool("generic").persona_context_path(root, name) == (
        root / ".skills" / name / "SKILL.md"
    )
    assert get_tool("windsurf").persona_context_path(root, name) == (
        root / ".windsurf" / "workflows" / f"{name}.md"
    )


# ── Bridge strategy ────────────────────────────────────────────────────────


def test_only_windsurf_declares_bridge():
    """Cursor / Devin / generic read from the repo — no user-level bridge."""
    assert get_tool("windsurf").bridge_to_user_dir is not None
    for name in ("devin", "cursor", "generic"):
        assert get_tool(name).bridge_to_user_dir is None


# ── Name resolution & detection ────────────────────────────────────────────


def test_resolve_tool_name_passthrough_for_known():
    assert resolve_tool_name("devin") == "devin"
    assert resolve_tool_name("cursor") == "cursor"
    assert resolve_tool_name("windsurf") == "windsurf"


def test_resolve_tool_name_unknown_falls_back_to_generic():
    """An unknown explicit name must not brick onboard — degrade gracefully."""
    assert resolve_tool_name("no-such-tool") == "generic"


def test_resolve_tool_name_auto_triggers_detection(monkeypatch):
    """`auto` runs detect_tool(); env override wins if valid."""
    monkeypatch.setenv("KEEL_CODE_ASSIST_TOOL", "devin")
    assert resolve_tool_name("auto") == "devin"
    assert resolve_tool_name(None) == "devin"


def test_detect_tool_env_override_wins(monkeypatch):
    monkeypatch.setenv("KEEL_CODE_ASSIST_TOOL", "cursor")
    assert detect_tool() == "cursor"


def test_detect_tool_env_override_ignores_unknown(monkeypatch):
    """A typo in the env var must not short-circuit real detection."""
    monkeypatch.setenv("KEEL_CODE_ASSIST_TOOL", "junk")
    # No env markers set below, so detection should fall through to the
    # `default` argument — proving the junk override was skipped.
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("DEVIN_SESSION_ID", raising=False)
    # Point HOME at an empty dir so cursor/windsurf detectors return False.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("HOME", tmp)
        assert detect_tool() == "generic"


def test_detect_tool_prefers_devin_env(monkeypatch):
    """Post-migration: DEVIN_API_KEY beats a Windsurf install on the same box."""
    monkeypatch.setenv("DEVIN_API_KEY", "sk-...")
    monkeypatch.delenv("KEEL_CODE_ASSIST_TOOL", raising=False)
    assert detect_tool() == "devin"


def test_detect_tool_falls_back_to_generic(monkeypatch):
    """No markers, no installed IDEs → generic (never a deprecated tool)."""
    monkeypatch.delenv("KEEL_CODE_ASSIST_TOOL", raising=False)
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("DEVIN_SESSION_ID", raising=False)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("HOME", tmp)
        assert detect_tool() == "generic"


# ── Extensibility ──────────────────────────────────────────────────────────


def test_register_tool_adds_a_new_ide(monkeypatch):
    """Adding a new IDE is one register_tool() — no dispatch changes needed."""
    def _my_ide_dir(p: Path) -> Path:
        return p / ".my-ide" / "skills"

    tool = CodeAssistTool(
        name="my-ide-test",
        label="MyIDE (test)",
        description="Test tool for the extensibility contract.",
        skills_dir=_my_ide_dir,
    )
    register_tool(tool)
    try:
        assert get_tool("my-ide-test").skills_dir(Path("/tmp/proj")) == (
            Path("/tmp/proj") / ".my-ide" / "skills"
        )
        assert resolve_tool_name("my-ide-test") == "my-ide-test"
    finally:
        # Clean up so we don't leak the test tool into other tests.
        from agentic_cli.code_assist.tools import _REGISTRY
        _REGISTRY.pop("my-ide-test", None)


def test_broken_detector_does_not_crash(monkeypatch):
    """A tool with a raising detect() must not brick detect_tool()."""
    def _boom() -> bool:
        raise RuntimeError("simulated")

    tool = CodeAssistTool(
        name="boom-test", label="Boom", description="", detect=_boom,
    )
    register_tool(tool)
    try:
        # No DEVIN_* / no HOME markers → we should fall through boom's raise
        # and land on generic (never propagate the error).
        monkeypatch.delenv("KEEL_CODE_ASSIST_TOOL", raising=False)
        monkeypatch.delenv("DEVIN_API_KEY", raising=False)
        monkeypatch.delenv("DEVIN_SESSION_ID", raising=False)
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("HOME", tmp)
            assert detect_tool() == "generic"
    finally:
        from agentic_cli.code_assist.tools import _REGISTRY
        _REGISTRY.pop("boom-test", None)
