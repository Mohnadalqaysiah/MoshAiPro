"""
Mosh AI Pro v5 - Chat API
"""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger
from app.services.chat_agent import trading_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class NewSessionResponse(BaseModel):
    session_id: str


@router.post("/message")
async def chat_message(req: ChatRequest):
    """إرسال رسالة للوكيل وتلقي الرد"""
    session_id = req.session_id or str(uuid.uuid4())
    try:
        response = await trading_agent.chat(session_id, req.message)
        return {
            "success": True,
            "session_id": session_id,
            "response": response,
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def new_session():
    """إنشاء جلسة محادثة جديدة"""
    sid = str(uuid.uuid4())
    return {"session_id": sid}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """مسح تاريخ المحادثة"""
    if session_id in trading_agent.sessions:
        del trading_agent.sessions[session_id]
    return {"success": True, "message": "تم مسح المحادثة"}


@router.get("/session/{session_id}/history")
async def get_history(session_id: str):
    """جلب تاريخ المحادثة"""
    history = trading_agent.sessions.get(session_id, [])
    return {"session_id": session_id, "messages": history}
