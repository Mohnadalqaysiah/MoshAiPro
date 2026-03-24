"""
Qaffel AI — Site Settings Model
إعدادات قابلة للتعديل من لوحة الإدارة (محفظة، بوت، إلخ)
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class SiteSettings(Base):
    __tablename__ = "site_settings"

    id          = Column(Integer, primary_key=True)
    key         = Column(String, unique=True, index=True, nullable=False)
    value       = Column(Text, nullable=True)
    description = Column(String, nullable=True)
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
