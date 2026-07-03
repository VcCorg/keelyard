"""Skill security scanning via NVIDIA SkillSpector (canonical, CLI-owned).

Wraps the ``skillspector`` CLI to scan Agent Skills for vulnerabilities and
malicious patterns. This lives in the CLI so every entry point — ``dva skill
scan``, the ``dva skill install`` gate, and the dashboard (which delegates
here) — shares one implementation and one verdict.

The scanner is optional: every entry point degrades gracefully when
``skillspector`` is not on PATH (reports ``available: False``). SkillSpector
exit codes: 0 = SAFE/CAUTION (score <= 50), 1 = DO_NOT_INSTALL (score > 50),
2 = error. Exit code 1 is a valid verdict, not a failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

_GATE = {"SAFE": "allow", "CAUTION": "warn", "DO_NOT_INSTALL": "block"}

_LLM_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "NVIDIA_INFERENCE_KEY",
    "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID",
)


def _binary() -> Optional[str]:
    override = os.environ.get("SKILLSPECTOR_BIN")
    if override:
        return override if Path(override).exists() or shutil.which(override) else None
    return shutil.which("skillspector")


def _llm_available() -> bool:
    return any(os.environ.get(k) for k in _LLM_ENV_KEYS)


def _is_llm_credential_error(text: str) -> bool:
    low = (text or "").lower()
    return "llm api key" in low or "no llm api key configured" in low


def is_available() -> Dict[str, Any]:
    """Report whether the SkillSpector scanner is installed and its version."""
    binary = _binary()
    if not binary:
        return {"available": False, "version": None, "binary": None}
    version: Optional[str] = None
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
        version = (proc.stdout or proc.stderr).strip() or None
    except (subprocess.SubprocessError, OSError):
        pass
    return {"available": True, "version": version, "binary": binary}


def _derive_verdict(score: Optional[float], recommendation: Optional[str]) -> str:
    if recommendation:
        rec = recommendation.upper().replace(" ", "_")
        if rec in _GATE:
            return rec
    if score is None:
        return "CAUTION"
    if score <= 20:
        return "SAFE"
    if score <= 50:
        return "CAUTION"
    return "DO_NOT_INSTALL"


def _normalize(raw: Dict[str, Any], target: str) -> Dict[str, Any]:
    risk = raw.get("risk_assessment", {}) or {}
    score = risk.get("score")
    verdict = _derive_verdict(score, risk.get("recommendation"))
    issues: List[Dict[str, Any]] = []
    for issue in raw.get("issues", []) or []:
        issues.append(
            {
                "id": issue.get("id", ""),
                "title": issue.get("title") or issue.get("name") or issue.get("id", ""),
                "severity": issue.get("severity", "UNKNOWN"),
                "category": issue.get("category", ""),
                "confidence": issue.get("confidence"),
                "description": issue.get("description", ""),
            }
        )
    meta = raw.get("metadata", {}) or {}
    return {
        "target": target,
        "score": score,
        "severity": risk.get("severity"),
        "verdict": verdict,
        "gate": _GATE.get(verdict, "warn"),
        "issue_count": len(issues),
        "issues": issues,
        "llm": {"requested": meta.get("llm_requested"), "available": meta.get("llm_available")},
    }


def _run(binary: str, target: Path, timeout: int, no_llm: bool):
    cmd = [binary, "scan", str(target), "--format", "json"]
    if no_llm:
        cmd.append("--no-llm")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def scan_path(target: Path, *, timeout: int = 180, use_llm: Optional[bool] = None) -> Dict[str, Any]:
    """Scan a skill dir / file / URL and return a normalized verdict.

    Raises RuntimeError when the scanner is unavailable or errors out.
    """
    binary = _binary()
    if not binary:
        raise RuntimeError(
            "SkillSpector is not installed. Install with: "
            "uv tool install git+https://github.com/NVIDIA/skillspector.git"
        )
    no_llm = (use_llm is False) or (use_llm is None and not _llm_available())
    try:
        proc = _run(binary, target, timeout, no_llm)
        if proc.returncode == 2 and not no_llm and _is_llm_credential_error(proc.stdout + proc.stderr):
            no_llm = True
            proc = _run(binary, target, timeout, no_llm)
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise RuntimeError(f"SkillSpector scan timed out after {timeout}s") from exc
    except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to run SkillSpector: {exc}") from exc

    if proc.returncode == 2 and not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "SkillSpector reported an error")
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse SkillSpector output: {proc.stderr.strip() or exc}") from exc

    result = _normalize(raw, str(target))
    result["llm"]["used"] = not no_llm
    return result


def scan_registry_skill(skill_name: str, *, use_llm: Optional[bool] = None) -> Dict[str, Any]:
    """Resolve a skill in the configured registry and scan its directory."""
    from agentic_cli.commands.code import _ensure_registry

    reg_path = _ensure_registry()
    skill_dir = reg_path / "skills" / skill_name
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill '{skill_name}' not found in registry")
    result = scan_path(skill_dir, use_llm=use_llm)
    result["skill_name"] = skill_name
    return result
