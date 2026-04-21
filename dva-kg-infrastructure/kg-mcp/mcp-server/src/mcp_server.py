"""
DVA Knowledge Graph MCP Server

This server exposes KG operations (query, search, ingest, etc.) via the Model Context Protocol (MCP).
It supports both Neo4j and LightRAG backends and can be used by IDEs and AI assistants.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=os.getenv("MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KGMCPServer:
    """MCP Server for Knowledge Graph operations."""
    
    def __init__(self):
        """Initialize MCP server with both Neo4j and LightRAG support."""
        self.config = self._load_config()
        self.neo4j_available = self._check_neo4j_available()
        self.lightrag_available = self._check_lightrag_available()
        logger.info(f"Initialized KG MCP Server")
        logger.info(f"  Neo4j: {'✓ Available' if self.neo4j_available else '✗ Not configured'}")
        logger.info(f"  LightRAG: {'✓ Available' if self.lightrag_available else '✗ Not configured'}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
            "neo4j": {
                "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                "user": os.getenv("NEO4J_USER", "neo4j"),
                "password": os.getenv("NEO4J_PASSWORD", "password"),
            },
            "lightrag": {
                "url": os.getenv("LIGHTRAG_URL", "http://localhost:8001"),
            },
            "vertex_ai": {
                "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                "location": os.getenv("GOOGLE_LOCATION", "us-central1"),
                "model": os.getenv("VERTEX_AI_MODEL", "gemini-1.5-flash"),
            }
        }
        return config
    
    def _check_neo4j_available(self) -> bool:
        """Check if Neo4j is configured and available."""
        uri = self.config["neo4j"]["uri"]
        return uri and uri != "bolt://localhost:7687" or os.getenv("NEO4J_URI")
    
    def _check_lightrag_available(self) -> bool:
        """Check if LightRAG is configured and available."""
        url = self.config["lightrag"]["url"]
        return url and url != "http://localhost:8001" or os.getenv("LIGHTRAG_URL")
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "providers": {
                "neo4j": {
                    "available": self.neo4j_available,
                    "uri": self.config["neo4j"]["uri"] if self.neo4j_available else None,
                },
                "lightrag": {
                    "available": self.lightrag_available,
                    "url": self.config["lightrag"]["url"] if self.lightrag_available else None,
                }
            }
        }


# Initialize server
kg_server = KGMCPServer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    logger.info("Starting DVA KG MCP Server...")
    logger.info(f"Neo4j: {'Available' if kg_server.neo4j_available else 'Not configured'}")
    logger.info(f"LightRAG: {'Available' if kg_server.lightrag_available else 'Not configured'}")
    yield
    logger.info("Shutting down DVA KG MCP Server...")


# Create FastAPI app
app = FastAPI(
    title="DVA Knowledge Graph MCP Server",
    description="MCP server for DVA Knowledge Graph operations",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "providers": {
            "neo4j": kg_server.neo4j_available,
            "lightrag": kg_server.lightrag_available
        },
        "version": "0.1.0"
    }


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "status": "running",
        "providers": kg_server.get_provider_status(),
        "mcp_version": "2024-11-05",
        "server_version": "0.1.0"
    }


# ============================================================================
# MCP Protocol Endpoints
# ============================================================================

@app.post("/mcp/initialize")
async def mcp_initialize(request: Request):
    """
    MCP initialization handshake.
    
    This endpoint is called when an MCP client (IDE, AI assistant) connects
    to discover server capabilities.
    """
    try:
        body = await request.json()
        logger.info(f"MCP Initialize request: {body}")
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                },
                "prompts": {}
            },
            "serverInfo": {
                "name": "dva-kg-mcp",
                "version": "0.1.0",
                "providers": {
                    "neo4j": kg_server.neo4j_available,
                    "lightrag": kg_server.lightrag_available
                }
            }
        }
    except Exception as e:
        logger.error(f"Error in MCP initialize: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/list")
async def mcp_list_tools():
    """
    List available MCP tools.
    
    Returns a catalog of all KG operations available via MCP.
    """
    try:
        tools = [
            {
                "name": "kg_query",
                "description": "Query the knowledge graph using natural language or Cypher. Supports both Neo4j and LightRAG backends.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Query text (natural language or Cypher)"
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["neo4j", "lightrag"],
                            "default": "neo4j",
                            "description": "Which KG provider to use (neo4j or lightrag)"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["natural", "cypher"],
                            "default": "natural",
                            "description": "Query format (cypher only works with neo4j)"
                        },
                        "limit": {
                            "type": "number",
                            "default": 10,
                            "description": "Maximum number of results"
                        },
                        "persona": {
                            "type": "string",
                            "enum": ["developer", "business", "null"],
                            "description": "Optional persona filter for code analysis results"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "kg_search",
                "description": "Search the knowledge graph semantically or by exact match. Uses embeddings for semantic search.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Search text"
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["neo4j", "lightrag"],
                            "default": "neo4j",
                            "description": "Which KG provider to use (neo4j or lightrag)"
                        },
                        "semantic": {
                            "type": "boolean",
                            "default": True,
                            "description": "Use semantic search (true) or exact match (false)"
                        },
                        "limit": {
                            "type": "number",
                            "default": 10,
                            "description": "Maximum number of results"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "kg_stats",
                "description": "Get knowledge graph statistics including node counts, relationship counts, and entity types.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["neo4j", "lightrag"],
                            "default": "neo4j",
                            "description": "Which KG provider to use (neo4j or lightrag)"
                        }
                    }
                }
            },
            {
                "name": "kg_ingest",
                "description": "Ingest data into the knowledge graph from configured data sources.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Data source name (configured via 'dva data create')"
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["neo4j", "lightrag"],
                            "default": "neo4j",
                            "description": "Which KG provider to use (neo4j or lightrag)"
                        },
                        "extract_entities": {
                            "type": "boolean",
                            "default": True,
                            "description": "Extract entities using AI"
                        },
                        "build_relationships": {
                            "type": "boolean",
                            "default": True,
                            "description": "Build relationships between entities"
                        }
                    },
                    "required": ["source"]
                }
            }
        ]
        
        logger.info(f"Returning {len(tools)} tools")
        return {"tools": tools}
    
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/call")
async def mcp_call_tool(request: Request):
    """
    Execute an MCP tool.
    
    This is the main endpoint that translates MCP requests to KG operations.
    """
    try:
        body = await request.json()
        tool_name = body.get("name")
        arguments = body.get("arguments", {})
        
        logger.info(f"Tool call: {tool_name} with args: {arguments}")
        
        # Route to appropriate handler
        if tool_name == "kg_query":
            result = await handle_kg_query(arguments)
        elif tool_name == "kg_search":
            result = await handle_kg_search(arguments)
        elif tool_name == "kg_stats":
            result = await handle_kg_stats(arguments)
        elif tool_name == "kg_ingest":
            result = await handle_kg_ingest(arguments)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        # Return in MCP format
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    
    except Exception as e:
        logger.error(f"Error calling tool: {e}", exc_info=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }
            ],
            "isError": True
        }


# ============================================================================
# MCP Resources Endpoints
# ============================================================================

@app.post("/mcp/resources/list")
async def mcp_list_resources():
    """
    List available MCP resources.
    
    Resources are read-only data that clients can access to understand
    the knowledge graph structure (schemas, templates, queries).
    """
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from mcp.resources import resource_manager
        
        resources = resource_manager.list_resources()
        logger.info(f"Returning {len(resources)} resources")
        
        return {"resources": resources}
    
    except Exception as e:
        logger.error(f"Error listing resources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/resources/read")
async def mcp_read_resource(request: Request):
    """
    Read a specific resource by URI.
    
    Returns the content of a resource (schema, template, or query collection).
    """
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from mcp.resources import resource_manager
        
        body = await request.json()
        uri = body.get("uri")
        
        if not uri:
            raise HTTPException(status_code=400, detail="Missing 'uri' parameter")
        
        logger.info(f"Reading resource: {uri}")
        content = resource_manager.read_resource(uri)
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(content, indent=2)
                }
            ]
        }
    
    except ValueError as e:
        logger.error(f"Resource not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading resource: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tool Handlers (Bridge to KG operations)
# ============================================================================

async def handle_kg_query(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle kg_query tool.
    
    Translates MCP request to KG query operation.
    """
    from dva_agentic_cli.kg.config import KGConfig
    
    # Get provider from args (defaults to neo4j)
    provider = args.get("provider", "neo4j")
    
    # Check if provider is available
    if provider == "neo4j" and not kg_server.neo4j_available:
        raise ValueError("Neo4j is not configured. Please set NEO4J_URI environment variable.")
    if provider == "lightrag" and not kg_server.lightrag_available:
        raise ValueError("LightRAG is not configured. Please set LIGHTRAG_URL environment variable.")
    
    if provider == "lightrag":
        # Use LightRAG client directly
        from dva_agentic_cli.kg.lightrag_client import LightRAGClient
        
        client = LightRAGClient(
            base_url=kg_server.config["lightrag"]["url"],
            timeout=30.0
        )
        
        # Determine query mode (default to hybrid)
        mode = args.get("mode", "hybrid")
        
        # Execute query
        result = client.query(
            query=args["query"],
            mode=mode,
            top_k=args.get("limit", 10)
        )
        client.close()
        
        # Extract result text
        result_text = result.get("result", "No results found")
        
        return {
            "provider": provider,
            "query": args["query"],
            "mode": mode,
            "result": result_text
        }
    else:
        # Use Neo4j execute_query
        from dva_agentic_cli.kg.query import execute_query
        
        # Load config
        config = KGConfig.load()
        
        # Override with environment variables
        config.provider = provider
        config.neo4j_uri = kg_server.config["neo4j"]["uri"]
        config.neo4j_username = kg_server.config["neo4j"]["user"]
        config.neo4j_password = kg_server.config["neo4j"]["password"]
        
        # Execute query
        results = execute_query(
            query_text=args["query"],
            format=args.get("format", "natural"),
            limit=args.get("limit", 10),
            persona=args.get("persona")
        )
        
        return {
            "provider": provider,
            "query": args["query"],
            "format": args.get("format", "natural"),
            "results": results,
            "count": len(results)
        }


async def handle_kg_search(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle kg_search tool.
    
    Translates MCP request to KG search operation.
    """
    from dva_agentic_cli.kg.search import search_graph
    from dva_agentic_cli.kg.config import KGConfig
    
    # Get provider from args (defaults to neo4j)
    provider = args.get("provider", "neo4j")
    
    # Check if provider is available
    if provider == "neo4j" and not kg_server.neo4j_available:
        raise ValueError("Neo4j is not configured. Please set NEO4J_URI environment variable.")
    if provider == "lightrag" and not kg_server.lightrag_available:
        raise ValueError("LightRAG is not configured. Please set LIGHTRAG_URL environment variable.")
    
    # Load config
    config = KGConfig.load()
    config.provider = provider
    
    if provider == "neo4j":
        config.neo4j_uri = kg_server.config["neo4j"]["uri"]
        config.neo4j_username = kg_server.config["neo4j"]["user"]
        config.neo4j_password = kg_server.config["neo4j"]["password"]
    else:
        config.lightrag_url = kg_server.config["lightrag"]["url"]
    
    # Execute search
    results = search_graph(
        text=args["text"],
        semantic=args.get("semantic", True),
        limit=args.get("limit", 10)
    )
    
    return {
        "provider": provider,
        "query": args["text"],
        "semantic": args.get("semantic", True),
        "results": results,
        "count": len(results)
    }


async def handle_kg_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle kg_stats tool.
    
    Returns knowledge graph statistics.
    """
    from dva_agentic_cli.kg.stats import get_graph_stats
    from dva_agentic_cli.kg.config import KGConfig
    
    # Get provider from args (defaults to neo4j)
    provider = args.get("provider", "neo4j")
    
    # Check if provider is available
    if provider == "neo4j" and not kg_server.neo4j_available:
        raise ValueError("Neo4j is not configured. Please set NEO4J_URI environment variable.")
    if provider == "lightrag" and not kg_server.lightrag_available:
        raise ValueError("LightRAG is not configured. Please set LIGHTRAG_URL environment variable.")
    
    config = KGConfig.load()
    config.provider = provider
    
    if provider == "neo4j":
        config.neo4j_uri = kg_server.config["neo4j"]["uri"]
        config.neo4j_username = kg_server.config["neo4j"]["user"]
        config.neo4j_password = kg_server.config["neo4j"]["password"]
    else:
        config.lightrag_url = kg_server.config["lightrag"]["url"]
    
    stats = get_graph_stats(config)
    stats["provider"] = provider
    return stats


async def handle_kg_ingest(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle kg_ingest tool.
    
    Ingests data from configured source.
    """
    return {
        "status": "not_implemented",
        "message": "Ingestion via MCP is not yet implemented. Use 'dva kg ingest' CLI command.",
        "source": args.get("source")
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_PORT", 8125))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
