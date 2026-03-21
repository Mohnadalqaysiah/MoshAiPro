"""
Mosh AI Pro v5 - Chat API with Auth & Usage Limits
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.user import User, PlanType
from app.services.chat_agent import trading_agent
from app.services.auth_service import get_current_user, check_subscription, deduct_trial

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


@router.post("/message")
async def chat_message(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """إرسال رسالة للوكيل مع فحص الصلاحية"""
    # Check subscription / trial
    status = check_subscription(user, db)
    if not status["allowed"]:
        raise HTTPException(status_code=403, detail=status["reason"])

    # Check trial chat credits specifically
    if user.plan == PlanType.TRIAL and user.trial_chat_left <= 0:
        raise HTTPException(
            status_code=403,
            detail=f"استهلكت رسائل المحادثة التجريبية. اشترك للمتابعة."
        )

    session_id = req.session_id or str(uuid.uuid4())
    try:
        response = await trading_agent.chat(session_id, req.message)

        # Deduct trial credit
        if user.plan == PlanType.TRIAL:
            deduct_trial(user, db, kind="chat")
        else:
            user.chat_total += 1
            user.chat_used_today += 1
            db.commit()

        return {
            "success": True,
            "session_id": session_id,
            "response": response,
            "credits_left": user.trial_chat_left if user.plan == PlanType.TRIAL else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def new_session(user: User = Depends(get_current_user)):
    """إنشاء جلسة محادثة جديدة"""
    sid = str(uuid.uuid4())
    return {"session_id": sid}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str, user: User = Depends(get_current_user)):
    """مسح تاريخ المحادثة"""
    if session_id in trading_agent.sessions:
        del trading_agent.sessions[session_id]
    return {"success": True, "message": "تم مسح المحادثة"}


@router.get("/session/{session_id}/history")
async def get_history(session_id: str, user: User = Depends(get_current_user)):
    """جلب تاريخ المحادثة"""
    history = trading_agent.sessions.get(session_id, [])
    return {"session_id": session_id, "messages": history}
