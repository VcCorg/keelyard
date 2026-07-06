# Knowledge Graph-Enhanced Code Onboarding

## Overview

Integrate KEEL's Knowledge Graph (Neo4j + LightRAG) into code onboarding to build **semantic codebase graphs** instead of just analyzing code text. This enables richer understanding, better skill generation, and knowledge reuse across projects.

## Architecture Integration

```
Code Onboarding Phases
├─ Phase 1: Repository Analysis
│  └─ [NEW] Store patterns/tech stack/conventions in KG
│     └─ Create entities: Project, Framework, Pattern, Convention, File
│     └─ Create relationships: uses, implements, follows
│
├─ Phase 2: Clarifying Questions
│  └─ [NEW] Query KG for domain-similar projects
│     └─ "Found similar projects in KG: "
│
├─ Phase 3: Understanding Document Generation
│  └─ [NEW] Query KG relationships for structured output
│     └─ Build from semantic relationships, not just text
│
├─ Phase 4: Skill Generation
│  └─ [NEW] Use KG patterns to auto-generate domain skills
│     └─ Reference KG entities for context
│
└─ Phase 5: Methodology Pack Application
   └─ [EXISTING] Apply pack with KG-enhanced context
```

## KG Tools Mapping to Onboarding Phases

| KG Tool | Phase | Use Case |
|---------|-------|----------|
| `register_knowledge_source` | Phase 1 | Register repo as KG source |
| `ingest_knowledge_source` | Phase 1 | Index repo docs/README/specs into KG |
| `query_knowledge_graph` | Phase 2-3 | Query for similar projects, patterns |
| `get_project_context` | Phase 2-3 | Retrieve context for questions |
| `search_business_context` | Phase 2 | Find business rules from KG |
| `get_entity_details` | Phase 3-4 | Get detailed entity relationships |
| `list_knowledge_projects` | Phase 2 | Discover similar projects |

## Phase-by-Phase Integration

### Phase 1A: Repository Analysis → KG Ingestion

**Current Flow:**
```
Clone repo → Analyze code → Extract patterns → Return JSON
```

**Enhanced Flow:**
```
Clone repo → Analyze code → Extract patterns → CREATE KG ENTITIES
                                              ├─ Project
                                              ├─ Framework (FastAPI)
                                              ├─ Pattern (async-await)
                                              ├─ Convention (snake_case)
                                              ├─ File (app/api/endpoints.py)
                                              └─ Relationships
                                                 ├─ Project uses FastAPI
                                                 ├─ FastAPI implements async
                                                 ├─ File follows convention
                                                 └─ Project has pattern
```

**Implementation:**
```python
# In codebase_analyzer.py Phase 1

class RepositoryAnalyzer:
    def __init__(self, kg_client: KGClient):
        self.kg = kg_client
    
    async def analyze(self, repo_path: str):
        # 1. Extract patterns (existing code)
        patterns = self._extract_patterns(repo_path)
        
        # 2. Register repo as KG source
        source_id = await self.kg.register_knowledge_source(
            name=repo_path.name,
            source_type="document",
            path=repo_path / "docs",  # Include README, ADRs, specs
        )
        
        # 3. Ingest documentation into KG
        await self.kg.ingest_knowledge_source(source_id)
        
        # 4. Create Project entity in KG
        project_entity = await self.kg.create_entity(
            label="Project",
            properties={
                "name": repo_path.name,
                "path": str(repo_path),
                "source_id": source_id,
                "_source": "agentic_kg",  # Scope for safety
            }
        )
        
        # 5. Create Framework entities and relationships
        for framework in patterns["frameworks"]:
            framework_entity = await self.kg.create_or_match_entity(
                label="Framework",
                properties={"name": framework}
            )
            await self.kg.create_relationship(
                from_id=project_entity.id,
                relationship="USES",
                to_id=framework_entity.id
            )
        
        # 6. Create Pattern entities
        for pattern_name, pattern_data in patterns["code_patterns"].items():
            pattern_entity = await self.kg.create_entity(
                label="Pattern",
                properties={
                    "name": pattern_name,
                    "value": pattern_data,
                    "_source": "agentic_kg"
                }
            )
            await self.kg.create_relationship(
                from_id=project_entity.id,
                relationship="IMPLEMENTS",
                to_id=pattern_entity.id
            )
        
        # 7. Return analysis WITH KG entity IDs
        return {
            "patterns": patterns,
            "kg_project_id": project_entity.id,
            "kg_source_id": source_id,
        }
```

**KG Schema Created:**
```
Project
├─ id: <uuid>
├─ name: "order-api"
├─ path: "/workspace/order-api"
├─ source_id: "source-123"
└─ _source: "agentic_kg"

USES relationship to →

Framework
├─ id: <uuid>
├─ name: "FastAPI"
└─ _source: "agentic_kg"

IMPLEMENTS relationship to →

Pattern
├─ id: <uuid>
├─ name: "async-await"
├─ value: "async-def, await, asyncio"
└─ _source: "agentic_kg"

USES relationship to →

Database
├─ id: <uuid>
├─ name: "PostgreSQL"
└─ _source: "agentic_kg"
```

### Phase 2: Clarifying Questions → KG Query

**Current Flow:**
```
Ask 7-8 hardcoded questions → User answers → Store in JSON
```

**Enhanced Flow:**
```
Query KG for similar projects
  ↓
Ask targeted questions based on differences
  ↓
"Found similar pattern in: project-A. How does yours differ?"
  ↓
Store in JSON WITH KG references
```

**Implementation:**
```python
# In questionnaire.py

class Questionnaire:
    def __init__(self, kg_client: KGClient):
        self.kg = kg_client
    
    async def ask_questions(self, project_entity_id: str, analysis: dict):
        questions = []
        
        # 1. Query KG for similar projects
        similar_projects = await self.kg.query_knowledge_graph(
            query="""
            MATCH (p:Project)-[:USES]->(f:Framework)
            WHERE p.id != $project_id
            AND (f.name IN $frameworks)
            RETURN DISTINCT p, count(f) as framework_count
            ORDER BY framework_count DESC
            LIMIT 3
            """,
            params={
                "project_id": project_entity_id,
                "frameworks": analysis["tech_stack"]["frameworks"]
            }
        )
        
        # 2. Build questions around differences
        if similar_projects:
            similar_names = [p["name"] for p in similar_projects]
            questions.append({
                "id": "business_purpose",
                "category": "business",
                "question": f"What is the primary business purpose? (Found similar projects: {similar_names})",
                "kg_context": {
                    "similar_projects": similar_projects,
                    "reason": "Found projects using same frameworks"
                }
            })
        
        # 3. Query KG for common conventions
        conventions = await self.kg.query_knowledge_graph(
            query="""
            MATCH (p:Project)-[:FOLLOWS]->(c:Convention)
            WHERE p.id != $project_id
            RETURN DISTINCT c.name, count(*) as frequency
            ORDER BY frequency DESC
            LIMIT 5
            """,
            params={"project_id": project_entity_id}
        )
        
        # 4. Add convention alignment question
        if conventions:
            questions.append({
                "id": "convention_alignment",
                "category": "technical",
                "question": "Do you follow these conventions? " + str([c["name"] for c in conventions]),
                "kg_context": {
                    "common_conventions": conventions,
                    "reason": "Most projects use these conventions"
                }
            })
        
        return questions
    
    async def store_responses(self, project_entity_id: str, answers: dict):
        """Store answers back to KG for future reference"""
        for answer_key, answer_value in answers.items():
            # Create Answer entity
            answer_entity = await self.kg.create_entity(
                label="Answer",
                properties={
                    "question": answer_key,
                    "value": str(answer_value),
                    "_source": "agentic_kg"
                }
            )
            
            # Link to project
            await self.kg.create_relationship(
                from_id=project_entity_id,
                relationship="HAS_ANSWER",
                to_id=answer_entity.id
            )
```

### Phase 3: Understanding Document → KG Relationships

**Current Flow:**
```
Generate markdown from analysis + questions → Write to file
```

**Enhanced Flow:**
```
Query KG for structured relationships
  ↓
Build understanding doc from semantic graph
  ↓
Reference KG entities: "See project-A for similar pattern"
  ↓
Export as both markdown AND graph visualization
```

**Implementation:**
```python
# In understanding_generator.py

class UnderstandingGenerator:
    def __init__(self, kg_client: KGClient):
        self.kg = kg_client
    
    async def generate(self, project_entity_id: str, analysis: dict, answers: dict):
        """Generate understanding doc from KG relationships"""
        
        # 1. Get full project entity with relationships
        project_details = await self.kg.get_entity_details(project_entity_id)
        
        # 2. Build doc from relationships
        doc_sections = []
        
        # Architecture section from KG
        frameworks = [rel["target"] for rel in project_details["relationships"] 
                     if rel["type"] == "USES" and rel["target"]["label"] == "Framework"]
        
        databases = [rel["target"] for rel in project_details["relationships"] 
                    if rel["type"] == "USES" and rel["target"]["label"] == "Database"]
        
        patterns = [rel["target"] for rel in project_details["relationships"] 
                   if rel["type"] == "IMPLEMENTS" and rel["target"]["label"] == "Pattern"]
        
        doc_sections.append({
            "section": "Technology Stack",
            "frameworks": [f["name"] for f in frameworks],
            "databases": [d["name"] for d in databases],
            "patterns": [p["name"] for p in patterns],
        })
        
        # 3. Query for similar implementations
        similar_implementations = await self.kg.query_knowledge_graph(
            query="""
            MATCH (this:Project)-[:USES]->(f:Framework),
                  (other:Project)-[:USES]->(f)
            WHERE this.id = $project_id
            AND other.id != this.id
            RETURN DISTINCT other.name, count(f) as shared_frameworks
            ORDER BY shared_frameworks DESC
            LIMIT 5
            """,
            params={"project_id": project_entity_id}
        )
        
        if similar_implementations:
            doc_sections.append({
                "section": "Similar Projects in KG",
                "projects": similar_implementations,
                "note": "These projects share similar technology choices"
            })
        
        # 4. Generate markdown
        markdown = self._generate_markdown(doc_sections, project_details)
        
        # 5. Also export graph visualization
        graph_viz = await self._export_graph_visualization(project_entity_id)
        
        return {
            "markdown": markdown,
            "graph_visualization": graph_viz,
            "kg_project_id": project_entity_id,
        }
    
    async def _export_graph_visualization(self, project_entity_id: str):
        """Export project graph for visualization"""
        entities = await self.kg.query_knowledge_graph(
            query="""
            MATCH (start:Project)-[rel*..2]->(node)
            WHERE start.id = $project_id
            RETURN start, rel, node
            """,
            params={"project_id": project_entity_id}
        )
        
        # Convert to graph format (nodes + edges)
        return {
            "nodes": entities,
            "edges": self._extract_relationships(entities),
            "format": "cytoscape.js"  # Can visualize in dashboard
        }
```

### Phase 4: Skill Generation → KG Patterns

**Current Flow:**
```
Use analysis to prompt LLM → Generate skills → Save to files
```

**Enhanced Flow:**
```
Query KG for existing skill implementations
  ↓
Analyze pattern variations in KG
  ↓
Generate skills customized to THIS project's patterns
  ↓
Link generated skills back to KG entities
```

**Implementation:**
```python
# In skill_generator.py

class SkillGenerator:
    def __init__(self, kg_client: KGClient):
        self.kg = kg_client
    
    async def generate_skills(self, project_entity_id: str, analysis: dict):
        """Generate project-specific skills using KG patterns"""
        
        # 1. Query for pattern implementations
        patterns = await self.kg.query_knowledge_graph(
            query="""
            MATCH (p:Project)-[:IMPLEMENTS]->(pattern:Pattern)
            WHERE p.id = $project_id
            RETURN pattern.name, pattern.value
            """,
            params={"project_id": project_entity_id}
        )
        
        # 2. For each pattern, find reference implementations
        generated_skills = []
        
        for pattern in patterns:
            # Find projects with same pattern
            references = await self.kg.query_knowledge_graph(
                query="""
                MATCH (other:Project)-[:IMPLEMENTS]->(p:Pattern)
                WHERE p.name = $pattern_name
                AND other.id != $project_id
                RETURN other.name, other.path
                LIMIT 3
                """,
                params={
                    "pattern_name": pattern["name"],
                    "project_id": project_entity_id
                }
            )
            
            # 3. Generate skill with context
            skill_context = {
                "pattern_name": pattern["name"],
                "implementation": pattern["value"],
                "reference_projects": references,
                "kg_pattern_id": pattern.get("id"),
            }
            
            skill = await self._generate_skill_from_pattern(skill_context)
            generated_skills.append(skill)
        
        # 4. Link skills back to KG
        for skill in generated_skills:
            skill_entity = await self.kg.create_entity(
                label="Skill",
                properties={
                    "name": skill["name"],
                    "type": "domain",
                    "domain": "auto-generated",
                    "kg_source": project_entity_id,
                    "_source": "agentic_kg"
                }
            )
            
            await self.kg.create_relationship(
                from_id=project_entity_id,
                relationship="HAS_SKILL",
                to_id=skill_entity.id
            )
        
        return generated_skills
    
    async def _generate_skill_from_pattern(self, context: dict):
        """Generate skill YAML from pattern context"""
        # Use LLM to generate skill, but with KG context
        prompt = f"""
        Generate a project-specific skill for this pattern:
        
        Pattern: {context['pattern_name']}
        Implementation: {context['implementation']}
        
        Reference implementations from similar projects:
        {json.dumps(context['reference_projects'], indent=2)}
        
        Create a skill that:
        1. Follows the pattern as implemented in this project
        2. References the pattern implementation details
        3. Shows examples from reference projects
        4. Is specific to this project's conventions
        """
        
        skill_yaml = await self.llm.generate(prompt)
        return skill_yaml
```

## KG Data Model

### Entities Created by Code Onboarding

```
Project
├─ id: uuid
├─ name: string
├─ path: string
├─ source_id: string (KG source reference)
├─ _source: "agentic_kg" (safety scope)
└─ created_at: timestamp

Framework
├─ id: uuid
├─ name: string (FastAPI, Django, etc.)
└─ _source: "agentic_kg"

Database
├─ id: uuid
├─ name: string (PostgreSQL, MongoDB, etc.)
└─ _source: "agentic_kg"

Pattern
├─ id: uuid
├─ name: string (async-await, dependency-injection, etc.)
├─ value: string (actual pattern implementation)
└─ _source: "agentic_kg"

Convention
├─ id: uuid
├─ name: string (snake_case, rest-api, etc.)
├─ category: string (naming, api-style, etc.)
└─ _source: "agentic_kg"

File
├─ id: uuid
├─ path: string
├─ language: string
├─ lines_of_code: int
└─ _source: "agentic_kg"

Answer
├─ id: uuid
├─ question: string
├─ value: string (user's answer)
└─ _source: "agentic_kg"

Skill
├─ id: uuid
├─ name: string
├─ type: string (domain, methodology, etc.)
├─ domain: string
├─ kg_source: uuid (reference to project)
└─ _source: "agentic_kg"
```

### Relationships

```
Project -USES-> Framework
Project -USES-> Database
Project -IMPLEMENTS-> Pattern
Project -FOLLOWS-> Convention
Project -CONTAINS-> File
Project -HAS_ANSWER-> Answer
Project -HAS_SKILL-> Skill

File -IMPLEMENTS-> Pattern
File -FOLLOWS-> Convention

Answer -FOR-> Question

Skill -BASED_ON-> Pattern
Skill -REFERENCES-> File
```

## Benefits of KG Integration

### 1. Knowledge Reuse
```
Project A onboarded → Creates KG entities
Project B onboarded → Finds similar patterns
  → Queries: "Who else uses async-await with FastAPI?"
  → References Project A's approach
  → Generates consistent skills
```

### 2. Pattern Discovery
```
Query KG: "All projects using PostgreSQL + SQLAlchemy + async"
Result: 5 projects, 3 patterns, consensus conventions
Use: Recommend conventions to new projects
```

### 3. Skill Context
```
Generated skill can reference:
- Pattern source (from KG)
- Reference implementations (from KG)
- Similar projects (from KG)
- Relationship chains (from KG)
```

### 4. Audit Trail
```
All onboarding decisions stored in KG with relationships:
- Why this pattern chosen
- Which projects influenced decision
- How it was implemented
- What alternatives existed
```

## CLI Integration

```bash
# Standard code onboarding (enhanced with KG)
agent code onboard https://github.com/myteam/backend

# Show KG graph during onboarding
agent code onboard https://github.com/myteam/backend --show-kg

# Query KG for similar projects
agent kg query "Projects using FastAPI and PostgreSQL"

# Visualize project graph
agent code onboard https://github.com/myteam/backend --export-graph graph.json
# Then open in dashboard: Agent Playground > Knowledge Graph > [project-name]

# List all onboarded projects in KG
agent kg list-projects

# Export project understanding with graph
agent code onboard https://github.com/myteam/backend --export-understanding
# Creates: .keel/codebase-understanding.md + .keel/codebase-graph.json
```

## Implementation Timeline

### Week 1: KG Integration Setup
- [ ] Create KG client wrapper for agentic-cli
- [ ] Implement Phase 1A (entity creation)
- [ ] Test Neo4j/LightRAG connectivity

### Week 2: Question Enrichment
- [ ] Implement Phase 2 KG queries
- [ ] Add similar project discovery
- [ ] Store answers back to KG

### Week 3: Understanding Generation
- [ ] Implement Phase 3 KG relationships
- [ ] Generate markdown from semantic graph
- [ ] Add graph visualization export

### Week 4: Skill Generation Enhancement
- [ ] Implement Phase 4 pattern-based generation
- [ ] Link skills to KG entities
- [ ] Test with multiple projects

## Next Steps

1. **Verify KG Connectivity**
   - Start kg-mcp server: `cd mcp-servers && docker compose up kg-mcp`
   - Test client connection to Neo4j and LightRAG

2. **Create KG Client Wrapper**
   - `agentic_cli/clients/kg_client.py`
   - Implement 8 KG tools as Python methods
   - Add to CLI context

3. **Integrate into Phase 1**
   - Modify `codebase_analyzer.py` to create entities
   - Test entity creation with sample repo

4. **Add Dashboard Visualization**
   - Create `Deployments.tsx` page for KG graphs
   - Show project entities + relationships
   - Add query interface

This transforms code onboarding from **text analysis** to **semantic graph building**, enabling knowledge reuse across all onboarded projects.
