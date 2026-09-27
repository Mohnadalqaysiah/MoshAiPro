"""
Mosh AI Pro v5 - Feature Survey Model
استطلاع "ساعدنا نطور المنصة لك" — قابل للتعديل الكامل من لوحة الأدمن
(سؤال + خيارات) بدل النص الثابت بـFeatureSurveyModal.jsx القديم.

نسخة واحدة فقط is_active=True بأي لحظة — نشر تعديل جديد يُخمِّد القديمة
(is_active=False) لا يحذفها، فتبقى إجابات FeatureRequest القديمة قابلة
للقراءة بسياقها (survey_id).
"""
from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class FeatureSurvey(Base):
    __tablename__ = "feature_surveys"

    id          = Column(Integer, primary_key=True, index=True)
    question_ar = Column(String, nullable=False)
    question_en = Column(String, nullable=False)
    # [{"key": "concurrent_signals_warning", "ar": "...", "en": "..."}, ...]
    options     = Column(JSON, nullable=False)
    is_active   = Column(Boolean, default=False, nullable=False, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
