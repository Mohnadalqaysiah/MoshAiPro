"""
Mosh AI Pro v5 - Feature Request Model
استطلاع رأي بسيط (Popup) يُعرض مرة واحدة لكل مستخدم: أي ميزة يعتبرها
الأهم حالياً. راجع app.models.user.feature_survey_dismissed للعلم
بأن المستخدم شاهد الاستطلاع (سواء أرسل أو تخطّاه).
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class FeatureRequest(Base):
    __tablename__ = "feature_requests"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    selected_option = Column(String, nullable=False)
    custom_text     = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
