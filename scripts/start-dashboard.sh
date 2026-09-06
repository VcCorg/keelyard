#!/usr/bin/env bash
#
# Agentic Platform — Start All Services
#
# Usage:
#   ./scripts/start-dashboard.sh          # Start everything (MCP + backend + frontend)
#   ./scripts/start-dashboard.sh --no-mcp # Skip MCP servers (backend + frontend only)
#   ./scripts/start-dashboard.sh --stop   # Stop all services
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
MCP_DIR="$ROOT_DIR/mcp-servers"
NEO4J_DIR="$ROOT_DIR/kg-infrastructure/neo4j"
BACKEND_DIR="$ROOT_DIR/dashboard/backend"
FRONTEND_DIR="$ROOT_DIR/dashboard/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

BACKEND_PORT=8000
FRONTEND_PORT=5173

log()  { echo -e "${CYAN}[agent]${NC} $1"; }
ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
err()  { echo -e "${RED}  ✗${NC} $1"; }

# ─── NVM helper ───────────────────────────────────────────────────────────
load_nvm() {
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        . "$NVM_DIR/nvm.sh"
        nvm use 22 --silent 2>/dev/null || nvm use node --silent 2>/dev/null || true
    fi
}

# ─── Stop everything ─────────────────────────────────────────────────────
stop_all() {
    log "${BOLD}Stopping Agentic Platform...${NC}"

    # Frontend
    if lsof -ti:$FRONTEND_PORT &>/dev/null; then
        kill $(lsof -ti:$FRONTEND_PORT) 2>/dev/null && ok "Frontend stopped (port $FRONTEND_PORT)"
    fi

    # Backend
    if lsof -ti:$BACKEND_PORT &>/dev/null; then
        kill $(lsof -ti:$BACKEND_PORT) 2>/dev/null && ok "Backend stopped (port $BACKEND_PORT)"
    fi

    # MCP servers
    if [ -f "$MCP_DIR/docker-compose.yml" ]; then
        log "Stopping MCP containers..."
        (cd "$MCP_DIR" && docker compose down 2>/dev/null) && ok "MCP servers stopped" || warn "MCP not running"
    fi

    # Neo4j
    if [ -f "$NEO4J_DIR/docker-compose.yml" ]; then
        log "Stopping Neo4j..."
        (cd "$NEO4J_DIR" && docker compose down 2>/dev/null) && ok "Neo4j stopped" || warn "Neo4j not running"
    fi

    ok "All services stopped"
    exit 0
}

# ─── Parse args ───────────────────────────────────────────────────────────
SKIP_MCP=false
for arg in "$@"; do
    case "$arg" in
        --no-mcp)  SKIP_MCP=true ;;
        --stop)    stop_all ;;
        --help|-h) echo "Usage: $0 [--no-mcp] [--stop]"; exit 0 ;;
    esac
done

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     Agentic Platform — Startup       ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ─── Preflight checks ────────────────────────────────────────────────────
log "${BOLD}Preflight checks...${NC}"

if [ ! -d "$VENV_DIR" ]; then
    err "Python venv not found at $VENV_DIR"
    err "Run: cd $ROOT_DIR && uv venv && uv sync"
    exit 1
fi
ok "Python venv found"

if ! command -v docker &>/dev/null; then
    warn "Docker not found — MCP servers will be skipped"
    SKIP_MCP=true
else
    ok "Docker available"
fi

load_nvm
# Numeric, and against the toolchain's real range. The previous check compared
# version strings lexically, so "v8" sorted after "v20" and Node 8 or 9 passed a
# gate that existed to require 20+.
# shellcheck source=lib/require-node.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/require-node.sh"
keel_require_node
ok "Node.js $(node --version)"

# ─── Step 1: MCP Servers ─────────────────────────────────────────────────
if [ "$SKIP_MCP" = false ]; then
    log "${BOLD}Step 1/3: Starting MCP servers...${NC}"

    # Ensure docker network exists
    docker network create agentic-network 2>/dev/null || true

    # Start Neo4j (required by memory-mcp)
    if [ -f "$NEO4J_DIR/docker-compose.yml" ]; then
        log "Starting Neo4j..."
        (cd "$NEO4J_DIR" && docker compose up -d 2>&1 | tail -3) || warn "Neo4j may have failed"
        # Wait for Neo4j health before starting MCP servers
        for i in $(seq 1 12); do
            NEO4J_STATUS=$(docker inspect neo4j --format '{{.State.Health.Status}}' 2>/dev/null || echo "starting")
            if [ "$NEO4J_STATUS" = "healthy" ]; then ok "Neo4j healthy"; break; fi
            if [ $i -eq 12 ]; then warn "Neo4j not healthy yet — continuing anyway"; fi
            sleep 5
        done
    fi

    if [ -f "$MCP_DIR/docker-compose.yml" ]; then
        MCP_SERVICES="bitbucket-mcp glean-mcp jira-mcp confluence-mcp memory-mcp kg-mcp mcp-gateway mcp-proxy"
        log "Starting MCP: $MCP_SERVICES"
        (cd "$MCP_DIR" && docker compose up -d --build $MCP_SERVICES 2>&1 | tail -5) || warn "Some MCP containers may have failed"
        ok "MCP containers started"

        # Wait for health
        log "Waiting for MCP health checks (up to 60s)..."
        TIMEOUT=60
        ELAPSED=0
        while [ $ELAPSED -lt $TIMEOUT ]; do
            HEALTHY=$(cd "$MCP_DIR" && docker compose ps --format json $MCP_SERVICES 2>/dev/null | python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
healthy = sum(1 for l in lines if l.strip() and json.loads(l).get('Health','') == 'healthy')
print(healthy)
" 2>/dev/null || echo 0)
            TOTAL=8  # 8 MCP services
            echo -ne "\r  Healthy: $HEALTHY/$TOTAL  (${ELAPSED}s)"
            if [ "$HEALTHY" = "$TOTAL" ] && [ "$TOTAL" != "0" ]; then
                echo ""
                ok "All $TOTAL MCP servers healthy"
                break
            fi
            sleep 5
            ELAPSED=$((ELAPSED + 5))
        done
        if [ $ELAPSED -ge $TIMEOUT ]; then
            echo ""
            warn "Timeout — some MCP servers may not be healthy yet"
        fi
    else
        warn "docker-compose.yml not found in $MCP_DIR"
    fi
else
    log "${BOLD}Step 1/3: Skipping MCP servers (--no-mcp)${NC}"
fi

# ─── Step 2: Backend ─────────────────────────────────────────────────────
log "${BOLD}Step 2/3: Starting backend (port $BACKEND_PORT)...${NC}"

# Kill existing
if lsof -ti:$BACKEND_PORT &>/dev/null; then
    kill $(lsof -ti:$BACKEND_PORT) 2>/dev/null
    sleep 1
    warn "Killed existing process on port $BACKEND_PORT"
fi

# Install backend + CLI into venv
"$VENV_DIR/bin/pip" install -q -e "$ROOT_DIR/agentic-cli" -e "$BACKEND_DIR" 2>/dev/null

# Start backend (must cd into backend dir for relative imports)
mkdir -p "$ROOT_DIR/logs"
(cd "$BACKEND_DIR" && "$VENV_DIR/bin/uvicorn" src.api.main:app \
    --reload \
    --port $BACKEND_PORT \
    --log-level info \
    > "$ROOT_DIR/logs/backend.log" 2>&1) &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2
for i in $(seq 1 15); do
    if curl -s "http://localhost:$BACKEND_PORT/api/health" &>/dev/null; then
        ok "Backend running (PID $BACKEND_PID)"
        break
    fi
    if [ $i -eq 15 ]; then
        err "Backend failed to start. Check logs/backend.log"
        exit 1
    fi
    sleep 1
done

# ─── Step 3: Frontend ────────────────────────────────────────────────────
log "${BOLD}Step 3/3: Starting frontend (port $FRONTEND_PORT)...${NC}"

# Kill existing
if lsof -ti:$FRONTEND_PORT &>/dev/null; then
    kill $(lsof -ti:$FRONTEND_PORT) 2>/dev/null
    sleep 1
    warn "Killed existing process on port $FRONTEND_PORT"
fi

# Install deps if needed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log "Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# Start Vite dev server
(cd "$FRONTEND_DIR" && npm run dev) > "$ROOT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!

# Wait for frontend
sleep 3
for i in $(seq 1 10); do
    if curl -s "http://localhost:$FRONTEND_PORT" &>/dev/null; then
        ok "Frontend running (PID $FRONTEND_PID)"
        break
    fi
    if [ $i -eq 10 ]; then
        warn "Frontend may still be starting. Check logs/frontend.log"
    fi
    sleep 1
done

# ─── Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║     Agentic Platform Ready!                  ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Dashboard:${NC}  http://localhost:$FRONTEND_PORT"
echo -e "  ${BOLD}Backend:${NC}    http://localhost:$BACKEND_PORT/api/health"
if [ "$SKIP_MCP" = false ]; then
echo -e "  ${BOLD}MCP Gateway:${NC} http://localhost:9090/sse"
fi
echo ""
echo -e "  ${BOLD}Logs:${NC}"
echo -e "    Backend:  $ROOT_DIR/logs/backend.log"
echo -e "    Frontend: $ROOT_DIR/logs/frontend.log"
echo ""
echo -e "  ${BOLD}Stop:${NC} $0 --stop"
echo ""
