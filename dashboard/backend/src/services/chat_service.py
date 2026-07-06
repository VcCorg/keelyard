"""Chat service — manages ADK Agent sessions with MCP tool integration.

Uses Google ADK AgentRunner with MCPToolset to provide interactive
chat backed by MCP servers (Bitbucket, Jira, KG, Memory, etc.).
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # user, agent
    content: str
    timestamp: str = ""
    tool_calls: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ChatSession:
    """An active chat session with an agent."""
    id: str
    agent_name: str
    user_id: str = "dashboard-user"
    created_at: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    mcp_toolsets: list[MCPToolset] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# In-memory session store
_sessions: dict[str, ChatSession] = {}
_session_service = InMemorySessionService()

# Default MCP servers to connect to for chat
DEFAULT_MCP_SERVERS = {
    "bitbucket": "http://localhost:8126/sse",
    "glean": "http://localhost:8127/sse",
    "jira": "http://localhost:8128/sse",
    "confluence": "http://localhost:8129/sse",
    "memory": "http://localhost:8130/sse",
    "kg": "http://localhost:8131/sse",
}

# Default model
DEFAULT_MODEL = "gemini-2.5-flash"

DEFAULT_INSTRUCTION = """You are a helpful KEEL platform assistant with access to various tools.
You can search Bitbucket PRs, query Jira issues, search Confluence docs,
access the knowledge graph, and use memory for context.
Be concise and helpful. When using tools, explain what you're doing."""


async def _get_available_mcp_tools(
    server_urls: Optional[dict[str, str]] = None,
) -> tuple[list, list[MCPToolset]]:
    """Connect to MCP servers and gather available tools.

    Returns (tools_list, toolset_instances) so we can close toolsets later.
    """
    urls = server_urls or DEFAULT_MCP_SERVERS
    all_tools = []
    toolsets = []

    for name, url in urls.items():
        try:
            toolset = MCPToolset(
                connection_params=SseServerParams(url=url, timeout=5),
            )
            tools = await toolset.get_tools()
            if tools:
                all_tools.extend(tools)
                toolsets.append(toolset)
                logger.info(f"Connected to {name} MCP: {len(tools)} tools")
            else:
                logger.warning(f"No tools from {name} MCP at {url}")
        except Exception as e:
            logger.warning(f"Failed to connect to {name} MCP at {url}: {e}")

    return all_tools, toolsets


async def create_session(
    agent_name: str = "keel-assistant",
    mcp_servers: Optional[dict[str, str]] = None,
) -> ChatSession:
    """Create a new chat session with an ADK agent."""
    session_id = str(uuid.uuid4())[:8]

    session = ChatSession(
        id=session_id,
        agent_name=agent_name,
    )

    # Create ADK session
    await _session_service.create_session(
        app_name=agent_name,
        user_id=session.user_id,
        session_id=session_id,
    )

    _sessions[session_id] = session
    logger.info(f"Created chat session {session_id} for agent {agent_name}")
    return session


def get_session(session_id: str) -> Optional[ChatSession]:
    """Get an existing chat session."""
    return _sessions.get(session_id)


def list_sessions() -> list[dict]:
    """List all active sessions."""
    return [
        {
            "id": s.id,
            "agent_name": s.agent_name,
            "created_at": s.created_at,
            "message_count": len(s.messages),
        }
        for s in _sessions.values()
    ]


async def delete_session(session_id: str) -> bool:
    """Delete a chat session and clean up MCP connections."""
    session = _sessions.pop(session_id, None)
    if not session:
        return False

    for toolset in session.mcp_toolsets:
        try:
            await toolset.close()
        except Exception:
            pass

    logger.info(f"Deleted chat session {session_id}")
    return True


@dataclass
class ChatEvent:
    """Streamed chat event for the WebSocket."""
    type: str  # thinking_start, tool_call, tool_result, thinking_end, agent_response, agent_response_end, error
    data: dict = field(default_factory=dict)


async def send_message(
    session_id: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    instruction: str = DEFAULT_INSTRUCTION,
    mcp_servers: Optional[dict[str, str]] = None,
) -> AsyncGenerator[ChatEvent, None]:
    """Send a message and stream back events (tool calls, responses, etc.).

    Yields ChatEvent objects that the WebSocket handler sends to the client.
    """
    session = _sessions.get(session_id)
    if not session:
        yield ChatEvent(type="error", data={"message": f"Session {session_id} not found"})
        return

    # Record user message
    session.messages.append(ChatMessage(role="user", content=user_message))

    # Connect to MCP servers and get tools
    yield ChatEvent(type="thinking_start")

    tools, toolsets = await _get_available_mcp_tools(mcp_servers)
    session.mcp_toolsets = toolsets

    if not tools:
        logger.warning("No MCP tools available, agent will run without tools")

    # Create ADK agent with MCP tools
    agent = Agent(
        name=session.agent_name,
        model=model,
        instruction=instruction,
        tools=tools,
    )

    runner = Runner(
        agent=agent,
        app_name=session.agent_name,
        session_service=_session_service,
    )

    # Build the user content
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    # Run agent and stream events
    collected_text = []
    tool_calls_in_turn = []

    try:
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            # Check for function calls in the content
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Tool call (function_call)
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_call_data = {
                            "tool": fc.name,
                            "args": dict(fc.args) if fc.args else {},
                        }
                        tool_calls_in_turn.append(tool_call_data)
                        yield ChatEvent(type="tool_call", data=tool_call_data)

                    # Tool result (function_response)
                    elif hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        result_str = str(fr.response) if fr.response else ""
                        # Truncate very long results
                        if len(result_str) > 2000:
                            result_str = result_str[:2000] + "... (truncated)"
                        yield ChatEvent(
                            type="tool_result",
                            data={"tool": fr.name, "result": result_str},
                        )

                    # Text response
                    elif hasattr(part, "text") and part.text:
                        collected_text.append(part.text)
                        yield ChatEvent(
                            type="agent_response",
                            data={"content": part.text, "partial": bool(event.partial)},
                        )

            # Check for errors
            if event.error_message:
                yield ChatEvent(type="error", data={"message": event.error_message})

    except Exception as e:
        logger.error(f"Agent error in session {session_id}: {e}")
        yield ChatEvent(type="error", data={"message": str(e)})

    yield ChatEvent(type="thinking_end")
    yield ChatEvent(type="agent_response_end")

    # Record agent response
    full_response = "".join(collected_text)
    if full_response:
        session.messages.append(ChatMessage(
            role="agent",
            content=full_response,
            tool_calls=tool_calls_in_turn,
        ))

    # Clean up MCP toolsets after each turn
    for toolset in toolsets:
        try:
            await toolset.close()
        except Exception:
            pass
    session.mcp_toolsets = []


def get_session_history(session_id: str) -> list[dict]:
    """Get message history for a session."""
    session = _sessions.get(session_id)
    if not session:
        return []
    return [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp,
            "tool_calls": m.tool_calls,
        }
        for m in session.messages
    ]
