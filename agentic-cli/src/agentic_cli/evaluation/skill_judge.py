"""LLM-as-judge skill impact evaluation.

Answers the question a scorecard can't: *does this skill actually improve an
agent's output?* For N generated scenarios the model answers twice — once WITH
the skill's guidance in context, once WITHOUT (baseline) — and an LLM judge
scores both on a rubric, blind to which is which. The aggregate delta is the
skill's measured impact.

Built on the platform's provider chain (``get_llm_provider``) so it runs on
Vertex, a local Ollama/LM Studio model, or the downloadable built-in model.
Under the test-mode fallback the pipeline still executes end-to-end but the
report is clearly labeled non-authoritative.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

RUBRIC = ("task_adherence", "actionability", "correctness")


@dataclass
class ScenarioResult:
    scenario: str
    with_skill_score: float
    baseline_score: float
    winner: str          # with_skill | baseline | tie
    rationale: str = ""


@dataclass
class SkillJudgeReport:
    skill: str
    domain: str
    judge: str                        # provider name, e.g. local/llama3.2
    scenarios: List[ScenarioResult] = field(default_factory=list)
    avg_with_skill: float = 0.0
    avg_baseline: float = 0.0
    delta: float = 0.0
    verdict: str = "neutral"          # positive | neutral | negative
    authoritative: bool = True        # False when judged by test-mode

    def to_dict(self) -> dict:
        return {
            "skill": self.skill, "domain": self.domain, "judge": self.judge,
            "avg_with_skill": self.avg_with_skill, "avg_baseline": self.avg_baseline,
            "delta": self.delta, "verdict": self.verdict,
            "authoritative": self.authoritative,
            "scenarios": [vars(s) for s in self.scenarios],
        }


def _first_json(text: str):
    m = re.search(r"\[.*\]|\{.*\}", text or "", re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _heuristic_scenarios(skill_text: str, n: int) -> List[str]:
    """Fallback scenario derivation from the skill's own headings/sentences."""
    heads = re.findall(r"^#{1,3}\s+(.+)$", skill_text, re.MULTILINE)
    base = [h.strip() for h in heads if len(h.strip()) > 4][: n]
    out = [f"Complete this task correctly: {h}" for h in base]
    while len(out) < n:
        out.append(f"Apply this skill's guidance to a realistic task ({len(out) + 1}).")
    return out[:n]


def _generate_scenarios(provider, skill_text: str, domain: str, n: int) -> List[str]:
    raw = provider.generate(
        f"From this agent skill, write {n} short, concrete test task prompts a "
        f"user in the '{domain or 'general'}' domain might ask. Return ONLY a "
        "JSON array of strings.\n\nSKILL:\n" + skill_text[:4000])
    data = _first_json(raw)
    if isinstance(data, list) and all(isinstance(x, str) for x in data) and data:
        return [x.strip() for x in data][:n]
    return _heuristic_scenarios(skill_text, n)


def _answer(provider_factory, scenario: str, skill_text: Optional[str]) -> str:
    system = ("Answer the task. Follow this skill's guidance exactly:\n" + skill_text[:5000]
              if skill_text else "Answer the task using only general knowledge.")
    provider = provider_factory(system)
    return provider.generate(scenario)[:4000]


def _judge_pair(provider, scenario: str, a: str, b: str) -> dict:
    """Blind pairwise judgement — A/B order hides which answer used the skill."""
    raw = provider.generate(
        "You are an impartial judge. Score the two answers to the task on "
        f"{', '.join(RUBRIC)} (1-10 overall each) and pick a winner. Return ONLY "
        'a JSON object: {"score_a": n, "score_b": n, "winner": "A"|"B"|"tie", '
        '"rationale": "one sentence"}.\n\n'
        f"TASK:\n{scenario}\n\nANSWER A:\n{a}\n\nANSWER B:\n{b}")
    data = _first_json(raw) or {}
    try:
        return {
            "score_a": float(data.get("score_a", 5)),
            "score_b": float(data.get("score_b", 5)),
            "winner": str(data.get("winner", "tie")).strip().lower(),
            "rationale": str(data.get("rationale", ""))[:300],
        }
    except (TypeError, ValueError):
        return {"score_a": 5.0, "score_b": 5.0, "winner": "tie", "rationale": ""}


def judge_skill(skill_name: str, skill_text: str, domain: str = "",
                scenarios: int = 3, model: Optional[str] = None) -> SkillJudgeReport:
    """Run the LLM-as-judge impact evaluation for a skill."""
    from agentic_cli.llm.factory import get_llm_provider

    def factory(system: Optional[str] = None):
        return get_llm_provider(model_name=model, system_instruction=system)

    gen = factory("You design evaluation scenarios. Answer strict JSON.")
    judge_name = gen.get_name()
    authoritative = not judge_name.startswith("test-mode")

    n = max(1, min(scenarios, 5))
    tasks = _generate_scenarios(gen, skill_text, domain, n)

    judge = factory("You are a strict, impartial evaluation judge. Answer strict JSON.")
    results: List[ScenarioResult] = []
    for i, task in enumerate(tasks):
        with_ans = _answer(factory, task, skill_text)
        base_ans = _answer(factory, task, None)
        # Alternate A/B assignment so ordering bias can't systematically favor
        # the skill answer.
        skill_is_a = (i % 2 == 0)
        verdictd = _judge_pair(judge, task,
                               with_ans if skill_is_a else base_ans,
                               base_ans if skill_is_a else with_ans)
        ws = verdictd["score_a"] if skill_is_a else verdictd["score_b"]
        bs = verdictd["score_b"] if skill_is_a else verdictd["score_a"]
        w = verdictd["winner"]
        winner = ("with_skill" if (w == "a") == skill_is_a and w in ("a", "b")
                  else "baseline" if w in ("a", "b") else "tie")
        results.append(ScenarioResult(scenario=task, with_skill_score=ws,
                                      baseline_score=bs, winner=winner,
                                      rationale=verdictd["rationale"]))

    avg_w = round(sum(r.with_skill_score for r in results) / len(results), 2)
    avg_b = round(sum(r.baseline_score for r in results) / len(results), 2)
    delta = round(avg_w - avg_b, 2)
    verdict = "positive" if delta >= 0.5 else ("negative" if delta <= -0.5 else "neutral")

    return SkillJudgeReport(skill=skill_name, domain=domain, judge=judge_name,
                            scenarios=results, avg_with_skill=avg_w,
                            avg_baseline=avg_b, delta=delta, verdict=verdict,
                            authoritative=authoritative)
