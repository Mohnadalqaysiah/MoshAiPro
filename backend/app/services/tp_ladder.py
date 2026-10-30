"""
سلّم الأهداف الثلاثة (2026-10-30، قرار المالك "نعم ابني كل شيء") — DECISIONS.md 30/10.

الهدف الأول كما هو (1R، _cap_tp1)، والهدف البعيد إن تجاوز 2.5R ينقسم: **الثاني عند 2.5R والبعيد يصير ثالثاً**. وإن كان البعيد
≤ 2.5R تبقى الصفقة بهدفين كما كانت.

القياس: أعلى هدف بلغته الصفقة أو الوقف (مقياس المنصة). بعد الهدف الثاني تبقى تحت الرصد حتى الثالث أو الوقف أو انتهاء المدة،
ويبقى الهدف الثاني مقفلاً، تماماً كما يُقفل الأول قبله.

**لماذا لا حالة TP3_HIT جديدة:** الحالة TP2_HIT تقرأها ~90 موضعاً (إحصاءات، تقارير، بوت، موقع). حالة جديدة يفوتها موضع واحد =
صفقة رابحة تختفي من الأرقام بصمت. الهدف الثالث عمودان (take_profit_3، tp3_hit_at) فوق TP2_HIT: أي موضع لم يُحدَّث يعدّها
2.5R بدل البعيد — خطأ بتحفّظ لا اختفاء. مجموع R يمر من Signal.final_tp.

**معطّل افتراضياً:** يُنشر الكود أي وقت بلا أثر، ويتفعّل بـTP_LADDER_ENABLED=1 بـbackend/.env.prod ثم force-recreate للخادم، حتى لا يبدأ
أثناء قراءة أسبوع. الرجوع: حذف السطر ثم force-recreate — الصفقات المفتوحة تكمل رصدها، والجديدة بهدفين.
لا يمس الظل والقوالب والباكتيست: تبقى بهدفين عمداً لتبقى مقارنتها بما قبلها صالحة.

**المفتاح ladder_tp3 لا tp3:** المحرك ينتج levels["tp3"] من زمان (ict_engine، gemini) ولا يرصده أحد. قراءة هذا الاسم حفظت هدفاً قديماً
لصفقات حقيقية والسلّم معطّل (نشر 30/10). كل من يحفظ الهدف الثالث أو يعرضه يقرأ ladder_tp3 وحده.
"""
import os
from typing import Optional, Tuple

from sqlalchemy import and_

LADDER_TP2_R = 2.5


def ladder_enabled() -> bool:
    return os.getenv("TP_LADDER_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def split_far_target(entry: float, sl: float, tp1: float, tp2: Optional[float], is_buy: bool) -> Optional[Tuple[float, float]]:
    """يعيد (الهدف الثاني الجديد، الهدف الثالث) إن كان البعيد أبعد من 2.5R، وإلا None (تبقى الأهداف كما هي)."""
    risk = abs(entry - sl)
    if not risk:
        return None
    sgn = 1 if is_buy else -1
    far = tp2 if tp2 is not None and sgn * (tp2 - tp1) > 0 else tp1
    if sgn * (far - entry) / risk <= LADDER_TP2_R:
        return None
    mid = entry + sgn * LADDER_TP2_R * risk
    if sgn * (mid - tp1) <= 0:                      # هدف أول أبعد من 2.5R (ليس حال TP1=1R) — لا سلّم معكوس
        return None
    return round(mid, 5), round(far, 5)


def tp3_open_clause(signal_cls):
    """صف بلغ الهدف الثاني وما زال ينتظر الثالث — يُعامل كصفقة مفتوحة."""
    from app.models.signal import SignalStatus
    return and_(signal_cls.status == SignalStatus.TP2_HIT, signal_cls.take_profit_3.isnot(None),
                signal_cls.tp3_hit_at.is_(None))
