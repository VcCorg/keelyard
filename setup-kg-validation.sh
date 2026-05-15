#!/bin/bash

# KG Linker Validation Setup Script
# Sets up infrastructure and runs validation for cwow-facility domain

set -e

echo "================================================"
echo "KG Linker Validation Setup"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "agentic-cli/pyproject.toml" ]; then
    echo -e "${RED}✗ Please run this script from the myAgentPG root directory${NC}"
    exit 1
fi

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"

# Install CLI if not already installed
echo ""
echo "Installing agentic-cli..."
if ! command -v python -m agentic_cli.main &> /dev/null 2>&1; then
    echo -e "${YELLOW}Installing agentic-cli...${NC}"
    pip install -e agentic-cli/
else
    echo -e "${GREEN}✓ agentic-cli already installed${NC}"
fi

# Setup Neo4j
echo ""
echo "Setting up Neo4j..."
cd kg-infrastructure/neo4j

# Create .env if missing
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
# Neo4j Configuration
NEO4J_AUTH=neo4j/password
NEO4J_server_memory_heap_initial__size=512m
NEO4J_server_memory_heap_max__size=2G
NEO4J_server_memory_pagecache_size=1G
NEO4J_PLUGINS=["apoc"]
EOF
fi

# Create network if needed
docker network inspect dva-network >/dev/null 2>&1 || docker network create dva-network

# Start Neo4j
echo "Starting Neo4j..."
docker-compose up -d

# Wait for Neo4j
echo ""
echo "Waiting for Neo4j to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Neo4j is ready!${NC}"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Neo4j failed to start${NC}"
    echo "Check logs with: cd kg-infrastructure/neo4j && docker-compose logs neo4j"
    exit 1
fi

# Go back to root
cd ../..

# Configure CLI for Neo4j
echo ""
echo "Configuring agentic-cli for Neo4j..."
python -m agentic_cli.main kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password
echo -e "${GREEN}✓ CLI configured for Neo4j${NC}"

# Check if we have any data
echo ""
echo "Checking for existing KG data..."
python -m agentic_cli.main kg stats 2>/dev/null || echo "No data yet (expected for first run)"

# Check if Vertex AI is configured
echo ""
echo "Checking Vertex AI configuration..."
if python -c "from agentic_cli.kg.config import KGConfig; print('✓' if KGConfig.load().is_vertex_ai_configured() else '✗')" 2>/dev/null | grep -q "✓"; then
    echo -e "${GREEN}✓ Vertex AI is configured${NC}"
    VERTEX_CONFIGURED=true
else
    echo -e "${YELLOW}⚠ Vertex AI is not configured${NC}"
    echo "  To configure: python -m agentic_cli.main init vertex-ai"
    VERTEX_CONFIGURED=false
fi

# Validation steps
echo ""
echo "================================================"
echo "Validation Steps"
echo "================================================"
echo ""

# Step 1: Check if we have cwow-facility domain
echo -e "${BLUE}Step 1: Checking cwow-facility domain setup${NC}"
if python -c "import sys; sys.path.append('mcp-servers/agentic/src'); from agentic_mcp.db import TrackerDB; db = TrackerDB(); print('✓' if db.domain_get('cwow-facility') else '✗')" 2>/dev/null | grep -q "✓"; then
    echo -e "${GREEN}✓ cwow-facility domain exists${NC}"
    DOMAIN_EXISTS=true
else
    echo -e "${YELLOW}⚠ cwow-facility domain not found${NC}"
    echo "  To create: python -m agentic_cli.main domain create --domain Facility --product CWOW"
    DOMAIN_EXISTS=false
fi

# Step 2: Check if we have onboarded repos
echo ""
echo -e "${BLUE}Step 2: Checking onboarded repos${NC}"
REPOS_COUNT=$(python -c "
import sys; sys.path.append('mcp-servers/agentic/src'); 
from agentic_mcp.db import TrackerDB; 
db = TrackerDB(); 
repos = db.repo_list(); 
print(len(repos))
" 2>/dev/null || echo "0")

if [ "$REPOS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $REPOS_COUNT onboarded repos${NC}"
    REPOS_EXIST=true
else
    echo -e "${YELLOW}⚠ No repos onboarded yet${NC}"
    echo "  To onboard: python -m agentic_cli.main code onboard --path <repo-path> --kg --extract-entities"
    REPOS_EXIST=false
fi

# Step 3: Check if we have business docs
echo ""
echo -e "${BLUE}Step 3: Checking business documents${NC}"
DOCS_COUNT=$(python -m agentic_cli.main domain list-docs cwow-facility 2>/dev/null | grep -c "doc_" || echo "0")
if [ "$DOCS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $DOCS_COUNT business docs${NC}"
    DOCS_EXIST=true
else
    echo -e "${YELLOW}⚠ No business docs found${NC}"
    echo "  To add docs: python -m agentic_cli.main domain add-doc cwow-facility --source confluence"
    DOCS_EXIST=false
fi

# Run validation if everything is ready
echo ""
echo "================================================"
echo "Ready to Validate KG Linker"
echo "================================================"
echo ""

if [ "$VERTEX_CONFIGURED" = true ] && [ "$DOMAIN_EXISTS" = true ] && [ "$REPOS_EXIST" = true ] && [ "$DOCS_EXIST" = true ]; then
    echo -e "${GREEN}✓ All prerequisites met! Running validation...${NC}"
    echo ""
    
    # Run dry-run
    echo -e "${BLUE}Running KG linker dry-run for cwow-facility...${NC}"
    python -m agentic_cli.main kg link --domain cwow-facility --dry-run --threshold 0.75
    
    echo ""
    echo -e "${GREEN}✓ Dry-run completed successfully!${NC}"
    echo ""
    echo "To run the actual linking:"
    echo "  python -m agentic_cli.main kg link --domain cwow-facility"
    echo ""
    echo "To test MCP tools (after linking):"
    echo "  1. Start MCP server: cd mcp-servers/agentic && docker-compose up -d"
    echo "  2. Set env vars: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
    echo "  3. Call: kg_get_domain_graph_summary('cwow-facility')"
    
else
    echo -e "${YELLOW}⚠ Setup incomplete. Please complete the following:${NC}"
    echo ""
    
    [ "$VERTEX_CONFIGURED" = false ] && echo "  1. Configure Vertex AI: python -m agentic_cli.main init vertex-ai"
    [ "$DOMAIN_EXISTS" = false ] && echo "  2. Create domain: python -m agentic_cli.main domain create --domain Facility --product CWOW"
    [ "$REPOS_EXIST" = false ] && echo "  3. Onboard repos: python -m agentic_cli.main code onboard --path <repo-path> --kg --extract-entities"
    [ "$DOCS_EXIST" = false ] && echo "  4. Add business docs: python -m agentic_cli.main domain add-doc cwow-facility --source confluence"
    
    echo ""
    echo "After completing these steps, run this script again to validate."
fi

echo ""
echo "================================================"
echo "Infrastructure Status"
echo "================================================"
echo ""
echo "Neo4j:"
echo "  - Browser: http://localhost:7474"
echo "  - Bolt: bolt://localhost:7687"
echo "  - Status: $(docker ps --filter "name=dva-neo4j" --format "table {{.Status}}" | tail -n 1)"
echo ""
echo "Useful commands:"
echo "  - View Neo4j logs: cd kg-infrastructure/neo4j && docker-compose logs -f neo4j"
echo "  - Stop Neo4j: cd kg-infrastructure/neo4j && docker-compose down"
echo "  - Restart Neo4j: cd kg-infrastructure/neo4j && docker-compose restart"
echo ""
