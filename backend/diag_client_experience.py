"""
(2026-11-14) ماذا يعيش العميل فعلاً — المالك: "العملاء بحس مش راضيين عن المنصة وانا كذلك".
للقراءة فقط. المجموع بـR يقيس المنصة؛ رضا العميل يقيسه ما يراه كل يوم: كم إشارة تصله، كم "❌ وقف" يقرأ، أسوأ يوم،
أطول سلسلة خسائر، وهل الخسائر تأتي **متكدّسة** (عدة صفقات بنفس الاتجاه على أسواق مترابطة بنفس الساعات = رهان واحد مكرّر).

يقارن "الكل" (ما يصل الآن) بأوضاع تخفيف **محددة سلفاً** (لا بحث عن أفضل عتبة):
  - تكدّس: من صفقات نفس المجموعة ونفس الاتجاه خلال 4 ساعات تبقى الأولى فقط.
  - سقف يومي 5: أول 5 إشارات باليوم (UTC).
  - الاثنان معاً.

⚠️ حدود: اليوم = يوم إنشاء الإشارة (لا يوم إغلاقها). السلسلة بترتيب الإنشاء. إجمالي بلا سبريد. الأسهم الأمريكية مستبعدة (موقوفة).
أي وضع يبدو أفضل هنا **مرشّح يُسجَّل ثم يُقاس صامتاً للأمام**، لا قرار.

    docker exec moshapi_backend python diag_client_experience.py [من=2026-10-14]
"""
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

SINCE = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc) if len(sys.argv) > 1 \
    else datetime(2026, 10, 14, tzinfo=timezone.utc)
CLUSTER_WINDOW = timedelta(hours=4)
DAILY_CAP = 5


def declutter(decs, window=CLUSTER_WINDOW):
    """من كل تكدّس (نفس المجموعة + نفس الاتجاه، خلال window من أول صفقة فيه) تبقى الأولى."""
    kept, anchor = [], {}
    for d in decs:
        k = (d["group"], d["side"])
        a = anchor.get(k)
        if a is not None and d["created_at"] - a < window:
            continue
        anchor[k] = d["created_at"]
        kept.append(d)
    return kept


def daily_cap(decs, cap=DAILY_CAP):
    kept, per_day = [], defaultdict(int)
    for d in decs:
        day = d["created_at"].date()
        if per_day[day] < cap:
            per_day[day] += 1
            kept.append(d)
    return kept


def clusters(decs, window=CLUSTER_WINDOW):
    """التكدّسات بحجم ≥ 3: [(المجموعة، الاتجاه، العدد، مجموع R)]"""
    out, cur = [], {}
    for d in decs:
        k = (d["group"], d["side"])
        c = cur.get(k)
        if c and d["created_at"] - c["start"] < window:
            c["rs"].append(d["r"])
        else:
            if c and len(c["rs"]) >= 3:
                out.append((k[0], k[1], len(c["rs"]), sum(c["rs"])))
            cur[k] = {"start": d["created_at"], "rs": [d["r"]]}
    out += [(k[0], k[1], len(c["rs"]), sum(c["rs"])) for k, c in cur.items() if len(c["rs"]) >= 3]
    return out


from app.services.client_experience import experience  # noqa: E402 — مشتركة مع أرقام الباقات (recommended_prefs)


def main():
    from app.database import SessionLocal
    from app.services.weekly_markets import closed_decisions
    db = SessionLocal()
    decs = sorted((d for d in closed_decisions(db, SINCE) if d["status"] != "BREAKEVEN" and d["group"] != "stock"),
                  key=lambda d: d["created_at"])
    db.close()
    if not decs:
        print("لا قرارات مغلقة بهذه الفترة")
        return
    days = max(1, (decs[-1]["created_at"].date() - decs[0]["created_at"].date()).days + 1)
    print(f"تجربة العميل من {SINCE:%Y-%m-%d} ({days} يوماً، بلا الأسهم الأمريكية): {len(decs)} قراراً محسوماً\n")
    print(f"  {'الوضع':<24} {'عدد':>4} {'باليوم':>6} {'نجاح':>5} {'المجموع':>8} {'المتوسط':>7} {'أسوأ يوم':>8} "
          f"{'أيام سالبة':>9} {'❌ باليوم':>8} {'أقصى ❌ بيوم':>11} {'أطول سلسلة':>10}")
    modes = [("الكل (ما يصل الآن)", decs), ("بلا تكدّس (4 ساعات)", declutter(decs)),
             (f"سقف {DAILY_CAP} يومياً", daily_cap(decs)), ("بلا تكدّس + سقف", daily_cap(declutter(decs)))]
    for name, ds in modes:
        e = experience(ds, days)
        print(f"  {name:<24} {e['n']:>4} {e['per_day']:>6.1f} {e['win']:>4.0f}% {e['tot']:>+7.1f}R {e['avg']:>+6.2f}R "
              f"{e['worst_day']:>+7.1f}R {e['neg_days']:>8.0f}% {e['sl_day']:>8.1f} {e['max_sl_day']:>11} {e['streak']:>10}")

    # (2026-11-14، بعد القراءة الأولى) التخصص بسوق بدل التخفيف بالوقت: لكل مجموعة ما يعيشه من يتداولها وحدها
    print(f"\nمن يتداول مجموعة واحدة فقط (كل إشاراتها):")
    print(f"  {'المجموعة':<24} {'عدد':>4} {'باليوم':>6} {'نجاح':>5} {'المجموع':>8} {'المتوسط':>7} {'أسوأ يوم':>8} "
          f"{'أيام سالبة':>9} {'❌ باليوم':>8} {'أقصى ❌ بيوم':>11} {'أطول سلسلة':>10}")
    groups = defaultdict(list)
    for d in decs:
        groups[d["group"]].append(d)
    for g, ds in sorted(groups.items(), key=lambda kv: -sum(x["r"] for x in kv[1])):
        e = experience(ds, days)
        print(f"  {g:<24} {e['n']:>4} {e['per_day']:>6.1f} {e['win']:>4.0f}% {e['tot']:>+7.1f}R {e['avg']:>+6.2f}R "
              f"{e['worst_day']:>+7.1f}R {e['neg_days']:>8.0f}% {e['sl_day']:>8.1f} {e['max_sl_day']:>11} {e['streak']:>10}")
    print("  (أيام سالبة = من الأيام التي فيها إشارة لهذه المجموعة)")

    cl = clusters(decs)
    print(f"\nالتكدّسات (≥ 3 صفقات بنفس المجموعة والاتجاه خلال 4 ساعات): {len(cl)}، "
          f"فيها {sum(c[2] for c in cl)} صفقة من {len(decs)}، مجموعها {sum(c[3] for c in cl):+.1f}R")
    by_g = defaultdict(lambda: [0, 0, 0.0, 0])
    for g, side, k, tot in cl:
        x = by_g[(g, side)]
        x[0] += 1
        x[1] += k
        x[2] += tot
        x[3] += tot < 0
    for (g, side), (c, k, tot, losing) in sorted(by_g.items(), key=lambda kv: kv[1][2]):
        print(f"  {g:<10} {side:<5} {c:>3} تكدّساً، {k:>4} صفقة، {tot:>+7.1f}R، الخاسر منها {losing}/{c}")
    worst = sorted(cl, key=lambda c: c[3])[:5]
    print("  أسوأ 5:", "، ".join(f"{g} {s} ×{k} {t:+.1f}R" for g, s, k, t in worst))
    print("\nأي وضع أفضل هنا مرشّح للتسجيل ثم القياس الصامت للأمام — لا يُطبَّق من هذا التقرير.")


if __name__ == "__main__":
    main()
