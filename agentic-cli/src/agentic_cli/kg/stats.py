"""Statistics for knowledge graph."""

from typing import Any, Dict

from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.neo4j_client import Neo4jClient


def get_stats(domain: str | None = None) -> Dict[str, Any]:
    """
    Get knowledge graph statistics.
    
    Args:
        domain: Optional domain slug to filter statistics
        
    Returns:
        Dictionary with statistics
    """
    config = KGConfig.load()
    
    with Neo4jClient(config) as client:
        stats = client.get_stats(domain=domain)
    
    return stats
