---
name: database-postgres
description: >-
  PostgreSQL schema patterns, indexing, query optimization, migrations.
  Use this skill when working with PostgreSQL databases.
---

# PostgreSQL Development

## Schema Patterns

```sql
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX idx_resources_metadata ON resources USING GIN(metadata);
```

## Query Patterns

```sql
-- Upsert
INSERT INTO resources (id, name, status)
VALUES ($1, $2, $3)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, updated_at = now();

-- JSONB query
SELECT * FROM resources WHERE metadata @> '{"type": "premium"}';

-- Window functions
SELECT name, status, ROW_NUMBER() OVER (PARTITION BY status ORDER BY created_at) as rn
FROM resources;

-- CTE
WITH active AS (
    SELECT * FROM resources WHERE status = 'active'
)
SELECT * FROM active WHERE created_at > now() - INTERVAL '7 days';
```

## Indexing Guidelines

- Use B-tree (default) for equality and range queries
- Use GIN for JSONB, arrays, full-text search
- Use partial indexes for filtered queries: `CREATE INDEX ... WHERE status = 'active'`
- Use `EXPLAIN ANALYZE` to verify index usage
- Avoid over-indexing — each index slows writes

## Migration Tools

- **Flyway**: `V1__create_resources.sql` naming convention
- **Liquibase**: XML/YAML/SQL changelogs
- **Alembic** (Python): `alembic upgrade head`
- **Django**: `python manage.py migrate`

## Guidelines

- Use `TIMESTAMPTZ` (not `TIMESTAMP`) for time-aware data
- Use `UUID` for primary keys in distributed systems
- Use `JSONB` over `JSON` (supports indexing and operators)
- Use connection pooling (PgBouncer, HikariCP)
- Use transactions for multi-statement operations
- Prefer `EXISTS` over `IN` for subqueries
