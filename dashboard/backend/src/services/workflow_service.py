"""Task Contract assembler — turn a Jira issue into a governed, launch-ready plan.

This is the P1 "Start work" surface. It does NOT enforce anything yet; it
computes a structured contract that both execution paths consume:

  - Local meta workspace  (Tech-Lead domain-tier workspace, opened in Devin/IDE)
  - Devin Cloud session    (createDevinSession with snapshot/playbook/knowledge)

The contract is derived purely from primitives that already exist:
  - Jira issue           -> jira_service.get_issue
  - Domain resolution    -> domain_service.list_domains (match jira_project)
  - Governance rules     -> domain_service.get_product_governance
  - Devin per-domain cfg -> agentic_cli.devin.config (snapshot/playbook/folder)
  - Snapshot drift       -> devin_service.list_domain_snapshots
  - Local workspace      -> workspace_service.resolve_target("tech-lead", ...)
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel


# ── Transport shapes ─────────────────────────────────────────────────────────

class ContractIssue(BaseModel):
    key: str
    summary: str
    description: str = ""
    priority: str = ""
    issuetype: str = ""
    project: str = ""
    labels: list[str] = []
    link: str = ""


class ContractDomain(BaseModel):
    found: bool
    slug: Optional[str] = None
    label: Optional[str] = None
    product: Optional[str] = None


class ContractGovernance(BaseModel):
    found: bool = False
    branch_pattern: Optional[str] = None
    require_code_review: Optional[bool] = None
    min_reviewers: Optional[int] = None
    require_tests: Optional[bool] = None
    test_coverage_min: Optional[float] = None
    require_ci_gates: Optional[bool] = None
    gates: list[str] = []


class ContractDevin(BaseModel):
    snapshot_id: Optional[str] = None
    playbook_id: Optional[str] = None
    knowledge_folder: Optional[str] = None
    snapshot_state: Optional[str] = None
    snapshot_detail: Optional[str] = None


class ContractLocalWorkspace(BaseModel):
    persona: str = "tech-lead"
    tier: str = "domain"
    path: Optional[str] = None
    exists: bool = False
    ready: bool = False
    needs: Optional[str] = None
    hint: str = ""


class TaskContract(BaseModel):
    issue: ContractIssue
    domain: ContractDomain
    governance: ContractGovernance
    devin: ContractDevin
    local_workspace: ContractLocalWorkspace
    branch_name: str = ""
    prompt: str = ""
    warnings: list[str] = []
    can_launch_local: bool = False
    can_launch_devin: bool = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
    return "-".join(words[:max_words]) or "task"


def _resolve_domain(project_key: str):
    """Find the onboarded domain whose jira_project matches this issue's project."""
    from src.services.domain_service import list_domains

    pk = (project_key or "").strip().upper()
    for d in list_domains():
        if (d.jira_project or "").strip().upper() == pk and pk:
            return d
    return None


def _branch_name(pattern: Optional[str], issuetype: str, key: str, summary: str) -> str:
    """Compute a branch name from a governance pattern (best-effort).

    Supports ``{placeholder}`` tokens (key/type/slug/summary). If the pattern
    has no tokens we treat it as a prefix; with no pattern we default to
    ``feature/<KEY>-<slug>``.
    """
    slug = _slugify(summary)
    kind = _slugify(issuetype or "feature", max_words=1) or "feature"
    tokens = {
        "key": key,
        "type": kind,
        "issuetype": kind,
        "slug": slug,
        "summary": slug,
    }
    if pattern and "{" in pattern:
        out = pattern
        for k, v in tokens.items():
            out = out.replace("{" + k + "}", str(v))
        # Drop any leftover unknown tokens.
        out = re.sub(r"\{[^}]*\}", "", out).strip("/-")
        return out or f"feature/{key}-{slug}"
    if pattern:
        return f"{pattern.rstrip('/')}/{key}-{slug}"
    return f"feature/{key}-{slug}"


def _build_prompt(issue: ContractIssue, gov: ContractGovernance, branch: str,
                  domain: ContractDomain) -> str:
    lines: list[str] = []
    lines.append(f"Implement Jira issue {issue.key}: {issue.summary}")
    if domain.found:
        lines.append(f"Domain: {domain.label or domain.slug} (product {domain.product}).")
    lines.append("")
    if issue.description:
        lines.append("## Ticket details")
        lines.append(issue.description.strip())
        lines.append("")
    lines.append("## Working agreement (governance)")
    lines.append(f"- Open a pull request from branch `{branch}`.")
    if gov.require_code_review:
        n = gov.min_reviewers or 1
        lines.append(f"- Requires code review: at least {n} reviewer(s) must approve.")
    if gov.require_tests:
        cov = f" (>= {gov.test_coverage_min}% coverage)" if gov.test_coverage_min else ""
        lines.append(f"- Add/extend tests{cov}.")
    if gov.require_ci_gates and gov.gates:
        lines.append(f"- Must pass CI gates: {', '.join(gov.gates)}.")
    if not gov.found:
        lines.append("- No product governance file found — follow repo conventions.")
    lines.append("")
    lines.append(f"Reference: {issue.link}")
    return "\n".join(lines)


# ── Public API ───────────────────────────────────────────────────────────────

def build_task_contract(issue_key: str) -> TaskContract:
    from src.services import jira_service

    warnings: list[str] = []

    # 1) Jira issue (raises RuntimeError on config/transport problems).
    detail = jira_service.get_issue(issue_key)
    if detail is None:
        raise RuntimeError(f"Issue {issue_key} not found.")

    issue = ContractIssue(
        key=detail.key, summary=detail.summary, description=detail.description,
        priority=detail.priority, issuetype=detail.issuetype,
        project=detail.project, labels=detail.labels, link=detail.link,
    )

    # 2) Resolve domain from the issue's project key.
    d = _resolve_domain(issue.project)
    if d is None:
        domain = ContractDomain(found=False)
        warnings.append(
            f"No onboarded domain maps to Jira project '{issue.project}'. "
            "Onboard the domain (set its Jira project) to enable launches."
        )
        governance = ContractGovernance()
        devin = ContractDevin()
        local = ContractLocalWorkspace()
        branch = _branch_name(None, issue.issuetype, issue.key, issue.summary)
        prompt = _build_prompt(issue, governance, branch, domain)
        return TaskContract(
            issue=issue, domain=domain, governance=governance, devin=devin,
            local_workspace=local, branch_name=branch, prompt=prompt,
            warnings=warnings, can_launch_local=False, can_launch_devin=False,
        )

    domain = ContractDomain(found=True, slug=d.name, label=d.domain, product=d.product)

    # 3) Governance rules for the product.
    governance = _governance_for(d.product, warnings)

    # 4) Devin per-domain config + snapshot drift.
    devin = _devin_for(d.name, warnings)

    # 5) Local meta workspace readiness (Tech-Lead, domain tier).
    local = _local_workspace_for(d.name, warnings)

    branch = _branch_name(governance.branch_pattern, issue.issuetype, issue.key, issue.summary)
    prompt = _build_prompt(issue, governance, branch, domain)

    return TaskContract(
        issue=issue, domain=domain, governance=governance, devin=devin,
        local_workspace=local, branch_name=branch, prompt=prompt,
        warnings=warnings,
        can_launch_local=True,
        can_launch_devin=True,
    )


def _governance_for(product: Optional[str], warnings: list[str]) -> ContractGovernance:
    if not product:
        return ContractGovernance()
    try:
        from src.services.domain_service import get_product_governance

        gi = get_product_governance(product)
        if not gi.found or not gi.governance:
            warnings.append(f"No governance file found for product '{product}'.")
            return ContractGovernance(found=bool(gi.found))
        g = gi.governance
        gates = [
            c.get("gate", "")
            for c in (g.get("checkpoint_gate_map") or [])
            if isinstance(c, dict) and c.get("gate")
        ]
        return ContractGovernance(
            found=True,
            branch_pattern=g.get("branch_pattern"),
            require_code_review=g.get("require_code_review"),
            min_reviewers=g.get("min_reviewers"),
            require_tests=g.get("require_tests"),
            test_coverage_min=g.get("test_coverage_min"),
            require_ci_gates=g.get("require_ci_gates"),
            gates=gates,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Could not read governance: {str(exc)[:120]}")
        return ContractGovernance()


def _devin_for(slug: str, warnings: list[str]) -> ContractDevin:
    dv = ContractDevin()
    try:
        from agentic_cli.devin.config import DevinConfig

        cfg = DevinConfig.load().domain(slug) or {}
        dv.snapshot_id = cfg.get("snapshot_id")
        dv.playbook_id = cfg.get("playbook_id")
        dv.knowledge_folder = cfg.get("knowledge_folder")
    except Exception:  # noqa: BLE001
        pass
    try:
        from src.services.devin_service import list_domain_snapshots

        snap = next((s for s in list_domain_snapshots() if s.domain == slug), None)
        if snap:
            dv.snapshot_state = snap.state
            dv.snapshot_detail = snap.detail
            if snap.state == "drift":
                warnings.append(
                    "Devin snapshot has drifted from the meta-repo — rebuild before delegating."
                )
    except Exception:  # noqa: BLE001
        pass
    return dv


def _local_workspace_for(slug: str, warnings: list[str]) -> ContractLocalWorkspace:
    try:
        from src.services.workspace_service import resolve_target

        t = resolve_target("tech-lead", domain=slug)
        return ContractLocalWorkspace(
            persona="tech-lead", tier=t.tier, path=t.path, exists=t.exists,
            ready=t.ready, needs=t.needs, hint=t.hint,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Could not resolve local workspace: {str(exc)[:120]}")
        return ContractLocalWorkspace()
