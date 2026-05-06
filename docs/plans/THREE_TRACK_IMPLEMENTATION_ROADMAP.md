# Three-Track Implementation Roadmap

**Date**: May 6, 2026  
**Status**: Ready for Execution  
**Scope**: Three parallel implementation tracks for platform transformation

---

## Executive Summary

Three coordinated implementation tracks to transform agentic-cli from a tool-focused platform to a methodology-focused agent platform:

1. **Track A: MCP Business Context Internalization** (5-7 days)
2. **Track B: Enhanced Code Onboarding + Methodology** (8-10 days)
3. **Track C: Knowledge Graph Integration** (6-8 days)

These tracks are **interdependent** and should be executed in parallel with careful coordination.

---

## Track A: MCP Business Context Internalization

### Objective
Use MCP services (Confluence, Memory, KG) to automatically extract and internalize business context from Confluence PDFs, making it queryable during code onboarding.

### Current State
- ✅ Confluence MCP running (port 8129)
- ✅ Memory MCP running (port 8130)
- ✅ KG MCP running (port 8131)
- ❌ No PDF attachment extraction
- ❌ No business context persistence
- ❌ No integration with code onboarding

### Deliverables

#### Phase A1: Extend Confluence MCP (2-3 days)
**Goal**: Add PDF attachment extraction capability

**Tasks**:
1. [ ] Extend `confluence/src/confluence_mcp/confluence_client.py`
   - [ ] Add `list_page_attachments(page_id, file_type="pdf")` method
   - [ ] Add `download_attachment(attachment_url)` method
   - [ ] Add `extract_pdf_text(pdf_bytes)` method (using PyPDF2 or pdfplumber)

2. [ ] Add MCP tools to Confluence server
   - [ ] Tool: `confluence_list_attachments` - List PDFs on a page
   - [ ] Tool: `confluence_download_attachment` - Download PDF content
   - [ ] Tool: `confluence_extract_pdf_text` - Extract text from PDF

3. [ ] Create test suite
   - [ ] Test PDF listing
   - [ ] Test PDF download
   - [ ] Test text extraction

**Files to Create/Modify**:
```
mcp-servers/confluence/
├── src/confluence_mcp/confluence_client.py (MODIFY)
├── src/confluence_mcp/server.py (MODIFY - add tools)
└── tests/test_pdf_extraction.py (NEW)
```

**Success Criteria**:
- ✅ Can list PDF attachments on Confluence pages
- ✅ Can download PDFs
- ✅ Can extract text from PDFs
- ✅ All tests passing

#### Phase A2: Store Business Context in Memory MCP (2-3 days)
**Goal**: Persist extracted business rules as queryable entities

**Tasks**:
1. [ ] Create business context ingestion pipeline
   - [ ] Extract business rules from PDF text
   - [ ] Categorize rules (SLA, Integration, Security, Performance)
   - [ ] Create structured entities

2. [ ] Implement Memory MCP integration
   - [ ] Store BusinessRule entities
   - [ ] Store IntegrationSpec entities
   - [ ] Store SLA entities
   - [ ] Create relationships between entities

3. [ ] Create query interface
   - [ ] Query business rules by category
   - [ ] Semantic search for rules
   - [ ] Get related rules

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/
├── mcp_integrations/business_context_ingester.py (NEW)
├── mcp_integrations/memory_client.py (MODIFY)
└── tests/test_business_context.py (NEW)
```

**Success Criteria**:
- ✅ Business rules extracted from PDFs
- ✅ Rules stored in Memory MCP
- ✅ Can query rules by category
- ✅ Semantic search working

#### Phase A3: Integrate with Code Onboarding (1-2 days)
**Goal**: Query business context during code analysis

**Tasks**:
1. [ ] Modify code onboarding to query business context
   - [ ] Before analyzing code, query for relevant business rules
   - [ ] Include business context in analysis output
   - [ ] Reference business rules in generated skills

2. [ ] Create business context awareness in skill generation
   - [ ] Skills aware of business constraints
   - [ ] Skills reference business rules
   - [ ] Skills include compliance checks

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/commands/
├── code.py (MODIFY - add business context query)
└── skill.py (MODIFY - add business context to skills)
```

**Success Criteria**:
- ✅ Code onboarding queries business context
- ✅ Business rules included in analysis
- ✅ Skills reference business rules
- ✅ End-to-end test passing

---

## Track B: Enhanced Code Onboarding + Methodology

### Objective
Transform code onboarding from simple analysis to structured understanding with approval gates, auto-skill generation, and methodology application.

### Current State
- ✅ Basic code analysis (ProjectAnalyzer, Gitingest, Graphify, LightRAG)
- ❌ No structured understanding document
- ❌ No interactive questionnaire
- ❌ No auto-skill generation
- ❌ No methodology matching
- ❌ No approval gates

### Deliverables

#### Phase B1: Structured Understanding Document (3-4 days)
**Goal**: Generate comprehensive codebase understanding document

**Tasks**:
1. [ ] Create `codebase_analyzer.py`
   - [ ] Analyze repository structure
   - [ ] Detect tech stack
   - [ ] Identify code patterns
   - [ ] Extract conventions
   - [ ] Calculate quality metrics
   - [ ] Estimate complexity

2. [ ] Create `understanding_generator.py`
   - [ ] Generate markdown document with:
     - Architecture overview
     - Key files and purposes
     - Development workflow
     - Testing strategy
     - Common patterns
     - Deployment process
     - Known issues/limitations

3. [ ] Create test suite
   - [ ] Test analysis accuracy
   - [ ] Test document generation
   - [ ] Test with real repositories

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/analysis/
├── codebase_analyzer.py (NEW)
├── understanding_generator.py (NEW)
└── tests/test_understanding.py (NEW)
```

**Success Criteria**:
- ✅ Analysis detects all major components
- ✅ Understanding document is comprehensive
- ✅ Document is well-structured and readable
- ✅ Accuracy validated on test repos

#### Phase B2: Interactive Questionnaire (2-3 days)
**Goal**: Ask clarifying questions to refine understanding

**Tasks**:
1. [ ] Create `questionnaire.py`
   - [ ] Generate context-aware questions
   - [ ] Ask about business goals
   - [ ] Ask about key workflows
   - [ ] Ask about pain points
   - [ ] Ask about future plans

2. [ ] Implement interactive flow
   - [ ] Present questions to user
   - [ ] Collect answers
   - [ ] Refine analysis based on answers
   - [ ] Update understanding document

3. [ ] Create test suite
   - [ ] Test question generation
   - [ ] Test answer processing
   - [ ] Test refinement logic

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/analysis/
├── questionnaire.py (NEW)
└── tests/test_questionnaire.py (NEW)
```

**Success Criteria**:
- ✅ Questions are relevant and insightful
- ✅ Answers improve understanding
- ✅ Document is refined based on answers
- ✅ User experience is smooth

#### Phase B3: Auto-Skill Generation (2-3 days)
**Goal**: Generate domain-specific skills from analysis

**Tasks**:
1. [ ] Create `skill_generator.py`
   - [ ] Identify skill opportunities from analysis
   - [ ] Generate skill templates
   - [ ] Create skill metadata
   - [ ] Generate skill documentation

2. [ ] Implement skill generation logic
   - [ ] Generate 8-15 domain-specific skills
   - [ ] Skills based on tech stack
   - [ ] Skills based on code patterns
   - [ ] Skills based on business context

3. [ ] Create test suite
   - [ ] Test skill generation
   - [ ] Test skill quality
   - [ ] Test skill usability

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/analysis/
├── skill_generator.py (NEW)
└── tests/test_skill_generation.py (NEW)
```

**Success Criteria**:
- ✅ Skills are relevant to codebase
- ✅ Skills follow OpenSkill format
- ✅ Skills are well-documented
- ✅ Skills are immediately usable

#### Phase B4: Methodology Matching (1-2 days)
**Goal**: Recommend and apply best-fit methodology

**Tasks**:
1. [ ] Create `methodology_matcher.py`
   - [ ] Analyze codebase characteristics
   - [ ] Match to available methodologies
   - [ ] Rank by fit
   - [ ] Generate recommendations

2. [ ] Implement methodology application
   - [ ] Apply selected methodology
   - [ ] Create methodology pack
   - [ ] Generate workflow documentation

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/analysis/
├── methodology_matcher.py (NEW)
└── tests/test_methodology_matching.py (NEW)
```

**Success Criteria**:
- ✅ Methodology matching is accurate
- ✅ Recommendations are useful
- ✅ Methodology application is smooth

#### Phase B5: CLI Integration & Approval Gates (1-2 days)
**Goal**: Integrate into CLI with approval checkpoints

**Tasks**:
1. [ ] Enhance `commands/code.py`
   - [ ] Implement `agent code onboard` command
   - [ ] Add approval gates for major decisions
   - [ ] Create interactive flow
   - [ ] Generate output files

2. [ ] Create approval checkpoint system
   - [ ] Checkpoint after analysis
   - [ ] Checkpoint after questionnaire
   - [ ] Checkpoint before skill generation
   - [ ] Checkpoint before methodology application

3. [ ] Create test suite
   - [ ] Test CLI flow
   - [ ] Test approval gates
   - [ ] Test output files

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/commands/
├── code.py (MODIFY)
└── tests/test_code_onboard.py (NEW)
```

**Success Criteria**:
- ✅ CLI command works end-to-end
- ✅ Approval gates function correctly
- ✅ Output files are generated
- ✅ User experience is smooth

---

## Track C: Knowledge Graph Integration

### Objective
Integrate DVA's Knowledge Graph (Neo4j + LightRAG) into code onboarding to build semantic codebase graphs for richer understanding and skill generation.

### Current State
- ✅ KG infrastructure in place (Neo4j, LightRAG)
- ✅ KG MCP available
- ❌ No code onboarding integration
- ❌ No semantic codebase graphs
- ❌ No pattern reuse across projects
- ❌ No domain similarity matching

### Deliverables

#### Phase C1: KG Entity Model for Code (2-3 days)
**Goal**: Define semantic entities for code analysis

**Tasks**:
1. [ ] Design KG entity model
   - [ ] Project entity (name, language, framework)
   - [ ] Framework entity (name, version, patterns)
   - [ ] Pattern entity (name, description, examples)
   - [ ] Convention entity (name, scope, rules)
   - [ ] File entity (path, purpose, patterns)
   - [ ] Relationship types (uses, implements, follows, contains)

2. [ ] Implement entity creation
   - [ ] Create Project entities
   - [ ] Create Framework entities
   - [ ] Create Pattern entities
   - [ ] Create Convention entities
   - [ ] Create File entities

3. [ ] Implement relationship creation
   - [ ] Project uses Framework
   - [ ] Framework implements Pattern
   - [ ] File follows Convention
   - [ ] Project contains File

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/kg_integration/
├── code_entity_model.py (NEW)
├── kg_entity_creator.py (NEW)
└── tests/test_kg_entities.py (NEW)
```

**Success Criteria**:
- ✅ Entity model is comprehensive
- ✅ Entities are created correctly
- ✅ Relationships are established
- ✅ Queries work as expected

#### Phase C2: KG-Enhanced Analysis (2-3 days)
**Goal**: Enhance code analysis with KG queries

**Tasks**:
1. [ ] Modify `codebase_analyzer.py` to use KG
   - [ ] Query for similar projects
   - [ ] Query for known patterns
   - [ ] Query for conventions
   - [ ] Query for best practices

2. [ ] Implement KG-based enrichment
   - [ ] Enrich analysis with KG data
   - [ ] Add pattern references
   - [ ] Add best practice recommendations
   - [ ] Add similar project references

3. [ ] Create test suite
   - [ ] Test KG queries
   - [ ] Test enrichment logic
   - [ ] Test accuracy

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/analysis/
├── codebase_analyzer.py (MODIFY)
└── tests/test_kg_enrichment.py (NEW)
```

**Success Criteria**:
- ✅ KG queries work correctly
- ✅ Analysis is enriched with KG data
- ✅ Similar projects are identified
- ✅ Recommendations are useful

#### Phase C3: KG-Based Skill Generation (2-3 days)
**Goal**: Generate skills using KG patterns

**Tasks**:
1. [ ] Modify `skill_generator.py` to use KG
   - [ ] Query KG for pattern-based skills
   - [ ] Reference KG entities in skills
   - [ ] Include pattern examples
   - [ ] Link to similar skills

2. [ ] Implement KG-aware skill generation
   - [ ] Generate skills from KG patterns
   - [ ] Include best practices
   - [ ] Reference similar projects
   - [ ] Create skill relationships

3. [ ] Create test suite
   - [ ] Test skill generation from KG
   - [ ] Test skill quality
   - [ ] Test skill relationships

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/analysis/
├── skill_generator.py (MODIFY)
└── tests/test_kg_skill_generation.py (NEW)
```

**Success Criteria**:
- ✅ Skills generated from KG patterns
- ✅ Skills include best practices
- ✅ Skills reference similar projects
- ✅ Skill quality is high

#### Phase C4: KG Query Interface (1-2 days)
**Goal**: Create user-friendly KG query interface

**Tasks**:
1. [ ] Create KG query commands
   - [ ] `agent kg search-projects` - Find similar projects
   - [ ] `agent kg search-patterns` - Find patterns
   - [ ] `agent kg search-conventions` - Find conventions
   - [ ] `agent kg get-context` - Get project context

2. [ ] Implement query interface
   - [ ] Interactive search
   - [ ] Result formatting
   - [ ] Context display

3. [ ] Create test suite
   - [ ] Test query commands
   - [ ] Test result formatting
   - [ ] Test user experience

**Files to Create/Modify**:
```
agentic-cli/src/agentic_cli/commands/
├── kg.py (MODIFY)
└── tests/test_kg_commands.py (NEW)
```

**Success Criteria**:
- ✅ Query commands work
- ✅ Results are useful
- ✅ User experience is smooth

---

## Track Interdependencies

### Critical Path
```
Track A (MCP Context) → Track B (Code Onboarding) → Track C (KG Integration)
                              ↓
                        Track C (Parallel)
```

### Coordination Points

**Week 1**:
- Track A: Phase A1-A2 (Confluence PDF extraction + Memory storage)
- Track B: Phase B1-B2 (Analysis + Questionnaire)
- Track C: Phase C1 (KG entity model)

**Week 2**:
- Track A: Phase A3 (Integration with code onboarding)
- Track B: Phase B3-B5 (Skill generation + CLI integration)
- Track C: Phase C2-C4 (KG-enhanced analysis + skill generation)

### Dependencies
- Track B depends on Track A for business context
- Track C enhances both Track A and Track B
- All tracks must coordinate on data models and APIs

---

## Success Metrics

### Track A Success
- [ ] PDF extraction working reliably
- [ ] Business context queryable
- [ ] Integration with code onboarding smooth
- [ ] User satisfaction >4/5

### Track B Success
- [ ] Understanding documents comprehensive
- [ ] Auto-generated skills are usable
- [ ] Methodology matching accurate
- [ ] End-to-end flow works
- [ ] User satisfaction >4/5

### Track C Success
- [ ] KG entities created correctly
- [ ] Queries return relevant results
- [ ] KG-based skills are high quality
- [ ] Pattern reuse working
- [ ] User satisfaction >4/5

### Overall Success
- [ ] All three tracks integrated
- [ ] End-to-end workflow smooth
- [ ] Performance acceptable (<5 min for typical repo)
- [ ] Documentation complete
- [ ] Tests >90% coverage

---

## Resource Requirements

### Team Composition
- **Backend Engineers**: 2-3 (primary implementation)
- **DevOps**: 1 (MCP/KG infrastructure)
- **QA**: 1 (testing and validation)
- **Documentation**: 0.5 (guides and examples)

### Infrastructure
- MCP servers (Confluence, Memory, KG) running
- Neo4j instance for KG
- LightRAG for semantic indexing
- Development environment with all dependencies

### Timeline
- **Total Duration**: 16-21 days
- **Start Date**: Week of May 6, 2026
- **Target Completion**: May 30, 2026

---

## Risk Mitigation

### Technical Risks
| Risk | Mitigation |
|------|-----------|
| MCP API changes | Version pinning, API contracts |
| KG query performance | Indexing strategy, caching |
| PDF extraction errors | Fallback to text extraction |
| Skill generation quality | Human review, validation |

### Operational Risks
| Risk | Mitigation |
|------|-----------|
| Track coordination issues | Daily standups, shared docs |
| Dependency conflicts | Early integration testing |
| Performance degradation | Profiling, optimization |

---

## Getting Started

### Immediate Actions (Today)
1. [ ] Review this roadmap with team
2. [ ] Assign team members to tracks
3. [ ] Set up daily standups (15 min)
4. [ ] Create shared tracking document
5. [ ] Verify infrastructure is ready

### Week 1 Kickoff
1. [ ] Track A: Start Confluence PDF extension
2. [ ] Track B: Start codebase analyzer
3. [ ] Track C: Design KG entity model
4. [ ] Daily: Sync on progress and blockers

### Tracking & Communication
- **Daily Standups**: 15 min (9:30 AM UTC)
- **Weekly Sync**: 30 min (Friday 10 AM UTC)
- **Shared Document**: Track progress in real-time
- **GitHub Issues**: Create issues for each task

---

## Next Steps

1. **Review & Approval**: Get team approval on this roadmap
2. **Resource Allocation**: Assign team members to tracks
3. **Infrastructure Check**: Verify all systems ready
4. **Kickoff Meeting**: Align on approach and expectations
5. **Begin Implementation**: Start with Phase A1, B1, C1

---

**Document Status**: Ready for Execution  
**Last Updated**: May 6, 2026  
**Next Review**: May 13, 2026
