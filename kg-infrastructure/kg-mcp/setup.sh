#!/bin/bash

# Agentic Knowledge Graph MCP Server Setup Script
# This script sets up and starts the MCP server

set -e

echo "=========================================="
echo "Agentic Knowledge Graph MCP Server Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ docker-compose is not installed${NC}"
    echo "Please install docker-compose"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose is installed${NC}"

echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env file with your configuration${NC}"
    echo ""
fi

# Create Docker network if it doesn't exist
echo "Creating Docker network..."
docker network inspect agentic-network >/dev/null 2>&1 || docker network create agentic-network
echo -e "${GREEN}✓ Docker network ready${NC}"
echo ""

# Ask user which mode to start
echo "Select startup mode:"
echo "  1) MCP server only (assumes Neo4j/LightRAG already running)"
echo "  2) Full stack (MCP + Neo4j + LightRAG)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo ""
        echo "Starting MCP server only..."
        docker-compose build
        docker-compose up -d
        ;;
    2)
        echo ""
        echo "Starting full stack..."
        docker-compose -f docker-compose.full.yml build
        docker-compose -f docker-compose.full.yml up -d
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Check health
echo ""
echo "Checking MCP server health..."
for i in {1..30}; do
    if curl -s http://localhost:8125/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MCP server is healthy${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ MCP server failed to start${NC}"
        echo "Check logs with: docker-compose logs kg-mcp-server"
        exit 1
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "MCP Server: http://localhost:8125"
if [ "$choice" = "2" ]; then
    echo "Neo4j Browser: http://localhost:7474"
    echo "Neo4j Bolt: bolt://localhost:7687"
    echo "LightRAG API: http://localhost:8001"
fi
echo ""
echo "Useful commands:"
echo "  make status      - Check container status"
echo "  make logs        - View logs"
echo "  make health      - Check health"
echo "  make test        - Test MCP endpoints"
echo "  make stop        - Stop services"
echo ""
echo "IDE Configuration:"
echo "  Add to your IDE's MCP config:"
echo "  {"
echo "    \"kg-mcp\": {"
echo "      \"url\": \"http://localhost:8125/mcp\","
echo "      \"transport\": \"http\""
echo "    }"
echo "  }"
echo ""
