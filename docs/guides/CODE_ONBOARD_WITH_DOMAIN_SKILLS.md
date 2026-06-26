# Code Onboard with Domain Skills — Implementation Guide

## Overview

This document explains how to integrate domain-validated skills into the `code onboard` workflow, enabling repos to be onboarded with domain-specific best practices and validated skills.

---

## Current Code Onboard Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. CLONE (if --repo provided)                                    │
│    git clone <repo-url> <target>                                 │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 2. ANALYZE PROJECT                                               │
│    - Detect language, framework, testing framework               │
│    - Analyze dependencies                                        │
│    - Identify tech stack                                         │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 3. MATCH SKILLS FROM REGISTRY                                    │
│    - Load skills/registry.json                                   │
│    - Match based on tech stack                                   │
│    - Detect MCP server requirements                              │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 4. GENERATE PROJECT-CONTEXT SKILL                                │
│    - Analyze codebase                                            │
│    - Extract key components, APIs, patterns                      │
│    - Generate .skills/project-context/SKILL.md                  │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 5. INSTALL MATCHED SKILLS                                        │
│    - Copy skill directories to .skills/                          │
│    - Generate .skills/<skill>/SKILL.md                           │
│    - Create .skills/<skill>/config.json                          │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 6. SAVE MANIFEST & SUGGESTIONS                                   │
│    - Write .onboard-manifest.json                                │
│    - Save skill suggestions for manual review                    │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 7. OPTIONAL: RUN AGENT FOR SKILL PROPOSALS                       │
│    - Use AI agent to detect skill gaps                           │
│    - Generate custom skill proposals                             │
│    - Save proposals for review                                   │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 8. OPTIONAL: INGEST INTO KG                                      │
│    - Prepare project context for KG                              │
│    - Ingest into LightRAG                                        │
│    - Tag with domain metadata (if --domain provided)             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Enhanced Flow with Domain Skills

### New Flags
```bash
dva code onboard --path <repo> \
  --domain <domain-slug> \
  --use-domain-skills
```

**New Parameters**:
- `--domain`: Domain slug (e.g., `cwow-facility`)
- `--use-domain-skills`: Enable domain-aware skill matching

### Enhanced Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ 1-4. CLONE, ANALYZE, MATCH, GENERATE (same as before)           │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 5. LOAD DOMAIN SKILLS (NEW)                                      │
│    if --domain and --use-domain-skills:                          │
│      - Load domain-context-repo                                  │
│      - Parse .domain/skills-manifest.json                        │
│      - Load domain-validated skills from .skills/                │
│      - Load domain-customized skills (forked from superpowers)   │
│      - Load superpowers baseline skills (from submodule)         │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 6. MATCH WITH DOMAIN-AWARE PRIORITY (ENHANCED)                   │
│    Priority order:                                               │
│    1. Domain-validated skills (highest priority)                 │
│    2. Domain-customized skills (forked from superpowers)         │
│    3. Generic registry skills                                    │
│    4. Superpowers baseline skills (lowest priority)              │
│                                                                  │
│    For each skill, check:                                        │
│    - Tech stack match                                            │
│    - Validation status (if domain skill)                         │
│    - MCP requirements                                            │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 7. INSTALL MATCHED SKILLS (ENHANCED)                             │
│    - Install domain-validated skills first                       │
│    - Install domain-customized skills                            │
│    - Install generic registry skills                             │
│    - Generate .skills/domain-skills/SKILL.md (NEW)               │
│      (lists all domain-specific skills installed)                │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 8. SAVE ENHANCED MANIFEST (ENHANCED)                             │
│    - Write .onboard-manifest.json with domain info               │
│    - Include domain-skills section                               │
│    - Track skill sources (domain vs. generic)                    │
│    - Record validation status of domain skills                   │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│ 9-10. OPTIONAL: AGENT & KG (same as before)                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Code Changes Required

### 1. Extend `code onboard` Command Signature

File: `agentic_cli/commands/code.py`

```python
@code_app.command("onboard")
def onboard(
    # ... existing parameters ...
    domain: Annotated[
        Optional[str],
        typer.Option("--domain", "-d", help="Domain slug for domain-aware skill matching"),
    ] = None,
    use_domain_skills: Annotated[
        bool,
        typer.Option("--use-domain-skills", help="Use domain-validated skills (requires --domain)"),
    ] = False,
) -> None:
    """
    Onboard a repository for AI code assist.
    
    ...existing docstring...
    
    Domain-aware onboarding:
        {CLI_NAME} code onboard --path ./my-repo --domain cwow-facility --use-domain-skills
    """
    
    # Validate flags
    if use_domain_skills and not domain:
        console.print("[red]--use-domain-skills requires --domain[/red]")
        raise typer.Exit(1)
    
    # ... existing code (steps 1-4) ...
    
    # NEW: Step 5 - Load domain skills
    domain_skills = {}
    if domain and use_domain_skills:
        console.print(f"[cyan]Loading domain skills for '{domain}'...[/cyan]")
        try:
            domain_skills = _load_domain_skills(domain)
            console.print(f"[green]✓[/green] Loaded {len(domain_skills)} domain skills")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not load domain skills: {e}[/yellow]")
    
    # ENHANCED: Step 6 - Match skills with domain awareness
    matches = match_skills_with_domain(
        analysis,
        registry_data,
        domain_skills=domain_skills,
        domain=domain,
        mcp_servers=mcp_servers,
    )
    
    # ... rest of flow ...
```

### 2. Create Domain Skills Loader

File: `agentic_cli/commands/code.py` (new helper function)

```python
def _load_domain_skills(domain_slug: str) -> Dict[str, Dict]:
    """
    Load domain-validated and domain-customized skills.
    
    Returns:
        {
            "pr-reviewer-domain": {
                "source": "domain",
                "validated": True,
                "validation_date": "2026-05-15",
                "path": Path,
                "metadata": {...}
            },
            ...
        }
    """
    from agentic_cli.tracker import get_domain
    
    domain = get_domain(domain_slug)
    if not domain:
        raise ValueError(f"Domain '{domain_slug}' not found")
    
    # Try to find domain-context repo
    # Option 1: Use --domain-context-repo if provided
    # Option 2: Look for .domain-context.json in current repo
    # Option 3: Query domain tracker for domain-context-repo URL
    
    domain_context_path = _find_domain_context_repo(domain_slug)
    if not domain_context_path:
        raise ValueError(f"Domain context repo not found for '{domain_slug}'")
    
    # Load skills manifest
    manifest_path = domain_context_path / ".domain" / "skills-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Skills manifest not found at {manifest_path}")
    
    manifest = json.loads(manifest_path.read_text())
    
    # Load each domain skill
    domain_skills = {}
    skills_dir = domain_context_path / ".skills"
    
    for skill_name, skill_info in manifest.get("skills", {}).items():
        skill_path = skills_dir / skill_name
        if skill_path.exists():
            skill_md = skill_path / "SKILL.md"
            if skill_md.exists():
                domain_skills[skill_name] = {
                    "source": "domain",
                    "validated": skill_info.get("validated", False),
                    "validation_date": skill_info.get("validation_date"),
                    "path": skill_path,
                    "metadata": skill_info,
                }
    
    return domain_skills
```

### 3. Enhance Skill Matching

File: `agentic_cli/analyzer/matcher.py` (new function)

```python
def match_skills_with_domain(
    analysis: ProjectAnalysis,
    registry_data: Dict,
    domain_skills: Dict[str, Dict] = None,
    domain: Optional[str] = None,
    mcp_servers: Optional[List[str]] = None,
) -> List[SkillMatch]:
    """
    Match skills with domain-aware prioritization.
    
    Priority:
    1. Domain-validated skills (highest)
    2. Domain-customized skills
    3. Generic registry skills
    4. Superpowers baseline skills (lowest)
    """
    matches = []
    domain_skills = domain_skills or {}
    mcp_servers = mcp_servers or []
    
    # Priority 1: Domain-validated skills
    for skill_name, skill_info in domain_skills.items():
        if skill_info.get("validated"):
            skill_def = _load_skill_definition(skill_info["path"])
            if _matches_project(skill_def, analysis, mcp_servers):
                matches.append(SkillMatch(
                    name=skill_name,
                    source="domain-validated",
                    priority=1,
                    domain=domain,
                    metadata=skill_info,
                ))
    
    # Priority 2: Domain-customized skills
    for skill_name, skill_info in domain_skills.items():
        if not skill_info.get("validated"):
            skill_def = _load_skill_definition(skill_info["path"])
            if _matches_project(skill_def, analysis, mcp_servers):
                matches.append(SkillMatch(
                    name=skill_name,
                    source="domain-customized",
                    priority=2,
                    domain=domain,
                    metadata=skill_info,
                ))
    
    # Priority 3: Generic registry skills
    for skill_name, skill_def in registry_data.items():
        if _matches_project(skill_def, analysis, mcp_servers):
            # Skip if already matched from domain
            if not any(m.name == skill_name for m in matches):
                matches.append(SkillMatch(
                    name=skill_name,
                    source="registry",
                    priority=3,
                ))
    
    return sorted(matches, key=lambda m: m.priority)
```

### 4. Generate Domain Skills Skill

File: `agentic_cli/commands/code.py` (new helper function)

```python
def _generate_domain_skills_skill(
    project_path: Path,
    domain_slug: str,
    installed_domain_skills: List[str],
) -> None:
    """
    Generate .skills/domain-skills/SKILL.md listing domain-specific skills.
    """
    skills_dir = project_path / ".skills" / "domain-skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    skill_md = skills_dir / "SKILL.md"
    
    content = f"""---
name: domain-skills
version: 1.0.0
description: Domain-specific skills for {domain_slug}
tags: [domain, {domain_slug}]
---

# Domain Skills for {domain_slug}

This skill aggregates domain-validated and domain-customized skills
for the **{domain_slug}** domain.

## Installed Skills

"""
    
    for skill_name in installed_domain_skills:
        content += f"- **{skill_name}**: Domain-specific skill\n"
    
    content += f"""

## Using Domain Skills

These skills are automatically installed and configured for {domain_slug}.

For more information, see the domain-context repository:
- Skills manifest: `.domain/skills-manifest.json`
- Skills evolution: `.domain/skills-evolution.json`

## Validation Status

See `.domain/skills-manifest.json` for validation status of each skill.

## Contributing Back

To contribute validated skills back to superpowers:

```bash
dva domain contribute-skill {domain_slug} --skill <skill-name>
```
"""
    
    skill_md.write_text(content)
```

### 5. Enhanced Manifest

File: `agentic_cli/commands/code.py` (update `_save_onboard_manifest`)

```python
def _save_onboard_manifest(
    project_path: Path,
    analysis: ProjectAnalysis,
    installed_names: List[str],
    suggested_names: List[str],
    domain: Optional[str] = None,
    domain_skills: Optional[List[str]] = None,
) -> None:
    """
    Save onboard manifest with domain information.
    """
    manifest = {
        "project": project_path.name,
        "tech_stack": analysis.tech_stack,
        "installed_skills": installed_names,
        "suggested_skills": suggested_names,
    }
    
    # NEW: Add domain information
    if domain:
        manifest["domain"] = domain
        manifest["domain_skills"] = domain_skills or []
    
    manifest_path = project_path / ".onboard-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
```

---

## Example Usage

### Scenario: Onboard cwow-facility-service with Domain Skills

```bash
# Step 1: Create domain-context repo (one-time)
dva domain init-context cwow-facility \
  --git-remote https://github.com/company/cwow-facility-domain-context.git \
  --bootstrap-skills superpowers

# Step 2: Validate skills (ongoing)
dva domain validate-skills cwow-facility \
  --skill pr-reviewer \
  --task "Review PR #123" \
  --feedback "works"

# Step 3: Onboard repo with domain skills
dva code onboard --path ./cwow-facility-service \
  --domain cwow-facility \
  --use-domain-skills

# Output:
# ✓ Analyzing cwow-facility-service...
# ✓ Loading domain skills for 'cwow-facility'...
# ✓ Loaded 3 domain skills
# ✓ Matched skills (priority order):
#   1. pr-reviewer-domain (domain-validated)
#   2. test-generator-domain (domain-customized)
#   3. doc-generator (generic registry)
# ✓ Generated project-context skill
# ✓ Installed 3 domain skills + 1 generic skill
# ✓ Generated .skills/domain-skills/SKILL.md
# ✓ Saved .onboard-manifest.json
```

### Resulting Repo Structure

```
cwow-facility-service/
├── .skills/
│   ├── project-context/
│   │   └── SKILL.md
│   ├── domain-skills/
│   │   └── SKILL.md                    ← NEW: Lists domain skills
│   ├── pr-reviewer-domain/             ← Domain-validated
│   │   └── SKILL.md
│   ├── test-generator-domain/          ← Domain-customized
│   │   └── SKILL.md
│   └── doc-generator/                  ← Generic registry
│       └── SKILL.md
├── .domain-context.json                ← References domain-context repo
├── .onboard-manifest.json              ← Enhanced with domain info
└── [project files]
```

---

## Testing Strategy

### Unit Tests
- Test `_load_domain_skills()` with various manifest formats
- Test `match_skills_with_domain()` with different priority scenarios
- Test domain skill filtering and prioritization

### Integration Tests
- Create test domain-context repo with sample skills
- Onboard test project with `--domain --use-domain-skills`
- Verify correct skills are installed in priority order
- Verify manifest and domain-skills skill are generated correctly

### End-to-End Tests
- Create real domain-context repo with superpowers skills
- Validate a skill
- Fork a skill
- Onboard multiple repos
- Verify all repos have consistent domain skills

---

## Backward Compatibility

The changes are fully backward compatible:
- Existing `code onboard` without `--domain` works as before
- `--use-domain-skills` requires `--domain` (validated)
- Domain skills are optional enhancement
- Generic registry skills still work as fallback

---

## Performance Considerations

- **Domain Skills Loading**: Cache manifest in memory during onboard
- **Skill Matching**: O(n) where n = total skills (domain + registry)
- **Manifest Generation**: Minimal overhead
- **Git Submodule Updates**: Only on first domain-context load

---

## Future Enhancements

1. **Skill Recommendations**: AI-powered skill gap detection for domain
2. **Skill Versioning**: Track skill versions and compatibility
3. **Skill Dependencies**: Handle skill-to-skill dependencies
4. **Skill Metrics**: Track skill usage and effectiveness per domain
5. **Skill Marketplace**: Discover and share domain skills across organizations

---

## References

- **Domain Skills Integration Plan**: `doc/DOMAIN_SKILLS_INTEGRATION_PLAN.md`
- **Superpowers Reference**: `doc/SUPERPOWERS_INTEGRATION_REFERENCE.md`
- **Current Code Onboard**: `agentic_cli/commands/code.py`
- **Skill Matching**: `agentic_cli/analyzer/matcher.py`
