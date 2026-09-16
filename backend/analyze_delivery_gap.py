"""
analyze_delivery_gap.py
==========================
تحليل قراءة فقط لسجل التسليم (signal_deliveries) — يجيب على السؤال
الذي لم تستطع لوقات الحاوية الإجابة عليه: أين يذهب الفارق بين
المؤهلين والمستلمين فعلاً؟

الأرقام المرصودة قبل السجل: 129 مستخدماً ربطوا تيليجرام ويُفترض أن
~119 منهم مؤهلون (بعد فلتر watchlist ومالك الإشارة)، بينما لوقات
البوت أظهرت وصول 57-63 فقط لكل إشارة. الفارق (~60) كان غير مفسَّر،
ومحاولة عدّه من اللوقات فشلت لأن إعادة إنشاء الحاوية تمسحها.

يعرض:
 1) آخر الإشارات: كم أُرسلت، كم نجحت، كم فشلت.
 2) المستخدمون الذين يفشل الإرسال إليهم دائماً — بالاسم والبريد وسبب
    الفشل (غالباً حظر البوت أو chat_id غير صالح). هؤلاء قابلون
    للمعالجة: تذكيرهم بإعادة الربط.
 3) من ربط تيليجرام ولم يظهر بأي تسليم إطلاقاً — الفجوة الصامتة.

التشغيل:
  docker cp analyze_delivery_gap.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_delivery_gap.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from app.database import SessionLocal
from app.models.user import User, PlanType
from app.models.signal import Signal
from app.models.signal_delivery import SignalDelivery


def main():
    db = SessionLocal()
    try:
        total_rows = db.query(SignalDelivery).count()
        print("=" * 92)
        print("سجل التسليم")
        print("=" * 92)
        if total_rows == 0:
            print("  ⚠️ السجل فارغ — لم يحدث أي بث بعد منذ تفعيله.")
            print("     انتظر أول إشارة جديدة ثم أعد تشغيل هذا السكربت.")
            return
        print(f"  إجمالي سجلات التسليم: {total_rows}")

        # ── 1) آخر الإشارات ───────────────────────────────────────────────
        print("\n" + "-" * 92)
        print("آخر الإشارات المبثوثة")
        print("-" * 92)
        recent_ids = [r[0] for r in db.query(SignalDelivery.signal_id)
                        .distinct().order_by(SignalDelivery.signal_id.desc())
                        .limit(15).all()]
        sigs = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(recent_ids)).all()}
        for sid in recent_ids:
            rows = db.query(SignalDelivery).filter(SignalDelivery.signal_id == sid).all()
            ok   = sum(1 for r in rows if r.ok)
            bad  = len(rows) - ok
            full = sum(1 for r in rows if r.ok and r.variant == "full")
            s    = sigs.get(sid)
            label = f"{s.market}/{s.timeframe}" if s else "?"
            print(f"  #{sid:<5} {label:<14} أُرسلت={len(rows):>3}  نجح={ok:>3}  "
                  f"فشل={bad:>3}  (كاملة={full})")

        # ── 2) من يفشل الإرسال إليهم ──────────────────────────────────────
        print("\n" + "-" * 92)
        print("المستخدمون الذين يفشل الإرسال إليهم — قابلون للمعالجة")
        print("-" * 92)
        failed = db.query(SignalDelivery).filter(SignalDelivery.ok == False).all()
        if not failed:
            print("  لا توجد حالات فشل مسجّلة ✅")
        else:
            by_tid = defaultdict(list)
            for r in failed:
                by_tid[r.telegram_id].append(r)
            uids = [r.user_id for r in failed if r.user_id]
            users = {u.id: u for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
            print(f"  عدد المستخدمين المتأثرين: {len(by_tid)}")
            for tid, rows in sorted(by_tid.items(), key=lambda kv: -len(kv[1]))[:25]:
                u = users.get(rows[0].user_id)
                who = f"{u.email}" if u else f"TG {tid} (غير مرتبط بحساب)"
                err = (rows[-1].error or "")[:80]
                print(f"    {who:<38} مرات الفشل={len(rows):>3}  السبب: {err}")
            errs = Counter((r.error or "")[:60] for r in failed)
            print("\n  أكثر أسباب الفشل تكراراً:")
            for e, c in errs.most_common(5):
                print(f"    {c:>4}×  {e}")

        # ── 3) الفجوة الصامتة ─────────────────────────────────────────────
        print("\n" + "-" * 92)
        print("ربطوا تيليجرام لكن لا يظهر لهم أي تسليم إطلاقاً")
        print("-" * 92)
        linked = db.query(User).filter(
            User.telegram_id != None,
            User.is_active == True,
            User.plan != PlanType.BANNED,
        ).all()
        seen = {r[0] for r in db.query(SignalDelivery.telegram_id).distinct().all()}
        missing = [u for u in linked if str(u.telegram_id) not in seen]
        print(f"  ربطوا تيليجرام: {len(linked)}   ظهروا بالسجل: {len(linked) - len(missing)}   "
              f"لم يظهروا إطلاقاً: {len(missing)}")
        if missing:
            print("  (السبب المرجّح: watchlist يحصرهم برموز لم تصدر لها إشارة بعد، "
                  "أو الإشعارات مطفأة، أو انضموا بعد آخر بث)")
            for u in missing[:20]:
                wl = u.notify_watchlist or []
                print(f"    {u.email:<38} watchlist={len(wl)} رمز  "
                      f"إشعارات={'مفعّلة' if u.notifications_enabled else 'مطفأة'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
