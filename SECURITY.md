# Security Policy

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.**

Report it privately through
[GitHub's private vulnerability reporting](https://github.com/VcCorg/keelyard/security/advisories/new)
(Security tab → Report a vulnerability). That creates a private advisory only
maintainers can see.

Please include:

- what an attacker can do, and what access they'd need to start
- steps to reproduce, ideally minimal
- affected version or commit
- your platform (desktop app vs. dev workspace, OS)

We aim to acknowledge within a few business days. This is a small project, so
please allow reasonable time for a fix before disclosing publicly.

## Supported versions

Keel has not reached a stable release. Security fixes land on `main`; there are
no maintained release branches yet.

## Where the risk actually sits

Some context on the areas most worth scrutiny:

**Credentials.** Keel stores provider keys and integration tokens in `~/.keel/`
on the user's machine. It is not a secret-management system. Configuration is
read from environment variables and local files — never commit either.

**MCP servers get real access.** Configured MCP servers (Bitbucket, Jira,
Confluence, Glean, and others) act with the credentials you give them. Treat
adding an MCP server as granting an agent that system's access.

**Skills are executable influence.** A skill shapes what an agent does, and may
carry scripts. Skills from outside your organization are untrusted input. The
built-in scanner and the persona/skill policy exist for this; keep enforcement on
when running third-party skills.

**The desktop app runs a local backend.** It binds to `127.0.0.1` on a
per-launch port and serves the dashboard plus a terminal (PTY) over WebSocket.
That terminal is a real shell with the user's privileges. Do not expose the
backend port beyond localhost.

**Installers are unsigned.** Builds are not yet code-signed or notarized, so the
usual OS integrity guarantees don't apply. Verify you obtained an installer from
an official release before running it.

**Governance is a control, not a sandbox.** The seams
(`execution.registry.create_session`, `keel code onboard`) enforce policy and
produce an audit trail. They do not sandbox agent execution — an agent runs with
the permissions of the user and the tools it has been given.

## Scope

In scope: anything letting an attacker read or exfiltrate credentials, execute
code the user did not intend, bypass a governance seam or its audit trail, or
escalate what an agent can reach.

Out of scope: findings that require an already-compromised machine, the unsigned
installer warning itself (known and documented), and vulnerabilities in
third-party dependencies without a demonstrated impact on Keel — report those
upstream, and tell us if we should pin or patch.
