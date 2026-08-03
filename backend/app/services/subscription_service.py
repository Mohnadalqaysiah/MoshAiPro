"""
Mosh AI Pro v5 - Subscription Activation Service
Shared logic to activate a user's plan after a payment is approved,
used by both manual USDT admin approval and the Stripe webhook.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from loguru import logger

from app.models.user import User, PlanType
from app.models.payment import Payment, PaymentPlan
from app.models.site_settings import SiteSettings
from app.models.affiliate import Affiliate, AffiliateReferral, TIER1_RATE, TIER2_RATE, TIER2_THRESHOLD
from app.config import get_settings

settings = get_settings()


def _get_plan_days(db: Session, plan_key: str, default: int) -> int:
    r = db.query(SiteSettings).filter(SiteSettings.key == f"plan_{plan_key}_days").first()
    try:
        return int(r.value) if r and r.value else default
    except Exception:
        return default


def activate_subscription_payment(
    db: Session,
    payment: Payment,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[User]:
    """
    Extends/activates a user's subscription based on an approved Payment row,
    credits affiliate commission (if applicable), and emails the user.
    Assumes payment.status is already set to APPROVED by the caller.
    Does NOT commit — caller is responsible for db.commit().
    """
    now = datetime.now(timezone.utc)

    user = db.query(User).filter(User.id == payment.user_id).first()
    if not user:
        return None

    days = (
        _get_plan_days(db, "weekly", 7)
        if payment.plan == PaymentPlan.WEEKLY
        else _get_plan_days(db, "monthly", 30)
    )
    if user.subscription_ends_at and user.subscription_ends_at > now:
        user.subscription_ends_at += timedelta(days=days)
    else:
        user.subscription_ends_at = now + timedelta(days=days)

    user.plan      = PlanType(payment.plan.value)
    user.is_active = True
    logger.info(
        f"✅ Payment activated: user={user.email} plan={payment.plan} "
        f"days={days} provider={payment.provider}"
    )

    # ── Affiliate commission ──────────────────────────────────────
    if user.referred_by_code:
        ref_aff = db.query(Affiliate).filter(
            Affiliate.code == user.referred_by_code
        ).first()
        if ref_aff:
            already = db.query(AffiliateReferral).filter(
                AffiliateReferral.payment_id == payment.id
            ).first()
            if not already:
                rate = TIER2_RATE if ref_aff.total_referrals >= TIER2_THRESHOLD else TIER1_RATE
                tier = 2 if ref_aff.total_referrals >= TIER2_THRESHOLD else 1
                commission = round(payment.amount_usd * rate, 4)
                db.add(AffiliateReferral(
                    affiliate_id       = ref_aff.id,
                    referred_user_id   = user.id,
                    payment_id         = payment.id,
                    payment_amount_usd = payment.amount_usd,
                    commission_rate    = rate,
                    commission_usd     = commission,
                    tier               = tier,
                ))
                ref_aff.total_referrals     += 1
                ref_aff.pending_balance_usd += commission
                if ref_user := db.query(User).filter(User.id == ref_aff.user_id).first():
                    ref_user.referral_points = (ref_user.referral_points or 0) + 50
                logger.info(
                    f"💰 Affiliate commission: referrer_id={ref_aff.user_id} "
                    f"tier={tier} rate={rate*100:.0f}% earned={commission}$ +50pts"
                )
                if ref_user and settings.SMTP_PASSWORD:
                    from app.services.email_service import send_email, affiliate_commission_email_body
                    body = affiliate_commission_email_body(
                        name=ref_user.full_name or ref_user.email,
                        commission_usd=commission,
                        referral_name=user.full_name or user.email,
                        tier=tier,
                        pending_balance=ref_aff.pending_balance_usd + commission,
                    )
                    if background_tasks:
                        background_tasks.add_task(
                            send_email, ref_user.email,
                            f"💰 عمولة جديدة ${commission:.2f} — Qaffel AI",
                            body, settings.SMTP_PASSWORD,
                        )

    # ── User notification email ───────────────────────────────────
    if settings.SMTP_PASSWORD and background_tasks:
        from app.services.email_service import send_email, payment_approved_email_body
        ends_str = user.subscription_ends_at.strftime("%Y-%m-%d") if user.subscription_ends_at else "—"
        body = payment_approved_email_body(
            user.full_name or user.email,
            payment.plan.value, days, ends_str,
        )
        background_tasks.add_task(
            send_email, user.email,
            "✅ تم تفعيل اشتراكك — Qaffel AI", body, settings.SMTP_PASSWORD,
        )

    return user
