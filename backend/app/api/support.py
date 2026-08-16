"""
Mosh AI Pro v5 - Support Chat API (in-house live chat, user <-> admin)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.models.support_chat import SupportChatThread, SupportChatMessage, ChatThreadStatus
from app.services.auth_service import get_current_user, get_admin_user

router = APIRouter()


def _get_or_create_thread(user: User, db: Session) -> SupportChatThread:
    thread = db.query(SupportChatThread).filter(SupportChatThread.user_id == user.id).first()
    if not thread:
        thread = SupportChatThread(user_id=user.id)
        db.add(thread)
        db.commit()
        db.refresh(thread)
    return thread


def _thread_out(t: SupportChatThread) -> dict:
    return {
        "id":               t.id,
        "status":           t.status.value if hasattr(t.status, "value") else t.status,
        "unread_for_admin": t.unread_for_admin,
        "unread_for_user":  t.unread_for_user,
        "last_message_at":  t.last_message_at.isoformat() if t.last_message_at else None,
        "created_at":       t.created_at.isoformat() if t.created_at else None,
    }


def _msg_out(m: SupportChatMessage) -> dict:
    return {
        "id":          m.id,
        "thread_id":   m.thread_id,
        "sender_role": m.sender_role,
        "sender_id":   m.sender_id,
        "body":        m.body,
        "created_at":  m.created_at.isoformat() if m.created_at else None,
    }


class MessageIn(BaseModel):
    body: str


class StatusIn(BaseModel):
    status: str


# ═══════════════════════════ User-side ═══════════════════════════

@router.get("/thread")
async def get_my_thread(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = _get_or_create_thread(user, db)
    return _thread_out(thread)


@router.get("/messages")
async def get_my_messages(
    after_id: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = _get_or_create_thread(user, db)
    msgs = (
        db.query(SupportChatMessage)
        .filter(SupportChatMessage.thread_id == thread.id, SupportChatMessage.id > after_id)
        .order_by(SupportChatMessage.id.asc())
        .all()
    )
    if thread.unread_for_user > 0:
        thread.unread_for_user = 0
        db.commit()
    return {"thread": _thread_out(thread), "messages": [_msg_out(m) for m in msgs]}


@router.post("/messages")
async def send_my_message(
    payload: MessageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="الرسالة فارغة")
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="الرسالة طويلة جداً")

    thread = _get_or_create_thread(user, db)
    msg = SupportChatMessage(thread_id=thread.id, sender_role="user", sender_id=user.id, body=body)
    db.add(msg)
    thread.unread_for_admin += 1
    thread.last_message_at  = datetime.now(timezone.utc)
    thread.status = ChatThreadStatus.OPEN
    db.commit()
    db.refresh(msg)
    return _msg_out(msg)


# ═══════════════════════════ Admin-side ═══════════════════════════

@router.get("/admin/threads")
async def list_threads(_: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    threads = db.query(SupportChatThread).order_by(SupportChatThread.last_message_at.desc()).all()
    result = []
    for t in threads:
        u = t.user
        last_msg = (
            db.query(SupportChatMessage)
            .filter(SupportChatMessage.thread_id == t.id)
            .order_by(SupportChatMessage.id.desc())
            .first()
        )
        result.append({
            **_thread_out(t),
            "user_id":    u.id if u else None,
            "user_email": u.email if u else "",
            "user_name":  (u.full_name or "") if u else "",
            "last_message_preview": (last_msg.body[:120] if last_msg else ""),
        })
    return {"threads": result}


@router.get("/admin/unread-count")
async def unread_count(_: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    total = sum(
        t.unread_for_admin
        for t in db.query(SupportChatThread).filter(SupportChatThread.unread_for_admin > 0).all()
    )
    return {"unread": total}


@router.get("/admin/threads/{thread_id}/messages")
async def admin_get_messages(
    thread_id: int,
    after_id: int = 0,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    thread = db.query(SupportChatThread).filter(SupportChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")
    msgs = (
        db.query(SupportChatMessage)
        .filter(SupportChatMessage.thread_id == thread.id, SupportChatMessage.id > after_id)
        .order_by(SupportChatMessage.id.asc())
        .all()
    )
    if thread.unread_for_admin > 0:
        thread.unread_for_admin = 0
        db.commit()
    u = thread.user
    return {
        "thread": {**_thread_out(thread), "user_email": u.email if u else "", "user_name": (u.full_name or "") if u else ""},
        "messages": [_msg_out(m) for m in msgs],
    }


@router.post("/admin/threads/{thread_id}/messages")
async def admin_send_message(
    thread_id: int,
    payload: MessageIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="الرسالة فارغة")
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="الرسالة طويلة جداً")

    thread = db.query(SupportChatThread).filter(SupportChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")

    msg = SupportChatMessage(thread_id=thread.id, sender_role="admin", sender_id=admin.id, body=body)
    db.add(msg)
    thread.unread_for_user += 1
    thread.last_message_at  = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    logger.info(f"Support reply sent by admin {admin.id} on thread {thread.id}")
    return _msg_out(msg)


@router.put("/admin/threads/{thread_id}/status")
async def admin_set_status(
    thread_id: int,
    payload: StatusIn,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    if payload.status not in ("open", "closed"):
        raise HTTPException(status_code=400, detail="حالة غير صالحة")
    thread = db.query(SupportChatThread).filter(SupportChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")
    thread.status = ChatThreadStatus(payload.status)
    db.commit()
    return _thread_out(thread)
