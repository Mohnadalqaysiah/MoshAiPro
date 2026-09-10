"""
Mosh AI Pro v5 - Signal Data Integrity Checker
Background loop that watches for the two failure patterns that have bitten
us before (both discovered manually, days after the fact, via a customer
report): a closed signal that got points_earned ≈ 0 (multiplier/formula
bug for that symbol — e.g. the ADAUSD/DOGEUSD ×10000 bug), and a signal
stuck ACTIVE long past when its timeframe should have resolved it
(outcome-checker not covering that symbol — e.g. the pre-TV_SYMBOL_MAP
gap). Sends an instant Telegram alert to the admin instead of waiting for
someone to notice a skewed report.

Same asyncio.create_task + while-True + singleton-lock pattern as
strategy_checker.py / _price_alert_checker() in app/main.py.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

CHECK_INTERVAL_SEC = 3 * 3600     # كل 3 ساعات
ZERO_PTS_WINDOW_HOURS = 26        # يفحص الصفقات المغلقة خلال آخر 26 ساعة (أكبر من الفاصل قليلاً حتى ما يفوت شي بين دورتين)
ZERO_PTS_EPSILON = 0.01           # points_earned بهاي القيمة أو أقل = مشبوه لصفقة محسومة فعلياً
STUCK_REALERT_HOURS = 24          # لو لسه عالقة، ذكّر الأدمن مرة كل 24 ساعة بس مو كل دورة

# بعتبر الصفقة "عالقة" (يُفترض إنها انحسمت SL/TP من زمان) إذا تجاوز عمرها
# هالعتبة حسب الفريم — أكبر بكثير من عتبة "الحداثة" المستخدمة بودجت أفضل
# فرصة بالواجهة (تلك تخفي عن العميل، هاي تنبّه الأدمن لخلل محتمل بالمراقبة).
STUCK_THRESHOLD_HOURS = {
    "1m": 6, "5m": 12, "15m": 24, "30m": 48,
    "1h": 72, "4h": 168, "1d": 336,
}
STUCK_DEFAULT_HOURS = 48
STUCK_ABSOLUTE_CAP_HOURS = 24 * 30   # سقف مطلق: أي إشارة ACTIVE عمرها أكثر من 30 يوم = علامة حمراء بغض النظر عن الفريم

_LOCK_KEY = 90210002  # مفتاح فريد لهالمهمة، مختلف عن strategy_checker (90210001)

# ذاكرة داخل العملية فقط (تصفر بإعادة التشغيل) — نفس روح last_alert
# بـtelegram-bot/bot.py: تمنع تكرار نفس التنبيه كل دورة.
_alerted_zero_pts_ids: set = set()
_stuck_last_alerted: dict = {}   # signal_id -> datetime آخر تنبيه


def _stuck_threshold_hours(timeframe: str) -> int:
    return STUCK_THRESHOLD_HOURS.get((timeframe or "").lower(), STUCK_DEFAULT_HOURS)


async def integrity_checker():
    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.services.admin_notify import notify_admin_telegram
    from app.services.worker_lock import try_acquire_singleton_lock

    # production تشغّل عدة workers — عامل واحد بس يشغّل هالحلقة (نفس منطق
    # strategy_checker) حتى ما يوصل تنبيه مكرر للأدمن.
    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Integrity checker")
    if lock_conn is None:
        return

    logger.info("🔒 Integrity checker: acquired singleton lock — running")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)

                # ── 1) صفقات محسومة بنقاط ≈ 0 (علامة خلل احتساب) ──────────
                zero_cutoff = now - timedelta(hours=ZERO_PTS_WINDOW_HOURS)
                closed = (
                    db.query(Signal)
                    .filter(Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]))
                    .filter(Signal.exit_executed.isnot(None))
                    .filter(Signal.exit_executed >= zero_cutoff)
                    .all()
                )
                zero_pts_flagged = [
                    s for s in closed
                    if s.id not in _alerted_zero_pts_ids
                    and abs(s.points_earned or 0.0) <= ZERO_PTS_EPSILON
                ]
                for s in zero_pts_flagged:
                    _alerted_zero_pts_ids.add(s.id)

                if zero_pts_flagged:
                    lines = "\n".join(
                        f"• #{s.id} <b>{s.market}</b> ({s.timeframe}) — "
                        f"{s.status.value if hasattr(s.status, 'value') else s.status} → "
                        f"<code>{s.points_earned}</code> نقطة"
                        for s in zero_pts_flagged[:15]
                    )
                    extra = f"\n… و{len(zero_pts_flagged) - 15} إشارة إضافية" if len(zero_pts_flagged) > 15 else ""
                    msg = (
                        f"⚠️ <b>فحص سلامة الإحصائيات — نقاط صفرية مشبوهة</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"صفقات محسومة (هدف/وقف) بنقاط ≈ 0 — على الأغلب خلل بمضاعف\n"
                        f"الرمز داخل _calc_points، مو نتيجة تداول حقيقية:\n\n"
                        f"{lines}{extra}"
                    )
                    notify_admin_telegram(msg)
                    logger.warning(f"Integrity checker: {len(zero_pts_flagged)} zero-points signals flagged")

                # ── 2) صفقات ACTIVE عالقة أطول من المعقول لفريمها ─────────
                active = db.query(Signal).filter(Signal.status == SignalStatus.ACTIVE).all()
                stuck_flagged = []
                for s in active:
                    if not s.created_at:
                        continue
                    created = s.created_at
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    age_hours = (now - created).total_seconds() / 3600.0
                    threshold = min(_stuck_threshold_hours(s.timeframe), STUCK_ABSOLUTE_CAP_HOURS)
                    if age_hours < threshold:
                        continue
                    last_alerted = _stuck_last_alerted.get(s.id)
                    if last_alerted and (now - last_alerted).total_seconds() < STUCK_REALERT_HOURS * 3600:
                        continue
                    stuck_flagged.append((s, age_hours))
                    _stuck_last_alerted[s.id] = now

                if stuck_flagged:
                    lines = "\n".join(
                        f"• #{s.id} <b>{s.market}</b> ({s.timeframe}) — عمرها {age:.0f} ساعة"
                        for s, age in stuck_flagged[:15]
                    )
                    extra = f"\n… و{len(stuck_flagged) - 15} إشارة إضافية" if len(stuck_flagged) > 15 else ""
                    msg = (
                        f"⏰ <b>فحص سلامة الإحصائيات — إشارات عالقة ACTIVE</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"إشارات لسا ACTIVE بعد ما تجاوزت المدة الطبيعية لفريمها —\n"
                        f"على الأغلب outcome-checker ما بيغطي رمزها (تحقق من TV_SYMBOL_MAP):\n\n"
                        f"{lines}{extra}"
                    )
                    notify_admin_telegram(msg)
                    logger.warning(f"Integrity checker: {len(stuck_flagged)} stuck-ACTIVE signals flagged")

            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Integrity checker error: {e}")

    lock_conn.close()
