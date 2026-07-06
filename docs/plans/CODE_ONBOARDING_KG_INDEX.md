# Code Onboarding & KG Integration - Complete Index

**Date**: May 6, 2026  
**Topic**: How KG information flows through code onboarding tools  
**Documents**: 2 comprehensive guides + source code analysis

---

## Quick Navigation

### 📚 Main Documents

1. **CODE_ONBOARDING_INTERNALS_SUMMARY.md** ⭐ START HERE
   - Visual overview of three-layer architecture
   - Data flow diagrams
   - Example skills generated
   - 10-minute read

2. **docs/plans/CODE_ONBOARDING_KG_INTEGRATION.md** 
   - Detailed technical analysis
   - Code examples and implementation details
   - Complete data flow documentation
   - 20-minute read

### 📖 Source Code References

- `agentic-cli/src/agentic_cli/kg/graphify_integration.py` - Graphify integration
- `agentic-cli/src/agentic_cli/kg/context_builder.py` - Context building
- `agentic-cli/src/agentic_cli/kg/parsers.py` - GitIngest integration
- `agentic-cli/src/agentic_cli/commands/code.py` - Code onboarding command

---

## The Three Layers

### Layer 1: GitIngest
**Purpose**: Generate repository digest

**Input**: Repository directory  
**Process**: Analyze file structure, technology stack, dependencies  
**Output**: Repository overview document

**Key Code**:
```python
from gitingest import ingest
digest = ingest(str(project_path))
```

**Document Type**: `repository_overview`

### Layer 2: Graphify
**Purpose**: Analyze code structure and relationships

**Input**: Source code files  
**Process**: Extract nodes, build graph, detect communities, analyze architecture  
**Output**: Code structure document with relationships, modules, insights

**Key Code**:
```python
import graphify
graph = graphify.build.build_graph(extractions)
graph = graphify.cluster.cluster(graph)
analysis = graphify.analyze.analyze(graph)
```

**Document Type**: `code_structure`

### Layer 3: KG Integration
**Purpose**: Map domain knowledge to code context

**Input**: Knowledge Graph (domain knowledge)  
**Process**: Query KG for SLAs, integration specs, security policies, performance requirements  
**Output**: Business context document

**Key Code**:
```python
domain_knowledge = query_kg_for_domain("cwow-facility")
# Returns: slas, integration_specs, security_policies, performance_requirements
```

**Document Type**: `business_context`

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   Code Onboarding Pipeline                      │
└─────────────────────────────────────────────────────────────────┘

Step 1: Repository Analysis
├─ Detect languages, frameworks
├─ Identify dependencies
└─ Analyze project structure

Step 2: Three-Layer Analysis
├─ GitIngest (repository digest)
├─ Graphify (code relationships)
└─ KG Query (domain knowledge)

Step 3: Build Hybrid Context
├─ Business Context (KG)
├─ Code Structure (Graphify)
└─ Repository Overview (GitIngest)

Step 4: Save kg-context.md
└─ .skills/project-context/kg-context.md

Step 5: Ingest into LightRAG
├─ Parse documents
├─ Extract entities
└─ Build relationships

Step 6: Generate Domain-Aware Skills
├─ Aware of SLAs
├─ Aware of integration patterns
├─ Aware of security constraints
└─ Aware of code architecture
```

---

## Example: Facility Service

### KG Information
```
Domain: cwow-facility
├─ SLAs
│  ├─ Response time < 100ms
│  └─ Availability > 99.9%
├─ Integration
│  ├─ FHIR API
│  └─ OAuth 2.0
├─ Security
│  ├─ HIPAA compliance
│  └─ AES-256 encryption
└─ Performance
   ├─ 10K concurrent users
   └─ DB latency < 50ms
```

### Graphify Analysis
```
Code Structure
├─ Nodes: 45 (classes, functions)
├─ Edges: 120 (relationships)
├─ Communities: 5 (code modules)
├─ God nodes: FacilityService
└─ Surprises: Circular dependency
```

### GitIngest Digest
```
Repository
├─ Language: Python 3.9+
├─ Framework: FastAPI
├─ Database: PostgreSQL
├─ Files: 120
└─ Dependencies: 25
```

### Generated kg-context.md
```markdown
# Facility Service - Codebase Understanding

## Business Context (KG)
- Response time < 100ms
- FHIR API integration
- HIPAA compliance
- 10K concurrent users

## Code Structure (Graphify)
- 45 code nodes
- 5 code modules
- FacilityService is highly connected
- Circular dependency detected

## Repository Overview (GitIngest)
- Python 3.9+ with FastAPI
- PostgreSQL database
- 120 files, 25 dependencies
```

### Generated Skills
```
1. FHIR API Handler
   - Implements OAuth 2.0 (from KG)
   - Caches for SLA compliance (from KG)
   - Uses FacilityService (from Graphify)

2. Security Validator
   - HIPAA compliance (from KG)
   - AES-256 encryption (from KG)
   - Validates all data (from code structure)

3. Performance Monitor
   - Tracks < 100ms SLA (from KG)
   - Monitors 10K users (from KG)
   - Monitors DB latency (from KG)
```

---

## Key Concepts

### Business Context (From KG)
- **SLAs**: Service level agreements (response time, availability)
- **Integration Specs**: How to integrate with other systems
- **Security Policies**: Security requirements and constraints
- **Performance Requirements**: Performance targets and limits

### Code Structure (From Graphify)
- **Nodes**: Classes, functions, modules
- **Edges**: Relationships between code elements
- **Communities**: Groups of related code (modules)
- **God Nodes**: Highly connected components (potential refactoring)
- **Surprises**: Anomalies and unexpected patterns
- **Questions**: Architectural issues to investigate

### Repository Overview (From GitIngest)
- **File Structure**: Directory tree and organization
- **Technology Stack**: Languages, frameworks, databases
- **Dependencies**: External libraries and versions
- **Build Configuration**: How to build and test

---

## How KG Information Influences Skills

### Example 1: API Handler

**KG Information**:
- Integration: FHIR API
- Authentication: OAuth 2.0
- SLA: Response time < 100ms

**Generated Skill**:
- Implements OAuth 2.0 authentication
- Adds caching for SLA compliance
- Validates FHIR format

### Example 2: Database Skill

**KG Information**:
- Performance: DB latency < 50ms
- Concurrent users: 10K
- Data consistency: Strong

**Generated Skill**:
- Implements connection pooling
- Adds query optimization
- Implements strong consistency checks

### Example 3: Security Skill

**KG Information**:
- Security: HIPAA compliance
- Encryption: AES-256
- Audit logging: Required

**Generated Skill**:
- Implements HIPAA validation
- Encrypts sensitive data
- Logs all access

---

## Implementation Details

### Building kg-context.md

```python
# Step 1: Build base context with KG data
base_content = build_kg_context_document(
    project_path,
    analysis,
    installed_skills,
    domain_knowledge  # From KG
)

# Step 2: Generate Graphify insights
graphify_insights = format_graphify_insights(graphify_data)

# Step 3: Combine all layers
hybrid_content = base_content + "\n\n" + graphify_insights

# Step 4: Save
context_path = project_path / ".skills" / "project-context" / "kg-context.md"
context_path.write_text(hybrid_content)
```

### Querying KG for Domain Knowledge

```python
# Query KG for domain knowledge
domain_knowledge = query_kg_for_domain("cwow-facility")

# Returns:
{
    "slas": [
        {"title": "Response time", "value": "< 100ms"},
        {"title": "Availability", "value": "> 99.9%"}
    ],
    "integration_specs": [
        {"title": "FHIR API", "endpoint": "https://..."},
        {"title": "OAuth 2.0", "flow": "authorization_code"}
    ],
    "security_policies": [
        {"title": "HIPAA compliance", "requirement": "required"},
        {"title": "AES-256 encryption", "scope": "data_at_rest"}
    ],
    "performance_requirements": [
        {"title": "Concurrent users", "value": "10K"},
        {"title": "DB latency", "value": "< 50ms"}
    ]
}
```

### Formatting Graphify Insights

```python
# Format Graphify analysis for inclusion in context
graphify_insights = format_graphify_insights(graphify_data)

# Includes:
# 1. Key Code Relationships
# 2. Code Modules/Communities
# 3. Architectural Insights
#    - Highly Connected Components
#    - Notable Patterns
#    - Architecture Questions
# 4. Analysis Statistics
```

---

## Command Usage

### Code Onboarding with KG

```bash
# Basic code onboarding with KG
keel code onboard --path ./facility-service --kg

# With Graphify analysis
keel code onboard --path ./facility-service --kg --graphify

# With full entity extraction
keel code onboard --path ./facility-service --kg --extract-entities

# With both Graphify and entity extraction
keel code onboard --path ./facility-service --kg --graphify --extract-entities

# With domain specification
keel code onboard --path ./facility-service --kg --domain cwow-facility
```

### Output

```
✓ Project Onboarded

Project: facility-service
Language: Python
Framework: FastAPI
Dependencies: 25 found
Skills Installed: 8
KG Context: Prepared
KG Ingested: LightRAG
Graphify Analysis: Completed
```

---

## Files Generated

### In Project Directory

```
facility-service/
└── .skills/
    └── project-context/
        ├── kg-context.md              # Hybrid context (all three layers)
        ├── graphify-graph.json        # Graphify raw data
        ├── graphify-summary.json      # Graphify summary
        └── SKILL.md                   # Skill instructions
```

### In Database

```
kg_onboarding_jobs
├─ job_id
├─ domain_id
├─ status
├─ releases_scanned
├─ documents_found
└─ rules_extracted

data_sources
├─ name
├─ location
├─ format
├─ created_at
└─ ingested_at
```

---

## Benefits

### For Code Analysis
- ✅ Understand code structure (Graphify)
- ✅ Understand repository organization (GitIngest)
- ✅ Understand business constraints (KG)

### For Skill Generation
- ✅ Skills aware of business requirements
- ✅ Skills aware of security constraints
- ✅ Skills aware of performance requirements
- ✅ Skills aware of integration patterns

### For Agents
- ✅ Agents understand code architecture
- ✅ Agents understand business context
- ✅ Agents can make better decisions
- ✅ Agents can validate against constraints

### For Development
- ✅ Generated code follows business rules
- ✅ Generated code implements security requirements
- ✅ Generated code meets performance targets
- ✅ Generated code uses correct integration patterns

---

## Next Steps

1. **Read** CODE_ONBOARDING_INTERNALS_SUMMARY.md (visual overview)
2. **Study** docs/plans/CODE_ONBOARDING_KG_INTEGRATION.md (detailed analysis)
3. **Review** source code files (implementation details)
4. **Experiment** with code onboarding on a test project
5. **Validate** that KG information is correctly included in kg-context.md

---

## Summary

Code onboarding integrates **three complementary tools**:

1. **GitIngest** - Repository digest (file structure, technology stack)
2. **Graphify** - Code structure (relationships, communities, architecture)
3. **KG Integration** - Domain knowledge (SLAs, integration specs, security, performance)

These are combined into a **hybrid kg-context.md** that includes all three perspectives.

The result is a **complete project understanding** that includes:
- Business context and constraints
- Code architecture and relationships
- Repository structure and technology

This enables **domain-aware skill generation** where skills are aware of business requirements, security constraints, and performance targets.

**Status**: ✅ COMPLETE & DOCUMENTED
