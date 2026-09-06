"""
Mosh AI Pro v5 - Support Chat API (in-house live chat, user <-> admin)
"""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.support_chat import SupportChatThread, SupportChatMessage, ChatThreadStatus
from app.services.auth_service import get_current_user, get_admin_user
from app.services.admin_notify import notify_admin_telegram, notify_user_telegram

router = APIRouter()
_settings = get_settings()

# ── Attachments (images + docs, ≤1MB) ───────────────────────────────────────
_MAX_ATTACHMENT_BYTES = 1 * 1024 * 1024
_ALLOWED_ATTACHMENT_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "application/pdf",
}
_UPLOAD_DIR = "/app/static/uploads/support"


def _frontend_url() -> str:
    return _settings.ALLOWED_ORIGINS.split(",")[0].strip().rstrip("/")


async def _save_attachment(file: UploadFile) -> dict:
    if file.content_type not in _ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(status_code=400, detail="نوع الملف غير مدعوم — صورة (PNG/JPG/GIF/WebP) أو PDF فقط")

    data = await file.read()
    if len(data) > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="حجم الملف أكبر من 1 ميجابايت")

    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    fname = f"{uuid.uuid4().hex}.{ext}"
    with open(f"{_UPLOAD_DIR}/{fname}", "wb") as f:
        f.write(data)

    return {
        "attachment_url":  f"/static/uploads/support/{fname}",
        "attachment_name": file.filename or fname,
        "attachment_type": file.content_type,
    }


def _get_thread(user: User, db: Session) -> SupportChatThread | None:
    return db.query(SupportChatThread).filter(SupportChatThread.user_id == user.id).first()


def _get_or_create_thread(user: User, db: Session) -> SupportChatThread:
    thread = _get_thread(user, db)
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
        "id":               m.id,
        "thread_id":        m.thread_id,
        "sender_role":      m.sender_role,
        "sender_id":        m.sender_id,
        "body":             m.body,
        "attachment_url":   m.attachment_url,
        "attachment_name":  m.attachment_name,
        "attachment_type":  m.attachment_type,
        "created_at":       m.created_at.isoformat() if m.created_at else None,
    }


class StatusIn(BaseModel):
    status: str


# ═══════════════════════════ User-side ═══════════════════════════

_EMPTY_THREAD = {
    "id": None, "status": "open", "unread_for_admin": 0, "unread_for_user": 0,
    "last_message_at": None, "created_at": None,
}


@router.get("/thread")
async def get_my_thread(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # (2026-09-06) هاد الـ endpoint يُستدعى كل 20 ثانية من كل مستخدم مسجّل دخول
    # (فحص خفيف لعداد unread)، حتى لو ما فتح الشات أبداً — كان يستخدم
    # _get_or_create_thread فينشئ صف "محادثة مفتوحة" لكل مستخدم بمجرد زيارته
    # أي صفحة محمية. صار read-only: ما في محادثة حقيقية إلا لما المستخدم
    # فعلاً يرسل رسالة (send_my_message تستخدم _get_or_create_thread).
    thread = _get_thread(user, db)
    return _thread_out(thread) if thread else _EMPTY_THREAD


@router.get("/messages")
async def get_my_messages(
    after_id: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = _get_thread(user, db)
    if not thread:
        return {"thread": _EMPTY_THREAD, "messages": []}
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
    background_tasks: BackgroundTasks,
    body: str = Form(""),
    file: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = (body or "").strip()
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="الرسالة طويلة جداً")

    attachment = await _save_attachment(file) if file is not None else {}
    if not body and not attachment:
        raise HTTPException(status_code=400, detail="الرسالة فارغة")

    thread = _get_or_create_thread(user, db)
    msg = SupportChatMessage(
        thread_id=thread.id, sender_role="user", sender_id=user.id,
        body=body or None, **attachment,
    )
    db.add(msg)
    thread.unread_for_admin += 1
    thread.last_message_at  = datetime.now(timezone.utc)
    thread.status = ChatThreadStatus.OPEN
    db.commit()
    db.refresh(msg)

    preview = body[:200] if body else ("📎 " + (attachment.get("attachment_name") or "مرفق"))
    admin_link = f"{_frontend_url()}/admin?tab=support"
    background_tasks.add_task(
        notify_admin_telegram,
        f"💬 <b>رسالة دعم جديدة</b>\n"
        f"من: {user.full_name or user.email}\n"
        f"{preview}\n\n"
        f"<a href=\"{admin_link}\">فتح لوحة الدعم</a>",
    )
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
        preview = ""
        if last_msg:
            preview = last_msg.body[:120] if last_msg.body else f"📎 {last_msg.attachment_name or 'مرفق'}"
        result.append({
            **_thread_out(t),
            "user_id":    u.id if u else None,
            "user_email": u.email if u else "",
            "user_name":  (u.full_name or "") if u else "",
            "last_message_preview": preview,
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
    background_tasks: BackgroundTasks,
    body: str = Form(""),
    file: UploadFile | None = File(None),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    body = (body or "").strip()
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="الرسالة طويلة جداً")

    attachment = await _save_attachment(file) if file is not None else {}
    if not body and not attachment:
        raise HTTPException(status_code=400, detail="الرسالة فارغة")

    thread = db.query(SupportChatThread).filter(SupportChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")

    msg = SupportChatMessage(
        thread_id=thread.id, sender_role="admin", sender_id=admin.id,
        body=body or None, **attachment,
    )
    db.add(msg)
    thread.unread_for_user += 1
    thread.last_message_at  = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    logger.info(f"Support reply sent by admin {admin.id} on thread {thread.id}")

    customer = thread.user
    if customer and customer.telegram_id:
        preview = body[:200] if body else ("📎 " + (attachment.get("attachment_name") or "مرفق"))
        background_tasks.add_task(
            notify_user_telegram,
            customer.telegram_id,
            f"💬 <b>وردك رد جديد من الدعم الفني</b>\n{preview}\n\n"
            f"افتح لوحة التحكم لقراءة الرد والمتابعة.",
        )
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
