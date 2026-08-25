"""Template lifecycle API: drift on a workspace target, status, promote, upgrade.

The behaviours worth pinning down here are the ones a UI would otherwise get
wrong:

1. Resolving a workspace target must stay fast — the drift check re-renders the
   whole template, so it only runs when explicitly asked for.
2. A broken/missing template baseline must never break the Workspaces page.
3. `ready` must not be downgraded by drift: a drifted meta-repo is still usable.
4. The write paths (upgrade / promote) must be lead-gated and must preview by
   default, exactly like the CLI.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import app
from src.services import template_service as tmpl
from src.services import workspace_service as svc

client = TestClient(app)

DOMAIN = "some-domain"


class FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


def _as(roles: str, monkeypatch):
    monkeypatch.setenv("KEEL_AUTH_MODE", "dev")
    monkeypatch.setenv("KEEL_DEV_ROLES", roles)
    monkeypatch.setenv("KEEL_DEV_USER", "smoke@test")


class FakeReport:
    """Stand-in for a DriftReport, so tests never scaffold a real meta-repo."""

    def __init__(self, entries, recorded="1.0.0", has_baseline=True):
        from agentic_cli.meta_repo import template_drift as drift

        self.meta_repo = "/tmp/meta"
        self.domain = DOMAIN
        self.recorded_version = recorded
        self.current_version = "1.0.0"
        self.has_baseline = has_baseline
        self.entries = [drift.FileDrift(path=p, status=s, detail="")
                        for p, s in entries]

    @property
    def counts(self):
        out = {}
        for e in self.entries:
            out[e.status] = out.get(e.status, 0) + 1
        return out

    @property
    def upgradable(self):
        return [e for e in self.entries if e.upgradable]

    @property
    def promotable(self):
        return [e for e in self.entries if e.promotable]

    @property
    def conflicted(self):
        from agentic_cli.meta_repo import template_drift as drift
        return [e for e in self.entries if e.status in drift.CONFLICTED]

    @property
    def drifted(self):
        from agentic_cli.meta_repo import template_drift as drift
        return any(e.status != drift.UNCHANGED for e in self.entries)

    @property
    def version_behind(self):
        return False


def _mixed_report():
    from agentic_cli.meta_repo import template_drift as drift

    return FakeReport([
        ("AGENTS.md", drift.TEMPLATE_UPDATED),
        ("docs/GOVERNANCE.md", drift.LOCALLY_MODIFIED),
        ("docs/PLAYBOOK.md", drift.LOCAL_ONLY),
        ("Makefile", drift.BOTH_MODIFIED),
        ("README.md", drift.UNCHANGED),
    ])


@pytest.fixture
def stub_drift(monkeypatch):
    monkeypatch.setattr(tmpl, "_classify", lambda domain, meta=None: _mixed_report())


# ── Status ───────────────────────────────────────────────────────────────────

def test_status_summarizes_each_drift_bucket(stub_drift):
    status = tmpl.template_status(DOMAIN)

    assert status.drifted is True
    assert status.upgradable == 1      # template-updated
    assert status.promotable == 2      # locally-modified + local-only
    assert status.conflicted == 1      # both-modified
    assert len(status.files) == 5


def test_status_endpoint_returns_the_file_list(stub_drift):
    r = client.get("/api/workspaces/template/status", params={"domain": DOMAIN})

    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["template-updated"] == 1
    assert {f["path"] for f in body["files"]} >= {"AGENTS.md", "Makefile"}


def test_status_endpoint_404s_for_an_unscaffolded_domain(monkeypatch):
    def boom(domain, meta=None):
        raise FileNotFoundError(f"No meta-repo found for domain '{domain}'")

    monkeypatch.setattr(tmpl, "_classify", boom)

    r = client.get("/api/workspaces/template/status", params={"domain": "ghost"})

    assert r.status_code == 404
    assert "No meta-repo" in r.json()["detail"]


def test_overlay_endpoint_reports_the_shared_template_contents():
    r = client.get("/api/workspaces/template/overlay")

    assert r.status_code == 200
    body = r.json()
    assert body["env_var"] == "KEEL_TEMPLATE_OVERLAY"
    assert isinstance(body["files"], list)


# ── Drift summary is failure-tolerant ───────────────────────────────────────

def test_drift_summary_reports_a_missing_meta_repo_without_raising(monkeypatch):
    def boom(domain, meta=None):
        raise FileNotFoundError("No meta-repo found for domain 'ghost'")

    monkeypatch.setattr(tmpl, "_classify", boom)

    summary = tmpl.drift_summary("ghost")

    assert summary.error and "No meta-repo" in summary.error
    assert summary.drifted is False


def test_drift_summary_swallows_unexpected_failures(monkeypatch):
    def boom(domain, meta=None):
        raise RuntimeError("render blew up")

    monkeypatch.setattr(tmpl, "_classify", boom)

    summary = tmpl.drift_summary(DOMAIN)

    assert "RuntimeError" in summary.error
    assert summary.counts == {}


def test_drift_summary_omits_the_file_list():
    """The chip only needs counts; shipping every file on every poll is waste."""
    assert "files" not in tmpl.TemplateDriftSummary.model_fields


# ── Workspace target integration ────────────────────────────────────────────

@pytest.fixture
def domain_target(monkeypatch, tmp_path):
    """A tech-lead target that resolves to an existing, synced meta-repo."""
    import agentic_cli.persona_workspace as pw

    meta = tmp_path / "meta"
    (meta / pw.GRAPH_DIR_NAME).mkdir(parents=True)
    (meta / pw.GRAPH_DIR_NAME / pw.GRAPH_REFS_FILENAME).write_text("{}")
    monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                        lambda *a, **k: meta)
    return meta


def test_target_has_no_drift_unless_asked(domain_target, monkeypatch):
    called = []
    monkeypatch.setattr(tmpl, "drift_summary",
                        lambda d: called.append(d) or tmpl.TemplateDriftSummary(domain=d))

    target = svc.resolve_target("tech-lead", domain=DOMAIN)

    assert target.drift is None
    assert called == []          # the expensive render never ran


def test_target_includes_drift_on_request(domain_target, stub_drift):
    target = svc.resolve_target("tech-lead", domain=DOMAIN, include_drift=True)

    assert target.drift is not None
    assert target.drift.drifted is True
    assert target.drift.upgradable == 1


def test_drift_does_not_downgrade_readiness(domain_target, stub_drift):
    """A drifted meta-repo is still a working workspace — the chip informs, it
    doesn't block."""
    target = svc.resolve_target("tech-lead", domain=DOMAIN, include_drift=True)

    assert target.ready is True
    assert target.needs is None


def test_repo_tier_targets_are_never_drift_checked(monkeypatch, tmp_path):
    """Only the domain meta-repo is generated from the template."""
    called = []
    monkeypatch.setattr(tmpl, "drift_summary", lambda d: called.append(d))
    monkeypatch.setattr("agentic_cli.persona_workspace.get_workspace_base",
                        lambda: tmp_path)

    target = svc.resolve_target("dev", domain=DOMAIN, repo="svc",
                                include_drift=True)

    assert target.drift is None
    assert called == []


def test_target_endpoint_defaults_to_no_drift(domain_target, monkeypatch):
    called = []
    monkeypatch.setattr(tmpl, "drift_summary",
                        lambda d: called.append(d) or tmpl.TemplateDriftSummary(domain=d))

    r = client.get("/api/workspaces/target",
                   params={"persona": "tech-lead", "domain": DOMAIN})

    assert r.status_code == 200
    assert r.json()["drift"] is None
    assert called == []


def test_target_endpoint_passes_the_drift_flag_through(domain_target, stub_drift):
    r = client.get("/api/workspaces/target",
                   params={"persona": "tech-lead", "domain": DOMAIN, "drift": "true"})

    assert r.status_code == 200
    assert r.json()["drift"]["drifted"] is True


# ── Promotable listing ──────────────────────────────────────────────────────

def test_promotable_endpoint_404s_without_a_meta_repo(monkeypatch):
    monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                        lambda *a, **k: None)

    r = client.get("/api/workspaces/template/promotable",
                   params={"domain": "ghost"})

    assert r.status_code == 404


def test_promotable_endpoint_lists_local_files(monkeypatch, tmp_path):
    from agentic_cli.meta_repo import template_drift as drift
    from agentic_cli.meta_repo import template_promote as prom

    monkeypatch.setattr("agentic_cli.meta_repo.detector.detect_domain_meta_repo",
                        lambda *a, **k: tmp_path)
    monkeypatch.setattr(prom, "promotable", lambda meta, domain="": (
        [drift.FileDrift(path="docs/PLAYBOOK.md", status=drift.LOCAL_ONLY,
                         detail="added locally")],
        {"domain": DOMAIN, "product": "P"},
    ))

    r = client.get("/api/workspaces/template/promotable",
                   params={"domain": DOMAIN})

    assert r.status_code == 200
    body = r.json()
    assert body["files"][0]["path"] == "docs/PLAYBOOK.md"
    assert body["overlay_root"]


# ── Write paths: CLI argument construction ──────────────────────────────────

def _args_of(monkeypatch, call) -> list[str]:
    """Capture the argv the service would hand to the CLI."""
    captured: dict = {}

    async def fake_stream(args):
        captured["args"] = args
        yield "__EXIT__ 0"

    monkeypatch.setattr("src.services.workspace_service._stream_cli", fake_stream)
    gen = call()
    import asyncio

    async def drain():
        async for _ in gen:
            pass

    asyncio.run(drain())
    return captured["args"]


def test_upgrade_previews_by_default(monkeypatch):
    args = _args_of(monkeypatch, lambda: tmpl.stream_upgrade(DOMAIN))

    assert args[:4] == ["domain", "template", "upgrade", DOMAIN]
    assert "--apply" not in args


def test_upgrade_apply_is_non_interactive(monkeypatch):
    """The CLI confirms interactively; there is no TTY behind an HTTP request, so
    apply must pass -y or the stream would hang forever."""
    args = _args_of(monkeypatch,
                    lambda: tmpl.stream_upgrade(DOMAIN, apply=True))

    assert "--apply" in args and "-y" in args


def test_upgrade_forwards_prune_and_force(monkeypatch):
    args = _args_of(monkeypatch, lambda: tmpl.stream_upgrade(
        DOMAIN, apply=True, prune=True, force=True))

    assert {"--prune", "--force"} <= set(args)


def test_promote_previews_by_default_and_passes_each_file(monkeypatch):
    args = _args_of(monkeypatch, lambda: tmpl.stream_promote(
        DOMAIN, ["AGENTS.md", "docs/PLAYBOOK.md"]))

    assert args.count("--file") == 2
    assert "AGENTS.md" in args and "docs/PLAYBOOK.md" in args
    assert "--apply" not in args and "--push" not in args


def test_promote_publishing_stays_opt_in(monkeypatch):
    args = _args_of(monkeypatch, lambda: tmpl.stream_promote(
        DOMAIN, ["AGENTS.md"], apply=True, push=True, allow_unreviewed=True))

    assert {"--apply", "--push", "--allow-unreviewed"} <= set(args)


# ── Write paths: authorization ──────────────────────────────────────────────

def test_viewer_cannot_upgrade_a_template(monkeypatch):
    from src.api.workspace import _require_template_write

    _as("viewer", monkeypatch)
    with pytest.raises(HTTPException) as e:
        _require_template_write()(FakeRequest())
    assert e.value.status_code == 403


def test_lead_can_upgrade_a_template(monkeypatch):
    from agentic_cli.auth import PERM_KNOWLEDGE_PROJECT
    from src.api.workspace import _require_template_write

    _as("maintainer", monkeypatch)
    principal = _require_template_write()(FakeRequest())
    assert principal.has(PERM_KNOWLEDGE_PROJECT)


def test_promote_requires_at_least_one_file():
    r = client.get("/api/workspaces/template/promote/stream",
                   params={"domain": DOMAIN})
    assert r.status_code == 422   # `file` is a required query param
