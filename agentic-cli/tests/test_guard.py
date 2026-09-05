"""Tests for the KeelGuard inventory — what a session can reach.

The load-bearing test is ``test_a_credential_value_never_enters_the_inventory``.
An inventory that leaked the secrets it inventoried would be the worst possible
version of this feature, so the values are never read rather than read and
masked — and the test asserts against the serialised form, which is what would
actually reach a file or an API response.

``test_reached_is_unknown_without_a_session`` is the other one: "we did not look"
and "configured and never used" are different facts, and only one of them is a
reason to remove something.
"""
from __future__ import annotations

import json

import pytest

from agentic_cli import guard


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    from agentic_cli import tracker

    db_dir = tmp_path / ".keel-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    tracker._ensure_db()
    yield db_dir


#: A sentinel the test searches for, carrying the word "placeholder" on purpose.
#:
#: The repository's own company-data guard reads `SECRET = "<20+ chars>"` as a
#: hardcoded credential — correctly — and exempts values that name themselves as
#: placeholders. Bypassing that check inside a test about not leaking
#: credentials would be precisely the wrong lesson, so this takes the exemption
#: the guard offers instead.
SECRET = "canary-placeholder-never-serialised"


@pytest.fixture
def registry(monkeypatch):
    from agentic_cli.mcp import config as mcpcfg

    reg = mcpcfg.MCPRegistry(servers={
        "jira": mcpcfg.MCPServer(name="jira", type="http", transport="sse",
                                 url="http://localhost:9001/sse",
                                 env={"JIRA_API_TOKEN": SECRET}),
        "confluence": mcpcfg.MCPServer(name="confluence", type="http",
                                       transport="sse",
                                       url="http://localhost:9002/sse",
                                       env={"CONFLUENCE_TOKEN": SECRET}),
        "filesystem": mcpcfg.MCPServer(name="filesystem", type="stdio",
                                       command="npx", enabled=False),
    })
    monkeypatch.setattr(mcpcfg, "load_registry", lambda: reg)
    return reg


# ── the disclosure boundary ─────────────────────────────────────────────────

class TestCredentials:
    def test_a_credential_value_never_enters_the_inventory(self, registry):
        """Asserted against the serialised form — that is what leaves the process."""
        inventory = guard.collect()
        assert SECRET not in json.dumps(inventory.to_dict())
        assert SECRET not in repr(inventory)

    def test_credential_names_are_reported(self, registry):
        """Knowing a server is handed a key is the useful, safe half."""
        inventory = guard.collect()
        jira = next(c for c in inventory.of(guard.MCP) if c.name == "jira")
        assert jira.credentials == ("JIRA_API_TOKEN",)
        assert jira.credentialed

    def test_a_server_with_no_credentials_is_not_credentialed(self, registry):
        inventory = guard.collect()
        fs = next(c for c in inventory.of(guard.MCP) if c.name == "filesystem")
        assert fs.credentials == ()
        assert not fs.credentialed

    def test_the_credentialed_set_is_the_ones_holding_keys(self, registry):
        inventory = guard.collect()
        assert {c.name for c in inventory.credentialed} == {"jira", "confluence"}


# ── configured versus reached ───────────────────────────────────────────────

class TestReached:
    def test_reached_is_unknown_without_a_session(self, registry):
        """Not False — "we did not look" is not "configured and unused"."""
        inventory = guard.collect()
        for component in inventory.of(guard.MCP):
            assert component.reached is None
            assert not component.unused

    def test_a_session_separates_touched_from_untouched(self, registry):
        from agentic_cli import tracing

        with tracing.session_scope("sess-1", domain="payments"):
            tracing.record_context_read(source="mcp", operation="jira/get_issue",
                                        size_bytes=100, payload="body " * 20)

        inventory = guard.collect(session_id="sess-1")
        by_name = {c.name: c for c in inventory.of(guard.MCP)}
        assert by_name["jira"].reached is True
        assert by_name["confluence"].reached is False
        assert by_name["confluence"].unused

    def test_unused_is_the_surface_carried_for_nothing(self, registry):
        """The most actionable output: credentialed and never touched."""
        from agentic_cli import tracing

        with tracing.session_scope("sess-1", domain="payments"):
            tracing.record_context_read(source="mcp", operation="jira/get_issue",
                                        size_bytes=100, payload="body " * 20)

        inventory = guard.collect(session_id="sess-1")
        unused = {c.name for c in inventory.unused}
        assert "confluence" in unused
        assert "jira" not in unused


# ── completeness ────────────────────────────────────────────────────────────

class TestCompleteness:
    def test_a_disabled_component_is_listed_not_dropped(self, registry):
        """It is one config edit from being live, so it is still surface."""
        inventory = guard.collect()
        fs = next(c for c in inventory.of(guard.MCP) if c.name == "filesystem")
        assert not fs.enabled

    def test_a_section_that_cannot_be_enumerated_is_named(self, registry,
                                                          monkeypatch):
        """A Bill of Materials missing a section silently reads as a clean bill."""
        import agentic_cli.guard as g

        monkeypatch.setattr(
            g, "_mcp", lambda domain: (_ for _ in ()).throw(OSError("no registry")))
        inventory = guard.collect()
        assert "mcp servers" in inventory.unknown
        assert not inventory.complete

    def test_one_broken_section_does_not_lose_the_others(self, registry,
                                                         monkeypatch):
        import agentic_cli.guard as g

        monkeypatch.setattr(
            g, "_engine", lambda domain: (_ for _ in ()).throw(RuntimeError("x")))
        inventory = guard.collect()
        assert inventory.of(guard.MCP)          # still enumerated
        assert "engine" in inventory.unknown

    def test_an_empty_inventory_is_complete_not_broken(self, monkeypatch):
        import agentic_cli.guard as g
        from agentic_cli.mcp import config as mcpcfg

        monkeypatch.setattr(mcpcfg, "load_registry",
                            lambda: mcpcfg.MCPRegistry(servers={}))
        monkeypatch.setattr(g, "_engine", lambda domain: [])
        inventory = guard.collect()
        assert inventory.complete


class TestScopeDiscipline:
    def test_phase_one_scores_nothing(self):
        """Composing components into a verdict is policy, and policy lives with
        the governance floor — not invented here."""
        import inspect

        source = inspect.getsource(guard)
        for forbidden in ("risk_score", "def score", "def verdict",
                          "DO_NOT_INSTALL", "def assess"):
            assert forbidden not in source
