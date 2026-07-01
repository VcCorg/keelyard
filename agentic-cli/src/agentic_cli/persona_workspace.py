"""Persona-scoped, tier-aware development workspaces.

This module implements the three-tier workspace model:

- **Developer** (repo tier): an editable git *worktree* of a single repo, plus
  that repo's ``graphify-out/`` for navigation.
- **Tech Lead** (domain tier): *no* code — a federated set of references to each
  domain repo's ``graphify-out/`` (queried side-by-side), kept in the canonical
  store. Clones a repo only when actually editing it.
- **Solutions Architect** (product tier): tracker-only — consumes per-domain
  graph rollups across the product; clones nothing.

Design choices (federation + separate store, referenced):
- Canonical clones and their graphs live once under ``<workspace>/.store/<slug>``.
- The domain meta-repo holds only a small reference manifest
  (``.graph/graph-refs.json``) pointing at the store graphs — no copies, no code.
- Code flows *down* to developers (worktrees from the store); graphs flow *up*
  to leads/architects (references to store ``graphify-out/``).
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Persona ids per tier (built-ins augmented with the two cross-repo roles).
TIER_PERSONAS = {
    "repo": "dev",
    "domain": "tech-lead",
    "product": "solutions-architect",
}

GRAPH_REFS_FILENAME = "graph-refs.json"
GRAPH_DIR_NAME = ".graph"
STORE_DIR_NAME = ".store"

AGENT_CONFIG_FILE = Path.home() / ".agent-cli-agentic" / "config.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Workspace base / store resolution
# ---------------------------------------------------------------------------

def get_workspace_base() -> Path:
    """Resolve the code workspace base.

    Order: ``code_workspace`` in the global CLI config, else ``~/dva-code-workspace``.
    """
    if AGENT_CONFIG_FILE.exists():
        try:
            data = json.loads(AGENT_CONFIG_FILE.read_text())
            ws = data.get("code_workspace")
            if ws:
                return Path(ws).expanduser().resolve()
        except (json.JSONDecodeError, OSError):
            pass
    return (Path.home() / "dva-code-workspace").resolve()


def get_store_base() -> Path:
    """Canonical store directory: ``<workspace>/.store``."""
    return get_workspace_base() / STORE_DIR_NAME


def store_repo_path(repo_slug: str) -> Path:
    """Path to a repo's canonical clone in the store."""
    return get_store_base() / repo_slug


def find_product_meta(product: str, override: Optional[Path] = None) -> Optional[Path]:
    """Best-effort locate a product meta-repo by convention.

    Looks for ``product-<product-lower>-meta`` under the workspace base and CWD.
    An explicit ``override`` path takes precedence.
    """
    if override:
        p = Path(override).expanduser().resolve()
        return p if (p / ".platform" / "config").exists() else None

    slug = product.lower()
    name = f"product-{slug}-meta"
    base = get_workspace_base()
    candidates = [
        base / slug / name,
        base / name,
        Path.cwd() / name,
        Path.cwd(),
    ]
    for c in candidates:
        if (c / ".platform" / "config" / "product.yaml").exists():
            return c.resolve()
    return None


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _is_local_path(url: str) -> bool:
    return not (url.startswith("http://") or url.startswith("https://")
                or url.startswith("git@") or url.startswith("ssh://"))


def _git_env() -> dict:
    """Environment for git calls that must never block on a credential prompt."""
    import os
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_ASKPASS", "echo")
    return env


def _run_git(
    args: list[str],
    cwd: Optional[Path] = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            env=_git_env(),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, returncode=124, stdout="", stderr="git timed out")


def ensure_store_clone(
    repo_slug: str,
    clone_url: str,
    branch: Optional[str] = None,
) -> tuple[Path, bool]:
    """Ensure a canonical clone of ``repo_slug`` exists in the store.

    Clones if missing, otherwise fetches updates. Returns ``(path, newly_cloned)``.

    Raises:
        RuntimeError: if the clone fails.
    """
    dest = store_repo_path(repo_slug)
    if (dest / ".git").exists():
        _run_git(["fetch", "--prune"], cwd=dest, timeout=120)
        return dest, False

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = []
    if _is_local_path(clone_url):
        cmd += ["-c", "protocol.file.allow=always"]
    cmd += ["clone"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [clone_url, str(dest)]
    proc = _run_git(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to clone {repo_slug}: {proc.stderr.strip()}")
    return dest, True


def _ref_resolves(repo_path: Path, ref: str) -> bool:
    """True if ``ref`` names an existing object (commit) in the repo."""
    return _run_git(
        ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=repo_path
    ).returncode == 0


def detect_default_branch(repo_path: Path) -> str:
    """Resolve a base ref to branch a worktree from.

    Returns a ref that is guaranteed to resolve to a commit (so
    ``git worktree add -b <new> <dest> <ref>`` succeeds). A freshly-cloned
    store repo may have an *unborn* local HEAD (e.g. HEAD -> refs/heads/develop
    with no local branch) and no ``main``; in that case the checkout-able ref is
    a remote-tracking branch like ``origin/develop``. Resolution order:

    1. The current local branch, if it resolves to a commit.
    2. The remote's advertised default via ``origin/HEAD`` (e.g. ``origin/develop``).
    3. The first existing of ``origin/{develop,main,master}``.
    4. ``HEAD`` as a last resort.
    """
    proc = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    branch = proc.stdout.strip() if proc.returncode == 0 else ""
    if branch and branch != "HEAD" and _ref_resolves(repo_path, branch):
        return branch

    remote_head = _run_git(
        ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_path
    )
    ref = remote_head.stdout.strip() if remote_head.returncode == 0 else ""
    if ref and _ref_resolves(repo_path, ref):
        return ref

    for cand in ("origin/develop", "origin/main", "origin/master"):
        if _ref_resolves(repo_path, cand):
            return cand

    return "HEAD"


def add_worktree(
    repo_slug: str,
    dest: Path,
    new_branch: str,
    base_ref: Optional[str] = None,
) -> Path:
    """Create a git worktree of a store repo at ``dest`` on a new branch.

    Reuses the canonical store clone so no repo data is duplicated.

    Raises:
        RuntimeError: if the store clone is missing or the worktree add fails.
    """
    store = store_repo_path(repo_slug)
    if not (store / ".git").exists():
        raise RuntimeError(
            f"No store clone for '{repo_slug}'. Run 'dva domain sync' first."
        )
    if dest.exists() and any(dest.iterdir()):
        # Already materialized — treat as idempotent.
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    base = base_ref or detect_default_branch(store)
    proc = _run_git(
        ["worktree", "add", "-b", new_branch, str(dest), base],
        cwd=store,
    )
    if proc.returncode != 0:
        # Branch may already exist (re-open); retry without -b.
        proc2 = _run_git(["worktree", "add", str(dest), new_branch], cwd=store)
        if proc2.returncode != 0:
            raise RuntimeError(
                f"Failed to add worktree for {repo_slug}: {proc.stderr.strip()}"
            )
    return dest


# ---------------------------------------------------------------------------
# Graphify (CLI path) — federation per repo
# ---------------------------------------------------------------------------

def graphify_available() -> bool:
    """True if the graphify CLI is installed."""
    try:
        proc = subprocess.run(
            ["graphify", "--help"], capture_output=True, text=True
        )
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def run_graphify_update(repo_path: Path) -> bool:
    """Run ``graphify update . --force`` in a repo (AST-only, cheap).

    Returns True on success. Best-effort: returns False if graphify is missing
    or the run fails, without raising.
    """
    if not graphify_available():
        return False
    try:
        proc = subprocess.run(
            ["graphify", "update", ".", "--force"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning("graphify update timed out in %s", repo_path)
        return False


def graph_artifacts(repo_path: Path) -> dict:
    """Inspect a repo's ``graphify-out/`` and report available artifacts."""
    out = repo_path / "graphify-out"
    return {
        "graph_json": str(out / "graph.json") if (out / "graph.json").exists() else None,
        "report": str(out / "GRAPH_REPORT.md") if (out / "GRAPH_REPORT.md").exists() else None,
        "wiki": str(out / "wiki" / "index.md") if (out / "wiki" / "index.md").exists() else None,
        "has_graph": (out / "graph.json").exists(),
    }


def build_graph_refs(
    domain: str,
    product: Optional[str],
    repos: list[dict],
    run_graphify: bool = True,
) -> dict:
    """Ensure store clones + (optionally) refresh graphs, then build the manifest.

    Args:
        domain: Domain slug.
        product: Product name.
        repos: List of ``{repo_slug, clone_url, branch?}`` dicts (domain repos).
        run_graphify: Whether to run ``graphify update`` per repo.

    Returns:
        The federated ``graph-refs.json`` manifest dict.
    """
    have_graphify = graphify_available() if run_graphify else False
    entries = []
    for r in repos:
        slug = r.get("repo_slug") or r.get("slug")
        clone_url = r.get("clone_url", "")
        if not slug or not clone_url:
            continue
        entry = {"slug": slug, "clone_url": clone_url, "store_path": None,
                 "graph": {"has_graph": False}, "status": "pending"}
        try:
            path, _ = ensure_store_clone(slug, clone_url, r.get("branch"))
            entry["store_path"] = str(path)
            if have_graphify:
                run_graphify_update(path)
            entry["graph"] = graph_artifacts(path)
            entry["status"] = "ready"
        except Exception as e:  # noqa: BLE001 - record per-repo failure, continue
            entry["status"] = "error"
            entry["error"] = str(e)
            logger.warning("graph-ref build failed for %s: %s", slug, e)
        entries.append(entry)

    return {
        "schema": "graph-refs/v1",
        "mode": "federation",
        "domain": domain,
        "product": product,
        "store_base": str(get_store_base()),
        "graphify_available": have_graphify,
        "generated_at": _now_iso(),
        "repos": entries,
    }


def write_graph_refs(domain_meta_path: Path, manifest: dict) -> Path:
    """Write the federated manifest to ``<domain-meta>/.graph/graph-refs.json``."""
    graph_dir = domain_meta_path / GRAPH_DIR_NAME
    graph_dir.mkdir(parents=True, exist_ok=True)
    refs_path = graph_dir / GRAPH_REFS_FILENAME
    refs_path.write_text(json.dumps(manifest, indent=2))
    return refs_path


# ---------------------------------------------------------------------------
# Persona skill assembly
# ---------------------------------------------------------------------------

def persona_skill_path(root: Path, persona: str, code_assist_tool: str) -> Path:
    """Resolve the on-disk file a given IDE/agent picks up for a persona skill.

    Each tool reads from a different location and layout:

    - ``devin``    → ``.devin/skills/<persona>-context/SKILL.md`` (Devin project
      skills; also mirrored by ``.agents/skills/``). Subfolder + ``SKILL.md``.
    - ``windsurf`` → ``.windsurf/workflows/<persona>-context.md`` (flat workflow
      file with ``description:`` frontmatter — Windsurf slash-command/workflow).
    - ``cursor``   → ``.cursor/rules/<persona>-context.md`` (flat conditional rule).
    - ``generic``  → ``.skills/<persona>-context/SKILL.md`` (portable subfolder).
    """
    name = f"{persona}-context"
    if code_assist_tool == "devin":
        return root / ".devin" / "skills" / name / "SKILL.md"
    if code_assist_tool == "windsurf":
        return root / ".windsurf" / "workflows" / f"{name}.md"
    if code_assist_tool == "cursor":
        return root / ".cursor" / "rules" / f"{name}.md"
    return root / ".skills" / name / "SKILL.md"


def assemble_persona_skill(
    root: Path,
    persona: str,
    content: str,
    code_assist_tool: str = "windsurf",
) -> Path:
    """Write a persona context skill into the IDE-specific pickup location.

    Returns the path written. ``content`` already carries ``name:`` /
    ``description:`` frontmatter, which Windsurf/Cursor/Devin all require to load
    the file as a workflow/rule/skill.
    """
    skill_path = persona_skill_path(root, persona, code_assist_tool)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(content)
    return skill_path


def render_dev_skill(ctx: dict) -> str:
    """Repo-tier developer persona skill (single repo + its graphify-out)."""
    return f"""---
name: {ctx['domain']}-dev-context
description: >-
  Developer (repo tier) context for {ctx['repo_slug']} in the {ctx['domain_label']}
  domain ({ctx['product']}). Single-repo coding with graphify navigation.
domain: {ctx['domain']}
product: {ctx['product']}
tier: repo
persona: dev
repo: {ctx['repo_slug']}
generated_at: {_now_iso()}
---

# Developer Workspace — {ctx['repo_slug']}

You are working at the **repo tier** as a **developer**. Scope is this single
repository; use graphify to navigate it and keep the graph current as you edit.

## Code Navigation (graphify, single repo)

This repo has a graphify graph at `graphify-out/`. Prefer graph queries over
broad grep:

- `graphify query "<question>"` — scoped subgraph for a question
- `graphify explain "<symbol>"` — explain a node and its neighbors
- `graphify path "<A>" "<B>"` — shortest path between two nodes

After modifying files this session, refresh the graph:

```bash
graphify update .
```

## Domain & Product Context

- Domain business context: see the `domain-context` skill (KG/MCP) for SLAs,
  integrations, security, and architecture constraints.
- Branch convention: `feature/{ctx['product']}-<ticket>-<short-description>`.

## Boundaries

- Stay within this repo. For cross-repo/architecture questions, escalate to the
  **tech-lead** workspace (domain tier), which federates graphs across all repos.
"""


def render_tech_lead_skill(ctx: dict) -> str:
    """Domain-tier tech-lead persona skill (federated graphs, no code)."""
    repo_lines = "\n".join(
        f"- **{r['slug']}** — graph: {'available' if r.get('graph', {}).get('has_graph') else 'not generated'} "
        f"(`{r.get('store_path') or 'not cloned'}`)"
        for r in ctx.get("repos", [])
    ) or "- _(no repos linked yet)_"

    return f"""---
name: {ctx['domain']}-tech-lead-context
description: >-
  Tech Lead (domain tier) context for the {ctx['domain_label']} domain
  ({ctx['product']}). Federated, cross-repo graph reasoning over ALL domain
  repos via referenced graphify-out — no code checkout.
domain: {ctx['domain']}
product: {ctx['product']}
tier: domain
persona: tech-lead
generated_at: {_now_iso()}
---

# Tech Lead Workspace — {ctx['domain_label']} Domain

You are working at the **domain tier** as a **tech lead**. You reason across
**all** repos in the domain using their graphify graphs — without cloning code.
Clone a repo (open a dev workspace) only when you actually need to edit it.

## Federated Graph References

The manifest at `{GRAPH_DIR_NAME}/{GRAPH_REFS_FILENAME}` lists each repo's graph
in the canonical store (federation — no merged graph). Query each side-by-side
and compose the answers.

Repos in this domain:
{repo_lines}

## How to Answer Cross-Repo Questions

1. Read `{GRAPH_DIR_NAME}/{GRAPH_REFS_FILENAME}` to get each repo's `store_path`.
2. For each repo with `has_graph: true`, run graphify against its store path:
   - `graphify query "<question>"` (run from the repo's store_path)
   - `graphify explain "<symbol>"`
3. **Compose** the per-repo results to infer cross-repo links (e.g. which
   service calls another's REST endpoint, shared model usage, duplication).

## Architecture Lens (review focus)

Use each repo's `graphify-out/GRAPH_REPORT.md` analysis for lead-level review:
- highly-connected components (god-nodes), module/community boundaries,
  notable patterns/anomalies, and architecture questions.

## Governance

The domain inherits product governance via `repos/product-meta` (promotion path,
crosswalk, exceptions). Enforce branch naming and checkpoint gates for the team.

## Escalation

For cross-**domain** / solution-design concerns, escalate to the
**solutions-architect** workspace (product tier).
"""


def render_sa_skill(ctx: dict) -> str:
    """Product-tier solutions-architect persona skill (tracker-only rollups)."""
    domain_lines = "\n".join(
        f"- **{d['domain']}** — {d.get('repo_count', 0)} repo(s), "
        f"graphs: {d.get('graphs_ready', 0)}/{d.get('repo_count', 0)} ready"
        for d in ctx.get("domains", [])
    ) or "- _(no domains registered yet)_"

    return f"""---
name: {ctx['product'].lower()}-solutions-architect-context
description: >-
  Solutions Architect (product tier) context for {ctx['product']}. Cross-domain
  solution design from tracker rollups + per-domain graph reports. Tracker-only:
  no code checkout.
product: {ctx['product']}
tier: product
persona: solutions-architect
generated_at: {_now_iso()}
---

# Solutions Architect Workspace — {ctx['product']}

You are working at the **product tier** as a **solutions architect**. You do
cross-domain solution design from the registry and per-domain graph rollups —
you do **not** clone code.

## Domains in this Product
{domain_lines}

## How to Work

1. Use the registry (`dva workspace status --product {ctx['product']}`) for the
   product → domain → repo map and graph availability.
2. For a domain's structure, read its tech-lead manifest
   (`<domain-meta>/{GRAPH_DIR_NAME}/{GRAPH_REFS_FILENAME}`) and the referenced
   `graphify-out/GRAPH_REPORT.md` rollups.
3. Reason about cross-domain coupling, shared models, duplication, and
   integration seams for solution design.

## Governance Authoring

This product meta-repo owns governance (promotion path, crosswalk, exceptions,
persona catalog). Solution decisions that change gates belong here.

## Drilling Down

To inspect a specific repo's code, open a dev workspace on demand:
`dva workspace open <domain> <repo> --persona dev` (creates a worktree).
"""
