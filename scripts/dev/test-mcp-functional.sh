#!/usr/bin/env bash
# MCP Services Functional Test
# Tests container status and MCP protocol connectivity

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}▸${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }
log_header(){ echo -e "\n${BOLD}$*${NC}\n"; }

log_header "MCP Services Functional Test"

# Step 1: Check container status
echo "Step 1: Checking container status..."
echo ""

CORE_SERVICES=(bitbucket-mcp glean-mcp jira-mcp confluence-mcp)
SERVICE_PORTS=(
    "bitbucket-mcp:8126"
    "glean-mcp:8127"
    "jira-mcp:8128"
    "confluence-mcp:8129"
)

pass=0
fail=0

for svc in "${CORE_SERVICES[@]}"; do
    port=""
    for entry in "${SERVICE_PORTS[@]}"; do
        if [[ "$entry" == "$svc:"* ]]; then
            port="${entry#*:}"
            break
        fi
    done

    if [[ -z "$port" ]]; then
        log_warn "$svc — unknown port, skipping"
        continue
    fi

    # Check if container is running
    container_status=$(docker ps --filter "name=dva-${svc}" --format "{{.Status}}" 2>/dev/null || echo "not found")

    if [[ "$container_status" == *"Up"* ]]; then
        log_ok "$svc — running (port $port)"
        ((pass++))
    else
        log_error "$svc — container not running ($container_status)"
        ((fail++))
    fi
done

echo ""
echo -e "${BOLD}Container Status:${NC} ${GREEN}${pass} passed${NC}, ${RED}${fail} failed${NC}"

if [[ $fail -gt 0 ]]; then
    echo ""
    log_error "Some containers are not running. Skipping protocol test."
    exit 1
fi

# Step 2: Test MCP protocol
echo ""
echo "Step 2: Testing MCP protocol connectivity..."
echo ""

if command -v python3 &> /dev/null; then
    if python3 "$SCRIPT_DIR/test-mcp-protocol.py"; then
        log_ok "MCP protocol test passed"
    else
        log_error "MCP protocol test failed"
        exit 1
    fi
else
    log_warn "python3 not found, skipping protocol test"
    log_info "Install Python 3 to test MCP protocol connectivity"
fi

echo ""
log_header "All tests passed"
