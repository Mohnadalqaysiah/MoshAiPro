"""
Mosh AI Pro v5 - Affiliate / Referral API
User-facing affiliate dashboard
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.models.affiliate import Affiliate, AffiliateReferral, TIER1_RATE, TIER2_RATE, TIER2_THRESHOLD, generate_affiliate_code
from app.services.auth_service import get_current_user
from app.config import get_settings

router = APIRouter()
_settings = get_settings()


def _get_or_create(user: User, db: Session) -> Affiliate:
    """Return affiliate record, creating one if missing (safety net)."""
    aff = db.query(Affiliate).filter(Affiliate.user_id == user.id).first()
    if not aff:
        code = user.affiliate_code or generate_affiliate_code(db)
        if not user.affiliate_code:
            user.affiliate_code = code
        aff = Affiliate(
            user_id             = user.id,
            code                = code,
            referred_by_code    = user.referred_by_code,
            total_referrals     = 0,
            pending_balance_usd = 0.0,
            paid_out_usd        = 0.0,
        )
        db.add(aff)
        db.commit()
        db.refresh(aff)
    return aff


@router.get("/dashboard")
def affiliate_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """لوحة تحكم الأفلييت للمستخدم"""
    aff = _get_or_create(user, db)

    tier = 2 if aff.total_referrals >= TIER2_THRESHOLD else 1
    rate_pct = 15 if tier == 2 else 5
    to_next = max(0, TIER2_THRESHOLD - aff.total_referrals) if tier == 1 else None

    # Referral link — use site's public URL or fallback
    frontend_url = _settings.ALLOWED_ORIGINS.split(",")[0].strip().rstrip("/")
    link = f"{frontend_url}/register?ref={aff.code}"

    rows = db.query(AffiliateReferral).filter(
        AffiliateReferral.affiliate_id == aff.id
    ).order_by(AffiliateReferral.created_at.desc()).all()

    referrals = [
        {
            "referred_user_email": r.referred_user.email if r.referred_user else "",
            "payment_amount_usd":  r.payment_amount_usd,
            "commission_usd":      r.commission_usd,
            "tier":                r.tier,
            "created_at":          r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {
        "affiliate_code":        aff.code,
        "referral_link":         link,
        "current_tier":          tier,
        "commission_rate_pct":   rate_pct,
        "total_referrals":       aff.total_referrals,
        "referrals_to_next_tier": to_next,
        "pending_balance_usd":   aff.pending_balance_usd,
        "paid_out_usd":          aff.paid_out_usd,
        "referrals":             referrals,
    }


@router.get("/link")
def affiliate_link(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """رابط الإحالة فقط (خفيف)"""
    aff = _get_or_create(user, db)
    frontend_url = _settings.ALLOWED_ORIGINS.split(",")[0].strip().rstrip("/")
    return {
        "code": aff.code,
        "link": f"{frontend_url}/register?ref={aff.code}",
    }
