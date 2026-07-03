"""Skill security scanning — thin dashboard delegation to the CLI.

The canonical SkillSpector wrapper lives in ``agentic_cli.skill_security`` so
the CLI (`dva skill scan`, the `dva skill install` gate) and the dashboard
share one implementation and one verdict. The dashboard calls it and records
user-initiated scans in the CLI audit trail as ``source="dashboard"``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def is_available() -> Dict[str, Any]:
    """Report whether the SkillSpector scanner is installed (delegates to CLI)."""
    from agentic_cli.skill_security import is_available as _is_available

    return _is_available()


def scan_path(target: Path, *, timeout: int = 180, use_llm: Optional[bool] = None) -> Dict[str, Any]:
    """Scan a skill dir/file/URL (delegates to the CLI scanner)."""
    from agentic_cli.skill_security import scan_path as _scan_path

    return _scan_path(target, timeout=timeout, use_llm=use_llm)


def scan_registry_skill(skill_name: str, *, use_llm: Optional[bool] = None) -> Dict[str, Any]:
    """Scan a registry skill via the CLI, auditing the scan as dashboard-sourced."""
    from agentic_cli.skill_security import scan_registry_skill as _scan_registry

    result = _scan_registry(skill_name, use_llm=use_llm)
    try:
        from agentic_cli.tracker import record_action

        record_action(
            "skill",
            "scan",
            entity_type="skill",
            entity_id=skill_name,
            status="error" if result.get("verdict") == "DO_NOT_INSTALL" else "success",
            source="dashboard",
            details={"verdict": result.get("verdict"), "score": result.get("score")},
        )
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return result
