"""Template configuration and use case to tools mapping."""

from dataclasses import dataclass, field
from typing import Optional

from agentic_cli.templates.enums import Framework, UseCase, Tool


# Mapping of use cases to their required tools
USE_CASE_TOOLS: dict[UseCase, list[Tool]] = {
    UseCase.BASIC: [
        Tool.CALCULATOR,
        Tool.TEXT_ANALYZER,
        Tool.FILE_READER,
    ],
    UseCase.RAG: [
        Tool.DOCUMENT_LOADER,
        Tool.EMBEDDINGS,
        Tool.VECTOR_SEARCH,
        Tool.FILE_READER,
        Tool.TEXT_ANALYZER,
    ],
    UseCase.KNOWLEDGE_GRAPH: [
        Tool.KG_QUERY,
        Tool.KG_INGEST,
        Tool.ENTITY_EXTRACTOR,
        Tool.DOCUMENT_LOADER,
        Tool.FILE_READER,
    ],
    UseCase.MULTI_AGENT: [
        Tool.AGENT_ROUTER,
        Tool.MEMORY,
        Tool.TEXT_ANALYZER,
        Tool.FILE_READER,
        Tool.FILE_WRITER,
    ],
    UseCase.CHATBOT: [
        Tool.MEMORY,
        Tool.TEXT_ANALYZER,
        Tool.WEB_SEARCH,
        Tool.API_CALLER,
    ],
    UseCase.DATA_PIPELINE: [
        Tool.CSV_PROCESSOR,
        Tool.JSON_PROCESSOR,
        Tool.DATABASE_TOOL,
        Tool.FILE_READER,
        Tool.FILE_WRITER,
    ],
    UseCase.CODE_ASSISTANT: [
        Tool.CODE_EXECUTOR,
        Tool.CODE_ANALYZER,
        Tool.GIT_TOOL,
        Tool.FILE_READER,
        Tool.FILE_WRITER,
    ],
    UseCase.PR_REVIEWER: [
        Tool.BITBUCKET_MCP,
        Tool.MEMORY,
    ],
    UseCase.ONBOARD: [
        Tool.CODE_ANALYZER,
        Tool.FILE_READER,
    ],
    UseCase.SCRUM_MASTER: [
        Tool.JIRA_MCP,
        Tool.CONFLUENCE_MCP,
        Tool.BITBUCKET_MCP,
        Tool.MEMORY,
    ],
}


@dataclass
class TemplateConfig:
    """Configuration for project template generation."""
    
    name: str
    framework: Framework
    use_case: UseCase
    tools: list[Tool] = field(default_factory=list)
    include_tests: bool = True
    include_examples: bool = True
    include_docker: bool = False
    include_a2a: bool = False  # A2A protocol support for multi-agent
    include_kg_mcp: bool = False  # KG MCP server for knowledge-graph use case
    include_jira_mcp: bool = False  # Jira MCP add-on for pr-reviewer
    include_bitbucket_mcp: bool = True  # Bitbucket MCP (mandatory for pr-reviewer)
    kg_workspace: Optional[str] = None  # Connect to existing dva kg workspace
    domain_name: Optional[str] = None  # Domain slug for auto-wiring context
    google_project_id: Optional[str] = None
    google_location: str = "us-central1"
    bitbucket_mcp_url: str = "http://localhost:8126/sse"  # Bitbucket MCP SSE endpoint
    jira_mcp_url: str = "http://localhost:8128/sse"  # Jira MCP SSE endpoint
    poll_interval: int = 60  # PR polling interval in seconds
    
    def __post_init__(self):
        """Auto-populate tools based on use case if not provided."""
        if not self.tools:
            self.tools = USE_CASE_TOOLS.get(self.use_case, [])
    
    @property
    def extra_tools(self) -> list[Tool]:
        """Get tools beyond the default use case tools."""
        default_tools = USE_CASE_TOOLS.get(self.use_case, [])
        return [t for t in self.tools if t not in default_tools]
    
    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the configuration."""
        if tool not in self.tools:
            self.tools.append(tool)
    
    def remove_tool(self, tool: Tool) -> None:
        """Remove a tool from the configuration."""
        if tool in self.tools:
            self.tools.remove(tool)
    
    @property
    def dependencies(self) -> list[str]:
        """Get Python dependencies based on tools and framework."""
        deps = ["typer>=0.12.0", "rich>=13.7.0", "pydantic>=2.0.0"]
        
        # Framework-specific dependencies
        if self.framework == Framework.ADK:
            deps.extend([
                "google-adk>=0.1.0",
                "google-cloud-aiplatform>=1.38.0",
            ])
        elif self.framework == Framework.LANGGRAPH:
            deps.extend([
                "langgraph>=0.0.40",
                "langchain>=0.1.0",
                "langchain-google-genai>=0.0.6",
            ])
        
        # Tool-specific dependencies
        tool_deps = {
            Tool.VECTOR_SEARCH: ["chromadb>=0.4.0", "sentence-transformers>=2.2.0"],
            Tool.DOCUMENT_LOADER: ["PyPDF2>=3.0.0", "python-docx>=0.8.11"],
            Tool.EMBEDDINGS: ["google-cloud-aiplatform>=1.38.0"],
            Tool.KG_QUERY: ["neo4j>=5.14.0"],
            Tool.KG_INGEST: ["neo4j>=5.14.0"],
            Tool.ENTITY_EXTRACTOR: ["google-cloud-aiplatform>=1.38.0"],
            Tool.WEB_SEARCH: ["httpx>=0.25.0"],
            Tool.WEB_SCRAPER: ["beautifulsoup4>=4.12.0", "httpx>=0.25.0"],
            Tool.DATABASE_TOOL: ["sqlalchemy>=2.0.0"],
            Tool.GIT_TOOL: ["gitpython>=3.1.40"],
            Tool.CODE_EXECUTOR: ["docker>=6.1.0"],
        }
        
        for tool in self.tools:
            if tool in tool_deps:
                deps.extend(tool_deps[tool])
        
        # A2A protocol dependencies
        if self.include_a2a:
            deps.extend([
                "fastapi>=0.109.0",
                "uvicorn>=0.27.0",
                "httpx>=0.25.0",
                "sse-starlette>=1.8.0",
            ])
        
        # KG MCP server dependencies
        if self.include_kg_mcp:
            deps.extend([
                "mcp>=1.0.0",
                "neo4j>=5.14.0",
                "httpx>=0.25.0",
            ])
        
        # Onboard agent dependencies
        if self.use_case == UseCase.ONBOARD:
            deps.extend([
                "agentic-cli[agent]",
            ])
        
        # Scrum Master dependencies
        if self.use_case == UseCase.SCRUM_MASTER:
            deps.extend([
                "mcp>=1.0.0",
                "httpx>=0.25.0",
                "google-generativeai>=0.4.0",
            ])

        # PR Reviewer / MCP integration dependencies
        if self.use_case == UseCase.PR_REVIEWER or Tool.BITBUCKET_MCP in self.tools:
            deps.extend([
                "mcp>=1.0.0",
                "httpx>=0.25.0",
                "google-generativeai>=0.4.0",
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_deps = []
        for dep in deps:
            base = dep.split(">=")[0].split("[")[0]
            if base not in seen:
                seen.add(base)
                unique_deps.append(dep)
        
        return unique_deps
