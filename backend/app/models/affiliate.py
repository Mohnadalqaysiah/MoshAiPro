"""
Mosh AI Pro v5 - Affiliate / Referral Models
"""
import secrets
import string
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Session
from app.database import Base

# Commission tiers
TIER1_RATE      = 0.05   # 5%
TIER2_RATE      = 0.15   # 15%
TIER2_THRESHOLD = 25     # referrals needed to reach tier 2


def generate_affiliate_code(db: Session) -> str:
    """Generate a unique 8-char alphanumeric referral code."""
    from app.models.user import User
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        if not db.query(User).filter(User.affiliate_code == code).first():
            return code
    raise ValueError("Could not generate a unique affiliate code after 20 attempts")


class Affiliate(Base):
    __tablename__ = "affiliates"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    code                = Column(String(8), unique=True, nullable=False, index=True)
    referred_by_code    = Column(String(8), nullable=True, index=True)

    total_referrals     = Column(Integer, default=0, nullable=False)
    pending_balance_usd = Column(Float, default=0.0, nullable=False)
    paid_out_usd        = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user     = relationship("User", back_populates="affiliate")
    referrals = relationship("AffiliateReferral", back_populates="affiliate", cascade="all, delete-orphan")


class AffiliateReferral(Base):
    __tablename__ = "affiliate_referrals"

    id                 = Column(Integer, primary_key=True, index=True)
    affiliate_id       = Column(Integer, ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False, index=True)
    referred_user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id         = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, unique=True)

    payment_amount_usd = Column(Float, nullable=False)
    commission_rate    = Column(Float, nullable=False)   # 0.05 or 0.15
    commission_usd     = Column(Float, nullable=False)
    tier               = Column(Integer, nullable=False) # 1 or 2

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    affiliate     = relationship("Affiliate", back_populates="referrals")
    referred_user = relationship("User", foreign_keys=[referred_user_id])
    payment       = relationship("Payment")
