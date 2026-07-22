"""Neo4j preflight — pinpoints which stage blocks KG ingest."""

from src.services import kg_service as svc


def test_no_driver_reports_missing_package(monkeypatch):
    """If `neo4j` package isn't importable, preflight says so clearly."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "neo4j":
            raise ImportError("simulated missing driver")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    p = svc.neo4j_preflight()
    assert p.driver_available is False
    assert p.ok is False
    assert "driver" in p.message.lower()


def test_not_configured_reports_missing_config(monkeypatch):
    """Driver installed but no config → tell the user to configure."""
    class Cfg:
        provider = "neo4j"
        neo4j_uri = ""
        def is_neo4j_configured(self): return False

    import agentic_cli.kg.config as cfg_mod
    monkeypatch.setattr(cfg_mod.KGConfig, "load", classmethod(lambda cls: Cfg()))
    p = svc.neo4j_preflight()
    assert p.driver_available is True
    assert p.configured is False
    assert "configure" in p.message.lower() or "not configured" in p.message.lower()


def test_unreachable_reports_reachable_false(monkeypatch):
    """Configured but port closed → reachable=False."""
    class Cfg:
        provider = "neo4j"
        neo4j_uri = "bolt://localhost:7687"
        neo4j_username = "neo4j"
        neo4j_password = "x"
        def is_neo4j_configured(self): return True

    import agentic_cli.kg.config as cfg_mod
    monkeypatch.setattr(cfg_mod.KGConfig, "load", classmethod(lambda cls: Cfg()))

    import agentic_cli.kg.validation as val
    monkeypatch.setattr(val, "check_neo4j_availability",
                        lambda *_a, **_kw: (False, "Cannot connect to Neo4j at localhost:7687"))

    p = svc.neo4j_preflight()
    assert p.configured is True
    assert p.reachable is False and p.auth_ok is False and p.ok is False


def test_auth_failure_reports_reachable_true(monkeypatch):
    """Port answered but credentials rejected → reachable=True, auth_ok=False."""
    class Cfg:
        provider = "neo4j"
        neo4j_uri = "bolt://localhost:7687"
        neo4j_username = "neo4j"
        neo4j_password = "wrong"
        def is_neo4j_configured(self): return True

    import agentic_cli.kg.config as cfg_mod
    monkeypatch.setattr(cfg_mod.KGConfig, "load", classmethod(lambda cls: Cfg()))

    import agentic_cli.kg.validation as val
    monkeypatch.setattr(val, "check_neo4j_availability",
                        lambda *_a, **_kw: (False, "Authentication failed. Check username/password."))

    p = svc.neo4j_preflight()
    assert p.configured is True
    assert p.reachable is True
    assert p.auth_ok is False
    assert p.ok is False


def test_all_green(monkeypatch):
    class Cfg:
        provider = "neo4j"
        neo4j_uri = "bolt://localhost:7687"
        neo4j_username = "neo4j"
        neo4j_password = "pw"
        def is_neo4j_configured(self): return True

    import agentic_cli.kg.config as cfg_mod
    monkeypatch.setattr(cfg_mod.KGConfig, "load", classmethod(lambda cls: Cfg()))

    import agentic_cli.kg.validation as val
    monkeypatch.setattr(val, "check_neo4j_availability",
                        lambda *_a, **_kw: (True, "Neo4j is available and accessible"))

    p = svc.neo4j_preflight()
    assert p.driver_available and p.configured and p.reachable and p.auth_ok and p.ok
