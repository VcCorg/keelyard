"""Scaffold domain meta-repo directory structure."""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from .config import DomainConfig, GovernanceConfig, RepoConfig, SkillsConfig
from .git_utils import register_submodule, resolve_remote_shas
from .template_manifest import write_manifest

logger = logging.getLogger(__name__)


def scaffold_domain_meta_repo(
    output_dir: Path,
    domain: str,
    product: str,
    description: str = "",
    owner: str = "",
    context_repo_url: Optional[str] = None,
    product_meta_url: Optional[str] = None,
    repos: Optional[list[dict]] = None,
    git_init: bool = True,
    code_assist_tool: str = "generic",
    personas: Optional[list] = None,
    persona_context: Optional[dict] = None,
    enrich_personas: bool = False,
    clone_repos: bool = False,
    write_blueprint: bool = True,
    repo_name: Optional[str] = None,
    allow_existing: bool = False,
) -> dict[str, Path]:
    """Create domain meta-repo directory structure.

    Args:
        output_dir: Parent directory where meta-repo will be created
        domain: Domain slug (e.g., "cwow-facility")
        product: Product name (e.g., "CWOW")
        description: Domain description
        owner: Domain owner email
        context_repo_url: Git URL of domain-context-repo (optional)
        repos: List of linked repo configs (optional)
        git_init: Initialize as git repo with submodules
        code_assist_tool: Code assist tool (windsurf, cursor, or generic)
        personas: Resolved list of PersonaSpec to generate into
            ``.agents/skills/personas/<id>/SKILL.md`` (optional)
        persona_context: Domain context dict (from gather_domain_context) used
            to render personas. Required for persona generation.
        enrich_personas: Whether to AI-enrich custom personas marked ai_enrich.

    Returns:
        Dictionary mapping directory names to created paths.

    Raises:
        ValueError: If output_dir doesn't exist or is not writable
        RuntimeError: If git operations fail
    """
    if not output_dir.exists():
        raise ValueError(f"Output directory does not exist: {output_dir}")

    meta_repo_name = repo_name or f"domain-{domain}-meta"
    meta_repo_path = output_dir / meta_repo_name

    # ``allow_existing`` lets the unified context-meta flow layer meta content
    # into a directory that already holds the domain-context files/skills.
    if meta_repo_path.exists() and any(meta_repo_path.iterdir()) and not allow_existing:
        raise ValueError(f"Meta-repo already exists: {meta_repo_path}")

    created = {}

    try:
        # Create root directory
        meta_repo_path.mkdir(parents=True, exist_ok=True)
        created["root"] = meta_repo_path

        # Create .platform directory structure
        platform_dir = meta_repo_path / ".platform"
        platform_dir.mkdir(exist_ok=True)
        created["platform"] = platform_dir

        config_dir = platform_dir / "config"
        config_dir.mkdir(exist_ok=True)
        created["config"] = config_dir

        common_dir = platform_dir / "common"
        common_dir.mkdir(exist_ok=True)
        created["common"] = common_dir

        scripts_dir = platform_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        created["scripts"] = scripts_dir

        # Create .agents directory structure
        agents_dir = meta_repo_path / ".agents"
        agents_dir.mkdir(exist_ok=True)
        created["agents"] = agents_dir

        agents_subdir = agents_dir / "agents"
        agents_subdir.mkdir(exist_ok=True)
        created["agents_subdir"] = agents_subdir

        skills_subdir = agents_dir / "skills"
        skills_subdir.mkdir(exist_ok=True)
        created["skills_subdir"] = skills_subdir

        # Create repos directory (for submodules)
        repos_dir = meta_repo_path / "repos"
        repos_dir.mkdir(exist_ok=True)
        created["repos"] = repos_dir

        # Create docs directory
        docs_dir = meta_repo_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        created["docs"] = docs_dir

        # Create plans directory (gitignored)
        plans_dir = meta_repo_path / "plans"
        plans_dir.mkdir(exist_ok=True)
        created["plans"] = plans_dir

        # Create .githooks directory
        githooks_dir = meta_repo_path / ".githooks"
        githooks_dir.mkdir(exist_ok=True)
        created["githooks"] = githooks_dir

        # Write configuration files
        _write_domain_config(config_dir, domain, product, description, owner)
        _write_repos_config(config_dir, repos or [])
        _write_governance_config(config_dir)
        _write_skills_config(config_dir)

        # Write platform common files
        _write_platform_common(common_dir)
        _write_skills_profiler(scripts_dir)
        _write_platform_readme(platform_dir, domain)

        # Write documentation files
        _write_docs(meta_repo_path, domain, product, description)

        # Write root-level docs (README.md, AGENTS.md) per meta-repo standards
        _write_root_readme(meta_repo_path, domain, product, description)
        _write_agents_md(meta_repo_path, domain)

        # Generate persona skills into .agents/skills/personas/<id>/SKILL.md
        if personas and persona_context:
            persona_paths = _generate_personas(
                skills_subdir, personas, persona_context, enrich_personas
            )
            if persona_paths:
                created["personas"] = skills_subdir / "personas"

        # Write git hooks (pre-push branch-naming enforcement)
        _write_pre_push_hook(githooks_dir)

        # Write Makefile
        _write_makefile(meta_repo_path)

        # Write .gitignore
        _write_gitignore(meta_repo_path)

        # Write the Devin DRS snapshot blueprint (.devin/environment.yaml +
        # setup.sh). Generated here so it is captured in the initial commit;
        # the snapshot itself is built later via `keel domain build-snapshot`.
        if write_blueprint:
            from agentic_cli.devin.blueprint import (
                load_workspace_mcp_servers,
                write_domain_blueprint,
            )

            bp = write_domain_blueprint(
                meta_repo_path,
                domain,
                product,
                code_assist_tool=code_assist_tool,
                mcp_servers=load_workspace_mcp_servers(),
            )
            created["devin_blueprint"] = bp["environment"]

        # Apply the template overlay LAST, so promoted improvements win over the
        # built-in defaults written above — and BEFORE the manifest below, so
        # overlay content is part of the recorded baseline. A fresh install has
        # an empty overlay, making this a no-op.
        from .template_overlay import apply_overlay

        overlaid = apply_overlay(
            meta_repo_path, domain=domain, product=product,
            description=description, owner=owner,
        )
        if overlaid:
            created["template_overlay"] = meta_repo_path
            logger.debug("Applied %d template overlay file(s)", len(overlaid))

        # Fingerprint the template that produced this repo (.platform/template.json)
        # BEFORE the initial commit, so the baseline is versioned with the repo.
        # This is what lets `keel domain template status` later tell a template
        # update apart from a local edit.
        created["template_manifest"] = write_manifest(
            meta_repo_path, domain, product, description, owner
        )

        # Initialize git repository if requested
        if git_init:
            _init_git_repo(
                meta_repo_path, context_repo_url, repos or [], product_meta_url,
                clone_repos=clone_repos,
            )

        logger.info(f"Created domain meta-repo at {meta_repo_path}")
        return created

    except Exception as e:
        logger.error(f"Failed to scaffold meta-repo: {e}")
        raise


def _write_domain_config(
    config_dir: Path, domain: str, product: str, description: str, owner: str
) -> None:
    """Write domain.yaml configuration file."""
    config = DomainConfig(
        domain=domain,
        product=product,
        description=description,
        owner=owner,
        created_at=datetime.utcnow().isoformat() + "Z",
    )

    config_file = config_dir / "domain.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote domain config: {config_file}")


def _write_repos_config(config_dir: Path, repos: list[dict]) -> None:
    """Write repos.yaml configuration file."""
    repos_config = {"repos": repos}

    config_file = config_dir / "repos.yaml"
    with open(config_file, "w") as f:
        yaml.dump(repos_config, f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote repos config: {config_file}")


def _write_governance_config(config_dir: Path) -> None:
    """Write governance.yaml configuration file."""
    governance = GovernanceConfig()

    config_file = config_dir / "governance.yaml"
    with open(config_file, "w") as f:
        yaml.dump(governance.to_dict(), f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Wrote governance config: {config_file}")


def _write_skills_config(config_dir: Path) -> None:
    """Write a documented skills.yaml with persona-scoped governance.

    Authored as commented YAML (not a bare dump) so the ``personas`` policy is
    self-explanatory. It round-trips through ``SkillsConfig.from_dict`` and the
    stdlib profiler reads the ``personas`` block directly to enforce, per user
    profile, which skills a persona may load/use.
    """
    config_file = config_dir / "skills.yaml"
    config_file.write_text(
        """\
# Domain skills policy.
#
# validation/priority govern how skills are sourced and ranked. The `personas`
# block governs WHO may use WHICH skills — persona-scoped access control that
# `make skills PERSONA=<id>` / `make validate PERSONA=<id>` report on, and that
# `keel code onboard` enforces for a signed-in user (their SSO profile resolves
# to a persona; see KEEL_PERSONA_MAP).
validation_required: true
auto_inject_superpowers: true
allow_custom_skills: true
skill_priority_order:
  - validated
  - customized
  - injected

# Persona -> skill governance.
#   allow/deny tokens: tier names (persona, agent-skill, domain-validated,
#   linked:<repo>, local), persona:self, persona:<id>, skill-name globs, or '*'.
#   A specific (non-'*') deny always wins. `deny: ['*']` makes a persona
#   allow-list only. `default` applies to any persona without an explicit rule
#   and is least-privilege on purpose. Tune these per domain.
personas:
  # Everyone may read persona guidance + domain-validated skills.
  default:
    allow: [persona, domain-validated]
    deny: []
  # Builders get everything; add explicit denies to fence off anything a dev
  # must never touch (a specific deny fails `make validate PERSONA=dev`).
  dev:
    allow: ['*']
    deny: []
  domain:
    allow: ['*']
    deny: []
  # Non-builder personas are allow-list only. deny: ['*'] is the baseline, so
  # unlisted skills are "out-of-policy" (not granted) rather than a violation.
  qa:
    allow: [persona, domain-validated, 'testing-*']
    deny: ['*']
  ba:
    allow: [persona, domain-validated]
    deny: ['*']
  sm:
    allow: [persona, domain-validated]
    deny: ['*']
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote skills config: {config_file}")


def _generate_personas(
    skills_subdir: Path,
    personas: list,
    persona_context: dict,
    enrich: bool,
) -> dict:
    """Render persona skills into .agents/skills/personas/<id>/SKILL.md.

    Lazy-imported to avoid an import cycle during meta_repo package init.
    """
    from agentic_cli.skill_generator import generate_personas

    personas_dir = skills_subdir / "personas"
    written = generate_personas(personas, persona_context, personas_dir, enrich=enrich)
    logger.debug("Generated %d persona skills in %s", len(written), personas_dir)
    return written


def _write_platform_common(common_dir: Path) -> None:
    """Write platform common files."""
    # __init__.py
    init_file = common_dir / "__init__.py"
    init_file.write_text('"""Platform common utilities."""\n')

    # config_loader.py
    config_loader_file = common_dir / "config_loader.py"
    config_loader_file.write_text(
        '''"""Load and parse platform configuration files."""

import yaml
from pathlib import Path
from typing import Any


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config(config_dir: Path, filename: str) -> dict[str, Any]:
    """Load config file from .platform/config/."""
    return load_yaml(config_dir / filename)
'''
    )

    logger.debug(f"Wrote platform common files to {common_dir}")


def _write_skills_profiler(scripts_dir: Path) -> None:
    """Write .platform/scripts/profile_skills.py — the skills loader/profiler.

    Stdlib-only (no keel/PyYAML dependency) so it runs on any clone with just
    ``python3``. ``make init`` calls it with ``--write`` to load/index every
    skill across ``.agents/skills`` and the ``repos/*`` submodules into
    ``.platform/skills-manifest.json``; ``make validate`` calls it with
    ``--check`` to print the profile of what is loaded into the working repo.
    """
    script = scripts_dir / "profile_skills.py"
    script.write_text(
        '''#!/usr/bin/env python3
"""Load and profile the skills present across this domain meta-repo.

Skills live in several places once the repo is initialized:

  * ``.agents/skills/personas/<id>/SKILL.md``  — role personas (baked in)
  * ``.agents/skills/<name>/SKILL.md``          — domain/local agent skills
  * ``repos/domain-context/**/SKILL.md``        — domain-validated skills
  * ``repos/<linked>/**/SKILL.md``              — skills carried by linked repos

This scans for every ``SKILL.md``, classifies it by source tier, and:

  --write     refresh ``.platform/skills-manifest.json`` (the loaded index)
  --summary   print a grouped, counted profile (default when no flag given)
  --check     print the profile plus soft warnings (uninitialized submodules)
  --json      print the raw manifest JSON to stdout

Exit status is 0 in every mode; this is a profiler, not a gate. Missing skills
are surfaced as warnings so ``make validate`` stays informative, not blocking.
"""

import fnmatch
import json
import sys
from pathlib import Path

# scripts/ -> .platform/ -> repo root
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / ".platform" / "skills-manifest.json"
CONFIG = ROOT / ".platform" / "config" / "skills.yaml"

# Fallback when a persona has no explicit rule and no `default` is defined.
_BUILTIN_DEFAULT = {"allow": ["persona:self", "domain-validated"], "deny": []}

# Directories that never hold first-class skills; pruned while walking.
_PRUNE = {".git", "node_modules", "__pycache__", ".venv", "venv",
          "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def _parse_frontmatter(text):
    """Minimal YAML-frontmatter reader: name/description without PyYAML."""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    fm, key, folded, buf = {}, None, False, []
    for ln in lines[1:end]:
        if folded:
            if ln.strip() and (ln.startswith(" ") or ln.startswith("\\t")):
                buf.append(ln.strip())
                continue
            fm[key] = " ".join(buf).strip()
            folded, buf = False, []
        if not ln.strip():
            continue
        if ":" in ln and not (ln.startswith(" ") or ln.startswith("\\t")):
            k, _, v = ln.partition(":")
            k, v = k.strip(), v.strip()
            if v in (">-", ">", "|", "|-", ">+", "|+"):
                key, folded, buf = k, True, []
            else:
                fm[k] = v.strip('"').strip("'")
    if folded and buf:
        fm[key] = " ".join(buf).strip()
    return fm


def _tier(rel):
    """Classify a SKILL.md by its location relative to the repo root."""
    parts = rel.parts
    if parts[:1] == (".agents",) and "personas" in parts:
        return "persona"
    if parts[:2] == (".agents", "skills"):
        return "agent-skill"
    if parts[:2] == ("repos", "domain-context"):
        return "domain-validated"
    if parts[:1] == ("repos",) and len(parts) > 1:
        return "linked:" + parts[1]
    if parts[:1] == (".skills",):
        return "local"
    return "other"


def _iter_skill_files():
    """Yield every SKILL.md under the repo, skipping pruned directories."""
    stack = [ROOT]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir():
                if e.name not in _PRUNE:
                    stack.append(e)
            elif e.name == "SKILL.md":
                yield e


def build_manifest():
    """Discover skills and return the manifest dict."""
    skills = []
    for f in _iter_skill_files():
        rel = f.relative_to(ROOT)
        try:
            fm = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            fm = {}
        desc = " ".join((fm.get("description") or "").split())
        if len(desc) > 100:
            desc = desc[:97] + "..."
        skills.append({
            "name": fm.get("name") or f.parent.name,
            "description": desc,
            "tier": _tier(rel),
            "path": str(rel),
        })
    skills.sort(key=lambda s: (s["tier"], s["name"]))
    by_tier = {}
    for s in skills:
        by_tier[s["tier"]] = by_tier.get(s["tier"], 0) + 1
    return {"total": len(skills), "by_tier": by_tier, "skills": skills}


def uninitialized_submodules():
    """Return repos/* submodule paths that are registered but not yet fetched."""
    gm = ROOT / ".gitmodules"
    if not gm.exists():
        return []
    paths = []
    for ln in gm.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if ln.startswith("path"):
            _, _, p = ln.partition("=")
            paths.append(p.strip())
    stale = []
    for p in paths:
        d = ROOT / p
        # Present in .gitmodules but empty working tree => `make init` not run.
        if not d.exists() or not any(d.iterdir()):
            stale.append(p)
    return stale


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in "'\\"" and s[-1] == s[0]:
        return s[1:-1]
    return s


def _parse_scalar_list(val):
    """Parse an inline flow list ``[a, b]``; return None if a block follows."""
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        return [_unquote(x) for x in inner.split(",") if x.strip()] if inner else []
    return None


def load_persona_policy():
    """Read the ``personas:`` block of skills.yaml (stdlib YAML subset reader).

    Handles both inline flow lists and block ``- item`` lists. Returns
    ``{persona: {"allow": [...], "deny": [...]}}`` or ``{}`` when no policy is
    defined (pre-governance repos — everything is then permitted).
    """
    if not CONFIG.exists():
        return {}
    try:
        lines = CONFIG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("personas:") and not ln[:1].isspace():
            start = i + 1
            break
    if start is None:
        return {}
    policy, persona, curkey = {}, None, None
    for ln in lines[start:]:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if not ln[:1].isspace():
            break  # dedent to another top-level key
        stripped = ln.strip()
        if stripped.startswith("- ") and persona and curkey:
            policy[persona][curkey].append(_unquote(stripped[2:]))
            continue
        indent = len(ln) - len(ln.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            persona = stripped[:-1].strip()
            policy[persona] = {"allow": [], "deny": []}
            curkey = None
        elif persona and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            if key in ("allow", "deny"):
                items = _parse_scalar_list(val)
                if items is None:
                    curkey = key  # a block list follows on the next lines
                    policy[persona][key] = []
                else:
                    policy[persona][key], curkey = items, None
    return policy


def policy_for(policy, persona):
    """Resolve the effective allow/deny rule for a persona (None => no policy)."""
    if not policy:
        return None
    rule = policy.get(persona) or policy.get("default") or _BUILTIN_DEFAULT
    return {"allow": list(rule.get("allow", [])), "deny": list(rule.get("deny", []))}


def _match(token, skill, persona):
    """True if a policy token matches a skill for the given persona."""
    tier, name = skill["tier"], skill["name"]
    if token == "*":
        return True
    if token == "persona:self":
        return tier == "persona" and name == persona
    if token.startswith("persona:"):
        return tier == "persona" and name == token[len("persona:"):]
    if token == "persona":
        return tier == "persona"
    if token == tier:
        return True
    if token == "linked" and tier.startswith("linked:"):
        return True
    if token.endswith(":*") and tier.startswith(token[:-1]):
        return True
    return fnmatch.fnmatch(name, token)


def evaluate_persona(m, persona, policy):
    """Annotate each skill with permitted / denied / out-of-policy for a persona.

    deny is split: a specific (non-'*') deny always wins; a bare '*' deny only
    sets the baseline, so an allow-list still grants matching skills.
    """
    rule = policy_for(policy, persona)
    rows = []
    for s in m["skills"]:
        if rule is None:
            status = "permitted"
        else:
            allow = any(_match(t, s, persona) for t in rule["allow"])
            spec_deny = any(t != "*" and _match(t, s, persona) for t in rule["deny"])
            status = "denied" if spec_deny else ("permitted" if allow else "out-of-policy")
        rows.append(dict(s, status=status))
    return rows, rule


def print_persona(m, persona, check=False):
    """Print the per-persona governance view; return the count of denied skills."""
    rows, rule = evaluate_persona(m, persona, load_persona_policy())
    print(f"Skills governance — persona '{persona}'")
    print("=" * 44)
    if rule is None:
        print("  (no persona policy in skills.yaml — all skills permitted)")
    order = ["permitted", "out-of-policy", "denied"]
    icon = {"permitted": "✓", "out-of-policy": "·", "denied": "✗"}
    counts = {}
    for st in order:
        names = [r["name"] for r in rows if r["status"] == st]
        counts[st] = len(names)
        if names:
            shown = ", ".join(names[:6]) + (" ..." if len(names) > 6 else "")
            print(f"  {icon[st]} {st:<14} ({len(names):>2})  {shown}")
    print("-" * 44)
    if rule is not None:
        print(f"  allow: {rule['allow']}")
        print(f"  deny:  {rule['deny']}")
    denied = counts.get("denied", 0)
    if check and denied:
        print("")
        print(f"  ✗ Governance violation: {denied} loaded skill(s) DENIED for "
              f"persona '{persona}'.")
    return denied


def print_summary(m, check=False):
    """Print a grouped, counted profile of loaded skills."""
    print("Skills profile — loaded into working repo")
    print("=" * 44)
    if not m["skills"]:
        print("  (no skills found yet — run `make init` to fetch submodules)")
    else:
        for tier in sorted(m["by_tier"]):
            names = [s["name"] for s in m["skills"] if s["tier"] == tier]
            shown = ", ".join(names[:6]) + (" ..." if len(names) > 6 else "")
            print(f"  {tier:<20} ({m['by_tier'][tier]:>2})  {shown}")
        print("-" * 44)
        print(f"  Total: {m['total']} skills across {len(m['by_tier'])} source(s)")
    if check:
        stale = uninitialized_submodules()
        if stale:
            print("")
            print("  ! Uninitialized submodules (skills not loaded):")
            for p in stale:
                print(f"      - {p}   (run `make init`)")
    if MANIFEST.exists():
        print(f"\\n  Manifest: {MANIFEST.relative_to(ROOT)}")


def _persona_arg(argv):
    """Extract --persona <id> / --persona=<id> from argv."""
    for i, a in enumerate(argv):
        if a == "--persona" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--persona="):
            return a.split("=", 1)[1]
    return None


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    persona = _persona_arg(argv)
    m = build_manifest()
    if "--write" in flags:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(m, indent=2) + "\\n", encoding="utf-8")
    if "--json" in flags:
        print(json.dumps(m, indent=2))
        return 0
    rc = 0
    # Default to a summary unless the caller only asked to write.
    if "--write" not in flags or "--summary" in flags or "--check" in flags:
        print_summary(m, check="--check" in flags)
        if persona:
            print("")
            denied = print_persona(m, persona, check="--check" in flags)
            # In validate mode a persona with DENIED loaded skills fails the gate.
            if "--check" in flags and denied:
                rc = 3
    elif "--write" in flags:
        print(f"Loaded {m['total']} skills -> {MANIFEST.relative_to(ROOT)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
''',
        encoding="utf-8",
    )
    try:
        script.chmod(0o755)
    except OSError:
        pass
    logger.debug(f"Wrote skills profiler to {scripts_dir}")


def _write_docs(meta_repo_path: Path, domain: str, product: str, description: str) -> None:
    """Write documentation files."""
    docs_dir = meta_repo_path / "docs"

    # README.md
    readme_file = docs_dir / "README.md"
    readme_file.write_text(
        f"""# {domain.upper()} Domain Meta-Repo

**Product**: {product}
**Domain**: {domain}

{description or "Domain-specific repository for managing code, skills, and governance."}

## Quick Start

```bash
# Configure hooks, initialize submodules, and load all skills
make init

# Show which skills are loaded into the working repo
make skills

# Update all submodules
make update

# Validate repo state + print the skills profile
make validate
```

## Structure

- `.platform/config/` — Domain configuration (domain.yaml, repos.yaml, governance.yaml, skills.yaml)
- `.agents/` — Domain-specific agents and skills
- `repos/` — Git submodules for linked domain repositories
- `docs/` — Documentation
- `plans/` — Local design specs (gitignored)

## Linked Repositories

See `.platform/config/repos.yaml` for the list of linked domain repositories.

## Governance

See `.platform/config/governance.yaml` for domain governance rules.

## Skills

See `.platform/config/skills.yaml` for domain skills configuration.

## Getting Help

- Read `ONBOARDING.md` for repo onboarding guide
- Read `GOVERNANCE.md` for branch/workflow rules
- Read `ARCHITECTURE.md` for domain architecture
""",
        encoding="utf-8",
    )

    # ONBOARDING.md
    onboarding_file = docs_dir / "ONBOARDING.md"
    onboarding_file.write_text(
        f"""# {domain.upper()} Repository Onboarding Guide

This guide explains how to onboard a new repository into the {domain} domain.

## Prerequisites

- Git installed
- `keel` CLI installed
- Access to domain repositories

## Onboarding Steps

### 1. Clone the Repository

```bash
git clone <repo-url> <local-path>
cd <local-path>
```

### 2. Run Code Onboard

```bash
keel code onboard --path . --domain {domain} --link-meta-repo --use-domain-skills
```

This will:
- Detect and link the domain meta-repo
- Load domain-specific configurations
- Install domain-validated skills
- Generate project-context skill
- Create onboard manifest

### 3. Verify Installation

```bash
# Check .skills directory
ls -la .skills/

# Review onboard manifest
cat .onboard-manifest.json
```

## Domain-Specific Configuration

The domain meta-repo provides:
- **Domain settings** — `.platform/config/domain.yaml`
- **Linked repos** — `.platform/config/repos.yaml`
- **Governance rules** — `.platform/config/governance.yaml`
- **Skills config** — `.platform/config/skills.yaml`

## Support

For issues or questions, contact the domain owner or team.
""",
        encoding="utf-8",
    )

    # GOVERNANCE.md
    governance_file = docs_dir / "GOVERNANCE.md"
    governance_file.write_text(
        f"""# {domain.upper()} Governance Rules

This document outlines the governance rules for the {domain} domain.

## Branch Naming Convention

Branches must follow the pattern:
```
<type>/<JIRA-ID>-<kebab-case-description>
```

Examples:
- `feat/CWOW-123-add-water-quality-check`
- `fix/CWOW-456-resolve-facility-sync-bug`
- `docs/CWOW-789-update-api-docs`

## Pre-Push Hooks

All repositories must have pre-push hooks installed to enforce:
- Branch naming convention
- Commit message format
- Code quality checks

## CI/CD Gates

All code must pass:
- SAST (Static Application Security Testing)
- SCA (Software Composition Analysis)
- Unit tests (minimum 80% coverage)
- Code review (minimum 1 reviewer)

## Code Review

All pull requests require:
- Minimum 1 reviewer approval
- All conversations resolved
- CI/CD gates passing

## Submodule Management

- Submodules are pinned to specific commits
- Updates require explicit commits to parent repo
- Use `make update` to update all submodules

## Questions?

Contact the domain owner for clarification on governance rules.
""",
        encoding="utf-8",
    )

    # ARCHITECTURE.md
    architecture_file = docs_dir / "ARCHITECTURE.md"
    architecture_file.write_text(
        f"""# {domain.upper()} Domain Architecture

This document describes the architecture of the {domain} domain.

## Overview

The {domain} domain consists of multiple repositories organized as git submodules
in this meta-repo. Each repository serves a specific purpose.

## Repositories

See `.platform/config/repos.yaml` for the list of repositories and their descriptions.

## Skills

Domain-specific skills are managed in the domain-context-repo (linked as a submodule).

Skills are organized by:
- **Validated skills** — Tested and approved for domain use
- **Customized skills** — Forked from superpowers and tailored for domain
- **Injected skills** — Baseline skills from superpowers

## Configuration

Domain configuration is centralized in `.platform/config/`:
- `domain.yaml` — Domain metadata
- `repos.yaml` — Linked repositories
- `governance.yaml` — Governance rules
- `skills.yaml` — Skills configuration

## Development Workflow

1. Create a feature branch following naming convention
2. Make changes in your repository
3. Commit and push to feature branch
4. Create pull request
5. Get review approval
6. Merge to main

See `GOVERNANCE.md` for detailed governance rules.

## Deployment

Deployment procedures are repository-specific. See individual repository documentation.

## Support

For architecture questions, contact the domain owner.
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote documentation files to {docs_dir}")


def _write_makefile(meta_repo_path: Path) -> None:
    """Write Makefile with automation targets."""
    makefile_path = meta_repo_path / "Makefile"
    makefile_path.write_text(
        """.PHONY: init update update-one validate setup-hooks load-skills skills ide-install help

# Optional persona scope: `make skills PERSONA=qa` / `make validate PERSONA=qa`
# report and gate the skills profile against that persona's policy in skills.yaml.
PERSONA_FLAG := $(if $(PERSONA),--persona $(PERSONA))

# Which code-assist tool to install skills for. Reads the same env var the
# `keel` CLI does, so `KEEL_CODE_ASSIST_TOOL=cursor make init` just works.
# Override on the command line too: `make ide-install CODE_ASSIST_TOOL=windsurf`.
CODE_ASSIST_TOOL ?= $(if $(KEEL_CODE_ASSIST_TOOL),$(KEEL_CODE_ASSIST_TOOL),generic)

init: setup-hooks
	@echo "Initializing domain meta-repo (shallow, parallel)..."
	git -c protocol.file.allow=always submodule update --init --recursive --depth 1 --jobs 8
	@echo "✓ Submodules initialized"
	@$(MAKE) --no-print-directory load-skills
	@if [ "$(SKIP_IDE_INSTALL)" = "1" ]; then \\
		echo "  (SKIP_IDE_INSTALL=1 — skipping IDE placement; run 'make ide-install' later)"; \\
	else \\
		$(MAKE) --no-print-directory ide-install; \\
	fi

update:
	@echo "Updating all submodules..."
	git submodule update --remote --merge
	@echo "✓ Submodules updated"

update-one:
	@if [ -z "$(REPO)" ]; then \\
		echo "Usage: make update-one REPO=repos/<name>"; \\
		exit 1; \\
	fi
	@echo "Updating submodule $(REPO)..."
	git submodule update --remote --merge "$(REPO)"
	@echo "✓ Submodule $(REPO) updated"

setup-hooks:
	@if [ -d ".githooks" ]; then \\
		git config core.hooksPath .githooks; \\
		chmod +x .githooks/* 2>/dev/null || true; \\
		echo "✓ Git hooks configured (core.hooksPath=.githooks)"; \\
	fi

load-skills:
	@echo "Loading skills across meta-repo (.agents + submodules)..."
	@python3 .platform/scripts/profile_skills.py --write --summary
	@echo "✓ Skills loaded → .platform/skills-manifest.json"

# Place skills where the code-assist tool actually reads them (.cursorrules,
# .devin/skills, .skills, ~/.codeium/windsurf/skills/<domain>__<name> for
# Windsurf). Governance policy (skills.yaml + admin skill_enforcement) is
# applied at this seam: under `enforce`, denied / out-of-policy skills are
# filtered out before they land in an IDE-visible directory.
#
# No-op if the `keel` CLI isn't installed — the meta-repo Makefile itself
# stays stdlib-only, and this step just prints a hint.
ide-install:
	@if command -v keel >/dev/null 2>&1; then \\
		DOMAIN=$$(grep -E '^domain:' .platform/config/domain.yaml 2>/dev/null | awk '{print $$2}' | tr -d '"' | tr -d "'"); \\
		echo "Placing skills for $(CODE_ASSIST_TOOL) via 'keel code onboard'..."; \\
		if [ -n "$$DOMAIN" ]; then \\
			keel code onboard --path . --domain "$$DOMAIN" --use-domain-skills --code-assist-tool $(CODE_ASSIST_TOOL) \\
				|| echo "  (keel code onboard reported issues — see above)"; \\
		else \\
			keel code onboard --path . --code-assist-tool $(CODE_ASSIST_TOOL) \\
				|| echo "  (keel code onboard reported issues — see above)"; \\
		fi; \\
	else \\
		echo ""; \\
		echo "  ! keel CLI not found on PATH — skills indexed, but NOT placed for the IDE."; \\
		echo "    Install Keel and run 'make ide-install' to complete IDE setup."; \\
		echo "    Override tool: make ide-install CODE_ASSIST_TOOL=cursor  (or windsurf/devin)"; \\
		echo "    Docs: docs/GOVERNANCE_LAYERS.md"; \\
	fi

skills:
	@python3 .platform/scripts/profile_skills.py --summary $(PERSONA_FLAG)

validate:
	@echo "Validating repo state..."
	@if [ -d ".platform/config" ]; then \\
		echo "✓ .platform/config exists"; \\
	else \\
		echo "✗ .platform/config missing"; \\
		exit 1; \\
	fi
	@if [ -d "repos" ]; then \\
		echo "✓ repos directory exists"; \\
	else \\
		echo "✗ repos directory missing"; \\
		exit 1; \\
	fi
	@echo ""
	@if command -v python3 >/dev/null 2>&1; then \\
		python3 .platform/scripts/profile_skills.py --check $(PERSONA_FLAG); \\
	else \\
		echo "  (skills profiler unavailable — needs python3)"; \\
	fi
	@echo ""
	@echo "✓ Validation passed"

help:
	@echo "Domain Meta-Repo Targets:"
	@echo "  make init        - Configure hooks, init submodules, load skills, place them for the IDE"
	@echo "                     (skip IDE placement with SKIP_IDE_INSTALL=1)"
	@echo "  make update      - Update all submodules"
	@echo "  make update-one  - Update one submodule (REPO=repos/<name>)"
	@echo "  make setup-hooks - Configure git hooks path"
	@echo "  make load-skills - Index all skills into .platform/skills-manifest.json"
	@echo "  make ide-install - Place skills where your code-assist tool reads them"
	@echo "                     (CODE_ASSIST_TOOL=devin|cursor|generic|windsurf; needs keel CLI)"
	@echo "  make skills      - Print the loaded-skills profile (PERSONA=<id> to scope)"
	@echo "  make validate    - Validate repo state + skills profile (PERSONA=<id> gates)"
	@echo "  make help        - Show this help message"
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote Makefile to {meta_repo_path}")


def _write_platform_readme(platform_dir: Path, domain: str) -> None:
    """Write .platform/README.md documenting config structure."""
    readme = platform_dir / "README.md"
    readme.write_text(
        f"""# .platform — Centralized Configuration

This directory holds all platform-wide configuration and shared utilities for
the **{domain}** domain meta-repo.

## Structure

- `config/` — YAML configuration files
  - `domain.yaml` — Domain metadata (product, owner, tags)
  - `repos.yaml` — Linked repositories (slug, clone_url, languages)
  - `governance.yaml` — Branch naming, review, and CI/CD rules
  - `skills.yaml` — Domain skill validation and priority rules
- `common/` — Shared Python utilities
  - `config_loader.py` — Helpers to load YAML configs

## Usage

```python
from pathlib import Path
from common.config_loader import load_config

config_dir = Path(__file__).parent / "config"
domain_cfg = load_config(config_dir, "domain.yaml")
repos_cfg = load_config(config_dir, "repos.yaml")
```

These configs are consumed by the `keel code onboard --use-meta-config` workflow.
""",
        encoding="utf-8",
    )
    logger.debug(f"Wrote .platform/README.md to {platform_dir}")


def _write_root_readme(
    meta_repo_path: Path, domain: str, product: str, description: str
) -> None:
    """Write root README.md per meta-repo standards."""
    readme = meta_repo_path / "README.md"
    readme.write_text(
        f"""# {domain} Domain Meta-Repo

**Product**: {product}

{description or "Meta-repository orchestrating code, skills, and governance for this domain."}

## Quickstart

```bash
make init        # Configure hooks, init submodules, load skills
make skills      # Show which skills are loaded into the working repo
make validate    # Validate repo state + skills profile
make update      # Update all submodules
```

## Layout

| Path | Purpose |
|------|---------|
| `.platform/` | Centralized configs and shared utilities |
| `.agents/` | Agent and skill definitions (modular, discoverable) |
| `repos/` | Submodules (domain-context + linked repos) |
| `plans/` | Local-only design specs (gitignored) |
| `docs/` | Onboarding, governance, architecture guides |
| `.githooks/` | Git hooks (pre-push branch-naming enforcement) |
| `Makefile` | Automation targets |

## Documentation

- [AGENTS.md](AGENTS.md) — Agent/skill architecture and submodule workflow
- [docs/ONBOARDING.md](docs/ONBOARDING.md) — Repo onboarding guide
- [docs/GOVERNANCE.md](docs/GOVERNANCE.md) — Branch/workflow rules
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Domain architecture
- [.platform/README.md](.platform/README.md) — Config structure
""",
        encoding="utf-8",
    )
    logger.debug(f"Wrote root README.md to {meta_repo_path}")


def _write_agents_md(meta_repo_path: Path, domain: str) -> None:
    """Write AGENTS.md explaining agent/skill architecture and governance."""
    agents_md = meta_repo_path / "AGENTS.md"
    agents_md.write_text(
        f"""# Agents & Skills — {domain}

This document explains how agents and skills are organized in this meta-repo and
how they integrate with the submodule workflow and governance.

## Agent & Skill Discovery

- **Agents** live in `.agents/agents/` — each agent is a self-contained project.
- **Skills** live in `.agents/skills/` — each skill has a `SKILL.md` plus optional
  references and scripts.
- Domain-validated skills are sourced from the `repos/domain-context` submodule
  and prioritized during `keel code onboard --use-domain-skills`.

`make init` loads every skill it can find (across `.agents/skills` and the
`repos/*` submodules) into `.platform/skills-manifest.json`. Run `make skills`
to print the profile of what is loaded, or `make validate` to see it alongside
the repo-state checks. The manifest is regenerated on every load — treat it as
a derived index, not a hand-edited source.

## Persona-Scoped Skill Governance

`.platform/config/skills.yaml` carries a `personas:` policy that governs **which
skills each persona may load/use** (allow/deny over tiers, `persona:<id>`, and
skill-name globs; a specific deny always wins). Scope the profile to a persona:

```bash
make skills PERSONA=qa       # what a QA user is granted vs out-of-policy
make validate PERSONA=dev    # gate: fails if a loaded skill is explicitly denied
```

A signed-in user's SSO profile resolves to a persona (role default, overridable
via `KEEL_PERSONA_MAP='group:persona'` or a per-user assignment), so the same
policy that reports here is what `keel code onboard` enforces for that user.

## Skill Priority Order

Defined in `.platform/config/skills.yaml`:

1. **validated** — Tested and approved for this domain (highest)
2. **customized** — Forked from superpowers and tailored
3. **injected** — Superpowers baseline (lowest)

## Submodule Workflow

1. Make changes inside the submodule first, commit there.
2. Update the parent meta-repo to point at the new submodule commit.
3. Pin submodules to specific commits (never floating branches in production).

```bash
make update-one REPO=repos/<name>   # Update a single submodule
make update                         # Update all submodules
```

## Governance

- Branch naming and review rules are enforced via `.githooks/pre-push` and CI.
- See `docs/GOVERNANCE.md` for the full ruleset.
- Never commit secrets or `.env` files.
""",
        encoding="utf-8",
    )
    logger.debug(f"Wrote AGENTS.md to {meta_repo_path}")


def _write_pre_push_hook(githooks_dir: Path) -> None:
    """Write a pre-push hook that enforces branch naming conventions."""
    hook = githooks_dir / "pre-push"
    hook.write_text(
        """#!/usr/bin/env bash
# Pre-push hook: enforce branch naming convention.
# Pattern: <type>/<JIRA-ID>-<kebab-case-description>
# Types: feat, fix, docs, style, refactor, test, chore

set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"

# Allow main/master/develop
if [[ "$branch" =~ ^(main|master|develop)$ ]]; then
  exit 0
fi

pattern='^(feat|fix|docs|style|refactor|test|chore)/[A-Z]+-[0-9]+-.+$'
if [[ ! "$branch" =~ $pattern ]]; then
  echo "✗ Branch name '$branch' does not match required pattern:" >&2
  echo "  <type>/<JIRA-ID>-<kebab-case-description>" >&2
  echo "  e.g. feat/CWOW-123-add-water-quality-check" >&2
  exit 1
fi

exit 0
""",
        encoding="utf-8",
    )
    try:
        hook.chmod(0o755)
    except OSError:
        pass
    logger.debug(f"Wrote pre-push hook to {githooks_dir}")


def _write_gitignore(meta_repo_path: Path) -> None:
    """Write .gitignore file."""
    gitignore_path = meta_repo_path / ".gitignore"
    gitignore_path.write_text(
        """# Local development
plans/
*.local
# Derived skills index (regenerated by `make init` / `make load-skills`)
.platform/skills-manifest.json
.DS_Store
.vscode/
.idea/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build artifacts
dist/
build/
*.egg-info/
""",
        encoding="utf-8",
    )

    logger.debug(f"Wrote .gitignore to {meta_repo_path}")


def _init_git_repo(
    meta_repo_path: Path,
    context_repo_url: Optional[str],
    repos: list[dict],
    product_meta_url: Optional[str] = None,
    *,
    clone_repos: bool = False,
) -> None:
    """Initialize git repository with submodules.

    By default, submodules are *registered* (``.gitmodules`` + pinned gitlink)
    without cloning — the working trees are fetched lazily via ``make init``
    (``git submodule update --init``). This keeps scaffolding fast even for
    domains with many linked repos. Pinned commit SHAs are resolved up-front in
    parallel with clone-free ``git ls-remote`` calls.

    Args:
        meta_repo_path: Path to meta-repo
        context_repo_url: Git URL of domain-context-repo (optional)
        repos: List of linked repo configs
        product_meta_url: Git URL/path of the product meta-repo (outer-loop
            shared tier) to reference as a submodule (optional)
        clone_repos: If True, also clone the submodule working trees now
            (shallow + parallel). If False (default), defer to ``make init``.

    Raises:
        RuntimeError: If git operations fail
    """
    try:
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )
        logger.debug(f"Initialized git repo at {meta_repo_path}")

        # Activate git hooks (branch-naming enforcement)
        if (meta_repo_path / ".githooks").exists():
            subprocess.run(
                ["git", "config", "core.hooksPath", ".githooks"],
                cwd=str(meta_repo_path),
                check=True,
                capture_output=True,
            )
            logger.debug("Configured core.hooksPath=.githooks")

        # Stage the scaffold files FIRST. This must happen before submodule
        # gitlinks are staged: `git add .` stages the deletion of any tracked
        # path missing from the working tree, which would clobber the gitlinks
        # for the (intentionally un-cloned) submodules registered below.
        subprocess.run(
            ["git", "add", "."],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )

        # Build the full submodule spec list: (path, url, branch).
        specs: list[tuple[str, str, Optional[str]]] = []
        if context_repo_url:
            specs.append(("repos/domain-context", context_repo_url, None))
        if product_meta_url:
            specs.append(("repos/product-meta", product_meta_url, None))
        for repo in repos:
            repo_slug = repo.get("slug")
            clone_url = repo.get("clone_url")
            if repo_slug and clone_url:
                specs.append((f"repos/{repo_slug}", clone_url, repo.get("branch")))

        # Resolve pinned commit SHAs in parallel WITHOUT cloning. This replaces
        # N sequential full clones with N cheap, concurrent `ls-remote` calls.
        sha_map = resolve_remote_shas([(p, u, b) for p, u, b in specs])

        for path, url, branch in specs:
            resolved = sha_map.get(path)
            sha = resolved[0] if resolved else None
            eff_branch = (resolved[1] if resolved else None) or branch
            register_submodule(meta_repo_path, url, path, sha=sha, branch=eff_branch)
            if not sha:
                logger.warning(
                    f"Could not resolve a commit for {url}; recorded pointer only "
                    f"(fetch later with `git submodule update --init --remote {path}`)."
                )

        # Stage only .gitmodules (the gitlinks were already staged via
        # update-index inside register_submodule). Avoid `git add .` here.
        if specs:
            subprocess.run(
                ["git", "add", ".gitmodules"],
                cwd=str(meta_repo_path),
                check=True,
                capture_output=True,
            )

        # Initial commit
        subprocess.run(
            ["git", "commit", "-m", "Initial commit: domain meta-repo scaffold"],
            cwd=str(meta_repo_path),
            check=True,
            capture_output=True,
        )
        logger.debug("Created initial git commit")

        # Optionally fetch the working trees now (shallow + parallel). This is
        # the same operation as `make init`, just run inline when requested.
        if clone_repos and specs:
            logger.debug("Cloning submodule working trees (shallow, parallel)...")
            subprocess.run(
                [
                    "git", "-c", "protocol.file.allow=always",
                    "submodule", "update", "--init", "--recursive",
                    "--depth", "1", "--jobs", "8",
                ],
                cwd=str(meta_repo_path),
                check=False,  # best-effort; pointers remain valid if a fetch fails
                capture_output=True,
            )

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        raise RuntimeError(f"Git operation failed: {stderr}")
