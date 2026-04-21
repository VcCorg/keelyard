.PHONY: help start stop restart status logs health test validate clean backup restore install

# Detect docker compose command
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo 'docker compose' || echo 'docker-compose')

help:
	@echo "LightRAG Infrastructure - Available commands:"
	@echo "  make start       - Start LightRAG container"
	@echo "  make stop        - Stop LightRAG container"
	@echo "  make restart     - Restart LightRAG container"
	@echo "  make status      - Show container status"
	@echo "  make logs        - Show container logs"
	@echo "  make health      - Check LightRAG health"
	@echo "  make test        - Test LightRAG API endpoints"
	@echo "  make validate    - Comprehensive validation (container + API)"
	@echo "  make clean       - Stop and remove containers and volumes"
	@echo "  make backup      - Backup LightRAG data"
	@echo "  make restore     - Restore LightRAG data from backup"
	@echo "  make install     - Install Python client dependencies"

start:
	@echo "Starting LightRAG..."
	$(DOCKER_COMPOSE) up -d
	@echo "Waiting for LightRAG to be ready..."
	@sleep 5
	@make health

stop:
	@echo "Stopping LightRAG..."
	$(DOCKER_COMPOSE) down

restart:
	@echo "Restarting LightRAG..."
	$(DOCKER_COMPOSE) restart
	@sleep 5
	@make health

status:
	@echo "Container status:"
	@$(DOCKER_COMPOSE) ps

logs:
	$(DOCKER_COMPOSE) logs -f lightrag

health:
	@echo "Checking LightRAG health..."
	@curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8001/health || echo "LightRAG is not responding"

test:
	@echo "Testing LightRAG API endpoints..."
	@echo "\n1. Health check:"
	@curl -s http://localhost:8001/health && echo "" || echo "FAILED"
	@echo "\n2. Stats endpoint:"
	@curl -s http://localhost:8001/stats && echo "" || echo "FAILED"
	@echo "\n3. Insert test:"
	@curl -s -X POST http://localhost:8001/insert \
		-H "Content-Type: application/json" \
		-d '{"text":"Test document for validation"}' && echo "" || echo "FAILED"
	@echo "\n✓ All tests completed"

validate:
	@echo "=========================================="
	@echo "LightRAG Infrastructure Validation"
	@echo "=========================================="
	@echo ""
	@echo "1. Docker Status"
	@echo "-------------------"
	@docker --version 2>/dev/null && echo "✓ Docker installed" || echo "✗ Docker not found"
	@docker ps >/dev/null 2>&1 && echo "✓ Docker daemon running" || echo "✗ Docker daemon not running"
	@echo ""
	@echo "2. Container Status"
	@echo "-------------------"
	@if docker ps --filter "name=dva-lightrag" --format "{{.Names}}" | grep -q "dva-lightrag"; then \
		echo "✓ LightRAG container running"; \
		docker ps --filter "name=dva-lightrag" --format "  Status: {{.Status}}"; \
	else \
		echo "✗ LightRAG container not running"; \
		exit 1; \
	fi
	@echo ""
	@echo "3. Health Check"
	@echo "-------------------"
	@response=$$(curl -s -w "\n%{http_code}" http://localhost:8001/health); \
	status=$$(echo "$$response" | tail -n1); \
	body=$$(echo "$$response" | head -n-1); \
	if [ "$$status" = "200" ]; then \
		echo "✓ Health endpoint responding (HTTP $$status)"; \
		echo "  $$body"; \
	else \
		echo "✗ Health endpoint failed (HTTP $$status)"; \
		exit 1; \
	fi
	@echo ""
	@echo "4. Stats Endpoint"
	@echo "-------------------"
	@response=$$(curl -s -w "\n%{http_code}" http://localhost:8001/stats); \
	status=$$(echo "$$response" | tail -n1); \
	body=$$(echo "$$response" | head -n-1); \
	if [ "$$status" = "200" ]; then \
		echo "✓ Stats endpoint responding (HTTP $$status)"; \
		echo "  $$body"; \
	else \
		echo "✗ Stats endpoint failed (HTTP $$status)"; \
		exit 1; \
	fi
	@echo ""
	@echo "5. Insert Endpoint Test"
	@echo "-------------------"
	@response=$$(curl -s -w "\n%{http_code}" -X POST http://localhost:8001/insert \
		-H "Content-Type: application/json" \
		-d '{"text":"Validation test document"}'); \
	status=$$(echo "$$response" | tail -n1); \
	body=$$(echo "$$response" | head -n-1); \
	if [ "$$status" = "200" ]; then \
		echo "✓ Insert endpoint working (HTTP $$status)"; \
		echo "  $$body"; \
	else \
		echo "✗ Insert endpoint failed (HTTP $$status)"; \
		echo "  Response: $$body"; \
		echo ""; \
		echo "Checking container logs for errors..."; \
		docker logs --tail 20 dva-lightrag 2>&1 | grep -i error || echo "No obvious errors in logs"; \
		exit 1; \
	fi
	@echo ""
	@echo "=========================================="
	@echo "✓ All validation checks passed!"
	@echo "=========================================="

clean:
	@echo "WARNING: This will remove all containers and volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "Cleaned up successfully"; \
	else \
		echo "Cancelled"; \
	fi

backup:
	@echo "Creating backup..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker cp dva-lightrag:/data/lightrag backups/lightrag_$$timestamp || echo "Failed to create backup"
	@echo "Backup created in backups/"

restore:
	@echo "Available backups:"
	@ls -1 backups/ 2>/dev/null || echo "No backups found"
	@read -p "Enter backup name to restore: " backup; \
	if [ -d "backups/$$backup" ]; then \
		docker cp backups/$$backup dva-lightrag:/data/lightrag; \
		make restart; \
		echo "Restored from $$backup"; \
	else \
		echo "Backup not found"; \
	fi

install:
	@echo "Installing Python client dependencies..."
	pip install httpx
	@echo "Dependencies installed"

# Production mode with Milvus
start-prod:
	@echo "Starting LightRAG with Milvus (production mode)..."
	$(DOCKER_COMPOSE) --profile production up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@make health

# Development helpers
shell:
	docker exec -it dva-lightrag bash

python-shell:
	@python3 -i -c "import sys; sys.path.insert(0, 'lib'); from lightrag_client import LightRAGClient; client = LightRAGClient(); print('LightRAG client ready. Use: client.insert(), client.query(), etc.')"
