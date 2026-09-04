"""Governance across every domain of a product — compare, then promote.

``template_promote`` moves *files* through the overlay, and its three-way hash
classifier is what makes "fast-forward" and "conflict" meaningful there. That
does not transfer here: ``governance.yaml`` holds scalars, and a scalar has no
"fresh render" to diff against. So this classifier uses the axes that actually
apply to a policy value — is a domain the same as the product floor, stricter
than it, looser than it, or simply different in a way nobody can order?

The distinction that matters is **stricter versus looser**, because the product
meta-repo already declares the asymmetry: a domain may tighten governance
freely, and loosening requires a recorded :class:`ExceptionEntry`. That rule was
written down and never enforced or reported on across a fleet — a domain could
quietly sit below the floor indefinitely and nothing would say so.

Fields nobody can order (a branch regex, a promotion path) are reported as
``differs`` rather than guessed at. Calling a different regex "looser" would be
a fabrication, and calling it "same" would hide it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

#: Domain matches the product floor.
SAME = "same"
#: Domain is stricter than the floor — always allowed.
STRICTER = "stricter"
#: Domain is looser than the floor — needs a recorded exception.
LOOSER = "looser"
#: Values differ on a field with no ordering; a human decides.
DIFFERS = "differs"
#: Domain does not set this field, so it inherits the floor.
UNSET = "unset"

VERDICT_ORDER = (LOOSER, DIFFERS, UNSET, STRICTER, SAME)

#: Higher is stricter.
_NUMERIC_UP = frozenset({"min_reviewers", "test_coverage_min"})
#: True is stricter.
_BOOL_UP = frozenset({
    "require_pre_push_hook", "require_ci_gates", "require_code_review",
    "require_tests",
})
#: Ordered enums, least strict first.
_ORDINAL: dict[str, tuple[str, ...]] = {
    "build_governance": ("off", "warn", "enforce"),
}
#: Comparable fields, in display order.
COMPARABLE = tuple(sorted(_NUMERIC_UP | _BOOL_UP)) + tuple(sorted(_ORDINAL))

#: Present in governance.yaml but not orderable.
OPAQUE = ("branch_pattern", "promotion_path", "checkpoint_gate_map", "inner_loop_floor")

ALL_FIELDS = COMPARABLE + OPAQUE


@dataclass
class FieldVerdict:
    """How one domain's value for one field compares to the product floor."""

    field: str
    verdict: str
    domain_value: Any = None
    floor_value: Any = None
    exception_id: str = ""

    @property
    def needs_exception(self) -> bool:
        return self.verdict == LOOSER

    @property
    def violation(self) -> bool:
        """Looser than the floor with nothing on record permitting it."""
        return self.needs_exception and not self.exception_id

    def to_dict(self) -> dict:
        return {
            "field": self.field, "verdict": self.verdict,
            "domain_value": self.domain_value, "floor_value": self.floor_value,
            "exception_id": self.exception_id, "violation": self.violation,
        }


@dataclass
class DomainGovernance:
    """One domain's standing against its product's floor."""

    domain: str
    meta_repo: Optional[Path] = None
    found: bool = False
    verdicts: list[FieldVerdict] = field(default_factory=list)

    @property
    def violations(self) -> list[FieldVerdict]:
        return [v for v in self.verdicts if v.violation]

    @property
    def waived(self) -> list[FieldVerdict]:
        return [v for v in self.verdicts if v.needs_exception and v.exception_id]

    @property
    def stricter(self) -> list[FieldVerdict]:
        return [v for v in self.verdicts if v.verdict == STRICTER]

    @property
    def status(self) -> str:
        if not self.found:
            return "missing"
        if self.violations:
            return "violation"
        if any(v.verdict == DIFFERS for v in self.verdicts):
            return "differs"
        if self.waived:
            return "waived"
        return "ok"

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "meta_repo": str(self.meta_repo) if self.meta_repo else "",
            "found": self.found,
            "status": self.status,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


@dataclass
class FleetReport:
    """Every domain of a product against one floor."""

    product: str
    floor: dict = field(default_factory=dict)
    product_meta: Optional[Path] = None
    domains: list[DomainGovernance] = field(default_factory=list)

    @property
    def violations(self) -> list[DomainGovernance]:
        return [d for d in self.domains if d.violations]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for domain in self.domains:
            out[domain.status] = out.get(domain.status, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "product": self.product,
            "product_meta": str(self.product_meta) if self.product_meta else "",
            "floor": self.floor,
            "counts": self.counts,
            "domains": [d.to_dict() for d in self.domains],
        }


# ── comparison ──────────────────────────────────────────────────────────────

def compare_field(name: str, domain_value: Any, floor_value: Any) -> str:
    """Classify one field. See the module docstring for why ``differs`` exists."""
    if domain_value is None:
        return UNSET
    if floor_value is None:
        # Nothing to be looser *than*: the product has not set a floor here.
        return DIFFERS if name in OPAQUE else UNSET
    if domain_value == floor_value:
        return SAME

    if name in _NUMERIC_UP:
        try:
            return STRICTER if float(domain_value) > float(floor_value) else LOOSER
        except (TypeError, ValueError):
            return DIFFERS
    if name in _BOOL_UP:
        return STRICTER if bool(domain_value) and not bool(floor_value) else LOOSER
    if name in _ORDINAL:
        levels = _ORDINAL[name]
        try:
            return (STRICTER if levels.index(str(domain_value).lower())
                    > levels.index(str(floor_value).lower()) else LOOSER)
        except ValueError:
            return DIFFERS
    return DIFFERS


def load_governance(meta_repo: Path) -> dict:
    """Read a meta-repo's ``governance.yaml``; empty when absent or unreadable."""
    path = Path(meta_repo) / ".platform" / "config" / "governance.yaml"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _active_exceptions(product_meta: Optional[Path]) -> list:
    if product_meta is None:
        return []
    try:
        from agentic_cli.meta_repo.product_scaffold import list_exceptions

        entries = list_exceptions(product_meta)
    except Exception:  # noqa: BLE001 - a missing ledger is not an error here
        return []
    today = date.today().isoformat()
    return [
        e for e in entries
        if getattr(e, "status", "") == "active"
        and (not getattr(e, "expires_at", "") or e.expires_at >= today)
    ]


def _covering_exception(exceptions: list, domain: str, rule: str) -> str:
    """The id of an active waiver permitting ``rule`` for ``domain``, if any."""
    for entry in exceptions:
        if getattr(entry, "rule", "") != rule:
            continue
        scope = getattr(entry, "scope", "")
        if scope in (f"domain:{domain}", "domain:*", "product", ""):
            return getattr(entry, "id", "") or "recorded"
    return ""


def compare_domain(
    domain: str, meta_repo: Optional[Path], floor: dict, exceptions: list
) -> DomainGovernance:
    """Compare one domain's governance to the floor."""
    if meta_repo is None:
        return DomainGovernance(domain=domain, found=False)

    values = load_governance(meta_repo)
    verdicts: list[FieldVerdict] = []
    for name in ALL_FIELDS:
        verdict = compare_field(name, values.get(name), floor.get(name))
        if verdict in (SAME, UNSET):
            # Agreement is the common case; listing it drowns the exceptions.
            continue
        verdicts.append(FieldVerdict(
            field=name, verdict=verdict,
            domain_value=values.get(name), floor_value=floor.get(name),
            exception_id=(_covering_exception(exceptions, domain, name)
                          if verdict == LOOSER else ""),
        ))
    return DomainGovernance(domain=domain, meta_repo=meta_repo, found=True,
                            verdicts=verdicts)


def build_report(product: str, domains: list[str],
                 product_meta: Optional[Path] = None) -> FleetReport:
    """Compare every named domain against the product's floor."""
    from agentic_cli import persona_workspace as pw
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    product_meta = product_meta or pw.find_product_meta(product)
    floor = load_governance(product_meta) if product_meta else {}
    exceptions = _active_exceptions(product_meta)

    return FleetReport(
        product=product, floor=floor, product_meta=product_meta,
        domains=[
            compare_domain(slug, detect_domain_meta_repo(slug), floor, exceptions)
            for slug in domains
        ],
    )


__all__ = [
    "SAME", "STRICTER", "LOOSER", "DIFFERS", "UNSET", "VERDICT_ORDER",
    "COMPARABLE", "OPAQUE", "ALL_FIELDS", "FieldVerdict", "DomainGovernance",
    "FleetReport", "compare_field", "load_governance", "compare_domain",
    "build_report",
]
