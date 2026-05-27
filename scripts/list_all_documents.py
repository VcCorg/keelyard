#!/usr/bin/env python3
"""List all Document nodes in the KG."""

from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.config import KGConfig

# Connect to Neo4j
config = KGConfig.load()
client = Neo4jClient(config=config)
client.connect()

# Get all Document nodes
document_nodes = client.find_nodes(label="Document")

print(f"Found {len(document_nodes)} Document nodes")
print("\nSample documents:")
for i, node in enumerate(document_nodes[:20]):
    name = node.get("name", "")
    print(f"  {i+1}. {name}")

client.close()
