"""
Deleted accounts (2026-10-16) — بصمة البريد لحساب حذفه صاحبه (DECISIONS.md 16/10).

الحذف = مسح الهوية لا حذف الصف: الإشارات والمدفوعات مربوطة بـusers.id (إحصاء الأداء والمحاسبة)، فيبقى الصف
بلا بريد ولا اسم ولا هاتف ولا تلجرام. هنا فقط sha256 للبريد (غير قابل للقراءة) — حتى لا يصير "احذف وسجّل من جديد"
طريقاً لتجربة مجانية لا نهائية: نفس البريد يُسجَّل لكن بلا تجربة جديدة.
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class DeletedAccount(Base):
    __tablename__ = "deleted_accounts"

    id         = Column(Integer, primary_key=True, index=True)
    email_hash = Column(String(64), nullable=False, index=True)
    user_id    = Column(Integer, nullable=True)        # الصف المُمسوح (بلا FK — للتتبّع فقط)
    had_paid   = Column(String, nullable=True)          # الباقة وقت الحذف (weekly/monthly/...)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
