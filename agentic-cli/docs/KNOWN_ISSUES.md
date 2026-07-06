# Known Issues

## Help Display Error (Non-Breaking)

### Issue
Running `keel --help` or `keel <command> --help` shows a TypeError:
```
TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'
```

### Impact
- **Commands still work perfectly** - This only affects help display
- All functionality is intact
- Users can still use all commands without issues

### Cause
This is a known compatibility issue between Typer and Click when using `Optional[str]` type hints with `typer.Option()`. The issue occurs in the help rendering system but doesn't affect command execution.

### Workaround
Instead of using `--help`, refer to this documentation or the README for command usage.

### Commands That Work (Despite Help Error)

All commands function correctly:

```bash
# Project commands
`agent project create my-project
`agent project list-templates
`agent project info
`agent project run
`agent project run --script examples/demo.py
`agent project agent list
`agent project agent info AgentName

# KG commands  
`agent kg init --provider neo4j
`agent kg config --show
`agent kg ingest document.pdf
`agent kg query "Find all people"
`agent kg stats

# Init commands
`agent init vertex-ai --project-id PROJECT_ID
`agent init show
```

### Command Reference

#### Project Commands
```bash
# Create new project
`agent project create <name> [--path PATH] [--agent-type adk]

# List templates
`agent project list-templates

# Show project info
`agent project info [--path PATH]

# Run project
`agent project run [--path PATH] [--script SCRIPT] [--agent AGENT]

# List agents
`agent project agent list [--path PATH]

# Show agent info
`agent project agent info <agent_name> [--path PATH]
```

#### Knowledge Graph Commands
```bash
# Initialize KG
`agent kg init --provider neo4j [--uri URI] [--username USER] [--password PASS]

# Show config
`agent kg config --show

# Ingest data
`agent kg ingest <source> [--format FORMAT] [--extract-entities] [--build-relationships]

# Query graph
`agent kg query <query_string>

# Search
`agent kg search <term> [--semantic] [--exact]

# Statistics
`agent kg stats

# Visualize
`agent kg visualize [--output FILE]
```

#### Init Commands
```bash
# Configure Vertex AI
`agent init vertex-ai --project-id PROJECT_ID [--location LOCATION] [--model MODEL]

# Show configuration
`agent init show

# Reset configuration
`agent init reset
```

### Resolution Plan
This will be fixed in a future release by either:
1. Upgrading to a newer version of Typer that fixes this issue
2. Refactoring Optional parameters to use a different pattern
3. Adding custom help rendering

### Testing
To verify commands work despite the help error:
```bash
# These all work correctly
`agent project create test-proj
`agent project agent list
`agent kg stats
`agent init show
```

## Summary
**Status**: Known, Non-Breaking
**Priority**: Low (cosmetic issue only)
**Workaround**: Use commands directly without --help flag
**All functionality**: ✅ Working correctly
