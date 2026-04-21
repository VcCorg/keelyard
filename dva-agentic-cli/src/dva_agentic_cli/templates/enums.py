"""Enums for template system configuration."""

from enum import Enum


class Framework(str, Enum):
    """Supported agent frameworks."""
    
    ADK = "adk"
    LANGGRAPH = "langgraph"
    
    @classmethod
    def choices(cls) -> list[str]:
        return [e.value for e in cls]
    
    @property
    def display_name(self) -> str:
        names = {
            "adk": "Google ADK (Agent Development Kit)",
            "langgraph": "LangGraph",
        }
        return names.get(self.value, self.value)


class UseCase(str, Enum):
    """Supported use cases for agent projects."""
    
    BASIC = "basic"
    RAG = "rag"
    KNOWLEDGE_GRAPH = "knowledge-graph"
    MULTI_AGENT = "multi-agent"
    CHATBOT = "chatbot"
    DATA_PIPELINE = "data-pipeline"
    CODE_ASSISTANT = "code-assistant"
    PR_REVIEWER = "pr-reviewer"
    ONBOARD = "onboard"
    SCRUM_MASTER = "scrum-master"
    
    @classmethod
    def choices(cls) -> list[str]:
        return [e.value for e in cls]
    
    @property
    def display_name(self) -> str:
        names = {
            "basic": "Basic Agent",
            "rag": "RAG (Retrieval-Augmented Generation)",
            "knowledge-graph": "Knowledge Graph Agent",
            "multi-agent": "Multi-Agent System",
            "chatbot": "Conversational Chatbot",
            "data-pipeline": "Data Processing Pipeline",
            "code-assistant": "Code Assistant",
            "pr-reviewer": "PR Review Automation Agent",
            "onboard": "Onboard Agent (Skill Gap Detection)",
            "scrum-master": "Scrum Master Agent",
        }
        return names.get(self.value, self.value)
    
    @property
    def description(self) -> str:
        descriptions = {
            "basic": "Simple agent with basic tools for getting started",
            "rag": "Agent with document retrieval and vector search capabilities",
            "knowledge-graph": "Agent integrated with Neo4j knowledge graph",
            "multi-agent": "Orchestrated system with multiple specialized agents",
            "chatbot": "Conversational agent with memory and context management",
            "data-pipeline": "Agent for ETL and data processing workflows",
            "code-assistant": "Agent for code generation, review, and refactoring",
            "pr-reviewer": "Automated PR watcher with AI-powered code review, approval, and MCP integration",
            "onboard": "AI agent that detects skill gaps in onboarded projects and proposes new skills for the registry",
            "scrum-master": "Domain-scoped Scrum Master agent with Jira, Confluence, and Bitbucket MCP integration",
        }
        return descriptions.get(self.value, "")


class Tool(str, Enum):
    """Available tools that can be included in projects."""
    
    # Basic tools
    CALCULATOR = "calculator"
    TEXT_ANALYZER = "text_analyzer"
    FILE_READER = "file_reader"
    FILE_WRITER = "file_writer"
    
    # Web tools
    WEB_SEARCH = "web_search"
    WEB_SCRAPER = "web_scraper"
    API_CALLER = "api_caller"
    
    # RAG tools
    VECTOR_SEARCH = "vector_search"
    DOCUMENT_LOADER = "document_loader"
    EMBEDDINGS = "embeddings"
    
    # Knowledge Graph tools
    KG_QUERY = "kg_query"
    KG_INGEST = "kg_ingest"
    ENTITY_EXTRACTOR = "entity_extractor"
    
    # Code tools
    CODE_EXECUTOR = "code_executor"
    CODE_ANALYZER = "code_analyzer"
    GIT_TOOL = "git_tool"
    
    # Data tools
    CSV_PROCESSOR = "csv_processor"
    JSON_PROCESSOR = "json_processor"
    DATABASE_TOOL = "database_tool"
    
    # Communication tools
    MEMORY = "memory"
    AGENT_ROUTER = "agent_router"
    
    # MCP integration tools
    BITBUCKET_MCP = "bitbucket_mcp"
    JIRA_MCP = "jira_mcp"
    KG_MCP_TOOL = "kg_mcp_tool"
    CONFLUENCE_MCP = "confluence_mcp"
    
    @classmethod
    def choices(cls) -> list[str]:
        return [e.value for e in cls]
    
    @property
    def display_name(self) -> str:
        names = {
            "calculator": "Calculator",
            "text_analyzer": "Text Analyzer",
            "file_reader": "File Reader",
            "file_writer": "File Writer",
            "web_search": "Web Search",
            "web_scraper": "Web Scraper",
            "api_caller": "API Caller",
            "vector_search": "Vector Search",
            "document_loader": "Document Loader",
            "embeddings": "Embeddings Generator",
            "kg_query": "Knowledge Graph Query",
            "kg_ingest": "Knowledge Graph Ingest",
            "entity_extractor": "Entity Extractor",
            "code_executor": "Code Executor",
            "code_analyzer": "Code Analyzer",
            "git_tool": "Git Operations",
            "csv_processor": "CSV Processor",
            "json_processor": "JSON Processor",
            "database_tool": "Database Tool",
            "memory": "Conversation Memory",
            "agent_router": "Agent Router",
            "bitbucket_mcp": "Bitbucket MCP (PR operations)",
            "jira_mcp": "Jira MCP (issue tracking)",
            "kg_mcp_tool": "KG MCP (knowledge graph)",
            "confluence_mcp": "Confluence MCP (wiki operations)",
        }
        return names.get(self.value, self.value)
