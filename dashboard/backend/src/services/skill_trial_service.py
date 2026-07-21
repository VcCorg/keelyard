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

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class UploadResult(BaseModel):
    skill: str
    files: int
    registry: str


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


_SKIP_DIRS = {"__pycache__", ".git", "node_modules"}


def _discover_scripts(skill_dir: Path) -> tuple[list[Path], list[Path]]:
    """Return (python, shell) script files in a skill folder (recursively)."""
    py: list[Path] = []
    sh: list[Path] = []
    for p in skill_dir.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(skill_dir).parts
        if any(part in _SKIP_DIRS or part.startswith(".") for part in rel_parts):
            continue
        if p.suffix == ".py":
            py.append(p)
        elif p.suffix == ".sh":
            sh.append(p)
    return sorted(py), sorted(sh)


def _check_scripts(skill_dir: Path) -> TrialCheck:
    """Static validation of a skill's scripts: compile Python, verify referenced
    files exist, and surface (possibly undeclared) dependencies.

    Runtime behaviour is out of scope here — that's the 'Validate with Devin'
    path; this catches syntax errors, missing scripts and undeclared deps
    locally with no execution.
    """
    import sys

    py_files, sh_files = _discover_scripts(skill_dir)
    if not py_files and not sh_files:
        return TrialCheck(name="Scripts", status="skipped",
                          detail="No scripts in this skill (doc-only)")

    problems: list[str] = []

    # Compile Python (syntax only — never executes the code).
    import py_compile

    compiled = 0
    for p in py_files:
        try:
            py_compile.compile(str(p), doraise=True)
            compiled += 1
        except py_compile.PyCompileError as e:
            rel = p.relative_to(skill_dir)
            msg = (str(e).splitlines() or ["syntax error"])[-1][:90]
            problems.append(f"syntax error in {rel}: {msg}")
        except Exception:  # noqa: BLE001
            problems.append(f"could not compile {p.relative_to(skill_dir)}")

    # Scripts referenced in SKILL.md that don't exist in the folder.
    referenced_missing: list[str] = []
    md_path = skill_dir / "SKILL.md"
    if md_path.is_file():
        md = md_path.read_text(encoding="utf-8", errors="replace")
        present_names = {p.name for p in (*py_files, *sh_files)}
        for ref in sorted(set(re.findall(r"[\w./-]+\.(?:py|sh)", md))):
            name = Path(ref).name
            cand = skill_dir / ref
            if not cand.is_file() and name not in present_names:
                referenced_missing.append(ref)

    # Dependency surfacing: top-level third-party imports vs a declared manifest.
    has_manifest = any((skill_dir / f).is_file()
                       for f in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile"))
    imports: set[str] = set()
    for p in py_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        for m in re.finditer(r"^\s*(?:import|from)\s+([a-zA-Z_][\w]*)", txt, re.MULTILINE):
            imports.add(m.group(1))
    stdlib = getattr(sys, "stdlib_module_names", set())
    local_names = {p.stem for p in py_files}
    third_party = sorted(n for n in imports if n not in stdlib and n not in local_names)

    counts = f"{len(py_files)} py" + (f", {len(sh_files)} sh" if sh_files else "")
    if problems or referenced_missing:
        issues = problems + [f"missing referenced script: {r}" for r in referenced_missing]
        return TrialCheck(name="Scripts", status="fail",
                          detail=f"{counts} — " + "; ".join(issues[:4]))

    if third_party and not has_manifest:
        return TrialCheck(
            name="Scripts", status="warn",
            detail=f"{counts}, all compiled — imports {', '.join(third_party[:6])} "
                   "but no requirements.txt/pyproject.toml (deps may be undeclared)")

    dep_note = ("deps declared" if has_manifest else
                ("no third-party imports" if not third_party else "deps ok"))
    return TrialCheck(name="Scripts", status="pass",
                      detail=f"{counts}, all compiled; {dep_note}")


def _scripts_context(skill_dir: Path, total_budget: int = 5000, per_file: int = 1500) -> str:
    """A compact inventory + excerpts of a skill's scripts for the AI review."""
    py_files, sh_files = _discover_scripts(skill_dir)
    files = [*py_files, *sh_files]
    if not files:
        return ""
    out: list[str] = []
    used = 0
    for p in files[:8]:
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        snippet = body[:per_file]
        rel = p.relative_to(skill_dir)
        block = f"\n--- {rel} ---\n{snippet}"
        if used + len(block) > total_budget:
            break
        out.append(block)
        used += len(block)
    remaining = len(files) - len(out)
    header = f"\n\nScripts in this skill ({len(files)} file(s)):"
    if remaining > 0:
        header += f" [showing {len(out)}]"
    return header + "".join(out)


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
        scripts = _scripts_context(skill_dir)
        provider = get_llm_provider(
            system_instruction="You review AI agent skills (docs + code) for quality. "
                               "Answer strict JSON.")
        raw = provider.generate(
            "Review this agent skill for use in the domain "
            f"'{domain or 'general'}'. Consider both the SKILL.md and any scripts — "
            "whether the scripts match what the doc claims, look correct, and are safe. "
            "Return ONLY a JSON object with keys: "
            '"verdict" ("good"|"acceptable"|"poor"), "summary" (one sentence), '
            '"risks" (array of short strings).\n\nSKILL.md:\n' + text + scripts)
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
                   actor: Optional[str] = None,
                   run_security: bool = True) -> TrialScorecard:
    """Run the trial scorecard for a skill against a domain.

    ``run_security`` toggles the SkillSpector scan — leads can skip it when the
    scanner isn't installed or a skill is trusted (the check reports as skipped).
    """
    skill_dir = _skill_dir(skill_name)
    security = (_check_security(skill_dir) if run_security else
                TrialCheck(name="Security scan", status="skipped",
                           detail="Disabled for this trial"))
    checks = [
        _check_structure(skill_dir),
        _check_scripts(skill_dir),
        security,
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


# ── Upload a candidate skill into the registry for trialing ──────────────────

def _safe_component(name: str) -> str:
    return _SAFE.sub("-", (name or "").strip()).strip("-.") or ""


def _registry_root() -> Path:
    """The skills registry dir, creating a local one if none exists yet.

    Uploading a candidate skill is the "test before you push to master" path,
    so a fresh install gets a local registry to stage into.
    """
    from agentic_cli.commands.code import _get_registry_path

    reg = _get_registry_path()
    reg.mkdir(parents=True, exist_ok=True)
    rj = reg / "registry.json"
    if not rj.exists():
        rj.write_text(json.dumps({"skills": []}, indent=2), encoding="utf-8")
    (reg / "skills").mkdir(parents=True, exist_ok=True)
    return reg


def stage_uploaded_skill(skill_name: str, files: List[Tuple[str, str]],
                         actor: Optional[str] = None) -> UploadResult:
    """Write an uploaded skill (a folder of files, or a single file) into the
    registry so it can be trialed. ``files`` is a list of (relative_path, text).

    A single ``.md`` file with no folder is treated as the skill's SKILL.md.
    Requires (or synthesizes) a SKILL.md; upserts the registry.json entry.
    """
    if not files:
        raise ValueError("No files were uploaded")

    # Normalize paths, dropping traversal segments and empty entries.
    norm: List[Tuple[List[str], str]] = []
    for rel, content in files:
        parts = [p for p in (rel or "").replace("\\", "/").split("/")
                 if p not in ("", ".", "..")]
        if parts:
            norm.append((parts, content or ""))
    if not norm:
        raise ValueError("No valid files were uploaded")

    # A single shared top-level folder is the natural skill root/name.
    tops = {p[0] for p, _ in norm}
    common = tops.pop() if len(tops) == 1 and len(norm) > 1 else None
    name = _safe_component(skill_name) or _safe_component(common or "")
    staged = [(p[1:] if (common and len(p) > 1) else p, c) for p, c in norm]

    # A single markdown file becomes the skill's SKILL.md (flattened to root).
    if len(staged) == 1 and staged[0][0][-1].lower().endswith(".md"):
        orig = staged[0][0]
        if not name:
            name = _safe_component(orig[0] if len(orig) > 1 else Path(orig[-1]).stem)
        staged = [(["SKILL.md"], staged[0][1])]
    if not name:
        raise ValueError("Could not determine a skill name — provide one")

    reg = _registry_root()
    dest = reg / "skills" / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    dest_resolved = dest.resolve()

    for parts, content in staged:
        target = dest.joinpath(*parts)
        # Guard against path traversal outside the skill dir.
        try:
            target.resolve().relative_to(dest_resolved)
        except ValueError:
            shutil.rmtree(dest, ignore_errors=True)
            raise ValueError(f"Illegal path in upload: {'/'.join(parts)}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    if not (dest / "SKILL.md").is_file():
        shutil.rmtree(dest, ignore_errors=True)
        raise ValueError("Upload must include a SKILL.md (or a single .md file)")

    # Upsert the registry.json entry so it shows in the picker + can be trialed.
    rj = reg / "registry.json"
    try:
        data = json.loads(rj.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        data = {"skills": []}
    md = (dest / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^description:\s*(.+)$", md, re.MULTILINE)
    desc = (m.group(1).strip().strip("\"'")[:300] if m else "")
    skills = [s for s in data.get("skills", []) if s.get("name") != name]
    skills.append({"name": name, "description": desc, "tags": ["uploaded"]})
    data["skills"] = skills
    rj.write_text(json.dumps(data, indent=2), encoding="utf-8")

    try:
        from agentic_cli.tracker import record_action

        record_action("skill", "trial_upload", entity_type="skill", entity_id=name,
                      source="dashboard", actor=actor, details={"files": len(staged)})
    except Exception:  # noqa: BLE001
        pass

    return UploadResult(skill=name, files=len(staged), registry=str(reg))


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
