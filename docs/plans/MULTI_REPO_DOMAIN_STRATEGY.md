# Multi-Repo Domain Strategy - Brainstorm & Options

**Date**: May 6, 2026  
**Question**: How to handle domains with multiple repositories?  
**Example**: Facility domain with facility-query, facility-command, facility-events repos

---

## The Challenge

### Current Assumption
```
One domain = One repository
├─ facility-service (single repo)
└─ Code onboarding prepares this one repo
```

### Reality
```
One domain = Multiple repositories
├─ facility-query (query side - read operations)
├─ facility-command (command side - write operations)
├─ facility-events (event handling)
├─ facility-api (API gateway/facade)
└─ facility-shared (shared models, utilities)
```

### The Problem
```
When we onboard a domain, we need to:
├─ Onboard ALL repositories in the domain
├─ Share domain context across all repos
├─ Ensure consistency across repos
├─ Allow developers to work on any repo with full domain context
└─ Coordinate development across repos
```

---

## Option 1: Domain Context Repository (Recommended)

### Concept
```
Create a central domain-context repository
├─ Stores shared domain knowledge
├─ Stores shared skills
├─ Stores shared context documents
├─ Referenced by all repos in the domain
```

### Structure

```
facility-domain/                          # Central domain repo
├── .domain/
│   ├── kg-context.md                    # Shared business context
│   ├── domain-metadata.json              # Domain metadata
│   ├── architecture.md                   # Domain architecture
│   └── integration-map.md                # How repos integrate
│
├── .skills/
│   ├── shared/
│   │   ├── facility-domain-skill/       # Shared across all repos
│   │   ├── facility-api-design-skill/
│   │   └── facility-event-design-skill/
│   │
│   ├── query/                           # Query-specific skills
│   │   ├── facility-query-optimization-skill/
│   │   └── facility-cqrs-query-skill/
│   │
│   ├── command/                         # Command-specific skills
│   │   ├── facility-command-validation-skill/
│   │   └── facility-saga-pattern-skill/
│   │
│   └── events/                          # Event-specific skills
│       ├── facility-event-design-skill/
│       └── facility-event-sourcing-skill/
│
├── .templates/
│   ├── query-repo-template/             # Template for query repos
│   ├── command-repo-template/           # Template for command repos
│   └── events-repo-template/            # Template for event repos
│
└── README.md                             # Domain overview

facility-query/                           # Query repo
├── .domain-link -> ../facility-domain/   # Symlink to domain context
├── .skills/
│   ├── domain/ -> ../../facility-domain/.skills/shared/
│   ├── domain-specific/
│   │   ├── facility-query-optimization-skill/
│   │   └── facility-cqrs-query-skill/
│   └── generated/                       # From code onboarding
├── kg-context.md -> ../../facility-domain/.domain/kg-context.md
└── [query repo code]

facility-command/                        # Command repo
├── .domain-link -> ../facility-domain/  # Symlink to domain context
├── .skills/
│   ├── domain/ -> ../../facility-domain/.skills/shared/
│   ├── domain-specific/
│   │   ├── facility-command-validation-skill/
│   │   └── facility-saga-pattern-skill/
│   └── generated/                       # From code onboarding
├── kg-context.md -> ../../facility-domain/.domain/kg-context.md
└── [command repo code]

facility-events/                         # Events repo
├── .domain-link -> ../facility-domain/  # Symlink to domain context
├── .skills/
│   ├── domain/ -> ../../facility-domain/.skills/shared/
│   ├── domain-specific/
│   │   ├── facility-event-design-skill/
│   │   └── facility-event-sourcing-skill/
│   └── generated/                       # From code onboarding
├── kg-context.md -> ../../facility-domain/.domain/kg-context.md
└── [events repo code]
```

### Workflow

#### Step 1: Create Domain Context Repository
```bash
# Create central domain repository
$ keel domain create facility \
  --repos facility-query,facility-command,facility-events \
  --confluence-space FACILITY \
  --release-aware

Creates:
├─ facility-domain/ (central domain repo)
├─ .domain/kg-context.md (shared business context)
├─ .domain/domain-metadata.json (domain metadata)
├─ .domain/architecture.md (domain architecture)
├─ .skills/shared/ (shared domain skills)
├─ .skills/query/ (query-specific skills)
├─ .skills/command/ (command-specific skills)
└─ .skills/events/ (event-specific skills)
```

#### Step 2: Onboard Each Repository
```bash
# Onboard query repository
$ keel code onboard --path ./facility-query \
  --domain facility \
  --domain-context ../facility-domain

Creates:
├─ facility-query/.skills/generated/ (query-specific skills)
├─ facility-query/.keel/codebase-understanding.md
├─ facility-query/kg-context.md (symlink to domain context)
└─ facility-query/.domain-context.json (references domain)

# Onboard command repository
$ keel code onboard --path ./facility-command \
  --domain facility \
  --domain-context ../facility-domain

# Onboard events repository
$ keel code onboard --path ./facility-events \
  --domain facility \
  --domain-context ../facility-domain
```

#### Step 3: Developer Opens Any Repo in Windsurf
```bash
# Developer opens query repo
$ windsurf ./facility-query

Windsurf detects:
├─ .domain-context.json (references facility domain)
├─ kg-context.md (symlink to shared domain context)
├─ .skills/domain/ (symlink to shared domain skills)
├─ .skills/domain-specific/ (query-specific skills)
├─ .skills/generated/ (query repo-specific skills)
└─ .domain-link -> ../facility-domain/

Windsurf loads:
├─ Shared domain context (from facility-domain/)
├─ Shared domain skills (from facility-domain/)
├─ Query-specific skills
├─ Query repo context
└─ Full domain understanding
```

### Advantages
✅ Single source of truth for domain context  
✅ Shared skills across all repos  
✅ Easy to maintain consistency  
✅ Easy to see domain architecture  
✅ Developers understand how repos integrate  
✅ Symlinks keep repos lightweight  
✅ Easy to add new repos to domain  

### Disadvantages
❌ Requires symlinks (not all systems support)  
❌ Central repo must be cloned first  
❌ Dependency on central repo structure  

---

## Option 2: Distributed Domain Context (Copy-Based)

### Concept
```
Each repo gets a copy of domain context
├─ Each repo has full domain knowledge
├─ No symlinks or dependencies
├─ Repos can work independently
├─ But requires synchronization
```

### Structure

```
facility-query/
├── .domain/
│   ├── kg-context.md (copy of shared context)
│   ├── domain-metadata.json (copy)
│   ├── architecture.md (copy)
│   └── integration-map.md (copy)
├── .skills/
│   ├── domain/ (copy of shared skills)
│   ├── domain-specific/
│   └── generated/
└── [query repo code]

facility-command/
├── .domain/
│   ├── kg-context.md (copy of shared context)
│   ├── domain-metadata.json (copy)
│   ├── architecture.md (copy)
│   └── integration-map.md (copy)
├── .skills/
│   ├── domain/ (copy of shared skills)
│   ├── domain-specific/
│   └── generated/
└── [command repo code]

facility-events/
├── .domain/
│   ├── kg-context.md (copy of shared context)
│   ├── domain-metadata.json (copy)
│   ├── architecture.md (copy)
│   └── integration-map.md (copy)
├── .skills/
│   ├── domain/ (copy of shared skills)
│   ├── domain-specific/
│   └── generated/
└── [events repo code]
```

### Workflow

#### Step 1: Create Domain Context (One-Time)
```bash
# Create domain context
$ keel domain create facility \
  --repos facility-query,facility-command,facility-events \
  --confluence-space FACILITY

Creates:
├─ Shared domain context (kg-context.md)
├─ Shared domain skills
└─ Domain metadata
```

#### Step 2: Onboard Each Repository (Copies Context)
```bash
# Onboard query repository
$ keel code onboard --path ./facility-query \
  --domain facility \
  --copy-domain-context

Copies to facility-query/:
├─ .domain/kg-context.md (copy)
├─ .domain/domain-metadata.json (copy)
├─ .domain/architecture.md (copy)
├─ .skills/domain/ (copy of shared skills)
├─ .skills/generated/ (query-specific skills)
└─ .keel/codebase-understanding.md

# Onboard command repository
$ keel code onboard --path ./facility-command \
  --domain facility \
  --copy-domain-context

# Onboard events repository
$ keel code onboard --path ./facility-events \
  --domain facility \
  --copy-domain-context
```

#### Step 3: Synchronize Domain Context (Periodic)
```bash
# Update domain context across all repos
$ keel domain sync facility \
  --repos facility-query,facility-command,facility-events

Updates all repos with latest:
├─ kg-context.md
├─ domain-metadata.json
├─ architecture.md
├─ Shared domain skills
└─ Integration maps
```

### Advantages
✅ No symlinks needed  
✅ Repos can work independently  
✅ Easy to clone individual repos  
✅ No dependencies between repos  
✅ Works with any file system  

### Disadvantages
❌ Duplication of context  
❌ Synchronization complexity  
❌ Risk of context drift  
❌ Larger repo size  
❌ Manual sync required  

---

## Option 3: Monorepo with Workspaces

### Concept
```
Single monorepo with multiple workspaces
├─ All repos in one git repository
├─ Shared domain context at root
├─ Each workspace has own code
├─ Easy to manage and synchronize
```

### Structure

```
facility-domain-monorepo/
├── .domain/
│   ├── kg-context.md (shared)
│   ├── domain-metadata.json (shared)
│   ├── architecture.md (shared)
│   └── integration-map.md (shared)
│
├── .skills/
│   ├── shared/ (shared domain skills)
│   ├── query/ (query-specific skills)
│   ├── command/ (command-specific skills)
│   └── events/ (event-specific skills)
│
├── packages/
│   ├── query/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── .skills/generated/
│   │   ├── .keel/
│   │   └── package.json
│   │
│   ├── command/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── .skills/generated/
│   │   ├── .keel/
│   │   └── package.json
│   │
│   ├── events/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── .skills/generated/
│   │   ├── .keel/
│   │   └── package.json
│   │
│   └── shared/
│       ├── models/
│       ├── utils/
│       └── package.json
│
├── pnpm-workspace.yaml (or yarn workspaces)
└── README.md
```

### Workflow

#### Step 1: Create Monorepo
```bash
# Create monorepo structure
$ keel domain create facility \
  --monorepo \
  --workspaces query,command,events,shared

Creates:
├─ facility-domain-monorepo/
├─ .domain/ (shared domain context)
├─ .skills/ (shared and specific skills)
├─ packages/query/, packages/command/, packages/events/
└─ pnpm-workspace.yaml
```

#### Step 2: Onboard Each Workspace
```bash
# Onboard query workspace
$ keel code onboard --path ./facility-domain-monorepo/packages/query \
  --domain facility \
  --monorepo-root ../..

Creates:
├─ packages/query/.skills/generated/
├─ packages/query/.keel/codebase-understanding.md
└─ References shared domain context at root

# Onboard command workspace
$ keel code onboard --path ./facility-domain-monorepo/packages/command \
  --domain facility \
  --monorepo-root ../..

# Onboard events workspace
$ keel code onboard --path ./facility-domain-monorepo/packages/events \
  --domain facility \
  --monorepo-root ../..
```

#### Step 3: Developer Opens Monorepo in Windsurf
```bash
# Developer opens monorepo
$ windsurf ./facility-domain-monorepo

Windsurf detects:
├─ .domain/ (shared domain context)
├─ .skills/ (shared and specific skills)
├─ packages/query/, packages/command/, packages/events/
└─ pnpm-workspace.yaml

Windsurf understands:
├─ Shared domain context
├─ How workspaces relate
├─ Shared models and utilities
├─ Cross-workspace dependencies
└─ Full domain architecture
```

### Advantages
✅ Single source of truth  
✅ Easy to manage dependencies  
✅ Easy to synchronize context  
✅ Easy to see domain architecture  
✅ Shared utilities and models  
✅ Atomic commits across repos  
✅ Easy to refactor across repos  

### Disadvantages
❌ Larger repository  
❌ Slower clones  
❌ All repos must be cloned together  
❌ Requires workspace support  
❌ More complex CI/CD  

---

## Option 4: Domain Context Service (API-Based)

### Concept
```
Central service provides domain context
├─ REST API for domain knowledge
├─ Each repo queries context at runtime
├─ No copying or symlinking
├─ Dynamic context updates
```

### Architecture

```
Domain Context Service
├─ API endpoints:
│  ├─ GET /domains/{domain}/context
│  ├─ GET /domains/{domain}/skills
│  ├─ GET /domains/{domain}/slas
│  ├─ GET /domains/{domain}/integrations
│  └─ GET /domains/{domain}/repos
│
├─ Database:
│  ├─ Domain metadata
│  ├─ Domain context
│  ├─ Domain skills
│  └─ Repository mappings
│
└─ Admin UI:
   ├─ Manage domains
   ├─ Manage repositories
   ├─ Update context
   └─ Manage skills

facility-query/
├── .domain-config.json
│   ├─ domain: facility
│   ├─ context-service: https://domain-context.company.com
│   └─ repo-type: query
├── .skills/
│   ├── domain/ (fetched from service at startup)
│   ├── domain-specific/
│   └── generated/
└── [query repo code]

facility-command/
├── .domain-config.json
│   ├─ domain: facility
│   ├─ context-service: https://domain-context.company.com
│   └─ repo-type: command
├── .skills/
│   ├── domain/ (fetched from service at startup)
│   ├── domain-specific/
│   └── generated/
└── [command repo code]
```

### Workflow

#### Step 1: Set Up Domain Context Service
```bash
# Deploy domain context service
$ keel service deploy domain-context \
  --type api \
  --storage postgres

Service provides:
├─ REST API for domain context
├─ Admin UI for management
└─ Webhook support for updates
```

#### Step 2: Register Domain
```bash
# Register facility domain with service
$ keel domain register facility \
  --service https://domain-context.company.com \
  --repos facility-query,facility-command,facility-events \
  --confluence-space FACILITY

Service stores:
├─ Domain metadata
├─ Domain context (from KG)
├─ Domain skills
└─ Repository mappings
```

#### Step 3: Onboard Repositories
```bash
# Onboard query repository
$ keel code onboard --path ./facility-query \
  --domain facility \
  --context-service https://domain-context.company.com

Creates:
├─ .domain-config.json (service configuration)
├─ .skills/generated/ (query-specific skills)
├─ .keel/codebase-understanding.md
└─ Fetches domain context from service at startup

# Onboard command repository
$ keel code onboard --path ./facility-command \
  --domain facility \
  --context-service https://domain-context.company.com

# Onboard events repository
$ keel code onboard --path ./facility-events \
  --domain facility \
  --context-service https://domain-context.company.com
```

#### Step 4: Developer Opens Repo in Windsurf
```bash
# Developer opens query repo
$ windsurf ./facility-query

Windsurf detects:
├─ .domain-config.json (service configuration)
└─ Connects to domain context service

Windsurf fetches:
├─ Domain context (from service)
├─ Domain skills (from service)
├─ Domain metadata (from service)
└─ Repository mappings (from service)

Windsurf loads:
├─ Shared domain context
├─ Shared domain skills
├─ Query-specific skills
├─ Query repo context
└─ Full domain understanding
```

### Advantages
✅ Single source of truth  
✅ No duplication  
✅ Dynamic updates  
✅ Easy to manage  
✅ Scalable  
✅ Can serve multiple teams  
✅ Webhook support for updates  

### Disadvantages
❌ Requires service infrastructure  
❌ Network dependency  
❌ More complex setup  
❌ Service availability critical  
❌ Requires authentication  

---

## Comparison of Options

| Aspect | Option 1: Domain Repo | Option 2: Distributed | Option 3: Monorepo | Option 4: Service |
|--------|----------------------|----------------------|-------------------|-------------------|
| **Setup Complexity** | Medium | Low | High | High |
| **Synchronization** | Automatic | Manual | Automatic | Automatic |
| **Duplication** | None | High | None | None |
| **Independence** | Medium | High | Low | High |
| **Scalability** | Good | Good | Medium | Excellent |
| **Offline Support** | Yes | Yes | Yes | No |
| **Context Updates** | Automatic | Manual | Automatic | Automatic |
| **File System Support** | Symlinks | Any | Any | Any |
| **Repo Size** | Small | Large | Large | Small |
| **Learning Curve** | Medium | Low | High | High |

---

## Recommendation

### For Most Teams: Option 1 (Domain Context Repository)

```
Why:
├─ Single source of truth
├─ Automatic synchronization
├─ No duplication
├─ Works with any file system (with fallback)
├─ Easy to understand
├─ Easy to maintain
└─ Scales well

Implementation:
1. Create central facility-domain/ repository
2. Store shared context and skills there
3. Onboard each repo with reference to domain repo
4. Use symlinks where possible, fallback to copies
5. Developers understand domain architecture
```

### For Large Enterprises: Option 4 (Domain Context Service)

```
Why:
├─ Centralized management
├─ Serves multiple teams
├─ Dynamic updates
├─ Scalable
├─ No file system dependencies
└─ Webhook support

Implementation:
1. Deploy domain context service
2. Register domains with service
3. Onboard repos with service reference
4. Service provides context via API
5. Windsurf fetches context at startup
```

### For Monorepo Teams: Option 3 (Monorepo with Workspaces)

```
Why:
├─ Single repository
├─ Shared context at root
├─ Easy dependency management
├─ Atomic commits
└─ Easy refactoring

Implementation:
1. Create monorepo structure
2. Set up workspaces
3. Onboard each workspace
4. Shared context at root
5. Developers understand full domain
```

---

## Implementation Path

### Phase 1: Single Domain, Multiple Repos (Option 1)

```bash
# Create domain context repository
$ keel domain create facility \
  --repos facility-query,facility-command,facility-events \
  --confluence-space FACILITY \
  --context-repo

# Onboard each repository
$ keel code onboard --path ./facility-query --domain facility --domain-context ../facility-domain
$ keel code onboard --path ./facility-command --domain facility --domain-context ../facility-domain
$ keel code onboard --path ./facility-events --domain facility --domain-context ../facility-domain

# Developer workflow
$ windsurf ./facility-query
# Windsurf loads shared domain context + query-specific context
```

### Phase 2: Multiple Domains, Multiple Repos Each

```bash
# Create multiple domain context repositories
$ keel domain create facility --context-repo
$ keel domain create patient --context-repo
$ keel domain create order --context-repo

# Onboard repositories for each domain
$ keel code onboard --path ./facility-query --domain facility --domain-context ../facility-domain
$ keel code onboard --path ./patient-query --domain patient --domain-context ../patient-domain
$ keel code onboard --path ./order-query --domain order --domain-context ../order-domain

# Developer can work on any repo with full domain context
```

### Phase 3: Enterprise Scale (Option 4)

```bash
# Deploy domain context service
$ keel service deploy domain-context

# Register all domains
$ keel domain register facility --service https://domain-context.company.com
$ keel domain register patient --service https://domain-context.company.com
$ keel domain register order --service https://domain-context.company.com

# Onboard repositories
$ keel code onboard --path ./facility-query --domain facility --context-service https://domain-context.company.com
$ keel code onboard --path ./patient-query --domain patient --context-service https://domain-context.company.com

# Service provides context to all repos
```

---

## Summary

### The Challenge
```
One domain = Multiple repositories
Need to:
├─ Share domain context across repos
├─ Ensure consistency
├─ Allow independent development
└─ Coordinate across repos
```

### Recommended Solution (Option 1)
```
Create domain context repository
├─ Central facility-domain/ repo
├─ Stores shared context and skills
├─ Referenced by all repos
├─ Automatic synchronization
└─ Easy to maintain
```

### Developer Experience
```
Developer opens any repo in Windsurf
├─ Gets shared domain context
├─ Gets repo-specific context
├─ Gets shared domain skills
├─ Gets repo-specific skills
└─ Full domain understanding
```

### Key Points
✅ **Single source of truth** - Central domain repo  
✅ **Automatic synchronization** - No manual sync needed  
✅ **No duplication** - Symlinks or references  
✅ **Easy to understand** - Clear domain architecture  
✅ **Scalable** - Works for many repos  
✅ **Developer-friendly** - Full context in Windsurf  

**Result**: Developers can work on any repository in the domain with full domain context and understanding.
