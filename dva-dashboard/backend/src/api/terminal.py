"""Terminal API routes — WebSocket for PTY I/O, REST for session management."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.services.terminal_service import (
    create_session,
    list_sessions,
    get_session,
    kill_session,
    resize_session,
    write_to_pty,
    read_from_pty,
    cleanup_dead_sessions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


class CreateTerminalRequest(BaseModel):
    cols: int = 120
    rows: int = 30
    title: str = "Terminal"


class TerminalSessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    cols: int
    rows: int
    alive: bool


class ResizeRequest(BaseModel):
    cols: int
    rows: int


@router.post("/sessions", response_model=TerminalSessionResponse)
async def api_create_session(req: CreateTerminalRequest):
    """Create a new terminal session."""
    try:
        session = create_session(cols=req.cols, rows=req.rows, title=req.title)
        return TerminalSessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            cols=session.cols,
            rows=session.rows,
            alive=True,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.get("/sessions", response_model=list[TerminalSessionResponse])
async def api_list_sessions():
    """List all terminal sessions."""
    cleanup_dead_sessions()
    return [TerminalSessionResponse(**s) for s in list_sessions()]


@router.delete("/sessions/{session_id}")
async def api_kill_session(session_id: str):
    """Kill a terminal session."""
    if kill_session(session_id):
        return {"success": True, "message": f"Session {session_id} terminated"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions/{session_id}/resize")
async def api_resize_session(session_id: str, req: ResizeRequest):
    """Resize a terminal session."""
    if resize_session(session_id, req.cols, req.rows):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Session not found")


@router.websocket("/sessions/{session_id}/ws")
async def terminal_ws(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for bidirectional PTY I/O.

    Client sends:
      - Binary frames: raw keystrokes forwarded to PTY stdin
      - Text frames (JSON): {"type": "resize", "cols": N, "rows": N}

    Server sends:
      - Binary frames: raw PTY output (terminal escape codes, text, etc.)
    """
    session = get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    logger.info("Terminal WebSocket connected: %s", session_id)

    async def read_pty_loop():
        """Read PTY output and send to WebSocket."""
        try:
            while True:
                data = read_from_pty(session_id)
                if data is None:
                    # Session died
                    try:
                        await websocket.send_text(json.dumps({"type": "exit"}))
                    except Exception:
                        pass
                    break
                if data:
                    await websocket.send_bytes(data)
                else:
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.debug("PTY read loop ended: %s", e)

    async def write_pty_loop():
        """Read WebSocket messages and write to PTY."""
        try:
            while True:
                msg = await websocket.receive()

                if msg.get("type") == "websocket.disconnect":
                    break

                if "bytes" in msg and msg["bytes"]:
                    write_to_pty(session_id, msg["bytes"])
                elif "text" in msg and msg["text"]:
                    try:
                        payload = json.loads(msg["text"])
                        if payload.get("type") == "resize":
                            resize_session(
                                session_id,
                                payload.get("cols", 120),
                                payload.get("rows", 30),
                            )
                        elif payload.get("type") == "input":
                            write_to_pty(session_id, payload["data"].encode("utf-8"))
                    except (json.JSONDecodeError, KeyError):
                        # Treat as raw text input
                        write_to_pty(session_id, msg["text"].encode("utf-8"))
        except WebSocketDisconnect:
            logger.info("Terminal WebSocket disconnected: %s", session_id)
        except Exception as e:
            logger.debug("PTY write loop ended: %s", e)

    # Run both loops concurrently
    read_task = asyncio.create_task(read_pty_loop())
    write_task = asyncio.create_task(write_pty_loop())

    try:
        done, pending = await asyncio.wait(
            [read_task, write_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        logger.info("Terminal WebSocket closed: %s", session_id)
