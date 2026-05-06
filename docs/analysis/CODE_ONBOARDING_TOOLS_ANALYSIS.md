# Code Onboarding Tools & Business Context Ingestion

## Current Tool Stack

Your code onboarding system uses **4 complementary analysis tools** working together:

```
Code Repository
    ↓
1. ProjectAnalyzer (detector.py)
    ├─ Fast pattern matching
    ├─ File-based detection
    └─ Framework fingerprinting
    ↓
2. Gitingest Integration (parsers.py)
    ├─ Full source code content extraction
    ├─ Recursive directory scanning
    └─ Code file aggregation
    ↓
3. Graphify Analysis (graphify_integration.py)
    ├─ Function-level relationships
    ├─ Community detection (modules)
    ├─ Architectural insights
    └─ Interactive graph exports
    ↓
4. LightRAG Semantic Indexing (context_builder.py)
    ├─ Rich markdown context docs
    ├─ Semantic search indexing
    └─ Neo4j entity extraction
```

## Tool 1: ProjectAnalyzer (detector.py)

**Purpose:** Fast framework detection and project structure analysis

**What it detects:**
```python
class ProjectAnalysis:
    languages: list[str]              # Python, Java, TypeScript, etc.
    frameworks: list[str]             # FastAPI, Django, React, Spring, etc.
    build_tools: list[str]            # Maven, Gradle, npm, Webpack, etc.
    test_frameworks: list[str]        # pytest, Jest, JUnit, etc.
    dependencies: list[str]           # Full dependency list (40+ items)
    ci_cd: list[str]                  # GitHub Actions, Jenkins, CircleCI, etc.
    databases: list[str]              # PostgreSQL, MongoDB, Redis, etc.
    api_types: list[str]              # REST, GraphQL, gRPC, etc.
    has_docker: bool                  # Docker presence
    entry_points: list[str]           # main.py, index.js, app.py, etc.
    module_structure: list[str]       # Top-level directories/packages
    source_patterns: list[str]        # async/await, DI, ORM patterns, etc.
```

**Detection mechanism:**
```
┌─ Language Detection
│  └─ File glob matching: *.py, *.ts, *.java
│     └─ Language-specific analyzers active for each
│
├─ Framework Detection
│  └─ Build file fingerprinting (pom.xml, package.json, pyproject.toml)
│     └─ Import scanning (import FastAPI, from django import ...)
│     └─ Dependency matching against known frameworks
│
├─ Build Tool Detection
│  └─ BUILD_FILE_MAP: 50+ build file patterns
│
├─ Dependency Extraction
│  └─ Parse: requirements.txt, package.json, pom.xml, go.mod, Cargo.toml
│
├─ Entry Point Discovery
│  └─ Known patterns: main.py, index.ts, app.java, start.sh
│
└─ Module Structure
   └─ Top-level directory scan (first level only for speed)
```

**Speed:** < 1 second for most projects  
**Accuracy:** 90%+ for framework detection  

## Tool 2: Gitingest Integration (parsers.py)

**Purpose:** Extract complete source code content for semantic analysis

**What it does:**
```python
def parse_git_repository(
    repo_url: str,
    branch: str = "main",
    tag: str = None,
    repo_metadata: dict = None,
    detailed_analysis: bool = False,  # ← Controls Graphify usage
) → List[Document]
```

**Process:**
```
1. Clone repo (shallow clone, single branch)
   └─ git clone --depth=1 --branch=<branch> <url>

2. Scan all code files recursively
   ├─ Include: .py, .ts, .java, .go, etc.
   ├─ Exclude: node_modules, .git, __pycache__, .venv
   └─ Limit: First 50 files for performance

3. Extract file content + metadata
   ├─ Full source code (for semantic indexing)
   ├─ File paths (for structure)
   ├─ Language detection per file
   └─ Size/complexity metrics

4. Create Document objects
   ├─ doc_id: file path
   ├─ content: full source code
   ├─ metadata: {language, size, complexity, ...}
   └─ persona: "developer" (auto-detected)
```

**Output format:**
```json
{
    "doc_id": "app/api/v1/endpoints/users.py",
    "content": "<full Python source code>",
    "metadata": {
        "language": "python",
        "size_bytes": 3456,
        "complexity": "medium",
        "source": "git-repository",
        "branch": "main",
        "repo_url": "https://github.com/myteam/backend"
    },
    "persona": "developer"
}
```

## Tool 3: Graphify Analysis (graphify_integration.py)

**Purpose:** Deep code structure analysis with relationships and architectural insights

**Graphify pipeline:**
```
Project Files
    ↓
graphify.detect.collect_files()
    └─ Find all source files (50-file limit)
    ↓
graphify.extract.extract()
    ├─ Extract nodes: functions, classes, variables
    ├─ Extract edges: calls, imports, references
    └─ Return: {"nodes": [...], "edges": [...]}
    ↓
graphify.build.build_graph()
    └─ Create knowledge graph from extractions
    ↓
graphify.cluster.cluster()
    └─ Detect communities (code modules/packages)
    ↓
graphify.analyze.analyze()
    └─ Identify:
        ├─ Anomalies (unexpected relationships)
        ├─ Hotspots (high-interaction nodes)
        ├─ Opportunities (refactoring suggestions)
        └─ Architectural patterns
```

**Example output:**
```json
{
    "nodes": [
        {
            "id": "UserService.get_user",
            "type": "function",
            "file": "app/services/user.py",
            "community": "user-management",
            "centrality_score": 0.85
        }
    ],
    "edges": [
        {
            "from": "UserService.get_user",
            "to": "UserRepository.find_by_id",
            "type": "calls",
            "weight": 1.0
        },
        {
            "from": "UserController.get",
            "to": "UserService.get_user",
            "type": "calls",
            "weight": 1.0
        }
    ],
    "communities": [
        {
            "name": "user-management",
            "nodes": ["UserService", "UserRepository", "UserController"],
            "internal_edges": 5,
            "external_edges": 2
        }
    ],
    "insights": {
        "anomalies": ["UserValidator called from unexpected location"],
        "hotspots": ["UserService (degree: 8)"],
        "opportunities": ["Consider extracting UserRepository to separate module"]
    }
}
```

**When it's used:**
```bash
# Standard onboarding (Graphify OPTIONAL)
agent code onboard <repo>
    └─ Uses ProjectAnalyzer + Gitingest (fast)
    └─ Graphify skipped by default

# Deep analysis (with Graphify)
agent code onboard <repo> --detailed-analysis
    └─ Uses ProjectAnalyzer + Gitingest + Graphify
    └─ ~10-30 seconds (depending on repo size)

# Explicit control
agent code onboard <repo> --kg --skip-graphify
    └─ Uses everything EXCEPT Graphify
```

## Tool 4: LightRAG Semantic Indexing (context_builder.py)

**Purpose:** Create rich markdown context documents + semantic search capability

**What it generates:**
```markdown
# Project Context: order-api

> Auto-generated by `agent-cli code onboard --kg` on 2026-05-06T10:30:00Z
> This document is ingested into the Knowledge Graph for semantic search.

## Technology Stack

| Aspect | Detail |
|--------|--------|
| **Languages** | Python, SQL |
| **Frameworks** | FastAPI, SQLAlchemy |
| **Build Tools** | pip, poetry |
| **Databases** | PostgreSQL |
| **API Types** | REST |
| **CI/CD** | GitHub Actions |

## Architecture — Module Structure

- app/api/v1/endpoints/
- app/models/
- app/services/
- tests/integration/

## Entry Points

- app/main.py (FastAPI application)
- scripts/migrate.py (Database migrations)

## Source Code Patterns

- Async/await patterns
- Dependency injection (FastAPI depends)
- Pydantic validation
- SQLAlchemy ORM

## Dependencies

- fastapi (0.104.1)
- sqlalchemy (2.0.23)
- asyncpg (0.29.0)
- pytest (7.4.3)
- ... (40+ more)
```

**LightRAG integration:**
```
markdown doc
    ↓
Send to LightRAG REST API (http://dva-lightrag:8001)
    ↓
LightRAG processes:
├─ Entity extraction (FastAPI, PostgreSQL, async, etc.)
├─ Relationship building (uses, implements, follows)
├─ Entity community detection
└─ Semantic indexing
    ↓
Enables semantic search:
├─ "Projects using async FastAPI"
├─ "PostgreSQL patterns in our codebase"
├─ "Authentication implementations"
└─ Full graph traversal for context
```

## Where Business Context is Ingested

Business context comes from **TWO sources**:

### Source 1: Git Repository Documentation (Automatic)

```bash
agent code onboard https://github.com/myteam/backend --kg
```

**What gets parsed:**
```
Repository Root/
├─ README.md                    ← Business purpose, use cases
├─ docs/
│   ├─ ARCHITECTURE.md         ← Design decisions
│   ├─ API.md                  ← API contracts
│   ├─ DATABASE.md             ← Schema, migrations
│   └─ DEPLOYMENT.md           ← Deployment process
├─ ADR/                         ← Architecture Decision Records
│   ├─ 0001-use-fastapi.md
│   └─ 0002-async-database.md
├─ BUSINESS_RULES.md           ← Domain rules
└─ CODE_PATTERNS.md            ← Engineering practices
```

**Parsing mechanism:**
```python
# In parsers.py: parse_directory()
def parse_directory(
    path: str,
    recursive: bool = True,
) → List[Document]:
    """Scan directory for .md, .txt, .pdf files"""
    
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(('.md', '.txt', '.pdf', '.json', '.csv')):
                doc = parse_file(file)
                documents.append(doc)
```

### Source 2: Confluence/Wiki Integration (Manual)

```bash
# Register Confluence space
agent kg register-source \
    --name "order-api-docs" \
    --type confluence \
    --url https://company.atlassian.net/wiki/spaces/BACKEND

# Ingest into KG
agent kg ingest order-api-docs
```

**Confluence parsing:**
```python
# In parsers.py: parse_confluence()
def parse_confluence(
    space_key: str,
    confluence_url: str,
    token: str,
) → List[Document]:
    """Extract all pages from Confluence space"""
    
    # Uses Confluence API to:
    # ├─ List all pages in space
    # ├─ Retrieve page content
    # ├─ Extract CQL (Confluence Query Language) results
    # └─ Parse parent-child relationships
```

### Source 3: Interactive Questionnaire (Structured)

```bash
agent code onboard <repo>
    ↓ Phase 2: Structured questions
    ├─ "What is the primary business purpose?"
    ├─ "Who are the primary users?"
    ├─ "What scale requirements?"
    ├─ "What's your testing philosophy?"
    ├─ "Key business rules?"
    └─ Answers stored in .dva/questionnaire.json
```

**Questionnaire schema:**
```json
{
    "project_name": "order-api",
    "timestamp": "2026-05-06T10:30:00Z",
    "answers": {
        "business_purpose": "Real-time order management and fulfillment",
        "primary_users": "Internal sales team + customers via mobile app",
        "scale_requirements": "1M orders/day, p99 latency < 200ms",
        "testing_philosophy": "TDD with 80% minimum coverage",
        "key_business_rules": [
            "Order cannot be cancelled after payment confirmation",
            "Inventory reserved for 30 minutes after order creation",
            "High-value orders (>$10k) require manual approval"
        ]
    }
}
```

## Integration Flow Diagram

```
┌─ Code Onboarding Process
│
├─ Phase 1: Repository Analysis
│  ├─ ProjectAnalyzer.analyze_project()
│  │  └─ Detects: frameworks, languages, patterns (1 second)
│  │
│  ├─ Gitingest Integration
│  │  └─ Extract full source code content
│  │
│  └─ [OPTIONAL] Graphify Analysis
│     └─ Function relationships, communities, hotspots (10-30 sec)
│
├─ Phase 2: Interactive Questions
│  └─ Capture business context from user
│     ├─ Purpose, users, scale, testing philosophy
│     └─ Key business rules, integration points
│
├─ Phase 3: Business Context Ingestion
│  ├─ Parse repo docs (README, ADRs, specs)
│  ├─ [OPTIONAL] Ingest Confluence/Wiki
│  └─ Combine with questionnaire answers
│
├─ Phase 4: Context Building
│  ├─ Generate rich markdown context doc
│  │  ├─ Tech stack (from ProjectAnalyzer)
│  │  ├─ Architecture (from Gitingest + Graphify)
│  │  ├─ Business rules (from docs + questionnaire)
│  │  └─ Patterns (from source code analysis)
│  │
│  └─ Ingest into LightRAG
│     ├─ Entity extraction
│     ├─ Relationship building
│     └─ Semantic indexing
│
└─ Phase 5: Output
   ├─ .dva/codebase-understanding.md
   ├─ .dva/kg-context.md (for KG ingestion)
   ├─ .dva/questionnaire.json (business answers)
   ├─ .skills/project-context/SKILL.md (AI-ready context)
   └─ Neo4j/LightRAG indexed (queryable via kg-mcp)
```

## Current Implementation Status

### ✅ Fully Implemented
- **ProjectAnalyzer** (detector.py) — Fast framework detection
- **Gitingest Integration** (parsers.py) — Source code extraction
- **Graphify Integration** (graphify_integration.py) — Relationship analysis
- **LightRAG Client** (lightrag_client.py) — Semantic indexing
- **Context Builder** (context_builder.py) — Markdown doc generation
- **Neo4j Client** (neo4j_client.py) — Entity storage + relationships
- **Directory Parsing** (parsers.py) — Scan .md, .txt, .pdf files
- **Confluence Integration** (parsers.py) — Wiki ingestion
- **Questionnaire System** — Interactive business context capture

### 🟡 Partially Implemented
- **Graphify Analysis** — Available but marked as optional (performance concern)
- **KG Entity Extraction** — Basic implementation, could be enhanced
- **Business Rule Extraction** — Questionnaire-based only, could parse from code

### 🔴 Not Yet Implemented
- **LightRAG Semantic Search** — Index built but no query interface in CLI
- **Graph Visualization** — Graphify can export but not rendered in dashboard
- **KG Query Interface** — Neo4j available but no semantic query tool in CLI
- **Context Freshness** — No scheduled re-analysis of repos

## Usage Example: Full Code Onboarding

```bash
# 1. Fast analysis (ProjectAnalyzer + Gitingest)
agent code onboard https://github.com/myteam/order-api

# 2. Deep analysis (+ Graphify for architecture insights)
agent code onboard https://github.com/myteam/order-api --detailed-analysis

# 3. With business context (+ Confluence docs)
agent kg register-source \
    --name "order-api-docs" \
    --type confluence \
    --url https://company.atlassian.net/wiki/spaces/BACKEND

agent code onboard https://github.com/myteam/order-api \
    --kg \
    --confluence-space order-api-docs

# 4. Manual business context via questionnaire
agent code onboard https://github.com/myteam/order-api
    # Answers questionnaire about business purpose, users, scale

# Output: Complete project understanding
ls -la .dva/
├─ codebase-understanding.md     ← Human-readable
├─ kg-context.md                 ← For KG ingestion
├─ questionnaire.json            ← Business answers
└─ approvals/                    ← Approval checkpoints
```

## Next Steps: Leveraging KG for Better Onboarding

1. **Surface LightRAG Search** — Add `agent kg query` command
   ```bash
   agent kg query "async patterns in this codebase"
   agent kg query "PostgreSQL usage across all projects"
   ```

2. **Graphify Visualization** — Add to dashboard
   ```bash
   agent kg visualize order-api --format cytoscape
   # Opens: Agent Playground > Knowledge Graph > Architecture
   ```

3. **Automated Pattern Extraction** — Extract business rules from code
   ```python
   # Scan codebase for comments like:
   # BUSINESS_RULE: "Order cannot be cancelled after payment"
   # Extract into KG as Rule entities
   ```

4. **Context-Aware Skill Generation** — Use KG to find patterns
   ```bash
   agent skill generate fastapi-endpoint-skill \
       --kg-context order-api
   # Generates skill tailored to THIS project's async/DI patterns
   ```

5. **Multi-Project Learning** — Query similar projects
   ```bash
   # Find all projects using "async + PostgreSQL + FastAPI"
   agent kg query "tech_stack: async, postgres, fastapi"
   # Learn from how others structured similar projects
   ```

This transforms code onboarding from **text analysis** to **semantic codebase graphs** with business context integration.
