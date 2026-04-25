"""Search functionality for knowledge graph."""

from typing import Any, Dict, List

from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.entity_extraction import generate_embeddings
from agentic_cli.kg.neo4j_client import Neo4jClient


def search_graph(
    text: str,
    semantic: bool = True,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search the knowledge graph.
    
    Args:
        text: Search text
        semantic: Use semantic search (embeddings) or exact match
        limit: Maximum number of results
    
    Returns:
        List of search results
    """
    config = KGConfig.load()
    
    if semantic and config.is_vertex_ai_configured():
        return semantic_search(text, limit, config)
    else:
        return exact_search(text, limit, config)


def semantic_search(
    text: str,
    limit: int,
    config: KGConfig,
) -> List[Dict[str, Any]]:
    """
    Perform semantic search using embeddings.
    
    Args:
        text: Search text
        limit: Maximum number of results
        config: KG configuration
    
    Returns:
        List of search results with relevance scores
    """
    # Generate embedding for search text
    embeddings = generate_embeddings([text], config)
    search_embedding = embeddings[0]
    
    with Neo4jClient(config) as client:
        results = client.search_by_embedding(search_embedding, limit)
    
    # Format results
    formatted_results = []
    for result in results:
        node = result["node"]
        formatted_results.append({
            "entity": node.get("name", "Unknown"),
            "type": node.get("type", "Entity"),
            "description": node.get("content", "")[:200],
            "score": result["score"],
        })
    
    return formatted_results


def exact_search(
    text: str,
    limit: int,
    config: KGConfig,
) -> List[Dict[str, Any]]:
    """
    Perform exact text search.
    
    Args:
        text: Search text
        limit: Maximum number of results
        config: KG configuration
    
    Returns:
        List of search results
    """
    query = f"""
    MATCH (n)
    WHERE n._source = 'dva_kg' AND (n.name CONTAINS $text OR n.content CONTAINS $text)
    RETURN n
    LIMIT $limit
    """
    
    with Neo4jClient(config) as client:
        results = client.execute_cypher(query, {"text": text, "limit": limit})
    
    # Format results
    formatted_results = []
    for result in results:
        node = result.get("n", {})
        formatted_results.append({
            "entity": node.get("name", "Unknown"),
            "type": node.get("type", "Entity"),
            "description": node.get("content", "")[:200],
        })
    
    return formatted_results
