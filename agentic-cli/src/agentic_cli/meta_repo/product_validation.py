"""Semantic validation for a product meta-repo.

`product init-meta` scaffolds a deterministic structure; this module asserts
that the *generated* artifacts are internally coherent — the kind of checks the
shipped ``make validate`` (which only checks that two directories exist) does
not perform.

Invariants checked:
  - Required structure exists (.platform/config + the four YAMLs, exceptions/).
  - product.yaml parses and has a name (methodology URL recommended).
  - governance.yaml parses; promotion_path is non-empty; every gate referenced
    by checkpoint_gate_map exists in promotion_path; sane numeric bounds.
  - crosswalk.yaml agrees with governance.yaml (no drift between the two copies).
  - personas.yaml parses; defaults_enabled ⊆ built-ins; persona ids are unique,
    kebab-case, and don't silently collide with a built-in.
  - inner-loop methodology submodule is wired (and initialized).

Nothing here mutates state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from agentic_cli.meta_repo.config import (
    BUILTIN_PERSONA_IDS,
    GovernanceConfig,
    PersonasConfig,
    ProductConfig,
)

OK = "ok"
WARN = "warn"
FAIL = "fail"

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Check:
    """Outcome of a single validation check."""

    name: str
    status: str
    detail: str = ""
    fix: str = ""


@dataclass
class ValidationReport:
    """Aggregate result of validating a product meta-repo."""

    meta_path: Path
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "", fix: str = "") -> None:
        self.checks.append(Check(name=name, status=status, detail=detail, fix=fix))

    @property
    def failed(self) -> bool:
        return any(c.status == FAIL for c in self.checks)

    @property
    def counts(self) -> dict[str, int]:
        out = {OK: 0, WARN: 0, FAIL: 0}
        for c in self.checks:
            out[c.status] = out.get(c.status, 0) + 1
        return out


def _load_yaml(path: Path) -> Optional[dict]:
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


def validate_product_meta(meta_path: Path) -> ValidationReport:
    """Validate a product meta-repo at ``meta_path``. Returns a report."""
    report = ValidationReport(meta_path=meta_path)
    config_dir = meta_path / ".platform" / "config"

    # ── Structure ────────────────────────────────────────────────────────────
    if not meta_path.exists():
        report.add("meta-repo exists", FAIL, f"Not found: {meta_path}",
                   fix="Run: keel product init-meta <name>")
        return report

    if config_dir.is_dir():
        report.add(".platform/config", OK, str(config_dir))
    else:
        report.add(".platform/config", FAIL, "missing",
                   fix="Re-run: keel product init-meta <name>")
        return report

    required = ["product.yaml", "governance.yaml", "crosswalk.yaml", "personas.yaml"]
    for fname in required:
        exists = (config_dir / fname).is_file()
        report.add(f"config/{fname}", OK if exists else FAIL,
                   "present" if exists else "missing",
                   fix="" if exists else "Re-run: keel product init-meta <name>")

    report.add("exceptions/ ledger", OK if (meta_path / "exceptions").is_dir() else WARN,
               "present" if (meta_path / "exceptions").is_dir() else "missing")

    # ── product.yaml ───────────────────────────────────────────────────────────
    pdata = _load_yaml(config_dir / "product.yaml")
    if pdata is None:
        report.add("product.yaml parses", FAIL, "invalid YAML")
    else:
        product = ProductConfig.from_dict(pdata)
        if product.product:
            report.add("product.name", OK, product.product)
        else:
            report.add("product.name", FAIL, "empty")
        if product.org_methodology_url:
            report.add("product.org_methodology_url", OK, product.org_methodology_url)
        else:
            report.add("product.org_methodology_url", WARN, "empty",
                       fix="Set --org-methodology so the inner-loop submodule can be pinned.")

    # ── governance.yaml ──────────────────────────────────────────────────────
    gdata = _load_yaml(config_dir / "governance.yaml")
    gov: Optional[GovernanceConfig] = None
    if gdata is None:
        report.add("governance.yaml parses", FAIL, "invalid YAML")
    else:
        gov = GovernanceConfig.from_dict(gdata)
        path = list(gov.promotion_path or [])
        if path:
            report.add("governance.promotion_path", OK, " → ".join(path))
        else:
            report.add("governance.promotion_path", FAIL, "empty")

        # Every gate in the crosswalk must be a known promotion stage.
        bad = [
            entry.get("gate")
            for entry in (gov.checkpoint_gate_map or [])
            if entry.get("gate") not in path
        ]
        if not gov.checkpoint_gate_map:
            report.add("checkpoint_gate_map", WARN, "empty (no inner↔outer crosswalk)")
        elif bad:
            report.add("checkpoint_gate_map gates ⊆ promotion_path", FAIL,
                       f"unknown gate(s): {', '.join(str(b) for b in bad)}",
                       fix="Fix the 'gate' values or add them to promotion_path.")
        else:
            report.add("checkpoint_gate_map gates ⊆ promotion_path", OK,
                       f"{len(gov.checkpoint_gate_map)} checkpoint(s) mapped")

        # Sane numeric bounds.
        if gov.min_reviewers < 1 and gov.require_code_review:
            report.add("governance.min_reviewers", WARN,
                       f"{gov.min_reviewers} with require_code_review=true")
        if not (0.0 <= gov.test_coverage_min <= 100.0):
            report.add("governance.test_coverage_min", FAIL,
                       f"{gov.test_coverage_min} out of range 0–100")

    # ── crosswalk.yaml agrees with governance.yaml ───────────────────────────
    cdata = _load_yaml(config_dir / "crosswalk.yaml")
    if cdata is None:
        report.add("crosswalk.yaml parses", FAIL, "invalid YAML")
    elif gov is not None:
        drift = (
            cdata.get("promotion_path") != gov.promotion_path
            or cdata.get("checkpoint_gate_map") != gov.checkpoint_gate_map
        )
        report.add("crosswalk ↔ governance consistency",
                   WARN if drift else OK,
                   "drift detected" if drift else "in sync",
                   fix="Re-sync crosswalk.yaml with governance.yaml." if drift else "")

    # ── personas.yaml ──────────────────────────────────────────────────────────
    perdata = _load_yaml(config_dir / "personas.yaml")
    if perdata is None:
        report.add("personas.yaml parses", FAIL, "invalid YAML")
    else:
        personas = PersonasConfig.from_dict(perdata)
        unknown = [d for d in personas.defaults_enabled if d not in BUILTIN_PERSONA_IDS]
        if unknown:
            report.add("personas.defaults_enabled ⊆ built-ins", FAIL,
                       f"unknown built-in id(s): {', '.join(unknown)}",
                       fix=f"Allowed built-ins: {', '.join(BUILTIN_PERSONA_IDS)}")
        else:
            report.add("personas.defaults_enabled ⊆ built-ins", OK,
                       f"{len(personas.defaults_enabled)} enabled")

        ids = [p.id for p in personas.personas]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            report.add("personas[].id unique", FAIL,
                       f"duplicate id(s): {', '.join(sorted(dupes))}")
        bad_kebab = [i for i in ids if not _KEBAB.match(i)]
        if bad_kebab:
            report.add("personas[].id kebab-case", FAIL,
                       f"invalid id(s): {', '.join(bad_kebab)}")
        collide = [i for i in ids if i in BUILTIN_PERSONA_IDS]
        if collide:
            report.add("custom persona vs built-in", WARN,
                       f"overrides built-in: {', '.join(collide)}")
        if not dupes and not bad_kebab:
            report.add("personas catalog", OK,
                       f"{len(ids)} product persona(s)")

    # ── inner-loop methodology submodule ─────────────────────────────────────
    inner = meta_path / "inner-loop"
    if (meta_path / ".gitmodules").is_file() and inner.is_dir():
        initialized = any(inner.iterdir()) if inner.is_dir() else False
        report.add("inner-loop submodule",
                   OK if initialized else WARN,
                   "initialized" if initialized else "registered but empty",
                   fix="" if initialized else "Run: make init  (git submodule update --init)")
    else:
        report.add("inner-loop submodule", WARN, "not wired",
                   fix="Re-run init-meta with --org-methodology to pin the methodology.")

    return report
