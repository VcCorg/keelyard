#!/bin/bash
# Validation script for PostgreSQL + pgvector + Apache AGE MCP integration

set -e

echo "=== Validating PostgreSQL MCP Integration ==="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found, using defaults"
fi

# Default values
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DATABASE=${POSTGRES_DATABASE:-knowledge_graph}
MCP_PORT=${MCP_PORT:-8125}

echo "PostgreSQL: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DATABASE}"
echo "MCP Server: http://localhost:${MCP_PORT}"
echo ""

# Check if PostgreSQL is running
echo "1. Checking PostgreSQL connection..."
if PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DATABASE -c '\q' 2>/dev/null; then
    echo "   ✓ PostgreSQL is running"
else
    echo "   ✗ PostgreSQL is not running"
    echo "   Run: docker-compose up -d"
    exit 1
fi

# Check if extensions are loaded
echo "2. Checking PostgreSQL extensions..."
EXTENSIONS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DATABASE -t -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'age');")
if echo "$EXTENSIONS" | grep -q "vector"; then
    echo "   ✓ pgvector extension is loaded"
else
    echo "   ✗ pgvector extension is not loaded"
    exit 1
fi
if echo "$EXTENSIONS" | grep -q "age"; then
    echo "   ✓ Apache AGE extension is loaded"
else
    echo "   ✗ Apache AGE extension is not loaded"
    exit 1
fi

# Check if KG tables exist
echo "3. Checking KG tables..."
TABLES=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DATABASE -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('code_entities', 'document_entities', 'entity_relationships');")
if echo "$TABLES" | grep -q "code_entities"; then
    echo "   ✓ code_entities table exists"
else
    echo "   ✗ code_entities table does not exist"
    echo "   Run: ./setup-kg.sh"
    exit 1
fi
if echo "$TABLES" | grep -q "document_entities"; then
    echo "   ✓ document_entities table exists"
else
    echo "   ✗ document_entities table does not exist"
    echo "   Run: ./setup-kg.sh"
    exit 1
fi

# Check if vector indexes exist
echo "4. Checking vector indexes..."
INDEXES=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DATABASE -t -c "SELECT indexname FROM pg_indexes WHERE indexname LIKE '%_embedding_idx';")
if echo "$INDEXES" | grep -q "code_entities_embedding_idx"; then
    echo "   ✓ code_entities vector index exists"
else
    echo "   ✗ code_entities vector index does not exist"
    exit 1
fi

# Check if Apache AGE graph exists
echo "5. Checking Apache AGE graph..."
GRAPH_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DATABASE -t -c "SELECT graphname FROM ag_graph WHERE graphname = 'knowledge_graph';")
if echo "$GRAPH_EXISTS" | grep -q "knowledge_graph"; then
    echo "   ✓ Apache AGE graph 'knowledge_graph' exists"
else
    echo "   ✗ Apache AGE graph 'knowledge_graph' does not exist"
    exit 1
fi

# Check MCP server (optional, if running)
echo "6. Checking MCP server (if running)..."
if curl -s http://localhost:${MCP_PORT}/health > /dev/null 2>&1; then
    echo "   ✓ MCP server is running"
    MCP_STATUS=$(curl -s http://localhost:${MCP_PORT}/health)
    echo "   Status: $(echo $MCP_STATUS | jq -r '.status' 2>/dev/null || echo 'unknown')"
    
    # Check if PostgreSQL provider is available
    if echo "$MCP_STATUS" | jq -e '.providers.postgres == true' > /dev/null 2>&1; then
        echo "   ✓ PostgreSQL provider is available in MCP"
    else
        echo "   ℹ PostgreSQL provider not configured in MCP (check POSTGRES_HOST env var)"
    fi
else
    echo "   ℹ MCP server is not running (optional for validation)"
    echo "   To start MCP server, set POSTGRES_HOST and run the KG MCP service"
fi

echo ""
echo "=== Validation Complete ==="
echo "✓ All checks passed"
echo ""
echo "Next steps:"
echo "1. Start PostgreSQL (if not running): docker-compose up -d"
echo "2. Run KG setup (if not done): ./setup-kg.sh"
echo "3. Configure MCP server with POSTGRES_HOST environment variable"
echo "4. Test MCP tools via HTTP or IDE integration"
