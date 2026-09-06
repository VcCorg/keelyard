"""Composing per-component findings into one judgement — G3, the floor arithmetic.

G1 enumerated. G2 ruled on each component and stopped there deliberately, because
composing findings into a verdict is policy and policy belongs to the governance
floor. This is that composition, and it lives here rather than in ``guard`` so
the boundary stays visible: the inventory and its findings say what is true, and
only this file says whether that is *allowed*.

**The floor is the product's, and a domain may tighten it.** Nothing about that
is re-derived here. ``governance_fleet`` already classifies a domain's value
against the product's as same, stricter, looser or unset, already resolves
exceptions with their expiry and scope, and the two agent-surface rules are
registered in its own table of orderable fields. A second comparison living here
would be a second answer to "is this domain allowed to be laxer", and the two
would drift.

**A policy a domain was not allowed to set does not apply.** Where a domain
loosens the floor with no recorded exception, this judges against the *floor*,
not against the domain's value, and says so. Evaluating a session against a
policy its owner had no authority to set would let anyone pass any check by
editing their own governance.yaml — the loosening is itself the violation, and
the fleet report is where it is already visible.

**Silence is neither permission nor prohibition.** A floor that says nothing
about a finding is a product that has not made this policy, which is a gap in
their policy rather than in our knowledge. It is reported as ungoverned and
never counted as a pass — but it does not block either, because inventing a
default here would put a rule somewhere nobody agreed to and nobody can waive.

**What could not be ruled on is never a pass.** This is the one that matters. If
G2 could not enumerate a section, or could not establish where inference is
served from, then the honest session-level answer is *undetermined* — we might be
failing and cannot tell. Folding that into a pass is how a governance check comes
to certify the thing it never examined, and every layer underneath this one has
kept "we could not ask" apart from "there is nothing there" precisely so that
this layer would not have to invent it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── per-finding outcomes ────────────────────────────────────────────────────

#: The floor permits this.
ALLOWED = "allowed"
#: The floor forbids it and nothing on record waives it. A violation.
DENIED = "denied"
#: Forbidden, but an active, in-scope exception covers it.
WAIVED = "waived"
#: The floor makes no rule about this finding.
UNGOVERNED = "ungoverned"
#: Nothing could be established, so nothing could be ruled.
INDETERMINATE = "indeterminate"

OUTCOMES = (DENIED, INDETERMINATE, WAIVED, UNGOVERNED, ALLOWED)

# ── session-level verdicts ──────────────────────────────────────────────────

PASS = "pass"
FAIL = "fail"
UNDETERMINED = "undetermined"

#: Finding code → the floor rule that governs it. A code absent from this map is
#: not policy-relevant (hygiene, or the safe case) and comes out ungoverned.
RULE_FOR = {
    "credential-shared": "forbid_shared_credentials",
    "egress-external": "forbid_external_egress",
}

#: Finding codes that are themselves a failure to establish something. These
#: make a session undetermined rather than passing, which is the whole point.
INDETERMINATE_CODES = ("egress-unknown",)


@dataclass
class Ruling:
    """One finding, judged against the floor."""

    code: str
    component: str
    outcome: str
    rule: str = ""
    #: The value in force — the floor's, or the domain's tightening of it.
    in_force: Optional[bool] = None
    #: Set when the domain's own value was disregarded because it loosened the
    #: floor with nothing on record permitting that.
    disregarded_domain_value: bool = False
    exception_id: str = ""
    detail: str = ""

    @property
    def violation(self) -> bool:
        return self.outcome == DENIED

    def to_dict(self) -> dict:
        out = {"code": self.code, "component": self.component,
               "outcome": self.outcome}
        for key in ("rule", "exception_id", "detail"):
            if getattr(self, key):
                out[key] = getattr(self, key)
        if self.in_force is not None:
            out["in_force"] = self.in_force
        if self.disregarded_domain_value:
            out["disregarded_domain_value"] = True
        return out


@dataclass
class Judgement:
    """One session's standing against its floor, and why."""

    domain: str = ""
    rulings: list[Ruling] = field(default_factory=list)
    #: Things nothing could be ruled on: G2's own unruled list, plus any
    #: finding whose code is a failure to establish something.
    unruled: list[str] = field(default_factory=list)
    #: True when the floor itself could not be read. A judgement against no
    #: floor is not a pass.
    floor_found: bool = True
    detail: str = ""

    @property
    def violations(self) -> list[Ruling]:
        return [r for r in self.rulings if r.violation]

    @property
    def waived(self) -> list[Ruling]:
        return [r for r in self.rulings if r.outcome == WAIVED]

    @property
    def ungoverned(self) -> list[Ruling]:
        return [r for r in self.rulings if r.outcome == UNGOVERNED]

    @property
    def verdict(self) -> str:
        """PASS, FAIL, or UNDETERMINED — and undetermined is not a soft pass.

        A definite violation outranks an unknown: you are already failing, and
        more uncertainty does not change what to do about it. Everything else
        unknown outranks a pass, because passing would certify what was never
        examined.
        """
        if self.violations:
            return FAIL
        if self.unruled or not self.floor_found:
            return UNDETERMINED
        return PASS

    @property
    def counts(self) -> dict:
        out = {o: 0 for o in OUTCOMES}
        for ruling in self.rulings:
            out[ruling.outcome] = out.get(ruling.outcome, 0) + 1
        out["unruled"] = len(self.unruled)
        return out

    def to_dict(self) -> dict:
        return {"domain": self.domain, "verdict": self.verdict,
                "floor_found": self.floor_found, "detail": self.detail,
                "counts": self.counts, "unruled": list(self.unruled),
                "rulings": [r.to_dict() for r in self.rulings]}


# ── the floor in force ──────────────────────────────────────────────────────

@dataclass
class Policy:
    """What is actually in force for one domain, and how each value got there."""

    values: dict = field(default_factory=dict)
    #: Rules where the domain's own value was disregarded as an unpermitted
    #: loosening. Named so a report can say why the stricter value applied.
    disregarded: set = field(default_factory=set)
    exceptions: dict = field(default_factory=dict)
    found: bool = False


def policy_for(domain: str, *, product_meta: Optional[Path] = None,
               domain_meta: Optional[Path] = None) -> Policy:
    """Resolve the floor in force, letting a domain tighten but not loosen.

    Every comparison and every exception lookup goes through
    ``governance_fleet``; this only decides which of the two values applies.
    """
    from agentic_cli.meta_repo import governance_fleet as fleet

    policy = Policy()

    if product_meta is None or domain_meta is None:
        from agentic_cli.meta_repo.detector import detect_domain_meta_repo

        if domain_meta is None:
            try:
                domain_meta = detect_domain_meta_repo(domain)
            except Exception as exc:  # noqa: BLE001
                logger.debug("no meta-repo for %s: %s", domain, exc)
        if product_meta is None:
            product_meta = _product_meta_for(domain)

    floor = fleet.load_governance(product_meta) if product_meta else {}
    if not floor:
        return policy
    policy.found = True

    values = fleet.load_governance(domain_meta) if domain_meta else {}
    exceptions = fleet.active_exceptions(product_meta)

    for rule in sorted(set(RULE_FOR.values())):
        floor_value = floor.get(rule)
        if floor_value is None:
            continue                      # the product has made no rule here
        domain_value = values.get(rule)
        verdict = fleet.compare_field(rule, domain_value, floor_value)

        if verdict == fleet.STRICTER:
            policy.values[rule] = bool(domain_value)
            continue
        if verdict == fleet.LOOSER:
            covering = fleet.covering_exception(exceptions, domain, rule)
            if covering:
                policy.values[rule] = bool(domain_value)
                policy.exceptions[rule] = covering
                continue
            # Loosened with nothing on record permitting it. The floor applies,
            # and the loosening is itself the violation the fleet reports.
            policy.values[rule] = bool(floor_value)
            policy.disregarded.add(rule)
            continue
        policy.values[rule] = bool(floor_value)

    return policy


def _product_meta_for(domain: str) -> Optional[Path]:
    """The product meta-repo a domain's floor comes from, if it can be found."""
    try:
        from agentic_cli.meta_repo.detector import detect_domain_meta_repo
        from agentic_cli.tracker import get_domain

        record = get_domain(domain) or {}
        product = record.get("product") or ""
        if not product:
            return None
        # The product meta-repo is referenced as a submodule of the domain's,
        # which is where domain init puts it.
        meta = detect_domain_meta_repo(domain)
        if meta is None:
            return None
        for candidate in (Path(meta) / "product-meta", Path(meta).parent / product):
            if (candidate / ".platform" / "config").is_dir():
                return candidate
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not locate the product floor for %s: %s", domain, exc)
    return None


# ── composition ─────────────────────────────────────────────────────────────

def compose(findings, domain: str = "", *, product_meta: Optional[Path] = None,
            domain_meta: Optional[Path] = None) -> Judgement:
    """Judge one set of G2 findings against the floor in force.

    ``findings`` is a :class:`~agentic_cli.guard_findings.Findings`. Its own
    ``unruled`` entries carry straight through: a verdict G2 could not reach is
    one this cannot compose, and nothing here upgrades it.
    """
    policy = policy_for(domain, product_meta=product_meta, domain_meta=domain_meta)
    judgement = Judgement(domain=domain, floor_found=policy.found)
    if not policy.found:
        judgement.detail = ("No product governance floor could be read — there "
                            "is nothing to judge against.")

    # G2's gaps are this layer's gaps. Carried, never resolved by optimism.
    judgement.unruled.extend(getattr(findings, "unruled", []))

    for finding in getattr(findings, "findings", []):
        if finding.code in INDETERMINATE_CODES:
            judgement.rulings.append(Ruling(
                code=finding.code, component=finding.component,
                outcome=INDETERMINATE, detail=finding.statement))
            judgement.unruled.append(f"{finding.component}: {finding.code}")
            continue

        rule = RULE_FOR.get(finding.code, "")
        if not rule or rule not in policy.values:
            if not rule:
                why = "No floor rule addresses this."
            elif not policy.found:
                # Distinct from a floor that read fine and stayed silent: one is
                # a policy nobody wrote, the other a policy nobody could read,
                # and only the second says nothing about their intent.
                why = "No floor could be read, so this was not ruled on."
            else:
                why = "The floor sets no value for this rule."
            judgement.rulings.append(Ruling(
                code=finding.code, component=finding.component,
                outcome=UNGOVERNED, rule=rule, detail=why))
            continue

        in_force = policy.values[rule]
        waiver = policy.exceptions.get(rule, "")
        if waiver:
            # Checked first: permission that came from a waiver is not the same
            # fact as permission that came from the policy, and an audit that
            # cannot tell them apart cannot review its own waivers.
            outcome = WAIVED
        elif not in_force:
            outcome = ALLOWED
        else:
            outcome = DENIED
        judgement.rulings.append(Ruling(
            code=finding.code, component=finding.component, outcome=outcome,
            rule=rule, in_force=in_force,
            disregarded_domain_value=rule in policy.disregarded,
            exception_id=waiver,
            detail="" if outcome == ALLOWED else finding.statement))

    order = {o: i for i, o in enumerate(OUTCOMES)}
    judgement.rulings.sort(key=lambda r: (order.get(r.outcome, 99), r.component))
    return judgement


def assess_domain(domain: str, *, session_id: str = "") -> Judgement:
    """Inventory → findings → judgement, the whole G1→G3 path for one domain."""
    from agentic_cli import guard, guard_findings

    inventory = guard.collect(domain=domain, session_id=session_id)
    return compose(guard_findings.assess(inventory), domain)


__all__ = ["ALLOWED", "DENIED", "WAIVED", "UNGOVERNED", "INDETERMINATE",
           "OUTCOMES", "PASS", "FAIL", "UNDETERMINED", "RULE_FOR",
           "INDETERMINATE_CODES", "Ruling", "Judgement", "Policy",
           "policy_for", "compose", "assess_domain"]
