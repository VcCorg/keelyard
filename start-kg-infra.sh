#!/bin/bash

# One-click script to spin up Knowledge Graph infrastructure
# Supports: PostgreSQL + pgvector + Apache AGE, Neo4j, LightRAG, Weaviate

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/kg-infrastructure"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Available providers (mapping to directory names)
AVAILABLE_PROVIDERS=("postgres-graph" "neo4j" "lightrag" "weaviate")

# Function to get display name for provider
get_display_name() {
    local provider=$1
    case $provider in
        postgres-graph) echo "PostgreSQL" ;;
        neo4j) echo "Neo4j" ;;
        lightrag) echo "LightRAG" ;;
        weaviate) echo "Weaviate" ;;
        *) echo "$provider" ;;
    esac
}

# Function to print usage
usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [provider]    Start infrastructure for specific provider (or all if not specified)"
    echo "  stop [provider]     Stop infrastructure for specific provider (or all if not specified)"
    echo "  status              Show status of all infrastructure"
    echo "  restart [provider]  Restart infrastructure for specific provider (or all if not specified)"
    echo ""
    echo "Providers:"
    echo "  postgres-graph       PostgreSQL + pgvector + Apache AGE"
    echo "  neo4j               Neo4j graph database"
    echo "  lightrag            LightRAG API service"
    echo "  weaviate            Weaviate vector database"
    echo ""
    echo "Examples:"
    echo "  $0 start postgres-graph     # Start only PostgreSQL"
    echo "  $0 start                    # Start all providers"
    echo "  $0 stop neo4j               # Stop only Neo4j"
    echo "  $0 status                   # Show status of all"
    echo ""
    echo "Quick Start for PostgreSQL:"
    echo "  $0 start postgres-graph"
    echo "  cd kg-infrastructure/postgres-graph"
    echo "  ./setup-kg.sh"
}

# Function to check if provider is valid
validate_provider() {
    local provider=$1
    for p in "${AVAILABLE_PROVIDERS[@]}"; do
        if [ "$p" == "$provider" ]; then
            return 0
        fi
    done
    echo -e "${RED}Error: Invalid provider '$provider'${NC}"
    echo "Valid providers: ${AVAILABLE_PROVIDERS[*]}"
    exit 1
}

# Function to start a provider
start_provider() {
    local provider=$1
    local provider_dir="$INFRA_DIR/$provider"
    
    echo -e "${BLUE}Starting $provider...${NC}"
    
    if [ ! -d "$provider_dir" ]; then
        echo -e "${RED}Error: Provider directory not found: $provider_dir${NC}"
        return 1
    fi
    
    if [ ! -f "$provider_dir/docker-compose.yml" ]; then
        echo -e "${RED}Error: docker-compose.yml not found in $provider_dir${NC}"
        return 1
    fi
    
    cd "$provider_dir"
    
    # Check if .env.example exists and .env doesn't
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
    fi
    
    docker-compose up -d
    
    echo -e "${GREEN}✓ $display_name started successfully${NC}"
    cd "$SCRIPT_DIR"
}

# Function to stop a provider
stop_provider() {
    local provider=$1
    local provider_dir="$INFRA_DIR/$provider"
    local display_name=$(get_display_name "$provider")
    
    echo -e "${BLUE}Stopping $display_name...${NC}"
    
    if [ ! -d "$provider_dir" ]; then
        echo -e "${RED}Error: Provider directory not found: $provider_dir${NC}"
        return 1
    fi
    
    if [ ! -f "$provider_dir/docker-compose.yml" ]; then
        echo -e "${RED}Error: docker-compose.yml not found in $provider_dir${NC}"
        return 1
    fi
    
    cd "$provider_dir"
    docker-compose down
    echo -e "${GREEN}✓ $display_name stopped${NC}"
    cd "$SCRIPT_DIR"
}

# Function to restart a provider
restart_provider() {
    local provider=$1
    stop_provider "$provider"
    start_provider "$provider"
}

# Function to check status of a provider
check_status() {
    local provider=$1
    local provider_dir="$INFRA_DIR/$provider"
    local display_name=$(get_display_name "$provider")
    
    if [ ! -d "$provider_dir" ]; then
        echo -e "${RED}✗ $display_name: Directory not found${NC}"
        return 1
    fi
    
    cd "$provider_dir"
    
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ $display_name: Running${NC}"
    else
        echo -e "${YELLOW}○ $display_name: Stopped${NC}"
    fi
    
    cd "$SCRIPT_DIR"
}

# Function to show status of all providers
show_status() {
    echo -e "${BLUE}Infrastructure Status:${NC}"
    echo ""
    
    for provider in "${AVAILABLE_PROVIDERS[@]}"; do
        check_status "$provider"
    done
    
    echo ""
    echo "For detailed status, run:"
    echo "  docker ps"
    echo "  docker-compose ps (in provider directory)"
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

COMMAND=$1
shift

case $COMMAND in
    start)
        if [ $# -eq 0 ]; then
            echo -e "${BLUE}Starting all providers...${NC}"
            for provider in "${AVAILABLE_PROVIDERS[@]}"; do
                start_provider "$provider"
            done
            echo ""
            echo -e "${GREEN}All providers started${NC}"
            echo ""
            echo "Next steps:"
            echo "  1. PostgreSQL: cd kg-infrastructure/postgres-graph && ./setup-kg.sh"
            echo "  2. Neo4j: cd kg-infrastructure/neo4j && ./setup.sh"
            echo "  3. LightRAG: cd kg-infrastructure/lightrag && ./setup.sh"
            echo "  4. Weaviate: cd kg-infrastructure/weaviate && ./setup.sh"
        else
            validate_provider "$1"
            start_provider "$1"
            echo ""
            echo "Next steps:"
            case $1 in
                postgres-graph)
                    echo "  cd kg-infrastructure/postgres-graph && ./setup-kg.sh"
                    ;;
                neo4j)
                    echo "  cd kg-infrastructure/neo4j && ./setup.sh"
                    ;;
                lightrag)
                    echo "  cd kg-infrastructure/lightrag && ./setup.sh"
                    ;;
                weaviate)
                    echo "  cd kg-infrastructure/weaviate && ./setup.sh"
                    ;;
                *)
                    echo "  cd kg-infrastructure/$1 && ./setup.sh"
                    ;;
            esac
        fi
        ;;
    stop)
        if [ $# -eq 0 ]; then
            echo -e "${BLUE}Stopping all providers...${NC}"
            for provider in "${AVAILABLE_PROVIDERS[@]}"; do
                stop_provider "$provider"
            done
            echo ""
            echo -e "${GREEN}All providers stopped${NC}"
        else
            validate_provider "$1"
            stop_provider "$1"
        fi
        ;;
    restart)
        if [ $# -eq 0 ]; then
            echo -e "${BLUE}Restarting all providers...${NC}"
            for provider in "${AVAILABLE_PROVIDERS[@]}"; do
                restart_provider "$provider"
            done
        else
            validate_provider "$1"
            restart_provider "$1"
        fi
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${NC}"
        usage
        exit 1
        ;;
esac
