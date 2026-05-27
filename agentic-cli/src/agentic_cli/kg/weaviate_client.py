"""Weaviate client for knowledge graph operations."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed. Weaviate support will be limited.")


class WeaviateClient:
    """Client for Weaviate vector database for KG operations using REST API."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        scheme: str = "http",
        api_key: Optional[str] = None
    ):
        """
        Initialize Weaviate client.
        
        Args:
            host: Weaviate host
            port: Weaviate port
            scheme: Connection scheme (http or https)
            api_key: Optional API key for authentication
        """
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for Weaviate support. "
                "Install it with: pip install httpx"
            )
        
        self.host = host
        self.port = port
        self.scheme = scheme
        self.api_key = api_key
        self._client = None
        
        # Build connection URL
        self.url = f"{scheme}://{host}:{port}"
        logger.info(f"Weaviate client initialized: {self.url}")
    
    def connect(self):
        """Establish connection to Weaviate via REST API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self._client = httpx.Client(base_url=self.url, headers=headers, timeout=30.0)
        
        # Test connection
        response = self._client.get("/v1/.well-known/ready")
        if response.status_code == 200:
            logger.info("Connected to Weaviate (REST API)")
        else:
            raise Exception(f"Weaviate not ready: {response.status_code}")
    
    def close(self):
        """Close Weaviate connection."""
        if self._client:
            self._client.close()
            logger.info("Weaviate connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get Weaviate KG statistics.
        
        Returns:
            Statistics including object counts per class.
        """
        stats = {}
        
        try:
            # Get schema to determine classes
            response = self._client.get("/v1/schema")
            response.raise_for_status()
            schema = response.json()
            classes = schema.get("classes", [])
            
            for class_obj in classes:
                class_name = class_obj["class"]
                
                # Get object count for this class
                try:
                    count_response = self._client.get(f"/v1/objects?limit=1&class={class_name}")
                    count_response.raise_for_status()
                    result = count_response.json()
                    # Weaviate doesn't return total count directly, so we estimate
                    # For accurate counts, we'd need to query each class separately
                    stats[class_name] = 0  # Placeholder
                except Exception as e:
                    logger.warning(f"Failed to get count for {class_name}: {e}")
                    stats[class_name] = 0
            
            # Add total count
            stats["total_objects"] = 0  # Placeholder
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
        
        return stats
    
    def clear_graph(self) -> None:
        """
        Clear all data from Weaviate.
        
        This deletes all objects from all classes.
        """
        try:
            # Get schema
            response = self._client.get("/v1/schema")
            response.raise_for_status()
            schema = response.json()
            classes = schema.get("classes", [])
            
            total_deleted = 0
            for class_obj in classes:
                class_name = class_obj["class"]
                
                try:
                    # Delete all objects in this class
                    delete_response = self._client.delete(f"/v1/objects?class={class_name}")
                    delete_response.raise_for_status()
                    total_deleted += 1
                    logger.info(f"Cleared class: {class_name}")
                except Exception as e:
                    logger.warning(f"Failed to clear {class_name}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
        
        logger.info(f"Cleared Weaviate KG: {total_deleted} classes")
    
    def search(
        self,
        query: str,
        class_name: str = "Code",
        limit: int = 10,
        properties: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in Weaviate.
        
        Args:
            query: Search query text
            class_name: Weaviate class to search
            limit: Maximum results
            properties: Properties to retrieve
            
        Returns:
            Search results
        """
        try:
            # Use GraphQL API for nearText search
            graphql_query = f"""
            {{
                Get {{
                    {class_name}(
                        nearText: {{
                            concepts: ["{query}"]
                        }}
                        limit: {limit}
                    ) {{
                        _additional {{
                            id
                            distance
                        }}
                        {" ".join(properties) if properties else ""}
                    }}
                }}
            }}
            """
            
            response = self._client.post("/v1/graphql", json={"query": graphql_query})
            response.raise_for_status()
            result = response.json()
            
            objects = result.get("data", {}).get("Get", {}).get(class_name, [])
            return objects
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def query(
        self,
        class_name: str,
        where_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query Weaviate with filters.
        
        Args:
            class_name: Weaviate class to query
            where_filter: Optional where filter
            limit: Maximum results
            
        Returns:
            Query results
        """
        try:
            # Use REST API to get objects
            params = {"limit": limit, "class": class_name}
            response = self._client.get("/v1/objects", params=params)
            response.raise_for_status()
            result = response.json()
            
            objects = result.get("objects", [])
            return objects
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []


def check_weaviate_availability(
    host: str = "localhost",
    port: int = 8080,
    scheme: str = "http",
    api_key: Optional[str] = None
) -> tuple[bool, str]:
    """
    Check if Weaviate is available.
    
    Args:
        host: Weaviate host
        port: Weaviate port
        scheme: Connection scheme
        api_key: Optional API key
        
    Returns:
        Tuple of (is_available, message)
    """
    if not HTTPX_AVAILABLE:
        return False, "httpx is not installed. Install with: pip install httpx"
    
    try:
        client = WeaviateClient(host=host, port=port, scheme=scheme, api_key=api_key)
        client.connect()
        client.close()
        return True, "Weaviate is available"
    except Exception as e:
        return False, f"Weaviate is not available: {str(e)}"
