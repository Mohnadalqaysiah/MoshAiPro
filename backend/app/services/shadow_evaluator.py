"""
Mosh AI Pro v5 - Shadow Signal Evaluator (2026-10-12)
=====================================================
يقيّم إشارات الظل (كريبتو عطلة نهاية الأسبوع، راجع weekend_policy.py) من الشموع
الحقيقية ويحفظ النتيجة بالصف نفسه — كل 30 دقيقة.

لماذا آلياً لا وقت المراجعة: أداة التحقق (_verify_signal_outcome_core) تجلب آخر 1000
شمعة 5m (~3.5 أيام)، فإشارة السبت لا يمكن تقييمها بعد أسبوع.

نفس قواعد حلقة الرصد الحية (لا رصد قبل تفعيل الدخول، TP1 ليس نهائياً، الرصد ينتهي
عند expires_at) — لأنها نفس الأداة المستخدمة لتصحيح النتائج سابقاً.
تُحفظ النتيجة فقط حين تكون نهائية: TP2 أو SL، أو انتهت مدة الإشارة.

لا يلمس جدول signals ولا يرسل أي شيء لأي مستخدم.
"""
import asyncio
from datetime import datetime, timezone
from loguru import logger

CHECK_INTERVAL_SEC = 1800
MAX_PER_CYCLE = 60
_LOCK_KEY = 90210006   # 90210001..90210005 مستخدَمة


def _ts(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def evaluate_pending(db) -> int:
    from app.models.shadow_signal import ShadowSignal
    from app.api.admin import _verify_signal_outcome_core

    now = datetime.now(timezone.utc)
    pending = (db.query(ShadowSignal)
                 .filter(ShadowSignal.outcome.is_(None))
                 .order_by(ShadowSignal.created_at)
                 .limit(MAX_PER_CYCLE).all())
    done = 0
    for s in pending:
        try:
            res = await _verify_signal_outcome_core(s)
        except Exception as e:
            logger.warning(f"shadow #{s.id}: {e}")
            continue
        det = res.get("detected")
        exp = s.expires_at if (s.expires_at is None or s.expires_at.tzinfo) else s.expires_at.replace(tzinfo=timezone.utc)
        window_closed = exp is not None and exp <= now
        final = det in ("TP2_HIT", "SL_HIT") or (window_closed and det != "STILL_ACTIVE")
        if det == "NO_DATA" and not window_closed:
            final = False
        if not final:
            continue
        s.outcome = det
        s.r_multiple = res.get("r_multiple")
        s.entry_time = _ts(res.get("entry_time"))
        s.exit_time = _ts(res.get("hit_time"))
        s.evaluated_at = now
        db.commit()
        done += 1
    return done


async def shadow_evaluator():
    from app.database import SessionLocal
    from app.services.worker_lock import try_acquire_singleton_lock

    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Shadow evaluator")
    if lock_conn is None:
        return
    logger.success("✅ Shadow evaluator started")
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            db = SessionLocal()
            try:
                n = await evaluate_pending(db)
                if n:
                    logger.info(f"🌑 Shadow evaluator: {n} إشارة ظل قُيّمت")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Shadow evaluator error: {e}")
    lock_conn.close()
