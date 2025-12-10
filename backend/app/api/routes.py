from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.state.models import RentalSession
from app.agents.planner import RentalAgent
import uuid
import structlog
import json
from typing import Dict

router = APIRouter()
logger = structlog.get_logger()

# In-memory session storage for MVP
sessions: Dict[str, RentalSession] = {}

class CreateSessionRequest(json.JSONDecoder): # Pydantic model needed here usually
    pass 
# Wait, just use dict or simple endpoint
from pydantic import BaseModel
class SessionCreate(BaseModel):
    user_id: str | None = None

@router.post("/sessions")
async def create_session(request: SessionCreate):
    session = RentalSession()
    sessions[session.session_id] = session
    return {"session_id": session.session_id}

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")
    
    session = sessions.get(session_id)
    if not session:
        # Create ad-hoc if missing (dev convenience)
        session = RentalSession(session_id=session_id)
        sessions[session_id] = session
    
    agent = RentalAgent()

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                user_content = data.get("content")
                
                # Notify "thinking"
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                
                # Run Agent Turn
                response = await agent.run_turn(session, user_content)
                
                # Send Tool Calls/Results separate or inside response
                if "tool_calls" in response:
                     for tc in response["tool_calls"]:
                         await websocket.send_json({
                             "type": "tool_call", 
                             "tool_name": tc.get("name"), 
                             "arguments": tc.get("arguments")
                         })
                
                if "tool_results" in response:
                    for tr in response["tool_results"]:
                        await websocket.send_json({
                            "type": "tool_result",
                            "tool_name": tr.get("name"),
                            "result": tr.get("result")
                        })
                
                # Send Final Response
                await websocket.send_json({
                    "type": "message",
                    "role": "assistant",
                    "content": response.get("content")
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
