# Repository Migration Documentation

## Overview

On April 21, 2026, the Agentic Platform underwent a major repository consolidation to improve development workflow, dependency management, and version control.

## Migration Details

### From (4 separate repositories)
- **agentic-cli** - CLI tool for agent management
  - URL: `https://bitbucket.example.com/scm/~your-user/agentic-cli.git`
  - Status: **ARCHIVED** - Migration notice added

- **keel-agent-kg-infra** - Knowledge graph infrastructure  
  - URL: `https://bitbucket.example.com/scm/~your-user/keel-agent-kg-infra.git`
  - Status: **ARCHIVED** - Migration notice added

- **keel-agent-skills** - Agent skills registry
  - URL: `https://bitbucket.example.com/scm/~your-user/keel-agent-skills.git`
  - Status: **ARCHIVED** - Migration notice added

- **keel-agent-mcp-servers** - MCP servers for integrations
  - URL: `https://bitbucket.example.com/scm/~your-user/keel-agent-mcp-servers.git`
  - Status: **ARCHIVED** - Migration notice added

### To (single monorepo)
- **agentic-project** - Complete Agentic Platform
  - URL: `https://bitbucket.example.com/scm/~your-user/agentic-project.git`
  - Status: **ACTIVE** - New development location

## Repository Structure

The new monorepo maintains the same structure as the individual repositories:

```
agentic-project/
|
|--- agentic-cli/          # CLI tool (from agentic-cli)
|--- kg-infrastructure/    # KG infrastructure (from keel-agent-kg-infra)  
|--- mcp-servers/          # MCP servers (from keel-agent-mcp-servers)
|--- skills/               # Skills registry (from keel-agent-skills)
|--- dashboard/            # Dashboard application
|--- agent-templates/     # Agent development templates
|--- docs/                    # Consolidated documentation
|--- scripts/                 # Utility scripts
```

## Migration Process

1. **Removed local .git directories** from individual subfolders
2. **Initialized new git repository** at project root
3. **Created comprehensive .gitignore** covering all project types
4. **Added remote origin** to new Bitbucket repository
5. **Committed all files** with detailed migration commit message
6. **Pushed to new repository** on main branch
7. **Added migration notices** to all old repositories
8. **Updated README files** to point to new location

## Benefits of Consolidation

### Development Benefits
- **Unified version control** - Single repository for all components
- **Simplified dependency management** - Cross-project dependencies easier to manage
- **Consistent tooling** - Single set of development tools and configurations
- **Easier testing** - Integration tests across components more straightforward

### Operational Benefits
- **Single point of maintenance** - One repository to manage
- **Unified CI/CD** - Single pipeline for all components
- **Consistent documentation** - All docs in one location
- **Simplified onboarding** - New developers clone one repository

## Actions Required

### For Developers
1. **Update local repositories:**
   ```bash
   # Remove old repositories
   rm -rf agentic-cli keel-agent-kg-infra keel-agent-skills keel-agent-mcp-servers
   
   # Clone new monorepo
   git clone https://bitbucket.example.com/scm/~your-user/agentic-project.git
   cd agentic-project
   ```

2. **Update scripts and documentation** to reference new repository structure
3. **Update CI/CD pipelines** to use new repository URL

### For System Administrators
1. **Update any automated deployments** pointing to old repositories
2. **Update monitoring systems** to track new repository
3. **Archive old repositories** (already done with migration notices)

## Branch Strategy

### Old Repositories
- All branches preserved but **read-only**
- Migration notices added to main branches
- No further development planned

### New Repository  
- **main** - Primary development branch
- **develop** - Integration branch (if needed)
- **feature/*** - Feature branches
- **hotfix/*** - Emergency fixes

## Rollback Plan

If needed, the migration can be rolled back by:
1. Restoring individual repositories from Bitbucket backups
2. Updating scripts and documentation to point back to old URLs
3. Notifying team of rollback

However, this is not recommended as the consolidation provides significant benefits.

## Support

For questions or issues related to the migration:
- **Contact:** Your Name (your-user)
- **New Repository:** [agentic-project](https://bitbucket.example.com/users/your-user/repos/agentic-project/browse)

## Timeline

- **April 21, 2026** - Migration completed
- **April 21, 2026** - Old repositories archived with migration notices
- **Ongoing** - Monitor for any migration-related issues

---

**This migration represents a significant improvement in the Agentic Platform development workflow and sets the foundation for future growth.**
