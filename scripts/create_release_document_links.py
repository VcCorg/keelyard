#!/usr/bin/env python3
"""Create Release-Document links from existing IS_BASED_ON relationships."""

from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.config import KGConfig

# Connect to Neo4j
config = KGConfig.load()
client = Neo4jClient(config=config)
client.connect()

print("Finding existing IS_BASED_ON relationships...")

# Find all IS_BASED_ON relationships between Release and Document nodes
query = """
MATCH (r:Release)-[rel:IS_BASED_ON]->(d)
RETURN r.name as release_name, r.id as release_id, d.id as doc_id, d.name as doc_name
LIMIT 100
"""

results = client.execute_cypher(query)

print(f"Found {len(results)} IS_BASED_ON relationships")

# Create HAS_DOCUMENT relationships for each IS_BASED_ON relationship
created_count = 0
for result in results:
    release_name = result.get("release_name")
    release_id = result.get("release_id")
    doc_id = result.get("doc_id")
    doc_name = result.get("doc_name")
    
    print(f"Creating HAS_DOCUMENT: {release_name} -> {doc_name}")
    
    # Check if HAS_DOCUMENT already exists
    check_query = f"""
    MATCH (r:Release {{id: '{release_id}'}})-[HAS_DOCUMENT]->(d {{id: '{doc_id}'}})
    RETURN count(r) as count
    """
    check_result = client.execute_cypher(check_query)
    
    if check_result and check_result[0].get("count", 0) == 0:
        # Create HAS_DOCUMENT relationship
        client.execute_cypher(
            f"MATCH (r:Release {{id: '{release_id}'}}), (d {{id: '{doc_id}'}}) "
            f"CREATE (r)-[:HAS_DOCUMENT {{source: 'manual_link'}}]->(d)"
        )
        created_count += 1
    else:
        print(f"  HAS_DOCUMENT already exists, skipping")

print(f"\nCreated {created_count} new HAS_DOCUMENT relationships")
client.close()
