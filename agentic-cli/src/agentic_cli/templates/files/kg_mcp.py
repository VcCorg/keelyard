"""Generate KG MCP server and workspace integration files."""

from pathlib import Path
from agentic_cli.templates.config import TemplateConfig


KG_MCP_SERVER = '''"""Knowledge Graph MCP Server - Exposes KG operations via MCP protocol."""

import asyncio
import json
import logging
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import Settings

logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Create MCP server
server = Server("kg-mcp-server")


def get_neo4j_driver():
    """Get Neo4j driver instance."""
    from neo4j import GraphDatabase
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available KG tools."""
    return [
        Tool(
            name="kg_query",
            description="Execute a Cypher query against the knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "cypher": {
                        "type": "string",
                        "description": "Cypher query to execute"
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters (optional)",
                        "default": {}
                    }
                },
                "required": ["cypher"]
            }
        ),
        Tool(
            name="kg_search",
            description="Search the knowledge graph using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="kg_ingest",
            description="Ingest entities and relationships into the knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "description": "List of entities to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "properties": {"type": "object"}
                            }
                        }
                    },
                    "relationships": {
                        "type": "array",
                        "description": "List of relationships to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_id": {"type": "string"},
                                "to_id": {"type": "string"},
                                "type": {"type": "string"},
                                "properties": {"type": "object"}
                            }
                        }
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="kg_stats",
            description="Get statistics about the knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a KG tool."""
    try:
        if name == "kg_query":
            result = await kg_query(arguments.get("cypher", ""), arguments.get("params", {}))
        elif name == "kg_search":
            result = await kg_search(arguments.get("query", ""), arguments.get("limit", 10))
        elif name == "kg_ingest":
            result = await kg_ingest(
                arguments.get("entities", []),
                arguments.get("relationships", [])
            )
        elif name == "kg_stats":
            result = await kg_stats()
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def kg_query(cypher: str, params: dict = None) -> dict:
    """Execute a Cypher query."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            records = [dict(record) for record in result]
            return {"records": records, "count": len(records)}
    finally:
        driver.close()


async def kg_search(query: str, limit: int = 10) -> dict:
    """Search the knowledge graph."""
    # Full-text search across node properties
    cypher = """
    CALL db.index.fulltext.queryNodes('search_index', $query) 
    YIELD node, score
    RETURN node, score
    ORDER BY score DESC
    LIMIT $limit
    """
    try:
        return await kg_query(cypher, {"query": query, "limit": limit})
    except Exception:
        # Fallback to basic CONTAINS search if fulltext index doesn't exist
        cypher = """
        MATCH (n)
        WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $query)
        RETURN n as node, 1.0 as score
        LIMIT $limit
        """
        return await kg_query(cypher, {"query": query, "limit": limit})


async def kg_ingest(entities: list, relationships: list) -> dict:
    """Ingest entities and relationships."""
    driver = get_neo4j_driver()
    entities_created = 0
    relationships_created = 0
    
    try:
        with driver.session() as session:
            # Create entities
            for entity in entities:
                label = entity.get("label", "Entity")
                props = entity.get("properties", {})
                cypher = f"CREATE (n:{label} $props) RETURN n"
                session.run(cypher, {"props": props})
                entities_created += 1
            
            # Create relationships
            for rel in relationships:
                cypher = """
                MATCH (a), (b)
                WHERE id(a) = $from_id AND id(b) = $to_id
                CREATE (a)-[r:$type $props]->(b)
                RETURN r
                """
                session.run(cypher, {
                    "from_id": rel.get("from_id"),
                    "to_id": rel.get("to_id"),
                    "type": rel.get("type", "RELATED_TO"),
                    "props": rel.get("properties", {})
                })
                relationships_created += 1
        
        return {
            "entities_created": entities_created,
            "relationships_created": relationships_created
        }
    finally:
        driver.close()


async def kg_stats() -> dict:
    """Get knowledge graph statistics."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            # Node count
            node_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_result.single()["count"]
            
            # Relationship count
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
            
            # Label distribution
            label_result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
            """)
            labels = {record["label"]: record["count"] for record in label_result}
            
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "labels": labels
            }
    finally:
        driver.close()


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
'''


KG_WORKSPACE_CLIENT = '''"""Knowledge Graph Workspace Client - Connect to existing agent-cli kg workspace."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class KGWorkspaceClient:
    """
    Client for interacting with an existing agent-cli kg workspace.
    
    This allows your agent to use a pre-configured knowledge graph
    without managing Neo4j connections directly.
    
    Usage:
        client = KGWorkspaceClient("my-workspace")
        
        # Query the knowledge graph
        results = client.query("What are the main entities?")
        
        # Search for specific content
        results = client.search("patient records")
        
        # Get statistics
        stats = client.stats()
    """
    
    def __init__(self, workspace_name: str):
        self.workspace_name = workspace_name
        self._validate_workspace()
    
    def _validate_workspace(self) -> None:
        """Validate that the workspace exists."""
        result = subprocess.run(
            ["agent-cli", "kg", "workspace", "list"],
            capture_output=True,
            text=True
        )
        if self.workspace_name not in result.stdout:
            raise ValueError(f"Workspace '{self.workspace_name}' not found. "
                           f"Create it with: agent-cli kg workspace create {self.workspace_name}")
    
    def _run_dva_command(self, *args) -> Dict[str, Any]:
        """Run an agent-cli kg command and return parsed output."""
        cmd = ["agent-cli", "kg", *args, "--workspace", self.workspace_name, "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"agent-cli kg command failed: {result.stderr}")
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout}
    
    def query(self, question: str, persona: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the knowledge graph with natural language.
        
        Args:
            question: Natural language question
            persona: Optional persona for context
        
        Returns:
            Query results with answer and sources
        """
        args = ["query", question]
        if persona:
            args.extend(["--persona", persona])
        return self._run_dva_command(*args)
    
    def search(
        self,
        text: str,
        mode: str = "hybrid",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search the knowledge graph.
        
        Args:
            text: Search text
            mode: Search mode (semantic, exact, hybrid)
            limit: Maximum results
        
        Returns:
            Search results
        """
        return self._run_dva_command(
            "search", text,
            "--mode", mode,
            "--limit", str(limit)
        )
    
    def stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        return self._run_dva_command("stats")
    
    def ingest(
        self,
        path: str,
        format: str = "auto",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ingest data into the knowledge graph.
        
        Args:
            path: Path to file or directory
            format: File format (auto, pdf, txt, csv, json)
            tags: Optional tags for the ingested data
        
        Returns:
            Ingestion results
        """
        args = ["ingest", "--path", path, "--format", format]
        if tags:
            args.extend(["--tags", ",".join(tags)])
        return self._run_dva_command(*args)


# Convenience functions for direct use
_default_client: Optional[KGWorkspaceClient] = None


def init_workspace(workspace_name: str) -> KGWorkspaceClient:
    """Initialize the default workspace client."""
    global _default_client
    _default_client = KGWorkspaceClient(workspace_name)
    return _default_client


def query(question: str, persona: Optional[str] = None) -> Dict[str, Any]:
    """Query the default workspace."""
    if not _default_client:
        raise RuntimeError("Workspace not initialized. Call init_workspace() first.")
    return _default_client.query(question, persona)


def search(text: str, mode: str = "hybrid", limit: int = 10) -> Dict[str, Any]:
    """Search the default workspace."""
    if not _default_client:
        raise RuntimeError("Workspace not initialized. Call init_workspace() first.")
    return _default_client.search(text, mode, limit)


def stats() -> Dict[str, Any]:
    """Get stats from the default workspace."""
    if not _default_client:
        raise RuntimeError("Workspace not initialized. Call init_workspace() first.")
    return _default_client.stats()
'''


KG_MCP_INIT = '''"""Knowledge Graph MCP Integration."""

from .workspace_client import (
    KGWorkspaceClient,
    init_workspace,
    query,
    search,
    stats,
)

__all__ = [
    "KGWorkspaceClient",
    "init_workspace",
    "query",
    "search",
    "stats",
]
'''


KG_MCP_EXAMPLE = '''"""Example: Using KG MCP Server with an agent."""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """Example of connecting to the KG MCP server."""
    
    # Connect to the KG MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["src/mcp/kg_server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available KG tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Query the knowledge graph
            print("\\nQuerying knowledge graph...")
            result = await session.call_tool(
                "kg_query",
                {"cypher": "MATCH (n) RETURN n LIMIT 5"}
            )
            print(f"Query result: {result.content[0].text}")
            
            # Get statistics
            print("\\nGetting KG statistics...")
            stats = await session.call_tool("kg_stats", {})
            print(f"Stats: {stats.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
'''


KG_WORKSPACE_EXAMPLE = '''"""Example: Using KG Workspace Client with an agent."""

from kg import init_workspace, query, search, stats


def main():
    """Example of using the KG workspace client."""

    # Initialize connection to workspace
    # This workspace should be created with: agent-cli kg workspace create my-workspace
    workspace = init_workspace("WORKSPACE_NAME")
    
    print("Connected to KG workspace: WORKSPACE_NAME")
    
    # Get statistics
    print("\\nKnowledge Graph Statistics:")
    kg_stats = stats()
    print(f"  Nodes: {kg_stats.get('node_count', 'N/A')}")
    print(f"  Relationships: {kg_stats.get('relationship_count', 'N/A')}")
    
    # Query with natural language
    print("\\nQuerying knowledge graph...")
    result = query("What are the main entities in the graph?")
    print(f"Answer: {result.get('answer', result)}")
    
    # Search for specific content
    print("\\nSearching for 'patient'...")
    search_results = search("patient", mode="hybrid", limit=5)
    print(f"Found {len(search_results.get('results', []))} results")


if __name__ == "__main__":
    main()
'''


def generate_kg_mcp_files(project_dir: Path, config: TemplateConfig) -> None:
    """Generate KG MCP server files."""
    if not config.include_kg_mcp:
        return
    
    # Create mcp directory
    mcp_dir = project_dir / "src" / "mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    
    # Write MCP server files
    (mcp_dir / "__init__.py").write_text('"""MCP Server for Knowledge Graph operations."""\n')
    (mcp_dir / "kg_server.py").write_text(KG_MCP_SERVER)
    
    # Write example
    examples_dir = project_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    (examples_dir / "kg_mcp_client_example.py").write_text(KG_MCP_EXAMPLE)


def generate_kg_workspace_files(project_dir: Path, config: TemplateConfig) -> None:
    """Generate KG workspace integration files."""
    if not config.kg_workspace:
        return
    
    # Create kg directory
    kg_dir = project_dir / "src" / "kg"
    kg_dir.mkdir(parents=True, exist_ok=True)
    
    # Write workspace client files
    (kg_dir / "__init__.py").write_text(KG_MCP_INIT)
    (kg_dir / "workspace_client.py").write_text(KG_WORKSPACE_CLIENT)
    
    # Write example with workspace name substituted
    examples_dir = project_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    example_content = KG_WORKSPACE_EXAMPLE.replace("WORKSPACE_NAME", config.kg_workspace)
    (examples_dir / "kg_workspace_example.py").write_text(example_content)
