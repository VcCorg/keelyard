#!/bin/bash

set -e

echo "================================================"
echo "Neo4j Infrastructure Setup"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"

echo ""
echo "Setting up Neo4j..."
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}Note: Edit .env to customize settings${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Start Neo4j
echo ""
echo "Starting Neo4j container..."
docker-compose up -d

# Wait for Neo4j to be ready
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
    echo "Check logs with: docker-compose logs neo4j"
    exit 1
fi

# Test connection
echo ""
echo "Testing Neo4j connection..."
if docker exec dva-neo4j cypher-shell -u neo4j -p password "RETURN 'Connection successful' as status" &> /dev/null; then
    echo -e "${GREEN}✓ Neo4j connection successful${NC}"
else
    echo -e "${RED}✗ Neo4j connection failed${NC}"
    exit 1
fi

echo ""
echo "================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Neo4j is now running:"
echo "  - Browser UI: http://localhost:7474"
echo "  - Bolt URI: bolt://localhost:7687"
echo "  - Username: neo4j"
echo "  - Password: password"
echo ""
echo "Useful commands:"
echo "  make status  - Check container status"
echo "  make logs    - View logs"
echo "  make stop    - Stop Neo4j"
echo "  make restart - Restart Neo4j"
echo "  make health  - Check health"
echo ""
echo "Next steps:"
echo "  1. Configure Agentic CLI: agent kg init --provider neo4j"
echo "  2. Start ingesting data: agent kg ingest <source>"
echo ""
