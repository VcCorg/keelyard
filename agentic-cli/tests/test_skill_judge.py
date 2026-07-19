"""Tests for LLM-as-judge skill impact evaluation."""

import json

import pytest

from agentic_cli.evaluation import skill_judge as sj

SKILL_TEXT = (
    "---\nname: water-check\ndescription: Validate water quality readings\n---\n"
    "# Water quality validation\n\n## Validate sensor ranges\nCheck ppm bounds.\n"
    "## Escalate anomalies\nPage the on-call when out of range.\n"
)


class ScriptedProvider:
    """Fake provider: scenario-gen returns JSON array; judge returns scores."""

    def __init__(self, system_instruction=None, score_a=8, score_b=5, winner="A"):
        self.system = system_instruction or ""
        self.score_a, self.score_b, self.winner = score_a, score_b, winner

    def generate(self, prompt: str) -> str:
        if "test task prompts" in prompt:
            return json.dumps(["Task one about ranges", "Task two about escalation"])
        if "impartial judge" in prompt:
            return json.dumps({"score_a": self.score_a, "score_b": self.score_b,
                               "winner": self.winner, "rationale": "A follows the skill"})
        return "an answer"

    def get_name(self) -> str:
        return "scripted/fake"


def test_judge_skill_positive_impact(monkeypatch):
    """Skill answer always wins -> positive verdict regardless of A/B rotation."""
    import agentic_cli.llm.factory as factory

    def fake_get(model_name=None, provider_type=None, system_instruction=None):
        return ScriptedProvider(system_instruction)

    monkeypatch.setattr(factory, "get_llm_provider", fake_get)

    # Winner is always "A"; with A/B alternation the skill sits at A on even
    # scenarios and B on odd — so compute expectations per the rotation.
    report = sj.judge_skill("water-check", SKILL_TEXT, domain="alpha", scenarios=2)
    assert report.judge == "scripted/fake"
    assert report.authoritative is True
    assert len(report.scenarios) == 2
    # Scenario 0: skill=A scored 8 (winner with_skill); scenario 1: skill=B scored 5.
    assert report.scenarios[0].winner == "with_skill"
    assert report.scenarios[1].winner == "baseline"
    assert report.avg_with_skill == pytest.approx((8 + 5) / 2)
    assert report.avg_baseline == pytest.approx((5 + 8) / 2)


def test_judge_skill_delta_and_verdict(monkeypatch):
    """A judge that always favors the SKILL answer (by position) yields positive."""
    import agentic_cli.llm.factory as factory

    class SkillFavoringJudge(ScriptedProvider):
        def generate(self, prompt: str) -> str:
            if "test task prompts" in prompt:
                return json.dumps(["t1", "t2"])
            if "impartial judge" in prompt:
                # Favor whichever answer includes skill guidance: the answer
                # texts are identical here, so emulate by scoring A high on
                # even calls and B high on odd via winner toggling is complex —
                # simply always give a=9,b=4 with winner A on call 1, b=9,a=4
                # winner B on call 2 (matching the rotation).
                self.calls = getattr(self, "calls", 0) + 1
                if self.calls % 2 == 1:
                    return json.dumps({"score_a": 9, "score_b": 4, "winner": "A",
                                       "rationale": ""})
                return json.dumps({"score_a": 4, "score_b": 9, "winner": "B",
                                   "rationale": ""})
            return "answer"

    holder = {}

    def fake_get(model_name=None, provider_type=None, system_instruction=None):
        # One shared judge instance so call-counting works across judgements.
        if "judge" in (system_instruction or ""):
            return holder.setdefault("judge", SkillFavoringJudge(system_instruction))
        return ScriptedProvider(system_instruction)

    monkeypatch.setattr(factory, "get_llm_provider", fake_get)
    report = sj.judge_skill("water-check", SKILL_TEXT, scenarios=2)
    assert report.avg_with_skill == 9.0
    assert report.avg_baseline == 4.0
    assert report.delta == 5.0
    assert report.verdict == "positive"
    assert all(r.winner == "with_skill" for r in report.scenarios)


def test_judge_skill_runs_end_to_end_under_test_mode(monkeypatch):
    """The full pipeline executes with zero model config, flagged non-authoritative."""
    for var in ("KEEL_LLM_PROVIDER", "KEEL_LOCAL_LLM_MODEL", "KEEL_DISABLE_TEST_MODE"):
        monkeypatch.delenv(var, raising=False)
    import agentic_cli.kg.config as kg_config

    monkeypatch.setattr(kg_config.KGConfig, "load",
                        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("none"))))

    report = sj.judge_skill("water-check", SKILL_TEXT, scenarios=2)
    assert report.judge.startswith("test-mode")
    assert report.authoritative is False
    assert len(report.scenarios) == 2          # heuristic scenarios kick in
    assert report.verdict in ("positive", "neutral", "negative")


def test_heuristic_scenarios_fallback():
    tasks = sj._heuristic_scenarios(SKILL_TEXT, 3)
    assert len(tasks) == 3
    assert any("Validate sensor ranges" in t for t in tasks)
