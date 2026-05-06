# Code Onboarding Internals - Visual Summary

**Date**: May 6, 2026  
**Focus**: How KG information flows through graphify and git-inject tools

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Code Onboarding Pipeline                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  1. Repository Analysis                 │
        │  ├─ Detect languages, frameworks        │
        │  ├─ Identify dependencies               │
        │  └─ Analyze project structure           │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  2. Three-Layer Analysis                │
        │  ├─ GitIngest (repository digest)       │
        │  ├─ Graphify (code relationships)       │
        │  └─ KG Query (domain knowledge)         │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  3. Build Hybrid Context                │
        │  ├─ Business Context (KG)               │
        │  ├─ Code Structure (Graphify)           │
        │  └─ Repository Overview (GitIngest)     │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  4. Save kg-context.md                  │
        │  └─ .skills/project-context/            │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  5. Ingest into LightRAG                │
        │  ├─ Parse documents                     │
        │  ├─ Extract entities                    │
        │  └─ Build relationships                 │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  6. Generate Domain-Aware Skills        │
        │  ├─ Aware of SLAs                       │
        │  ├─ Aware of integration patterns       │
        │  ├─ Aware of security constraints       │
        │  └─ Aware of code architecture          │
        └─────────────────────────────────────────┘
```

---

## Layer 1: GitIngest - Repository Digest

### Input
```
Repository Directory
├── src/
├── tests/
├── requirements.txt
└── README.md
```

### Process
```python
from gitingest import ingest

digest = ingest(str(project_path))
# Analyzes entire repository
# Generates summary and file tree
```

### Output
```
Repository Overview
├─ File structure (tree view)
├─ Key files identified
├─ Technology stack
├─ Build configuration
├─ Dependencies summary
└─ README content
```

### Document Created
```python
{
    "title": "Repository: facility-service",
    "content": "[GitIngest digest]",
    "metadata": {
        "source_type": "git",
        "doc_type": "repository_overview",
        "format": "git"
    }
}
```

---

## Layer 2: Graphify - Code Structure Analysis

### Input
```
Source Code Files
├── src/services/facility_service.py
├── src/models/facility.py
├── src/controllers/facility_controller.py
└── src/utils/validators.py
```

### Process
```python
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
```

### Output
```
Code Graph Analysis
├─ Nodes (classes, functions, modules)
├─ Edges (relationships, dependencies)
├─ Communities (code modules)
├─ God nodes (highly connected)
├─ Surprises (anomalies)
└─ Questions (architecture issues)
```

### Example Output
```json
{
    "nodes": [
        {
            "id": "FacilityService",
            "type": "class",
            "community": 1
        }
    ],
    "edges": [
        {
            "source": "FacilityService",
            "target": "FacilityModel",
            "relation": "uses"
        }
    ],
    "communities": [
        {
            "name": "Service Module",
            "size": 8,
            "nodes": [...]
        }
    ],
    "analysis": {
        "god_nodes": ["FacilityService"],
        "surprises": ["Circular dependency"],
        "questions": ["Why does FacilityService depend on both models and utils?"]
    }
}
```

### Document Created
```python
{
    "title": "Code Structure: facility-service",
    "content": """
    ### Key Code Relationships
    - **FacilityService** uses **FacilityModel**
    - **FacilityController** uses **FacilityService**
    
    ### Code Modules
    #### Service Module (8 files)
    - src/services/facility_service.py
    - src/services/patient_service.py
    
    ### Architectural Insights
    #### Highly Connected Components
    - FacilityService (many dependencies)
    """,
    "metadata": {
        "source_type": "code",
        "doc_type": "code_structure",
        "format": "graphify"
    }
}
```

---

## Layer 3: KG Integration - Domain Knowledge Mapping

### Input
```
Knowledge Graph (Domain Knowledge)
├─ SLAs
│  ├─ Response time < 100ms
│  ├─ Availability > 99.9%
│  └─ Data consistency: Strong
├─ Integration Specs
│  ├─ FHIR API integration
│  ├─ OAuth 2.0 authentication
│  └─ HL7 v2 support
├─ Security Policies
│  ├─ HIPAA compliance
│  ├─ AES-256 encryption
│  └─ TLS 1.2+ required
└─ Performance Requirements
   ├─ 10K concurrent users
   ├─ DB query latency < 50ms
   └─ Cache hit rate > 80%
```

### Process
```python
# Query KG for domain knowledge
domain_knowledge = query_kg_for_domain("cwow-facility")

# Returns:
{
    "slas": [...],
    "integration_specs": [...],
    "security_policies": [...],
    "performance_requirements": [...]
}
```

### Output
```
Business Context
├─ SLAs
│  ├─ Response time < 100ms
│  └─ Availability > 99.9%
├─ Integration Requirements
│  ├─ FHIR API integration
│  └─ OAuth 2.0 authentication
├─ Security Requirements
│  ├─ HIPAA compliance
│  └─ AES-256 encryption
└─ Performance Requirements
   ├─ 10K concurrent users
   └─ DB query latency < 50ms
```

### Document Created
```python
{
    "title": "Business Context: Facility Domain",
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
    
    ## Performance Requirements
    - 10K concurrent users
    - DB query latency < 50ms
    """,
    "metadata": {
        "source_type": "kg",
        "doc_type": "business_context",
        "domain": "facility"
    }
}
```

---

## Combining All Three Layers

### Process
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

# Step 4: Save to kg-context.md
context_path = project_path / ".skills" / "project-context" / "kg-context.md"
context_path.write_text(hybrid_content)
```

### Result: kg-context.md
```markdown
# Facility Service - Codebase Understanding

## Business Context (From KG)
### SLAs
- Response time < 100ms
- Availability > 99.9%

### Integration Requirements
- FHIR API integration
- OAuth 2.0 authentication

### Security Requirements
- HIPAA compliance
- AES-256 encryption

### Performance Requirements
- 10K concurrent users
- DB query latency < 50ms

## Code Structure (From Graphify)
### Key Code Relationships
- **FacilityService** uses **FacilityModel**
- **FacilityController** uses **FacilityService**

### Code Modules
#### Service Module (8 files)
- src/services/facility_service.py
- src/services/patient_service.py

### Architectural Insights
#### Highly Connected Components
- FacilityService (many dependencies)

## Repository Overview (From GitIngest)
### File Structure
```
facility-service/
├── src/
│   ├── models/
│   ├── services/
│   └── controllers/
├── tests/
└── requirements.txt
```

### Technology Stack
- Language: Python 3.9+
- Framework: FastAPI
- Database: PostgreSQL
```

---

## Data Flow: KG → Skills

```
Knowledge Graph
├─ SLA: Response time < 100ms
├─ Integration: FHIR API
├─ Security: HIPAA compliance
└─ Performance: 10K concurrent users
    ↓
kg-context.md (Hybrid Context)
    ├─ Business Context section
    ├─ Code Structure section
    └─ Repository Overview section
    ↓
LightRAG Ingestion
    ├─ Parse business context
    ├─ Extract entities
    ├─ Build relationships
    └─ Index for search
    ↓
Skill Generation
    ├─ API Handler Skill
    │  └─ Aware of FHIR API requirement
    ├─ Database Skill
    │  └─ Aware of performance requirement
    ├─ Security Skill
    │  └─ Aware of HIPAA compliance
    └─ Monitoring Skill
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

## How KG Information Influences Skills

### Example 1: API Handler Skill

**KG Information**:
- Integration: FHIR API
- Authentication: OAuth 2.0
- SLA: Response time < 100ms

**Generated Skill**:
```python
class FHIRAPIHandler:
    def __init__(self):
        self.auth = OAuth2Handler()
        self.cache = CacheManager()
    
    async def handle_request(self, request):
        # OAuth 2.0 authentication (from KG)
        if not self.auth.validate(request):
            raise UnauthorizedError()
        
        # Caching for SLA compliance (from KG)
        cached = self.cache.get(request.key)
        if cached:
            return cached
        
        # FHIR API call
        result = await self.fhir_client.call(request)
        
        # Cache result
        self.cache.set(request.key, result)
        
        return result
```

### Example 2: Security Validator Skill

**KG Information**:
- Security: HIPAA compliance
- Encryption: AES-256
- Audit logging: Required

**Generated Skill**:
```python
class SecurityValidator:
    def __init__(self):
        self.encryptor = AES256Encryptor()
        self.audit_logger = AuditLogger()
    
    def validate_and_encrypt(self, data):
        # HIPAA compliance check (from KG)
        if not self.is_hipaa_compliant(data):
            raise ComplianceError()
        
        # AES-256 encryption (from KG)
        encrypted = self.encryptor.encrypt(data)
        
        # Audit logging (from KG)
        self.audit_logger.log(f"Data encrypted: {len(data)} bytes")
        
        return encrypted
```

### Example 3: Performance Monitor Skill

**KG Information**:
- SLA: Response time < 100ms
- Concurrent users: 10K
- DB query latency: < 50ms

**Generated Skill**:
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = MetricsCollector()
    
    async def monitor_request(self, request):
        start = time.time()
        
        try:
            result = await self.handle_request(request)
            
            # Track response time (from KG SLA)
            response_time = time.time() - start
            if response_time > 100:  # SLA threshold
                self.metrics.record_sla_violation(response_time)
            
            # Track concurrent users (from KG requirement)
            self.metrics.record_concurrent_user()
            
            return result
        finally:
            self.metrics.record_db_latency()
```

---

## Benefits of This Integration

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

## Summary

**Three-Layer Integration**:

1. **GitIngest** - Repository digest (file structure, overview)
2. **Graphify** - Code structure (relationships, communities, architecture)
3. **KG Integration** - Domain knowledge (SLAs, integration specs, security, performance)

**Result**: A **hybrid kg-context.md** that includes:
- Business context from KG
- Code structure from Graphify
- Repository overview from GitIngest

**Usage**: 
- Ingested into LightRAG
- Used to generate domain-aware skills
- Available for agents to query

**Outcome**: **Complete project understanding** combining code and business knowledge.
