# Vendor-Neutral Orchestrator — Knowledge That Outlives the Vendor

*Positioning. The durable thesis behind the platform.*

---

## The thesis

> **The organization owns the knowledge and the workflow. The coding engine is a
> replaceable execution provider.**

Coding agents are excellent and evolving fast — but if your **context, governance, and
history live inside a vendor** (e.g. a vendor's "Knowledge" store, playbooks, snapshots),
then **switching or losing that vendor loses your institutional knowledge with it.**

The platform's job is to keep the durable layer — knowledge, governance, audit — at the
**org level**, and use the vendor (Devin today) purely as a **cloud-native execution
engine** behind a swappable adapter.

---

## The durability model

```mermaid
flowchart TB
  subgraph ORG["🏛 Org Knowledge Layer — canonical · portable · vendor-neutral"]
    direction LR
    KG["Knowledge Graph"]
    META["Meta-repo domain context"]
    GOV["Governance rules"]
    AUD["Audit trail<br/>Jira ↔ session ↔ actions"]
  end

  subgraph PROJ["Projections — generated one-way, disposable"]
    direction LR
    DK["Devin Knowledge"]
    PB["Devin Playbooks / Snapshots"]
    CB["Context bundle<br/>(any agent)"]
  end

  subgraph EXE["Execution engines — swappable adapters"]
    direction LR
    DEVIN["Devin Cloud<br/>Sessions API"]
    OTHER["Other agents<br/>(future)"]
  end

  ORG -->|project| PROJ -->|feed| EXE
  EXE -. "results + audit back" .-> AUD

  classDef org fill:#eef2ff,stroke:#6366f1,color:#1e1b4b;
  classDef proj fill:#fefce8,stroke:#eab308,color:#713f12;
  classDef exe fill:#faf5ff,stroke:#a855f7,color:#581c87;
  class KG,META,GOV,AUD org;
  class DK,PB,CB proj;
  class DEVIN,OTHER exe;
```

**Rule:** knowledge is **authored in the org layer** and **projected** into the vendor.
Nothing of record is authored *only* inside the vendor — so projections are disposable.

---

## What survives if the vendor changes

```mermaid
flowchart LR
  ORG["🏛 Org Knowledge + Orchestration + Audit<br/><b>stays</b>"] --> AD["🔌 ExecutionEngine adapter"]
  AD --> D1["Devin Cloud"]
  AD -. "swap · re-project" .-> D2["Alternative engine"]

  classDef keep fill:#f0fdf4,stroke:#22c55e,color:#14532d;
  classDef ad fill:#eef2ff,stroke:#6366f1,color:#1e1b4b;
  classDef eng fill:#faf5ff,stroke:#a855f7,color:#581c87;
  class ORG keep;
  class AD ad;
  class D1,D2 eng;
```

Swap the adapter, re-project the knowledge — the org keeps its context, governance, and
history intact.

---

## The execution flow (unchanged for the user, neutral underneath)

```mermaid
flowchart LR
  J["Jira work item"] --> C["Task Contract<br/>assembled from org knowledge"]
  C --> E["ExecutionEngine.createSession()<br/>Devin adapter"]
  E --> R["Session linked to Jira ID"]
  R --> A["Audited in the org trail"]

  classDef s fill:#ecfeff,stroke:#06b6d4,color:#083344;
  class J,C,E,R,A s;
```

The developer experience is identical; only the layer *underneath* the adapter is
vendor-specific.

---

## Built vs. roadmap (honest state)

| Capability | State | Notes |
|------------|-------|-------|
| Org knowledge layer (KG + meta-repo + governance) | ✅ Built | Canonical, portable, org-owned |
| Jira work item → Task Contract → Devin session, linked | ✅ Built | `workflow_service` + `StartWorkDialog` + `createDevinSession` |
| Cross-feature audit (correlation_id · source) | ✅ Built | `tracker` / `record_action` |
| **ExecutionEngine adapter (swappable)** | ✅ Built | `agentic_cli.execution` seam; Devin is one adapter; dashboard routes through it (`source="dashboard"`) |
| **Canonical → Devin projection, one-way** | ✅ Built | `push-devin` is idempotent + versioned; each entry carries a provenance footer |
| **Provenance + drift status (no Devin-only authoring)** | ✅ Built | `dva kg okf project-status`: `okf://…` source refs + `in_sync/drift/unprojected/orphan`; surfaced as a per-bundle badge in the UI |
| **Portable context bundle (non-Devin agents)** | 🔶 Roadmap | Render the same context for Claude Code / Codex / etc. |
| **Enterprise auth (SSO / RBAC / secrets)** | 🔶 Roadmap | Today a local role switcher |

### What "canonical → projection" now guarantees, concretely

- **One source of truth.** Knowledge is authored in the OKF bundle (KG + meta-repo). The
  Devin Knowledge panel is labelled a *projection* — a regenerable copy, not an edit surface.
- **Provenance.** Every projected entry points back at `okf://<domain>/<concept_id>` and
  carries a content-hash + version footer, so any Devin entry is traceable to its canonical origin.
- **Drift is observable at a glance.** `dva kg okf project-status` (and the per-bundle badge)
  compares the live bundle against the recorded projection — *without* calling Devin — and flags
  `drift` (canonical changed), `unprojected` (never sent), and `orphan` (source concept deleted).
- **Regenerable.** Delete every entry in the vendor and re-project; swap the engine and the
  knowledge comes with you. The vendor holds a copy, never the original.

---

## Why this is defensible (vs. leaning on the vendor's own features)

Devin Cloud already offers Knowledge, Playbooks, a Jira-aware Sessions API, MCP, and
enterprise controls — so **competing on those loses to the vendor's roadmap.** The
durable, org-level value the vendor *cannot* own for you:

1. **Portability** — your knowledge and history are not hostage to one vendor.
2. **Cross-tool governance & audit** — one trail across Devin *and* any other agent/tool.
3. **Neutral orchestration** — route work to the best engine per task without re-platforming.

The platform is the **front door and the memory**; the vendor is the **hands**.
