"""
(2026-10-12) إيقاف إشارات الكريبتو في عطلة نهاية الأسبوع — مع استمرار القياس.

القرار والأرقام في DECISIONS.md (2026-10-12): قاعدة مسجّلة مسبقاً، وفحص
diag_crypto_weekend.py حقّق شرطيها (44 قراراً بالعطلة، متوسط −0.25R، مقابل +0.37R
لنفس الرموز أيام الأسبوع).

ما يحدث بالعطلة (السبت والأحد UTC) لرموز فئة crypto:
  - لا يُنشأ صف Signal → لا بث، لا تنبيه مراقبة، لا إشعار جوال، لا ظهور بأي شاشة أو إحصائية.
  - تُحفظ الإشارة بجدول shadow_signals المنفصل فقط، وتُقيَّم نتيجتها لاحقاً من الشموع
    (diag_shadow_signals.py) — لنعرف بالأرقام هل الإيقاف ما زال صحيحاً.
جدول منفصل عمداً لا علَم بجدول signals: أكثر من 40 استعلاماً بـ9 ملفات تقرأ signals،
وأي استعلام يُنسى كان سيُظهر صفقة داخلية لمشترك أو يُدخلها إحصائياته.

التحليل الفوري الذي يطلبه المستخدم بنفسه يبقى متاحاً (يرى نتيجة المحرك)، لكنه لا يُحفظ كإشارة.
"""
import hashlib
import time
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

CRYPTO_WEEKEND_PAUSE = True   # مفتاح القرار — False يعيد السلوك القديم فوراً

_FALLBACK_CRYPTO = {"BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD", "ADAUSD", "DOGEUSD"}
_cache = {"at": 0.0, "symbols": set()}


def _crypto_symbols(db) -> set:
    if time.time() - _cache["at"] < 600 and _cache["symbols"]:
        return _cache["symbols"]
    try:
        from app.models.market_config import MarketConfig
        rows = db.query(MarketConfig.symbol).filter(MarketConfig.category == "crypto").all()
        syms = {r[0].upper() for r in rows} or _FALLBACK_CRYPTO
    except Exception:
        syms = _FALLBACK_CRYPTO
    _cache.update(at=time.time(), symbols=syms)
    return syms


def is_weekend(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).weekday() >= 5


def crypto_weekend_paused(db, symbol: str, now: Optional[datetime] = None) -> bool:
    if not CRYPTO_WEEKEND_PAUSE or not symbol:
        return False
    return is_weekend(now) and symbol.upper() in _crypto_symbols(db)


def record_shadow(db, *, source: str, symbol: str, timeframe: str, signal_type: str,
                  entry, sl, tp1, tp2=None, confidence=None, rr=None, expires_at=None,
                  user_id: Optional[int] = None, reason: str = "crypto_weekend") -> Optional[int]:
    """يحفظ الإشارة بجدول الظل ويعيد رقمها (لربط بصمة السوق)، أو None إن لم تُحفظ.
    نفس (رمز+فريم+اتجاه+دخول) تُحفظ مرة واحدة — المراقبة الشخصية تكرر نفس الإعداد
    لكل مشترك. لا يرمي استثناء أبداً."""
    try:
        from app.models.shadow_signal import ShadowSignal
        from app.services.shadow_levels import final_levels_valid, LEVELS_VERSION
        # (2026-10-18) لا يُحفظ صف ظل بمستويات غير صالحة — نفس فحص الجهة الحي (shadow_levels.py)، لكل المسارات
        bad = final_levels_valid(signal_type, entry, sl, tp1, tp2)
        if bad:
            logger.info(f"🌑 SHADOW_LEVELS_REJECTED {bad}: {reason} {symbol}/{timeframe} {signal_type} "
                        f"e={entry} sl={sl} tp1={tp1} [{source}]")
            return None
        h = hashlib.md5(f"{reason}-{symbol}-{timeframe}-{signal_type}-{round(float(entry), 4)}".encode()).hexdigest()
        if db.query(ShadowSignal.id).filter(ShadowSignal.signal_hash == h).first():
            return None
        if reason != "crypto_weekend":
            # (2026-10-14) صفقات مرفوضة: الماسح يعيد نفس الفكرة كل دورة بسعر مختلف قليلاً — صفقة ظل مفتوحة
            # واحدة لكل (سبب، رمز، فريم، اتجاه) كما يفعل النظام الحي (_has_active_signal)، وإلا تضخّمت العينة.
            now = datetime.now(timezone.utc)
            if db.query(ShadowSignal.id).filter(
                ShadowSignal.reason == reason[:60], ShadowSignal.market == symbol.upper(),
                ShadowSignal.timeframe == timeframe, ShadowSignal.signal_type == signal_type,
                ShadowSignal.outcome.is_(None), ShadowSignal.expires_at > now,
            ).first():
                return None
        sh = ShadowSignal(
            source=source, market=symbol.upper(), timeframe=timeframe, signal_type=signal_type,
            entry_price=float(entry), stop_loss=float(sl), take_profit_1=float(tp1),
            take_profit_2=float(tp2 or tp1), ai_confidence=float(confidence or 0),
            risk_reward_ratio=float(rr) if rr else None, expires_at=expires_at,
            user_id=user_id, signal_hash=h, reason=reason[:60], levels_version=LEVELS_VERSION,
        )
        db.add(sh)
        db.commit()
        logger.info(f"🌑 Shadow ({reason}): {symbol}/{timeframe} {signal_type} @ {entry} [{source}]")
        return sh.id
    except Exception as e:
        db.rollback()
        logger.warning(f"record_shadow: {e}")
        return None
