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

(2026-10-31) بلاغ المالك: نفس الإشارة تتكرر بإشعارات التطبيق. القرار الواحد صف Signal
لكل مستخدم، والبث كان يرسل كل صف لكل المشتركين بوسم مختلف (signal-{id}): 5 صفوف = 5 إشعارات.
الوسم الآن للقرار لا للصف، ويُفحص بجدول notifications فيصمد بين الدورات وبعد إعادة التشغيل.

نفس asyncio.create_task + while-True + singleton-lock pattern الموجود
بـstrategy_checker.py / market_scanner.py.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

CHECK_INTERVAL_SEC = 120   # كل دقيقتين — أسرع من التليجرام (60ث) غير ضروري هون
MAX_SIGNAL_AGE_MIN = 30    # إشارة أقدم من هيك: لا تبث (وقتها فات، نفس روح _MAX_SIGNAL_AGE بـbot.py)
REPEAT_WINDOW_HOURS = 24   # نفس القرار بعدها صفقة جديدة وصلت لنفس السعر، لا تكرار

_LOCK_KEY = 90210005  # فريد — 90210001..90210004 مستخدَمة أصلاً


def decision_tag(sig) -> str:
    """وسم واحد لكل صفوف القرار، ونفس الوسم يجعل المتصفح يستبدل الإشعار بدل تكديسه."""
    from app.services.decision_grouping import decision_key
    market, timeframe, side, entry = decision_key(sig.market, sig.timeframe, sig.signal_type, sig.entry_price)
    return f"signal-{market}-{timeframe}-{side}-{entry}"


def broadcast_cycle(db, now: datetime) -> int:
    """دورة بث واحدة، ويعيد عدد الإشعارات المرسلة."""
    from app.models.notification import Notification
    from app.models.push_subscription import PushSubscription
    from app.models.signal import Signal, SignalStatus
    from app.models.user import User
    from app.services.web_push import send_push

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
        return 0

    # مستخدمو إشعارات المتصفح المسجَّلين حالياً — استعلام واحد
    # لكل دورة، لا لكل إشارة.
    subscriber_ids = {
        row[0] for row in db.query(PushSubscription.user_id).distinct().all()
    }
    if not subscriber_ids:
        for sig in candidates:
            sig.push_broadcast_sent = True
        db.commit()
        return 0

    users = db.query(User).filter(User.id.in_(subscriber_ids)).all()
    tags = {decision_tag(s) for s in candidates}
    notified = {
        (r[0], r[1]) for r in db.query(Notification.user_id, Notification.tag).filter(
            Notification.tag.in_(tags),
            Notification.created_at >= now - timedelta(hours=REPEAT_WINDOW_HOURS),
        ).all()
    }
    sent_total = 0
    for sig in candidates:
        sig.push_broadcast_sent = True
        created = sig.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_min = (now - created).total_seconds() / 60 if created else 0
        if age_min > MAX_SIGNAL_AGE_MIN:
            continue

        rec_ar = "شراء" if sig.signal_type.value == "BUY" else "بيع"
        title  = f"🚨 إشارة جديدة — {sig.market}"
        body   = f"{rec_ar} {sig.market} ({sig.timeframe}) — افتح التطبيق لرؤية التفاصيل"

        # (2026-09-28) بلاغ حقيقي: الضغط على الإشعار كان يفتح
        # الداشبورد العامة دايماً بدل الإشارة نفسها بالضبط —
        # Dashboard.jsx يقرأ ?signal=ID ويفتح نافذة التحليل لها مباشرة.
        signal_url = f"/dashboard?signal={sig.id}"
        tag = decision_tag(sig)
        for u in users:
            if (u.id, tag) in notified:
                continue
            # (2026-10-12) نفس تخصيص الإشارات: الأزواج والفريمات والثقة.
            # لا نطبّق notifications_enabled هنا — زرّه بالواجهة "إشعارات
            # تيليجرام"، وإشعار الجوال له موافقة مستقلة من المتصفح.
            wl = u.notify_watchlist or []
            if wl and sig.market.upper() not in [w.upper() for w in wl]:
                continue
            tfs = {t for t in (u.notify_timeframes or []) if t != "all"}
            if tfs and sig.timeframe not in tfs:
                continue
            if (u.notify_min_confidence or 0) > 0 and float(sig.ai_confidence or 0) < u.notify_min_confidence:
                continue
            sent_total += send_push(db, u, title, body, url=signal_url, tag=tag)
            notified.add((u.id, tag))

    db.commit()
    return sent_total


async def web_push_broadcaster():
    from app.database import SessionLocal
    from app.services.web_push import push_enabled
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
                sent_total = broadcast_cycle(db, datetime.now(timezone.utc))
                if sent_total:
                    logger.info(f"📲 Web push: {sent_total} إشعار متصفح أُرسل هالدورة")

            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Web push broadcaster error: {e}")

    lock_conn.close()
