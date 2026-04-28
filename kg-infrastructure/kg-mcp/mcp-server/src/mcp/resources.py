"""
MCP Resources Management

Handles loading and serving MCP resources (schemas, templates, queries).
Resources are read-only data that MCP clients can access to understand
the knowledge graph structure and capabilities.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Resource base directory
RESOURCES_DIR = Path(__file__).parent.parent / "resources"


class ResourceManager:
    """Manages MCP resources (schemas, templates, queries)."""
    
    def __init__(self):
        """Initialize resource manager."""
        self.resources_dir = RESOURCES_DIR
        self._cache: Dict[str, Any] = {}
        logger.info(f"Resource manager initialized: {self.resources_dir}")
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """
        List all available resources.
        
        Returns:
            List of resource descriptors with URI, name, description, mimeType
        """
        resources = []
        
        # Schemas
        for schema_file in (self.resources_dir / "schemas").glob("*.json"):
            provider = schema_file.stem
            resources.append({
                "uri": f"kg://schema/{provider}",
                "name": f"{provider.title()} Graph Schema",
                "description": f"Schema for {provider} knowledge graph",
                "mimeType": "application/json"
            })
        
        # Templates
        for template_file in (self.resources_dir / "templates").glob("*.json"):
            entity_type = template_file.stem
            resources.append({
                "uri": f"kg://template/{entity_type}",
                "name": f"{entity_type.title()} Entity Template",
                "description": f"Template for creating {entity_type} entities",
                "mimeType": "application/json"
            })
        
        # Queries
        for query_file in (self.resources_dir / "queries").glob("*.json"):
            query_set = query_file.stem
            resources.append({
                "uri": f"kg://queries/{query_set}",
                "name": f"{query_set.title()} Queries",
                "description": f"Collection of {query_set} Cypher queries",
                "mimeType": "application/json"
            })
        
        logger.info(f"Listed {len(resources)} resources")
        return resources
    
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a specific resource by URI.
        
        Args:
            uri: Resource URI (e.g., "kg://schema/neo4j")
        
        Returns:
            Resource content
        
        Raises:
            ValueError: If resource not found
        """
        # Check cache
        if uri in self._cache:
            logger.debug(f"Resource cache hit: {uri}")
            return self._cache[uri]
        
        # Parse URI
        if not uri.startswith("kg://"):
            raise ValueError(f"Invalid resource URI: {uri}")
        
        path = uri[5:]  # Remove "kg://" prefix
        parts = path.split("/")
        
        if len(parts) < 2:
            raise ValueError(f"Invalid resource URI format: {uri}")
        
        resource_type = parts[0]  # schema, template, queries
        resource_name = parts[1]  # neo4j, person, common
        
        # Map to file path
        if resource_type == "schema":
            file_path = self.resources_dir / "schemas" / f"{resource_name}.json"
        elif resource_type == "template":
            file_path = self.resources_dir / "templates" / f"{resource_name}.json"
        elif resource_type == "queries":
            file_path = self.resources_dir / "queries" / f"{resource_name}.json"
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")
        
        # Load resource
        if not file_path.exists():
            raise ValueError(f"Resource not found: {uri}")
        
        try:
            with open(file_path, "r") as f:
                content = json.load(f)
            
            # Cache the resource
            self._cache[uri] = content
            logger.info(f"Loaded resource: {uri}")
            return content
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse resource {uri}: {e}")
            raise ValueError(f"Invalid JSON in resource: {uri}")
        except Exception as e:
            logger.error(f"Failed to load resource {uri}: {e}")
            raise ValueError(f"Failed to load resource: {uri}")
    
    def get_schema(self, provider: str) -> Dict[str, Any]:
        """
        Get schema for a specific provider.
        
        Args:
            provider: Provider name (neo4j, lightrag)
        
        Returns:
            Schema content
        """
        uri = f"kg://schema/{provider}"
        return self.read_resource(uri)
    
    def get_template(self, entity_type: str) -> Dict[str, Any]:
        """
        Get template for a specific entity type.
        
        Args:
            entity_type: Entity type (patient, facility)
        
        Returns:
            Template content
        """
        uri = f"kg://template/{entity_type}"
        return self.read_resource(uri)
    
    def get_queries(self, query_set: str = "common") -> Dict[str, Any]:
        """
        Get query collection.
        
        Args:
            query_set: Query set name (common, advanced)
        
        Returns:
            Query collection content
        """
        uri = f"kg://queries/{query_set}"
        return self.read_resource(uri)
    
    def clear_cache(self):
        """Clear resource cache."""
        self._cache.clear()
        logger.info("Resource cache cleared")
    
    def validate_resources(self) -> Dict[str, Any]:
        """
        Validate all resources can be loaded.
        
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "resources": [],
            "errors": []
        }
        
        for resource in self.list_resources():
            uri = resource["uri"]
            try:
                self.read_resource(uri)
                results["resources"].append({
                    "uri": uri,
                    "status": "valid"
                })
            except Exception as e:
                results["valid"] = False
                results["errors"].append({
                    "uri": uri,
                    "error": str(e)
                })
                logger.error(f"Resource validation failed for {uri}: {e}")
        
        return results


# Global resource manager instance
resource_manager = ResourceManager()
