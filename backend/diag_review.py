"""
(2026-10-17) أداة المراجعة الدورية — تطبّق قواعد القرار المسجّلة مسبقاً (DECISIONS.md 16/10 و17/10) آلياً على كل مرشّح.
كُتبت **قبل** رؤية أرقام المراجعة (30/10)، فلا يُفصَّل الحكم على النتيجة. للقراءة فقط — لا تعدّل شيئاً.

القواعد:
  (1) شرط رفض جديد ← "مرشّح لتجربة صامتة" فقط إن: ن ≥ 30، توقّع < −0.3R، وسالب بالنصفين (ترتيب زمني، نصفان بالعدد).
  (2) قاعدة رفض قائمة (صفقاتها بالظل) ← "مرشّحة للتخفيف" فقط إن: ن ≥ 30، توقّع > +0.3R، وموجب بالنصفين. وإلا تبقى.
  (3) قالب ذهب بتجربة الظل ← "مرشّح لاعتماده لتوصيات الذهب" فقط إن: أسبوعان على الأقل منذ 16/10، صافٍ موجب، ≥ 20 صفقة،
      أغلب الأسابيع رابحة، أقصى تراجع < 6R، **و**صافيه أعلى من قرارات المحرك للذهب بنفس الفترة. قالب بيع فقط لا يُعتمد وحده.
  (4) كريبتو العطلة (~09/11): يُعاد إن كان متوسط الظل ≥ 0R على ≥ 30 صفقة، وإلا يبقى الإيقاف.
كل "مرشّح" يعني: يُعرض على المالك — لا شيء يُطبَّق من هنا.

(2026-10-18، المرحلة 2) صفقات الظل في (2) و(4) تُقرأ عبر app/services/shadow_stats.py: **النظيفة فقط** (levels_version —
تدقيق 18/10 وجد 254 من 797 قديمة بمستويات معكوسة قلبت الحكم)، و**فرصة مستقلة لا صف** (797 صفاً = 557 فرصة). هذا تنظيف
للبيانات لا تعديل للقواعد: العتبات والنصفان كما سُجّلت أعلاه حرفياً، وتُطبَّق على R الإجمالي كما سُجّلت. يُعرض بجانبها R بعد
سبريد الجدول (تقدير لا قياس) مع تنبيه إن اختلف الاتجاه — تعديل القاعدة نفسها قرار المالك.

    docker exec moshapi_backend python diag_review.py [أيام=30]
"""
import sys
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def _halves(rs):
    if len(rs) < 10:
        return None, None
    h = len(rs) // 2
    a, b = rs[:h], rs[h:]
    return sum(a) / len(a), sum(b) / len(b)


def _line(name, rs, base_total, mode="reject", nets=None, rows=None):
    n = len(rs)
    if not n:
        return f"  {name:<34} لا صفقات"
    avg = sum(rs) / n
    h1, h2 = _halves(rs)
    hs = "عينة صغيرة" if h1 is None else f"{h1:+.2f}R ← {h2:+.2f}R"
    if mode == "reject":
        ok_n, ok_e, ok_h = n >= 30, avg < -0.3, h1 is not None and h1 < 0 and h2 < 0
        verdict = "🟠 مرشّح لتجربة صامتة (ثم قرار المالك)" if ok_n and ok_e and ok_h else \
            "⚪ لا يُعدَّل — " + "، ".join(x for x, ok in (("ن<30", ok_n), ("التوقّع ليس أسوأ من −0.3R", ok_e),
                                                          ("ليس سالباً بالنصفين", ok_h)) if not ok)
        extra = f" | لو حُذف: {base_total - sum(rs):+.1f}R بدل {base_total:+.1f}R"
    else:   # relax: صفقات منعتها قاعدة قائمة
        ok_n, ok_e, ok_h = n >= 30, avg > 0.3, h1 is not None and h1 > 0 and h2 > 0
        verdict = "🟢 مرشّحة للتخفيف (تمنع رابحات)" if ok_n and ok_e and ok_h else \
            ("✅ القاعدة تمنع خاسرات — تبقى" if avg < 0 else "⚪ تبقى — " + "، ".join(
                x for x, ok in (("ن<30", ok_n), ("التوقّع ليس أفضل من +0.3R", ok_e), ("ليس موجباً بالنصفين", ok_h)) if not ok))
        extra = ""
    if nets is not None:
        ok = [x for x in nets if x is not None]
        if ok:
            na = sum(ok) / len(ok)
            extra += f" | بعد سبريد الجدول {na:+.2f}R"
            if (na > 0) != (avg > 0):
                verdict += "\n      ⚠️ الاتجاه ينقلب بعد السبريد — لا يُعتمد الحكم الإجمالي وحده (قرار المالك)"
    if rows is not None:
        extra += f" | ({rows} صفاً → {n} فرصة محسومة)"
    return f"  {name:<34} ن={n:<4} توقّع {avg:+.2f}R | النصفان {hs}{extra}\n      {verdict}"


def main():
    from app.services.weekly_markets import closed_decisions
    from app.models.shadow_signal import ShadowSignal
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=DAYS)
    decs = sorted(closed_decisions(db, since), key=lambda d: d["created_at"])
    decided = [d for d in decs if d["status"] != "BREAKEVEN"]
    base = sum(d["r"] for d in decided)
    print(f"مراجعة {now:%Y-%m-%d} — آخر {DAYS} يوماً: {len(decided)} قراراً محسوماً، توقّع "
          f"{base / max(1, len(decided)):+.3f}R، مجموع {base:+.1f}R\n")

    print("═" * 90 + "\n(1) شروط رفض مرشّحة — ن ≥ 30، < −0.3R، سالبة بالنصفين\n" + "═" * 90)
    tp2r = lambda d: abs((d["tp2"] or d["entry"]) - d["entry"]) / max(1e-12, abs(d["entry"] - d["stop_loss"]))
    cands = [
        ("المؤشرات الأمريكية (مجموعة)", lambda d: d["group"] == "index"),
        ("الهدف الثاني ≥ 8R (وقف ضيق)", lambda d: tp2r(d) >= 8),
        ("Premium/Discount = EXTREME_DISCOUNT", lambda d: (d["premium_discount"] or "") == "EXTREME_DISCOUNT"),
        ("كل صفقات الشراء", lambda d: d["side"] == "BUY"),
    ]
    for name, f in cands:
        print(_line(name, [d["r"] for d in decided if f(d)], base))

    from app.services import shadow_stats as st
    print("\n" + "═" * 90 + "\n(2) قواعد الرفض القائمة — صفقات منعتها (بجدول الظل، نظيفة، فرص مستقلة)\n" + "═" * 90)
    every = (db.query(ShadowSignal).filter(ShadowSignal.created_at >= since,
                                           ~ShadowSignal.reason.like("tpl:%"), ShadowSignal.reason != "crypto_weekend")
               .order_by(ShadowSignal.created_at).all())
    legacy = sum(1 for s in every if not st.is_clean(s))
    sh = st.filter_scope(every, "clean")
    lv = st.filter_scope(every, "legacy_valid")
    print(f"  قديمة (قبل إصلاح المستويات): {legacy} صفاً — منها {len(lv)} سليمة تُعرض كسطر تأكيد ولا تدخل الحكم الرسمي")
    reasons = sorted({s.reason for s in sh} | {s.reason for s in lv})
    if not reasons:
        print("  لا صفقات مرفوضة نظيفة بعد")

    def _reps(rows):
        return [s for s in st.representatives(rows) if s.outcome in ("TP1_HIT", "TP2_HIT", "SL_HIT") and s.r_multiple is not None]
    for rsn in reasons:
        rows = [s for s in sh if s.reason == rsn]
        reps = _reps(rows)
        print(_line(rsn, [s.r_multiple for s in reps], base, mode="relax",
                    nets=[st.net_r(s) for s in reps], rows=len(rows)))
        # (2026-10-18) تأكيد من القديمة السليمة — نفس شروط الجديدة، لكن رأينا أرقامها قبل التسجيل فلا تُحكِّم
        lrows = [s for s in lv if s.reason == rsn]
        lreps = _reps(lrows)
        if lreps:
            la = sum(s.r_multiple for s in lreps) / len(lreps)
            ln = [x for x in (st.net_r(s) for s in lreps) if x is not None]
            lna = sum(ln) / len(ln) if ln else None
            agree = ""
            if reps:
                oa = sum(s.r_multiple for s in reps) / len(reps)
                agree = " — يتفق مع الرسمي" if (oa > 0) == (la > 0) else " — يخالف الرسمي: انتظر بيانات أكثر"
            print(f"      ↳ تأكيدي (قديمة سليمة): {len(lrows)} صفاً → {len(lreps)} فرصة، توقّع {la:+.2f}R"
                  + (f"، بعد سبريد الجدول {lna:+.2f}R" if lna is not None else "") + agree)

    print("\n" + "═" * 90 + "\n(3) قوالب الذهب بتجربة الظل مقابل المحرك\n" + "═" * 90)
    from app.services.template_shadow import SHADOW_START, SHADOW_TEMPLATES
    weeks_running = (now - SHADOW_START).days / 7
    gold_engine = [d["r"] for d in decided if d["market"] == "XAUUSD" and d["created_at"] >= SHADOW_START]
    eng_net = sum(gold_engine)
    print(f"  مدة التجربة: {weeks_running:.1f} أسبوع | المحرك للذهب بنفس الفترة: {len(gold_engine)} قرار، {eng_net:+.2f}R")
    for key in SHADOW_TEMPLATES:
        rows = (db.query(ShadowSignal).filter(ShadowSignal.reason == f"tpl:{key}", ShadowSignal.r_multiple.isnot(None))
                  .order_by(ShadowSignal.created_at).all())
        rs = [s.r_multiple for s in rows]
        weeks = {}
        eq = peak = dd = 0.0
        for s in rows:
            y, w, _ = s.created_at.isocalendar()
            weeks[(y, w)] = weeks.get((y, w), 0.0) + s.r_multiple
            eq += s.r_multiple
            peak = max(peak, eq)
            dd = min(dd, eq - peak)
        won = sum(1 for v in weeks.values() if v > 0)
        net = sum(rs)
        checks = [("أسبوعان", weeks_running >= 2), ("صافٍ موجب", net > 0), ("≥20 صفقة", len(rs) >= 20),
                  ("أغلب الأسابيع رابحة", bool(weeks) and won > len(weeks) / 2), ("تراجع < 6R", dd > -6),
                  ("يتفوّق على المحرك", net > eng_net)]
        sell_only = True   # كل قوالب التجربة باتجاه واحد (DECISIONS 15/10: لا يُعتمد قالب باتجاه واحد وحده)
        ok = all(c for _, c in checks)
        verdict = ("🟢 يجتاز الشروط — " + ("قالب باتجاه واحد: لا يُعتمد وحده، يُعرض مع نظيره" if sell_only else "مرشّح للاعتماد")) \
            if ok else "⚪ لم يجتز: " + "، ".join(n for n, c in checks if not c)
        print(f"  {key:<26} {len(rs):>3} صفقة | صافٍ {net:+.2f}R | أسابيع رابحة {won}/{len(weeks)} | تراجع {dd:.2f}R\n      {verdict}")

    print("\n" + "═" * 90 + "\n(4) كريبتو العطلة بالظل — يُعاد إن ≥ 30 صفقة ومتوسط ≥ 0R (الموعد ~09/11)\n" + "═" * 90)
    cw_all = db.query(ShadowSignal).filter(ShadowSignal.reason == "crypto_weekend").all()
    cw_rows = st.filter_scope(cw_all, "clean")
    cw = [s.r_multiple for s in st.representatives(cw_rows)
          if s.outcome in ("TP1_HIT", "TP2_HIT", "SL_HIT") and s.r_multiple is not None]
    print(f"  (نظيفة فقط: {len(cw_rows)} صفاً → {len(cw)} فرصة محسومة)")
    cw_lv = [s.r_multiple for s in st.representatives(st.filter_scope(cw_all, "legacy_valid"))
             if s.outcome in ("TP1_HIT", "TP2_HIT", "SL_HIT") and s.r_multiple is not None]
    if cw_lv:
        print(f"      ↳ تأكيدي (قديمة سليمة بقاعدة الحي): {len(cw_lv)} فرصة، متوسط {sum(cw_lv) / len(cw_lv):+.2f}R")
    if cw:
        avg = sum(cw) / len(cw)
        v = "🟢 يُعاد تداول الكريبتو بالعطلة" if len(cw) >= 30 and avg >= 0 else \
            ("⏳ عينة غير كافية بعد" if len(cw) < 30 else "🔴 يبقى الإيقاف")
        print(f"  {len(cw)} صفقة ظل، متوسط {avg:+.2f}R\n      {v}")
    else:
        print("  لا صفقات ظل مُقيَّمة بعد")
    print("\n⚠️ كل حكم هنا اقتراح للمالك حسب قاعدة مسجّلة — لا يُطبَّق شيء آلياً.")
    db.close()


if __name__ == "__main__":
    main()
