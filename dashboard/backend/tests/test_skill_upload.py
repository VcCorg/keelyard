"""Tests for uploading a candidate skill into the registry + the scan toggle."""

import json

import pytest

from src.services import skill_trial_service as svc


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    """Point the skills registry at a temp dir (created empty on first use)."""
    import agentic_cli.commands.code as code

    reg = tmp_path / "skills-registry"
    monkeypatch.setattr(code, "_get_registry_path", lambda: reg)
    return reg


SKILL_MD = "---\nname: demo\ndescription: A demo skill\n---\n\n# Demo\nDo the thing.\n"


def test_upload_folder_stages_and_registers(registry):
    res = svc.stage_uploaded_skill("", [
        ("demo/SKILL.md", SKILL_MD),
        ("demo/scripts/run.py", "print('hi')\n"),
    ])
    assert res.skill == "demo" and res.files == 2
    skill_dir = registry / "skills" / "demo"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "scripts" / "run.py").is_file()
    # registry.json upserted with the uploaded entry.
    data = json.loads((registry / "registry.json").read_text())
    entry = next(s for s in data["skills"] if s["name"] == "demo")
    assert entry["description"] == "A demo skill" and "uploaded" in entry["tags"]


def test_upload_single_markdown_becomes_skill_md(registry):
    res = svc.stage_uploaded_skill("my-skill", [("notes.md", SKILL_MD)])
    assert res.skill == "my-skill"
    assert (registry / "skills" / "my-skill" / "SKILL.md").read_text().startswith("---")


def test_upload_requires_skill_md(registry):
    with pytest.raises(ValueError, match="SKILL.md"):
        svc.stage_uploaded_skill("x", [("x/readme.txt", "no frontmatter here")])


def test_upload_contains_path_traversal(registry):
    # '..' segments are stripped during normalization, so nothing escapes the
    # skill directory — the escape file lands harmlessly inside it.
    svc.stage_uploaded_skill("x", [
        ("x/SKILL.md", SKILL_MD),
        ("x/../../evil.txt", "pwned"),
    ])
    assert not (registry.parent / "evil.txt").exists()
    assert not (registry / "evil.txt").exists()
    # It was flattened into the skill dir, not written anywhere outside it.
    assert (registry / "skills" / "x" / "evil.txt").is_file()


def test_run_security_false_skips_scan(registry, monkeypatch):
    svc.stage_uploaded_skill("demo", [("demo/SKILL.md", SKILL_MD)])
    # Avoid a real LLM call for the AI-review check.
    monkeypatch.setattr(svc, "_check_ai_review",
                        lambda *_a, **_k: (svc.TrialCheck(name="AI review", status="skipped"), ""))
    card = svc.evaluate_trial("demo", "", "dev", run_security=False)
    sec = next(c for c in card.checks if c.name == "Security scan")
    assert sec.status == "skipped" and "Disabled" in sec.detail
