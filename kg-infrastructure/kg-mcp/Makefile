.PHONY: help build start stop restart status logs health test clean

help:
	@echo "KEEL Knowledge Graph MCP Server - Management Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build       Build MCP server Docker image"
	@echo "  start       Start MCP server (assumes Neo4j/LightRAG running)"
	@echo "  start-full  Start full stack (MCP + Neo4j + LightRAG)"
	@echo "  stop        Stop MCP server"
	@echo "  stop-full   Stop full stack"
	@echo "  restart     Restart MCP server"
	@echo "  status      Show container status"
	@echo "  logs        Show MCP server logs (use 'make logs-follow' to follow)"
	@echo "  logs-follow Follow MCP server logs"
	@echo "  health      Check MCP server health"
	@echo "  test        Test MCP endpoints"
	@echo "  clean       Remove containers and images"
	@echo "  network     Create Docker network"

build:
	@echo "Building MCP server image..."
	docker-compose build

start:
	@echo "Starting MCP server..."
	@$(MAKE) network
	docker-compose up -d
	@echo "MCP server started on http://localhost:8125"
	@echo "Run 'make health' to check status"

start-full:
	@echo "Starting full stack (MCP + Neo4j + LightRAG)..."
	@$(MAKE) network
	docker-compose -f docker-compose.full.yml up -d
	@echo "Full stack started:"
	@echo "  - MCP Server: http://localhost:8125"
	@echo "  - Neo4j: http://localhost:7474 (bolt://localhost:7687)"
	@echo "  - LightRAG: http://localhost:8001"

stop:
	@echo "Stopping MCP server..."
	docker-compose down

stop-full:
	@echo "Stopping full stack..."
	docker-compose -f docker-compose.full.yml down

restart:
	@echo "Restarting MCP server..."
	@$(MAKE) stop
	@$(MAKE) start

status:
	@echo "Container status:"
	@docker-compose ps

logs:
	@echo "MCP server logs:"
	@docker-compose logs kg-mcp-server

logs-follow:
	@echo "Following MCP server logs (Ctrl+C to stop):"
	@docker-compose logs -f kg-mcp-server

health:
	@echo "Checking MCP server health..."
	@curl -s http://localhost:8125/health | python3 -m json.tool || echo "MCP server not responding"

test:
	@echo "Testing MCP endpoints..."
	@echo "\n1. Health check:"
	@curl -s http://localhost:8125/health | python3 -m json.tool
	@echo "\n2. Status:"
	@curl -s http://localhost:8125/status | python3 -m json.tool
	@echo "\n3. List tools:"
	@curl -s -X POST http://localhost:8125/mcp/tools/list | python3 -m json.tool

clean:
	@echo "Cleaning up..."
	@read -p "This will remove containers and images. Continue? [y/N] " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker rmi kg-mcp-infrastructure-kg-mcp-server 2>/dev/null || true; \
		echo "Cleanup complete"; \
	else \
		echo "Cleanup cancelled"; \
	fi

network:
	@docker network inspect keel-network >/dev/null 2>&1 || \
		(echo "Creating keel-network..." && docker network create keel-network)
