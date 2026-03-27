"""
Mosh AI Pro v5 - Affiliate / Referral API
User-facing affiliate dashboard
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.models.affiliate import Affiliate, AffiliateReferral, TIER1_RATE, TIER2_RATE, TIER2_THRESHOLD, generate_affiliate_code
from app.models.site_settings import SiteSettings
from app.services.auth_service import get_current_user
from app.services.email_service import send_email
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

    min_row = db.query(SiteSettings).filter(SiteSettings.key == "affiliate_min_payout_usd").first()
    min_payout = float(min_row.value) if min_row and min_row.value else 10.0

    return {
        "affiliate_code":        aff.code,
        "referral_link":         link,
        "current_tier":          tier,
        "commission_rate_pct":   rate_pct,
        "total_referrals":       aff.total_referrals,
        "referrals_to_next_tier": to_next,
        "pending_balance_usd":   aff.pending_balance_usd,
        "paid_out_usd":          aff.paid_out_usd,
        "min_payout_usd":        min_payout,
        "referrals":             referrals,
    }


class PayoutRequestSchema(BaseModel):
    amount_usd: float
    note: str = ""


@router.post("/payout-request")
def request_payout(
    data: PayoutRequestSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """طلب سحب رصيد الإحالات — يُرسل إشعاراً للمشرف"""
    aff = _get_or_create(user, db)

    min_row = db.query(SiteSettings).filter(SiteSettings.key == "affiliate_min_payout_usd").first()
    min_payout = float(min_row.value) if min_row and min_row.value else 10.0

    if data.amount_usd <= 0:
        raise HTTPException(400, "المبلغ يجب أن يكون أكبر من صفر")
    if data.amount_usd < min_payout:
        raise HTTPException(400, f"الحد الأدنى للسحب هو ${min_payout:.2f}")
    if data.amount_usd > aff.pending_balance_usd:
        raise HTTPException(400, f"الرصيد المتاح ${aff.pending_balance_usd:.2f} فقط")

    # Notify admin by email
    settings = get_settings()
    admin_email = settings.SMTP_USER
    if admin_email:
        subject = f"طلب سحب رصيد إحالات — {user.email}"
        body = (
            f"<h2>طلب سحب جديد</h2>"
            f"<p><b>المستخدم:</b> {user.full_name or ''} ({user.email})</p>"
            f"<p><b>المبلغ المطلوب:</b> ${data.amount_usd:.2f} USDT</p>"
            f"<p><b>الرصيد المتاح:</b> ${aff.pending_balance_usd:.2f}</p>"
            f"<p><b>ملاحظة:</b> {data.note or '—'}</p>"
            f"<p>يرجى معالجة الطلب من لوحة الإدارة.</p>"
        )
        try:
            send_email(admin_email, subject, body)
        except Exception as e:
            logger.warning(f"Failed to notify admin of payout request: {e}")

    logger.info(f"💳 Payout request: user={user.email} amount=${data.amount_usd} note={data.note}")
    return {"success": True, "message": "تم إرسال طلب السحب بنجاح. سيتم مراجعته من قِبَل الفريق خلال 24 ساعة."}


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
