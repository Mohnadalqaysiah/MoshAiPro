"""
Mosh AI Pro v5 - Checkout Abandonment Reminder
خلفية دورية: تلاحظ مستخدماً بدأ خطوات الدفع (FunnelEvent.event ==
"checkout_started") ولم يكمله خلال ساعة، وترسل له تذكيراً لطيفاً — تيليجرام
إذا حسابه مربوط، وإلا إيميل. مرة واحدة فقط لكل محاولة (reminded_at).

راجع DECISIONS.md 2026-09-24 لسياق القرار: ما كان عندنا أي أثر لمحاولة دفع
لم تكتمل أصلاً قبل FunnelEvent، فهاي أول مرة يصير عندنا إمكانية استرجاع
عميل بدل ما يضيع بصمت.

نفس asyncio.create_task + while-True + singleton-lock pattern الموجود
بـ integrity_checker.py / strategy_checker.py / market_scanner.py.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

CHECK_INTERVAL_SEC   = 15 * 60   # كل 15 دقيقة
REMIND_AFTER_HOURS   = 1          # لا تذكير قبل ساعة كاملة من بدء الدفع — فرصة طبيعية للإكمال بلا إزعاج
REMIND_MAX_AGE_HOURS = 48         # محاولات أقدم من يومين تُهمَل (لا نُذكّر بشيء قديم جداً بلا سياق)

_LOCK_KEY = 90210004  # مفتاح فريد — 90210001/2/3 مستخدمة أصلاً بمهام أخرى


async def checkout_reminder_checker():
    from app.database import SessionLocal
    from app.models.funnel_event import FunnelEvent
    from app.models.payment import Payment, PaymentStatus
    from app.models.user import User
    from app.services.admin_notify import notify_user_telegram
    from app.services.email_service import send_email, checkout_reminder_email_body
    from app.services.worker_lock import try_acquire_singleton_lock

    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Checkout reminder checker")
    if lock_conn is None:
        return

    logger.info("🔒 Checkout reminder checker: acquired singleton lock — running")
    plan_labels = {"trial": "تجريبي", "weekly": "أسبوعي", "monthly": "شهري", "yearly": "سنوي"}

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)
                window_end   = now - timedelta(hours=REMIND_AFTER_HOURS)
                window_start = now - timedelta(hours=REMIND_MAX_AGE_HOURS)

                candidates = (
                    db.query(FunnelEvent)
                    .filter(
                        FunnelEvent.event == "checkout_started",
                        FunnelEvent.reminded_at.is_(None),
                        FunnelEvent.created_at <= window_end,
                        FunnelEvent.created_at >= window_start,
                    )
                    .all()
                )

                sent_count = 0
                for ev in candidates:
                    # أكمل الدفع أصلاً بعد بدء المحاولة؟ لا تذكير، فقط علِّمها معالَجة.
                    converted = (
                        db.query(Payment)
                        .filter(
                            Payment.user_id == ev.user_id,
                            Payment.status == PaymentStatus.APPROVED,
                            Payment.created_at >= ev.created_at,
                        )
                        .first()
                    )
                    if converted:
                        ev.reminded_at = now
                        continue

                    user = db.query(User).filter(User.id == ev.user_id).first()
                    if not user:
                        ev.reminded_at = now
                        continue

                    plan_label = plan_labels.get(ev.plan, ev.plan or "المختارة")
                    if user.telegram_id:
                        notify_user_telegram(
                            user.telegram_id,
                            f"👋 لاحظنا إنك بدأت الاشتراك بالباقة <b>{plan_label}</b> ولم تكمل الدفع.\n"
                            f"واجهتك مشكلة؟ راسلنا مباشرة، أو أكمل الآن:\n"
                            f"https://qaffel.com/pricing"
                        )
                        sent_count += 1
                    elif user.email:
                        send_email(
                            user.email,
                            "أكمل اشتراكك بـ Qaffel AI",
                            checkout_reminder_email_body(user.full_name, plan_label),
                        )
                        sent_count += 1

                    ev.reminded_at = now

                db.commit()
                if sent_count:
                    logger.info(f"📩 Checkout reminder: {sent_count} sent this cycle")

            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Checkout reminder checker error: {e}")

    lock_conn.close()
