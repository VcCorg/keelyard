# Three Tracks - Getting Started Guide

**Quick Reference**: How to begin implementation of the three parallel tracks

---

## Overview

You have three coordinated implementation tracks to transform agentic-cli into a methodology-focused agent platform:

| Track | Focus | Duration | Priority |
|-------|-------|----------|----------|
| **Track A** | MCP Business Context | 5-7 days | High |
| **Track B** | Code Onboarding + Methodology | 8-10 days | High |
| **Track C** | Knowledge Graph Integration | 6-8 days | Medium |

**Total Timeline**: 16-21 days (parallel execution)

---

## Track A: MCP Business Context Internalization

### What It Does
Extracts business rules from Confluence PDFs and makes them queryable during code analysis.

### Why It Matters
- Code onboarding becomes aware of business constraints
- Generated skills reference business rules
- Better compliance and governance

### Getting Started

**Step 1: Understand Current State** (30 min)
- Read: `docs/analysis/MCP_BUSINESS_CONTEXT_INTERNALIZATION.md`
- Check: MCP servers running (ports 8129, 8130, 8131)
- Verify: Confluence access and Memory MCP connectivity

**Step 2: Phase A1 - Extend Confluence MCP** (2-3 days)
```bash
# 1. Review Confluence API documentation
# 2. Extend confluence_client.py with:
#    - list_page_attachments(page_id, file_type="pdf")
#    - download_attachment(attachment_url)
#    - extract_pdf_text(pdf_bytes)

# 3. Add MCP tools to server.py:
#    - confluence_list_attachments
#    - confluence_download_attachment
#    - confluence_extract_pdf_text

# 4. Test with real Confluence pages
```

**Files to Start With**:
- `mcp-servers/confluence/src/confluence_mcp/confluence_client.py`
- `mcp-servers/confluence/src/confluence_mcp/server.py`

**Step 3: Phase A2 - Store in Memory MCP** (2-3 days)
```bash
# 1. Create business_context_ingester.py
#    - Extract rules from PDF text
#    - Categorize (SLA, Integration, Security, Performance)
#    - Create structured entities

# 2. Integrate with Memory MCP
#    - Store BusinessRule entities
#    - Store IntegrationSpec entities
#    - Create relationships

# 3. Test entity storage and retrieval
```

**Files to Create**:
- `agentic-cli/src/agentic_cli/mcp_integrations/business_context_ingester.py` (NEW)

**Step 4: Phase A3 - Integrate with Code Onboarding** (1-2 days)
```bash
# 1. Modify code.py to query business context
# 2. Include business rules in analysis output
# 3. Reference rules in generated skills
# 4. Test end-to-end flow
```

### Success Checklist
- [ ] PDF extraction working
- [ ] Business rules stored in Memory MCP
- [ ] Rules queryable by category
- [ ] Code onboarding queries rules
- [ ] Skills reference business rules
- [ ] All tests passing

---

## Track B: Enhanced Code Onboarding + Methodology

### What It Does
Transforms code onboarding from simple analysis to structured understanding with auto-skill generation and methodology application.

### Why It Matters
- Users get comprehensive codebase understanding
- Skills auto-generated from analysis
- Methodology recommendations
- Approval gates for governance

### Getting Started

**Step 1: Understand Current State** (30 min)
- Read: `docs/specs/IMPLEMENTATION_SPECS.md`
- Read: `docs/analysis/SUPERPOWERS_REFERENCE_ANALYSIS.md`
- Review: Existing code analysis tools (ProjectAnalyzer, Gitingest, Graphify, LightRAG)

**Step 2: Phase B1 - Structured Understanding Document** (3-4 days)
```bash
# 1. Create codebase_analyzer.py
#    - Analyze repository structure
#    - Detect tech stack
#    - Identify code patterns
#    - Extract conventions
#    - Calculate quality metrics

# 2. Create understanding_generator.py
#    - Generate markdown document with:
#      - Architecture overview
#      - Key files and purposes
#      - Development workflow
#      - Testing strategy
#      - Common patterns

# 3. Test with real repositories
```

**Files to Create**:
- `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py` (NEW)
- `agentic-cli/src/agentic_cli/analysis/understanding_generator.py` (NEW)

**Step 3: Phase B2 - Interactive Questionnaire** (2-3 days)
```bash
# 1. Create questionnaire.py
#    - Generate context-aware questions
#    - Ask about business goals
#    - Ask about key workflows
#    - Ask about pain points

# 2. Implement interactive flow
#    - Present questions to user
#    - Collect answers
#    - Refine analysis based on answers

# 3. Test question quality
```

**Files to Create**:
- `agentic-cli/src/agentic_cli/analysis/questionnaire.py` (NEW)

**Step 4: Phase B3 - Auto-Skill Generation** (2-3 days)
```bash
# 1. Create skill_generator.py
#    - Identify skill opportunities
#    - Generate skill templates
#    - Create skill metadata

# 2. Generate 8-15 domain-specific skills
#    - Based on tech stack
#    - Based on code patterns
#    - Based on business context (from Track A)

# 3. Test skill quality
```

**Files to Create**:
- `agentic-cli/src/agentic_cli/analysis/skill_generator.py` (NEW)

**Step 5: Phase B4 - Methodology Matching** (1-2 days)
```bash
# 1. Create methodology_matcher.py
#    - Analyze codebase characteristics
#    - Match to available methodologies
#    - Rank by fit

# 2. Implement methodology application
#    - Apply selected methodology
#    - Create methodology pack

# 3. Test recommendations
```

**Files to Create**:
- `agentic-cli/src/agentic_cli/analysis/methodology_matcher.py` (NEW)

**Step 6: Phase B5 - CLI Integration** (1-2 days)
```bash
# 1. Enhance commands/code.py
#    - Implement agent code onboard command
#    - Add approval gates
#    - Create interactive flow

# 2. Create approval checkpoint system
#    - Checkpoint after analysis
#    - Checkpoint after questionnaire
#    - Checkpoint before skill generation

# 3. Test end-to-end flow
```

### Success Checklist
- [ ] Analysis detects all major components
- [ ] Understanding document is comprehensive
- [ ] Questions are relevant and insightful
- [ ] Skills are domain-specific and usable
- [ ] Methodology matching is accurate
- [ ] CLI flow works end-to-end
- [ ] Approval gates function correctly
- [ ] All tests passing

---

## Track C: Knowledge Graph Integration

### What It Does
Integrates KG (Neo4j + LightRAG) into code onboarding to build semantic codebase graphs for richer understanding and pattern reuse.

### Why It Matters
- Semantic understanding of code relationships
- Pattern reuse across projects
- Similar project discovery
- Better skill generation from patterns

### Getting Started

**Step 1: Understand Current State** (30 min)
- Read: `docs/analysis/KG_ENHANCED_CODE_ONBOARDING.md`
- Read: `docs/analysis/CODE_ONBOARDING_TOOLS_ANALYSIS.md`
- Review: KG infrastructure (Neo4j, LightRAG, KG MCP)

**Step 2: Phase C1 - KG Entity Model** (2-3 days)
```bash
# 1. Design KG entity model
#    - Project entity
#    - Framework entity
#    - Pattern entity
#    - Convention entity
#    - File entity
#    - Relationship types

# 2. Implement entity creation
#    - Create entities in Neo4j
#    - Create relationships
#    - Test entity queries

# 3. Validate model with real projects
```

**Files to Create**:
- `agentic-cli/src/agentic_cli/kg_integration/code_entity_model.py` (NEW)
- `agentic-cli/src/agentic_cli/kg_integration/kg_entity_creator.py` (NEW)

**Step 3: Phase C2 - KG-Enhanced Analysis** (2-3 days)
```bash
# 1. Modify codebase_analyzer.py to use KG
#    - Query for similar projects
#    - Query for known patterns
#    - Query for conventions
#    - Query for best practices

# 2. Implement KG-based enrichment
#    - Enrich analysis with KG data
#    - Add pattern references
#    - Add best practice recommendations

# 3. Test enrichment quality
```

**Files to Modify**:
- `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py` (MODIFY)

**Step 4: Phase C3 - KG-Based Skill Generation** (2-3 days)
```bash
# 1. Modify skill_generator.py to use KG
#    - Query KG for pattern-based skills
#    - Reference KG entities in skills
#    - Include pattern examples

# 2. Generate skills from KG patterns
#    - Include best practices
#    - Reference similar projects
#    - Create skill relationships

# 3. Test skill quality
```

**Files to Modify**:
- `agentic-cli/src/agentic_cli/analysis/skill_generator.py` (MODIFY)

**Step 5: Phase C4 - KG Query Interface** (1-2 days)
```bash
# 1. Create KG query commands
#    - agent kg search-projects
#    - agent kg search-patterns
#    - agent kg search-conventions
#    - agent kg get-context

# 2. Implement query interface
#    - Interactive search
#    - Result formatting
#    - Context display

# 3. Test user experience
```

**Files to Create/Modify**:
- `agentic-cli/src/agentic_cli/commands/kg.py` (NEW/MODIFY)

### Success Checklist
- [ ] Entity model is comprehensive
- [ ] Entities created correctly in KG
- [ ] KG queries work as expected
- [ ] Analysis enriched with KG data
- [ ] Similar projects identified
- [ ] Skills generated from KG patterns
- [ ] Query commands work smoothly
- [ ] All tests passing

---

## Execution Strategy

### Week 1: Foundation
```
Mon-Tue: Track A Phase A1 (Confluence PDF)
         Track B Phase B1 (Understanding)
         Track C Phase C1 (KG Model)

Wed-Thu: Track A Phase A2 (Memory Storage)
         Track B Phase B2 (Questionnaire)
         Track C Phase C1 (continued)

Fri:     Sync & Integration Testing
```

### Week 2: Integration
```
Mon-Tue: Track A Phase A3 (Integration)
         Track B Phase B3 (Skill Generation)
         Track C Phase C2 (KG Analysis)

Wed-Thu: Track B Phase B4-B5 (Methodology + CLI)
         Track C Phase C3-C4 (KG Skills + Query)

Fri:     Final Integration & Testing
```

### Daily Standup (15 min)
- What did you complete yesterday?
- What are you working on today?
- Any blockers?

### Weekly Sync (30 min)
- Review progress on all tracks
- Discuss integration points
- Plan next week
- Address blockers

---

## Key Files to Know

### Track A
- `mcp-servers/confluence/src/confluence_mcp/confluence_client.py`
- `mcp-servers/confluence/src/confluence_mcp/server.py`
- `agentic-cli/src/agentic_cli/mcp_integrations/` (new)

### Track B
- `agentic-cli/src/agentic_cli/analysis/` (main work area)
- `agentic-cli/src/agentic_cli/commands/code.py`
- `agentic-cli/src/agentic_cli/commands/skill.py`

### Track C
- `agentic-cli/src/agentic_cli/kg_integration/` (new)
- `kg-infrastructure/` (reference)
- `agentic-cli/src/agentic_cli/analysis/` (integration)

---

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies (MCP, KG, LLM)
- Target >90% coverage

### Integration Tests
- Test components working together
- Test with real MCP servers
- Test with real KG instance

### End-to-End Tests
- Test full workflows
- Test with real repositories
- Test user experience

### Test Locations
```
agentic-cli/tests/
├── unit/
│   ├── test_codebase_analyzer.py
│   ├── test_questionnaire.py
│   ├── test_skill_generator.py
│   └── ...
├── integration/
│   ├── test_mcp_integration.py
│   ├── test_kg_integration.py
│   └── ...
└── e2e/
    ├── test_code_onboard_flow.py
    └── ...
```

---

## Common Pitfalls to Avoid

1. **Not coordinating between tracks**
   - Use shared tracking document
   - Daily standups are essential
   - Communicate API changes early

2. **Skipping tests**
   - Write tests as you go
   - Don't leave testing for the end
   - Aim for >90% coverage

3. **Not validating with real data**
   - Test with real repositories
   - Test with real Confluence pages
   - Get user feedback early

4. **Over-engineering**
   - Start simple, iterate
   - Don't over-generalize
   - Focus on the happy path first

5. **Ignoring performance**
   - Profile early and often
   - Set performance targets
   - Optimize bottlenecks

---

## Success Criteria

### By End of Week 1
- [ ] Track A: PDF extraction working
- [ ] Track B: Understanding document generation working
- [ ] Track C: KG entity model designed and tested

### By End of Week 2
- [ ] Track A: Business context queryable
- [ ] Track B: Full CLI flow working with approval gates
- [ ] Track C: KG-enhanced analysis and skill generation working

### Final Success
- [ ] All three tracks integrated
- [ ] End-to-end workflow smooth
- [ ] Performance acceptable
- [ ] Tests >90% coverage
- [ ] Documentation complete
- [ ] User satisfaction >4/5

---

## Resources

### Documentation
- `docs/plans/THREE_TRACK_IMPLEMENTATION_ROADMAP.md` - Detailed roadmap
- `docs/specs/IMPLEMENTATION_SPECS.md` - Implementation specifications
- `docs/analysis/` - Analysis documents

### Code References
- `agentic-cli/src/agentic_cli/` - Main codebase
- `mcp-servers/` - MCP implementations
- `kg-infrastructure/` - KG setup

### External Resources
- Confluence API docs
- Neo4j documentation
- LightRAG documentation

---

## Questions?

Refer to the detailed roadmap: `docs/plans/THREE_TRACK_IMPLEMENTATION_ROADMAP.md`

---

**Document Status**: Ready for Execution  
**Last Updated**: May 6, 2026  
**Next Review**: May 13, 2026
