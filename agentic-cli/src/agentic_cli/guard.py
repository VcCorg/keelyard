"""What an agent *can* reach — the inventory half of KeelGuard.

KeelTrace answers what an agent **did** reach: one ledger row per retrieval,
after the fact. That is evidence, and evidence arrives too late to stop
anything. KeelGuard is the other question — what is *reachable* before a session
starts — and this module is its first phase: the Bill of Materials itself, with
no verdict attached.

**Deliberately no risk scoring here.** Composing components into a verdict is a
policy question, and the policy belongs where every other governance dial lives
— a product sets a floor, a domain may tighten it. Whether one cautious skill
plus three credentialed servers adds up to a refusal is not a judgement this
file should be making up. Phase one enumerates; the arithmetic comes later and
comes from governance.

**Configured is not reached, and both matter.** A component that is configured
and never touched is surface carried for nothing — the cheapest thing to remove,
and invisible until the two are shown side by side. A component reached that
nobody configured deliberately is the more alarming direction. The ledger
supplies the second column, which is the point of building this on top of
KeelTrace rather than beside it.

**What this refuses to claim.** Credential *names* are enumerable and useful:
knowing a server is handed an API key is a real fact. What that key can *do* is
not knowable from here without asking the service, so this reports the names and
stops. It also **never reads or records a credential value** — an inventory that
leaked the secrets it inventoried would be the worst possible version of this
feature. Values are dropped at the point of reading, not masked afterwards.

Whatever could not be enumerated is listed rather than omitted. A Bill of
Materials silently missing a section reads as a clean bill.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

SKILL = "skill"
MCP = "mcp"
ENGINE = "engine"
MODEL = "model"
REPO = "repo"

#: The order a report shows components in: what runs, what it can call, what it
#: can read, and what it thinks with.
KIND_ORDER = (SKILL, MCP, REPO, ENGINE, MODEL)

KIND_LABELS = {
    SKILL: "Skills",
    MCP: "MCP servers",
    REPO: "Repositories",
    ENGINE: "Execution engine",
    MODEL: "Model",
}


@dataclass
class Component:
    """One thing a session could reach."""

    kind: str
    name: str
    detail: str = ""
    origin: str = ""
    enabled: bool = True
    #: Credential *names* only — never values. See the module docstring.
    credentials: tuple[str, ...] = ()
    #: True when the ledger shows this was actually used by the session being
    #: inventoried. ``None`` means no session was given, which is different
    #: from "configured and unused" and must not render the same.
    reached: Optional[bool] = None

    @property
    def credentialed(self) -> bool:
        return bool(self.credentials)

    @property
    def unused(self) -> bool:
        """Configured, and this session did not touch it."""
        return self.reached is False

    def to_dict(self) -> dict:
        return {"kind": self.kind, "name": self.name, "detail": self.detail,
                "origin": self.origin, "enabled": self.enabled,
                "credentials": list(self.credentials), "reached": self.reached}


@dataclass
class Inventory:
    """Everything one domain's session could reach, and what we could not ask."""

    domain: str = ""
    session_id: str = ""
    components: list[Component] = field(default_factory=list)
    #: Sections that could not be enumerated. Listed, never omitted: a Bill of
    #: Materials missing a section silently reads as a clean bill.
    unknown: list[str] = field(default_factory=list)

    def of(self, kind: str) -> list[Component]:
        return [c for c in self.components if c.kind == kind]

    @property
    def enabled(self) -> list[Component]:
        return [c for c in self.components if c.enabled]

    @property
    def credentialed(self) -> list[Component]:
        return [c for c in self.components if c.credentialed]

    @property
    def unused(self) -> list[Component]:
        """Configured and untouched — the cheapest surface to remove."""
        return [c for c in self.components if c.unused]

    @property
    def complete(self) -> bool:
        return not self.unknown

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for component in self.components:
            out[component.kind] = out.get(component.kind, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "domain": self.domain, "session_id": self.session_id,
            "counts": self.counts, "complete": self.complete,
            "unknown": list(self.unknown),
            "credentialed": len(self.credentialed),
            "unused": len(self.unused),
            "components": [c.to_dict() for c in self.components],
        }


def collect(domain: str = "", session_id: str = "") -> Inventory:
    """Enumerate what a domain's sessions can reach.

    ``session_id`` adds the second column: which of these a specific run
    actually touched, read from the ledger. Without it every component's
    ``reached`` stays None, because "we did not look" and "configured and
    unused" are different facts and collapsing them would invent the more
    flattering one.
    """
    inventory = Inventory(domain=domain, session_id=session_id)

    for section, gather in (("skills", _skills), ("mcp servers", _mcp),
                            ("repositories", _repos), ("engine", _engine),
                            ("model", _model)):
        try:
            inventory.components.extend(gather(domain))
        except Exception as exc:  # noqa: BLE001 - a section we cannot read is named
            logger.debug("could not enumerate %s: %s", section, exc)
            inventory.unknown.append(section)

    if session_id:
        try:
            _mark_reached(inventory, session_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("could not read the ledger for %s: %s", session_id, exc)
            inventory.unknown.append("what the session reached")
    return inventory


def _skills(domain: str) -> list[Component]:
    """Skills installed for the domain, from its context-meta repo."""
    if not domain:
        return []
    from agentic_cli.skills_upstream import discover_for_domain

    repo, candidates = discover_for_domain(domain)
    return [
        Component(kind=SKILL, name=getattr(c, "name", "") or str(c),
                  detail=getattr(c, "description", "") or "",
                  origin=str(repo))
        for c in candidates
    ]


def _mcp(domain: str) -> list[Component]:
    """Registered MCP servers, with credential *names* only."""
    from agentic_cli.mcp.config import load_registry

    found: list[Component] = []
    for name, server in (load_registry().servers or {}).items():
        # Only the keys. A value never leaves the config object — this is the
        # one place an inventory could turn into a disclosure, so the values are
        # not read at all rather than read and masked.
        credentials = tuple(sorted((server.env or {}).keys()))
        found.append(Component(
            kind=MCP, name=name,
            # `.value` on both: these are str-Enums, and their repr
            # ("MCPServerType.HTTP") is not what an operator reading a bill of
            # materials wants to see.
            detail=(server.description or "")
                   or f"{_enum_value(server.type)} / {_enum_value(server.transport)}",
            origin=server.url or server.command or "",
            enabled=bool(server.enabled),
            credentials=credentials,
        ))
    return found


def _enum_value(value) -> str:
    return str(getattr(value, "value", value) or "")


def _repos(domain: str) -> list[Component]:
    """Repositories linked to the domain — what a session can read from disk."""
    if not domain:
        return []
    from agentic_cli.tracker import get_domain_repos

    return [
        Component(kind=REPO, name=r.get("repo_slug") or "?",
                  detail=r.get("repo_url") or "", origin="domain link")
        for r in get_domain_repos(domain)
    ]


def _engine(domain: str) -> list[Component]:
    """The execution engine a session would run on, and its governance stance."""
    from agentic_cli.execution.registry import get_engine
    from agentic_cli.meta_repo.build_governance import check_session

    found: list[Component] = []
    try:
        engine = get_engine()
        found.append(Component(kind=ENGINE, name=getattr(engine, "name", "?"),
                               origin="execution.registry"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("no engine resolved: %s", exc)

    policy = check_session(domain)
    mode = getattr(policy, "mode", "") or getattr(policy, "level", "") or "unknown"
    found.append(Component(
        kind=ENGINE, name="build governance", detail=f"mode: {mode}",
        origin="meta_repo.build_governance"))
    return found


def _model(domain: str) -> list[Component]:
    """The model a session would think with, and where it is served from.

    Resolved from configuration rather than by constructing a provider: building
    one can prompt, download, or fail on a missing credential, and an inventory
    that changes the thing it is inventorying is not an inventory.

    ``KIND_ORDER`` has always listed models and nothing collected one, so every
    inventory reported a session that thinks with nothing. Egress is the verdict
    that needed it.
    """
    import os

    from agentic_cli.llm.models import ModelRegistry

    name = ""
    for key in ("KEEL_LLM_MODEL", "KEEL_LOCAL_LLM_MODEL"):
        if os.environ.get(key):
            name = os.environ[key]
            if key == "KEEL_LOCAL_LLM_MODEL" and not ModelRegistry.detect_provider(name):
                # The local runtime's own env holds a bare model name; the
                # prefix is what carries the routing, so put it back.
                name = f"local:{name}"
            break
    if not name:
        try:
            from agentic_cli.kg.config import KGConfig

            name = (KGConfig.load().vertex_ai_model or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.debug("no model config: %s", exc)

    provider = os.environ.get("KEEL_LLM_PROVIDER") or (
        ModelRegistry.detect_provider(name) if name else "")
    if not name and not provider:
        # Named as unknown by the caller rather than reported as "no model",
        # which would read as "nothing to worry about".
        raise LookupError("no model configured")

    return [Component(kind=MODEL, name=name or provider,
                      detail=f"provider: {provider or 'unresolved'}",
                      origin="llm configuration")]


def _mark_reached(inventory: Inventory, session_id: str) -> None:
    """Fill in which components the session actually touched, from the ledger."""
    from agentic_cli import tracing

    touched: set[str] = set()
    for row in tracing.session_chain(session_id, limit=500):
        if row.get("entity_type") != "context":
            continue
        operation = str(row.get("subcommand") or "")
        # MCP operations are recorded as "<server>/<tool>"; the server half is
        # what an inventory entry is named by.
        if row.get("command") == "mcp" and "/" in operation:
            touched.add(operation.split("/", 1)[0].lower())
        elif row.get("command") == "retriever" and "/" in operation:
            touched.add(operation.split("/", 1)[0].lower())

    for component in inventory.components:
        if component.kind in (MCP,):
            component.reached = component.name.lower() in touched


__all__ = ["SKILL", "MCP", "ENGINE", "MODEL", "REPO", "KIND_ORDER",
           "KIND_LABELS", "Component", "Inventory", "collect"]
