"""
(2026-10-30) شرط فتح سجل الأداء العام: "أسبوعان ممتازان متتاليان" (DECISIONS 24/10). الممتاز = متوسط الصفقة ≥ +0.40R
و≥ 5 من 8 مجموعات أسواق رابحة (DECISIONS 30/10، معتمد من المالك). للقراءة فقط: لا يكتب شيئاً ولا يفتح الصفحة.

الحكم على آخر أسبوعين مكتملين، والأسبوع الجاري يُعرض ولا يدخله. الأسبوع = أسبوع الصدور، فصفقاته المفتوحة تُعرض بجانبه لأنها
قد تغيّر رقمه بعد القراءة. وبجانبه حكم مبدئي يعدّ الجاري مكتملاً: أسواق الأسبوع تغلق قبل نهايته (سؤال المالك 30/10)، بالعتبات نفسها.

    docker exec moshapi_backend python diag_gate.py
"""
from datetime import datetime, timedelta, timezone


def verdict(weeks, with_current=False):
    """True/False على آخر أسبوعين مكتملين (weekly_table["weeks"])، وNone إن لم يكتمل أسبوعان بعد.
    with_current=True: حكم مبدئي يعدّ الأسبوع الجاري مكتملاً."""
    from app.services.weekly_markets import week_grade
    done = [w for w in weeks if with_current or not w["current"]]
    if len(done) < 2:
        return None
    return all(week_grade(w["cells"])["excellent"] for w in done[-2:])


def open_decisions(db, week) -> int:
    """قرارات الأسبوع التي لم تُغلق بعد — group_unique_decisions لأن القرار الواحد صف لكل مستخدم."""
    from app.models.signal import Signal, SignalStatus
    from app.services.decision_grouping import group_unique_decisions
    start = datetime.fromisoformat(week["from"]).replace(tzinfo=timezone.utc)
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.PENDING, SignalStatus.ACTIVE]),
        Signal.created_at >= start, Signal.created_at < start + timedelta(days=7),
    ).all()
    return len(group_unique_decisions(rows))


def main():
    from app.database import SessionLocal
    from app.services.weekly_markets import EXCELLENT_AVG_R, EXCELLENT_MIN_GROUPS, GROUPS, week_grade, weekly_table

    db = SessionLocal()
    weeks = weekly_table(db, weeks=4)["weeks"]
    print(f"شرط فتح السجل: أسبوعان ممتازان متتاليان (متوسط ≥ +{EXCELLENT_AVG_R:.2f}R و≥ {EXCELLENT_MIN_GROUPS} من {len(GROUPS)} مجموعات رابحة)\n")
    for w in weeks:
        g = week_grade(w["cells"])
        avg = f"{g['avg_r']:+.2f}R" if g["avg_r"] is not None else "—"
        grade = "ممتاز حتى الآن" if g["excellent"] else "دون الحد حتى الآن"
        mark = f"⏳ جارٍ، {grade}" if w["current"] else ("✅ ممتاز" if g["excellent"] else "❌ ليس ممتازاً")
        print(f"{w['week']} (من {w['from']})  {mark}")
        print(f"   الصفقات {g['n']}، المجموع {g['r']:+.2f}R، المتوسط {avg}، المجموعات الرابحة {g['groups_won']}/{len(GROUPS)}، "
              f"المفتوحة {open_decisions(db, w)}")
        cells = [f"{name} {w['cells'][k]['r']:+.1f}R" if k in w["cells"] else f"{name} —" for k, name in GROUPS]
        print("   " + " | ".join(cells))

    words = {True: "✅ الشرط متحقق", False: "❌ الشرط غير متحقق", None: "⏳ لم يكتمل أسبوعان"}
    print("\nالحكم على آخر أسبوعين مكتملين: " + words[verdict(weeks)])
    if weeks and weeks[-1]["current"]:
        print("الحكم المبدئي بعدّ الأسبوع الجاري مكتملاً: " + words[verdict(weeks, with_current=True)])
    print("قرار الفتح وتفعيل سلّم الأهداف للمالك؛ هذه الأداة لا تغيّر شيئاً.")
    db.close()


if __name__ == "__main__":
    main()
