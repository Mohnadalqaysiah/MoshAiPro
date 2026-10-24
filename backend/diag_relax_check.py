"""
(2026-10-24) فحص قبل تخفيف فلتر — للقراءة فقط، لا يكتب شيئاً.

طلب المالك: "جهز الفحص حتى نشوف كيف ممكن نحسنه ونوقفه" — بعد أن اجتاز ZONE_CONFLICT_SELL_IN_DISCOUNT قاعدة التخفيف المسجّلة
(diag_review: 121 فرصة، +0.53R، موجب بالنصفين، والقديمة السليمة تؤكد). القاعدة نفسها لا تُمس هنا؛ هذا تفصيل لنفس الأرقام
للإجابة عن ثلاثة أسئلة قبل القرار:

  (أ) هل الربح منتشر أم مركّز؟ — حسب الفئة، الرمز، الأسبوع، الفريم، ومجموعه بدون أكبر رمز/أسبوع.
      فلتر "بيع في خصم" يربح طبيعياً بسوق هابط؛ ربح من رمز واحد بأسبوع واحد = اتجاه سوق لا ميزة.
  (ب) كم يضيف فعلاً؟ — صفقة ظل يقابلها وقتها صفقة منصة نشطة على نفس الرمز:
        نفس الاتجاه ← تكرار لا إضافة (لن تُرسل غالباً)، عكس الاتجاه ← تعارض (إشارتان متضادتان للعميل).
      الباقي = الإضافة الحقيقية المتوقعة.
  (ج) الهدف الثاني ≥ 8R بصفقات المنصة — هل ما زالت تصدر بعد 14/10 (بدء SL_INSIDE_SPREAD_NOISE وسقف TP1)؟

الأرقام: الظل نظيف فقط وفرص مستقلة (shadow_stats، نفس diag_review)، R إجمالي (قرار المالك 24/10: الأداء بنتيجة الصفقة).

    docker exec moshapi_backend python diag_relax_check.py [أيام=60]
    (قبل إعادة البناء: docker exec -i moshapi_backend python - 60 < backend/diag_relax_check.py)
"""
import sys
from datetime import datetime, timedelta, timezone

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
REASONS = ("ZONE_CONFLICT_SELL_IN_DISCOUNT", "COMMODITY_COUNTER_4H_TREND")
CUTOFF_TP2 = datetime(2026, 10, 14, tzinfo=timezone.utc)
DECIDED = ("TP1_HIT", "TP2_HIT", "SL_HIT")


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _week(d):
    y, w, _ = _aware(d).isocalendar()
    return f"{y}-W{w:02d}"


def stats(rs):
    n = len(rs)
    if not n:
        return {"n": 0, "w": 0, "avg": 0.0, "tot": 0.0, "win": 0.0}
    w = sum(1 for r in rs if r > 0)
    return {"n": n, "w": w, "avg": sum(rs) / n, "tot": sum(rs), "win": 100.0 * w / n}


def breakdown(reps, keyfn):
    """{مفتاح: stats} مرتبة بالمجموع تنازلياً."""
    groups = {}
    for s in reps:
        groups.setdefault(keyfn(s), []).append(s.r_multiple)
    return sorted(((k, stats(v)) for k, v in groups.items()), key=lambda kv: -kv[1]["tot"])


def concentration(reps, keyfn):
    """(أكبر مفتاح، حصته من المجموع، المجموع بدونه، المتوسط بدونه)."""
    b = breakdown(reps, keyfn)
    if not b:
        return None
    top, ts = b[0]
    total = sum(s.r_multiple for s in reps)
    rest = [s.r_multiple for s in reps if keyfn(s) != top]
    return {"top": top, "top_tot": ts["tot"], "share": (100.0 * ts["tot"] / total) if total > 0 else None,
            "rest_tot": sum(rest), "rest_avg": (sum(rest) / len(rest)) if rest else 0.0, "rest_n": len(rest)}


def _window(sig):
    start = _aware(sig.created_at)
    end = _aware(sig.exit_executed) or _aware(sig.expires_at) or (start + timedelta(hours=24))
    return start - timedelta(hours=1), end


def overlap(reps, platform):
    """يصنّف كل فرصة ظل: same (منصة نشطة بنفس الاتجاه)، opposite (عكسه)، none."""
    by_mkt = {}
    for p in platform:
        by_mkt.setdefault((p.market or "").upper(), []).append(p)
    out = {"same": [], "opposite": [], "none": []}
    for s in reps:
        t = _aware(s.created_at)
        kind = "none"
        for p in by_mkt.get((s.market or "").upper(), []):
            a, b = _window(p)
            if a <= t <= b:
                side = getattr(p.signal_type, "value", p.signal_type)
                if side == s.signal_type:
                    kind = "same"
                    break
                kind = "opposite"
        out[kind].append(s)
    return out


def _fmt(k, st, w=24):
    return (f"  {str(k):<{w}} ن={st['n']:<4} ربح {st['w']}/{st['n']} ({st['win']:.0f}%)   "
            f"متوسط {st['avg']:+.2f}R   مجموع {st['tot']:+.1f}R")


def report_reason(reason, reps, lv_reps, platform, group_of):
    print("═" * 92 + f"\n{reason}\n" + "═" * 92)
    if not reps:
        print("  لا فرص محسومة نظيفة")
        return
    print(_fmt("الإجمالي (نظيفة)", stats([s.r_multiple for s in reps])))
    if lv_reps:
        print(_fmt("تأكيدي: قديمة سليمة", stats([s.r_multiple for s in lv_reps])))

    for title, keyfn in (("حسب الفئة", lambda s: group_of(s.market)),
                         ("حسب الأسبوع", lambda s: _week(s.created_at)),
                         ("حسب الفريم", lambda s: s.timeframe or "?")):
        print(f"\n  ── {title}")
        for k, st in breakdown(reps, keyfn):
            print(_fmt(k, st))
    print("\n  ── حسب الرمز (3 فرص فأكثر)")
    for k, st in breakdown(reps, lambda s: s.market):
        if st["n"] >= 3:
            print(_fmt(k, st))
    small = [k for k, st in breakdown(reps, lambda s: s.market) if st["n"] < 3]
    if small:
        print(f"  (+{len(small)} رمزاً بأقل من 3 فرص)")

    print("\n  ── التركّز: هل الربح من مصدر واحد؟")
    for title, keyfn in (("أكبر رمز", lambda s: s.market), ("أكبر أسبوع", lambda s: _week(s.created_at)),
                         ("أكبر فئة", lambda s: group_of(s.market))):
        c = concentration(reps, keyfn)
        if c:
            share = f"{c['share']:.0f}% من المجموع" if c["share"] is not None else "المجموع ≤ 0"
            print(f"  {title}: {c['top']} = {c['top_tot']:+.1f}R ({share}) ← بدونه: {c['rest_tot']:+.1f}R على "
                  f"{c['rest_n']} فرصة، متوسط {c['rest_avg']:+.2f}R")

    ov = overlap(reps, platform)
    print("\n  ── الإضافة الحقيقية: هل كانت المنصة ترسل صفقة على نفس الرمز وقتها؟")
    for k, title in (("none", "لا صفقة منصة نشطة ← إضافة حقيقية"),
                     ("same", "منصة نشطة بنفس الاتجاه ← تكرار"),
                     ("opposite", "منصة نشطة بعكس الاتجاه ← تعارض")):
        print(_fmt(title, stats([s.r_multiple for s in ov[k]]), w=36))


def report_tp2(decided):
    print("═" * 92 + "\nالهدف الثاني ≥ 8R — صفقات المنصة الفعلية (مرشّح رفض جديد)\n" + "═" * 92)
    tp2r = lambda d: abs((d["tp2"] or d["entry"]) - d["entry"]) / max(1e-12, abs(d["entry"] - d["stop_loss"]))
    hits = [d for d in decided if tp2r(d) >= 8]
    before = [d["r"] for d in hits if d["created_at"] < CUTOFF_TP2]
    after = [d["r"] for d in hits if d["created_at"] >= CUTOFF_TP2]
    print(_fmt("قبل 14/10", stats(before), w=16))
    print(_fmt("بعد 14/10", stats(after), w=16))
    print("\n  ── حسب الأسبوع")
    for k, st in breakdown([type("D", (), {"r_multiple": d["r"], "created_at": d["created_at"]}) for d in hits],
                           lambda s: _week(s.created_at)):
        print(_fmt(k, st, w=16))
    if not after:
        print("\n  ✅ لا صفقات بهدف ≥ 8R بعد 14/10 — يبدو أن الفلاتر الحالية أوقفتها؛ لا حاجة لتجربة صامتة")
    elif len(after) < 10:
        print(f"\n  ⚠️ {len(after)} صفقة فقط بعد 14/10 — ما زالت تصدر لكن بقلة")


def rollback_verdict(weekly, n, avg):
    """قاعدة الرجوع المسجّلة 24/10 قبل أي نتيجة حية: أسبوعان متتاليان خاسران (مكتملان)، أو متوسط < 0R بعد 30 صفقة."""
    losing_run = 0
    for _, tot in weekly:
        losing_run = losing_run + 1 if tot < 0 else 0
        if losing_run >= 2:
            return "🔴 أعِد الفلتر — أسبوعان متتاليان خاسران"
    if n >= 30 and avg < 0:
        return f"🔴 أعِد الفلتر — متوسط {avg:+.2f}R بعد {n} صفقة"
    if n < 30:
        return f"⏳ استمر — {n}/30 صفقة، لا أسبوعين خاسرين متتاليين"
    return f"🟢 استمر — {n} صفقة، متوسط {avg:+.2f}R"


def report_live(decs, now):
    """الصفقات الحية التي مرّت بالتخفيف (signals.relaxed_rule) — أسبوعياً، مع قاعدة الرجوع."""
    print("═" * 92 + "\nالصفقات الحية المخفَّفة (بيع في خصم، 15m/1h) منذ 24/10 — قاعدة الرجوع\n" + "═" * 92)
    if not decs:
        print("  لا صفقات مخفَّفة محسومة بعد")
        return
    rs = [d["r"] for d in decs]
    print(_fmt("الإجمالي", stats(rs), w=16))
    cur = _week(now)
    by_week = breakdown([type("D", (), {"r_multiple": d["r"], "created_at": d["created_at"]}) for d in decs],
                        lambda x: _week(x.created_at))
    for k, st_ in sorted(by_week):
        print(_fmt(k + (" (جارٍ)" if k == cur else ""), st_, w=16))
    done = [(k, st_["tot"]) for k, st_ in sorted(by_week) if k != cur]
    st_all = stats(rs)
    print(f"\n  {rollback_verdict(done, st_all['n'], st_all['avg'])}")


def main():
    from app.database import SessionLocal
    from app.models.market_config import MarketConfig
    from app.models.shadow_signal import ShadowSignal
    from app.models.signal import Signal
    from app.services import shadow_stats as st
    from app.services.weekly_markets import closed_decisions, market_group

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=DAYS)
    cat = {r[0].upper(): (r[1] or "") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    group_of = lambda m: market_group((m or "").upper(), cat.get((m or "").upper(), ""))  # noqa: E731
    print(f"فحص قبل التخفيف {now:%Y-%m-%d} — آخر {DAYS} يوماً. للقراءة فقط.\n")

    platform = db.query(Signal).filter(Signal.created_at >= since - timedelta(days=4)).all()

    def reps_of(rows):
        return [s for s in st.representatives(rows) if s.outcome in DECIDED and s.r_multiple is not None]

    for reason in REASONS:
        rows = (db.query(ShadowSignal).filter(ShadowSignal.created_at >= since, ShadowSignal.reason == reason)
                  .order_by(ShadowSignal.created_at).all())
        report_reason(reason, reps_of(st.filter_scope(rows, "clean")), reps_of(st.filter_scope(rows, "legacy_valid")),
                      platform, group_of)
        print()

    decs = [d for d in closed_decisions(db, since) if d["status"] != "BREAKEVEN"]
    report_tp2(decs)
    print()
    from app.services.relax_policy import RELAX_START, RELAX_TAG
    relaxed_ids = {i for (i,) in db.query(Signal.id).filter(Signal.relaxed_rule == RELAX_TAG).all()}
    report_live([d for d in decs if d["id"] in relaxed_ids and d["created_at"] >= RELAX_START], now)
    print("\n⚠️ للقراءة فقط — لا يغيّر فلتراً ولا إعداداً. القرار للمالك.")
    db.close()


if __name__ == "__main__":
    main()
