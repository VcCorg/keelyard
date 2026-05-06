# Domain Context Git Reference Approach

**Date**: May 6, 2026  
**Approach**: Use git references to link individual repos to central domain context repo  
**Goal**: Each domain has its own repo space with common context loaded via git reference

---

## The Approach

### Core Concept

```
Each domain has:
├─ Central domain-context repository (git repo)
│  └─ Contains shared domain knowledge, skills, architecture
│
└─ Individual repositories (git repos)
   ├─ facility-query
   ├─ facility-command
   ├─ facility-events
   └─ facility-api
   
Connection:
├─ Individual repos reference central domain-context repo via git
├─ Local code can reach domain-context repo via git paths
├─ No symlinks needed (works on all systems)
├─ No duplication (git handles the reference)
└─ Always up-to-date (git pull updates context)
```

---

## Repository Structure

### Central Domain Context Repository

```
facility-domain-context/                    # Central domain repo
├── .domain/
│   ├── kg-context.md                      # Shared business context
│   ├── domain-metadata.json                # Domain metadata
│   ├── architecture.md                     # Domain architecture
│   ├── integration-map.md                  # How repos integrate
│   └── slas.json                           # Domain SLAs
│
├── .skills/
│   ├── shared/
│   │   ├── facility-domain-skill/         # Shared across all repos
│   │   │   ├── SKILL.md
│   │   │   ├── examples/
│   │   │   └── templates/
│   │   ├── facility-api-design-skill/
│   │   └── facility-event-design-skill/
│   │
│   ├── query/                             # Query-specific skills
│   │   ├── facility-query-optimization-skill/
│   │   │   ├── SKILL.md
│   │   │   └── examples/
│   │   └── facility-cqrs-query-skill/
│   │
│   ├── command/                           # Command-specific skills
│   │   ├── facility-command-validation-skill/
│   │   │   ├── SKILL.md
│   │   │   └── examples/
│   │   └── facility-saga-pattern-skill/
│   │
│   └── events/                            # Event-specific skills
│       ├── facility-event-design-skill/
│       │   ├── SKILL.md
│       │   └── examples/
│       └── facility-event-sourcing-skill/
│
├── .templates/
│   ├── query-repo-template/               # Template for query repos
│   ├── command-repo-template/             # Template for command repos
│   └── events-repo-template/              # Template for event repos
│
├── README.md                              # Domain overview
└── .gitignore

Git URL: https://github.com/company/facility-domain-context.git
```

### Individual Repository (facility-query)

```
facility-query/                            # Individual repo
├── src/
│   ├── main.py
│   ├── models/
│   ├── api/
│   └── services/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── .skills/
│   ├── domain/                           # Git submodule reference
│   │   └─ points to facility-domain-context/.skills/shared/
│   │
│   ├── domain-specific/                  # Query-specific skills
│   │   ├── facility-query-optimization-skill/
│   │   │   ├── SKILL.md
│   │   │   └── examples/
│   │   └── facility-cqrs-query-skill/
│   │
│   └── generated/                        # From code onboarding
│       ├── query-pattern-skill/
│       └── query-performance-skill/
│
├── .domain-context/                      # Git submodule reference
│   └─ points to facility-domain-context/.domain/
│
├── .domain-config.json                   # Domain configuration
│   ├─ domain: facility
│   ├─ domain-context-repo: https://github.com/company/facility-domain-context.git
│   ├─ domain-context-path: ../.domain-context/
│   ├─ domain-skills-path: ../.skills/domain/
│   └─ repo-type: query
│
├── kg-context.md                         # Reference to domain context
│   └─ Content: "See .domain-context/kg-context.md"
│
├── .gitmodules                           # Git submodule configuration
│   ├─ [submodule ".domain-context"]
│   │  path = .domain-context
│   │  url = https://github.com/company/facility-domain-context.git
│   │  branch = main
│   │
│   └─ [submodule ".skills/domain"]
│      path = .skills/domain
│      url = https://github.com/company/facility-domain-context.git
│      branch = main
│
├── pyproject.toml
└── README.md
```

---

## Git Submodule Setup

### What is a Git Submodule?

```
Git submodule allows you to:
├─ Include another git repository inside your repository
├─ Keep the submodule repository separate
├─ Update submodule independently
├─ Reference specific commits/branches
└─ Share code without duplication
```

### Setting Up Git Submodules

#### Step 1: Create Central Domain Context Repository

```bash
# Create and initialize central domain context repo
$ mkdir facility-domain-context
$ cd facility-domain-context
$ git init
$ git remote add origin https://github.com/company/facility-domain-context.git

# Create structure
$ mkdir -p .domain .skills/shared .skills/query .skills/command .skills/events
$ mkdir -p .templates

# Add content
$ echo "# Facility Domain Context" > README.md
$ echo "{\"domain\": \"facility\"}" > .domain/domain-metadata.json

# Commit and push
$ git add .
$ git commit -m "Initial domain context structure"
$ git push -u origin main
```

#### Step 2: Add Submodules to Individual Repos

```bash
# In facility-query repository
$ cd facility-query

# Add domain context as submodule
$ git submodule add \
  --branch main \
  https://github.com/company/facility-domain-context.git \
  .domain-context

# Add domain skills as submodule
$ git submodule add \
  --branch main \
  https://github.com/company/facility-domain-context.git \
  .skills/domain

# Create .gitmodules file (automatically created)
$ cat .gitmodules
[submodule ".domain-context"]
    path = .domain-context
    url = https://github.com/company/facility-domain-context.git
    branch = main
[submodule ".skills/domain"]
    path = .skills/domain
    url = https://github.com/company/facility-domain-context.git
    branch = main

# Commit submodule references
$ git add .gitmodules .domain-context .skills/domain
$ git commit -m "Add domain context as git submodules"
$ git push
```

#### Step 3: Clone Repository with Submodules

```bash
# Clone with submodules
$ git clone --recurse-submodules \
  https://github.com/company/facility-query.git

# Or initialize submodules after cloning
$ git clone https://github.com/company/facility-query.git
$ cd facility-query
$ git submodule update --init --recursive
```

---

## How Local Code Accesses Domain Context

### Via Git Paths

```python
# In facility-query/src/api/endpoints.py

import sys
from pathlib import Path

# Access domain context via git submodule path
domain_context_path = Path(__file__).parent.parent.parent / ".domain-context"

# Load domain metadata
domain_metadata_file = domain_context_path / ".domain" / "domain-metadata.json"
with open(domain_metadata_file) as f:
    domain_metadata = json.load(f)

# Load domain SLAs
slas_file = domain_context_path / ".domain" / "slas.json"
with open(slas_file) as f:
    slas = json.load(f)

# Load domain architecture
architecture_file = domain_context_path / ".domain" / "architecture.md"
with open(architecture_file) as f:
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
```

### Via Environment Variables

```python
# In facility-query/src/config.py

import os
from pathlib import Path

# Get domain context path from environment or default
domain_context_path = Path(os.getenv(
    'DOMAIN_CONTEXT_PATH',
    Path(__file__).parent.parent.parent / ".domain-context"
))

# Load domain configuration
class DomainConfig:
    def __init__(self, context_path: Path):
        self.context_path = context_path
        self.metadata = self._load_metadata()
        self.slas = self._load_slas()
        self.architecture = self._load_architecture()
    
    def _load_metadata(self):
        with open(self.context_path / ".domain" / "domain-metadata.json") as f:
            return json.load(f)
    
    def _load_slas(self):
        with open(self.context_path / ".domain" / "slas.json") as f:
            return json.load(f)
    
    def _load_architecture(self):
        with open(self.context_path / ".domain" / "architecture.md") as f:
            return f.read()

# Use in application
domain_config = DomainConfig(domain_context_path)

# Access SLAs
response_time_sla = domain_config.slas['response_time_ms']
availability_sla = domain_config.slas['availability_percent']

# Access integrations
integrations = domain_config.metadata['integrations']

# Access security policies
security_policies = domain_config.metadata['security_policies']
```

### Via Configuration Files

```yaml
# facility-query/.domain-config.yaml

domain: facility
domain_context_repo: https://github.com/company/facility-domain-context.git
domain_context_path: ./.domain-context
domain_skills_path: ./.skills/domain

# Load domain context at startup
slas:
  response_time_ms: 100
  availability_percent: 99.9

integrations:
  - FHIR API
  - OAuth 2.0

security_policies:
  - HIPAA compliance
  - AES-256 encryption

# Python code
import yaml

with open('.domain-config.yaml') as f:
    config = yaml.safe_load(f)

response_time_sla = config['slas']['response_time_ms']
integrations = config['integrations']
security_policies = config['security_policies']
```

---

## Workflow: Code Onboarding with Git References

### Step 1: Create Central Domain Context Repository

```bash
# Create domain context repo
$ dva domain create facility \
  --repos facility-query,facility-command,facility-events \
  --confluence-space FACILITY \
  --git-repo https://github.com/company/facility-domain-context.git

Creates:
├─ facility-domain-context/ (git repo)
├─ .domain/kg-context.md (shared business context)
├─ .domain/domain-metadata.json (domain metadata)
├─ .domain/slas.json (domain SLAs)
├─ .skills/shared/ (shared domain skills)
├─ .skills/query/, .skills/command/, .skills/events/
└─ Pushed to GitHub
```

### Step 2: Onboard Individual Repositories

```bash
# Onboard query repository
$ dva code onboard --path ./facility-query \
  --domain facility \
  --domain-context-repo https://github.com/company/facility-domain-context.git

Creates:
├─ .gitmodules (git submodule configuration)
├─ .domain-context/ (git submodule pointing to domain context)
├─ .skills/domain/ (git submodule pointing to shared skills)
├─ .skills/domain-specific/ (query-specific skills)
├─ .skills/generated/ (from code onboarding)
├─ .domain-config.json (domain configuration)
└─ Commits submodule references

# Onboard command repository
$ dva code onboard --path ./facility-command \
  --domain facility \
  --domain-context-repo https://github.com/company/facility-domain-context.git

# Onboard events repository
$ dva code onboard --path ./facility-events \
  --domain facility \
  --domain-context-repo https://github.com/company/facility-domain-context.git
```

### Step 3: Developer Clones Repository

```bash
# Clone with submodules
$ git clone --recurse-submodules \
  https://github.com/company/facility-query.git

# Or initialize submodules after cloning
$ git clone https://github.com/company/facility-query.git
$ cd facility-query
$ git submodule update --init --recursive

Result:
├─ .domain-context/ (populated with domain context)
├─ .skills/domain/ (populated with shared skills)
├─ Local code can access domain context via git paths
└─ Always up-to-date (git handles versioning)
```

### Step 4: Developer Opens in Windsurf

```bash
$ windsurf ./facility-query

Windsurf detects:
├─ .domain-config.json (domain configuration)
├─ .domain-context/ (git submodule with domain context)
├─ .skills/domain/ (git submodule with shared skills)
├─ .skills/domain-specific/ (query-specific skills)
├─ .skills/generated/ (query repo-specific skills)
└─ .gitmodules (submodule configuration)

Windsurf loads:
├─ Domain context from .domain-context/
├─ Shared skills from .skills/domain/
├─ Query-specific skills
├─ Query repo context
└─ Full domain understanding

Developer can:
├─ Access domain context via git paths in code
├─ Reference domain SLAs, integrations, security
├─ Use shared domain skills
├─ Develop with full domain context
└─ Update domain context via git pull
```

---

## Updating Domain Context

### Scenario 1: Update Domain Context (Central Repo)

```bash
# In facility-domain-context repository
$ cd facility-domain-context

# Update domain context
$ vim .domain/slas.json
# Change response_time_ms from 100 to 50

# Commit and push
$ git add .domain/slas.json
$ git commit -m "Update SLA: response time from 100ms to 50ms"
$ git push origin main
```

### Scenario 2: Pull Updated Context (Individual Repos)

```bash
# In facility-query repository
$ cd facility-query

# Update submodule to latest version
$ git submodule update --remote

# Or pull all submodules
$ git pull --recurse-submodules

# Verify updated context
$ cat .domain-context/.domain/slas.json
# Shows updated SLA: response_time_ms = 50

# Commit submodule update
$ git add .domain-context .skills/domain
$ git commit -m "Update domain context to latest version"
$ git push
```

### Scenario 3: Pin Specific Version

```bash
# Pin submodule to specific commit
$ cd facility-query
$ git submodule set-branch --branch v1.0.0 .domain-context
$ git add .gitmodules .domain-context
$ git commit -m "Pin domain context to v1.0.0"
$ git push

# Or pin to specific commit
$ cd .domain-context
$ git checkout abc123def456
$ cd ..
$ git add .domain-context
$ git commit -m "Pin domain context to commit abc123def456"
$ git push
```

---

## Benefits of This Approach

### For Individual Repositories

```
✅ No duplication of domain context
✅ Always up-to-date (git handles versioning)
✅ Can pin to specific versions if needed
✅ Local code can access context via git paths
✅ No symlinks (works on all systems)
✅ Git handles all synchronization
✅ Clear dependency management (.gitmodules)
✅ Easy to understand (standard git feature)
```

### For Domain Context Repository

```
✅ Single source of truth
✅ Centralized management
✅ Easy to update and maintain
✅ Version control for all changes
✅ Can serve multiple repos
✅ Clear history of changes
✅ Easy to rollback if needed
```

### For Developers

```
✅ Full domain context available locally
✅ Can access context via code (git paths)
✅ Windsurf loads all context automatically
✅ Can reference domain SLAs, integrations, security
✅ Can use shared domain skills
✅ Can update context via git pull
✅ Clear understanding of domain architecture
```

---

## Implementation Steps

### Step 1: Create Domain Context Repository Template

```bash
# Create template for domain context repos
$ mkdir -p domain-context-template
$ cd domain-context-template

# Create structure
$ mkdir -p .domain .skills/shared .skills/query .skills/command .skills/events
$ mkdir -p .templates

# Create template files
$ cat > .domain/domain-metadata.json << 'EOF'
{
  "domain": "{{DOMAIN_NAME}}",
  "description": "{{DOMAIN_DESCRIPTION}}",
  "integrations": [],
  "security_policies": [],
  "performance_requirements": {}
}
EOF

$ cat > .domain/slas.json << 'EOF'
{
  "response_time_ms": 100,
  "availability_percent": 99.9
}
EOF

$ cat > .domain/kg-context.md << 'EOF'
# {{DOMAIN_NAME}} Domain Context

## Business Context
[From Knowledge Graph]

## Integration Requirements
[From Knowledge Graph]

## Security Requirements
[From Knowledge Graph]

## Performance Requirements
[From Knowledge Graph]
EOF

$ cat > README.md << 'EOF'
# {{DOMAIN_NAME}} Domain Context

This repository contains shared domain knowledge and skills for the {{DOMAIN_NAME}} domain.

## Structure
- `.domain/` - Domain metadata, SLAs, architecture
- `.skills/` - Domain-specific skills
  - `shared/` - Shared across all repos
  - `query/` - Query-specific skills
  - `command/` - Command-specific skills
  - `events/` - Event-specific skills
- `.templates/` - Repository templates

## Usage
This repository is referenced as a git submodule in individual repositories:
- facility-query
- facility-command
- facility-events

## Updating Context
1. Update files in this repository
2. Commit and push changes
3. Individual repos pull updates via `git submodule update --remote`
EOF

# Initialize git
$ git init
$ git add .
$ git commit -m "Initial domain context template"
```

### Step 2: Create Domain Context Repository

```bash
# Use template to create facility domain context
$ dva domain create facility \
  --template domain-context-template \
  --confluence-space FACILITY \
  --git-repo https://github.com/company/facility-domain-context.git

# This:
# 1. Creates facility-domain-context/ from template
# 2. Populates .domain/ with KG context
# 3. Generates .skills/ from code analysis
# 4. Initializes git and pushes to GitHub
```

### Step 3: Onboard Individual Repositories

```bash
# For each repository
$ dva code onboard --path ./facility-query \
  --domain facility \
  --domain-context-repo https://github.com/company/facility-domain-context.git

# This:
# 1. Adds .gitmodules configuration
# 2. Adds .domain-context/ as git submodule
# 3. Adds .skills/domain/ as git submodule
# 4. Generates repo-specific skills
# 5. Creates .domain-config.json
# 6. Commits submodule references
```

### Step 4: Developer Workflow

```bash
# Clone with submodules
$ git clone --recurse-submodules \
  https://github.com/company/facility-query.git
$ cd facility-query

# Open in Windsurf
$ windsurf .

# Windsurf loads all context automatically
# Developer can access domain context via code
# Developer gets intelligent suggestions
```

---

## CLI Commands

### Domain Management

```bash
# Create domain context repository
$ dva domain create facility \
  --confluence-space FACILITY \
  --git-repo https://github.com/company/facility-domain-context.git

# List domains
$ dva domain list

# Show domain details
$ dva domain show facility

# Update domain context
$ dva domain update facility \
  --confluence-space FACILITY
```

### Code Onboarding

```bash
# Onboard repository with git submodule reference
$ dva code onboard --path ./facility-query \
  --domain facility \
  --domain-context-repo https://github.com/company/facility-domain-context.git

# Onboard with specific branch
$ dva code onboard --path ./facility-query \
  --domain facility \
  --domain-context-repo https://github.com/company/facility-domain-context.git \
  --domain-context-branch v1.0.0
```

### Submodule Management

```bash
# Update all submodules
$ git submodule update --remote

# Update specific submodule
$ git submodule update --remote .domain-context

# Pin submodule to specific version
$ git submodule set-branch --branch v1.0.0 .domain-context

# Check submodule status
$ git submodule status
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
   ├─ Stores shared domain knowledge
   ├─ Stores shared skills
   ├─ Stores architecture and SLAs
   └─ Pushed to GitHub

2. Onboard individual repositories
   ├─ Add .domain-context/ as git submodule
   ├─ Add .skills/domain/ as git submodule
   ├─ Generate repo-specific skills
   └─ Commit submodule references

3. Developer clones repository
   ├─ Clone with --recurse-submodules
   ├─ Git automatically fetches domain context
   ├─ Local code can access context via git paths
   └─ Always up-to-date

4. Developer opens in Windsurf
   ├─ Windsurf loads all context
   ├─ Developer gets intelligent suggestions
   ├─ Can reference domain SLAs, integrations, security
   └─ Full domain understanding
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
