#!/usr/bin/env python3
"""Check all relationships between Release and Document nodes."""

from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.config import KGConfig

# Connect to Neo4j
config = KGConfig.load()
client = Neo4jClient(config=config)
client.connect()

# Check all relationship types between Release and Document nodes
query = """
MATCH (r:Release)-[rel]->(d)
RETURN type(rel) as rel_type, count(rel) as count
ORDER BY count DESC
"""

results = client.execute_cypher(query)

print("All relationships from Release nodes:")
for result in results:
    print(f"  {result['rel_type']}: {result['count']}")

# Check all relationship types to Document nodes
query = """
MATCH (r:Release)<-[rel]-(d)
RETURN type(rel) as rel_type, count(rel) as count
ORDER BY count DESC
"""

results = client.execute_cypher(query)

print("\nAll relationships to Release nodes:")
for result in results:
    print(f"  {result['rel_type']}: {result['count']}")

# Check sample documents for Release 28
query = """
MATCH (r:Release {name: 'Release 28: Facility Management (CWOV)'})
MATCH (r)-[rel]-(d)
RETURN type(rel) as rel_type, d.name as doc_name, d.id as doc_id
LIMIT 10
"""

results = client.execute_cypher(query)

print("\nSample relationships for Release 28:")
for result in results:
    print(f"  {result['rel_type']}: {result['doc_name']}")

client.close()
