# DVA Dashboard — Build Progress

## Decisions
| Decision | Choice |
|----------|--------|
| Stack | FastAPI backend + React SPA (Vite + TailwindCSS + shadcn/ui) |
| Backend approach | Hybrid — import CLI modules for reads, subprocess for mutations |
| Scope (v1) | Agents + MCP servers + Activity feed + Interactive Chat |
| Status updates | SSE for log streaming, REST polling for status |
| Chat transport | WebSocket (bidirectional) |
| Chat engine | Google ADK AgentRunner with MCP tool bridge |
| Chat UX | Full transparency — thinking panel with tool calls |
| Agent types | Interactive (chat-enabled) vs Background (daemon, logs only) |
| Auth | None for v1 (local only) |

## Phases

### Phase 1: Backend Skeleton ✅ DONE
- [x] pyproject.toml with FastAPI + deps
- [x] FastAPI app with CORS, SSE support
- [x] Agent service (reads ~/.dva/agents/running.json, discovers projects)
- [x] MCP service (reads config, Docker health, tools)
- [x] Activity service (reads from tracker)
- [x] Agent API routes: GET /api/agents, GET /api/agents/:name, POST start/stop
- [x] MCP API routes: GET /api/mcp/servers, GET /api/mcp/health, POST start/stop
- [x] Activity API routes: GET /api/activity, GET /api/activity/stats
- [x] Log streaming: GET /api/agents/:name/logs (SSE), GET /api/mcp/:name/logs (SSE)
- [x] GET /api/overview endpoint for dashboard home page

### Phase 2: Frontend Skeleton ✅ DONE
- [x] Vite + React + TypeScript scaffold (Node 22 required)
- [x] TailwindCSS v4 via @tailwindcss/vite plugin
- [x] React Router with layout shell (sidebar nav: Dashboard, Agents, MCP, Activity, Chat)
- [x] API client (typed fetch wrapper, all endpoints)
- [x] Hooks: usePolling (generic interval refresh), useSSE (EventSource log streaming)
- [x] Vite proxy: /api -> localhost:8000

### Phase 3: Agent Management Pages ✅ DONE
- [x] Agent list with status badges (running/stopped)
- [x] Start/stop controls per agent
- [x] Agent detail: path, PID, review mode, poll interval, agent type badge
- [x] Chat button for interactive agents (opens /chat?agent=name)
- [x] Live log viewer (SSE-powered, auto-scroll)

### Phase 4: MCP Server Management ✅ DONE
- [x] Server grid (2-col) with health status badges
- [x] Port, URL, type display per server
- [x] Start/stop Docker services
- [x] Docker log viewer (SSE-powered)

### Phase 5: Activity Feed ✅ DONE
- [x] Activity timeline with command/subcommand, status, duration
- [x] Filter bar by command type (all, agent, code, project, kg, mcp, skill, data)
- [x] Dashboard overview with stat cards linking to each section

### Phase 6: Chat Backend ✅ DONE
- [x] MCP tool bridge via ADK MCPToolset (SSE connections to all 6 MCP servers)
- [x] ADK Agent + Runner integration (google-adk 1.0.0, Gemini model)
- [x] WebSocket endpoint: /api/chat/{session_id}/stream (bidirectional streaming)
- [x] Chat session management: create, list, delete, history REST endpoints
- [x] Event streaming protocol: thinking_start, tool_call, tool_result, thinking_end, agent_response, agent_response_end, error

### Phase 7: Chat UI ✅ DONE
- [x] ChatWindow with message list, textarea input, WebSocket connection
- [x] MessageBubble component (user/agent with avatars, timestamps, streaming cursor)
- [x] ThinkingPanel with collapsible tool call cards (expandable args/results)
- [x] ToolCallCard with animated spinner during execution, checkmark on completion
- [x] Session sidebar with create/delete, active session highlight
- [x] Pop-out to new window support
- [x] Vite WS proxy for dev: /api proxied with ws:true

## Management View (Team) — Plan: ~/.windsurf/plans/agentplayground-management-view-ab117b.md
Hybrid/phased: per-user local app + shared layer; Jira-synced tasks (anchor MCP).

### P0: Nav restructure + local identity ✅ DONE (frontend only)
- [x] `context/UserContext.tsx` — local current_user seam (localStorage profile, role) + workspace lens ("mine"/"team"). Single seam for future SSO swap.
- [x] `components/Layout.tsx` — grouped sidebar (Overview/Work/Build/Knowledge/Platform/Admin), collapsible sections, workspace switcher, user footer. Groups filter by lens + minRole.
- [x] `components/PlaceholderPage.tsx` — shared phased-capability placeholder.
- [x] New pages: Tasks (visual mockup w/ CWOW-271902 Heparin + Assign modal), Assignments, Sessions (fleet), People, SharedAgents, SharedKG.
- [x] `App.tsx` — UserProvider wrap + 6 new routes. `npm run build` passes (pre-existing tsconfig baseUrl deprecation only).

### NEXT (backend, not started)
- P1 Tasks read: `/api/tasks` from anchor Jira MCP + `tasks_cache` table.
- P2 Assignments + KG binding: `assignments` table, wire Assign → `devin_service.create_session` w/ resolved knowledge_ids.
- P3 Fleet sessions + `dva task status` local heartbeat.
- P4 Sharing: `/people`, `shared_kg`, `shared_agents` + Agentic MCP tools.
- P5 Graduate: swap local identity for SSO/OIDC.
