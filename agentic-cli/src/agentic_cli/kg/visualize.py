"""Visualization for knowledge graph."""

from pathlib import Path
from typing import Optional

from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.neo4j_client import Neo4jClient


def create_visualization(
    output: Path,
    filter: Optional[str] = None,
    depth: int = 2,
) -> None:
    """
    Create an interactive HTML visualization of the knowledge graph.
    
    Args:
        output: Output file path
        filter: Filter nodes by type or property
        depth: Maximum depth for graph traversal
    """
    try:
        from pyvis.network import Network
    except ImportError:
        raise ImportError(
            "pyvis not installed. Install with: pip install pyvis"
        )
    
    config = KGConfig.load()
    
    # Fetch graph data
    with Neo4jClient(config) as client:
        if filter:
            query = f"""
            MATCH (n:{filter})-[r*1..{depth}]-(m)
            RETURN n, r, m
            LIMIT 500
            """
        else:
            query = f"""
            MATCH (n)-[r]-(m)
            RETURN n, r, m
            LIMIT 500
            """
        
        results = client.execute_cypher(query)
    
    # Create network visualization
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        directed=True,
    )
    
    # Set physics options for better layout
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 95,
                "springConstant": 0.04
            }
        }
    }
    """)
    
    # Add nodes and edges
    nodes_added = set()
    
    for result in results:
        # Add source node
        if "n" in result:
            node = result["n"]
            node_id = node.get("id", str(hash(str(node))))
            
            if node_id not in nodes_added:
                net.add_node(
                    node_id,
                    label=node.get("name", "Unknown"),
                    title=node.get("content", "")[:200],
                    color=get_node_color(node.get("type", "Entity")),
                )
                nodes_added.add(node_id)
        
        # Add target node
        if "m" in result:
            node = result["m"]
            node_id = node.get("id", str(hash(str(node))))
            
            if node_id not in nodes_added:
                net.add_node(
                    node_id,
                    label=node.get("name", "Unknown"),
                    title=node.get("content", "")[:200],
                    color=get_node_color(node.get("type", "Entity")),
                )
                nodes_added.add(node_id)
        
        # Add relationship
        if "r" in result and "n" in result and "m" in result:
            source_id = result["n"].get("id", str(hash(str(result["n"]))))
            target_id = result["m"].get("id", str(hash(str(result["m"]))))
            
            net.add_edge(
                source_id,
                target_id,
                title=str(result["r"]),
            )
    
    # Save visualization
    net.save_graph(str(output))


def get_node_color(node_type: str) -> str:
    """
    Get color for node based on type.
    
    Args:
        node_type: Node type
    
    Returns:
        Hex color code
    """
    colors = {
        "Person": "#FF6B6B",
        "Organization": "#4ECDC4",
        "Location": "#45B7D1",
        "Concept": "#FFA07A",
        "Product": "#98D8C8",
        "Event": "#F7DC6F",
        "Document": "#BB8FCE",
        "Entity": "#85C1E2",
    }
    
    return colors.get(node_type, "#95A5A6")
