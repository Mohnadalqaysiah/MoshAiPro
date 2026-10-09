"""
diag_duplicates.py — تشخيص قراءة فقط: من أين تأتي الإشارات المكررة؟ (2026-10-10)
==============================================================================
تقرير الأداء أظهر نفس الصفقة كقرارين منفصلين (مثال: XAGUSD بيع −20.04 مرة
لمستخدم واحد ومرة لـ111). group_unique_decisions يجمع بـ(رمز، فريم، نوع،
دخول مقرّب لـ5 خانات) + نافذة دقيقتين — فما يفلت منه يعني اختلافاً بأحد هذه.

يبحث عن أزواج "قرارات" مختلفة بنفس الرمز والاتجاه، دخولها متقارب (≤0.05%)
وإنشاؤها متقارب (≤6 ساعات)، ويصنّف سبب انفصالها:
  - فريم مختلف (نفس المستويات على 15m و1h مثلاً)
  - فارق زمني > دقيقتين (أُعيد إصدارها لاحقاً)
  - فارق دخول صغير (تقريب)
ومعه: هل بُثّت كل واحدة (broadcast_sent) وكم مستخدماً استلمها.

التشغيل:
  docker cp backend/diag_duplicates.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diag_duplicates.py 2>/dev/null
"""
import sys
sys.path.insert(0, "/app")

from collections import Counter
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import group_unique_decisions

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
ENTRY_TOL = 0.0005      # 0.05%
TIME_TOL = timedelta(hours=6)


def _aware(d):
    return d if (d is None or d.tzinfo) else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    rows = db.query(Signal).filter(Signal.created_at >= since).all()
    by_id = {s.id: s for s in rows}
    groups = group_unique_decisions(rows)
    print(f"📊 آخر {DAYS} يوم: {len(rows)} صف = {len(groups)} قرار\n")

    decs = []
    for g in groups:
        rids = g.get("row_ids", [g["id"]])
        rs = [by_id[i] for i in rids if i in by_id]
        first = min(rs, key=lambda r: r.created_at)
        decs.append(dict(
            id=first.id, market=(first.market or "").upper(), tf=first.timeframe,
            side=first.signal_type.value if hasattr(first.signal_type, "value") else first.signal_type,
            entry=float(first.entry_price or 0), sl=float(first.stop_loss or 0),
            created=_aware(first.created_at), rows=len(rs),
            users=len({r.user_id for r in rs}),
            broadcast=any(r.broadcast_sent for r in rs),
            status=g.get("status"),
        ))
    decs.sort(key=lambda d: (d["market"], d["side"], d["created"]))

    pairs, reasons = [], Counter()
    for i, a in enumerate(decs):
        for b in decs[i + 1:]:
            if b["market"] != a["market"] or b["side"] != a["side"]:
                break
            if b["created"] - a["created"] > TIME_TOL:
                break
            if not a["entry"] or abs(b["entry"] - a["entry"]) / a["entry"] > ENTRY_TOL:
                continue
            why = []
            if a["tf"] != b["tf"]:
                why.append(f"فريم مختلف {a['tf']}/{b['tf']}")
            gap = (b["created"] - a["created"]).total_seconds() / 60
            if gap > 2:
                why.append(f"فارق {gap:.0f} دقيقة")
            if round(a["entry"], 5) != round(b["entry"], 5):
                why.append("فارق دخول صغير")
            for w in why:
                reasons[w.split(" ")[0] + " " + w.split(" ")[1]] += 1
            pairs.append((a, b, why))

    print(f"أزواج قرارات متطابقة تقريباً (نفس الرمز والاتجاه، دخول ≤0.05%، خلال 6 ساعات): {len(pairs)}\n")
    for a, b, why in pairs[:60]:
        print(f"  {a['market']:8s} {a['side']:4s}  #{a['id']} {a['tf']:4s} {a['created']:%m-%d %H:%M} "
              f"دخول={a['entry']:.6g} بث={'نعم' if a['broadcast'] else 'لا'} مستخدمون={a['users']} {a['status']}")
        print(f"  {'':8s} {'':4s}  #{b['id']} {b['tf']:4s} {b['created']:%m-%d %H:%M} "
              f"دخول={b['entry']:.6g} بث={'نعم' if b['broadcast'] else 'لا'} مستخدمون={b['users']} {b['status']}"
              f"   ← {' · '.join(why)}")
    print("\n" + "=" * 80)
    print("سبب الانفصال (زوج قد يحمل أكثر من سبب):")
    for k, v in reasons.most_common():
        print(f"   {k}: {v}")
    both_bc = sum(1 for a, b, _ in pairs if a["broadcast"] and b["broadcast"])
    print(f"   الاثنتان بُثّتا للمشتركين: {both_bc} من {len(pairs)}")
    print("=" * 80)
    db.close()


if __name__ == "__main__":
    main()
