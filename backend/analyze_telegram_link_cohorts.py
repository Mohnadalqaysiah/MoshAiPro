"""
analyze_telegram_link_cohorts.py
===================================
تحليل قراءة فقط — هل نفع إصلاح جولة التعريف (زر ربط تيليجرام الحقيقي،
commit 19fcc08 بتاريخ 2026-09-10) في رفع نسبة الربط؟

⚠️ الخطأ المنهجي الذي يتجنّبه هذا السكربت: مقارنة "نسبة المرتبطين" بين
نوافذ تسجيل مختلفة (آخر يوم 22% مقابل آخر 30 يوماً 42%) غير صالحة
إطلاقاً — من سجّل أمس أمامه يوم واحد ليربط، ومن سجّل قبل شهر أمامه 30
يوماً. هذا الانحياز (right-censoring) ينتج انحداراً وهمياً حتى لو كانت
نسبة الربط ثابتة تماماً. الاستنتاج الصحيح يحتاج أفواجاً بنفس مدة
التعرّض.

المقارنة هنا: فوج ما قبل الإصلاح مقابل فوج ما بعده، مع تثبيت الحد
الأدنى لمدة التعرّض للفوجين معاً (كل مستخدم مضى على تسجيله MIN_AGE_DAYS
على الأقل). ولأن عمود telegram_linked_at أُضيف بعد الإصلاح، لا يمكن
حساب "ربط خلال 48 ساعة" رجعياً — فالمقياس المتاح الآن هو "مرتبط الآن"
مع تثبيت العمر، ويُذكر اتجاه الانحياز صراحةً.

التشغيل:
  docker cp analyze_telegram_link_cohorts.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_telegram_link_cohorts.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.user import User, PlanType

FIX_DATE      = datetime(2026, 9, 10, tzinfo=timezone.utc)  # commit 19fcc08
MIN_AGE_DAYS  = 5   # أقل مدة تعرّض مشتركة (الإصلاح عمره ~6 أيام)


def rate(users):
    n = len(users)
    linked = sum(1 for u in users if u.telegram_id)
    return n, linked, (linked / n * 100 if n else 0.0)


def main():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cutoff_age = now - timedelta(days=MIN_AGE_DAYS)

        users = db.query(User).filter(
            User.is_active == True,
            User.plan != PlanType.BANNED,
            User.created_at != None,
        ).all()

        def created(u):
            c = u.created_at
            return c.replace(tzinfo=timezone.utc) if c.tzinfo is None else c

        mature = [u for u in users if created(u) <= cutoff_age]
        pre    = [u for u in mature if created(u) <  FIX_DATE]
        post   = [u for u in mature if created(u) >= FIX_DATE]
        fresh  = [u for u in users  if created(u) >  cutoff_age]

        print("=" * 92)
        print(f"أثر إصلاح جولة التعريف (زر ربط تيليجرام) — نُشر {FIX_DATE.date()}")
        print("=" * 92)
        print(f"  المقارنة مقيّدة بمن مضى على تسجيله ≥ {MIN_AGE_DAYS} أيام، "
              f"حتى يتساوى الفوجان بمدة الفرصة للربط.")
        print(f"  (مستبعدون لأنهم أحدث من ذلك: {len(fresh)} مستخدماً — "
              f"لم تمضِ عليهم مدة كافية ليُحكم عليهم)\n")

        for label, group in (("قبل الإصلاح", pre), ("بعد الإصلاح", post)):
            n, linked, pct = rate(group)
            flag = "  ⚠️ عينة صغيرة" if n < 15 else ""
            print(f"  {label:<14} n={n:>4}  ربطوا={linked:>4}  النسبة={pct:>5.1f}%{flag}")

        n_pre,  l_pre,  p_pre  = rate(pre)
        n_post, l_post, p_post = rate(post)

        print("\n" + "-" * 92)
        if not n_post:
            print("  لا يوجد فوج 'بعد الإصلاح' ناضج بعد — أعد التشغيل بعد أيام.")
        elif n_post < 15:
            print(f"  ⚠️ فوج ما بعد الإصلاح عيّنته {n_post} فقط — الفارق "
                  f"({p_post - p_pre:+.1f} نقطة مئوية) غير قاطع إحصائياً.")
            print("     الإصلاح عمره أيام قليلة؛ الحكم يحتاج وقتاً أطول.")
        else:
            diff = p_post - p_pre
            print(f"  الفارق: {diff:+.1f} نقطة مئوية")
            if diff > 0:
                print("  ⇒ فوج ما بعد الإصلاح أعلى رغم أن مدة تعرّضه أقصر — "
                      "الانحياز ضده، فالنتيجة الإيجابية موثوقة.")
            else:
                print("  ⇒ لا تحسّن ظاهر. لكن انتبه: فوج ما قبل الإصلاح مضى عليه "
                      "وقت أطول للربط، فجزء من الفارق قد يكون من الانحياز لا من الإصلاح.")

        # ── القياس الصحيح المتاح من الآن فصاعداً ─────────────────────────
        print("\n" + "=" * 92)
        print("القياس الدقيق (من تاريخ إضافة telegram_linked_at)")
        print("=" * 92)
        with_ts = [u for u in users if getattr(u, "telegram_linked_at", None)]
        print(f"  مستخدمون لديهم وقت ربط مسجّل: {len(with_ts)}")
        if with_ts:
            fast = 0
            for u in with_ts:
                t = u.telegram_linked_at
                t = t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t
                if (t - created(u)) <= timedelta(hours=48):
                    fast += 1
            print(f"  ربطوا خلال أول 48 ساعة: {fast}/{len(with_ts)} "
                  f"({fast/len(with_ts)*100:.1f}%)")
        else:
            print("  لا يوجد بعد — العمود جديد، والقيم تتراكم مع كل ربط قادم.")
            print("  هذا هو المقياس العادل الذي سنحكم به لاحقاً بدل نسب منحازة.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
