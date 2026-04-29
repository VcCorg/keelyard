.PHONY: help start stop restart status logs clean health test validate

help:
	@echo "Neo4j Infrastructure Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make start     - Start Neo4j container"
	@echo "  make stop      - Stop Neo4j container"
	@echo "  make restart   - Restart Neo4j container"
	@echo "  make status    - Check container status"
	@echo "  make logs      - View container logs"
	@echo "  make health    - Check Neo4j health"
	@echo "  make test      - Test Neo4j connection and queries"
	@echo "  make validate  - Comprehensive validation (container + connectivity)"
	@echo "  make clean     - Stop and remove containers and volumes"
	@echo "  make backup    - Backup Neo4j data"
	@echo "  make restore   - Restore Neo4j data from backup"

start:
	@echo "Starting Neo4j..."
	docker-compose up -d
	@echo "Waiting for Neo4j to be ready..."
	@sleep 10
	@make health

stop:
	@echo "Stopping Neo4j..."
	docker-compose down

restart:
	@echo "Restarting Neo4j..."
	docker-compose restart
	@sleep 5
	@make health

status:
	@echo "Container Status:"
	@docker-compose ps

logs:
	docker-compose logs -f neo4j

health:
	@echo "Checking Neo4j health..."
	@curl -s http://localhost:7474 > /dev/null && echo "✓ Neo4j HTTP (port 7474) is accessible" || echo "✗ Neo4j HTTP is not accessible"
	@docker exec dva-neo4j cypher-shell -u neo4j -p password "RETURN 'Connection successful' as status" 2>/dev/null && echo "✓ Neo4j Bolt (port 7687) is accessible" || echo "✗ Neo4j Bolt is not accessible"

test:
	@echo "Testing Neo4j queries..."
	@echo "\n1. Node count:"
	@docker exec dva-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as node_count" 2>/dev/null || echo "FAILED"
	@echo "\n2. Relationship count:"
	@docker exec dva-neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN count(r) as relationship_count" 2>/dev/null || echo "FAILED"
	@echo "\n3. Database info:"
	@docker exec dva-neo4j cypher-shell -u neo4j -p password "CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] as version, edition" 2>/dev/null || echo "FAILED"
	@echo "\n✓ All tests completed"

validate:
	@echo "=========================================="
	@echo "Neo4j Infrastructure Validation"
	@echo "=========================================="
	@echo ""
	@echo "1. Docker Status"
	@echo "-------------------"
	@docker --version 2>/dev/null && echo "✓ Docker installed" || echo "✗ Docker not found"
	@docker ps >/dev/null 2>&1 && echo "✓ Docker daemon running" || echo "✗ Docker daemon not running"
	@echo ""
	@echo "2. Container Status"
	@echo "-------------------"
	@if docker ps --filter "name=dva-neo4j" --format "{{.Names}}" | grep -q "dva-neo4j"; then \
		echo "✓ Neo4j container running"; \
		docker ps --filter "name=dva-neo4j" --format "  Status: {{.Status}}"; \
	else \
		echo "✗ Neo4j container not running"; \
		exit 1; \
	fi
	@echo ""
	@echo "3. HTTP Endpoint (Browser)"
	@echo "-------------------"
	@if curl -s -o /dev/null -w "%{http_code}" http://localhost:7474 | grep -q "200"; then \
		echo "✓ Neo4j Browser accessible at http://localhost:7474"; \
	else \
		echo "✗ Neo4j Browser not accessible"; \
		exit 1; \
	fi
	@echo ""
	@echo "4. Bolt Connection (Database)"
	@echo "-------------------"
	@if docker exec dva-neo4j cypher-shell -u neo4j -p password "RETURN 1 as test" >/dev/null 2>&1; then \
		echo "✓ Bolt connection successful (bolt://localhost:7687)"; \
	else \
		echo "✗ Bolt connection failed"; \
		echo "  Check credentials or wait for Neo4j to fully start"; \
		exit 1; \
	fi
	@echo ""
	@echo "5. Database Operations"
	@echo "-------------------"
	@node_count=$$(docker exec dva-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as count" --format plain 2>/dev/null | tail -n 1 | tr -d '"'); \
	rel_count=$$(docker exec dva-neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN count(r) as count" --format plain 2>/dev/null | tail -n 1 | tr -d '"'); \
	if [ -n "$$node_count" ]; then \
		echo "✓ Query execution working"; \
		echo "  Nodes: $$node_count"; \
		echo "  Relationships: $$rel_count"; \
	else \
		echo "✗ Query execution failed"; \
		exit 1; \
	fi
	@echo ""
	@echo "6. Database Info"
	@echo "-------------------"
	@docker exec dva-neo4j cypher-shell -u neo4j -p password "CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] as version, edition" --format plain 2>/dev/null | grep -v "^name" | head -n 1 | while read line; do \
		echo "✓ Neo4j: $$line"; \
	done || echo "✗ Could not retrieve database info"
	@echo ""
	@echo "7. APOC Plugin"
	@echo "-------------------"
	@if docker exec dva-neo4j cypher-shell -u neo4j -p password "RETURN apoc.version() as version" --format plain 2>/dev/null | grep -q "version"; then \
		apoc_ver=$$(docker exec dva-neo4j cypher-shell -u neo4j -p password "RETURN apoc.version() as version" --format plain 2>/dev/null | tail -n 1 | tr -d '"'); \
		echo "✓ APOC plugin installed ($$apoc_ver)"; \
	else \
		echo "⚠ APOC plugin not available (optional)"; \
	fi
	@echo ""
	@echo "=========================================="
	@echo "✓ All validation checks passed!"
	@echo "=========================================="
	@echo ""
	@echo "Neo4j is ready for use:"
	@echo "  Browser: http://localhost:7474"
	@echo "  Bolt:    bolt://localhost:7687"
	@echo "  User:    neo4j"
	@echo "  Pass:    password"

clean:
	@echo "Stopping and removing containers and volumes..."
	@read -p "This will delete all Neo4j data. Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "✓ Cleanup complete"; \
	else \
		echo "Cancelled"; \
	fi

backup:
	@echo "Creating backup..."
	@mkdir -p backups
	@docker exec dva-neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/import
	@docker cp dva-neo4j:/var/lib/neo4j/import/neo4j.dump ./backups/neo4j-backup-$$(date +%Y%m%d-%H%M%S).dump
	@echo "✓ Backup created in ./backups/"

restore:
	@echo "Available backups:"
	@ls -1 backups/ 2>/dev/null || echo "No backups found"
	@read -p "Enter backup filename: " backup; \
	if [ -f "backups/$$backup" ]; then \
		docker cp backups/$$backup dva-neo4j:/var/lib/neo4j/import/restore.dump; \
		docker exec dva-neo4j neo4j-admin database load neo4j --from-path=/var/lib/neo4j/import --overwrite-destination=true; \
		make restart; \
		echo "✓ Restore complete"; \
	else \
		echo "✗ Backup file not found"; \
	fi
