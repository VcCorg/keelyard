"""Agentic MCP Server — Integration Validation Script.

Run:  python tests/test_validate_integration.py
  or: pytest tests/test_validate_integration.py -v

Validates the full stack:
  1. Python imports & config
  2. DB connection to tracker.db
  3. Tool function correctness (product, domain, repo, activity, skills)
  4. MCP server tool registration
  5. Docker build (optional, skipped if Docker not available)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m⊘\033[0m"

results: list[tuple[str, str, str]] = []


def check(name: str, fn):
    """Run a check function and record result."""
    try:
        msg = fn()
        results.append((PASS, name, msg or "OK"))
    except Exception as e:
        results.append((FAIL, name, str(e)))


def skip(name: str, reason: str):
    results.append((SKIP, name, reason))


# ── Phase 1: Prerequisites ───────────────────────────────────────────────────


def check_python_version():
    v = sys.version_info
    assert v >= (3, 10), f"Python 3.10+ required, got {v.major}.{v.minor}"
    return f"Python {v.major}.{v.minor}.{v.micro}"


def check_pip_package():
    import importlib.metadata
    ver = importlib.metadata.version("agentic-mcp")
    return f"agentic-mcp {ver}"


def check_docker():
    result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, "Docker not found"
    return result.stdout.strip()


# ── Phase 2: Imports & Config ────────────────────────────────────────────────


def check_imports():
    from agentic_mcp.config import AgenticConfig
    from agentic_mcp.db import TrackerDB
    from agentic_mcp.server import mcp
    return "config, db, server modules imported"


def check_config():
    from agentic_mcp.config import AgenticConfig
    cfg = AgenticConfig()
    assert cfg.tracker_db, "tracker_db path is empty"
    return f"DB={cfg.tracker_db}, registry={cfg.skills_registry}"


def check_config_db_exists():
    from agentic_mcp.config import AgenticConfig
    cfg = AgenticConfig()
    assert cfg.tracker_db.exists(), f"tracker.db not found at {cfg.tracker_db}"
    return f"{cfg.tracker_db} ({cfg.tracker_db.stat().st_size} bytes)"


# ── Phase 3: DB Operations ──────────────────────────────────────────────────


def _get_db():
    from agentic_mcp.config import AgenticConfig
    from agentic_mcp.db import TrackerDB
    return TrackerDB(AgenticConfig().tracker_db)


def check_db_product_list():
    products = _get_db().product_list()
    assert isinstance(products, list), "product_list should return a list"
    return f"{len(products)} products"


def check_db_domain_list():
    domains = _get_db().domain_list()
    assert isinstance(domains, list), "domain_list should return a list"
    return f"{len(domains)} domains"


def check_db_repo_list():
    repos = _get_db().repo_list()
    assert isinstance(repos, list), "repo_list should return a list"
    return f"{len(repos)} repos"


def check_db_activity_summary():
    summary = _get_db().activity_summary()
    assert "repos" in summary, "summary missing 'repos' key"
    assert "products" in summary, "summary missing 'products' key"
    assert "domains" in summary, "summary missing 'domains' key"
    return f"repos={summary['repos']}, products={summary['products']}, domains={summary['domains']}, activities={summary['total_activities']}"


def check_db_activity_recent():
    recent = _get_db().activity_recent(5)
    assert isinstance(recent, list), "activity_recent should return a list"
    return f"{len(recent)} recent activities"


# ── Phase 4: Tool Functions (JSON round-trip) ────────────────────────────────


def check_tool_product_list():
    from agentic_mcp.server import product_list
    result = json.loads(product_list())
    assert isinstance(result, list), "product_list tool should return JSON array"
    return f"{len(result)} products"


def check_tool_domain_list():
    from agentic_mcp.server import domain_list
    result = json.loads(domain_list())
    assert isinstance(result, list), "domain_list tool should return JSON array"
    return f"{len(result)} domains"


def check_tool_repo_list():
    from agentic_mcp.server import repo_list
    result = json.loads(repo_list())
    assert isinstance(result, list), "repo_list tool should return JSON array"
    return f"{len(result)} repos"


def check_tool_activity_summary():
    from agentic_mcp.server import activity_summary
    result = json.loads(activity_summary())
    assert "repos" in result, "activity_summary missing 'repos'"
    return f"repos={result['repos']}, domains={result['domains']}"


def check_tool_registry_list():
    from agentic_mcp.server import registry_list
    result = json.loads(registry_list())
    if isinstance(result, dict) and "error" in result:
        return f"registry not found (expected in CI): {result['error']}"
    assert isinstance(result, list), "registry_list should return JSON array"
    return f"{len(result)} skills in registry"


def check_tool_skill_available():
    from agentic_mcp.server import skill_available
    result = json.loads(skill_available("docker"))
    assert "exists" in result, "skill_available missing 'exists' field"
    return f"docker skill exists={result['exists']}"


def check_tool_domain_get():
    from agentic_mcp.server import domain_list, domain_get
    domains = json.loads(domain_list())
    if not domains:
        return "no domains to test"
    slug = domains[0]["name"]
    result = json.loads(domain_get(slug))
    assert "repos" in result, "domain_get should include 'repos'"
    assert "docs" in result, "domain_get should include 'docs'"
    return f"domain '{slug}': {len(result['repos'])} repos, {len(result['docs'])} docs"


def check_tool_product_get():
    from agentic_mcp.server import product_list, product_get
    products = json.loads(product_list())
    if not products:
        return "no products to test"
    name = products[0]["name"]
    result = json.loads(product_get(name))
    assert "name" in result, "product_get should include 'name'"
    return f"product '{name}' found"


# ── Phase 5: MCP Server Registration ────────────────────────────────────────


def check_mcp_tools_registered():
    from agentic_mcp.server import mcp
    tools = mcp.list_tools()
    expected = {
        "product_create", "product_list", "product_get",
        "domain_create", "domain_list", "domain_get",
        "domain_link_repo", "domain_unlink_repo", "domain_list_repos",
        "domain_add_doc", "domain_list_docs",
        "repo_register", "repo_list", "repo_get",
        "activity_log", "activity_recent", "activity_summary",
        "registry_list", "skill_available",
    }
    # FastMCP list_tools is async; check via internal registry instead
    import asyncio
    tool_list = asyncio.run(tools)
    tool_names = {t.name for t in tool_list}
    missing = expected - tool_names
    assert not missing, f"Missing tools: {missing}"
    return f"{len(tool_names)} tools registered (expected {len(expected)})"


def check_mcp_no_dva_prefix():
    """Ensure no tool has a 'dva_' prefix."""
    from agentic_mcp.server import mcp
    import asyncio
    tool_list = asyncio.run(mcp.list_tools())
    dva_tools = [t.name for t in tool_list if t.name.startswith("dva_")]
    assert not dva_tools, f"Found dva_ prefixed tools: {dva_tools}"
    return "no dva_ prefixed tools"


# ── Phase 6: Docker Build ───────────────────────────────────────────────────


def check_docker_build():
    project_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["docker", "build", "-t", "agentic-mcp-test", "."],
        cwd=str(project_dir),
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"Docker build failed:\n{result.stderr[-500:]}"
    return "docker build succeeded"


# ── Phase 7: Naming Convention ───────────────────────────────────────────────


def check_no_dva_in_server_code():
    """Verify no 'dva' references in Python server code."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "agentic_mcp"
    violations = []
    for py_file in src_dir.glob("*.py"):
        content = py_file.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            lower = line.lower()
            if "dva" in lower and not line.strip().startswith("#"):
                violations.append(f"{py_file.name}:{i}: {line.strip()}")
    assert not violations, f"Found 'dva' in code:\n" + "\n".join(violations)
    return f"scanned {len(list(src_dir.glob('*.py')))} files, clean"


def check_registry_server_name():
    """Verify registry.json uses 'agentic' not 'dva' for MCP server."""
    from agentic_mcp.config import AgenticConfig
    cfg = AgenticConfig()
    if not cfg.skills_registry.exists():
        return "registry.json not found (expected in CI)"
    with open(cfg.skills_registry) as f:
        registry = json.load(f)
    for skill in registry.get("skills", []):
        mcp_cfg = skill.get("mcp", {})
        if mcp_cfg.get("server") == "dva":
            raise AssertionError(f"Skill '{skill['name']}' still uses server='dva'")
    agentic_skills = [s["name"] for s in registry["skills"] if s.get("mcp", {}).get("server") == "agentic"]
    return f"{len(agentic_skills)} skills use server='agentic'"


# ── Runner ───────────────────────────────────────────────────────────────────


def main():
    print("\n" + "=" * 70)
    print("  Agentic Platform MCP — Integration Validation")
    print("=" * 70)

    # Phase 1
    print("\n── Phase 1: Prerequisites ──")
    check("Python >= 3.10", check_python_version)
    check("agentic-mcp installed", check_pip_package)

    docker_ok = False
    try:
        check_docker()
        docker_ok = True
    except Exception:
        pass
    if docker_ok:
        check("Docker available", check_docker)
    else:
        skip("Docker available", "Docker not found — Docker tests will be skipped")

    # Phase 2
    print("\n── Phase 2: Imports & Config ──")
    check("Import modules", check_imports)
    check("Config loads", check_config)
    check("tracker.db exists", check_config_db_exists)

    # Phase 3
    print("\n── Phase 3: DB Operations ──")
    check("DB product_list()", check_db_product_list)
    check("DB domain_list()", check_db_domain_list)
    check("DB repo_list()", check_db_repo_list)
    check("DB activity_summary()", check_db_activity_summary)
    check("DB activity_recent()", check_db_activity_recent)

    # Phase 4
    print("\n── Phase 4: Tool Functions ──")
    check("Tool: product_list", check_tool_product_list)
    check("Tool: product_get", check_tool_product_get)
    check("Tool: domain_list", check_tool_domain_list)
    check("Tool: domain_get", check_tool_domain_get)
    check("Tool: repo_list", check_tool_repo_list)
    check("Tool: activity_summary", check_tool_activity_summary)
    check("Tool: registry_list", check_tool_registry_list)
    check("Tool: skill_available", check_tool_skill_available)

    # Phase 5
    print("\n── Phase 5: MCP Registration ──")
    check("All 19 tools registered", check_mcp_tools_registered)
    check("No dva_ prefix on tools", check_mcp_no_dva_prefix)

    # Phase 6
    if docker_ok:
        print("\n── Phase 6: Docker Build ──")
        check("Docker build", check_docker_build)
    else:
        print("\n── Phase 6: Docker Build (SKIPPED) ──")
        skip("Docker build", "Docker not available")

    # Phase 7
    print("\n── Phase 7: Naming Convention ──")
    check("No 'dva' in server code", check_no_dva_in_server_code)
    check("Registry uses server='agentic'", check_registry_server_name)

    # Summary
    print("\n" + "=" * 70)
    passed = sum(1 for s, _, _ in results if s == PASS)
    failed = sum(1 for s, _, _ in results if s == FAIL)
    skipped = sum(1 for s, _, _ in results if s == SKIP)

    for status, name, msg in results:
        print(f"  {status} {name}: {msg}")

    print(f"\n  Total: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 70)

    if failed:
        print(f"\n  {FAIL} VALIDATION FAILED — {failed} check(s) need attention")
        sys.exit(1)
    else:
        print(f"\n  {PASS} ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
