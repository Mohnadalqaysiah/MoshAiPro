"""
(2026-10-27) دراسة ما قبل مراجعة 30/10 — طلب المالك: "خلينا نراجع شوية امور واشارات ومحركات وندرسها لحين قدوم الموعد".
للقراءة فقط — لا تعدّل شيئاً، ولا تصدر أحكاماً. تقسّم القرارات المغلقة (فريدة، كما في التقارير) حسب أبعاد كثيرة:
العدد، الرابح/الخاسر، نسبة النجاح، **مجموع R** والمتوسط، والنصفان، وكل أسبوع.

⚠️ حدود القراءة:
  - البداية الافتراضية 2026-10-14 (TP1 = 1R منذها — ما قبلها R بشكل مختلف فلا يُخلط).
  - تقسيم بأبعاد كثيرة = مقارنات كثيرة: بعض الشرائح ستبدو سيئة أو ممتازة بالصدفة. أي ملاحظة هنا **مرشّح لتسجيله** قبل مراجعة
    لاحقة، لا قراراً. الوسم 🔎 يستخدم نفس عتبات القاعدة (1) المسجّلة (ن ≥ 30، < −0.3R، سالب بالنصفين) للتنبيه فقط.
  - الأرقام إجمالية (بلا سبريد) — قرار المالك 24/10.

    docker exec moshapi_backend python diag_study.py [من=2026-10-14]
"""
import sys
from datetime import datetime, timezone

from app.database import SessionLocal

SINCE = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc) if len(sys.argv) > 1 \
    else datetime(2026, 10, 14, tzinfo=timezone.utc)
DAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def _session(h):
    return "آسيا 00-07" if h < 7 else "لندن 07-12" if h < 12 else "نيويورك 12-17" if h < 17 else "مساءً 17-24"


def _conf(c):
    if c is None:
        return "بلا ثقة"
    c = float(c)
    return "<50" if c < 50 else "50-59" if c < 60 else "60-69" if c < 70 else "70-79" if c < 80 else "80+"


def _rr(d):
    risk = abs(d["entry"] - d["stop_loss"]) or 1e-12
    r2 = abs((d["tp2"] or d["entry"]) - d["entry"]) / risk
    return "TP2 <2R" if r2 < 2 else "TP2 2-3R" if r2 < 3 else "TP2 3-5R" if r2 < 5 else "TP2 5-8R" if r2 < 8 else "TP2 ≥8R"


def _row(name, ds):
    rs = [d["r"] for d in ds]
    n = len(rs)
    w = sum(1 for r in rs if r > 0)
    tot = sum(rs)
    avg = tot / n
    h = n // 2
    halves = f"{sum(rs[:h]) / h:+.2f} ← {sum(rs[h:]) / (n - h):+.2f}" if n >= 10 else "—"
    flag = " 🔎" if n >= 30 and avg < -0.3 and n >= 10 and sum(rs[:h]) < 0 and sum(rs[h:]) < 0 else ""
    wk = {}
    for d in ds:
        k = d["created_at"].isocalendar()[1]
        wk[k] = wk.get(k, 0.0) + d["r"]
    weeks = " ".join(f"W{k}:{v:+.1f}" for k, v in sorted(wk.items()))
    return (f"  {name[:26]:<26} {n:>4} {w:>4}/{n - w:<4} {100 * w / n:>5.0f}% {tot:>+8.1f}R {avg:>+6.2f}R  "
            f"{halves:<15} {weeks}{flag}")


def main():
    from app.models.signal import Signal
    from app.services.weekly_markets import closed_decisions
    db = SessionLocal()
    decs = sorted((d for d in closed_decisions(db, SINCE) if d["status"] != "BREAKEVEN"), key=lambda d: d["created_at"])
    if not decs:
        print("لا قرارات مغلقة بهذه الفترة")
        return
    extra = {s.id: s for s in db.query(Signal).filter(Signal.id.in_([d["id"] for d in decs])).all()}
    for d in decs:
        s = extra.get(d["id"])
        d["confidence"] = getattr(s, "ai_confidence", None)
        d["quality"] = getattr(getattr(s, "signal_quality", None), "value", getattr(s, "signal_quality", None))
        d["killzone"] = getattr(s, "killzone", None)
        d["relaxed"] = getattr(s, "relaxed_rule", None)

    tot = sum(d["r"] for d in decs)
    print(f"دراسة من {SINCE:%Y-%m-%d}: {len(decs)} قراراً محسوماً، مجموع {tot:+.1f}R، متوسط {tot / len(decs):+.3f}R\n")
    head = f"  {'الشريحة':<26} {'عدد':>4} {'رابح/خاسر':>9} {'نجاح':>6} {'المجموع':>9} {'المتوسط':>7}  {'النصفان':<15} أسبوعياً"

    dims = [
        ("مجموعة السوق", lambda d: d["group"] or "?"),
        ("الرمز (10+ قرارات)", lambda d: d["market"]),
        ("الفريم", lambda d: d["timeframe"] or "?"),
        ("الاتجاه", lambda d: d["side"]),
        ("المجموعة × الاتجاه", lambda d: f"{d['group']} {d['side']}"),
        ("الجلسة (توقيت UTC)", lambda d: _session(d["created_at"].hour)),
        ("يوم الأسبوع", lambda d: DAYS_AR[d["created_at"].weekday()]),
        ("Premium/Discount", lambda d: d["premium_discount"] or "?"),
        ("Killzone", lambda d: d["killzone"] or "?"),
        ("جودة الإشارة", lambda d: d["quality"] or "?"),
        ("الثقة", lambda d: _conf(d["confidence"])),
        ("بُعد الهدف الثاني", _rr),
        ("قاعدة مخفَّفة (24/10)", lambda d: d["relaxed"] or "عادية"),
    ]
    for title, key in dims:
        groups = {}
        for d in decs:
            groups.setdefault(str(key(d)), []).append(d)
        items = sorted(groups.items(), key=lambda kv: sum(x["r"] for x in kv[1]))
        if title.startswith("الرمز"):
            items = [kv for kv in items if len(kv[1]) >= 10]
        print("═" * 110 + f"\n{title}\n" + head)
        for name, ds in items:
            print(_row(name, ds))
        print()
    print("🔎 = نفس عتبات القاعدة (1) المسجّلة — تنبيه للدراسة فقط. مقارنات كثيرة ← بعض الشرائح متطرفة بالصدفة.\n"
          "أي فكرة من هنا تُسجَّل قاعدتها أولاً ثم تُختبر صامتة على بيانات جديدة — لا تُطبَّق من هذا التقرير.")
    db.close()


if __name__ == "__main__":
    main()
