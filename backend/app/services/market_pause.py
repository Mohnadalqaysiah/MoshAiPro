"""
(2026-11-11، قرار المالك "نعم ايقاف صامت") إيقاف صامت لإشارات الأسهم الأمريكية — DECISIONS 11/11.

لماذا: جدول الأسبوع × السوق (مقياس المالك): الأسهم الأمريكية خاسرة 4 أسابيع متتالية — W43 −5R، W44 −5R، W45 −2R، W46 −4R
(حتى 11/11): 24 صفقة، ‎−16R، ‎−0.67R للصفقة، ~17% ربح. قاعدة المراقبة (1) المسجّلة 27/10 (< −0.3R عند 15 قراراً جديداً)
كانت ~12/15 بمتوسط أسوأ من الحد بأكثر من الضعف؛ أوقفها المالك قبل اكتمال العدد.

ما يحدث: إشارة أي رمز فئته "stock" بجدول الأسواق (MarketConfig) تُسجَّل بجدول الظل (reason=US_STOCKS_PAUSE) بدل صف
Signal — لا بث ولا تنبيه ولا إحصائية، كإيقاف 15m وكريبتو العطلة. التحليل الذي يطلبه المستخدم بنفسه يبقى ظاهراً له.
الأسهم الخليجية فئة "gulf" فلا تتأثر. الإيقاف بالفئة لا بقائمة رموز: سهم أمريكي يُضاف لاحقاً يُوقف تلقائياً.

الإعادة بقاعدة مسجّلة قبل الإيقاف: diag_watch (12). الإيقاف الطارئ: PAUSE_US_STOCKS=0 بـbackend/.env.prod ثم إعادة تشغيل الخادم.
"""
import os
import time
from datetime import datetime, timezone

REASON = "US_STOCKS_PAUSE"
PAUSE_START = datetime(2026, 11, 12, tzinfo=timezone.utc)   # بداية بيانات قاعدة الإعادة (12)
_FALLBACK = {"AMD", "NFLX", "AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "META", "AMZN"}
_cache = {"at": 0.0, "symbols": set()}


def enabled() -> bool:
    return os.getenv("PAUSE_US_STOCKS", "1").strip().lower() not in ("0", "false", "no", "off")


def _stock_symbols(db) -> set:
    if time.time() - _cache["at"] < 600 and _cache["symbols"]:
        return _cache["symbols"]
    syms = set()
    try:
        from app.models.market_config import MarketConfig
        syms = {r[0].upper() for r in db.query(MarketConfig.symbol).filter(MarketConfig.category == "stock").all()}
    except Exception:
        db.rollback() if hasattr(db, "rollback") else None
    syms = syms | _FALLBACK
    _cache.update(at=time.time(), symbols=syms)
    return syms


def stocks_paused(db, symbol: str) -> bool:
    """True = لا صف Signal لهذه الإشارة، بل صف ظل."""
    if not enabled() or not symbol:
        return False
    return symbol.replace("/", "").upper() in _stock_symbols(db)
