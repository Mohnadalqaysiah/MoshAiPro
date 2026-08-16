"""
Mosh AI Pro v5 - Support Chat Model (in-house live chat)
"""

import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ChatThreadStatus(str, enum.Enum):
    OPEN   = "open"
    CLOSED = "closed"


class SupportChatThread(Base):
    __tablename__ = "support_chat_threads"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    status           = Column(SQLEnum(ChatThreadStatus), default=ChatThreadStatus.OPEN, nullable=False)
    unread_for_admin = Column(Integer, default=0, nullable=False)   # user messages not yet seen by admin
    unread_for_user  = Column(Integer, default=0, nullable=False)   # admin messages not yet seen by user
    last_message_at  = Column(DateTime(timezone=True), server_default=func.now())
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user     = relationship("User", back_populates="support_chat_thread")
    messages = relationship(
        "SupportChatMessage", back_populates="thread",
        cascade="all, delete-orphan", order_by="SupportChatMessage.id",
    )


class SupportChatMessage(Base):
    __tablename__ = "support_chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    thread_id   = Column(Integer, ForeignKey("support_chat_threads.id"), nullable=False, index=True)
    sender_role = Column(String, nullable=False)   # "user" | "admin"
    sender_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    body        = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("SupportChatThread", back_populates="messages")
