# Multi-Repo Domain Strategy - Visual Guide

**Date**: May 6, 2026  
**Focus**: How to handle domains with multiple repositories

---

## The Challenge

```
Current Assumption:
┌─────────────────────────────────┐
│  One Domain = One Repository    │
│                                 │
│  facility-service (single repo) │
└─────────────────────────────────┘

Reality:
┌─────────────────────────────────────────────────────────────┐
│         One Domain = Multiple Repositories                  │
│                                                             │
│  Facility Domain:                                           │
│  ├─ facility-query (query side - read operations)          │
│  ├─ facility-command (command side - write operations)     │
│  ├─ facility-events (event handling)                       │
│  ├─ facility-api (API gateway/facade)                      │
│  └─ facility-shared (shared models, utilities)             │
│                                                             │
│  Problem:                                                   │
│  ├─ How to share domain context across repos?              │
│  ├─ How to ensure consistency?                             │
│  ├─ How to coordinate development?                         │
│  └─ How to keep developers informed?                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Option 1: Domain Context Repository (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│              Central Domain Repository                      │
│                                                             │
│  facility-domain/                                           │
│  ├── .domain/                                               │
│  │   ├── kg-context.md (shared business context)           │
│  │   ├── domain-metadata.json (domain metadata)            │
│  │   ├── architecture.md (domain architecture)             │
│  │   └── integration-map.md (how repos integrate)          │
│  │                                                         │
│  ├── .skills/                                               │
│  │   ├── shared/ (shared domain skills)                    │
│  │   ├── query/ (query-specific skills)                    │
│  │   ├── command/ (command-specific skills)                │
│  │   └── events/ (event-specific skills)                   │
│  │                                                         │
│  └── .templates/                                            │
│      ├── query-repo-template/                              │
│      ├── command-repo-template/                            │
│      └── events-repo-template/                             │
└─────────────────────────────────────────────────────────────┘
           ↑           ↑           ↑
           │           │           │
      (symlink)   (symlink)   (symlink)
           │           │           │
           ↓           ↓           ↓
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ facility-query   │ │facility-command  │ │ facility-events  │
│                  │ │                  │ │                  │
│ .skills/         │ │ .skills/         │ │ .skills/         │
│ ├─ domain/ ──────┼─┼──→ shared skills │ │ ├─ domain/ ──────┼─┼──→ shared skills
│ ├─ domain-       │ │ ├─ domain-       │ │ ├─ domain-       │
│ │  specific/     │ │ │  specific/     │ │ │  specific/     │
│ └─ generated/    │ │ └─ generated/    │ │ └─ generated/    │
│                  │ │                  │ │                  │
│ kg-context.md ───┼─┼──→ shared context│ │ kg-context.md ───┼─┼──→ shared context
│                  │ │                  │ │                  │
│ [query code]     │ │ [command code]   │ │ [events code]    │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Workflow

```
Step 1: Create Domain Context Repository
┌─────────────────────────────────────────────────────────────┐
│ $ dva domain create facility \                              │
│   --repos facility-query,facility-command,facility-events \ │
│   --confluence-space FACILITY \                             │
│   --context-repo                                            │
│                                                             │
│ Creates:                                                    │
│ ├─ facility-domain/ (central repo)                          │
│ ├─ .domain/kg-context.md (shared business context)         │
│ ├─ .skills/shared/ (shared domain skills)                  │
│ └─ .skills/query/, .skills/command/, .skills/events/      │
└─────────────────────────────────────────────────────────────┘

Step 2: Onboard Each Repository
┌─────────────────────────────────────────────────────────────┐
│ $ dva code onboard --path ./facility-query \                │
│   --domain facility \                                       │
│   --domain-context ../facility-domain                       │
│                                                             │
│ $ dva code onboard --path ./facility-command \              │
│   --domain facility \                                       │
│   --domain-context ../facility-domain                       │
│                                                             │
│ $ dva code onboard --path ./facility-events \               │
│   --domain facility \                                       │
│   --domain-context ../facility-domain                       │
│                                                             │
│ Creates in each repo:                                       │
│ ├─ .skills/generated/ (repo-specific skills)               │
│ ├─ .skills/domain/ → symlink to shared skills              │
│ ├─ kg-context.md → symlink to shared context               │
│ └─ .dva/codebase-understanding.md (repo-specific)          │
└─────────────────────────────────────────────────────────────┘

Step 3: Developer Opens Any Repo in Windsurf
┌─────────────────────────────────────────────────────────────┐
│ $ windsurf ./facility-query                                 │
│                                                             │
│ Windsurf detects:                                           │
│ ├─ .domain-context.json (references facility domain)       │
│ ├─ kg-context.md (symlink to shared context)               │
│ ├─ .skills/domain/ (symlink to shared skills)              │
│ ├─ .skills/domain-specific/ (query-specific skills)        │
│ ├─ .skills/generated/ (query repo-specific skills)         │
│ └─ .domain-link → ../facility-domain/                      │
│                                                             │
│ Windsurf loads:                                             │
│ ├─ Shared domain context (from facility-domain/)           │
│ ├─ Shared domain skills (from facility-domain/)            │
│ ├─ Query-specific skills                                   │
│ ├─ Query repo context                                      │
│ └─ Full domain understanding                               │
└─────────────────────────────────────────────────────────────┘
```

### Advantages & Disadvantages

```
✅ Advantages:
├─ Single source of truth
├─ Automatic synchronization
├─ No duplication
├─ Easy to maintain consistency
├─ Easy to see domain architecture
├─ Developers understand how repos integrate
├─ Symlinks keep repos lightweight
└─ Easy to add new repos to domain

❌ Disadvantages:
├─ Requires symlink support
├─ Central repo must be cloned first
└─ Dependency on central repo structure
```

---

## Option 2: Distributed Domain Context (Copy-Based)

```
┌──────────────────────────────────────────────────────────────┐
│ Each Repo Gets a Copy of Domain Context                     │
│                                                              │
│ facility-query/                facility-command/             │
│ ├─ .domain/                    ├─ .domain/                  │
│ │  ├─ kg-context.md (copy)     │  ├─ kg-context.md (copy)  │
│ │  ├─ domain-metadata.json     │  ├─ domain-metadata.json  │
│ │  └─ architecture.md          │  └─ architecture.md       │
│ ├─ .skills/                    ├─ .skills/                 │
│ │  ├─ domain/ (copy)           │  ├─ domain/ (copy)        │
│ │  ├─ domain-specific/         │  ├─ domain-specific/      │
│ │  └─ generated/               │  └─ generated/            │
│ └─ [query code]                └─ [command code]           │
│                                                              │
│ facility-events/                                             │
│ ├─ .domain/                                                  │
│ │  ├─ kg-context.md (copy)                                  │
│ │  ├─ domain-metadata.json                                  │
│ │  └─ architecture.md                                       │
│ ├─ .skills/                                                  │
│ │  ├─ domain/ (copy)                                        │
│ │  ├─ domain-specific/                                      │
│ │  └─ generated/                                            │
│ └─ [events code]                                             │
└──────────────────────────────────────────────────────────────┘

Workflow:
1. Create domain context (one-time)
2. Onboard each repo (copies context)
3. Periodic sync to update all repos

✅ Advantages:
├─ No symlinks needed
├─ Repos can work independently
├─ Easy to clone individual repos
└─ Works with any file system

❌ Disadvantages:
├─ Duplication of context
├─ Synchronization complexity
├─ Risk of context drift
├─ Larger repo size
└─ Manual sync required
```

---

## Option 3: Monorepo with Workspaces

```
┌──────────────────────────────────────────────────────────────┐
│         Single Monorepo with Multiple Workspaces            │
│                                                              │
│  facility-domain-monorepo/                                   │
│  ├── .domain/                                                │
│  │   ├── kg-context.md (shared)                             │
│  │   ├── domain-metadata.json (shared)                      │
│  │   └── architecture.md (shared)                           │
│  │                                                          │
│  ├── .skills/                                                │
│  │   ├── shared/ (shared domain skills)                     │
│  │   ├── query/ (query-specific skills)                     │
│  │   ├── command/ (command-specific skills)                 │
│  │   └── events/ (event-specific skills)                    │
│  │                                                          │
│  ├── packages/                                               │
│  │   ├── query/                                              │
│  │   │   ├── src/                                            │
│  │   │   ├── tests/                                          │
│  │   │   ├── .skills/generated/                             │
│  │   │   └── package.json                                    │
│  │   │                                                      │
│  │   ├── command/                                            │
│  │   │   ├── src/                                            │
│  │   │   ├── tests/                                          │
│  │   │   ├── .skills/generated/                             │
│  │   │   └── package.json                                    │
│  │   │                                                      │
│  │   ├── events/                                             │
│  │   │   ├── src/                                            │
│  │   │   ├── tests/                                          │
│  │   │   ├── .skills/generated/                             │
│  │   │   └── package.json                                    │
│  │   │                                                      │
│  │   └── shared/                                             │
│  │       ├── models/                                         │
│  │       ├── utils/                                          │
│  │       └── package.json                                    │
│  │                                                          │
│  └── pnpm-workspace.yaml                                     │
└──────────────────────────────────────────────────────────────┘

Workflow:
1. Create monorepo structure
2. Onboard each workspace
3. Shared context at root

✅ Advantages:
├─ Single source of truth
├─ Easy to manage dependencies
├─ Easy to synchronize context
├─ Shared utilities and models
├─ Atomic commits across repos
└─ Easy to refactor across repos

❌ Disadvantages:
├─ Larger repository
├─ Slower clones
├─ All repos must be cloned together
├─ Requires workspace support
└─ More complex CI/CD
```

---

## Option 4: Domain Context Service (API-Based)

```
┌──────────────────────────────────────────────────────────────┐
│          Central Service Provides Domain Context             │
│                                                              │
│  Domain Context Service                                      │
│  ├─ REST API:                                                │
│  │  ├─ GET /domains/{domain}/context                        │
│  │  ├─ GET /domains/{domain}/skills                         │
│  │  ├─ GET /domains/{domain}/slas                           │
│  │  └─ GET /domains/{domain}/repos                          │
│  │                                                          │
│  ├─ Database:                                                │
│  │  ├─ Domain metadata                                       │
│  │  ├─ Domain context                                        │
│  │  ├─ Domain skills                                         │
│  │  └─ Repository mappings                                   │
│  │                                                          │
│  └─ Admin UI:                                                │
│     ├─ Manage domains                                        │
│     ├─ Manage repositories                                   │
│     └─ Update context                                        │
└──────────────────────────────────────────────────────────────┘
           ↑           ↑           ↑
           │           │           │
        (API)       (API)       (API)
           │           │           │
           ↓           ↓           ↓
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ facility-query   │ │facility-command  │ │ facility-events  │
│                  │ │                  │ │                  │
│ .domain-config   │ │ .domain-config   │ │ .domain-config   │
│ ├─ domain:       │ │ ├─ domain:       │ │ ├─ domain:       │
│ │  facility      │ │ │  facility      │ │ │  facility      │
│ └─ service:      │ │ └─ service:      │ │ └─ service:      │
│    https://...   │ │    https://...   │ │    https://...   │
│                  │ │                  │ │                  │
│ .skills/         │ │ .skills/         │ │ .skills/         │
│ ├─ domain/       │ │ ├─ domain/       │ │ ├─ domain/       │
│ │  (fetched)     │ │ │  (fetched)     │ │ │  (fetched)     │
│ ├─ domain-       │ │ ├─ domain-       │ │ ├─ domain-       │
│ │  specific/     │ │ │  specific/     │ │ │  specific/     │
│ └─ generated/    │ │ └─ generated/    │ │ └─ generated/    │
│                  │ │                  │ │                  │
│ [query code]     │ │ [command code]   │ │ [events code]    │
└──────────────────┘ └──────────────────┘ └──────────────────┘

Workflow:
1. Deploy domain context service
2. Register domains with service
3. Onboard repos with service reference
4. Service provides context via API

✅ Advantages:
├─ Single source of truth
├─ No duplication
├─ Dynamic updates
├─ Easy to manage
├─ Scalable
└─ Webhook support

❌ Disadvantages:
├─ Requires service infrastructure
├─ Network dependency
├─ More complex setup
├─ Service availability critical
└─ Requires authentication
```

---

## Comparison Table

```
┌─────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Aspect          │ Option 1:    │ Option 2:    │ Option 3:    │ Option 4:    │
│                 │ Domain Repo  │ Distributed  │ Monorepo     │ Service      │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Setup           │ Medium       │ Low          │ High         │ High         │
│ Complexity      │              │              │              │              │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Synchronization │ Automatic    │ Manual       │ Automatic    │ Automatic    │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Duplication     │ None         │ High         │ None         │ None         │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Independence    │ Medium       │ High         │ Low          │ High         │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Scalability     │ Good         │ Good         │ Medium       │ Excellent    │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Offline Support │ Yes          │ Yes          │ Yes          │ No           │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Context Updates │ Automatic    │ Manual       │ Automatic    │ Automatic    │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Repo Size       │ Small        │ Large        │ Large        │ Small        │
├─────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Learning Curve  │ Medium       │ Low          │ High         │ High         │
└─────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘

RECOMMENDED:
├─ Most Teams: Option 1 (Domain Context Repository)
├─ Large Enterprises: Option 4 (Domain Context Service)
└─ Monorepo Teams: Option 3 (Monorepo with Workspaces)
```

---

## Recommended: Option 1 (Domain Context Repository)

```
Why Option 1?
├─ Single source of truth
├─ Automatic synchronization
├─ No duplication
├─ Works with any file system
├─ Easy to understand
├─ Easy to maintain
└─ Scales well

Implementation:
┌─────────────────────────────────────────────────────────────┐
│ 1. Create central facility-domain/ repository               │
│ 2. Store shared context and skills there                    │
│ 3. Onboard each repo with reference to domain repo          │
│ 4. Use symlinks where possible, fallback to copies          │
│ 5. Developers understand domain architecture                │
└─────────────────────────────────────────────────────────────┘

Developer Experience:
┌─────────────────────────────────────────────────────────────┐
│ Developer opens facility-query in Windsurf                  │
│                                                             │
│ Windsurf loads:                                             │
│ ├─ Shared domain context (from facility-domain/)           │
│ ├─ Shared domain skills (from facility-domain/)            │
│ ├─ Query-specific skills                                   │
│ ├─ Query repo context                                      │
│ └─ Full domain understanding                               │
│                                                             │
│ Developer gets:                                             │
│ ├─ Full context for facility domain                        │
│ ├─ Understanding of how repos integrate                    │
│ ├─ Intelligent suggestions for query repo                  │
│ └─ Ability to work on any repo in the domain               │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary

### The Challenge
```
One domain = Multiple repositories
├─ facility-query (query side)
├─ facility-command (command side)
├─ facility-events (event handling)
├─ facility-api (API gateway)
└─ facility-shared (shared models)

Need to:
├─ Share domain context across repos
├─ Ensure consistency
├─ Allow independent development
└─ Coordinate across repos
```

### Recommended Solution
```
Option 1: Domain Context Repository
├─ Create central facility-domain/ repo
├─ Store shared context and skills there
├─ Each repo references the domain repo
├─ Use symlinks for automatic synchronization
└─ Developers get full domain context
```

### Key Points
✅ **Single source of truth** - Central domain repo  
✅ **Automatic synchronization** - No manual sync needed  
✅ **No duplication** - Symlinks or references  
✅ **Easy to understand** - Clear domain architecture  
✅ **Scalable** - Works for many repos  
✅ **Developer-friendly** - Full context in Windsurf  

**Result**: Developers can work on any repository in the domain with full domain context and understanding.
