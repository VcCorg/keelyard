"""Per-component verdicts — G2.

Two tests carry the design. ``test_no_severity_anywhere`` extends G1's
discipline: composing components into a judgement is the governance floor's job,
and a severity field is that arithmetic smuggled in early.
``test_a_local_model_served_remotely_is_reported_as_egress`` is the finding this
phase exists for — `local:` means OpenAI-compatible, not on-host, and a
deployment whose runtime moved to a shared box is exactly where somebody is
trusting a prefix that stopped being true.

Credential *values* are never involved: these fixtures use env var names, which
is all the inventory ever holds.
"""
from __future__ import annotations

import pytest

from agentic_cli import guard, guard_findings as assessor


def _mcp(name: str, credentials: tuple[str, ...] = (), reached=None):
    return guard.Component(kind=guard.MCP, name=name, credentials=credentials,
                           reached=reached)


def _model(name: str, provider: str):
    return guard.Component(kind=guard.MODEL, name=name,
                           detail=f"provider: {provider}")


def _inventory(*components, unknown=()):
    return guard.Inventory(domain="acme", components=list(components),
                           unknown=list(unknown))


class TestScopeDiscipline:
    def test_no_severity_anywhere(self):
        """G3's arithmetic must not arrive early wearing a different name."""
        result = assessor.assess(_inventory(
            _mcp("jira", ("ATLASSIAN_TOKEN",)),
            _mcp("confluence", ("ATLASSIAN_TOKEN",)),
        ))
        blob = str(result.to_dict())
        for word in ("severity", "score", "risk", "critical", "verdict",
                     "pass", "fail"):
            assert word not in blob.lower(), f"{word} leaked into a finding"

    def test_findings_are_ordered_not_ranked(self):
        """Ordered by code so output is stable; ranking would be severity."""
        result = assessor.assess(_inventory(
            _model("gpt-4", "openai"),
            _mcp("jira", ("T",)), _mcp("confluence", ("T",)),
        ))
        codes = [f.code for f in result.findings]
        assert codes == sorted(codes, key=assessor.CODES.index)

    def test_credential_scope_is_never_guessed_from_a_name(self):
        """`ADMIN` in a variable name is not evidence of what a key can do."""
        result = assessor.assess(_inventory(
            _mcp("jira", ("JIRA_ADMIN_WRITE_TOKEN",)),
            _mcp("confluence", ("JIRA_ADMIN_WRITE_TOKEN",)),
        ))
        shared = result.of(assessor.CREDENTIAL_SHARED)
        assert shared
        for finding in shared:
            assert "not knowable from its name" in finding.limit


class TestCredentialFindings:
    def test_a_shared_credential_names_both_sides(self):
        result = assessor.assess(_inventory(
            _mcp("jira", ("ATLASSIAN_TOKEN",)),
            _mcp("confluence", ("ATLASSIAN_TOKEN",)),
        ))
        shared = result.of(assessor.CREDENTIAL_SHARED)

        assert {f.component for f in shared} == {"jira", "confluence"}
        assert dict((f.component, f.related) for f in shared) == {
            "jira": ("confluence",), "confluence": ("jira",)}

    def test_a_credential_used_by_one_server_is_not_a_finding(self):
        result = assessor.assess(_inventory(_mcp("jira", ("JIRA_TOKEN",))))
        assert result.of(assessor.CREDENTIAL_SHARED) == []

    def test_an_untouched_credentialed_server_is_reported(self):
        result = assessor.assess(_inventory(
            _mcp("confluence", ("CONFLUENCE_TOKEN",), reached=False)))
        idle = result.of(assessor.CREDENTIAL_IDLE)

        assert len(idle) == 1
        # It rests on the ledger showing no read — an absence, and it says so.
        assert idle[0].observed is False
        assert "one run is not a usage history" in idle[0].limit

    def test_no_session_means_no_idle_finding(self):
        """`reached is None` is "we did not look", not "never used"."""
        result = assessor.assess(_inventory(
            _mcp("confluence", ("CONFLUENCE_TOKEN",), reached=None)))
        assert result.of(assessor.CREDENTIAL_IDLE) == []


class TestEgressFindings:
    @pytest.mark.parametrize("name,provider,vendor", [
        ("claude-3-5-sonnet", "anthropic", "Anthropic"),
        ("gpt-4", "openai", "OpenAI"),
        ("gemini-2.5-flash", "vertex-ai", "Google Vertex AI"),
        ("hf:org/model", "huggingface", "Hugging Face"),
    ])
    def test_a_hosted_model_is_egress(self, name, provider, vendor):
        result = assessor.assess(_inventory(_model(name, provider)))
        external = result.of(assessor.EGRESS_EXTERNAL)

        assert len(external) == 1
        assert vendor in external[0].statement
        # A destination, not a judgement — the floor decides acceptability.
        assert "not a judgement" in external[0].limit

    def test_an_in_process_model_does_not_leave(self):
        result = assessor.assess(_inventory(_model("builtin", "builtin")))
        assert len(result.of(assessor.EGRESS_LOCAL)) == 1

    def test_a_local_model_on_localhost_stays_put(self, monkeypatch):
        monkeypatch.setenv("KEEL_LOCAL_LLM_URL", "http://localhost:11434/v1")
        result = assessor.assess(_inventory(_model("local:llama3.2", "local")))

        local = result.of(assessor.EGRESS_LOCAL)
        assert len(local) == 1
        assert local[0].observed is True

    def test_a_local_model_served_remotely_is_reported_as_egress(self, monkeypatch):
        """The finding this phase exists for: the prefix is not the address."""
        monkeypatch.setenv("KEEL_LOCAL_LLM_URL", "http://gpu-box.example.net:8000/v1")
        result = assessor.assess(_inventory(_model("local:llama3.2", "local")))

        external = result.of(assessor.EGRESS_EXTERNAL)
        assert len(external) == 1
        assert "gpu-box.example.net" in external[0].statement
        assert result.of(assessor.EGRESS_LOCAL) == []

    def test_an_unset_runtime_url_says_it_rests_on_the_default(self, monkeypatch):
        monkeypatch.delenv("KEEL_LOCAL_LLM_URL", raising=False)
        result = assessor.assess(_inventory(_model("local:llama3.2", "local")))

        local = result.of(assessor.EGRESS_LOCAL)
        assert len(local) == 1
        assert local[0].observed is False

    def test_an_unresolved_provider_is_unknown_not_local(self):
        """Unknown is not local — the reassuring default is the wrong one."""
        result = assessor.assess(_inventory(_model("mystery-7b", "")))
        unknown = result.of(assessor.EGRESS_UNKNOWN)

        assert len(unknown) == 1
        assert "Unknown is not local" in unknown[0].limit
        assert result.of(assessor.EGRESS_LOCAL) == []

    def test_no_model_is_an_unruled_verdict_not_a_clean_one(self):
        result = assessor.assess(_inventory(_mcp("jira", ("T",))))

        assert result.of(assessor.EGRESS_EXTERNAL) == []
        assert result.of(assessor.EGRESS_LOCAL) == []
        assert not result.complete
        assert any("egress" in u for u in result.unruled)


class TestCompleteness:
    def test_a_section_the_inventory_could_not_read_is_carried_forward(self):
        """A verdict over a section nobody enumerated was never reached either."""
        result = assessor.assess(_inventory(
            _model("gpt-4", "openai"), unknown=["mcp servers"]))

        assert not result.complete
        assert any("mcp servers" in u for u in result.unruled)
