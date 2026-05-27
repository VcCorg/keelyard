#!/bin/bash
set -e

# Create database (plain PostgreSQL - extensions don't work on ARM64)
echo "Database initialized (plain PostgreSQL - use Neo4j for graph operations)"
