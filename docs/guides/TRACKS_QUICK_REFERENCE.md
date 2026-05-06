# Three Tracks - Quick Reference Card

**Print this and keep it handy during implementation**

---

## Track A: MCP Business Context (5-7 days)

### What to Build
```
Confluence PDFs → Extract → Store in Memory MCP → Query in Code Onboarding
```

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `mcp-servers/confluence/src/confluence_mcp/confluence_client.py` | MODIFY | Add PDF extraction methods |
| `mcp-servers/confluence/src/confluence_mcp/server.py` | MODIFY | Add MCP tools for PDF |
| `agentic-cli/src/agentic_cli/mcp_integrations/business_context_ingester.py` | NEW | Extract and store rules |
| `agentic-cli/src/agentic_cli/commands/code.py` | MODIFY | Query business context |

### Key Methods to Implement
```python
# Confluence MCP
list_page_attachments(page_id, file_type="pdf")
download_attachment(attachment_url)
extract_pdf_text(pdf_bytes)

# Business Context Ingester
extract_business_rules(pdf_text)
store_in_memory_mcp(rules)
query_rules_by_category(category)
```

### Success Criteria
- [ ] PDF extraction working
- [ ] Rules stored in Memory MCP
- [ ] Rules queryable by category
- [ ] Code onboarding queries rules
- [ ] Skills reference business rules

---

## Track B: Code Onboarding + Methodology (8-10 days)

### What to Build
```
Analyze → Question → Document → Generate Skills → Match Methodology → CLI
```

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py` | NEW | Analyze repository |
| `agentic-cli/src/agentic_cli/analysis/questionnaire.py` | NEW | Interactive questions |
| `agentic-cli/src/agentic_cli/analysis/understanding_generator.py` | NEW | Generate doc |
| `agentic-cli/src/agentic_cli/analysis/skill_generator.py` | NEW | Auto-generate skills |
| `agentic-cli/src/agentic_cli/analysis/methodology_matcher.py` | NEW | Match methodology |
| `agentic-cli/src/agentic_cli/commands/code.py` | MODIFY | CLI integration |

### Key Classes to Implement
```python
class CodebaseAnalyzer:
    def analyze(repo_path) → AnalysisResult

class Questionnaire:
    def generate_questions(analysis) → List[Question]
    def process_answers(answers) → RefinedAnalysis

class UnderstandingGenerator:
    def generate(analysis) → MarkdownDocument

class SkillGenerator:
    def generate_skills(analysis) → List[Skill]

class MethodologyMatcher:
    def match(analysis) → MethodologyRecommendation
```

### Success Criteria
- [ ] Analysis detects all components
- [ ] Understanding document comprehensive
- [ ] Questions are relevant
- [ ] 8-15 skills auto-generated
- [ ] Methodology matching accurate
- [ ] CLI flow works end-to-end
- [ ] Approval gates functional

---

## Track C: Knowledge Graph Integration (6-8 days)

### What to Build
```
Code Analysis → KG Entities → KG Queries → Enriched Analysis → KG Skills
```

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `agentic-cli/src/agentic_cli/kg_integration/code_entity_model.py` | NEW | Define KG entities |
| `agentic-cli/src/agentic_cli/kg_integration/kg_entity_creator.py` | NEW | Create KG entities |
| `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py` | MODIFY | Query KG |
| `agentic-cli/src/agentic_cli/analysis/skill_generator.py` | MODIFY | Use KG patterns |
| `agentic-cli/src/agentic_cli/commands/kg.py` | NEW | KG query interface |

### KG Entity Types
```
Project
├─ name: str
├─ language: str
├─ framework: str
└─ relationships: [uses, contains, implements]

Framework
├─ name: str
├─ version: str
└─ patterns: [async, DI, ORM, etc.]

Pattern
├─ name: str
├─ description: str
└─ examples: [code snippets]

Convention
├─ name: str
├─ scope: str
└─ rules: [naming, formatting, etc.]

File
├─ path: str
├─ purpose: str
└─ patterns: [used patterns]
```

### Key Methods to Implement
```python
class CodeEntityModel:
    def create_project_entity(analysis) → ProjectEntity
    def create_framework_entity(framework) → FrameworkEntity
    def create_pattern_entity(pattern) → PatternEntity
    def create_relationships(entities) → Relationships

class KGEnhancedAnalyzer:
    def query_similar_projects(analysis) → List[Project]
    def query_patterns(analysis) → List[Pattern]
    def enrich_analysis(analysis) → EnrichedAnalysis

class KGSkillGenerator:
    def generate_from_patterns(patterns) → List[Skill]
    def generate_from_similar_projects(projects) → List[Skill]
```

### KG Query Commands
```bash
agent kg search-projects --language python --framework fastapi
agent kg search-patterns --category async
agent kg search-conventions --scope naming
agent kg get-context --project-id <id>
```

### Success Criteria
- [ ] Entity model comprehensive
- [ ] Entities created in KG
- [ ] Queries return relevant results
- [ ] Analysis enriched with KG data
- [ ] Similar projects identified
- [ ] Skills generated from patterns
- [ ] Query interface works

---

## Daily Checklist

### Morning (Start of Day)
- [ ] Read yesterday's standup notes
- [ ] Check for blockers from other tracks
- [ ] Review today's tasks
- [ ] Update task status

### During Day
- [ ] Write code
- [ ] Write tests
- [ ] Commit frequently
- [ ] Update progress

### Evening (End of Day)
- [ ] Update task status
- [ ] Write standup notes (what done, what next, blockers)
- [ ] Commit final changes
- [ ] Push to GitHub

### Standup Notes Template
```
Track: [A/B/C]
Completed:
- Task 1
- Task 2

In Progress:
- Task 3

Blockers:
- Issue 1 (impact, mitigation)

Next:
- Task 4
- Task 5
```

---

## Testing Checklist

### Unit Tests
- [ ] Test each class in isolation
- [ ] Mock external dependencies
- [ ] Test happy path
- [ ] Test error cases
- [ ] Target >90% coverage

### Integration Tests
- [ ] Test components together
- [ ] Test with real MCP servers
- [ ] Test with real KG instance
- [ ] Test data flow

### End-to-End Tests
- [ ] Test full workflows
- [ ] Test with real repositories
- [ ] Test user experience
- [ ] Test performance

### Test Command
```bash
# Run all tests
pytest agentic-cli/tests/ -v --cov

# Run specific test
pytest agentic-cli/tests/unit/test_codebase_analyzer.py -v

# Run with coverage report
pytest agentic-cli/tests/ --cov=agentic_cli --cov-report=html
```

---

## Git Workflow

### Commit Frequently
```bash
# Create feature branch
git checkout -b feature/track-a-pdf-extraction

# Commit frequently
git add <files>
git commit -m "Add PDF extraction to Confluence MCP"

# Push to GitHub
git push origin feature/track-a-pdf-extraction

# Create PR when ready
# Review, approve, merge
```

### Commit Message Format
```
[Track A] Add PDF extraction to Confluence MCP

- Add list_page_attachments() method
- Add download_attachment() method
- Add extract_pdf_text() method
- Add unit tests
- Add integration tests
```

---

## Common Commands

### MCP Testing
```bash
# Test Confluence MCP
curl http://localhost:8129/health

# Test Memory MCP
curl http://localhost:8130/health

# Test KG MCP
curl http://localhost:8131/health
```

### Code Analysis
```bash
# Run linter
pylint agentic-cli/src/agentic_cli/

# Run formatter
black agentic-cli/src/agentic_cli/

# Run type checker
mypy agentic-cli/src/agentic_cli/
```

### Database
```bash
# Neo4j console
cypher-shell -u neo4j -p password

# Query example
MATCH (p:Project) RETURN p LIMIT 10
```

---

## Troubleshooting

### MCP Connection Issues
```
Error: Cannot connect to MCP server
Solution: Check port (8129, 8130, 8131), verify server running

Error: MCP tool not found
Solution: Verify tool registered in server.py, restart server
```

### KG Query Issues
```
Error: No results from KG query
Solution: Verify entities created, check query syntax, check indexes

Error: KG timeout
Solution: Optimize query, add indexes, increase timeout
```

### Skill Generation Issues
```
Error: Generated skills are low quality
Solution: Review analysis input, check skill templates, add validation

Error: Skills don't reference business context
Solution: Verify Track A integration, check query results
```

---

## Performance Targets

| Task | Target | Current |
|------|--------|---------|
| PDF extraction | <5 sec | - |
| Code analysis | <30 sec | - |
| Skill generation | <1 min | - |
| Full workflow | <5 min | - |
| KG query | <1 sec | - |

---

## Documentation Links

| Document | Purpose |
|----------|---------|
| `docs/plans/THREE_TRACK_IMPLEMENTATION_ROADMAP.md` | Detailed roadmap |
| `docs/guides/THREE_TRACKS_GETTING_STARTED.md` | Step-by-step guide |
| `docs/plans/TRACKS_SUMMARY.md` | Executive summary |
| `docs/analysis/MCP_BUSINESS_CONTEXT_INTERNALIZATION.md` | Track A details |
| `docs/specs/IMPLEMENTATION_SPECS.md` | Track B details |
| `docs/analysis/KG_ENHANCED_CODE_ONBOARDING.md` | Track C details |

---

## Key Contacts

- **Track A Lead**: [Name]
- **Track B Lead**: [Name]
- **Track C Lead**: [Name]
- **DevOps**: [Name]
- **QA**: [Name]

---

## Important Dates

- **Week 1 Kickoff**: May 7, 2026
- **Week 1 Sync**: May 10, 2026
- **Week 2 Sync**: May 17, 2026
- **Target Completion**: May 30, 2026

---

**Last Updated**: May 6, 2026  
**Print Date**: [Your Date]
