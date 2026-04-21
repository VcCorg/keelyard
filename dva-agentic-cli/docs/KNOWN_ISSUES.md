# Known Issues

## Help Display Error (Non-Breaking)

### Issue
Running `dva --help` or `dva <command> --help` shows a TypeError:
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
dva project create my-project
dva project list-templates
dva project info
dva project run
dva project run --script examples/demo.py
dva project agent list
dva project agent info AgentName

# KG commands  
dva kg init --provider neo4j
dva kg config --show
dva kg ingest document.pdf
dva kg query "Find all people"
dva kg stats

# Init commands
dva init vertex-ai --project-id PROJECT_ID
dva init show
```

### Command Reference

#### Project Commands
```bash
# Create new project
dva project create <name> [--path PATH] [--agent-type adk]

# List templates
dva project list-templates

# Show project info
dva project info [--path PATH]

# Run project
dva project run [--path PATH] [--script SCRIPT] [--agent AGENT]

# List agents
dva project agent list [--path PATH]

# Show agent info
dva project agent info <agent_name> [--path PATH]
```

#### Knowledge Graph Commands
```bash
# Initialize KG
dva kg init --provider neo4j [--uri URI] [--username USER] [--password PASS]

# Show config
dva kg config --show

# Ingest data
dva kg ingest <source> [--format FORMAT] [--extract-entities] [--build-relationships]

# Query graph
dva kg query <query_string>

# Search
dva kg search <term> [--semantic] [--exact]

# Statistics
dva kg stats

# Visualize
dva kg visualize [--output FILE]
```

#### Init Commands
```bash
# Configure Vertex AI
dva init vertex-ai --project-id PROJECT_ID [--location LOCATION] [--model MODEL]

# Show configuration
dva init show

# Reset configuration
dva init reset
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
dva project create test-proj
dva project agent list
dva kg stats
dva init show
```

## Summary
**Status**: Known, Non-Breaking
**Priority**: Low (cosmetic issue only)
**Workaround**: Use commands directly without --help flag
**All functionality**: ✅ Working correctly
