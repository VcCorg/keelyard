# Track A: Simplified Design - Separation of Concerns

**Date**: May 6, 2026  
**Status**: Redesigned for Simplicity  
**Scope**: Keep domain creation simple, move knowledge onboarding to separate commands

---

## The Problem with Previous Design

Previous design tried to do too much in `domain create`:
- ❌ Domain registration
- ❌ Release scanning
- ❌ Document collection
- ❌ Version deduplication
- ❌ Rule extraction
- ❌ Storage in Memory MCP
- ❌ KG indexing

This overloads the domain creation command and makes it hard to:
- Refresh KG asynchronously
- Update business context independently
- Handle failures gracefully
- Test each component separately

---

## The Solution: Separation of Concerns

### 1. Domain Creation (Simple & Fast)
```bash
dva domain create Facility --product CWOW \
  --jira CWOW \
  --bb CGF \
  --confluence CWOV
```

**What it does**:
- ✅ Register domain in database
- ✅ Store Jira/Bitbucket/Confluence links
- ✅ Done in seconds

**What it does NOT do**:
- ❌ Extract documents
- ❌ Extract rules
- ❌ Index in KG
- ❌ Store in Memory MCP

### 2. Knowledge Onboarding (Separate Activity)
```bash
# Onboard domain knowledge from Confluence
dva kg onboard --domain cwow-facility --confluence-space CWOV

# Or with options
dva kg onboard --domain cwow-facility \
  --confluence-space CWOV \
  --release-aware \
  --domain-keywords "Facility,Facility Domain,Facility Service" \
  --version-strategy "latest"
```

**What it does**:
- ✅ Scan Confluence space
- ✅ Collect domain documents
- ✅ Extract rules
- ✅ Store in Memory MCP
- ✅ Index in KG

**Benefits**:
- ✅ Can run asynchronously
- ✅ Can be refreshed independently
- ✅ Can be scheduled (e.g., after each release)
- ✅ Doesn't block domain creation

---

## Architecture

### Simple Domain Creation Flow
```
User Command
    ↓
dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
    ↓
Validate inputs
    ↓
Store in database
    ↓
Done (< 1 second)
    ↓
Output: Domain registered successfully
```

### Separate Knowledge Onboarding Flow
```
User Command
    ↓
dva kg onboard --domain cwow-facility --confluence-space CWOV
    ↓
Phase 1: Release Discovery
├─ Discover all releases
└─ Sort by release number
    ↓
Phase 2: Document Collection
├─ Find domain documents
├─ Extract metadata
└─ Deduplicate by version
    ↓
Phase 3: Content Extraction
├─ Extract page content
├─ Download PDFs
└─ Extract text
    ↓
Phase 4: Rule Extraction
├─ Extract rules using LLM
├─ Categorize rules
└─ Merge from multiple documents
    ↓
Phase 5: Storage
├─ Store in Memory MCP
└─ Index in KG
    ↓
Output: Knowledge onboarding complete
```

---

## Domain Create Command (Simplified)

### Current Implementation
```python
@domain_app.command()
def create(
    domain: str,
    product: str,
    description: str = None,
    jira_project: str = None,
    bitbucket_project: str = None,
    confluence_space: str = None,
    jira_dashboard: str = None,
    confluence_url: str = None,
    tags: str = None,
) -> None:
    """
    Register a new domain under a product.
    
    Examples:
        dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
        dva domain create Patient --product CWOW --jira CWOW --bb CGP --confluence CWOV
    """
    # Validate product exists
    prod = get_product(product.upper())
    if not prod:
        console.print(f"[red]✗ Product '{product.upper()}' not found.[/red]")
        raise typer.Exit(1)
    
    # Register domain
    name = _slugify(product.upper(), domain)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    
    register_domain(
        name=name,
        product=product.upper(),
        domain=domain,
        description=description,
        jira_project=jira_project,
        bitbucket_project=bitbucket_project,
        confluence_space=confluence_space,
        jira_dashboard=jira_dashboard,
        confluence_url=confluence_url,
        tags=tag_list,
    )
    
    console.print(f"[bold green]✓[/bold green] Domain registered: [cyan]{name}[/cyan]")
    
    # Show summary
    panel_lines = [
        f"[cyan]Name:[/cyan] {name}",
        f"[cyan]Product:[/cyan] {product.upper()}",
        f"[cyan]Domain:[/cyan] {domain}",
    ]
    if description:
        panel_lines.append(f"[cyan]Description:[/cyan] {description}")
    if jira_project:
        panel_lines.append(f"[cyan]Jira Project:[/cyan] {jira_project}")
    if bitbucket_project:
        panel_lines.append(f"[cyan]Bitbucket Project:[/cyan] {bitbucket_project}")
    if confluence_space:
        panel_lines.append(f"[cyan]Confluence Space:[/cyan] {confluence_space}")
    
    console.print(Panel("\n".join(panel_lines), title="Domain Details"))
    
    # Hint for next step
    console.print(f"\n[dim]Next: Onboard domain knowledge:[/dim]")
    console.print(f"  dva kg onboard --domain {name} --confluence-space {confluence_space}")
    
    record_activity(
        command="domain", subcommand="create",
        args={"name": name, "product": product.upper(), "domain": domain},
    )
```

**No changes needed** - Keep it as is!

---

## Knowledge Onboarding Command (New)

### New Command: `dva kg onboard`
```python
# In commands/kg.py (NEW)

kg_app = typer.Typer(
    help="Knowledge Graph management — onboard domain knowledge, search, and manage KG",
    rich_markup_mode=None,
)

@kg_app.command()
def onboard(
    domain: Annotated[str, typer.Option("--domain", "-d", help="Domain name (e.g., cwow-facility)")] = ...,
    confluence_space: Annotated[str, typer.Option("--confluence-space", "-c", help="Confluence space key")] = None,
    release_aware: Annotated[bool, typer.Option("--release-aware", help="Scan all releases")] = False,
    domain_keywords: Annotated[str, typer.Option("--domain-keywords", help="Comma-separated keywords")] = None,
    version_strategy: Annotated[str, typer.Option("--version-strategy", help="latest, all, or compare")] = "latest",
    async_mode: Annotated[bool, typer.Option("--async", help="Run asynchronously")] = False,
) -> None:
    """
    Onboard domain knowledge into the Knowledge Graph.
    
    This is a separate activity from domain creation. It collects domain documents
    from Confluence, extracts rules, and indexes them in the KG.
    
    Can be run:
    - Immediately after domain creation
    - Periodically to refresh knowledge
    - Asynchronously to avoid blocking other operations
    
    Examples:
        # Basic: Onboard from Confluence space
        dva kg onboard --domain cwow-facility --confluence-space CWOV
        
        # Release-aware: Scan all releases, keep latest
        dva kg onboard --domain cwow-facility --confluence-space CWOV \
          --release-aware \
          --domain-keywords "Facility,Facility Domain,Facility Service"
        
        # Async: Run in background
        dva kg onboard --domain cwow-facility --confluence-space CWOV --async
    """
    
    # Validate domain exists
    domain_obj = get_domain(domain)
    if not domain_obj:
        console.print(f"[red]✗ Domain '{domain}' not found.[/red]")
        console.print(f"[dim]Register it first: dva domain create <DOMAIN> --product <PRODUCT>[/dim]")
        raise typer.Exit(1)
    
    # Get Confluence space from domain or option
    space = confluence_space or domain_obj.get("confluence_space")
    if not space:
        console.print(f"[red]✗ No Confluence space configured for domain '{domain}'.[/red]")
        console.print(f"[dim]Update domain: dva domain update {domain} --confluence <SPACE_KEY>[/dim]")
        raise typer.Exit(1)
    
    if async_mode:
        # Run asynchronously (background job)
        console.print(f"[cyan]Starting async knowledge onboarding for {domain}...[/cyan]")
        job_id = start_async_kg_onboarding(
            domain=domain,
            confluence_space=space,
            release_aware=release_aware,
            domain_keywords=domain_keywords,
            version_strategy=version_strategy,
        )
        console.print(f"[green]✓ Job started: {job_id}[/green]")
        console.print(f"[dim]Check status: dva kg status {job_id}[/dim]")
    else:
        # Run synchronously
        console.print(f"[cyan]Onboarding knowledge for {domain}...[/cyan]")
        
        result = sync_kg_onboarding(
            domain=domain,
            confluence_space=space,
            release_aware=release_aware,
            domain_keywords=domain_keywords,
            version_strategy=version_strategy,
        )
        
        console.print(f"[bold green]✓[/bold green] Knowledge onboarding complete")
        console.print(Panel(
            f"Domain: {domain}\n"
            f"Releases scanned: {result['releases_scanned']}\n"
            f"Documents found: {result['documents_found']}\n"
            f"After deduplication: {result['documents_after_dedup']}\n"
            f"Rules extracted: {result['rules_extracted']}\n"
            f"Stored in KG: ✓",
            title="Onboarding Summary"
        ))
    
    record_activity(
        command="kg", subcommand="onboard",
        args={"domain": domain, "confluence_space": space},
    )
```

---

## Implementation Plan

### Phase 1: Keep Domain Create As-Is (0 days)
- ✅ No changes needed
- ✅ Already simple and fast

### Phase 2: Create KG Onboarding Command (3-5 days)
**New file**: `agentic-cli/src/agentic_cli/commands/kg.py`

**New classes**:
- `KGOnboardingOrchestrator` - Orchestrate onboarding
- `ReleaseDocumentCollector` - Collect documents
- `DocumentDeduplicator` - Deduplicate versions
- `VersionComparator` - Compare versions
- `RuleExtractor` - Extract rules

**New file**: `agentic-cli/src/agentic_cli/kg_integration/onboarding.py`

### Phase 3: Create Async Job System (2-3 days)
**New file**: `agentic-cli/src/agentic_cli/async_jobs/kg_onboarding_job.py`

**Features**:
- Background job execution
- Job status tracking
- Job result storage
- Job scheduling

### Phase 4: Integrate with Code Onboarding (1-2 days)
**Modify**: `agentic-cli/src/agentic_cli/analysis/codebase_analyzer.py`

**Features**:
- Query KG for domain knowledge
- Include in understanding documents
- Reference in generated skills

---

## CLI Workflow

### Step 1: Create Domain (Fast)
```bash
$ dva domain create Facility --product CWOW --jira CWOW --bb CGF --confluence CWOV
✓ Domain registered: cwow-facility
Next: Onboard domain knowledge:
  dva kg onboard --domain cwow-facility --confluence-space CWOV
```

### Step 2: Onboard Knowledge (Separate)
```bash
$ dva kg onboard --domain cwow-facility --confluence-space CWOV --release-aware
✓ Knowledge onboarding complete
  Releases scanned: 5
  Documents found: 20
  After deduplication: 4
  Rules extracted: 45
  Stored in KG: ✓
```

### Step 3: Use in Code Onboarding
```bash
$ dva code onboard https://github.com/company/facility-service --domain cwow-facility
✓ Code onboarding complete
  Understanding includes business context from KG
  Generated skills reference business rules
```

---

## Benefits of Separation

### For Domain Creation
- ✅ Fast (< 1 second)
- ✅ Simple (just store metadata)
- ✅ Reliable (no external dependencies)
- ✅ Easy to test

### For Knowledge Onboarding
- ✅ Can run asynchronously
- ✅ Can be scheduled
- ✅ Can be refreshed independently
- ✅ Can be retried on failure
- ✅ Can be monitored separately

### For Future Enhancements
- ✅ Refresh KG without recreating domain
- ✅ Update business context without domain changes
- ✅ Schedule periodic KG updates
- ✅ Support multiple knowledge sources
- ✅ Implement KG versioning

---

## Database Schema

### No Changes to Existing Tables
- `domains` - Already has confluence_space, jira_project, etc.
- `domain_business_context` - For storing onboarding results

### New Table: kg_onboarding_jobs
```sql
CREATE TABLE kg_onboarding_jobs (
    id INTEGER PRIMARY KEY,
    job_id TEXT UNIQUE,
    domain_id TEXT NOT NULL,
    confluence_space TEXT,
    status TEXT,  -- pending, running, completed, failed
    releases_scanned INTEGER,
    documents_found INTEGER,
    documents_after_dedup INTEGER,
    rules_extracted INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

---

## Files to Create

```
agentic-cli/src/agentic_cli/
├── commands/kg.py (NEW)
│   └── onboard command
├── kg_integration/
│   ├── onboarding.py (NEW)
│   ├── release_document_collector.py (NEW)
│   ├── document_deduplicator.py (NEW)
│   └── version_comparator.py (NEW)
└── async_jobs/
    └── kg_onboarding_job.py (NEW)
```

---

## Files to Modify

```
agentic-cli/src/agentic_cli/
├── commands/__init__.py (add kg_app)
├── tracker.py (add kg_onboarding_jobs table)
└── analysis/codebase_analyzer.py (query KG)
```

---

## Timeline

| Task | Duration |
|------|----------|
| Phase 1: Keep domain create as-is | 0 days |
| Phase 2: Create KG onboarding command | 3-5 days |
| Phase 3: Create async job system | 2-3 days |
| Phase 4: Integrate with code onboarding | 1-2 days |
| **Total** | **6-10 days** |

---

## Success Criteria

- [ ] Domain create command unchanged
- [ ] KG onboarding command working
- [ ] Release-aware document collection working
- [ ] Version deduplication working
- [ ] Rule extraction working
- [ ] Async job system working
- [ ] Code onboarding integration smooth
- [ ] Tests passing

---

## Advantages Over Previous Design

| Aspect | Previous | New |
|--------|----------|-----|
| **Domain Create** | Overloaded | Simple |
| **Speed** | Slow (30+ sec) | Fast (< 1 sec) |
| **Async Support** | Not possible | Built-in |
| **Refresh KG** | Recreate domain | Just run onboard again |
| **Error Handling** | All-or-nothing | Granular |
| **Testing** | Complex | Simple |
| **Future Enhancements** | Hard | Easy |

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**Approach**: Simple, Clean, Extensible  
**Timeline**: 6-10 days

---

## Summary

The redesigned Track A:

1. **Keeps domain creation simple** - Just register metadata
2. **Moves knowledge onboarding to separate command** - `dva kg onboard`
3. **Supports async execution** - Can run in background
4. **Enables future enhancements** - Refresh, schedule, version KG
5. **Maintains clean separation** - Each command has single responsibility

This is much better than trying to do everything in `domain create`.
