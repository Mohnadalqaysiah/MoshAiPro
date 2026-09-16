"""
diagnose_broadcast_reach.py
==============================
تشخيص قراءة فقط — لماذا تُسجَّل الإشارة كأنها أُرسلت لـ5 أشخاص فقط
بينما ينضم 5 مستخدمين جدد يومياً؟

المسار الفعلي للبث (telegram-bot/bot.py → broadcast_new_signals):
  1) /api/v1/bot/active-subscribers  ← يفلتر telegram_id != None
  2) /api/v1/bot/all-watchlists      ← من له watchlist يستلم رموزه فقط،
                                        ومن لا watchlist له يستلم الكل
  3) تبريد/قفل الاتجاه لكل رمز
ثم يُنشأ صف Signal لكل مستلم — فعدد "المستخدمين" بالسجل = من اجتاز
كل الفلاتر أعلاه، لا عدد مستخدمي المنصة.

يقيس كل مرحلة بالأرقام الحقيقية ليُظهر أين يُفقد المستخدمون بالضبط.

التشغيل:
  docker cp diagnose_broadcast_reach.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diagnose_broadcast_reach.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import Counter
from app.database import SessionLocal
from app.models.user import User, PlanType
from app.models.signal import Signal


def main():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        total     = db.query(User).count()
        active    = db.query(User).filter(User.is_active == True).count()
        not_banned= db.query(User).filter(User.is_active == True,
                                          User.plan != PlanType.BANNED).count()
        # نفس فلتر /active-subscribers بالضبط
        subs = db.query(User).filter(
            User.telegram_id != None,
            User.is_active == True,
            User.plan != PlanType.BANNED,
        ).all()

        print("=" * 88)
        print("مسار البث — أين يُفقد المستخدمون؟")
        print("=" * 88)
        print(f"  كل المستخدمين المسجّلين:                {total}")
        print(f"  نشطون (is_active):                      {active}")
        print(f"  نشطون وغير محظورين:                     {not_banned}")
        print(f"  ✅ يجتازون فلتر /active-subscribers:     {len(subs)}"
              f"   ← هؤلاء فقط من يمكن أن يستلم إشارة")
        lost = not_banned - len(subs)
        print(f"  ⛔ مفقودون لعدم ربط تيليجرام:            {lost}"
              f"  ({lost/not_banned*100:.0f}% من النشطين)" if not_banned else "")

        # ── تفصيل فلاتر التفضيلات داخل من ربط تيليجرام ────────────────────
        print("\n" + "-" * 88)
        print("داخل من ربط تيليجرام — فلاتر التفضيلات")
        print("-" * 88)
        notif_off = [u for u in subs if not u.notifications_enabled]
        with_wl   = [u for u in subs if (u.notify_watchlist or [])]
        no_wl     = [u for u in subs if not (u.notify_watchlist or [])]
        print(f"  الإشعارات مُطفأة عندهم:                 {len(notif_off)}")
        print(f"  لديهم watchlist (يستلمون رموزها فقط):   {len(with_wl)}")
        print(f"  بلا watchlist (يستلمون كل الرموز):      {len(no_wl)}")
        if with_wl:
            sizes = Counter(len(u.notify_watchlist or []) for u in with_wl)
            print(f"    أحجام الـwatchlist: "
                  + ", ".join(f"{k} رمز×{v}" for k, v in sorted(sizes.items())))
            syms = Counter()
            for u in with_wl:
                for s in (u.notify_watchlist or []):
                    syms[str(s).upper()] += 1
            print(f"    أكثر الرموز اختياراً: "
                  + ", ".join(f"{k}×{v}" for k, v in syms.most_common(8)))
        confs = Counter(int(u.notify_min_confidence or 65) for u in subs)
        print(f"  حد الثقة الأدنى المضبوط: "
              + ", ".join(f"{k}%×{v}" for k, v in sorted(confs.items())))

        # ── التسجيلات الجديدة مقابل الربط ─────────────────────────────────
        print("\n" + "-" * 88)
        print("المسجّلون حديثاً — كم منهم ربط تيليجرام؟")
        print("-" * 88)
        for days in (1, 7, 30):
            since = now - timedelta(days=days)
            newu  = db.query(User).filter(User.created_at >= since).all()
            linked = [u for u in newu if u.telegram_id]
            if newu:
                print(f"  آخر {days:>2} يوم: مسجّلون={len(newu):>3}  "
                      f"ربطوا تيليجرام={len(linked):>3}  "
                      f"({len(linked)/len(newu)*100:.0f}%)")
            else:
                print(f"  آخر {days:>2} يوم: لا تسجيلات")

        # ── واقع التوزيع بآخر الإشارات ────────────────────────────────────
        print("\n" + "-" * 88)
        print("آخر الإشارات — كم صفاً أُنشئ فعلاً لكل قرار؟")
        print("-" * 88)
        since = now - timedelta(days=2)
        rows = (db.query(Signal).filter(Signal.created_at >= since)
                  .order_by(Signal.created_at.desc()).all())
        groups = {}
        for s in rows:
            key = (s.market, s.timeframe,
                   s.created_at.replace(second=0, microsecond=0))
            groups.setdefault(key, []).append(s)
        for (market, tf, ts), g in sorted(groups.items(), key=lambda kv: kv[0][2], reverse=True)[:12]:
            users = ", ".join(sorted({str(x.user_id) for x in g}))
            print(f"  {ts:%m-%d %H:%M} {market:<10} {tf:<4} صفوف={len(g):>2}  user_ids: {users}")

        print("\n" + "=" * 88)
        print("الخلاصة: 'عدد المستخدمين' بسجل الإشارة = من اجتاز فلتر تيليجرام")
        print("ثم فلتر الـwatchlist — وليس عدد مستخدمي المنصة.")
        print("=" * 88)
    finally:
        db.close()


if __name__ == "__main__":
    main()
