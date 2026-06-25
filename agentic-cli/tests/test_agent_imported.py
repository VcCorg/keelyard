"""Tests for imported-agent listing/run entrypoint resolution."""
from __future__ import annotations

from pathlib import Path

from agentic_cli.commands import agent as agent_cmd


def _make_pkg_agent(root: Path, with_main: bool = True, script: bool = True):
    """Create a minimal installable agent package layout under root."""
    pkg = root / "src" / "myagent"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    if with_main:
        (pkg / "__main__.py").write_text("print('hi')\n")
    (pkg / "cli.py").write_text("def main():\n    pass\n")
    scripts = '\n[project.scripts]\nmyagent = "myagent.cli:main"\n' if script else ""
    (root / "pyproject.toml").write_text(
        '[project]\nname = "myagent"\nversion = "0.1.0"\n' + scripts
    )


def test_resolve_entrypoint_with_main_and_script(tmp_path: Path):
    _make_pkg_agent(tmp_path)
    ep = agent_cmd._resolve_imported_entrypoint(tmp_path)
    assert ep["src"] == tmp_path / "src"
    assert ep["package"] == "myagent"
    assert ep["module"] == "myagent"
    assert ep["console_scripts"] == {"myagent": "myagent.cli:main"}


def test_resolve_entrypoint_without_main(tmp_path: Path):
    _make_pkg_agent(tmp_path, with_main=False)
    ep = agent_cmd._resolve_imported_entrypoint(tmp_path)
    assert ep["package"] == "myagent"
    assert ep["module"] is None  # no __main__.py -> not runnable via python -m


def test_resolve_entrypoint_no_src_dir(tmp_path: Path):
    pkg = tmp_path / "flatagent"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\nversion="0"\n')
    ep = agent_cmd._resolve_imported_entrypoint(tmp_path)
    assert ep["src"] == tmp_path  # falls back to repo root
    assert ep["module"] == "flatagent"


def test_load_imported_agents(tmp_path: Path, monkeypatch):
    import json
    imported_dir = tmp_path / "imported"
    imported_dir.mkdir()
    (imported_dir / "registry.json").write_text(
        json.dumps({"a": {"name": "a", "local_path": "/x", "installed": False}})
    )
    monkeypatch.setattr(agent_cmd, "_imported_dir", lambda: imported_dir)
    reg = agent_cmd._load_imported_agents()
    assert "a" in reg and reg["a"]["installed"] is False


def test_load_imported_agents_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(agent_cmd, "_imported_dir", lambda: tmp_path / "none")
    assert agent_cmd._load_imported_agents() == {}
