"""
تخفيف جزئي لفلتر "بيع في منطقة خصم" (2026-10-24، قرار المالك "نفّذ الإيقاف الجزئي")
==================================================================================
الدليل (diag_review + diag_relax_check، 24/10): 121 فرصة ظل نظيفة، 74% رابحة، +0.53R (ضعف متوسط المنصة +0.26R)، موجبة
بالنصفين؛ القديمة السليمة من أسابيع سابقة تؤكد (55 فرصة، +0.60R)؛ منتشر (فوركس +0.54R، معادن +0.63R، كريبتو +0.33R،
بدون أكبر رمز +0.49R). **لكن** إطار 4 ساعات خاسر (12 فرصة، 42%، −0.07R) ← التخفيف على 15m و1h فقط.

القاعدة:
- SELL في منطقة خصم (zone_bias=BUY بـ_decision_finalizer) على إطار ضمن RELAX_SELL_IN_DISCOUNT_TFS ← لا يُرفض، ويُوسم
  analysis["relaxed_rule"]="SELL_IN_DISCOUNT"، وتتجاوزه فحوص المنطقة الثلاثة اللاحقة (Rule 2/6/7 بـ_output_safety_gate)
  **للموسوم فقط** — أي نفس الصفقات التي قاسها الظل لا أوسع. بقية فحوص المحرك كلها نافذة كما هي.
- لا تُحفظ/تُرسل إن كانت للمنصة صفقة نشطة **بعكس الاتجاه** على نفس الرمز (أي فريم) — لا إشارتان متضادتان للعميل.
- تُوسم بعمود signals.relaxed_rule للقياس الأسبوعي (diag_relax_check، قسم "الصفقات الحية").
- الرجوع الفوري بلا إعادة بناء: RELAX_SELL_IN_DISCOUNT_TFS= (فارغ) بـbackend/.env.prod ثم إعادة إنشاء الحاوية.

قاعدة الرجوع (مسجّلة قبل رؤية أي نتيجة حية — DECISIONS 24/10): يُعاد الفلتر إن خسرت الصفقات الموسومة أسبوعين متتاليين،
أو كان متوسطها < 0R بعد 30 صفقة محسومة. مراجعة أولى 30/10 بقرار المالك.
"""
from datetime import datetime, timezone

from app.config import get_settings

RELAX_TAG = "SELL_IN_DISCOUNT"
RELAX_START = datetime(2026, 10, 24, tzinfo=timezone.utc)


def relaxed_timeframes() -> set:
    raw = getattr(get_settings(), "RELAX_SELL_IN_DISCOUNT_TFS", "") or ""
    return {t.strip().lower() for t in raw.split(",") if t.strip()}


def allows_sell_in_discount(timeframe: str) -> bool:
    return (timeframe or "").lower() in relaxed_timeframes()


def is_relaxed(analysis: dict) -> bool:
    return (analysis or {}).get("relaxed_rule") == RELAX_TAG


def opposite_active(db, symbol: str, rec: str) -> bool:
    """صفقة منصة نشطة (غير منتهية) على نفس الرمز بعكس الاتجاه — أي فريم."""
    from app.models.signal import Signal, SignalStatus, SignalType
    if rec not in ("BUY", "SELL"):
        return False
    opposite = SignalType.BUY if rec == "SELL" else SignalType.SELL
    now = datetime.now(timezone.utc)
    return db.query(Signal.id).filter(
        Signal.market == symbol,
        Signal.signal_type == opposite,
        Signal.status == SignalStatus.ACTIVE,
        (Signal.expires_at.is_(None)) | (Signal.expires_at > now),
    ).first() is not None


def should_drop(db, analysis: dict, symbol: str) -> bool:
    """صفقة مخفَّفة تتعارض مع صفقة منصة نشطة ← لا تُحفظ ولا تُرسل."""
    return is_relaxed(analysis) and opposite_active(db, symbol, analysis.get("recommendation"))
