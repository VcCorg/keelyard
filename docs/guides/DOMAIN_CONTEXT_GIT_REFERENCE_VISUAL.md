# Domain Context Git Reference - Visual Guide

**Date**: May 6, 2026  
**Approach**: Use git submodules to link individual repos to central domain context repo

---

## The Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│         Central Domain Context Repository (Git Repo)            │
│                                                                  │
│  facility-domain-context/                                        │
│  ├── .domain/                                                    │
│  │   ├── kg-context.md (shared business context)               │
│  │   ├── domain-metadata.json (domain metadata)                │
│  │   ├── slas.json (domain SLAs)                               │
│  │   ├── architecture.md (domain architecture)                 │
│  │   └── integration-map.md (how repos integrate)              │
│  │                                                              │
│  ├── .skills/                                                   │
│  │   ├── shared/ (shared domain skills)                        │
│  │   ├── query/ (query-specific skills)                        │
│  │   ├── command/ (command-specific skills)                    │
│  │   └── events/ (event-specific skills)                       │
│  │                                                              │
│  ├── .templates/ (repo templates)                               │
│  └── README.md                                                   │
│                                                                  │
│  Git URL: https://github.com/company/facility-domain-context   │
└──────────────────────────────────────────────────────────────────┘
           ↑                    ↑                    ↑
           │                    │                    │
      (git submodule)      (git submodule)      (git submodule)
           │                    │                    │
           ↓                    ↓                    ↓
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│  facility-query      │ │ facility-command     │ │ facility-events      │
│  (Git Repo)          │ │ (Git Repo)           │ │ (Git Repo)           │
│                      │ │                      │ │                      │
│ .domain-context/ ────┼─┼──→ submodule ref    │ │ .domain-context/ ────┼─┼──→ submodule ref
│ .skills/domain/ ─────┼─┼──→ submodule ref    │ │ .skills/domain/ ─────┼─┼──→ submodule ref
│                      │ │                      │ │                      │
│ .skills/             │ │ .skills/             │ │ .skills/             │
│ ├─ domain-specific/  │ │ ├─ domain-specific/  │ │ ├─ domain-specific/  │
│ └─ generated/        │ │ └─ generated/        │ │ └─ generated/        │
│                      │ │                      │ │                      │
│ .domain-config.json  │ │ .domain-config.json  │ │ .domain-config.json  │
│ .gitmodules          │ │ .gitmodules          │ │ .gitmodules          │
│                      │ │                      │ │                      │
│ [query code]         │ │ [command code]       │ │ [events code]        │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

---

## Git Submodule Setup

```
┌──────────────────────────────────────────────────────────────────┐
│              Step 1: Create Domain Context Repository            │
│                                                                  │
│  $ keel domain create facility \                                  │
│    --confluence-space FACILITY \                                 │
│    --git-repo https://github.com/company/facility-domain-context │
│                                                                  │
│  Creates:                                                        │
│  ├─ facility-domain-context/ (git repo)                         │
│  ├─ .domain/ (shared business context)                          │
│  ├─ .skills/ (shared and specific skills)                       │
│  └─ Pushed to GitHub                                             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│         Step 2: Onboard Individual Repositories                  │
│                                                                  │
│  $ keel code onboard --path ./facility-query \                    │
│    --domain facility \                                           │
│    --domain-context-repo https://github.com/company/facility-domain-context
│                                                                  │
│  Creates:                                                        │
│  ├─ .gitmodules (git submodule configuration)                   │
│  ├─ .domain-context/ (git submodule pointing to domain context) │
│  ├─ .skills/domain/ (git submodule pointing to shared skills)   │
│  ├─ .skills/domain-specific/ (repo-specific skills)             │
│  ├─ .skills/generated/ (from code onboarding)                   │
│  ├─ .domain-config.json (domain configuration)                  │
│  └─ Commits submodule references                                │
│                                                                  │
│  Repeat for:                                                     │
│  ├─ facility-command                                             │
│  └─ facility-events                                              │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│           Step 3: Developer Clones Repository                    │
│                                                                  │
│  $ git clone --recurse-submodules \                              │
│    https://github.com/company/facility-query.git                │
│                                                                  │
│  Or:                                                             │
│  $ git clone https://github.com/company/facility-query.git       │
│  $ cd facility-query                                             │
│  $ git submodule update --init --recursive                       │
│                                                                  │
│  Result:                                                         │
│  ├─ .domain-context/ (populated with domain context)            │
│  ├─ .skills/domain/ (populated with shared skills)              │
│  ├─ Local code can access domain context via git paths          │
│  └─ Always up-to-date (git handles versioning)                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│         Step 4: Developer Opens in Windsurf                      │
│                                                                  │
│  $ windsurf ./facility-query                                     │
│                                                                  │
│  Windsurf detects:                                               │
│  ├─ .domain-config.json (domain configuration)                  │
│  ├─ .domain-context/ (git submodule with domain context)        │
│  ├─ .skills/domain/ (git submodule with shared skills)          │
│  ├─ .skills/domain-specific/ (repo-specific skills)             │
│  ├─ .skills/generated/ (repo-specific skills)                   │
│  └─ .gitmodules (submodule configuration)                       │
│                                                                  │
│  Windsurf loads:                                                 │
│  ├─ Domain context from .domain-context/                        │
│  ├─ Shared skills from .skills/domain/                          │
│  ├─ Query-specific skills                                       │
│  ├─ Query repo context                                          │
│  └─ Full domain understanding                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## How Local Code Accesses Domain Context

### Via Git Paths

```python
# In facility-query/src/api/endpoints.py

from pathlib import Path
import json

# Access domain context via git submodule path
domain_context_path = Path(__file__).parent.parent.parent / ".domain-context"

# Load domain metadata
with open(domain_context_path / ".domain" / "domain-metadata.json") as f:
    domain_metadata = json.load(f)

# Load domain SLAs
with open(domain_context_path / ".domain" / "slas.json") as f:
    slas = json.load(f)

# Load domain architecture
with open(domain_context_path / ".domain" / "architecture.md") as f:
    architecture = f.read()

# Use domain context in code
@router.get("/api/v1/patients/{patient_id}")
async def get_patient(patient_id: str):
    """
    Get patient data.
    
    SLA: Response time < {slas['response_time_ms']}ms
    Integration: {domain_metadata['integrations']}
    Security: {domain_metadata['security_policies']}
    """
    # Implementation
    if response_time > slas['response_time_ms']:
        logger.warning(f"SLA violation: response time {response_time}ms > {slas['response_time_ms']}ms")
```

### Via Configuration Files

```yaml
# facility-query/.domain-config.yaml

domain: facility
domain_context_repo: https://github.com/company/facility-domain-context.git
domain_context_path: ./.domain-context
domain_skills_path: ./.skills/domain

slas:
  response_time_ms: 100
  availability_percent: 99.9

integrations:
  - FHIR API
  - OAuth 2.0

security_policies:
  - HIPAA compliance
  - AES-256 encryption
```

```python
# Python code
import yaml

with open('.domain-config.yaml') as f:
    config = yaml.safe_load(f)

response_time_sla = config['slas']['response_time_ms']
integrations = config['integrations']
security_policies = config['security_policies']
```

---

## Updating Domain Context

```
┌──────────────────────────────────────────────────────────────────┐
│        Scenario 1: Update Domain Context (Central Repo)          │
│                                                                  │
│  $ cd facility-domain-context                                    │
│  $ vim .domain/slas.json                                         │
│  # Change response_time_ms from 100 to 50                        │
│                                                                  │
│  $ git add .domain/slas.json                                     │
│  $ git commit -m "Update SLA: response time from 100ms to 50ms"  │
│  $ git push origin main                                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│      Scenario 2: Pull Updated Context (Individual Repos)         │
│                                                                  │
│  $ cd facility-query                                             │
│                                                                  │
│  # Update submodule to latest version                            │
│  $ git submodule update --remote                                 │
│                                                                  │
│  # Or pull all submodules                                        │
│  $ git pull --recurse-submodules                                 │
│                                                                  │
│  # Verify updated context                                        │
│  $ cat .domain-context/.domain/slas.json                         │
│  # Shows updated SLA: response_time_ms = 50                      │
│                                                                  │
│  # Commit submodule update                                       │
│  $ git add .domain-context .skills/domain                        │
│  $ git commit -m "Update domain context to latest version"       │
│  $ git push                                                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│       Scenario 3: Pin Specific Version (Optional)                │
│                                                                  │
│  # Pin submodule to specific version tag                         │
│  $ cd facility-query                                             │
│  $ git submodule set-branch --branch v1.0.0 .domain-context     │
│  $ git add .gitmodules .domain-context                           │
│  $ git commit -m "Pin domain context to v1.0.0"                  │
│  $ git push                                                      │
│                                                                  │
│  # Or pin to specific commit                                     │
│  $ cd .domain-context                                            │
│  $ git checkout abc123def456                                     │
│  $ cd ..                                                         │
│  $ git add .domain-context                                       │
│  $ git commit -m "Pin domain context to commit abc123def456"     │
│  $ git push                                                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Git Submodule Commands

```bash
# Add submodule to repository
$ git submodule add \
  --branch main \
  https://github.com/company/facility-domain-context.git \
  .domain-context

# Clone with submodules
$ git clone --recurse-submodules \
  https://github.com/company/facility-query.git

# Initialize submodules after cloning
$ git submodule update --init --recursive

# Update all submodules to latest
$ git submodule update --remote

# Update specific submodule
$ git submodule update --remote .domain-context

# Check submodule status
$ git submodule status

# Pin submodule to specific branch
$ git submodule set-branch --branch v1.0.0 .domain-context

# View submodule configuration
$ cat .gitmodules
```

---

## Benefits of This Approach

```
✅ No Duplication
   ├─ Git handles references
   ├─ Single source of truth
   └─ No copying needed

✅ Always Up-to-Date
   ├─ Git manages versioning
   ├─ Pull updates via git submodule update --remote
   └─ Can pin to specific versions if needed

✅ Works on All Systems
   ├─ No symlinks (works on Windows, Mac, Linux)
   ├─ Standard git feature
   └─ No special setup needed

✅ Local Access
   ├─ Code can access context via git paths
   ├─ Load domain metadata, SLAs, integrations
   └─ Reference security policies in code

✅ Single Source of Truth
   ├─ Central domain-context repository
   ├─ All repos reference same source
   └─ Easy to maintain consistency

✅ Developer-Friendly
   ├─ Full context in Windsurf
   ├─ Clear understanding of domain
   ├─ Can reference domain requirements
   └─ Intelligent suggestions
```

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Create Central Domain Context Repository                     │
│    $ keel domain create facility --git-repo https://...          │
│    Result: facility-domain-context/ (git repo)                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Onboard Individual Repositories                              │
│    $ keel code onboard --path ./facility-query \                 │
│      --domain-context-repo https://...                          │
│    Result: facility-query/ with git submodules                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Developer Clones Repository                                  │
│    $ git clone --recurse-submodules https://...                 │
│    Result: .domain-context/ populated locally                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Developer Opens in Windsurf                                  │
│    $ windsurf ./facility-query                                  │
│    Result: Full domain context available                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Developer Develops with Full Context                         │
│    ├─ Access domain context via git paths
│    ├─ Reference domain SLAs, integrations, security
│    ├─ Use shared domain skills
│    └─ Get intelligent suggestions from Windsurf
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary

### The Approach

```
Each domain has:
├─ Central domain-context repository (git repo)
│  └─ Contains shared domain knowledge, skills, architecture
│
└─ Individual repositories (git repos)
   ├─ facility-query (with git submodule reference)
   ├─ facility-command (with git submodule reference)
   ├─ facility-events (with git submodule reference)
   └─ facility-api (with git submodule reference)
```

### How It Works

```
1. Create central domain-context repository
2. Onboard individual repositories (adds git submodules)
3. Developer clones with --recurse-submodules
4. Git automatically fetches domain context
5. Local code can access context via git paths
6. Developer opens in Windsurf
7. Windsurf loads all context
8. Developer develops with full domain understanding
```

### Key Benefits

✅ **No duplication** - Git handles references  
✅ **Always up-to-date** - Git manages versioning  
✅ **Works on all systems** - No symlinks needed  
✅ **Local access** - Code can access context via git paths  
✅ **Single source of truth** - Central domain repo  
✅ **Easy to understand** - Standard git feature  
✅ **Developer-friendly** - Full context in Windsurf  

**Result**: Each domain has its own repo space with shared context loaded via git reference, allowing local code to always reach the domain context repo for common context via git paths.
