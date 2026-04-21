# Vertex AI Configuration Reuse Update

## Summary

Enhanced the `dva init vertex-ai` command to automatically reuse existing configurations. The command now only prompts for missing values when no configuration exists, making it much easier to refresh authentication or update specific settings.

## Changes Made

### 1. Command Behavior (`src/dva_agentic_cli/commands/init.py`)

**Before:**
- Always prompted for project ID (required parameter)
- All other parameters had hardcoded defaults
- No awareness of existing configuration

**After:**
- Loads existing configuration at startup
- Only prompts for project ID if no existing config found
- Reuses all existing values (project_id, location, model, credentials_path)
- All CLI parameters are now optional
- Shows message when reusing existing project ID

### 2. User Experience Improvements

**First Time Setup:**
```bash
# Prompts for project ID, uses defaults for others
dva init vertex-ai
# Enter your Google Cloud Project ID: my-project-123
# Runs gcloud auth...
# Saves configuration
```

**Subsequent Runs:**
```bash
# Reuses all existing config, only refreshes auth
dva init vertex-ai
# Using existing project ID: my-project-123
# Runs gcloud auth...
# Configuration updated
```

**Selective Updates:**
```bash
# Update only location, keep everything else
dva init vertex-ai --location us-east1

# Update model, keep everything else
dva init vertex-ai --model gemini-1.5-pro

# Skip auth if already authenticated
dva init vertex-ai --skip-auth
```

### 3. Implementation Details

**Configuration Loading:**
- Loads `~/.dva-agentic/config.json` at command start
- Extracts existing Google config if present
- Uses existing values as defaults for all parameters

**Parameter Resolution Order:**
1. CLI argument (if provided)
2. Existing config value (if available)
3. Hardcoded default (if no existing value)
4. Prompt user (only for project_id if no existing value)

**Default Values:**
- `project_id`: Existing → Prompt (no default)
- `location`: Existing → "us-central1"
- `model`: Existing → "gemini-pro"
- `credentials_path`: Existing → "" (empty)

### 4. Documentation Updates

Updated the following files:

- **README.md**: Added examples showing config reuse workflow
- **docs/VERTEX_AI_SETUP.md**: 
  - Updated Basic Usage section with reuse examples
  - Clarified that all options are optional
  - Explained default value resolution

## Benefits

1. **Simplified Workflow**: Run `dva init vertex-ai` without parameters to refresh auth
2. **No Repetition**: Don't need to re-enter project ID every time
3. **Selective Updates**: Change only what you need
4. **Better UX**: Less typing, fewer prompts
5. **Backward Compatible**: Can still provide all parameters explicitly

## Use Cases

### Refresh Authentication
```bash
# Just refresh the auth token, keep all settings
dva init vertex-ai
```

### Switch Regions
```bash
# Change region for a specific task
dva init vertex-ai --location europe-west1
```

### Update Model
```bash
# Try a different model
dva init vertex-ai --model gemini-1.5-flash
```

### Switch Projects
```bash
# Work with a different project
dva init vertex-ai --project-id another-project-456
```

### Skip Auth During Testing
```bash
# Skip auth when testing other changes
dva init vertex-ai --skip-auth
```

## Technical Details

### Code Changes

**Parameter Definitions:**
- Removed `prompt` from project_id parameter
- Changed all default values from hardcoded to empty strings
- Made all parameters truly optional

**Configuration Logic:**
```python
# Load existing configuration
config = load_config()
existing_google_config = config.get("google", {})

# Use existing values as defaults if not provided via CLI
if not project_id:
    existing_project_id = existing_google_config.get("project_id", "")
    if existing_project_id:
        console.print(f"[dim]Using existing project ID: {existing_project_id}[/dim]")
        project_id = existing_project_id
    else:
        project_id = Prompt.ask("Enter your Google Cloud Project ID")

if not location:
    location = existing_google_config.get("location", "us-central1")

if not model:
    model = existing_google_config.get("model", "gemini-pro")

if not credentials_path:
    credentials_path = existing_google_config.get("credentials_path", "")
```

### Configuration Storage

Configuration is stored in `~/.dva-agentic/config.json`:
```json
{
  "google": {
    "project_id": "my-project-123",
    "location": "us-central1",
    "model": "gemini-pro",
    "credentials_path": ""
  }
}
```

## Testing

Verified the following scenarios:
- ✅ First time setup prompts for project ID
- ✅ Subsequent runs reuse existing config
- ✅ Shows message when reusing project ID
- ✅ CLI parameters override existing values
- ✅ Selective parameter updates work correctly
- ✅ Authentication still runs by default
- ✅ --skip-auth flag works as expected
- ✅ Help text shows all parameters as optional

## Migration Guide

**No breaking changes** - The command is fully backward compatible.

**Old usage still works:**
```bash
# Explicit parameters still work
dva init vertex-ai --project-id PROJECT_ID --location us-central1
```

**New simplified usage:**
```bash
# First time
dva init vertex-ai
# Enter your Google Cloud Project ID: PROJECT_ID

# Subsequent runs
dva init vertex-ai  # Just refreshes auth
```

## Files Modified

1. `src/dva_agentic_cli/commands/init.py` - Core implementation
2. `README.md` - Updated examples
3. `docs/VERTEX_AI_SETUP.md` - Updated documentation

## Future Enhancements

Potential improvements:
- Add `--force-prompt` flag to re-prompt for all values
- Show diff of what changed after update
- Add `--show-defaults` to preview what values will be used
- Validate credentials before saving
- Support for multiple named configurations (profiles)
