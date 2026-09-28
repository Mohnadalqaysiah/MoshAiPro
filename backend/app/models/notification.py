"""
Mosh AI Pro v5 - In-App Notification Log
(2026-09-28) سجل الإشعارات يلي فعلياً أُرسلت لكل مستخدم عبر Web Push —
زر "🔔" بالتطبيق يعرض آخرها حتى لو المستخدم فوّت/رفض إشعار المتصفح
نفسه (خصوصاً بالهاتف). يُكتب من نقطة واحدة (web_push.py:send_push) —
كل مصدر إشعار (إشارة جديدة، تذكير دفع، إرسال إداري يدوي) يمرّ من هناك
أصلاً، فلا حاجة لتكرار الكتابة بكل مصدر.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title      = Column(String, nullable=False)
    body       = Column(String, nullable=False)
    url        = Column(String, nullable=True)
    tag        = Column(String, nullable=True)
    is_read    = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
