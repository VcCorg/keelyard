#!/usr/bin/env python3
"""Link Document nodes to Release nodes based on name pattern matching."""

from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.config import KGConfig
import re

# Connect to Neo4j
config = KGConfig.load()
client = Neo4jClient(config=config)
client.connect()

# Get all Release nodes
release_nodes = client.find_nodes(label="Release")

print(f"Found {len(release_nodes)} Release nodes")

# Get all Document nodes
document_nodes = client.find_nodes(label="Document")

print(f"Found {len(document_nodes)} Document nodes")

# Create Release name -> node mapping
release_map = {}
for node in release_nodes:
    name = node.get("name", "")
    node_id = node.get("id")
    # Extract release number (e.g., "Release 28" from "Release 28: Facility Management (CWOV)")
    match = re.search(r"Release (\d+)", name)
    if match:
        release_num = match.group(1)
        release_map[release_num] = {"name": name, "id": node_id}

print(f"\nRelease mapping: {list(release_map.keys())}")

# Link documents to releases based on name pattern
created_count = 0
for doc_node in document_nodes:
    doc_name = doc_node.get("name", "")
    doc_id = doc_node.get("id")
    
    # Check if document name contains a release number
    match = re.search(r"Release (\d+)", doc_name)
    if match:
        release_num = match.group(1)
        if release_num in release_map:
            release = release_map[release_num]
            print(f"Linking {doc_name} to {release['name']}")
            
            # Check if HAS_DOCUMENT already exists
            check_query = f"""
            MATCH (r:Release {{id: '{release['id']}'}})-[HAS_DOCUMENT]->(d {{id: '{doc_id}'}})
            RETURN count(r) as count
            """
            check_result = client.execute_cypher(check_query)
            
            if check_result and check_result[0].get("count", 0) == 0:
                # Create HAS_DOCUMENT relationship
                client.execute_cypher(
                    f"MATCH (r:Release {{id: '{release['id']}'}}), (d {{id: '{doc_id}'}}) "
                    f"CREATE (r)-[:HAS_DOCUMENT {{source: 'name_pattern_match'}}]->(d)"
                )
                created_count += 1
            else:
                print(f"  HAS_DOCUMENT already exists, skipping")

print(f"\nCreated {created_count} new HAS_DOCUMENT relationships")
client.close()
