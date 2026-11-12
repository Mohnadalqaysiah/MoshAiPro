"""
(2026-11-12) ماذا كان سيصل العميل بكل إعداد — سؤال المالك: "حسب دراستنا شو افضل اعداد ممكن يختاره عميل".
للقراءة فقط. يطبّق على القرارات المحسومة الفريدة (كما في التقارير، أعلى هدف أو الوقف) فلاتر العميل نفسها التي يطبّقها
البث (الفريمات، وحد الثقة) ويطبع لكل "ملف إعدادات": كم صفقة تصله، والنجاح، والمجموع والمتوسط بـR، والنصفين، وكل أسبوع.

⚠️ حدود القراءة:
  - الأسهم الأمريكية مستبعدة (موقوفة منذ 11/11 فلا تصل أحداً الآن).
  - إجمالي بلا سبريد (قرار 24/10). الهدف الأول 1R حتى 16/11 — الأرقام بالحساب الحالي لا بحساب 0.7R.
  - مقارنات قليلة ومحددة سلفاً (لا بحث عن أفضل عتبة): الفرق بين ملفين يُقرأ مع النصفين والأسابيع، لا بالمجموع وحده.

    docker exec moshapi_backend python diag_pref_profiles.py [من=2026-10-14]
"""
import sys
from datetime import datetime, timezone

from app.database import SessionLocal
from diag_study import _row

SINCE = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc) if len(sys.argv) > 1 \
    else datetime(2026, 10, 14, tzinfo=timezone.utc)

# (الاسم، الفريمات أو None = الكل، حد الثقة)
PROFILES = [
    ("الكل (الموصى به حالياً)", None, 0),
    ("1h فقط", {"1h"}, 0),
    ("4h فقط", {"4h"}, 0),
    ("1h + 4h (بلا 15m)", {"1h", "4h"}, 0),
    ("ثقة 60%+", None, 60),
    ("ثقة 65%+", None, 65),
    ("ثقة 70%+", None, 70),
    ("ثقة 75%+", None, 75),
    ("ثقة 80%+", None, 80),
    ("1h فقط + ثقة 65%+", {"1h"}, 65),
]


def passes(d, tfs, min_conf):
    """نفس منطق البث: فريم خارج الاختيار لا يصل؛ ثقة أقل من الحد لا تصل (بلا ثقة = تصل، كالبث)."""
    if tfs is not None and (d["timeframe"] or "") not in tfs:
        return False
    c = d.get("confidence")
    return not (min_conf and c is not None and float(c) < min_conf)


def main():
    from app.models.signal import Signal
    from app.services.weekly_markets import closed_decisions
    db = SessionLocal()
    decs = sorted((d for d in closed_decisions(db, SINCE)
                   if d["status"] != "BREAKEVEN" and d["group"] != "stock"), key=lambda d: d["created_at"])
    if not decs:
        print("لا قرارات مغلقة بهذه الفترة")
        return
    conf = dict(db.query(Signal.id, Signal.ai_confidence).filter(Signal.id.in_([d["id"] for d in decs])).all())
    for d in decs:
        d["confidence"] = conf.get(d["id"])

    print(f"ملفات إعدادات العميل من {SINCE:%Y-%m-%d} (بلا الأسهم الأمريكية): {len(decs)} قراراً محسوماً\n")
    print(f"  {'الإعداد':<26} {'عدد':>4} {'رابح/خاسر':>9} {'نجاح':>6} {'المجموع':>9} {'المتوسط':>7}  {'النصفان':<15} أسبوعياً")
    for name, tfs, mc in PROFILES:
        ds = [d for d in decs if passes(d, tfs, mc)]
        print(_row(name, ds) if ds else f"  {name:<26}    0")
    print("\nما يخسره العميل بكل إعداد = مجموع \"الكل\" ناقص مجموعه. الإعداد الأفضل للعميل هو الأعلى مجموعاً"
          " بشرط ألا يكون فرقه من أسبوع واحد.")
    db.close()


if __name__ == "__main__":
    main()
