"""
(2026-11-14) مقاييس "ما يعيشه العميل" — مشتركة بين diag_client_experience.py وأرقام باقات التخصص (recommended_prefs.py).
المجموع بـR يقيس المنصة؛ العميل يعيش يومه: كم إشارة تصله، كم منها رابحة، كم يوماً انتهى رابحاً، وأسوأ يوم.
اليوم = يوم إنشاء الإشارة (UTC)، والسلسلة بترتيب الإنشاء.
"""
from collections import defaultdict


def experience(decs, days):
    """decs مرتبة زمنياً (created_at، r). None إن لم تكن صفقات."""
    n = len(decs)
    if not n:
        return None
    rs = [d["r"] for d in decs]
    by_day = defaultdict(float)
    sl_day = defaultdict(int)
    for d in decs:
        by_day[d["created_at"].date()] += d["r"]
        if d["r"] < 0:
            sl_day[d["created_at"].date()] += 1
    streak = best = 0
    for r in rs:
        streak = streak + 1 if r < 0 else 0
        best = max(best, streak)
    neg_days = sum(1 for v in by_day.values() if v < 0)
    return {"n": n, "per_day": n / days, "win": 100 * sum(r > 0 for r in rs) / n, "tot": sum(rs), "avg": sum(rs) / n,
            "worst_day": min(by_day.values()), "neg_days": 100 * neg_days / len(by_day),
            "pos_days": 100 * sum(1 for v in by_day.values() if v > 0) / len(by_day),
            "sl_day": sum(sl_day.values()) / days, "max_sl_day": max(sl_day.values(), default=0), "streak": best}
