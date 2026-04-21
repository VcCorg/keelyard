"""Generate A2A (Agent-to-Agent) protocol files."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig


A2A_MODELS = '''"""A2A Protocol Models - Based on Google A2A Specification."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Task lifecycle states."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class AgentCapability(BaseModel):
    """Describes a capability of an agent."""
    id: str
    name: str
    description: Optional[str] = None


class AgentSkill(BaseModel):
    """Describes a skill an agent can perform."""
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    input_modes: List[str] = Field(default_factory=lambda: ["text"])
    output_modes: List[str] = Field(default_factory=lambda: ["text"])


class AgentProvider(BaseModel):
    """Information about the agent provider."""
    organization: str
    url: Optional[str] = None


class AgentCard(BaseModel):
    """
    Agent Card - JSON metadata describing agent capabilities.
    Served at /.well-known/agent.json
    """
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocol_version: str = "0.1"
    capabilities: List[AgentCapability] = Field(default_factory=list)
    skills: List[AgentSkill] = Field(default_factory=list)
    provider: Optional[AgentProvider] = None
    documentation_url: Optional[str] = None
    default_input_modes: List[str] = Field(default_factory=lambda: ["text"])
    default_output_modes: List[str] = Field(default_factory=lambda: ["text"])


class Message(BaseModel):
    """A message in a task conversation."""
    role: str  # "user" or "agent"
    parts: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Artifact(BaseModel):
    """An artifact produced by a task."""
    id: str
    name: str
    mime_type: str
    parts: List[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Task(BaseModel):
    """A task submitted to an agent."""
    id: str
    session_id: Optional[str] = None
    state: TaskState = TaskState.SUBMITTED
    messages: List[Message] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskSendParams(BaseModel):
    """Parameters for sending a task."""
    id: str
    session_id: Optional[str] = None
    message: Message
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusUpdateEvent(BaseModel):
    """Event for task status updates (SSE)."""
    task_id: str
    state: TaskState
    message: Optional[Message] = None
    artifact: Optional[Artifact] = None
    final: bool = False
'''


A2A_SERVER = '''"""A2A Protocol Server - FastAPI implementation."""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .models import (
    AgentCard,
    AgentCapability,
    AgentSkill,
    AgentProvider,
    Task,
    TaskState,
    TaskSendParams,
    TaskStatusUpdateEvent,
    Message,
    Artifact,
)

# In-memory task storage (replace with persistent storage in production)
tasks: Dict[str, Task] = {}
task_queues: Dict[str, asyncio.Queue] = {}


def create_a2a_app(
    agent_name: str,
    agent_description: str,
    agent_url: str,
    skills: list[AgentSkill] = None,
    process_message_fn=None,
) -> FastAPI:
    """
    Create a FastAPI app with A2A protocol endpoints.
    
    Args:
        agent_name: Name of the agent
        agent_description: Description of the agent
        agent_url: Base URL where agent is hosted
        skills: List of agent skills
        process_message_fn: Async function to process messages
            Signature: async def process(task: Task, message: Message) -> AsyncGenerator[TaskStatusUpdateEvent, None]
    """
    app = FastAPI(title=f"{agent_name} - A2A Agent")
    
    # Build agent card
    agent_card = AgentCard(
        name=agent_name,
        description=agent_description,
        url=agent_url,
        skills=skills or [],
        capabilities=[
            AgentCapability(id="streaming", name="Streaming", description="Supports SSE streaming"),
            AgentCapability(id="tasks", name="Task Management", description="Supports task lifecycle"),
        ],
    )
    
    @app.get("/.well-known/agent.json")
    async def get_agent_card() -> AgentCard:
        """Return the agent card (A2A discovery endpoint)."""
        return agent_card
    
    @app.post("/tasks/send")
    async def send_task(params: TaskSendParams) -> Task:
        """
        Send a task to the agent.
        Creates a new task or adds to existing session.
        """
        task_id = params.id or str(uuid.uuid4())
        
        if task_id in tasks:
            task = tasks[task_id]
            task.messages.append(params.message)
            task.updated_at = datetime.utcnow()
        else:
            task = Task(
                id=task_id,
                session_id=params.session_id,
                state=TaskState.SUBMITTED,
                messages=[params.message],
                metadata=params.metadata,
            )
            tasks[task_id] = task
            task_queues[task_id] = asyncio.Queue()
        
        # Start processing in background
        if process_message_fn:
            asyncio.create_task(_process_task(task, params.message, process_message_fn))
        
        return task
    
    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str) -> Task:
        """Get task status and history."""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return tasks[task_id]
    
    @app.post("/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> Task:
        """Cancel a running task."""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = tasks[task_id]
        if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
            raise HTTPException(status_code=400, detail=f"Task already in terminal state: {task.state}")
        
        task.state = TaskState.CANCELED
        task.updated_at = datetime.utcnow()
        
        # Notify subscribers
        if task_id in task_queues:
            await task_queues[task_id].put(
                TaskStatusUpdateEvent(task_id=task_id, state=TaskState.CANCELED, final=True)
            )
        
        return task
    
    @app.get("/tasks/{task_id}/stream")
    async def stream_task(task_id: str, request: Request):
        """Stream task updates via SSE."""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        async def event_generator() -> AsyncGenerator[dict, None]:
            queue = task_queues.get(task_id)
            if not queue:
                queue = asyncio.Queue()
                task_queues[task_id] = queue
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "update", "data": event.model_dump_json()}
                    
                    if event.final:
                        break
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        
        return EventSourceResponse(event_generator())
    
    async def _process_task(task: Task, message: Message, process_fn):
        """Process a task message and emit updates."""
        task.state = TaskState.WORKING
        task.updated_at = datetime.utcnow()
        
        queue = task_queues.get(task.id)
        if queue:
            await queue.put(TaskStatusUpdateEvent(task_id=task.id, state=TaskState.WORKING))
        
        try:
            async for event in process_fn(task, message):
                if event.message:
                    task.messages.append(event.message)
                if event.artifact:
                    task.artifacts.append(event.artifact)
                task.updated_at = datetime.utcnow()
                
                if queue:
                    await queue.put(event)
                
                if event.final:
                    task.state = event.state
                    break
            
            if task.state == TaskState.WORKING:
                task.state = TaskState.COMPLETED
                if queue:
                    await queue.put(
                        TaskStatusUpdateEvent(task_id=task.id, state=TaskState.COMPLETED, final=True)
                    )
        except Exception as e:
            task.state = TaskState.FAILED
            task.metadata["error"] = str(e)
            if queue:
                await queue.put(
                    TaskStatusUpdateEvent(task_id=task.id, state=TaskState.FAILED, final=True)
                )
    
    return app
'''


A2A_CLIENT = '''"""A2A Protocol Client - For discovering and communicating with A2A agents."""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from .models import AgentCard, Task, TaskSendParams, TaskStatusUpdateEvent, Message


class A2AClient:
    """
    Client for communicating with A2A-compliant agents.
    
    Usage:
        client = A2AClient("http://localhost:8000")
        
        # Discover agent capabilities
        card = await client.get_agent_card()
        print(f"Agent: {card.name}")
        print(f"Skills: {[s.name for s in card.skills]}")
        
        # Send a task
        task = await client.send_task("Hello, agent!")
        
        # Stream responses
        async for event in client.stream_task(task.id):
            print(f"State: {event.state}")
            if event.message:
                print(f"Response: {event.message.parts}")
    """
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def get_agent_card(self) -> AgentCard:
        """Fetch the agent card from /.well-known/agent.json"""
        response = await self._client.get(f"{self.base_url}/.well-known/agent.json")
        response.raise_for_status()
        return AgentCard(**response.json())
    
    async def send_task(
        self,
        message: str,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Send a task to the agent.
        
        Args:
            message: The message to send
            task_id: Optional task ID (for continuing a conversation)
            session_id: Optional session ID
            metadata: Optional metadata
        
        Returns:
            The created/updated task
        """
        import uuid
        
        params = TaskSendParams(
            id=task_id or str(uuid.uuid4()),
            session_id=session_id,
            message=Message(role="user", parts=[{"type": "text", "text": message}]),
            metadata=metadata or {},
        )
        
        response = await self._client.post(
            f"{self.base_url}/tasks/send",
            json=params.model_dump(mode="json"),
        )
        response.raise_for_status()
        return Task(**response.json())
    
    async def get_task(self, task_id: str) -> Task:
        """Get task status and history."""
        response = await self._client.get(f"{self.base_url}/tasks/{task_id}")
        response.raise_for_status()
        return Task(**response.json())
    
    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a running task."""
        response = await self._client.post(f"{self.base_url}/tasks/{task_id}/cancel")
        response.raise_for_status()
        return Task(**response.json())
    
    async def stream_task(self, task_id: str) -> AsyncGenerator[TaskStatusUpdateEvent, None]:
        """
        Stream task updates via SSE.
        
        Yields TaskStatusUpdateEvent objects as they arrive.
        """
        async with self._client.stream(
            "GET",
            f"{self.base_url}/tasks/{task_id}/stream",
            timeout=None,
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data and data != "":
                        try:
                            event = TaskStatusUpdateEvent(**json.loads(data))
                            yield event
                            if event.final:
                                break
                        except json.JSONDecodeError:
                            continue
    
    async def send_and_wait(
        self,
        message: str,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Task:
        """
        Send a task and wait for completion.
        
        Returns the final task state with all messages and artifacts.
        """
        task = await self.send_task(message, task_id, session_id)
        
        async for event in self.stream_task(task.id):
            if event.final:
                break
        
        return await self.get_task(task.id)


async def discover_agent(url: str) -> AgentCard:
    """
    Discover an agent's capabilities.
    
    Args:
        url: Base URL of the agent
    
    Returns:
        The agent's AgentCard
    """
    async with A2AClient(url) as client:
        return await client.get_agent_card()
'''


A2A_INIT = '''"""A2A Protocol Support for Multi-Agent Systems."""

from .models import (
    AgentCard,
    AgentCapability,
    AgentSkill,
    AgentProvider,
    Task,
    TaskState,
    TaskSendParams,
    TaskStatusUpdateEvent,
    Message,
    Artifact,
)
from .server import create_a2a_app
from .client import A2AClient, discover_agent

__all__ = [
    # Models
    "AgentCard",
    "AgentCapability", 
    "AgentSkill",
    "AgentProvider",
    "Task",
    "TaskState",
    "TaskSendParams",
    "TaskStatusUpdateEvent",
    "Message",
    "Artifact",
    # Server
    "create_a2a_app",
    # Client
    "A2AClient",
    "discover_agent",
]
'''


A2A_EXAMPLE = '''"""Example: Running an A2A-compliant agent server."""

import asyncio
from typing import AsyncGenerator

import uvicorn

from a2a import (
    create_a2a_app,
    AgentSkill,
    Task,
    TaskState,
    TaskStatusUpdateEvent,
    Message,
)


async def process_message(task: Task, message: Message) -> AsyncGenerator[TaskStatusUpdateEvent, None]:
    """
    Process incoming messages and yield status updates.
    
    This is where you implement your agent's logic.
    """
    # Extract text from message
    text = ""
    for part in message.parts:
        if part.get("type") == "text":
            text = part.get("text", "")
            break
    
    # Simulate processing
    yield TaskStatusUpdateEvent(
        task_id=task.id,
        state=TaskState.WORKING,
        message=Message(role="agent", parts=[{"type": "text", "text": f"Processing: {text}"}]),
    )
    
    await asyncio.sleep(1)  # Simulate work
    
    # Return final response
    yield TaskStatusUpdateEvent(
        task_id=task.id,
        state=TaskState.COMPLETED,
        message=Message(role="agent", parts=[{"type": "text", "text": f"Completed processing: {text}"}]),
        final=True,
    )


# Define agent skills
skills = [
    AgentSkill(
        id="chat",
        name="Chat",
        description="General conversation and Q&A",
        tags=["conversation", "qa"],
        examples=["Hello!", "What can you do?"],
    ),
    AgentSkill(
        id="analyze",
        name="Analyze",
        description="Analyze text and provide insights",
        tags=["analysis", "text"],
        examples=["Analyze this document", "What are the key points?"],
    ),
]

# Create the A2A app
app = create_a2a_app(
    agent_name="Example Agent",
    agent_description="An example A2A-compliant agent",
    agent_url="http://localhost:8000",
    skills=skills,
    process_message_fn=process_message,
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''


def generate_a2a_files(project_dir: Path, config: TemplateConfig) -> None:
    """Generate A2A protocol files for multi-agent projects."""
    if not config.include_a2a:
        return
    
    # Create a2a directory
    a2a_dir = project_dir / "src" / "a2a"
    a2a_dir.mkdir(parents=True, exist_ok=True)
    
    # Write A2A files
    (a2a_dir / "__init__.py").write_text(A2A_INIT)
    (a2a_dir / "models.py").write_text(A2A_MODELS)
    (a2a_dir / "server.py").write_text(A2A_SERVER)
    (a2a_dir / "client.py").write_text(A2A_CLIENT)
    
    # Write example
    examples_dir = project_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    (examples_dir / "a2a_server_example.py").write_text(A2A_EXAMPLE)
