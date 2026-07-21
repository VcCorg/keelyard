"""Tests for the static Scripts check in the trial scorecard."""

from pathlib import Path

from src.services import skill_trial_service as svc

SKILL_MD = "---\nname: demo\ndescription: A demo skill\n---\n\nRun `scripts/run.py`.\n"


def _mk(tmp_path: Path, files: dict[str, str]) -> Path:
    d = tmp_path / "skill"
    d.mkdir()
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


def test_no_scripts_skipped(tmp_path):
    d = _mk(tmp_path, {"SKILL.md": "---\nname: x\ndescription: y\n---\ndoc only\n"})
    c = svc._check_scripts(d)
    assert c.status == "skipped"


def test_valid_python_passes(tmp_path):
    d = _mk(tmp_path, {
        "SKILL.md": SKILL_MD,
        "scripts/run.py": "import os\nprint(os.getcwd())\n",
    })
    c = svc._check_scripts(d)
    assert c.status == "pass" and "1 py" in c.detail


def test_syntax_error_fails(tmp_path):
    d = _mk(tmp_path, {
        "SKILL.md": SKILL_MD,
        "scripts/run.py": "def broken(:\n    pass\n",
    })
    c = svc._check_scripts(d)
    assert c.status == "fail" and "syntax error" in c.detail


def test_missing_referenced_script_fails(tmp_path):
    # SKILL.md references scripts/run.py but only other.py exists.
    d = _mk(tmp_path, {
        "SKILL.md": SKILL_MD,
        "other.py": "x = 1\n",
    })
    c = svc._check_scripts(d)
    assert c.status == "fail" and "missing referenced script" in c.detail


def test_undeclared_third_party_dep_warns(tmp_path):
    d = _mk(tmp_path, {
        "SKILL.md": "---\nname: x\ndescription: y\n---\nno refs\n",
        "run.py": "import requests\nrequests.get('http://x')\n",
    })
    c = svc._check_scripts(d)
    assert c.status == "warn" and "requests" in c.detail


def test_declared_dep_passes(tmp_path):
    d = _mk(tmp_path, {
        "SKILL.md": "---\nname: x\ndescription: y\n---\nno refs\n",
        "run.py": "import requests\n",
        "requirements.txt": "requests\n",
    })
    c = svc._check_scripts(d)
    assert c.status == "pass"


def test_local_import_not_flagged(tmp_path):
    # Importing a sibling module in the skill is not an undeclared dependency.
    d = _mk(tmp_path, {
        "SKILL.md": "---\nname: x\ndescription: y\n---\nno refs\n",
        "run.py": "import helpers\n",
        "helpers.py": "VALUE = 1\n",
    })
    c = svc._check_scripts(d)
    assert c.status == "pass"


def test_scorecard_includes_scripts_check(tmp_path, monkeypatch):
    import agentic_cli.commands.code as code

    reg = tmp_path / "registry"
    monkeypatch.setattr(code, "_get_registry_path", lambda: reg)
    svc.stage_uploaded_skill("demo", [
        ("demo/SKILL.md", SKILL_MD),
        ("demo/scripts/run.py", "print('hi')\n"),
    ])
    monkeypatch.setattr(svc, "_check_ai_review",
                        lambda *_a, **_k: (svc.TrialCheck(name="AI review", status="skipped"), ""))
    card = svc.evaluate_trial("demo", "", "dev", run_security=False)
    names = [c.name for c in card.checks]
    assert "Scripts" in names
    scripts = next(c for c in card.checks if c.name == "Scripts")
    assert scripts.status == "pass"


def test_scripts_context_includes_code(tmp_path):
    d = _mk(tmp_path, {
        "SKILL.md": SKILL_MD,
        "scripts/run.py": "MAGIC_TOKEN = 42\n",
    })
    ctx = svc._scripts_context(d)
    assert "run.py" in ctx and "MAGIC_TOKEN" in ctx
