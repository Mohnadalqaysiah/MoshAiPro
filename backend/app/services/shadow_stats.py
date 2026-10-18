"""
shadow_stats.py (2026-10-18، المرحلة 2) — قراءة صفقات الظل بطريقة واحدة لكل التقارير (تبويب الأدمن، diag_review).

لماذا: تدقيق 18/10 أثبت أن التبويب وأداة المراجعة كانا يقرآن الجدول كما هو، فقلبا الحكم على HTF وZONE
(مستويات معكوسة 254 من 797) وضخّما العيّنة (797 صفاً = 557 فرصة) وأهملا السبريد. هنا القواعد الثلاث:

  1) نظيف فقط افتراضياً: صف الظل النظيف = levels_version غير فارغ (مرّ بفحص الجهة، shadow_levels.py)، أو صف قالب
     (tpl:) — القوالب لم تتأثر بالعطل (مستوياتها من trade_levels بالباكتيست). القديم يبقى بالجدول بلا تعديل.
  2) الفرصة المستقلة لا الصف: داخل نفس السبب، صفوف نفس (الرمز، الاتجاه) خلال ساعتين والدخول ضمن ±0.3% = فرصة واحدة
     (نفس الفكرة على 15m و1h مثلاً). يمثّلها **أقدم صف** — اختيار لا يعتمد على النتيجة، فلا انتقاء.
  3) R بعد السبريد بجانب الإجمالي: تكلفة الصفقة = سبريد spread_table ÷ |الدخول − الوقف| (نفس طريقة الباكتيست).
     **تقدير من جدول ثابت، لا قياس** — لا bid/ask مخزّن بأي جدول. صفوف القوالب R فيها صافٍ أصلاً (الباكتيست يخصمه).

الحد الأدنى قبل أي "حكم": 30 فرصة مستقلة محسومة (نفس رقم القواعد المسجّلة مسبقاً بـdiag_review).
"""
from datetime import timedelta
from typing import Dict, List, Optional

DECIDED = ("TP1_HIT", "TP2_HIT", "SL_HIT", "TP1_BE", "EXPIRED_TP1")
LOSS = ("SL_HIT",)
MIN_INDEPENDENT = 30
CLUSTER_WINDOW = timedelta(hours=2)
CLUSTER_ENTRY_PCT = 0.003


def is_template(s) -> bool:
    return (s.reason or "").startswith("tpl:")


def is_clean(s) -> bool:
    return is_template(s) or getattr(s, "levels_version", None) is not None


def filter_scope(rows: list, scope: str) -> list:
    """scope: clean (افتراضي) | legacy (قبل إصلاح المستويات) | all."""
    if scope == "all":
        return list(rows)
    if scope == "legacy":
        return [s for s in rows if not is_clean(s)]
    return [s for s in rows if is_clean(s)]


def _aware(d):
    from datetime import timezone
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _still_open_at(rep, t) -> bool:
    """هل كانت صفقة الممثّل ما زالت مفتوحة لحظة t؟ صفقة جديدة بعد إغلاق الأولى فكرة مستقلة لا تكرار."""
    end = _aware(rep.exit_time) or _aware(rep.expires_at)
    return end is None or t <= end


def opportunities(rows: list) -> List[list]:
    """صفوف سبب واحد → قائمة فرص، كل فرصة قائمة صفوف مرتبة زمنياً وأولها الممثّل.
    تكرار = نفس (الرمز، الاتجاه)، خلال ساعتين من الممثّل، والدخول ضمن ±0.3%، **والممثّل ما زال مفتوحاً**.
    القوالب لا تُجمَّع: صفقة واحدة مفتوحة لكل قالب بالبناء (template_shadow.busy_until)."""
    if rows and is_template(rows[0]):
        return [[s] for s in sorted(rows, key=lambda s: _aware(s.created_at))]
    srt = sorted(rows, key=lambda s: (s.market or "", s.signal_type or "", _aware(s.created_at)))
    out, cur = [], []
    for s in srt:
        t = _aware(s.created_at)
        if cur and cur[0].market == s.market and cur[0].signal_type == s.signal_type \
                and t - _aware(cur[0].created_at) <= CLUSTER_WINDOW and _still_open_at(cur[0], t) \
                and abs(float(s.entry_price) - float(cur[0].entry_price)) <= CLUSTER_ENTRY_PCT * float(cur[0].entry_price):
            cur.append(s)
        else:
            if cur:
                out.append(cur)
            cur = [s]
    if cur:
        out.append(cur)
    return out


def spread_cost_r(s) -> Optional[float]:
    from app.services.spread_table import typical_spread
    risk = abs(float(s.entry_price or 0) - float(s.stop_loss or 0))
    sp = typical_spread(s.market, float(s.entry_price or 0))
    if not risk or sp is None:
        return None
    return sp / risk


def net_r(s) -> Optional[float]:
    """R بعد السبريد. القوالب: R صافٍ أصلاً. رمز بلا سبريد بالجدول: None (لا تقدير)."""
    if s.r_multiple is None:
        return None
    if is_template(s):
        return float(s.r_multiple)
    c = spread_cost_r(s)
    return None if c is None else float(s.r_multiple) - c


def summarize(rows: list) -> Dict:
    """ملخّص سبب واحد على الفرص المستقلة (الممثّلون)، مع أعداد الصفوف للشفافية."""
    opps = opportunities(rows)
    reps = [o[0] for o in opps]
    dec = [s for s in reps if s.outcome in DECIDED and s.r_multiple is not None]
    gross = [float(s.r_multiple) for s in dec]
    nets = [net_r(s) for s in dec]
    nets_ok = [x for x in nets if x is not None]
    tpl = bool(rows) and is_template(rows[0])
    losses = sum(1 for s in dec if s.outcome in LOSS)
    n = len(dec)
    out = {
        "rows": len(rows),
        "rows_pending": sum(1 for s in rows if s.outcome is None),
        "opportunities": len(opps),
        "duplicates": len(rows) - len(opps),
        "decided": n,
        "wins": n - losses,
        "losses": losses,
        "win_rate": round(100 * (n - losses) / n, 1) if n else None,
        "r_gross": None if tpl else round(sum(gross), 2),
        "avg_gross": None if (tpl or not n) else round(sum(gross) / n, 3),
        "r_net": round(sum(nets_ok), 2) if nets_ok else None,
        "avg_net": round(sum(nets_ok) / len(nets_ok), 3) if nets_ok else None,
        "net_missing_spread": len(nets) - len(nets_ok),
        "min_required": MIN_INDEPENDENT,
    }
    out["verdict"], out["verdict_label"] = _verdict(out, tpl)
    return out


def _verdict(b: Dict, tpl: bool):
    n = b["decided"]
    if n == 0:
        return "no_data", "لا نتائج بعد"
    if n < MIN_INDEPENDENT:
        return "insufficient", f"عيّنة غير كافية ({n}/{MIN_INDEPENDENT} فرصة مستقلة) — لا حكم"
    a = b["avg_net"]
    if a is None:
        return "no_spread", "لا سبريد بالجدول لهذه الرموز — لا حكم"
    if tpl:
        return ("positive", "القالب رابح بعد السبريد — مؤشر، الحكم بقواعد المراجعة") if a > 0 else \
               ("negative", "القالب خاسر بعد السبريد")
    return ("blocks_losers", "المنع يبدو صحيحاً بعد السبريد — مؤشر، الحكم بقواعد المراجعة") if a < 0 else \
           ("blocks_winners", "المنع قد يحجب رابحات بعد السبريد — يُفحص بالنصفين بالمراجعة")


def representatives(rows: list) -> list:
    """ممثّل كل فرصة، مرتبة زمنياً — لقواعد المراجعة (النصفان بالترتيب الزمني)."""
    return sorted((o[0] for o in opportunities(rows)), key=lambda s: _aware(s.created_at))
