"""
Mosh AI Pro v5 - Payment Model
USDT payments via Binance wallet
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentPlan(str, enum.Enum):
    WEEKLY  = "weekly"
    MONTHLY = "monthly"


class Payment(Base):
    __tablename__ = "payments"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    plan        = Column(SAEnum(PaymentPlan), nullable=False)
    amount_usd  = Column(Float, nullable=False)          # 7 or 30
    network     = Column(String, default="TRC20")        # TRC20 / BEP20 / stripe
    tx_id       = Column(String, unique=True, nullable=False)  # Binance TxID or Stripe Checkout Session ID

    provider    = Column(String, default="usdt", nullable=False)  # "usdt" | "stripe"
    stripe_payment_intent = Column(String, nullable=True)

    status      = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    admin_note  = Column(String, nullable=True)
    approved_by = Column(Integer, nullable=True)          # admin user id

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    user        = relationship("User", back_populates="payments")
