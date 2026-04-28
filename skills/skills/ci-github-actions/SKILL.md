---
name: ci-github-actions
description: >-
  GitHub Actions workflow syntax, jobs, steps, actions marketplace.
  Use this skill when working with GitHub Actions CI/CD.
---

# GitHub Actions CI/CD

## Workflow Structure

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm test
      - run: npm run build

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying..."
```

## Key Concepts

- **`on`**: Trigger events (push, pull_request, schedule, workflow_dispatch)
- **`jobs`**: Parallel by default; use `needs` for dependencies
- **`steps`**: Sequential within a job; `uses` for actions, `run` for shell
- **`env`**: Workflow, job, or step-level environment variables
- **`secrets`**: `${{ secrets.MY_SECRET }}` — from repo/org settings
- **`matrix`**: Run across multiple configurations

## Matrix Strategy

```yaml
jobs:
  test:
    strategy:
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
```

## Guidelines

- Pin action versions to SHA or major version (`@v4`)
- Use `actions/cache` or built-in caching for dependencies
- Set minimal `permissions` (principle of least privilege)
- Use `concurrency` to cancel redundant runs
- Use reusable workflows for shared CI logic
- Store secrets in GitHub Settings, never in workflow files
- Use `if:` conditions to skip unnecessary steps
