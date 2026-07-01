"""Scaffold a product meta-repo (top-level outer-loop tier).

A product meta-repo holds the *shared* outer-loop governance for all domains
under a product, plus the inner↔outer crosswalk and the exceptions ledger. It
references the org-wide methodology (inner loop) as a pinned submodule.

Structure (product-<name>-meta):
    .platform/config/
        product.yaml        — product metadata + pinned org-methodology url
        governance.yaml      — shared gates + promotion_path + checkpoint_gate_map
        crosswalk.yaml       — inner checkpoint ↔ outer promotion-gate map
    outer-loop/product/
        definition-of-done.md
        promotion-path.md
        pipeline-standards.md
    inner-loop/              — submodule → org methodology (pinned), if url given
    exceptions/
        README.md            — how the "override with justification" ledger works
    docs/
        README.md, GOVERNANCE.md
    Makefile, README.md, .gitignore
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .config import GovernanceConfig, ProductConfig
from .git_utils import register_submodule, resolve_remote_sha

logger = logging.getLogger(__name__)


def scaffold_product_meta_repo(
    output_dir: Path,
    product: str,
    description: str = "",
    owner: str = "",
    org_methodology_url: Optional[str] = None,
    git_init: bool = True,
) -> dict[str, Path]:
    """Create a product meta-repo directory structure.

    Args:
        output_dir: Parent directory where the meta-repo will be created.
        product: Product name (e.g. "ABC", "CWOW").
        description: Product description.
        owner: Product owner email.
        org_methodology_url: Git URL of the org-wide methodology (inner loop)
            to add as a pinned submodule. Optional.
        git_init: Initialize as a git repo (and add the submodule).

    Returns:
        Dict mapping logical names to created paths.

    Raises:
        ValueError: If output_dir is missing or the meta-repo already exists.
        RuntimeError: If git operations fail.
    """
    if not output_dir.exists():
        raise ValueError(f"Output directory does not exist: {output_dir}")

    slug = product.lower()
    meta_repo_name = f"product-{slug}-meta"
    meta_repo_path = output_dir / meta_repo_name

    if meta_repo_path.exists():
        raise ValueError(f"Product meta-repo already exists: {meta_repo_path}")

    created: dict[str, Path] = {}

    try:
        meta_repo_path.mkdir(parents=True, exist_ok=True)
        created["root"] = meta_repo_path

        # .platform/config
        config_dir = meta_repo_path / ".platform" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        created["config"] = config_dir

        # outer-loop/product
        outer_dir = meta_repo_path / "outer-loop" / "product"
        outer_dir.mkdir(parents=True, exist_ok=True)
        created["outer_loop_product"] = outer_dir

        # exceptions ledger
        exceptions_dir = meta_repo_path / "exceptions"
        exceptions_dir.mkdir(exist_ok=True)
        created["exceptions"] = exceptions_dir

        # docs
        docs_dir = meta_repo_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        created["docs"] = docs_dir

        # Write config files
        _write_product_config(config_dir, product, description, owner, org_methodology_url)
        _write_governance_config(config_dir)
        _write_crosswalk_config(config_dir)
        _write_personas_config(config_dir)

        # Write outer-loop product files
        _write_outer_loop_product(outer_dir, product)

        # Write exceptions ledger README
        _write_exceptions_readme(exceptions_dir, product)

        # Write docs
        _write_docs(meta_repo_path, product, description)
        _write_root_readme(meta_repo_path, product, description)
        _write_makefile(meta_repo_path)
        _write_gitignore(meta_repo_path)

        if git_init:
            _init_git_repo(meta_repo_path, org_methodology_url)

        logger.info(f"Created product meta-repo at {meta_repo_path}")
        return created

    except Exception as e:
        logger.error(f"Failed to scaffold product meta-repo: {e}")
        raise


def _write_product_config(
    config_dir: Path,
    product: str,
    description: str,
    owner: str,
    org_methodology_url: Optional[str],
) -> None:
    config = ProductConfig(
        product=product.upper(),
        description=description,
        owner=owner,
        created_at=datetime.utcnow().isoformat() + "Z",
        org_methodology_url=org_methodology_url or "",
    )
    with open(config_dir / "product.yaml", "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


def _write_governance_config(config_dir: Path) -> None:
    governance = GovernanceConfig()
    with open(config_dir / "governance.yaml", "w") as f:
        yaml.dump(governance.to_dict(), f, default_flow_style=False, sort_keys=False)


def _write_crosswalk_config(config_dir: Path) -> None:
    """Write crosswalk.yaml — the inner↔outer checkpoint/gate map (standalone)."""
    governance = GovernanceConfig()
    crosswalk = {
        "promotion_path": governance.promotion_path,
        "checkpoint_gate_map": governance.checkpoint_gate_map,
    }
    with open(config_dir / "crosswalk.yaml", "w") as f:
        yaml.dump(crosswalk, f, default_flow_style=False, sort_keys=False)


def _write_personas_config(config_dir: Path) -> None:
    """Write a starter personas.yaml catalog with built-in defaults enabled.

    Product teams edit this to enable/disable built-ins and to add their own
    personas (e.g. tech-lead, product-owner). Written with explanatory comments
    plus a commented example so it is self-documenting.
    """
    content = """\
# Persona catalog for this product.
#
# `defaults_enabled` selects which built-in personas are generated into each
# domain meta-repo (.agents/skills/personas/<id>/SKILL.md) during scaffolding.
# Built-ins: domain, dev, qa, sm, ba
#
# Add product-specific personas under `personas`. Each is rendered
# deterministically from its `sections`; set `ai_enrich: true` to also enrich
# it via the onboard agent when a model is available (falls back to the
# skeleton when not).
version: 1
defaults_enabled:
  - domain
  - dev
  - qa
  - sm
  - ba
personas: []
# Example — uncomment and customize for your product team:
# personas:
#   - id: tech-lead
#     label: Tech Lead
#     description: Architecture direction, ADRs, review standards
#     ai_enrich: true
#     sections:
#       - title: Responsibilities
#         body: |
#           - Own technical design and ADRs
#           - Set and uphold the code-review bar
#           - Manage technical debt and sequencing
#       - title: Review Standards
#         body: |
#           - Require tests for all behavior changes
#           - Block on security and data-migration risks
#   - id: product-owner
#     label: Product Owner
#     description: Backlog ownership, prioritization, acceptance
#     sections:
#       - title: Responsibilities
#         body: |
#           - Own and prioritize the backlog
#           - Define acceptance criteria
#           - Sign off on releases
"""
    (config_dir / "personas.yaml").write_text(content, encoding="utf-8")
    logger.debug("Wrote personas config: %s", config_dir / "personas.yaml")


def _write_outer_loop_product(outer_dir: Path, product: str) -> None:
    (outer_dir / "definition-of-done.md").write_text(
        f"""# {product.upper()} — Definition of Done (Product-Shared)

A change in any {product.upper()} domain is **done** only when it passes both loops:

## Inner loop (engineering discipline)
- [ ] Spec approved before code (spec-first gate)
- [ ] Tests written first; code without a failing test first is discarded (TDD)
- [ ] Work decomposed into small, verifiable tasks
- [ ] Two-stage review passed (spec compliance, then code quality)

## Outer loop (governance)
- [ ] Branch follows naming convention
- [ ] CI gates pass (SAST, SCA, unit tests ≥ coverage min)
- [ ] Code review approvals met
- [ ] Promotes cleanly through the environment path (see promotion-path.md)

Any relaxation of an inner-loop item requires a recorded exception
(see `../../exceptions/`).
""",
        encoding="utf-8",
    )
    (outer_dir / "promotion-path.md").write_text(
        f"""# {product.upper()} — Environment Promotion Path

```
dev → qa → uat → prd
```

Each stage applies progressively stricter quality gates. The mapping of
engineering checkpoints to promotion gates lives in
`.platform/config/crosswalk.yaml` (the inner↔outer crosswalk).

| Gate | Checkpoint required (inner loop) |
|------|----------------------------------|
| dev  | spec-approved |
| qa   | tests-green |
| uat  | code-review-passed |
| prd  | governance-gates-passed |
""",
        encoding="utf-8",
    )
    (outer_dir / "pipeline-standards.md").write_text(
        f"""# {product.upper()} — Pipeline Standards (Product-Shared)

Shared CI/CD expectations inherited by all {product.upper()} domains. Domains
may **tighten** these but not loosen them without a recorded exception.

- SAST (static application security testing) — required
- SCA (software composition analysis) — required
- Unit tests — required, coverage floor defined in `governance.yaml`
- Reproducible builds; pinned submodule references for methodology provenance
""",
        encoding="utf-8",
    )


def _write_exceptions_readme(exceptions_dir: Path, product: str) -> None:
    (exceptions_dir / "README.md").write_text(
        f"""# {product.upper()} — Exceptions Ledger

This directory is the **auditable record of governance waivers** for
{product.upper()}. Domains and repos may *tighten* governance freely; *loosening*
an inner-loop or product rule requires an exception entry here
("override with justification").

## Entry format

Each waiver is a YAML file `exceptions/<id>.yaml`:

```yaml
id: EX-0001
rule: tdd                      # the rule being relaxed
reason: Spike to validate API  # why
scope: domain:cwow-facility    # domain:<slug> or repo:<slug>
owner: someone@example.com
created_at: 2026-06-27
expires_at: 2026-07-27         # waivers should expire
status: active                 # active | expired | revoked
```

## Managing entries

```bash
dva product exceptions add {product.upper()} --rule tdd \\
    --reason "spike" --scope domain:{product.lower()}-a1 \\
    --owner you@example.com --expires 2026-07-27
dva product exceptions list {product.upper()}
```
""",
        encoding="utf-8",
    )


def _write_docs(meta_repo_path: Path, product: str, description: str) -> None:
    docs_dir = meta_repo_path / "docs"
    (docs_dir / "README.md").write_text(
        f"""# {product.upper()} Product Meta-Repo

{description or "Top-level outer-loop governance shared across this product's domains."}

## Structure
- `.platform/config/` — product.yaml, governance.yaml, crosswalk.yaml
- `outer-loop/product/` — definition-of-done, promotion-path, pipeline-standards
- `inner-loop/` — submodule → org methodology (pinned, inner loop)
- `exceptions/` — governance waiver ledger
- `docs/` — this guide + GOVERNANCE.md
""",
        encoding="utf-8",
    )
    (docs_dir / "GOVERNANCE.md").write_text(
        f"""# {product.upper()} Governance (Product Tier)

This product tier defines the **shared outer-loop** governance inherited by all
domains, plus the inner↔outer **crosswalk** and the **exceptions ledger**.

## Precedence cascade
```
domain  >  product  >  inner-loop baseline
```
Lower tiers may tighten; loosening the inner-loop floor requires an exception.

## Crosswalk
See `.platform/config/crosswalk.yaml` — maps engineering checkpoints to the
`dev → qa → uat → prd` promotion gates.

## Exceptions
See `exceptions/` — every loosening of an inner-loop rule is recorded, scoped,
owned, and (ideally) given an expiry.
""",
        encoding="utf-8",
    )


def _write_root_readme(meta_repo_path: Path, product: str, description: str) -> None:
    (meta_repo_path / "README.md").write_text(
        f"""# {product.upper()} Product Meta-Repo

**Tier:** Product (outer-loop, shared)

{description or "Shared governance, crosswalk, and exceptions for this product's domains."}

## Quickstart
```bash
make init       # initialize the inner-loop submodule
make validate   # validate repo state
```

## Layout
| Path | Purpose |
|------|---------|
| `.platform/config/` | product.yaml, governance.yaml, crosswalk.yaml |
| `outer-loop/product/` | DoD, promotion path, pipeline standards |
| `inner-loop/` | submodule → org methodology (inner loop, pinned) |
| `exceptions/` | governance waiver ledger |
| `docs/` | governance documentation |

Domain meta-repos reference this product meta-repo via
`dva domain init-meta <slug> --product-meta <url>`.
""",
        encoding="utf-8",
    )


def _write_makefile(meta_repo_path: Path) -> None:
    (meta_repo_path / "Makefile").write_text(
        """.PHONY: init update validate help

init:
\t@echo "Initializing product meta-repo (shallow, parallel)..."
\tgit -c protocol.file.allow=always submodule update --init --recursive --depth 1 --jobs 8
\t@echo "✓ Submodules initialized"

update:
\t@echo "Updating inner-loop submodule..."
\tgit submodule update --remote --merge
\t@echo "✓ Submodules updated"

validate:
\t@if [ -d ".platform/config" ]; then echo "✓ .platform/config exists"; else echo "✗ .platform/config missing"; exit 1; fi
\t@if [ -d "exceptions" ]; then echo "✓ exceptions ledger exists"; else echo "✗ exceptions missing"; exit 1; fi
\t@echo "✓ Validation passed"

help:
\t@echo "Product Meta-Repo Targets:"
\t@echo "  make init      - Initialize submodules (inner loop)"
\t@echo "  make update    - Update submodules"
\t@echo "  make validate  - Validate repo state"
""",
        encoding="utf-8",
    )


def _write_gitignore(meta_repo_path: Path) -> None:
    (meta_repo_path / ".gitignore").write_text(
        """plans/
*.local
.DS_Store
.vscode/
.idea/
__pycache__/
*.py[cod]
.env
""",
        encoding="utf-8",
    )


def _init_git_repo(meta_repo_path: Path, org_methodology_url: Optional[str]) -> None:
    """Initialize the product meta-repo git repo.

    The org-methodology (inner loop) is *registered* as a submodule (pinned
    gitlink + ``.gitmodules``) without cloning — the working tree is fetched
    lazily via ``make init``. The pinned commit is resolved clone-free with
    ``git ls-remote``, keeping scaffolding fast.
    """
    try:
        subprocess.run(
            ["git", "init"], cwd=str(meta_repo_path), check=True, capture_output=True
        )

        # Stage scaffold files FIRST. `git add .` stages deletions for tracked
        # paths missing from the working tree, which would clobber the (un-cloned)
        # submodule gitlink registered below — so do it before registration.
        subprocess.run(
            ["git", "add", "."], cwd=str(meta_repo_path), check=True, capture_output=True
        )

        if org_methodology_url:
            resolved = resolve_remote_sha(org_methodology_url)
            sha = resolved[0] if resolved else None
            branch = resolved[1] if resolved else None
            register_submodule(
                meta_repo_path, org_methodology_url, "inner-loop",
                sha=sha, branch=branch,
            )
            subprocess.run(
                ["git", "add", ".gitmodules"],
                cwd=str(meta_repo_path), check=True, capture_output=True,
            )
            logger.debug(
                f"Registered inner-loop submodule (deferred): {org_methodology_url} "
                f"(sha={sha[:8] if sha else 'pointer-only'})"
            )

        subprocess.run(
            ["git", "commit", "-m", "Initial commit: product meta-repo scaffold"],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        raise RuntimeError(f"Git operation failed: {stderr}")


# ── Exceptions ledger helpers ───────────────────────────────────────────────

def add_exception(
    meta_repo_path: Path,
    rule: str,
    reason: str,
    scope: str,
    owner: str,
    expires_at: str = "",
) -> "object":
    """Append a waiver to the product meta-repo's exceptions ledger.

    Returns the created ExceptionEntry. Raises ValueError if the ledger dir
    is missing.
    """
    from datetime import date
    from .config import ExceptionEntry

    exceptions_dir = meta_repo_path / "exceptions"
    if not exceptions_dir.exists():
        raise ValueError(f"Exceptions ledger not found at {exceptions_dir}")

    existing = sorted(exceptions_dir.glob("EX-*.yaml"))
    next_num = len(existing) + 1
    ex_id = f"EX-{next_num:04d}"

    entry = ExceptionEntry(
        id=ex_id,
        rule=rule,
        reason=reason,
        scope=scope,
        owner=owner,
        created_at=date.today().isoformat(),
        expires_at=expires_at,
        status="active",
    )
    with open(exceptions_dir / f"{ex_id}.yaml", "w") as f:
        yaml.dump(entry.to_dict(), f, default_flow_style=False, sort_keys=False)
    return entry


def list_exceptions(meta_repo_path: Path) -> list:
    """Return all ExceptionEntry objects from the ledger (sorted by id)."""
    from .config import ExceptionEntry

    exceptions_dir = meta_repo_path / "exceptions"
    if not exceptions_dir.exists():
        return []
    out = []
    for path in sorted(exceptions_dir.glob("EX-*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        out.append(ExceptionEntry.from_dict(data))
    return out
