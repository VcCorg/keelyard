"""Chat API routes — WebSocket for streaming, REST for session management."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.services.chat_service import (
    ChatEvent,
    create_session,
    delete_session,
    get_session,
    get_session_history,
    list_sessions,
    send_message,
    DEFAULT_MCP_SERVERS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    agent_name: str = "keel-assistant"
    mcp_servers: Optional[dict[str, str]] = None


class CreateSessionResponse(BaseModel):
    id: str
    agent_name: str
    created_at: str


class SessionSummary(BaseModel):
    id: str
    agent_name: str
    created_at: str
    message_count: int


class MessageHistoryItem(BaseModel):
    role: str
    content: str
    timestamp: str
    tool_calls: list[dict] = []


# --- REST endpoints for session management ---

@router.post("/sessions", response_model=CreateSessionResponse)
async def api_create_session(req: CreateSessionRequest):
    """Create a new chat session."""
    session = await create_session(
        agent_name=req.agent_name,
        mcp_servers=req.mcp_servers,
    )
    return CreateSessionResponse(
        id=session.id,
        agent_name=session.agent_name,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def api_list_sessions():
    """List all active chat sessions."""
    return list_sessions()


@router.delete("/sessions/{session_id}")
async def api_delete_session(session_id: str):
    """Delete a chat session."""
    success = await delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"success": True, "message": f"Session '{session_id}' deleted"}


@router.get("/sessions/{session_id}/history", response_model=list[MessageHistoryItem])
async def api_session_history(session_id: str):
    """Get message history for a session."""
    history = get_session_history(session_id)
    if not history and not get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return history


# --- WebSocket for streaming chat ---

@router.websocket("/{session_id}/stream")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for streaming chat with an agent.

    Client sends: {"type": "user_message", "content": "..."}
    Server sends (in order):
      {"type": "thinking_start"}
      {"type": "tool_call", "data": {"tool": "...", "args": {...}}}
      {"type": "tool_result", "data": {"tool": "...", "result": "..."}}
      {"type": "thinking_end"}
      {"type": "agent_response", "data": {"content": "...", "partial": true/false}}
      {"type": "agent_response_end"}
    """
    session = get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason=f"Session '{session_id}' not found")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        while True:
            # Wait for a message from the client
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": {"message": "Invalid JSON"}})
                continue

            msg_type = msg.get("type")
            if msg_type != "user_message":
                await websocket.send_json({"type": "error", "data": {"message": f"Unknown type: {msg_type}"}})
                continue

            content = msg.get("content", "").strip()
            if not content:
                await websocket.send_json({"type": "error", "data": {"message": "Empty message"}})
                continue

            # Stream agent response events
            try:
                async for event in send_message(
                    session_id=session_id,
                    user_message=content,
                ):
                    await websocket.send_json({
                        "type": event.type,
                        "data": event.data,
                    })
            except Exception as e:
                logger.error(f"Error in chat session {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)},
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
