"""Statistics for knowledge graph."""

from typing import Any, Dict

from dva_agentic_cli.kg.config import KGConfig
from dva_agentic_cli.kg.neo4j_client import Neo4jClient


def get_stats() -> Dict[str, Any]:
    """
    Get knowledge graph statistics.
    
    Returns:
        Dictionary with statistics
    """
    config = KGConfig.load()
    
    with Neo4jClient(config) as client:
        stats = client.get_stats()
    
    return stats
