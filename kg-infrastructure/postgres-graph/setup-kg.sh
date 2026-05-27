#!/bin/bash
# KG Setup Script for PostgreSQL (using docker exec)
# This script initializes the knowledge graph with required tables and indexes

set -e

echo "=== PostgreSQL Knowledge Graph Setup ==="

# Container name
CONTAINER_NAME=${CONTAINER_NAME:-postgres-graph}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DATABASE=${POSTGRES_DATABASE:-knowledge_graph}
GRAPH_NAME=${GRAPH_NAME:-knowledge_graph}

echo "Using container: $CONTAINER_NAME"
echo "Database: $POSTGRES_DATABASE"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "Error: Container $CONTAINER_NAME is not running."
    echo "Run: docker-compose up -d"
    exit 1
fi

echo "Container is running"

# Skip extension setup (disabled for ARM64 compatibility)
echo "Skipping extension setup (pgvector/Apache AGE disabled for ARM64)"

# Create additional KG-specific tables
echo "Creating KG-specific tables..."
docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE TABLE IF NOT EXISTS code_entities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    content TEXT,
    entity_type TEXT NOT NULL,
    file_path TEXT,
    language TEXT,
    metadata JSONB,
    _source TEXT DEFAULT 'dva_kg',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"

docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE TABLE IF NOT EXISTS document_entities (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    doc_type TEXT,
    url TEXT,
    metadata JSONB,
    _source TEXT DEFAULT 'dva_kg',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"

docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE TABLE IF NOT EXISTS entity_relationships (
    id SERIAL PRIMARY KEY,
    from_entity_id INTEGER REFERENCES code_entities(id) ON DELETE CASCADE,
    to_entity_id INTEGER REFERENCES code_entities(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    metadata JSONB,
    _source TEXT DEFAULT 'dva_kg',
    created_at TIMESTAMP DEFAULT NOW()
);
"

# Create indexes
echo "Creating indexes..."
docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE INDEX IF NOT EXISTS code_entities_name_idx ON code_entities(name);
CREATE INDEX IF NOT EXISTS code_entities_type_idx ON code_entities(entity_type);
CREATE INDEX IF NOT EXISTS code_entities_file_idx ON code_entities(file_path);
"

docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE INDEX IF NOT EXISTS document_entities_title_idx ON document_entities(title);
CREATE INDEX IF NOT EXISTS document_entities_type_idx ON document_entities(doc_type);
"

docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE INDEX IF NOT EXISTS entity_relationships_from_idx ON entity_relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS entity_relationships_to_idx ON entity_relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS entity_relationships_type_idx ON entity_relationships(relationship_type);
"

# Grant permissions
docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
"

echo "Creating trigger for updated_at..."
docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
\$\$ language 'plpgsql';
"

docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE TRIGGER update_code_entities_updated_at BEFORE UPDATE ON code_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"

docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DATABASE -c "
CREATE TRIGGER update_document_entities_updated_at BEFORE UPDATE ON document_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"

echo "=== Setup Complete ==="
echo "Knowledge graph tables and indexes created successfully"
echo ""
echo "Tables created:"
echo "  - code_entities (relational storage only)"
echo "  - document_entities (relational storage only)"
echo "  - entity_relationships"
echo ""
echo "Note: pgvector and Apache AGE not available on ARM64."
echo "For graph operations and embeddings, use Neo4j provider instead."
echo "PostgreSQL provider provides relational storage only."
