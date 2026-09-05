"""Set one governance value across a product's domains, safely.

The values analogue of ``template_promote``, and deliberately not built on it:
that pushes a *file* into a shared overlay from which every domain
fast-forwards, whereas ``governance.yaml`` is per-domain configuration that must
be written into each meta-repo separately.

Two guards, both from the asymmetry the product meta-repo already declares —
tightening is free, loosening is not:

- A value **looser than the product floor** is refused unless a recorded
  :class:`ExceptionEntry` already permits it for that domain. Refusing at plan
  time rather than warning after the write is the difference between a guard
  and a comment.
- Nothing is written without a plan first. :func:`plan` reports the blast
  radius — every domain, its current value, and whether the change tightens or
  loosens it — so "raise coverage to 85 everywhere" cannot silently relax the
  three domains already at 90.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from agentic_cli.meta_repo import governance_fleet as fleet


class PromotionRefused(Exception):
    """Raised when a promotion would loosen a domain below the floor."""


@dataclass
class Change:
    """What one domain would get."""

    domain: str
    meta_repo: Optional[Path]
    current: Any = None
    proposed: Any = None
    effect: str = fleet.SAME       # vs the product floor
    # How the change lands for *this domain*, which is a different question.
    # A promotion at or above the floor can still lower a domain that had
    # chosen something stricter, and nothing about the floor comparison would
    # show that.
    domain_effect: str = fleet.SAME
    exception_id: str = ""
    writable: bool = True
    note: str = ""

    @property
    def is_noop(self) -> bool:
        return self.current == self.proposed

    @property
    def blocked(self) -> bool:
        return self.effect == fleet.LOOSER and not self.exception_id

    @property
    def relaxes_domain(self) -> bool:
        """True when this loosens a domain that had chosen something stricter.

        Allowed — it still clears the floor — but never silent: "raise coverage
        to 85 everywhere" must not quietly relax the domains already at 90.
        """
        return self.domain_effect == fleet.LOOSER and not self.blocked

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "meta_repo": str(self.meta_repo) if self.meta_repo else "",
            "current": self.current, "proposed": self.proposed,
            "effect": self.effect, "domain_effect": self.domain_effect,
            "exception_id": self.exception_id, "blocked": self.blocked,
            "relaxes_domain": self.relaxes_domain, "noop": self.is_noop,
            "note": self.note,
        }


@dataclass
class Plan:
    """The full blast radius of one promotion."""

    key: str
    value: Any
    product: str
    floor_value: Any = None
    changes: list[Change] = field(default_factory=list)

    @property
    def blocked(self) -> list[Change]:
        return [c for c in self.changes if c.blocked]

    @property
    def applicable(self) -> list[Change]:
        return [c for c in self.changes
                if c.writable and not c.blocked and not c.is_noop]

    @property
    def loosening(self) -> list[Change]:
        return [c for c in self.changes if c.effect == fleet.LOOSER]

    @property
    def relaxing(self) -> list[Change]:
        """Domains this would loosen even though it clears the floor."""
        return [c for c in self.changes if c.relaxes_domain]

    def to_dict(self) -> dict:
        return {
            "key": self.key, "value": self.value, "product": self.product,
            "floor_value": self.floor_value,
            "changes": [c.to_dict() for c in self.changes],
        }


def coerce(key: str, raw: str) -> Any:
    """Turn a command-line string into the field's real type."""
    text = (raw or "").strip()
    if key in ("min_reviewers",):
        return int(text)
    if key in ("test_coverage_min",):
        return float(text)
    if key in fleet._BOOL_UP:
        if text.lower() not in ("true", "false", "yes", "no", "1", "0"):
            raise ValueError(f"{key} expects a boolean, got {raw!r}")
        return text.lower() in ("true", "yes", "1")
    return text


def parse_assignment(assignment: str) -> tuple[str, Any]:
    """``test_coverage_min=85`` -> ``("test_coverage_min", 85.0)``."""
    key, sep, raw = (assignment or "").partition("=")
    key = key.strip()
    if not sep or not key:
        raise ValueError("Expected <key>=<value>, e.g. test_coverage_min=85")
    if key not in fleet.COMPARABLE:
        raise ValueError(
            f"'{key}' is not a promotable value. One of: {', '.join(fleet.COMPARABLE)}")
    return key, coerce(key, raw)


def plan(product: str, domains: list[str], key: str, value: Any,
         product_meta: Optional[Path] = None) -> Plan:
    """Work out what the change would do to each domain, writing nothing."""
    from agentic_cli import persona_workspace as pw
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    product_meta = product_meta or pw.find_product_meta(product)
    floor = fleet.load_governance(product_meta) if product_meta else {}
    exceptions = fleet._active_exceptions(product_meta)
    floor_value = floor.get(key)

    changes: list[Change] = []
    for slug in domains:
        meta = detect_domain_meta_repo(slug)
        if meta is None:
            changes.append(Change(domain=slug, meta_repo=None, writable=False,
                                  note="No meta-repo found."))
            continue

        current = fleet.load_governance(meta).get(key)
        # Effect is measured against the *floor*, not against the domain's
        # current value: the question a guard has to answer is whether the
        # domain ends up below what the product requires.
        effect = fleet.compare_field(key, value, floor_value)
        changes.append(Change(
            domain=slug, meta_repo=meta, current=current, proposed=value,
            effect=effect,
            domain_effect=fleet.compare_field(key, value, current),
            exception_id=(fleet._covering_exception(exceptions, slug, key)
                          if effect == fleet.LOOSER else ""),
        ))

    return Plan(key=key, value=value, product=product,
                floor_value=floor_value, changes=changes)


def apply(plan_: Plan, *, force: bool = False) -> list[Change]:
    """Write the plan. Refuses outright if anything would drop below the floor.

    ``force`` does not bypass the floor — nothing here does. It only proceeds
    when a change is merely *different* from the floor on an unorderable field,
    which a human has to judge anyway.
    """
    if plan_.blocked and not force:
        names = ", ".join(c.domain for c in plan_.blocked)
        raise PromotionRefused(
            f"{plan_.key}={plan_.value!r} is looser than the product floor "
            f"({plan_.floor_value!r}) for: {names}. Record an exception in the "
            f"product meta-repo's exceptions/ ledger, or choose a value at or "
            f"above the floor."
        )

    written: list[Change] = []
    for change in plan_.applicable:
        if change.blocked:
            continue
        path = Path(change.meta_repo) / ".platform" / "config" / "governance.yaml"
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            change.writable = False
            change.note = "governance.yaml unreadable"
            continue
        data[plan_.key] = plan_.value
        try:
            path.write_text(
                yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
                encoding="utf-8")
        except OSError as exc:
            change.writable = False
            change.note = f"write failed: {exc}"
            continue
        written.append(change)
    return written


__all__ = [
    "PromotionRefused", "Change", "Plan", "coerce", "parse_assignment",
    "plan", "apply",
]
