"""Skill security scanning via NVIDIA SkillSpector.

Wraps the `skillspector` CLI (https://github.com/NVIDIA/SkillSpector) to scan
Agent Skills for vulnerabilities and malicious patterns before they are
installed, published, or composed into a project.

Design notes
------------
* The scanner is an *optional* dependency. Every entry point degrades
  gracefully when `skillspector` is not on PATH so the dashboard never hard-
  fails just because the binary is missing — it reports ``available: False``.
* SkillSpector exit codes: ``0`` = SAFE/CAUTION (score <= 50), ``1`` =
  DO_NOT_INSTALL (score > 50), ``2`` = error. Exit code ``1`` is a *valid*
  verdict, not a failure, so we parse stdout regardless of return code and only
  treat ``2`` / unparseable output as an error.
* Pattern-only scans are fast and deterministic; LLM-augmented scans are deeper
  but need model access. We record which mode produced a verdict via the
  ``llm`` metadata field so callers can decide how much to trust it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Verdict → recommended gate action. Mirrors SkillSpector's own mapping.
_GATE = {
    "SAFE": "allow",
    "CAUTION": "warn",
    "DO_NOT_INSTALL": "block",
}


def _binary() -> Optional[str]:
    """Resolve the skillspector executable, honoring an env override."""
    override = os.environ.get("SKILLSPECTOR_BIN")
    if override:
        return override if Path(override).exists() or shutil.which(override) else None
    return shutil.which("skillspector")


def is_available() -> Dict[str, Any]:
    """Report whether the SkillSpector scanner is installed and its version."""
    binary = _binary()
    if not binary:
        return {"available": False, "version": None, "binary": None}

    version: Optional[str] = None
    try:
        proc = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        version = (proc.stdout or proc.stderr).strip() or None
    except (subprocess.SubprocessError, OSError):
        pass

    return {"available": True, "version": version, "binary": binary}


def _derive_verdict(score: Optional[float], recommendation: Optional[str]) -> str:
    """Prefer SkillSpector's recommendation; fall back to score thresholds."""
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
    """Flatten a raw SkillSpector JSON report into the shape the UI consumes."""
    risk = raw.get("risk_assessment", {}) or {}
    score = risk.get("score")
    severity = risk.get("severity")
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
        "severity": severity,
        "verdict": verdict,
        "gate": _GATE.get(verdict, "warn"),
        "issue_count": len(issues),
        "issues": issues,
        "llm": {
            "requested": meta.get("llm_requested"),
            "available": meta.get("llm_available"),
        },
    }


def scan_path(target: Path, *, timeout: int = 180) -> Dict[str, Any]:
    """Scan a skill directory / file / URL and return a normalized verdict.

    Raises ``RuntimeError`` when the scanner is unavailable or errors out
    (exit code 2 / unparseable output) so callers can surface a clean message.
    """
    binary = _binary()
    if not binary:
        raise RuntimeError(
            "SkillSpector is not installed. Install with: "
            "uv tool install git+https://github.com/NVIDIA/skillspector.git"
        )

    try:
        proc = subprocess.run(
            [binary, "scan", str(target), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"SkillSpector scan timed out after {timeout}s") from exc
    except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to run SkillSpector: {exc}") from exc

    # Exit code 1 == DO_NOT_INSTALL, which is a valid verdict with JSON on
    # stdout. Only exit code 2 (or missing JSON) is a real error.
    if proc.returncode == 2 and not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "SkillSpector reported an error")

    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse SkillSpector output: {proc.stderr.strip() or exc}"
        ) from exc

    return _normalize(raw, str(target))


def scan_registry_skill(skill_name: str) -> Dict[str, Any]:
    """Resolve a skill in the configured registry and scan its directory."""
    from agentic_cli.commands.code import _ensure_registry

    reg_path = _ensure_registry()
    skill_dir = reg_path / "skills" / skill_name
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill '{skill_name}' not found in registry")

    result = scan_path(skill_dir)
    result["skill_name"] = skill_name
    return result
