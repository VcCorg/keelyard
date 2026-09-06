"""Per-component verdicts over a guard inventory — G2, and not one step further.

G1 enumerated and stopped, deliberately. This says something *about* each
component, and stays on the near side of one line: a finding describes one
component's own surface. It never composes findings into a session-level
verdict, a score, or a pass/fail, because composition is policy — a product sets
a governance floor and a domain may tighten it, and inventing the arithmetic
here would put it somewhere nobody can waive it. That is G3, and it needs a
decision about how an organisation works, not a guess.

So there is no severity field, no score, and no ranking, and a test asserts it.
The two things a finding does carry are what is true and **what it is not
saying** — because both verdicts below are one sloppy sentence away from
claiming much more than they know.

**Credential scope, as far as a name goes.** The inventory holds credential
*names*, never values. What a key can actually do is not knowable without asking
the service, so nothing here guesses scope from a name — `JIRA_ADMIN_TOKEN` may
be read-only and `JIRA_TOKEN` may not be. What *is* knowable from names alone is
sharing: one credential name handed to two servers means compromising either
reaches both services, and that is a fact about the configuration rather than an
inference about the key. Paired with the ledger, the other knowable fact is a
credential held for a server this session never touched.

**Model egress, from the runtime and not the prefix.** Whether retrieved context
leaves the machine is a fact worth stating plainly, and the obvious way to
determine it is wrong: `local:` and `ollama:` mean *OpenAI-compatible runtime*,
not *local host*. ``KEEL_LOCAL_LLM_URL`` can point anywhere, and a deployment
that moved its runtime to a shared box is exactly the case where somebody is
relying on a prefix that stopped being true. So the host is what gets checked.

Egress is a destination, not a judgement. Sending context to a vendor under
contract is ordinary; this reports where it goes and leaves whether that is
allowed to the floor.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── finding codes ───────────────────────────────────────────────────────────

#: One credential name is handed to more than one server.
CREDENTIAL_SHARED = "credential-shared"
#: A credentialed component this session never touched.
CREDENTIAL_IDLE = "credential-idle"
#: Retrieved context leaves this machine to reach the model.
EGRESS_EXTERNAL = "egress-external"
#: Inference is served from this machine.
EGRESS_LOCAL = "egress-local"
#: Where inference is served from could not be established.
EGRESS_UNKNOWN = "egress-unknown"

CODES = (CREDENTIAL_SHARED, CREDENTIAL_IDLE, EGRESS_EXTERNAL, EGRESS_LOCAL,
         EGRESS_UNKNOWN)

#: Providers whose inference happens off this machine, by construction.
_REMOTE_PROVIDERS = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "vertex-ai": "Google Vertex AI",
    "huggingface": "Hugging Face",
}

#: Providers that run in-process, with nothing to reach.
_IN_PROCESS = {"builtin", "test-mode"}

#: Hosts that mean "this machine". A `local:` model served from anything else is
#: remote regardless of what the prefix says.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal"}


@dataclass
class Finding:
    """One statement about one component. Never about a session as a whole."""

    component: str
    kind: str
    code: str
    statement: str
    #: What this finding explicitly does not claim. Not decoration: both
    #: verdicts here are a short step from overclaiming, and the boundary is
    #: part of the finding rather than a footnote somebody drops.
    limit: str = ""
    #: True when this rests on something observed. False when it rests on the
    #: absence of evidence, which is a weaker thing and says so.
    observed: bool = True
    #: Other components implicated — the servers sharing one credential name.
    related: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        out = {"component": self.component, "kind": self.kind,
               "code": self.code, "statement": self.statement,
               "observed": self.observed}
        if self.limit:
            out["limit"] = self.limit
        if self.related:
            out["related"] = list(self.related)
        return out


@dataclass
class Findings:
    """Every finding over one inventory, plus what could not be ruled on."""

    findings: list[Finding] = field(default_factory=list)
    #: Verdicts that could not be reached, and why. Named rather than omitted,
    #: for the same reason the inventory names the sections it could not read:
    #: a report silently missing one reads as a clean one.
    unruled: list[str] = field(default_factory=list)

    def of(self, code: str) -> list[Finding]:
        return [f for f in self.findings if f.code == code]

    def for_component(self, name: str) -> list[Finding]:
        return [f for f in self.findings if f.component == name]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for finding in self.findings:
            out[finding.code] = out.get(finding.code, 0) + 1
        return out

    @property
    def complete(self) -> bool:
        return not self.unruled

    def to_dict(self) -> dict:
        return {"counts": self.counts, "complete": self.complete,
                "unruled": list(self.unruled),
                "findings": [f.to_dict() for f in self.findings]}


# ── credential scope ────────────────────────────────────────────────────────

def _credential_findings(inventory) -> list[Finding]:
    """What credential *names* support, and nothing beyond it."""
    scope_limit = ("What this credential can do is not knowable from its name — "
                   "only the service can say.")

    by_credential: dict[str, list] = {}
    for component in inventory.components:
        for credential in component.credentials:
            by_credential.setdefault(credential, []).append(component)

    found: list[Finding] = []
    for credential, components in sorted(by_credential.items()):
        if len(components) < 2:
            continue
        names = tuple(sorted(c.name for c in components))
        for component in sorted(components, key=lambda c: c.name):
            found.append(Finding(
                component=component.name, kind=component.kind,
                code=CREDENTIAL_SHARED,
                statement=(f"Shares credential '{credential}' with "
                           + ", ".join(n for n in names if n != component.name)
                           + " — compromising one reaches the others' services."),
                limit=scope_limit,
                related=tuple(n for n in names if n != component.name),
            ))

    for component in inventory.components:
        # `reached is None` means no session was given. Saying "idle" then would
        # turn "we did not look" into a finding about the configuration.
        if component.credentialed and component.reached is False:
            found.append(Finding(
                component=component.name, kind=component.kind,
                code=CREDENTIAL_IDLE,
                statement=(f"Holds {len(component.credentials)} credential(s) and "
                           f"this session never reached it."),
                limit=("Says nothing about other sessions — one run is not a "
                       "usage history."),
                # The ledger showed no read. That is an observation about this
                # session, and it is the absence of one about the component.
                observed=False,
            ))

    return found


# ── model egress ────────────────────────────────────────────────────────────

def _egress_findings(inventory) -> tuple[list[Finding], list[str]]:
    """Where retrieved context goes to reach the model."""
    from agentic_cli import guard
    from agentic_cli.llm.models import ModelRegistry

    models = inventory.of(guard.MODEL)
    if not models:
        return [], ["model egress (no model in the inventory)"]

    found: list[Finding] = []
    for component in models:
        provider = (component.detail.partition("provider:")[2].strip()
                    or ModelRegistry.detect_provider(component.name) or "")

        if provider in _IN_PROCESS:
            found.append(Finding(
                component=component.name, kind=component.kind,
                code=EGRESS_LOCAL,
                statement="Inference runs in this process — context does not "
                          "leave the machine.",
            ))
            continue

        if provider in _REMOTE_PROVIDERS:
            found.append(Finding(
                component=component.name, kind=component.kind,
                code=EGRESS_EXTERNAL,
                statement=(f"Retrieved context leaves this machine to "
                           f"{_REMOTE_PROVIDERS[provider]}."),
                limit="A destination, not a judgement — whether that is allowed "
                      "is the governance floor's call.",
            ))
            continue

        if provider == "local":
            url = os.environ.get("KEEL_LOCAL_LLM_URL") or ""
            host = (urlparse(url).hostname or "").lower() if url else ""
            if not url:
                # The default is Ollama on this machine, and defaulting to the
                # reassuring answer without checking is the whole failure mode
                # this verdict exists for.
                found.append(Finding(
                    component=component.name, kind=component.kind,
                    code=EGRESS_LOCAL,
                    statement="No runtime URL set, so the default local runtime "
                              "applies — context stays on this machine.",
                    limit="Rests on the default, not on a configured address.",
                    observed=False,
                ))
            elif host in _LOCAL_HOSTS:
                found.append(Finding(
                    component=component.name, kind=component.kind,
                    code=EGRESS_LOCAL,
                    statement=f"Runtime at {host} — context stays on this machine.",
                ))
            else:
                # The finding this check exists for: a `local:` model that is
                # not local. The prefix means OpenAI-compatible, not on-host.
                found.append(Finding(
                    component=component.name, kind=component.kind,
                    code=EGRESS_EXTERNAL,
                    statement=(f"Named local, but its runtime is at {host} — "
                               f"retrieved context leaves this machine."),
                    limit="A destination, not a judgement — whether that is "
                          "allowed is the governance floor's call.",
                ))
            continue

        found.append(Finding(
            component=component.name, kind=component.kind,
            code=EGRESS_UNKNOWN,
            statement=f"Provider '{provider or 'unresolved'}' — could not "
                      f"establish where inference is served from.",
            limit="Unknown is not local. Treat as unestablished, not as safe.",
            observed=False,
        ))

    return found, []


def assess(inventory) -> Findings:
    """Rule on each component of an inventory, one component at a time.

    Findings are returned in the order the codes are defined, not ranked: a rank
    is a severity judgement wearing a different hat, and severity is the floor's
    to assign.
    """
    result = Findings()
    try:
        result.findings.extend(_credential_findings(inventory))
    except Exception as exc:  # noqa: BLE001 - a verdict we cannot reach is named
        logger.debug("credential findings failed: %s", exc)
        result.unruled.append("credential scope")

    try:
        egress, unruled = _egress_findings(inventory)
        result.findings.extend(egress)
        result.unruled.extend(unruled)
    except Exception as exc:  # noqa: BLE001
        logger.debug("egress findings failed: %s", exc)
        result.unruled.append("model egress")

    # The inventory's own gaps are this report's gaps too: a verdict over a
    # section that could not be enumerated was never reached either.
    for section in getattr(inventory, "unknown", []):
        result.unruled.append(f"{section} (not enumerated)")

    order = {code: i for i, code in enumerate(CODES)}
    result.findings.sort(key=lambda f: (order.get(f.code, 99), f.component))
    return result


__all__ = ["CREDENTIAL_SHARED", "CREDENTIAL_IDLE", "EGRESS_EXTERNAL",
           "EGRESS_LOCAL", "EGRESS_UNKNOWN", "CODES", "Finding", "Findings",
           "assess"]
