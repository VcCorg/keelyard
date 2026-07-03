# Architecture — Current State vs New State

*High-level. Each section is a slide.*

---

## Principle

> **The CLI is the heart of all logic and the central auditor.**
> **The dashboard is a lens** — for interactive work and external (MCP) integrations.
> Every surface calls the CLI; every consequential action is audited.

---

## Current state — logic drifting into the dashboard

As features shipped quickly, engine logic and state landed in the **dashboard**, creating
a parallel implementation. CLI users and CI didn't benefit, and there was no shared audit.

```mermaid
flowchart TB
  subgraph DASH["🖥 Dashboard (grew its own engine)"]
    UI["React UI"] --> BE["FastAPI backend"]
    BE --> L1["manifest logic"]
    BE --> L2["security scan"]
    BE --> L3["retriever store (~/.dva JSON)"]
  end
  subgraph CLIB["⌨ CLI (agentic-cli)"]
    ENG["templates · onboard · skills"]
    TR["tracker (activity only)"]
  end
  BE -. "drives some cmds" .-> ENG
  L1 -. "duplicates" .-> ENG
  X(["⚠ CLI users and CI miss<br/>security · manifest · retrievers"])
  L2 -.-> X

  classDef dash fill:#fef2f2,stroke:#ef4444,color:#7f1d1d;
  classDef cli fill:#f1f5f9,stroke:#64748b,color:#0f172a;
  classDef warn fill:#fff7ed,stroke:#f97316,color:#7c2d12,stroke-dasharray:4 3;
  class UI,BE,L1,L2,L3 dash;
  class ENG,TR cli;
  class X warn;
```

**Symptoms:** duplicated logic · dashboard-only capabilities · no cross-feature audit ·
the manifest (meant to be the spine) understood only by the browser.

---

## New state — CLI-first, dashboard as a lens

Engine logic moves into the CLI. The dashboard delegates and is tagged `source="dashboard"`.
The **tracker becomes the auditor**, linking actions across features.

```mermaid
flowchart TB
  subgraph SURFACES["Surfaces"]
    UI["🖥 Dashboard UI"]
    CI["🤖 CI / automation"]
    DEV["⌨ CLI users"]
  end

  subgraph CLI["⌨ CLI (agentic-cli) — engine + auditor"]
    direction TB
    M["manifest"]
    SEC["skill_security"]
    RET["retrievers"]
    ENG["templates · onboard · eval"]
    AUD[("📋 tracker / audit trail<br/>correlation_id · entity · source")]
    M --> AUD
    SEC --> AUD
    RET --> AUD
    ENG --> AUD
  end

  subgraph EXT["External (via dashboard)"]
    MCP["MCP servers<br/>Glean · Confluence · Jira · Bitbucket"]
  end

  UI -->|delegates| CLI
  CI -->|invokes| CLI
  DEV -->|invokes| CLI
  UI -->|MCP calls| EXT

  classDef surface fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a;
  classDef cli fill:#f0fdf4,stroke:#22c55e,color:#14532d;
  classDef audit fill:#ecfeff,stroke:#06b6d4,color:#083344;
  classDef ext fill:#faf5ff,stroke:#a855f7,color:#581c87;
  class UI,CI,DEV surface;
  class M,SEC,RET,ENG cli;
  class AUD audit;
  class MCP ext;
```

---

## What moved (parity delivered)

| Capability | Current (drift) | New (CLI-first) |
|------------|-----------------|-----------------|
| **Manifest** | dashboard derives/writes `agent.yaml` | `dva project manifest` — dashboard delegates |
| **Security** | dashboard-only scan + CI script | `dva skill scan` + **gate in `dva skill install`** — dashboard delegates |
| **Retrievers** | dashboard-only JSON store | `dva retriever …` registry — dashboard delegates |
| **Audit** | activity log only | `activity_log` + **correlation_id / entity / source**; `record_action`, `get_action_chain`; `dva history` shows Source |

---

## Division of responsibility

```mermaid
flowchart LR
  subgraph CLIZONE["CLI owns"]
    A1["Business logic"]
    A2["Persistence and registries"]
    A3["Security gates"]
    A4["Audit / traceability"]
  end
  subgraph DASHZONE["Dashboard owns"]
    B1["Interactive UX"]
    B2["Visualization (Canvas)"]
    B3["External / MCP calls"]
    B4["Delegation to CLI"]
  end
  DASHZONE ==>|calls, tagged source=dashboard| CLIZONE

  classDef c fill:#f0fdf4,stroke:#22c55e,color:#14532d;
  classDef d fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a;
  class A1,A2,A3,A4 c;
  class B1,B2,B3,B4 d;
```
