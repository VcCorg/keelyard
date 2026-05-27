#!/usr/bin/env python3
"""Update Release nodes with page_id from Confluence using pattern matching."""

from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.config import KGConfig
from agentic_cli.mcp_tool_client import confluence_get_space_pages
import re

# Connect to Neo4j
config = KGConfig.load()
client = Neo4jClient(config=config)
client.connect()

# Get all Release nodes
release_nodes = client.find_nodes(label="Release")

print(f"Found {len(release_nodes)} Release nodes")

# Get all pages from MTT space (Confluence space for CWOW Facility)
print("Fetching all pages from MTT space...")
try:
    pages = confluence_get_space_pages("MTT", limit=1000)
    print(f"Found {len(pages)} pages in MTT space")
    
    # Create title -> page_id mapping
    title_to_page_id = {page.get("title", ""): page.get("id") for page in pages}
except Exception as e:
    print(f"Error fetching pages from MTT space: {e}")
    title_to_page_id = {}

# Update each Release node with page_id from Confluence
updated_count = 0
for node in release_nodes:
    node_name = node.get("name", "")
    node_id = node.get("id")
    
    # Skip if already has page_id
    if node.get("page_id"):
        print(f"Skipping {node_name} - already has page_id")
        continue
    
    # Extract release number from name (e.g., "Release 29: Facility Management (CWOV)" -> "Release 29")
    match = re.search(r"Release (\d+)", node_name)
    if match:
        release_num = match.group(1)
        release_short_name = f"Release {release_num}"
        
        # Try to match with short name
        if release_short_name in title_to_page_id:
            page_id = title_to_page_id[release_short_name]
            print(f"Updating {node_name} with page_id={page_id} (matched as {release_short_name})")
            client.execute_cypher(
                f"MATCH (n:Release {{id: '{node_id}'}}) SET n.page_id = '{page_id}'"
            )
            updated_count += 1
        else:
            print(f"No matching Confluence page found for {node_name} (tried {release_short_name})")
    else:
        print(f"Could not extract release number from {node_name}")

print(f"\nUpdated {updated_count} Release nodes with page_id")
client.close()
