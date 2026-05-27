#!/usr/bin/env python3
"""Check documents linked to Release 28 via SPECIFIES_RELEASE or BELONGS_TO."""

from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.config import KGConfig

# Connect to Neo4j
config = KGConfig.load()
client = Neo4jClient(config=config)
client.connect()

# Check documents with SPECIFIES_RELEASE to Release 28
query = """
MATCH (d)-[rel:SPECIFIES_RELEASE]->(r:Release {name: 'Release 28: Facility Management (CWOV)'})
RETURN d.name as doc_name, d.id as doc_id, type(rel) as rel_type
LIMIT 20
"""

results = client.execute_cypher(query)

print("Documents with SPECIFIES_RELEASE to Release 28:")
if results:
    for result in results:
        print(f"  {result['doc_name']}")
else:
    print("  None")

# Check documents with BELONGS_TO to Release 28
query = """
MATCH (d)-[rel:BELONGS_TO]->(r:Release {name: 'Release 28: Facility Management (CWOV)'})
RETURN d.name as doc_name, d.id as doc_id, type(rel) as rel_type
LIMIT 20
"""

results = client.execute_cypher(query)

print("\nDocuments with BELONGS_TO to Release 28:")
if results:
    for result in results:
        print(f"  {result['doc_name']}")
else:
    print("  None")

# Check all documents that mention "Release 28" in their content
query = """
MATCH (d)
WHERE d.content CONTAINS 'Release 28'
RETURN d.name as doc_name, d.id as doc_id
LIMIT 20
"""

results = client.execute_cypher(query)

print("\nDocuments that mention 'Release 28' in content:")
if results:
    for result in results:
        print(f"  {result['doc_name']}")
else:
    print("  None")

client.close()
