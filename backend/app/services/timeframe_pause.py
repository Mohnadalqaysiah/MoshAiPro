"""
(2026-11-07، قرار المالك "بختار ب") إيقاف تجريبي صامت لإشارات فريم 15m، عدا الذهب والمعادن — DECISIONS 07/11.

لماذا: قاعدة المراقبة (2) المسجّلة 27/10 تحققت على بيانات ما بعد 28/10: 15m ن=75، −0.04R (بعد السبريد −0.21R) مقابل 1h +0.56R،
و46 من 127 خسارة. داخل 15m: الذهب والمعادن موجبان (+0.91R على 20)، والباقي سالب. الاستثناء اختير بعد رؤية الأرقام، فتراقبه
القاعدة (10) بـdiag_watch.

ما يحدث: إشارة 15m لسوق غير مستثنى تُسجَّل بجدول الظل (reason=TF15M_PAUSE) بدل صف Signal — لا بث، ولا تنبيه مراقبة، ولا
إشعار، ولا إحصائية — تماماً كإيقاف كريبتو العطلة (weekend_policy.py). التحليل الذي يطلبه المستخدم بنفسه يبقى ظاهراً له.
كريبتو العطلة يُفحص قبله، فيبقى قياسه كما كان.

الإعادة بقاعدة مسجّلة مسبقاً (diag_watch (9)). الإيقاف الطارئ: PAUSE_15M=0 بـbackend/.env.prod ثم force-recreate للخادم.
"""
import os
from datetime import datetime, timezone

PAUSED_TIMEFRAME = "15m"
EXEMPT_GROUPS = {"gold", "metals"}
REASON = "TF15M_PAUSE"
PAUSE_START = datetime(2026, 11, 8, tzinfo=timezone.utc)   # بداية بيانات قاعدتي (9) و(10)


def enabled() -> bool:
    return os.getenv("PAUSE_15M", "1").strip().lower() not in ("0", "false", "no", "off")


def allowed_pref_timeframes(tfs) -> list:
    """(2026-11-09، طلب المالك) تفضيلات الفريمات لا تقبل 15m وهو موقوف — من اختاره صار "كل الفريمات" (migrate_15m_prefs.py)."""
    tfs = [t for t in (tfs or []) if t != "all"]
    return [t for t in tfs if t != PAUSED_TIMEFRAME] if enabled() else tfs


def tf_paused(symbol: str, timeframe: str) -> bool:
    """True = لا صف Signal لهذه الإشارة، بل صف ظل. الاستثناء بالرمز وحده (weekly_markets: الذهب والمعادن)، فلا يحتاج قاعدة البيانات."""
    if not enabled() or timeframe != PAUSED_TIMEFRAME or not symbol:
        return False
    from app.services.weekly_markets import market_group
    return market_group(symbol.replace("/", "").upper(), "") not in EXEMPT_GROUPS
