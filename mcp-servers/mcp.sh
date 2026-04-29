#!/usr/bin/env bash
# Agentic MCP Servers Management Script
# Usage: ./mcp.sh <command> [service...]
#
# Commands:
#   start [service...]    Start all or specific services
#   stop [service...]     Stop all or specific services
#   restart [service...]  Restart all or specific services
#   status                Show status of all services
#   logs [service]        Tail logs for a service (default: all)
#   build [service...]    Build/rebuild Docker images
#   validate              Health-check all running services
#   clean                 Stop all and remove containers/images
#
# Services: bitbucket-mcp, glean-mcp, jira-mcp, confluence-mcp, mcp-gateway, mcp-proxy
#
# Examples:
#   ./mcp.sh start                        # Start all services
#   ./mcp.sh start bitbucket-mcp jira-mcp # Start specific services
#   ./mcp.sh validate                     # Check health of all running services
#   ./mcp.sh logs confluence-mcp          # Tail logs for confluence

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# All MCP services (excluding infra like gateway/proxy by default)
CORE_SERVICES=(bitbucket-mcp glean-mcp jira-mcp confluence-mcp)
ALL_SERVICES=(bitbucket-mcp glean-mcp jira-mcp confluence-mcp mcp-gateway mcp-proxy)

SERVICE_PORTS=(
    "bitbucket-mcp:8126"
    "glean-mcp:8127"
    "jira-mcp:8128"
    "confluence-mcp:8129"
    "mcp-gateway:9090"
    "mcp-proxy:9091"
)

get_port() {
    local svc="$1"
    for entry in "${SERVICE_PORTS[@]}"; do
        if [[ "$entry" == "$svc:"* ]]; then
            echo "${entry#*:}"
            return
        fi
    done
    echo ""
}

log_info()  { echo -e "${BLUE}▸${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }
log_header(){ echo -e "\n${BOLD}$*${NC}"; }

docker_compose() {
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

ensure_network() {
    if ! docker network inspect agentic-network &>/dev/null; then
        log_info "Creating agentic-network..."
        docker network create agentic-network
    fi
}

check_env() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error ".env file not found. Copy from .env.example:"
        echo "  cp .env.example .env"
        exit 1
    fi
}

# ── Commands ─────────────────────────────────────────────────────────────────

cmd_start() {
    check_env
    ensure_network
    local services=("${@:-${CORE_SERVICES[@]}}")
    log_header "Starting MCP services: ${services[*]}"
    docker_compose up -d --build "${services[@]}"
    echo ""
    log_info "Waiting 10s for services to initialize..."
    sleep 10
    cmd_validate "${services[@]}"
}

cmd_stop() {
    local services=("${@:-${ALL_SERVICES[@]}}")
    log_header "Stopping MCP services: ${services[*]}"
    docker_compose stop "${services[@]}"
    log_ok "Stopped."
}

cmd_restart() {
    local services=("${@:-${CORE_SERVICES[@]}}")
    cmd_stop "${services[@]}"
    cmd_start "${services[@]}"
}

cmd_status() {
    log_header "MCP Services Status"
    echo ""
    printf "${BOLD}%-20s %-12s %-8s %-30s${NC}\n" "SERVICE" "STATUS" "PORT" "ENDPOINT"
    printf "%-20s %-12s %-8s %-30s\n" "───────────────────" "───────────" "──────" "────────────────────────────"

    for svc in "${ALL_SERVICES[@]}"; do
        local port
        port=$(get_port "$svc")
        local endpoint="http://localhost:${port}/sse"
        local status

        # Check if container is running
        local container_status
        container_status=$(docker_compose ps --format '{{.State}}' "$svc" 2>/dev/null || echo "not found")

        if [[ "$container_status" == "running" ]]; then
            status="${GREEN}running${NC}"
        elif [[ "$container_status" == "not found" ]] || [[ -z "$container_status" ]]; then
            status="${RED}stopped${NC}"
        else
            status="${YELLOW}${container_status}${NC}"
        fi

        printf "%-20s %-22b %-8s %-30s\n" "$svc" "$status" "$port" "$endpoint"
    done
    echo ""
}

cmd_logs() {
    local service="${1:-}"
    if [[ -z "$service" ]]; then
        docker_compose logs -f --tail=50
    else
        docker_compose logs -f --tail=50 "$service"
    fi
}

cmd_build() {
    local services=("${@:-${CORE_SERVICES[@]}}")
    log_header "Building MCP services: ${services[*]}"
    docker_compose build "${services[@]}"
    log_ok "Build complete."
}

cmd_validate() {
    local services=("${@:-${CORE_SERVICES[@]}}")
    log_header "Validating MCP Services"
    echo ""

    local pass=0
    local fail=0

    for svc in "${services[@]}"; do
        local port
        port=$(get_port "$svc")
        if [[ -z "$port" ]]; then
            log_warn "$svc — unknown port, skipping"
            continue
        fi

        local endpoint="http://localhost:${port}/sse"

        # Check container running
        local container_status
        container_status=$(docker_compose ps --format '{{.State}}' "$svc" 2>/dev/null || echo "stopped")

        if [[ "$container_status" != "running" ]]; then
            log_error "$svc — container not running (${container_status})"
            ((fail++))
            continue
        fi

        # SSE health check: SSE endpoints stream forever (HTTP 200 + chunked),
        # so curl never finishes. Use --connect-timeout to verify the port accepts
        # connections, then --max-time to cut off the streaming response.
        # Exit code 28 (timeout) after a successful connect = healthy.
        local curl_exit http_code
        http_code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 3 "$endpoint" 2>/dev/null) && curl_exit=$? || curl_exit=$?

        if [[ "$http_code" == "200" ]] || [[ "$curl_exit" -eq 28 && "$http_code" == "200" ]]; then
            log_ok "$svc — healthy (port $port, SSE streaming)"
            ((pass++))
        elif [[ "$curl_exit" -eq 28 && ("$http_code" == "000" || -z "$http_code") ]]; then
            # Timeout before any HTTP response — port might still be starting
            log_warn "$svc — timeout connecting on port $port (may still be starting)"
            ((fail++))
        else
            log_error "$svc — unhealthy (port $port, HTTP $http_code, exit $curl_exit)"
            ((fail++))
        fi
    done

    echo ""
    echo -e "${BOLD}Results:${NC} ${GREEN}${pass} passed${NC}, ${RED}${fail} failed${NC}"

    if [[ $fail -gt 0 ]]; then
        echo ""
        log_warn "Check logs for failing services:"
        echo "  ./mcp.sh logs <service-name>"
        return 1
    fi
}

cmd_clean() {
    log_header "Cleaning up MCP services"
    docker_compose down --rmi local --remove-orphans
    log_ok "All containers and local images removed."
}

cmd_help() {
    echo -e "${BOLD}Agentic MCP Servers Management${NC}"
    echo ""
    echo "Usage: ./mcp.sh <command> [service...]"
    echo ""
    echo "Commands:"
    echo "  start [service...]    Start all or specific services (builds first)"
    echo "  stop [service...]     Stop all or specific services"
    echo "  restart [service...]  Restart all or specific services"
    echo "  status                Show status of all services"
    echo "  logs [service]        Tail logs for a service (default: all)"
    echo "  build [service...]    Build/rebuild Docker images"
    echo "  validate [service...] Health-check running services"
    echo "  clean                 Stop all, remove containers and images"
    echo ""
    echo "Services: ${ALL_SERVICES[*]}"
    echo ""
    echo "Examples:"
    echo "  ./mcp.sh start                          # Start core services"
    echo "  ./mcp.sh start bitbucket-mcp jira-mcp   # Start specific services"
    echo "  ./mcp.sh validate                       # Check health"
    echo "  ./mcp.sh logs confluence-mcp             # Tail logs"
    echo "  ./mcp.sh status                          # Show all service states"
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        start)    cmd_start "$@" ;;
        stop)     cmd_stop "$@" ;;
        restart)  cmd_restart "$@" ;;
        status)   cmd_status ;;
        logs)     cmd_logs "$@" ;;
        build)    cmd_build "$@" ;;
        validate) cmd_validate "$@" ;;
        clean)    cmd_clean ;;
        help|--help|-h) cmd_help ;;
        *)
            log_error "Unknown command: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
