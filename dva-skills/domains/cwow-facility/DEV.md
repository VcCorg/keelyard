---
name: cwow-facility-dev
description: >-
  Developer persona skill for the Facility domain
  (CWOW product).
domain: cwow-facility
product: CWOW
role: dev
generated: 2026-04-13T11:39:24.475807+00:00
---

# Developer Guide — Facility Domain

## Overview

This skill provides developer context for the **Facility** domain in the **CWOW** product.

## Repositories

### `cwow-facility-batch-state-transition-scheduler-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-batch-state-transition-scheduler-spanner.git`

### `cwow-facility-billing-exception-command-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-billing-exception-command-spanner.git`

### `cwow-facility-command-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-command-spanner.git`

### `cwow-facility-data-migration`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-data-migration.git`

### `cwow-facility-datafix`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-datafix.git`

### `cwow-facility-model-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-model-spanner.git`

### `cwow-facility-pillar-synchronizer-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-pillar-synchronizer-spanner.git`

### `cwow-facility-product-recall-command-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-product-recall-command-spanner.git`

### `cwow-facility-product-recall-model-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-product-recall-model-spanner.git`

### `cwow-facility-query-spanner`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-query-spanner.git`

### `cwow-facility-watercheck`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-watercheck.git`

### `cwow-facility-watercheck-migration`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-watercheck-migration.git`

### `cwow-facility-watercheck-scheduler`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-watercheck-scheduler.git`

### `cwow-facility-watercheck-trigger`

- **Clone:** `https://bitbucket.example.com/scm/cgf/cwow-facility-watercheck-trigger.git`

### `deprecated-------cwow-facility-batch-state-transition-spanner-------`

- **Clone:** `https://bitbucket.example.com/scm/cgf/deprecated-------cwow-facility-batch-state-transition-spanner-------.git`

### `deprecated-------cwow-facility-product-ref-synchronizer-spanner-------`

- **Clone:** `https://bitbucket.example.com/scm/cgf/deprecated-------cwow-facility-product-ref-synchronizer-spanner-------.git`

### `deprecated-------cwow-facility-response-comparator-------`

- **Clone:** `https://bitbucket.example.com/scm/cgf/deprecated-------cwow-facility-response-comparator-------.git`

### `deprecated------cwow-facility-billing-exception-query-spanner-------`

- **Clone:** `https://bitbucket.example.com/scm/cgf/deprecated------cwow-facility-billing-exception-query-spanner-------.git`

## Code Conventions

<!-- Auto-populated when repos are onboarded via 'dva code onboard' -->
- Follow existing patterns in each repository
- Use the project's established build tool and dependency manager
- Prefer constructor injection over field injection (Spring Boot)

## Pull Request Conventions

- Branch naming: `feature/CWOW-<ticket-number>-<short-description>`
- PR title: `CWOW-<number>: <description>`
- All PRs require at least one reviewer approval
- CI must pass before merge

## Build & Deploy

- **Bitbucket Project:** https://bitbucket.example.com/projects/CGF
- Check each repo's `README.md` or `Makefile` for build instructions
- CI/CD pipelines are defined per-repo
