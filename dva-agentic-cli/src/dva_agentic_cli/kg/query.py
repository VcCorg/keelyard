"""Query execution for knowledge graph."""

from typing import Any, Dict, List

from dva_agentic_cli.kg.config import KGConfig
from dva_agentic_cli.kg.neo4j_client import Neo4jClient


def execute_query(
    query_text: str,
    format: str = "natural",
    limit: int = 10,
    persona: str = None,
) -> List[str]:
    """
    Execute a query against the knowledge graph with optional persona filtering.
    
    Args:
        query_text: Query string
        format: Query format ('natural' or 'cypher')
        limit: Maximum number of results
        persona: Optional persona filter ('developer', 'business', or None)
    
    Returns:
        List of result strings
    """
    config = KGConfig.load()
    
    if format == "cypher":
        # Execute Cypher query directly
        cypher_query = query_text
        
        # Add persona filter if specified and not already in query
        if persona and "persona" not in cypher_query.lower():
            # Inject WHERE clause for persona filtering
            if "WHERE" in cypher_query.upper():
                cypher_query = cypher_query.replace("WHERE", f"WHERE n.persona = '{persona}' AND", 1)
            elif "RETURN" in cypher_query.upper():
                cypher_query = cypher_query.replace("RETURN", f"WHERE n.persona = '{persona}' RETURN", 1)
    else:
        # Convert natural language to Cypher with persona context
        cypher_query = natural_language_to_cypher(query_text, limit, persona)
    
    with Neo4jClient(config) as client:
        results = client.execute_cypher(cypher_query)
    
    # Format results as strings
    formatted_results = []
    for result in results:
        formatted_results.append(format_result(result))
    
    return formatted_results[:limit]


def natural_language_to_cypher(query: str, limit: int = 10, persona: str = None) -> str:
    """
    Convert natural language query to Cypher using Vertex AI with optional persona filtering.
    
    Args:
        query: Natural language query
        limit: Maximum number of results
        persona: Optional persona filter ('developer', 'business', or None)
    
    Returns:
        Cypher query string
    """
    config = KGConfig.load()
    
    if not config.is_vertex_ai_configured():
        # Fallback to simple pattern matching
        return simple_query_to_cypher(query, limit, persona)
    
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
    except ImportError:
        return simple_query_to_cypher(query, limit, persona)
    
    # Initialize Vertex AI
    vertexai.init(
        project=config.google_project_id,
        location=config.google_location,
    )
    
    model = GenerativeModel("gemini-2.5-flash-lite")
    
    # Add persona context to prompt if specified
    persona_instruction = ""
    if persona:
        persona_instruction = f"\nIMPORTANT: Filter results to only include nodes where persona = '{persona}'."
        if persona == "developer":
            persona_instruction += "\nFocus on Code:: labeled nodes (Code::Function, Code::Class, Code::Module, etc.)."
        elif persona == "business":
            persona_instruction += "\nFocus on document/requirement nodes (not Code:: labeled)."
    
    prompt = f"""
Convert the following natural language query to a Cypher query for Neo4j.
IMPORTANT: Always include WHERE n._source = 'dva_kg' to scope results to knowledge graph nodes only.

Natural language query: {query}
{persona_instruction}

Return ONLY the Cypher query, no explanations or markdown.
The query should return at most {limit} results.
Use LIMIT {limit} in the query.
"""
    
    try:
        response = model.generate_content(prompt)
        cypher = response.text.strip()
        
        # Remove markdown code blocks if present
        if cypher.startswith("```"):
            cypher = cypher.split("```")[1]
            if cypher.startswith("cypher"):
                cypher = cypher[6:]
            cypher = cypher.strip()
        
        return cypher
    
    except Exception as e:
        print(f"Error converting query: {e}")
        return simple_query_to_cypher(query, limit)


def simple_query_to_cypher(query: str, limit: int = 10, persona: str = None) -> str:
    """
    Simple pattern-based conversion of natural language to Cypher with persona filtering.
    
    Args:
        query: Natural language query
        limit: Maximum number of results
        persona: Optional persona filter ('developer', 'business', or None)
    
    Returns:
        Cypher query string
    """
    query_lower = query.lower()
    
    # Build persona filter clause (always scope to dva_kg source)
    base_filter = "WHERE n._source = 'dva_kg'"
    if persona:
        base_filter += f" AND n.persona = '{persona}'"
    persona_filter = base_filter + " "
    
    # Simple patterns
    if "all" in query_lower and "node" in query_lower:
        return f"MATCH (n) {persona_filter}RETURN n LIMIT {limit}"
    
    elif "relationship" in query_lower:
        if persona:
            return f"MATCH (a)-[r]->(b) WHERE a._source = 'dva_kg' AND (a.persona = '{persona}' OR b.persona = '{persona}') RETURN a, r, b LIMIT {limit}"
        return f"MATCH (a)-[r]->(b) WHERE a._source = 'dva_kg' RETURN a, r, b LIMIT {limit}"
    
    elif "find" in query_lower or "search" in query_lower:
        # Extract potential entity name
        words = query.split()
        search_term = " ".join(words[-2:])  # Take last 2 words as search term
        where_clause = f"WHERE n._source = 'dva_kg' AND (n.name CONTAINS '{search_term}' OR n.content CONTAINS '{search_term}')"
        if persona:
            where_clause += f" AND n.persona = '{persona}'"
        return f"""
        MATCH (n)
        {where_clause}
        RETURN n
        LIMIT {limit}
        """
    
    else:
        # Default: return all dva_kg nodes with persona filter
        return f"MATCH (n) {persona_filter}RETURN n LIMIT {limit}"


def format_result(result: Dict[str, Any]) -> str:
    """
    Format a query result as a readable string.
    
    Args:
        result: Query result dictionary
    
    Returns:
        Formatted string
    """
    parts = []
    
    for key, value in result.items():
        if isinstance(value, dict):
            # Node or relationship
            name = value.get("name", value.get("id", "Unknown"))
            node_type = value.get("type", "Node")
            parts.append(f"{node_type}: {name}")
        else:
            parts.append(f"{key}: {value}")
    
    return " | ".join(parts)
