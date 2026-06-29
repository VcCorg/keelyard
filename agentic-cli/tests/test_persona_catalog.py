"""Tests for the data-driven persona catalog and rendering."""

from pathlib import Path

import pytest
import yaml

from agentic_cli.meta_repo.config import (
    BUILTIN_PERSONA_IDS,
    PersonaSection,
    PersonasConfig,
    PersonaSpec,
)
from agentic_cli.persona_catalog import (
    add_product_persona,
    builtin_catalog,
    load_product_personas,
    remove_product_persona,
    resolve_personas,
)
from agentic_cli.skill_generator import (
    gather_domain_context,
    generate_personas,
    render_persona,
)


@pytest.fixture
def ctx():
    d = {
        "name": "cwow-facility",
        "product": "CWOW",
        "domain": "Facility",
        "description": "Facility domain",
        "jira_project": "CFAC",
        "bitbucket_project": "CWOWFAC",
        "confluence_space": "CFAC",
    }
    repos = [{"repo_slug": "cwow-facility-ui", "clone_url": "http://x", "onboarded": 1}]
    return gather_domain_context(d, repos, [])


# ── Catalog resolution ──────────────────────────────────────────────────────

class TestResolveCatalog:
    def test_builtins_when_no_product_catalog(self):
        specs = resolve_personas(None)
        assert [s.id for s in specs] == list(BUILTIN_PERSONA_IDS)
        assert all(s.builtin for s in specs)

    def test_defaults_enabled_filters_builtins(self):
        cfg = PersonasConfig.from_dict({"defaults_enabled": ["domain", "dev"]})
        specs = resolve_personas(config=cfg)
        assert [s.id for s in specs] == ["domain", "dev"]

    def test_custom_persona_appended(self):
        cfg = PersonasConfig.from_dict({
            "defaults_enabled": ["dev"],
            "personas": [{"id": "tech-lead", "label": "Tech Lead"}],
        })
        specs = resolve_personas(config=cfg)
        ids = [s.id for s in specs]
        assert ids == ["dev", "tech-lead"]
        assert specs[-1].builtin is False

    def test_custom_overrides_builtin_of_same_id(self):
        cfg = PersonasConfig.from_dict({
            "defaults_enabled": ["domain", "dev"],
            "personas": [{"id": "dev", "label": "Custom Dev",
                          "sections": [{"title": "X", "body": "custom"}]}],
        })
        specs = resolve_personas(config=cfg)
        ids = [s.id for s in specs]
        assert ids == ["domain", "dev"]  # order preserved, no duplicate
        dev = next(s for s in specs if s.id == "dev")
        assert dev.builtin is False
        assert dev.label == "Custom Dev"


class TestLoadProductPersonas:
    def test_missing_file_returns_none(self, tmp_path):
        assert load_product_personas(tmp_path) is None

    def test_loads_yaml(self, tmp_path):
        cfg_dir = tmp_path / ".platform" / "config"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "personas.yaml").write_text(yaml.safe_dump({
            "defaults_enabled": ["dev"],
            "personas": [{"id": "po", "label": "Product Owner"}],
        }))
        cfg = load_product_personas(tmp_path)
        assert cfg is not None
        assert cfg.defaults_enabled == ["dev"]
        assert cfg.personas[0].id == "po"


# ── Rendering ────────────────────────────────────────────────────────────────

class TestRenderPersona:
    def test_builtin_uses_rich_generator(self, ctx):
        spec = next(s for s in builtin_catalog() if s.id == "dev")
        out = render_persona(spec, ctx)
        assert "Developer Guide" in out
        assert "cwow-facility-ui" in out

    def test_custom_renders_sections_and_context(self, ctx):
        spec = PersonaSpec(
            id="tech-lead", label="Tech Lead", description="Arch direction",
            sections=[PersonaSection(title="Responsibilities", body="- own ADRs")],
        )
        out = render_persona(spec, ctx)
        assert "role: tech-lead" in out
        assert "## Responsibilities" in out
        assert "- own ADRs" in out
        assert "## Domain Context" in out
        assert "CFAC" in out


class TestGeneratePersonas:
    def test_writes_skill_md_per_persona(self, ctx, tmp_path):
        specs = resolve_personas(None)
        written = generate_personas(specs, ctx, tmp_path)
        assert set(written) == set(BUILTIN_PERSONA_IDS)
        for pid in BUILTIN_PERSONA_IDS:
            assert (tmp_path / pid / "SKILL.md").exists()

    def test_persona_filter_subset(self, ctx, tmp_path):
        specs = [s for s in resolve_personas(None) if s.id in {"dev", "qa"}]
        written = generate_personas(specs, ctx, tmp_path)
        assert set(written) == {"dev", "qa"}
        assert not (tmp_path / "sm").exists()


# ── Product catalog mutations ────────────────────────────────────────────────

class TestProductMutations:
    def test_add_creates_catalog_and_persists(self, tmp_path):
        add_product_persona(tmp_path, PersonaSpec(id="tech-lead", label="Tech Lead"))
        cfg = load_product_personas(tmp_path)
        assert cfg is not None
        assert [p.id for p in cfg.personas] == ["tech-lead"]

    def test_add_is_idempotent_upsert(self, tmp_path):
        add_product_persona(tmp_path, PersonaSpec(id="po", label="PO v1"))
        add_product_persona(tmp_path, PersonaSpec(id="po", label="PO v2"))
        cfg = load_product_personas(tmp_path)
        assert len(cfg.personas) == 1
        assert cfg.personas[0].label == "PO v2"

    def test_remove_returns_true_then_false(self, tmp_path):
        add_product_persona(tmp_path, PersonaSpec(id="tech-lead", label="Tech Lead"))
        assert remove_product_persona(tmp_path, "tech-lead") is True
        assert remove_product_persona(tmp_path, "tech-lead") is False

    def test_remove_missing_when_no_catalog(self, tmp_path):
        assert remove_product_persona(tmp_path, "anything") is False
