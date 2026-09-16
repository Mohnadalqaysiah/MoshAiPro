"""
baseline_close_speed.py
==========================
قراءة محضة — لا يعدّل صفاً ولا يمسّ المحرك.

الغرض: تثبيت خط أساس قبل أن يُنتج إصلاح 16/09 (d84ad25) أثره، حتى
يكون الحكم على الإصلاح لاحقاً بمقارنة مقاسة لا بانطباع.

ما يقيسه وعلاقته بالإصلاح:

 1) سرعة الإغلاق. الإغلاق الكاذب الناتج عن اختلاف مرجعَي السعر له
    بصمة مميزة: يقع خلال دقائق من الإصدار، لأنه لا ينتظر حركة سوق —
    يكفيه فارق المصدرين وحده. فارتفاع نصيب شريحة "أقل من 5 دقائق"
    مؤشر على المشكلة، وانخفاضها بعد الإصلاح هو الدليل المطلوب.
    ⚠️ ليست كل إغلاقة سريعة كاذبة: وقف بعرض الضجيج يُضرب سريعاً
    بحق. لذلك تُطبع مسافة الوقف الوسيطة لكل شريحة — فإن كانت
    الشريحة السريعة أوقافها ضيقة فعلاً، فجزء منها حقيقي بنيوياً.

 2) القرارات المغلقة التي لم تُبثّ قط. الإغلاق خلال أقل من دقيقة
    يُخرج الإشارة من فلتر (status == ACTIVE) قبل أن يستفسر البوت،
    فلا تصل أحداً — ومع ذلك تُحتسب نقاطها بالتقارير. هذا المبلغ هو
    الفارق بين "أداء مقاس" و"أداء قابل للتداول".

التشغيل:
  docker cp baseline_close_speed.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/baseline_close_speed.py [أيام]
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import defaultdict

CLOSED  = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
BUCKETS = [(5, "< 5 دقائق"), (15, "5–15 دقيقة"), (60, "15–60 دقيقة"),
           (240, "1–4 ساعات"), (10**9, "> 4 ساعات")]


def bucket_of(minutes):
    for limit, label in BUCKETS:
        if minutes < limit:
            return label
    return BUCKETS[-1][1]


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 14

    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.services.decision_grouping import verified_unique_decisions

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(Signal).filter(Signal.created_at >= cutoff).all()
        decisions = verified_unique_decisions(rows)

        # broadcast_sent ليس ضمن مخرجات التجميع — نجلبه بالصف الممثِّل
        bcast = {s.id: bool(s.broadcast_sent) for s in rows}
        levels = {s.id: (s.entry_price, s.stop_loss) for s in rows}

        closed = [d for d in decisions if d["status"] in CLOSED and d.get("exit_executed")]
        print("=" * 94)
        print(f"خط أساس — سرعة إغلاق القرارات الفريدة، آخر {days} يوماً")
        print("=" * 94)
        print(f"  قرارات فريدة بالفترة: {len(decisions)}   منها مغلقة بوقت معروف: {len(closed)}\n")
        if not closed:
            print("  لا توجد بيانات كافية.")
            return

        agg = defaultdict(lambda: {"n": 0, "pts": 0.0, "slp": [], "unsent": 0})
        for d in closed:
            created, exited = d["created_at"], d["exit_executed"]
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if exited.tzinfo is None:
                exited = exited.replace(tzinfo=timezone.utc)
            mins = (exited - created).total_seconds() / 60.0
            if mins < 0:
                continue
            b = agg[bucket_of(mins)]
            b["n"]   += 1
            b["pts"] += float(d["points"] or 0)
            if not bcast.get(d["id"], True):
                b["unsent"] += 1
            e, sl = levels.get(d["id"], (None, None))
            if e and sl and float(e) > 0:
                b["slp"].append(abs(float(e) - float(sl)) / float(e) * 100)

        print(f"  {'الشريحة':<14}{'عدد':>6}{'%':>8}{'النقاط':>11}"
              f"{'وقف وسيط':>11}{'لم تُبثّ':>10}")
        print("  " + "-" * 60)
        total = sum(v["n"] for v in agg.values())
        for _, label in BUCKETS:
            v = agg.get(label)
            if not v or not v["n"]:
                continue
            med = sorted(v["slp"])[len(v["slp"]) // 2] if v["slp"] else 0.0
            print(f"  {label:<14}{v['n']:>6}{v['n']/total*100:>7.1f}%{v['pts']:>+11.2f}"
                  f"{med:>10.3f}%{v['unsent']:>10}")
        print("  " + "-" * 60)
        print(f"  {'الإجمالي':<14}{total:>6}{100.0:>7.1f}%"
              f"{sum(v['pts'] for v in agg.values()):>+11.2f}")

        # ── القرارات المغلقة التي لم تصل أحداً ───────────────────────────
        never = [d for d in closed if not bcast.get(d["id"], True)]
        print("\n" + "=" * 94)
        print("قرارات مغلقة لم تُبثّ قط — نقاطها بالتقارير ولم يستطع أحد تداولها")
        print("=" * 94)
        if not never:
            print("  لا شيء — كل قرار مغلق بالفترة وصل المستخدمين. ✅")
        else:
            net = 0.0
            for d in sorted(never, key=lambda x: x["created_at"]):
                created, exited = d["created_at"], d["exit_executed"]
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if exited.tzinfo is None:
                    exited = exited.replace(tzinfo=timezone.utc)
                mins = (exited - created).total_seconds() / 60.0
                pts  = float(d["points"] or 0)
                net += pts
                print(f"  #{d['id']:<6}{d['market']:<10}{d['timeframe']:<5}"
                      f"{d['status']:<9} عُمرها {mins:6.1f} دقيقة   نقاط {pts:+8.2f}"
                      f"   {created:%m-%d %H:%M}")
            print(f"\n  العدد: {len(never)} من {total}"
                  f"  ({len(never)/total*100:.1f}%)   صافي نقاطها: {net:+.2f}")
            print("  ⇒ هذا القدر يجب استبعاده قبل أي مقارنة بأداء حقيقي قابل للتداول.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
