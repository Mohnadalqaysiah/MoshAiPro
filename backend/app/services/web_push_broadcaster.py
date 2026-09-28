"""
Mosh AI Pro v5 - Web Push Broadcaster
حلقة خلفية دورية: تفحص الإشارات الجديدة (نفس مصدر broadcast_new_signals
بـtelegram-bot لكن قناة مختلفة تماماً) وترسل إشعار متصفح لكل مستخدم مشترك
بإشعارات المتصفح (PushSubscription) ورمزها ضمن قائمة مراقبته (أو قائمة
فاضية = كل الرموز، نفس اتفاقية notify_watchlist بكل مكان تاني بالمشروع).

(2026-09-27) لا تفاصيل دخول/وقف/هدف بالإشعار نفسه — تنبيه "افتح التطبيق"
فقط، فلا داعي لتكرار منطق القفل/التمويه المستخدم بتيليجرام للتفاصيل
الكاملة. push_broadcast_sent علَم مستقل عن broadcast_sent (تيليجرام) —
كل قناة تتبّع بثّها بنفسها.

نفس asyncio.create_task + while-True + singleton-lock pattern الموجود
بـstrategy_checker.py / market_scanner.py.
"""
import asyncio
from datetime import datetime, timezone
from loguru import logger

CHECK_INTERVAL_SEC = 120   # كل دقيقتين — أسرع من التليجرام (60ث) غير ضروري هون
MAX_SIGNAL_AGE_MIN = 30    # إشارة أقدم من هيك: لا تبث (وقتها فات، نفس روح _MAX_SIGNAL_AGE بـbot.py)

_LOCK_KEY = 90210005  # فريد — 90210001..90210004 مستخدَمة أصلاً


async def web_push_broadcaster():
    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.models.user import User
    from app.models.push_subscription import PushSubscription
    from app.services.web_push import send_push, push_enabled
    from app.services.worker_lock import try_acquire_singleton_lock

    if not push_enabled():
        logger.info("ℹ️ Web push broadcaster: VAPID keys غير مضبوطة — المهمة لن تعمل")
        return

    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Web push broadcaster")
    if lock_conn is None:
        return

    logger.success("✅ Web push broadcaster started")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)
                candidates = (
                    db.query(Signal)
                    .filter(
                        Signal.status.in_([SignalStatus.PENDING, SignalStatus.ACTIVE]),
                        (Signal.push_broadcast_sent == False) | (Signal.push_broadcast_sent.is_(None)),
                    )
                    .order_by(Signal.created_at.desc())
                    .limit(30)
                    .all()
                )
                if not candidates:
                    continue

                # مستخدمو إشعارات المتصفح المسجَّلين حالياً — استعلام واحد
                # لكل دورة، لا لكل إشارة.
                subscriber_ids = {
                    row[0] for row in db.query(PushSubscription.user_id).distinct().all()
                }
                if not subscriber_ids:
                    for sig in candidates:
                        sig.push_broadcast_sent = True
                    db.commit()
                    continue

                users = db.query(User).filter(User.id.in_(subscriber_ids)).all()
                sent_total = 0
                for sig in candidates:
                    created = sig.created_at
                    if created and created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    age_min = (now - created).total_seconds() / 60 if created else 0
                    if age_min > MAX_SIGNAL_AGE_MIN:
                        sig.push_broadcast_sent = True
                        continue

                    rec_ar = "شراء" if sig.signal_type.value == "BUY" else "بيع"
                    title  = f"🚨 إشارة جديدة — {sig.market}"
                    body   = f"{rec_ar} {sig.market} ({sig.timeframe}) — افتح التطبيق لرؤية التفاصيل"

                    # (2026-09-28) بلاغ حقيقي: الضغط على الإشعار كان يفتح
                    # الداشبورد العامة دايماً بدل الإشارة نفسها بالضبط —
                    # Dashboard.jsx يقرأ ?signal=ID ويفتح نافذة التحليل لها مباشرة.
                    signal_url = f"/dashboard?signal={sig.id}"
                    for u in users:
                        wl = u.notify_watchlist or []
                        if wl and sig.market.upper() not in [w.upper() for w in wl]:
                            continue
                        sent_total += send_push(db, u, title, body, url=signal_url, tag=f"signal-{sig.id}")

                    sig.push_broadcast_sent = True

                db.commit()
                if sent_total:
                    logger.info(f"📲 Web push: {sent_total} إشعار متصفح أُرسل هالدورة")

            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Web push broadcaster error: {e}")

    lock_conn.close()
