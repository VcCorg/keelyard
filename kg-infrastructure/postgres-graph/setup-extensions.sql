-- Load pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Load Apache AGE extension
CREATE EXTENSION IF NOT EXISTS age;

-- Set search path to include ag_catalog
SET search_path = ag_catalog, "$user", public;

-- Create a test graph
SELECT create_graph('knowledge_graph');

-- Grant permissions
GRANT ALL ON SCHEMA ag_catalog TO PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA ag_catalog TO PUBLIC;
