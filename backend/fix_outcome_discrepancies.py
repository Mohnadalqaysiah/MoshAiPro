"""
fix_outcome_discrepancies.py
===============================
يصحّح الصفوف التي يخالف فيها حكم أداة التحقق (شموع حقيقية، ترتيب زمني)
ما هو مسجّل بقاعدة البيانات — نتيجةَ عطلين بحلقة الرصد أُصلحا اليوم:
  • المشي الزمني كان ميتاً (TypeError مبتلَع) فسقط الرصد للسعر اللحظي.
  • TP1 كان نهائياً، فلا تُرى TP2 إن جاءت بشمعة لاحقة.

شهادتان مستقلتان تؤكدان أن حكم الأداة هو الصحيح لا المسجّل:
  • #2507 XAUUSD — رصد المستخدم بنفسه أن الإشارة بلغت الهدف الثاني
    بينما سُجّلت "هدف أول".
  • #2521 BTCUSD — فحص الشموع يدوياً: أعلى سعر بعد الإصدار يقل عن
    الوقف بـ9 نقاط، فالوقف لم يُلمس أصلاً.

⚠️ تفاوت الثقة بين الفئات — مطبوع صراحةً ويمكن استثناؤه:
  • TP1→TP2 و SL→TP2: عالية الثقة. بلوغ هدف أبعد واقعة موجبة لا تحتمل
    الغموض (السعر وصله فعلاً).
  • TP1→SL: أقل يقيناً. أداة التحقق ترجّح الوقف عند التعادل داخل
    الشمعة الواحدة، وبوقف ضيق على شمعة 5 دقائق قد تشمل الشمعة
    المستويين معاً — فقد يكون غموضاً لا خطأً مؤكداً. استخدم
    --skip-ambiguous لاستثنائها.
  • →STILL_ACTIVE: تُعاد الإشارة للحالة النشطة مع تنبيه إن كان
    expires_at بالماضي (لن تُفحص تلقائياً بعدها).

⚠️ افتراضياً DRY-RUN. لازم --apply صراحة.

التشغيل:
  docker cp fix_outcome_discrepancies.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/fix_outcome_discrepancies.py
  docker exec moshapi_backend python /app/fix_outcome_discrepancies.py --skip-ambiguous --apply
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from loguru import logger

# (2026-09-16) صار يُقرأ من سطر الأوامر: --days N. الدافع أن تقرير
# الجودة على 90 يوماً أظهر أن أسوأ رمز (XAUUSD: -0.45R على 65 قراراً،
# 63 منها بالنصف الأقدم) يقع خارج نافذة الـ10 أيام التي صُحّحت — أي أن
# أهم أرقامنا مبنية على فترة نعرف أنها مقيسة بأدوات معطوبة.
#
# ⚠️ قيد صلب لا تتجاوزه النافذة: _verify_signal_outcome_core تجلب 1000
# شمعة 5m = ~3.5 أيام فقط، وفيها حارس صريح يعيد NO_DATA إن كانت أقدم
# شمعة متاحة بعد لحظة إنشاء الإشارة. فتوسيع --days لا يوسّع التغطية
# الفعلية؛ الصفوف الأقدم تُستبعد بالامتناع لا بالتخمين (وهو السلوك
# الصحيح). الغرض من التوسيع هنا قياس التغطية الحقيقية لا افتراضها.
LOOKBACK_DAYS = 10
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}

# (2026-09-12) نفس الاستثناء المعتمد سابقاً: #2354 مستوياته وهمية بالكامل
# (بق حارس السعر، أُصلح 12daaf7) فأي تحقق عليها يعيد إنتاج قيمة فاسدة.
EXCLUDE_IDS = {2354}


async def main():
    apply_it  = "--apply" in sys.argv
    skip_amb  = "--skip-ambiguous" in sys.argv

    # (2026-09-16) --only 2521,2426: تطبيق انتقائي بأرقام محددة. أُضيف لأن
    # الفئات وحدها لم تعد كافية للقرار: صفوف الفضة ما زالت تختلف لأن
    # مستوياتها بُنيت على carry نظري بينما التحقق يقارنها بـTV الفوري —
    # مرجعان مختلفان لم يُوحَّدا بعد. فبعض الصفوف جاهزة للتصحيح وبعضها
    # ينتظر توحيد المرجع، والخلط بينها بتطبيق جماعي يفسد الاثنين.
    lookback = LOOKBACK_DAYS
    for i, a in enumerate(sys.argv):
        if a == "--days" and i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
            lookback = int(sys.argv[i + 1])

    only_ids = set()
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            only_ids = {int(x) for x in sys.argv[i + 1].split(",") if x.strip().isdigit()}
    if only_ids:
        print(f"⚠️ تطبيق انتقائي — الأرقام المحددة فقط: {sorted(only_ids)}\n")

    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.api.admin import _verify_signal_outcome_core, _calc_points

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback)
        rows = (db.query(Signal)
                  .filter(Signal.created_at >= cutoff)
                  .order_by(Signal.created_at.desc()).all())
        closed = [s for s in rows
                  if (s.status.value if hasattr(s.status, "value") else s.status) in CLOSED
                  and s.id not in EXCLUDE_IDS]

        print(f"إشارات مغلقة آخر {LOOKBACK_DAYS} أيام: {len(closed)} — جاري الفحص...\n")

        high_conf, ambiguous, reactivate = [], [], []
        for i, s in enumerate(closed):
            if i and i % 25 == 0:
                print(f"  … {i}/{len(closed)}")
            try:
                r = await _verify_signal_outcome_core(s)
            except Exception as e:
                verdicts["فشل"] += 1
                print(f"  #{s.id} فشل التحقق: {e}")
                continue
            det = r.get("detected")
            rec = s.status.value if hasattr(s.status, "value") else s.status
            if det in (None, "NO_DATA"):
                verdicts["لا بيانات"] += 1
                created_ = s.created_at
                if created_ and created_.tzinfo is None:
                    created_ = created_.replace(tzinfo=timezone.utc)
                age_d = (now_ - created_).total_seconds() / 86400 if created_ else 999
                key = "< 4 أيام" if age_d < 4 else ("4–10 أيام" if age_d < 10 else "> 10 أيام")
                nodata_by_age[key] += 1
                continue
            if det == rec:
                verdicts["مطابق"] += 1
                continue
            verdicts["مخالف"] += 1
            if only_ids and s.id not in only_ids:
                continue
            if det == "STILL_ACTIVE":
                reactivate.append((s, rec, det))
            elif det == "SL_HIT":
                ambiguous.append((s, rec, det))      # ربح مسجّل ← خسارة
            else:
                high_conf.append((s, rec, det))      # بلوغ هدف أبعد
            await asyncio.sleep(0.25)

        delta_total = 0.0

        def do_fix(group, title, enabled=True):
            nonlocal delta_total
            print("\n" + "=" * 92)
            print(f"{title}  ({len(group)} صف)" + ("" if enabled else "  — مستثناة بـ--skip-ambiguous"))
            print("=" * 92)
            if not group:
                print("  لا شيء.")
                return
            for s, rec, det in group:
                old_pts = s.points_earned or 0.0
                entry = float(s.entry_price); sl = float(s.stop_loss)
                tp1   = float(s.take_profit_1); tp2 = float(s.take_profit_2 or tp1)
                is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"

                if det == "SL_HIT":
                    diff, exit_price = abs(entry - sl), sl
                elif det == "TP2_HIT":
                    diff, exit_price = abs(tp2 - entry), tp2
                else:
                    diff, exit_price = abs(tp1 - entry), tp1

                pts = _calc_points(s.market, diff, entry)
                if det == "SL_HIT":
                    pts = -pts
                pnl_pct = round((exit_price - entry) / entry * 100, 3) if is_buy \
                          else round((entry - exit_price) / entry * 100, 3)

                print(f"  #{s.id:<5} {s.market:<11} {s.timeframe:<4} "
                      f"{rec:<9} ← {det:<9}  نقاط {old_pts:+8.2f} ← {pts:+8.2f}"
                      + ("" if (apply_it and enabled) else "   [محاكاة]"))

                if enabled:
                    delta_total += (pts - old_pts)
                    if apply_it:
                        s.status = SignalStatus(det)
                        s.points_earned = round(pts, 2)
                        s.profit_loss = round(pts, 2)
                        s.profit_loss_percentage = pnl_pct
                        s.outcome_verified = True
                        logger.info(f"[OUTCOME-FIX] #{s.id} {s.market} {rec}({old_pts}) -> {det}({pts:+.2f})")

        print("\n" + "=" * 92)
        print("تغطية الفحص — ما أمكن الحكم عليه فعلاً")
        print("=" * 92)
        for k, v in verdicts.items():
            print(f"  {k}: {v}")
        judged = verdicts["مطابق"] + verdicts["مخالف"]
        total_ = max(len(closed), 1)
        print(f"\n  نسبة القابل للحكم: {judged}/{total_} ({judged/total_*100:.1f}%)")
        if verdicts["لا بيانات"]:
            print("\n  توزيع 'لا بيانات' بحسب عمر الإشارة:")
            for k, v in nodata_by_age.items():
                print(f"    {k}: {v}")
            print("  ⇒ الامتناع هنا سلوك صحيح: الشموع المتاحة لا تعود لوقت")
            print("    الإنشاء، والحكم بها كان سيقيس نافذة زمنية أخرى تماماً.")

        do_fix(high_conf, "عالية الثقة — بلوغ هدف أبعد (واقعة موجبة)")
        do_fix(ambiguous, "أقل يقيناً — ربح مسجّل ← وقف (غموض داخل الشمعة ممكن)",
               enabled=not skip_amb)

        print("\n" + "=" * 92)
        print(f"إعادة تنشيط (لم تُحسم فعلياً)  ({len(reactivate)} صف)")
        print("=" * 92)
        now = datetime.now(timezone.utc)
        for s, rec, det in reactivate:
            warn = ""
            if s.expires_at and s.expires_at < now:
                warn = "  ⚠️ expires_at بالماضي — لن تُفحص تلقائياً بعدها"
            print(f"  #{s.id:<5} {s.market:<11} {s.timeframe:<4} {rec} ← ACTIVE"
                  + ("" if apply_it else "   [محاكاة]") + warn)
            if apply_it:
                s.status = SignalStatus.ACTIVE
                s.points_earned = None
                s.profit_loss = 0.0
                s.exit_executed = None
                logger.info(f"[OUTCOME-FIX] #{s.id} {s.market} {rec} -> ACTIVE")

        if apply_it:
            db.commit()

        print("\n" + "=" * 92)
        print(f"صافي تغيّر النقاط (الفئات المفعّلة فقط): {delta_total:+.2f}")
        print("=" * 92)
        print("✅ طُبّق." if apply_it
              else "ℹ️  محاكاة — لم يُعدَّل شيء. أضف --apply للتنفيذ.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
