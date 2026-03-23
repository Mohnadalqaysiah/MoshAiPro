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

    # حدود الرسائل اليومية حسب الخطة
    DAILY_CHAT_LIMITS = {
        PlanType.TRIAL:   0,    # يستخدم trial_chat_left
        PlanType.WEEKLY:  50,   # 50 رسالة/يوم
        PlanType.MONTHLY: 200,  # 200 رسالة/يوم
    }

    if user.plan == PlanType.TRIAL and user.trial_chat_left <= 0:
        raise HTTPException(
            status_code=403,
            detail="استهلكت رسائل المحادثة التجريبية. اشترك للمتابعة."
        )

    if user.plan in (PlanType.WEEKLY, PlanType.MONTHLY):
        daily_limit = DAILY_CHAT_LIMITS[user.plan]
        if user.chat_used_today >= daily_limit:
            raise HTTPException(
                status_code=403,
                detail=f"وصلت للحد اليومي ({daily_limit} رسالة). يتجدد غداً."
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

        DAILY_LIMITS = {PlanType.WEEKLY: 50, PlanType.MONTHLY: 200}
        if user.plan == PlanType.TRIAL:
            credits_left = user.trial_chat_left
        elif user.plan in DAILY_LIMITS:
            credits_left = max(0, DAILY_LIMITS[user.plan] - user.chat_used_today)
        else:
            credits_left = None

        return {
            "success": True,
            "session_id": session_id,
            "response": response,
            "credits_left": credits_left,
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
