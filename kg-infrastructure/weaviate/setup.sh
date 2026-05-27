#!/bin/bash
# Setup script for Weaviate KG infrastructure

set -e

echo "Setting up Weaviate KG infrastructure..."
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Start Weaviate
echo "Starting Weaviate container..."
docker-compose up -d

# Wait for Weaviate to be ready
echo "Waiting for Weaviate to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
        echo "✓ Weaviate is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Check if Weaviate is ready
if ! curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
    echo "Error: Weaviate failed to start. Check logs with: docker-compose logs weaviate"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install weaviate-client python-dotenv

# Setup schema
echo "Setting up Weaviate schema..."
cd scripts
python setup_schema.py

# Ingest test data
echo "Ingesting test data..."
python ingest_test_data.py

# Run test queries
echo "Running test queries..."
python test_queries.py

cd ..

echo
echo "✓ Weaviate KG infrastructure setup complete!"
echo
echo "Next steps:"
echo "  1. View Weaviate console: http://localhost:8080"
echo "  2. Run test queries: cd scripts && python test_queries.py"
echo "  3. Stop Weaviate: docker-compose down"
