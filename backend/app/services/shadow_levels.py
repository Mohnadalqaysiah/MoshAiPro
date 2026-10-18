"""
shadow_levels.py (2026-10-18) — التحقق من مستويات صفقات الظل قبل حفظها.

لماذا: تدقيق 18/10 (diag_shadow_audit، DECISIONS.md) وجد 299 من 793 صفقة ظل بمستويات معكوسة — اتجاه الرفض
(resolved، ai_engine_v5.py:2140) يخالف الاتجاه الذي بنى عليه محرك ICT المستويات (ict_engine.py:1262)، فيُحسب
"وقف" فور الدخول. HTF وZONE بدتا قاعدتين تمنعان خاسرات بسبب ذلك وحده.

القرار: **لا تُعاد صياغة المستويات** للاتجاه الآخر — الصفقة الحية تمر بفحص الجهة في _institutional_gate
(Rule 6، ai_engine_v5.py:2531-2552) فترفض أي صفقة وقفها أو هدفها الأول بالجهة الخطأ؛ أي أن الصفقة المعكوسة لم تكن
لتُرسل أبداً حتى لو أُزيلت القاعدة. مستويات مُخترعة كانت ستقيس استراتيجية لا ينتجها المحرك.
فتُطبَّق هنا القاعدة الحية **حرفياً** (نفس السماحية 0.0001، ونفس تبديل TP1/TP2)، والصفقة التي تفشل لا تُحفظ.

لا يُستدعى من أي مسار يرسل إشارة — فقط من مسار تسجيل الظل.
"""
from typing import Optional, Tuple

LEVELS_VERSION = 1          # يُخزَّن بكل صف ظل جديد؛ NULL = قبل هذا الإصلاح (بيانات متأثرة)
_TOL = 0.0001               # نفس سماحية _institutional_gate (entry * 0.9999 / 1.0001)


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_rejected_levels(side: str, levels: dict) -> Tuple[Optional[dict], Optional[str]]:
    """مستويات خام (قبل _cap_tp1) لاتجاه side → (نسخة صالحة، None) أو (None، سبب الرفض).

    مطابق لـ_institutional_gate Rule 6 بنفس الترتيب:
      MISSING_ENTRY_PRICE ← BUY_SL_ABOVE_ENTRY / SELL_SL_BELOW_ENTRY ← BUY_TP1_BELOW_ENTRY / SELL_TP1_ABOVE_ENTRY
      ← تبديل TP1/TP2 إن انعكس ترتيبهما ← ZERO_SL_DISTANCE.
    إضافة واحدة أشد من الحي: بعد التبديل يُعاد فحص جهة TP1 (الحي لا يعيده) — لا تُحفظ صفقة هدفها بالجهة الخطأ.
    وغياب الوقف/الهدف (يمرّره الحي لأن شرطه sl > 0) يُرفض هنا: صفقة ظل بلا وقف لا يمكن تقييمها.
    """
    if side not in ("BUY", "SELL"):
        return None, "INVALID_SIDE"
    lv = dict(levels or {})
    entry, sl = _f(lv.get("entry")), _f(lv.get("stop_loss"))
    tp1, tp2 = _f(lv.get("tp1")), _f(lv.get("tp2"))
    if not entry:
        return None, "MISSING_ENTRY_PRICE"
    if not sl or not tp1:
        return None, "MISSING_SL_OR_TP1"
    if side == "BUY":
        if sl >= entry * (1 - _TOL):
            return None, "BUY_SL_ABOVE_ENTRY"
        if tp1 <= entry * (1 + _TOL):
            return None, "BUY_TP1_BELOW_ENTRY"
        if tp2 and tp1 > tp2:
            tp1, tp2 = tp2, tp1
            if tp1 <= entry * (1 + _TOL):
                return None, "BUY_TP1_BELOW_ENTRY_AFTER_SWAP"
    else:
        if sl <= entry * (1 + _TOL):
            return None, "SELL_SL_BELOW_ENTRY"
        if tp1 >= entry * (1 - _TOL):
            return None, "SELL_TP1_ABOVE_ENTRY"
        if tp2 and tp1 < tp2:
            tp1, tp2 = tp2, tp1
            if tp1 >= entry * (1 - _TOL):
                return None, "SELL_TP1_ABOVE_ENTRY_AFTER_SWAP"
    if abs(entry - sl) <= 0:
        return None, "ZERO_SL_DISTANCE"
    lv["tp1"] = tp1
    lv["tp2"] = tp2 or None
    return lv, None


def final_levels_valid(side: str, entry, sl, tp1, tp2=None) -> Optional[str]:
    """فحص دفاعي للمستويات النهائية قبل الحفظ (بعد _cap_tp1) — None = صالحة، وإلا سبب الرفض.
    TP2 غائب أو قبل TP1 مقبول (يعني لا هدف ثانٍ، والمقيّم يتجاهله: has_tp2 بـadmin.py:1918).

    (2026-10-18، المرحلة 1.1) جهات صارمة **بلا سماحية**: السماحية 0.0001 جزء من Rule 6 الحي الذي يعمل **قبل**
    _cap_tp1 (وطُبّقت هنا في normalize_rejected_levels). بعد السقف يقع TP1 على 1R، ومع وقف أصغر من 0.01% من السعر
    (شائع بقاعدة SL_INSIDE_SPREAD_NOISE) كانت السماحية ترفض صفقة لا يرفضها الحي — 6 من 91 بالبيانات (القسم G)، وهي
    أضيق الوقوف بالذات، أي تحيّز بعيّنة قاعدة السبريد. الفحص هنا يمنع المعكوسة فقط، لا يعيد تطبيق Rule 6."""
    if side not in ("BUY", "SELL"):
        return "INVALID_SIDE"
    e, s, t1 = _f(entry), _f(sl), _f(tp1)
    if not e or not s or not t1:
        return "MISSING_LEVELS"
    if side == "BUY":
        if s >= e:
            return "BUY_SL_ABOVE_ENTRY"
        if t1 <= e:
            return "BUY_TP1_BELOW_ENTRY"
    else:
        if s <= e:
            return "SELL_SL_BELOW_ENTRY"
        if t1 >= e:
            return "SELL_TP1_ABOVE_ENTRY"
    return None
