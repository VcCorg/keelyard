"""Skill trials — evaluate a skill against a domain before promotion.

The skills mirror of KG scoping: domain leads initiate *domain skills*
(validated tier), while any role can TRIAL a registry skill against a specific
domain first — an intuitive scorecard instead of a leap of faith — and a lead
then PROMOTES passing skills into the domain-context repo (the path to the
master skills registry).

The scorecard composes checks the platform already trusts:
  1. structure      — SKILL.md present with name + description frontmatter
  2. security       — SkillSpector scan (skipped gracefully when unavailable)
  3. persona policy — would YOUR persona be allowed this skill in that domain?
  4. AI review      — LLM quality read (works with zero config via test-mode)

Every trial and promotion is recorded in the central audit trail.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TrialCheck(BaseModel):
    name: str
    status: str            # pass | warn | fail | skipped
    detail: str = ""


class TrialScorecard(BaseModel):
    skill: str
    domain: str
    persona: str
    verdict: str           # pass | warn | fail
    checks: List[TrialCheck] = []
    ai_provider: str = ""
    promotable: bool = False


class PromoteResult(BaseModel):
    skill: str
    domain: str
    promoted_to: str


def _skill_dir(skill_name: str) -> Path:
    from agentic_cli.commands.code import _ensure_registry

    d = _ensure_registry() / "skills" / skill_name
    if not d.exists():
        raise FileNotFoundError(f"Skill '{skill_name}' not found in registry")
    return d


def _check_structure(skill_dir: Path) -> TrialCheck:
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return TrialCheck(name="Structure", status="fail", detail="SKILL.md is missing")
    text = md.read_text(encoding="utf-8", errors="replace")
    has_name = bool(re.search(r"^name:\s*\S+", text, re.MULTILINE))
    has_desc = bool(re.search(r"^description:\s*\S+", text, re.MULTILINE))
    if not (text.startswith("---") and has_name and has_desc):
        return TrialCheck(name="Structure", status="fail",
                          detail="SKILL.md needs YAML frontmatter with name + description")
    body = len(text)
    if body < 200:
        return TrialCheck(name="Structure", status="warn",
                          detail=f"Very short skill ({body} chars) — likely underspecified")
    return TrialCheck(name="Structure", status="pass",
                      detail=f"Valid SKILL.md ({body} chars)")


def _check_security(skill_dir: Path) -> TrialCheck:
    try:
        from agentic_cli.skill_security import scan_path

        result = scan_path(skill_dir, use_llm=False)
        verdict = result.get("verdict", "UNKNOWN")
        score = result.get("score")
        detail = f"{verdict}" + (f" (risk {score})" if score is not None else "")
        if verdict == "DO_NOT_INSTALL":
            return TrialCheck(name="Security scan", status="fail", detail=detail)
        if verdict == "CAUTION":
            return TrialCheck(name="Security scan", status="warn", detail=detail)
        return TrialCheck(name="Security scan", status="pass", detail=detail)
    except Exception as e:  # noqa: BLE001 - scanner not installed etc.
        return TrialCheck(name="Security scan", status="skipped",
                          detail=f"Scanner unavailable ({str(e)[:80]})")


def _check_persona_policy(skill_name: str, domain: str, persona: str) -> TrialCheck:
    try:
        from agentic_cli.meta_repo.build_governance import find_meta_repo
        from agentic_cli.meta_repo.skill_policy import (
            default_policy, load_persona_policy, resolve_rule, status_for,
        )

        meta = find_meta_repo(domain) if domain else None
        policy = load_persona_policy(meta) if meta else default_policy()
        rule = resolve_rule(policy, persona)
        status = status_for(skill_name, "agent-skill", persona, rule)
        src = f"domain '{domain}'" if meta else "built-in default policy"
        if status == "denied":
            return TrialCheck(name="Persona policy", status="fail",
                              detail=f"'{persona}' is DENIED this skill by {src}")
        if status == "out-of-policy":
            return TrialCheck(
                name="Persona policy", status="warn",
                detail=f"Not granted to '{persona}' by {src} — promotion to the "
                       "validated tier would grant it")
        return TrialCheck(name="Persona policy", status="pass",
                          detail=f"Permitted for '{persona}' by {src}")
    except Exception as e:  # noqa: BLE001
        return TrialCheck(name="Persona policy", status="skipped",
                          detail=f"Policy unavailable ({str(e)[:80]})")


def _check_ai_review(skill_dir: Path, domain: str) -> tuple[TrialCheck, str]:
    try:
        from agentic_cli.llm.factory import get_llm_provider

        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")[:6000]
        provider = get_llm_provider(
            system_instruction="You review AI agent skills for quality. Answer strict JSON.")
        raw = provider.generate(
            "Review this agent skill for use in the domain "
            f"'{domain or 'general'}'. Return ONLY a JSON object with keys: "
            '"verdict" ("good"|"acceptable"|"poor"), "summary" (one sentence), '
            '"risks" (array of short strings).\n\nSKILL.md:\n' + text)
        import json as _json

        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = _json.loads(m.group(0)) if m else {}
        verdict = str(data.get("verdict", "acceptable")).lower()
        summary = str(data.get("summary", ""))[:200]
        risks = [str(r) for r in (data.get("risks") or [])][:3]
        detail = summary + (f" Risks: {'; '.join(risks)}" if risks else "")
        status = "pass" if verdict == "good" else ("warn" if verdict != "poor" else "fail")
        name = provider.get_name()
        if name.startswith("test-mode"):
            detail = "[test-mode provider — configure a model for a real review] " + detail
            status = "skipped"
        return TrialCheck(name="AI review", status=status, detail=detail), name
    except Exception as e:  # noqa: BLE001
        return TrialCheck(name="AI review", status="skipped",
                          detail=f"Review unavailable ({str(e)[:80]})"), ""


def evaluate_trial(skill_name: str, domain: str, persona: str,
                   actor: Optional[str] = None) -> TrialScorecard:
    """Run the trial scorecard for a skill against a domain."""
    skill_dir = _skill_dir(skill_name)
    checks = [
        _check_structure(skill_dir),
        _check_security(skill_dir),
        _check_persona_policy(skill_name, domain, persona),
    ]
    ai_check, ai_provider = _check_ai_review(skill_dir, domain)
    checks.append(ai_check)

    statuses = [c.status for c in checks]
    verdict = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "pass")
    # Promotable = nothing failed (warns are a lead's judgement call).
    promotable = "fail" not in statuses

    try:
        from agentic_cli.tracker import record_action

        record_action("skill", "trial_evaluate", entity_type="skill",
                      entity_id=skill_name, source="dashboard", actor=actor,
                      status="success" if verdict != "fail" else "error",
                      details={"domain": domain, "persona": persona,
                               "verdict": verdict,
                               "checks": {c.name: c.status for c in checks}})
    except Exception:  # noqa: BLE001 - never break on audit
        pass

    return TrialScorecard(skill=skill_name, domain=domain, persona=persona,
                          verdict=verdict, checks=checks,
                          ai_provider=ai_provider, promotable=promotable)


def _resolve_domain_context_dir(domain: str) -> Optional[Path]:
    """Find `<domain>-domain-context` by workspace conventions (no typer exit)."""
    import os

    candidates = [
        Path.cwd() / f"{domain}-domain-context",
        Path.cwd().parent / f"{domain}-domain-context",
        Path.home() / "workspace" / domain / f"{domain}-domain-context",
    ]
    ws = os.environ.get("KEEL_CODE_WORKSPACE", "")
    if ws:
        candidates.append(Path(ws).expanduser() / domain / f"{domain}-domain-context")
    for c in candidates:
        if c.is_dir() and (c / ".domain").exists():
            return c
    return None


def promote_trial(skill_name: str, domain: str, actor: Optional[str] = None) -> PromoteResult:
    """Promote a trialed skill into the domain's validated skills (lead action).

    Copies the registry skill into the domain-context repo's
    ``skills/validated/<skill>/`` — the tier `keel code onboard
    --use-domain-skills` installs first, and the staging ground for pushing to
    the master skills repo.
    """
    skill_dir = _skill_dir(skill_name)
    ctx = _resolve_domain_context_dir(domain)
    if ctx is None:
        raise FileNotFoundError(
            f"Domain context repo for '{domain}' not found (expected "
            f"'{domain}-domain-context' with a .domain marker). Clone/create it "
            "first: keel domain init-context " + domain)

    dest = ctx / "skills" / "validated" / skill_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skill_dir, dest)

    try:
        from agentic_cli.tracker import record_action

        record_action("skill", "trial_promote", entity_type="skill",
                      entity_id=skill_name, source="dashboard", actor=actor,
                      details={"domain": domain, "dest": str(dest)})
    except Exception:  # noqa: BLE001
        pass

    return PromoteResult(skill=skill_name, domain=domain, promoted_to=str(dest))


# ── LLM-as-judge impact evaluation (deep, on-demand) ─────────────────────────

def judge_trial(skill_name: str, domain: str, scenarios: int = 3,
                model: Optional[str] = None, actor: Optional[str] = None) -> Dict[str, Any]:
    """Run the LLM-as-judge impact evaluation for a trialed skill.

    Slower than the scorecard (2N answers + N judgements), so it runs on
    demand from the trial page. Works on any provider-chain rung; a test-mode
    judge is flagged non-authoritative rather than pretending.
    """
    from agentic_cli.evaluation.skill_judge import judge_skill

    skill_dir = _skill_dir(skill_name)
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    report = judge_skill(skill_name, text, domain=domain, scenarios=scenarios,
                         model=model)

    try:
        from agentic_cli.tracker import record_action

        record_action("skill", "trial_judge", entity_type="skill",
                      entity_id=skill_name, source="dashboard", actor=actor,
                      details={"domain": domain, "judge": report.judge,
                               "delta": report.delta, "verdict": report.verdict,
                               "authoritative": report.authoritative})
    except Exception:  # noqa: BLE001 - never break on audit
        pass

    return report.to_dict()
