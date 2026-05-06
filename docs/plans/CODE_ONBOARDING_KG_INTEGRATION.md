# Code Onboarding & KG Integration - Internals

**Date**: May 6, 2026  
**Focus**: How KG information maps into graphify and git-inject tools

---

## Overview

Code onboarding uses **three complementary tools** to build comprehensive project context:

1. **GitIngest** - Repository digest (file structure, overview)
2. **Graphify** - Code structure analysis (relationships, communities, architecture)
3. **KG Integration** - Domain knowledge mapping (business rules, SLAs, integration specs)

These tools work together to create a **hybrid context** that includes both technical and business information.

---

## Architecture: Three Layers of Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    Code Onboarding Process                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  Repository Analysis │
                    │  (Code Structure)    │
                    └─────────────────────┘
                              ↓
                    ┌─────────┬─────────┐
                    ↓         ↓         ↓
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  GitIngest   │ │  Graphify    │ │  KG Query    │
        │              │ │              │ │              │
        │ Repository   │ │ Code         │ │ Domain       │
        │ digest       │ │ relationships│ │ knowledge    │
        │ File tree    │ │ Communities  │ │ Business     │
        │ Overview     │ │ Architecture │ │ rules        │
        └──────────────┘ └──────────────┘ └──────────────┘
                    ↓         ↓         ↓
                    └─────────┬─────────┘
                              ↓
                    ┌─────────────────────┐
                    │  Hybrid Context     │
                    │  (kg-context.md)    │
                    └─────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  LightRAG Ingestion │
                    │  (KG Storage)       │
                    └─────────────────────┘
```

---

## Layer 1: GitIngest - Repository Digest

### What GitIngest Does

GitIngest generates a **repository digest** - a summary of the entire repository structure and content.

```python
# From parsers.py: parse_git_repository()

from gitingest import ingest

# Clone repository
repo = git.Repo.clone_from(repo_url, temp_dir)

# Generate digest
digest = ingest(str(temp_dir))
# Returns: Repository summary with file tree, structure, key files
```

### GitIngest Output

```
Repository Overview
├─ File structure (tree view)
├─ Key files identified
├─ Technology stack detected
├─ Build configuration
├─ Dependencies summary
└─ README content
```

### How It's Used in Code Onboarding

```python
# In kg-context.md

## Repository Overview
[GitIngest digest content]

## Technology Stack
- Languages: Python, SQL
- Frameworks: FastAPI, SQLAlchemy
- Build tools: pip, pytest
- Databases: PostgreSQL
```

### Document Created

```python
documents.append({
    "title": f"Repository: {repo_name}",
    "content": repo_summary,  # GitIngest output
    "metadata": {
        "source_type": "git",
        "persona": "developer",
        "repo_url": repo_url,
        "repo_name": repo_name,
        "domain": metadata.get("domain", ""),
        "doc_type": "repository_overview",
        "format": "git"
    }
})
```

---

## Layer 2: Graphify - Code Structure Analysis

### What Graphify Does

Graphify analyzes **code relationships** and detects **architectural patterns**.

```python
# From graphify_integration.py: generate_graphify_analysis()

import graphify

# Step 1: Detect files
files = graphify.detect.collect_files(str(project_path))

# Step 2: Extract nodes and edges
extractions = []
for file_path in files:
    extraction = graphify.extract.extract(file_path)
    extractions.append(extraction)

# Step 3: Build graph
graph = graphify.build.build_graph(extractions)

# Step 4: Detect communities
graph = graphify.cluster.cluster(graph)

# Step 5: Analyze graph
analysis = graphify.analyze.analyze(graph)

# Step 6: Export results
outputs = graphify.export.export(graph, out_dir=temp_dir, formats=["json"])
```

### Graphify Output Structure

```python
{
    "files_analyzed": 50,
    "total_files": 120,
    "nodes": [
        {
            "id": "src/models/facility.py::FacilityModel",
            "label": "FacilityModel",
            "type": "class",
            "community": 1
        },
        {
            "id": "src/services/facility_service.py::FacilityService",
            "label": "FacilityService",
            "type": "class",
            "community": 1
        }
    ],
    "edges": [
        {
            "source": "src/services/facility_service.py::FacilityService",
            "target": "src/models/facility.py::FacilityModel",
            "relation": "uses"
        }
    ],
    "communities": [
        {
            "id": 1,
            "name": "Service Module",
            "size": 8,
            "nodes": [...]
        }
    ],
    "analysis": {
        "god_nodes": ["FacilityService"],
        "surprises": ["Circular dependency detected"],
        "questions": ["Why does FacilityService depend on both models and utils?"]
    }
}
```

### Graphify Insights Formatting

```python
# From graphify_integration.py: format_graphify_insights()

sections = []

# 1. Key Code Relationships
sections.append("### Key Code Relationships\n")
for edge in edges:
    sections.append(f"**{edge['source']}** -> **{edge['target']}**")

# 2. Code Communities/Modules
sections.append("### Code Modules\n")
for community in communities:
    sections.append(f"#### {community['name']} ({community['size']} files)")
    for node in community['nodes']:
        sections.append(f"- `{node['id']}`")

# 3. Architectural Insights
sections.append("### Architectural Insights\n")
for god_node in analysis.get("god_nodes", []):
    sections.append(f"- `{god_node}` (many dependencies)")

# 4. Statistics
sections.append(f"- **Files analyzed**: {files_analyzed}")
sections.append(f"- **Code nodes**: {len(nodes)}")
sections.append(f"- **Relationships**: {len(edges)}")
```

### How It's Used in Code Onboarding

```python
# In kg-context.md

## Code Structure Analysis

### Key Code Relationships
- **FacilityService** -> **FacilityModel** (uses)
- **FacilityController** -> **FacilityService** (uses)

### Code Modules
#### Service Module (8 files)
- `src/services/facility_service.py`
- `src/services/patient_service.py`
- ...

### Architectural Insights
#### Highly Connected Components
- `FacilityService` (many dependencies)

#### Notable Patterns
- Circular dependency detected in models
```

### Document Created

```python
# Hybrid context combines base + graphify insights

base_content = build_kg_context_document(...)
graphify_insights = format_graphify_insights(graphify_data)
hybrid_content = base_content + "\n\n" + graphify_insights

# Save to kg-context.md
context_path.write_text(hybrid_content)
```

---

## Layer 3: KG Integration - Domain Knowledge Mapping

### What KG Integration Does

KG integration **maps domain knowledge** from the Knowledge Graph into the code context.

```python
# In context_builder.py: build_kg_context_document()

def build_kg_context_document(
    project_path: Path,
    analysis: ProjectAnalysis,
    installed_skills: list[str],
    suggested_skills: Optional[list[str]] = None,
) -> str:
    """Build kg-context.md with domain knowledge."""
    
    # Query KG for domain knowledge
    domain_knowledge = query_kg_for_domain(project_path.name)
    
    # Include in context
    context = f"""
    # {project_path.name} - Codebase Understanding
    
    ## Business Context
    
    ### Applicable SLAs
    {format_slas(domain_knowledge.get('slas', []))}
    
    ### Integration Requirements
    {format_integration_specs(domain_knowledge.get('integration_specs', []))}
    
    ### Security Requirements
    {format_security_policies(domain_knowledge.get('security_policies', []))}
    
    ### Performance Requirements
    {format_performance_requirements(domain_knowledge.get('performance_requirements', []))}
    
    ## Code Structure
    [Graphify analysis]
    
    ## Repository Overview
    [GitIngest digest]
    """
    
    return context
```

### KG Information Mapping

```
Knowledge Graph (Domain Knowledge)
    ↓
├─ SLAs
│  ├─ Response time < 100ms
│  ├─ Availability > 99.9%
│  └─ Data consistency: Strong
│
├─ Integration Specs
│  ├─ FHIR API integration
│  ├─ OAuth 2.0 authentication
│  └─ HL7 v2 support
│
├─ Security Policies
│  ├─ HIPAA compliance
│  ├─ AES-256 encryption
│  └─ TLS 1.2+ required
│
└─ Performance Requirements
   ├─ 10K concurrent users
   ├─ DB query latency < 50ms
   └─ Cache hit rate > 80%
    ↓
Mapped to Code Context
    ├─ Inform architecture decisions
    ├─ Guide implementation patterns
    ├─ Validate against constraints
    └─ Generate compliance checks
```

### How It's Used in Code Onboarding

```python
# In kg-context.md

## Business Context

### Applicable SLAs
- **Response Time**: < 100ms
  - Implication: Use caching, optimize queries
  - Validation: Add latency monitoring

- **Availability**: > 99.9%
  - Implication: Implement retry logic, circuit breakers
  - Validation: Add health checks

### Integration Requirements
- **FHIR API Integration**
  - Endpoint: https://fhir.example.com/api/v1
  - Authentication: OAuth 2.0
  - Validation: Use FHIR validator

- **HL7 v2 Support**
  - Format: HL7 v2.5
  - Encoding: UTF-8
  - Validation: Use HL7 parser

### Security Requirements
- **HIPAA Compliance**
  - Data encryption at rest: AES-256
  - Data encryption in transit: TLS 1.2+
  - Audit logging required

### Performance Requirements
- **Concurrent Users**: 10K
  - Connection pooling required
  - Load balancing needed
  
- **Database Performance**
  - Query latency: < 50ms
  - Connection pool size: 100+
```

### Document Created

```python
# KG context includes domain knowledge

documents_for_kg = [
    {
        "title": "Business Context - Facility Domain",
        "content": """
        ## SLAs
        - Response time < 100ms
        - Availability > 99.9%
        
        ## Integration Requirements
        - FHIR API integration
        - OAuth 2.0 authentication
        
        ## Security Requirements
        - HIPAA compliance
        - AES-256 encryption
        """,
        "metadata": {
            "source_type": "kg",
            "persona": "business_analyst",
            "domain": "facility",
            "doc_type": "business_context",
            "category": "sla,integration,security"
        }
    }
]
```

---

## Complete Integration Flow

### Step 1: Code Onboarding Initiated

```bash
dva code onboard --path ./facility-service --kg --graphify --domain cwow-facility
```

### Step 2: Repository Analysis

```python
# Step 1: Analyze project structure
analysis = ProjectAnalyzer.analyze(project_path)
# Returns: languages, frameworks, dependencies, etc.

# Step 2: Generate GitIngest digest
digest = ingest(str(project_path))
# Returns: Repository overview, file tree, key files

# Step 3: Generate Graphify analysis
graphify_data = generate_graphify_analysis(project_path)
# Returns: Nodes, edges, communities, architectural insights

# Step 4: Query KG for domain knowledge
domain_knowledge = query_kg_for_domain("cwow-facility")
# Returns: SLAs, integration specs, security policies, performance requirements
```

### Step 3: Build Hybrid Context

```python
# Combine all three layers

base_content = build_kg_context_document(
    project_path,
    analysis,
    installed_skills,
    suggested_skills,
    domain_knowledge  # NEW: Include KG data
)

graphify_insights = format_graphify_insights(graphify_data)

hybrid_content = base_content + "\n\n" + graphify_insights

# Save to kg-context.md
context_path = project_path / ".skills" / "project-context" / "kg-context.md"
context_path.write_text(hybrid_content)
```

### Step 4: Ingest into LightRAG

```python
# Ingest hybrid context into KG

ingest_result = ingest_context_to_lightrag(
    context_path,
    project_name,
    lightrag_url="http://localhost:8001"
)

# LightRAG processes:
# 1. Repository overview (GitIngest)
# 2. Code structure (Graphify)
# 3. Domain knowledge (KG)
# 4. Extracts entities and relationships
# 5. Builds searchable KG
```

### Step 5: Generate Skills with Context

```python
# Skills are generated with awareness of:
# 1. Code structure (Graphify)
# 2. Business requirements (KG)
# 3. Integration patterns (KG)
# 4. Security constraints (KG)

skill_generator = SkillGenerator(
    project_analysis=analysis,
    code_structure=graphify_data,
    business_context=domain_knowledge,
    kg_context=hybrid_content
)

skills = skill_generator.generate()
# Skills are now aware of:
# - SLAs and performance requirements
# - Integration patterns
# - Security constraints
# - Code architecture
```

---

## Data Flow: KG Information to Skills

```
Knowledge Graph (Domain Knowledge)
    ├─ SLAs: Response time < 100ms
    ├─ Integration: FHIR API
    ├─ Security: HIPAA compliance
    └─ Performance: 10K concurrent users
    ↓
kg-context.md (Hybrid Context)
    ├─ Business Context section
    ├─ Code Structure section (Graphify)
    └─ Repository Overview section (GitIngest)
    ↓
LightRAG Ingestion
    ├─ Parse business context
    ├─ Extract entities
    ├─ Build relationships
    └─ Index for search
    ↓
Skill Generation
    ├─ Generate API handler skill
    │  └─ Aware of FHIR API requirement
    ├─ Generate database skill
    │  └─ Aware of performance requirement
    ├─ Generate security skill
    │  └─ Aware of HIPAA compliance
    └─ Generate monitoring skill
       └─ Aware of SLA requirements
    ↓
Generated Skills
    ├─ FHIR API Handler
    │  └─ Implements OAuth 2.0
    ├─ Database Optimizer
    │  └─ Implements connection pooling
    ├─ Security Validator
    │  └─ Implements HIPAA checks
    └─ SLA Monitor
       └─ Tracks response time
```

---

## Implementation Details

### How KG Data is Queried

```python
# In context_builder.py

def query_kg_for_domain(domain_name: str) -> Dict[str, Any]:
    """Query KG for domain knowledge."""
    
    # Query Memory MCP or direct KG
    kg_client = KGClient(url="http://localhost:8001")
    
    # Get SLAs
    slas = kg_client.query(
        f"MATCH (n:SLA) WHERE n.domain = '{domain_name}' RETURN n"
    )
    
    # Get integration specs
    integration_specs = kg_client.query(
        f"MATCH (n:IntegrationSpec) WHERE n.domain = '{domain_name}' RETURN n"
    )
    
    # Get security policies
    security_policies = kg_client.query(
        f"MATCH (n:SecurityPolicy) WHERE n.domain = '{domain_name}' RETURN n"
    )
    
    # Get performance requirements
    performance_reqs = kg_client.query(
        f"MATCH (n:PerformanceRequirement) WHERE n.domain = '{domain_name}' RETURN n"
    )
    
    return {
        "slas": slas,
        "integration_specs": integration_specs,
        "security_policies": security_policies,
        "performance_requirements": performance_reqs
    }
```

### How Graphify Data is Formatted

```python
# In graphify_integration.py

def format_graphify_insights(graph_data: Dict[str, Any]) -> str:
    """Format Graphify analysis for inclusion in context."""
    
    sections = []
    
    # 1. Key relationships
    edges = graph_data.get("edges", [])
    sections.append("### Key Code Relationships\n")
    for edge in edges[:15]:
        rel_type = edge.get("relation", "related")
        sections.append(f"- **{edge['source']}** {rel_type} **{edge['target']}**")
    
    # 2. Code communities
    communities = graph_data.get("communities", [])
    sections.append("\n### Code Modules\n")
    for community in communities[:8]:
        sections.append(f"#### {community['name']} ({community['size']} files)")
        for node in community['nodes'][:5]:
            sections.append(f"- `{node['id']}`")
    
    # 3. Architectural insights
    analysis = graph_data.get("analysis", {})
    sections.append("\n### Architectural Insights\n")
    
    god_nodes = analysis.get("god_nodes", [])
    if god_nodes:
        sections.append("#### Highly Connected Components\n")
        for node in god_nodes[:5]:
            sections.append(f"- `{node}` (many dependencies)")
    
    surprises = analysis.get("surprises", [])
    if surprises:
        sections.append("\n#### Notable Patterns\n")
        for surprise in surprises[:5]:
            sections.append(f"- {surprise}")
    
    return "\n".join(sections)
```

### How GitIngest Data is Included

```python
# In parsers.py

def parse_git_repository(repo_url: str, ...) -> List[Dict[str, Any]]:
    """Parse Git repository using gitingest."""
    
    # Clone repo
    repo = git.Repo.clone_from(repo_url, temp_dir)
    
    # Generate digest
    digest = ingest(str(temp_dir))
    
    # Create document
    documents.append({
        "title": f"Repository: {repo_name}",
        "content": digest,  # GitIngest output
        "metadata": {
            "source_type": "git",
            "persona": "developer",
            "repo_url": repo_url,
            "repo_name": repo_name,
            "domain": metadata.get("domain", ""),
            "doc_type": "repository_overview",
            "format": "git"
        }
    })
    
    return documents
```

---

## Example: Complete kg-context.md

```markdown
# Facility Service - Codebase Understanding

## Business Context

### Applicable SLAs
- **Response Time**: < 100ms
  - Implication: Implement caching, optimize queries
  - Validation: Monitor response time in production

- **Availability**: > 99.9%
  - Implication: Implement retry logic, circuit breakers
  - Validation: Monitor uptime metrics

### Integration Requirements
- **FHIR API Integration**
  - Endpoint: https://fhir.example.com/api/v1
  - Authentication: OAuth 2.0
  - Validation: Use FHIR validator

### Security Requirements
- **HIPAA Compliance**
  - Data encryption at rest: AES-256
  - Data encryption in transit: TLS 1.2+
  - Audit logging required

### Performance Requirements
- **Concurrent Users**: 10K
  - Connection pooling required
  - Load balancing needed

## Code Structure Analysis

### Key Code Relationships
- **FacilityService** uses **FacilityModel**
- **FacilityController** uses **FacilityService**
- **FacilityRepository** uses **DatabaseConnection**

### Code Modules
#### Service Module (8 files)
- `src/services/facility_service.py`
- `src/services/patient_service.py`
- `src/services/integration_service.py`

#### Model Module (5 files)
- `src/models/facility.py`
- `src/models/patient.py`

### Architectural Insights
#### Highly Connected Components
- `FacilityService` (many dependencies)

#### Notable Patterns
- Circular dependency detected in models
- Missing error handling in integration layer

## Repository Overview

### File Structure
```
facility-service/
├── src/
│   ├── models/
│   ├── services/
│   ├── controllers/
│   └── utils/
├── tests/
├── requirements.txt
└── README.md
```

### Technology Stack
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Testing**: pytest

### Key Dependencies
- fastapi==0.104.1
- sqlalchemy==2.0.0
- pydantic==2.0.0
- requests==2.31.0

## Installed Skills
- `facility-api-handler`
- `database-optimizer`
- `security-validator`
- `sla-monitor`
```

---

## Benefits of Three-Layer Integration

### For Code Analysis
- ✅ Understand code structure (Graphify)
- ✅ Understand repository organization (GitIngest)
- ✅ Understand business constraints (KG)

### For Skill Generation
- ✅ Generate skills aware of architecture
- ✅ Generate skills aware of business requirements
- ✅ Generate skills aware of security constraints

### For Agents
- ✅ Agents understand code structure
- ✅ Agents understand business context
- ✅ Agents can make better decisions

### For Future Enhancements
- ✅ Add more analysis layers
- ✅ Add more KG information
- ✅ Improve skill generation

---

## Summary

Code onboarding integrates **three complementary tools**:

1. **GitIngest** - Repository digest and file structure
2. **Graphify** - Code relationships and architecture
3. **KG Integration** - Domain knowledge and business rules

These are combined into a **hybrid kg-context.md** that includes:
- Business context (SLAs, integration specs, security policies)
- Code structure (relationships, communities, architecture)
- Repository overview (file tree, technology stack)

This hybrid context is then:
- Ingested into LightRAG (KG storage)
- Used to generate domain-aware skills
- Available for agents to query during execution

The result is a **complete understanding** of both the code and the business domain.
