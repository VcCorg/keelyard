# AI Context Files — What Goes Where and Why

This documents the context file strategy for the Agentic Platform workspace, explaining which files each AI coding tool reads and how they relate.

## Architecture: Single Source of Truth + Tool-Specific Pointers

```
.skills/dva-agentic-platform/SKILL.md   ← SINGLE SOURCE OF TRUTH (comprehensive)
├── CLAUDE.md                            ← Pointer for Claude Code
├── .cursorrules                         ← Pointer for Cursor
├── .opencode/agent/dva-platform.md      ← Pointer for OpenCode (agent format)
├── .opencode/mcp.json                   ← MCP connections (OpenCode format)
├── .windsurf/mcp_config.json            ← MCP connections (Windsurf format)
└── .windsurf/workflows/*.md             ← Windsurf slash-command workflows
```

**Rule:** All project context lives in `SKILL.md`. Other files are thin pointers that say "read the SKILL.md" plus any tool-specific config (like MCP connection format).

## What Each Tool Reads

| AI Tool | Context Entrypoint | MCP Config | Agent Definition |
|---------|-------------------|------------|-----------------|
| **Any** (agentskills.io standard) | `.skills/<name>/SKILL.md` | — | — |
| **Windsurf / Cascade** | `.skills/` + `.windsurf/workflows/` | `.windsurf/mcp_config.json` | — |
| **OpenCode** | `.skills/` (if supported) | `.opencode/mcp.json` or `~/.config/opencode/config.json` | `.opencode/agent/<name>.md` |
| **Claude Code** | `CLAUDE.md` at project root | `.mcp.json` at project root | — |
| **Cursor** | `.cursorrules` at project root | — | — |
| **VS Code Copilot** | `.skills/` (agentskills.io) | — | — |

## File Details

### `.skills/dva-agentic-platform/SKILL.md` — The Source of Truth

- **Format:** agentskills.io standard (YAML frontmatter + markdown)
- **Size:** ~280 lines
- **Contains:** All 4 repos, 9 CLI command groups, 8 MCP servers with ports/tools, KG infrastructure, port map, config file locations, key workflows, design decisions, files-to-read-first
- **When to update:** Whenever you add a new repo, MCP server, CLI command group, or make a significant architecture change
- **Who reads it:** Any tool that supports the agentskills.io standard (Claude Code, OpenCode, VS Code Copilot, Windsurf)

### `CLAUDE.md` — Claude Code Entrypoint

- **Format:** Plain markdown
- **Size:** ~30 lines
- **Contains:** Quick reference table + "read the SKILL.md" pointer + workspace rules
- **When to update:** Only if the quick reference summary changes
- **Optional:** Remove if you don't use Claude Code

### `.cursorrules` — Cursor Entrypoint

- **Format:** Plain text
- **Size:** ~10 lines
- **Contains:** Compact summary + "read the SKILL.md" pointer
- **When to update:** Only if the tech stack summary changes
- **Optional:** Remove if you don't use Cursor

### `.opencode/agent/dva-platform.md` — OpenCode Agent

- **Format:** YAML frontmatter + markdown (OpenCode agent format)
- **Size:** ~60 lines
- **Contains:** Agent metadata + "read the SKILL.md" pointer + common task recipes
- **Invoked via:** `@dva-platform` in OpenCode TUI
- **When to update:** Only if common task recipes change
- **Required:** Yes, if you use OpenCode — it doesn't auto-discover `.skills/`

### `.opencode/mcp.json` — OpenCode MCP Connections

- **Format:** JSON (`"mcp"` key, `type: "remote"` for SSE)
- **Contains:** All 6 MCP server SSE URLs
- **When to update:** When adding/removing/moving an MCP server
- **Required:** Yes, if you use OpenCode with MCP tools

### `.windsurf/mcp_config.json` — Windsurf MCP Connections

- **Format:** JSON (`"mcpServers"` key, `transport: "sse"`)
- **Contains:** All 6 active MCP servers + gateway (disabled)
- **When to update:** When adding/removing/moving an MCP server
- **Required:** Yes, if you use Windsurf with MCP tools

### `.windsurf/workflows/*.md` — Windsurf Slash Commands

- **`context.md`** → `/context` — Bootstrap workflow for new sessions
- **`agents.md`** → `/agents` — Agent management commands reference
- **When to update:** When workflows or commands change

## Maintenance Rules

1. **Edit SKILL.md first** — It's the source of truth. All other files point to it.
2. **MCP configs are separate** — Each tool has its own JSON format. These are NOT duplicates of SKILL.md; they're connection configs.
3. **Pointer files rarely change** — `CLAUDE.md`, `.cursorrules`, and the OpenCode agent only need updates if the high-level summary changes.
4. **Adding a new MCP server** — Update both `.opencode/mcp.json` and `.windsurf/mcp_config.json` (different JSON formats).
5. **Adding a new repo** — Update `SKILL.md` only. Pointer files reference it.
6. **Don't duplicate context** — If you find yourself writing the same information in two places, put it in SKILL.md and point to it.

## Which Files to Keep

| If you use... | Keep these | Can remove |
|---------------|-----------|------------|
| Windsurf only | `.skills/`, `.windsurf/` | `CLAUDE.md`, `.cursorrules`, `.opencode/` |
| OpenCode only | `.skills/`, `.opencode/` | `CLAUDE.md`, `.cursorrules`, `.windsurf/` |
| Windsurf + OpenCode | `.skills/`, `.windsurf/`, `.opencode/` | `CLAUDE.md`, `.cursorrules` |
| All tools | Everything | Nothing |

## Adding a New AI Tool

If a new tool arrives that doesn't read `.skills/`:

1. Find what file it reads for context (check its docs)
2. Create a minimal pointer file that says "read `.skills/dva-agentic-platform/SKILL.md`"
3. If it has its own MCP config format, create that too
4. Document it in this file
