#!/bin/bash

# LightRAG Infrastructure Setup Script
# This script sets up the LightRAG infrastructure with Docker

set -e

echo "================================================"
echo "LightRAG Infrastructure Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check if docker compose is available (try both old and new syntax)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${GREEN}✓ docker compose is available${NC}"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo -e "${GREEN}✓ docker-compose is available${NC}"
else
    echo -e "${RED}Error: docker compose is not available${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

# Check if curl is installed (needed for health checks)
if ! command -v curl &> /dev/null; then
    echo -e "${YELLOW}⚠ curl is not installed (optional, but recommended for health checks)${NC}"
    CURL_AVAILABLE=false
else
    echo -e "${GREEN}✓ curl is available${NC}"
    CURL_AVAILABLE=true
fi

echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env file with your API keys${NC}"
    echo ""
fi

# Check for OpenAI API key
if ! grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env; then
    echo -e "${GREEN}✓ OpenAI API key is configured${NC}"
else
    echo -e "${YELLOW}⚠ OpenAI API key not configured in .env${NC}"
    echo "  Please add your OpenAI API key to .env file"
    echo ""
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p lib scripts config backups
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Start LightRAG
echo "Starting LightRAG container..."
$DOCKER_COMPOSE up -d

echo ""
echo "Waiting for LightRAG to be ready..."
sleep 10

# Check health
if [ "$CURL_AVAILABLE" = true ]; then
    echo "Checking LightRAG health..."
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ LightRAG is healthy and ready!${NC}"
            break
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${YELLOW}⚠ Health check timeout${NC}"
            echo "Container may still be starting. Check logs with: $DOCKER_COMPOSE logs lightrag"
            break
        fi
        
        echo "Waiting... (attempt $attempt/$max_attempts)"
        sleep 2
    done
else
    echo -e "${YELLOW}⚠ Skipping health check (curl not available)${NC}"
    echo "Waiting 30 seconds for container to start..."
    sleep 30
    echo "Check status with: $DOCKER_COMPOSE ps"
fi

echo ""
echo "================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "================================================"
echo ""
echo "LightRAG is running at: http://localhost:8001"
echo ""
echo "Quick commands:"
echo "  make status  - Check container status"
echo "  make logs    - View logs"
echo "  make health  - Check health"
echo "  make test    - Test connection"
echo "  make stop    - Stop container"
echo ""
echo "API Endpoints:"
echo "  POST http://localhost:8001/insert   - Insert documents"
echo "  POST http://localhost:8001/query    - Query knowledge graph"
echo "  POST http://localhost:8001/search   - Semantic search"
echo "  GET  http://localhost:8001/stats    - Get statistics"
echo "  GET  http://localhost:8001/health   - Health check"
echo ""
echo "For more information, see README.md"
echo ""
