---
name: cwow-facility-qa
description: >-
  Quality Assurance persona skill for the Facility domain
  (CWOW product).
domain: cwow-facility
product: CWOW
role: qa
generated: 2026-04-13T11:39:24.475807+00:00
---

# QA Guide — Facility Domain

## Overview

Quality assurance context for the **Facility** domain (CWOW product).

## Test Strategy

- **Unit Tests:** Required for all business logic
- **Integration Tests:** Required for API endpoints and database interactions
- **Contract Tests:** Recommended for inter-service communication
- **E2E Tests:** For critical user flows

## Repositories & Test Coverage

| Repository | Onboarded | Test Status |
|------------|-----------|-------------|
| `cwow-facility-batch-state-transition-scheduler-spanner` | — | Check CI pipeline |
| `cwow-facility-billing-exception-command-spanner` | — | Check CI pipeline |
| `cwow-facility-command-spanner` | — | Check CI pipeline |
| `cwow-facility-data-migration` | — | Check CI pipeline |
| `cwow-facility-datafix` | — | Check CI pipeline |
| `cwow-facility-model-spanner` | — | Check CI pipeline |
| `cwow-facility-pillar-synchronizer-spanner` | — | Check CI pipeline |
| `cwow-facility-product-recall-command-spanner` | — | Check CI pipeline |
| `cwow-facility-product-recall-model-spanner` | — | Check CI pipeline |
| `cwow-facility-query-spanner` | — | Check CI pipeline |
| `cwow-facility-watercheck` | — | Check CI pipeline |
| `cwow-facility-watercheck-migration` | — | Check CI pipeline |
| `cwow-facility-watercheck-scheduler` | — | Check CI pipeline |
| `cwow-facility-watercheck-trigger` | — | Check CI pipeline |
| `deprecated-------cwow-facility-batch-state-transition-spanner-------` | — | Check CI pipeline |
| `deprecated-------cwow-facility-product-ref-synchronizer-spanner-------` | — | Check CI pipeline |
| `deprecated-------cwow-facility-response-comparator-------` | — | Check CI pipeline |
| `deprecated------cwow-facility-billing-exception-query-spanner-------` | — | Check CI pipeline |

## Test Naming Conventions

- Java: `Test<ClassName>` with `@Test` methods named `test_<scenario>_<expected>`
- Python: `test_<module>.py` with `test_<scenario>` functions
- TypeScript: `<module>.test.ts` with `describe`/`it` blocks

## Quality Gates

- All tests must pass in CI before PR merge
- No new critical/blocker SonarQube issues
- Code coverage should not decrease
