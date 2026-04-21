---
name: cwow-facility-sm
description: >-
  Scrum Master persona skill for the Facility domain
  (CWOW product).
domain: cwow-facility
product: CWOW
role: sm
generated: 2026-04-13T11:39:24.475807+00:00
---

# Scrum Master Guide — Facility Domain

## Overview

Sprint management context for the **Facility** domain (CWOW product).

## Jira Configuration

- **Project Key:** CWOW
- **Dashboard:** https://jira.example.com/secure/Dashboard.jspa?selectPageId=81405

## Sprint Workflow

- **Sprint Duration:** 2 weeks (adjust per team)
- **Ceremonies:**
  - Sprint Planning (Day 1)
  - Daily Standup
  - Sprint Review (Last day)
  - Sprint Retrospective (Last day)

## Story Points

| Points | Complexity | Examples |
|--------|-----------|----------|
| 1 | Trivial | Config change, copy update |
| 2 | Small | Simple bug fix, minor feature |
| 3 | Medium | New endpoint, moderate feature |
| 5 | Large | Cross-service feature, schema change |
| 8 | Extra Large | New service, major refactor |
| 13 | Epic-level | Break into smaller stories |

## Ticket Workflow

```
Open → In Progress → In Review → QA → Done
```

- Tickets: `CWOW-<number>`
- Move to 'In Progress' when work starts
- Move to 'In Review' when PR is created
- Move to 'QA' after PR merge
- Move to 'Done' after verification

## Repositories (18 linked)

- `cwow-facility-batch-state-transition-scheduler-spanner`
- `cwow-facility-billing-exception-command-spanner`
- `cwow-facility-command-spanner`
- `cwow-facility-data-migration`
- `cwow-facility-datafix`
- `cwow-facility-model-spanner`
- `cwow-facility-pillar-synchronizer-spanner`
- `cwow-facility-product-recall-command-spanner`
- `cwow-facility-product-recall-model-spanner`
- `cwow-facility-query-spanner`
- `cwow-facility-watercheck`
- `cwow-facility-watercheck-migration`
- `cwow-facility-watercheck-scheduler`
- `cwow-facility-watercheck-trigger`
- `deprecated-------cwow-facility-batch-state-transition-spanner-------`
- `deprecated-------cwow-facility-product-ref-synchronizer-spanner-------`
- `deprecated-------cwow-facility-response-comparator-------`
- `deprecated------cwow-facility-billing-exception-query-spanner-------`
