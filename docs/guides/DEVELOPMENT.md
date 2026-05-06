# Development Guide

## Code Changes & Installation

When making changes to the CLI source code, you need to reinstall to see the changes take effect.

### After Code Changes

1. **Use the updated install script** (recommended):
   ```bash
   ./install-agentic-cli.sh --global --force
   ```

2. **Development mode** (for frequent changes):
   ```bash
   ./install-agentic-cli.sh --global --dev
   ```

### Manual Fix Process (if install script fails)

If changes don't take effect after installation, you may need to fix the installed package directly:

```bash
# Find installed package location
find /Users/your-user/.local/share/uv/tools/agentic-cli -name "*.py" -exec grep -l "PATTERN_TO_FIX" {} \;

# Apply fixes directly to installed files
sed -i '' 's/OLD_PATTERN/NEW_PATTERN/g' /Users/your-user/.local/share/uv/tools/agentic-cli/lib/python3.13/site-packages/agentic_cli/PATH/TO/FILE.py
```

### Common Issues

1. **Console.print() flush error**: Remove `flush=True` from console.print() calls
2. **Environment isolation**: Dependencies must be installed with `--with` flag for global installations
3. **Source not updating**: Use `--force` flag to ensure latest source is used

### Installation Modes

- **Standard**: `./install-agentic-cli.sh --global`
- **With dependencies**: `./install-agentic-cli.sh --global --with PACKAGE`
- **Development**: `./install-agentic-cli.sh --global --dev`
- **Force reinstall**: `./install-agentic-cli.sh --global --force`

The install script now automatically handles most of these scenarios.
