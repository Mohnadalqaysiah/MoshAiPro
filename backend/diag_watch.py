"""
(2026-10-27) قواعد المراقبة الأربع المسجّلة مسبقاً (DECISIONS.md 27/10 "أربع قواعد مراقبة") — بطلب المالك "نعم سجل".
تُحسب **على البيانات الجديدة وحدها** (من WATCH_START): رأينا أرقام ما قبلها في diag_study فلا تُحكِّم. للقراءة فقط.
العتبات هنا حرفياً كما سُجّلت — لا تُعدَّل بعد رؤية أي رقم جديد.

  (1) الأسهم الأمريكية: ≥ 15 قراراً جديداً، مرشّح إن المتوسط < −0.3R
  (2) فريم 15m: ≥ 40 قراراً جديداً على 15m، مرشّح إن متوسطه < نصف متوسط 1h (الجديد) **و** < +0.1R
  (3) كيلزون Midnight_Open: ≥ 10 قرارات جديدة، مرشّح إن المتوسط < −0.3R
  (4) ظل ZONE_CONFLICT_BUY_IN_PREMIUM (نظيف، فرص مستقلة): أسبوعان ISO مكتملان متتاليان، صافيهما بعد سبريد الجدول موجب
      بكلٍّ منهما، ومجموع فرصهما المحسومة ≥ 20
(2026-10-30، بعد مراجعة 30/10، قرار المالك "مابدي امنع صفقات ممكن تربح")
  (5) GBPJPY: من 31/10 (بعد رؤية أرقام المراجعة)، ≥ 15 قراراً جديداً، مرشّح إن المتوسط < −0.3R
  (6) الهدف الثاني ≥ 8R: من 14/10 (سقف TP1، نفس فصل diag_relax_check المسجّل 24/10)، ≥ 30 قراراً، مرشّح إن المتوسط < −0.3R
      وسالب بالنصفين. نفس عتبات القاعدة (1). لا منع حتى يتحقق هذا ثم يقرر المالك.
(2026-11-06، المالك: "اوك يلا"، بعد تقرير الجودة وأسبوع 30/10–06/11 — رأينا أرقامهما، فتُحكمان على الجديد وحده من 07/11)
  (7) الجلسة المتأخرة 21–24 UTC (بساعة الإنشاء، تعريف quality_report._session): ≥ 30 قراراً جديداً، مرشّح إن المتوسط < −0.3R
  (8) الكريبتو على فريم 15m: ≥ 20 قراراً جديداً، مرشّح إن المتوسط < −0.3R (لإيقاف تجريبي صامت، بقرار المالك)
(2026-11-07، المالك: "بختار ب") القاعدة (2) تحققت ← إيقاف 15m عدا الذهب والمعادن من 08/11 (timeframe_pause.py)، فالقاعدة (8) صارت ضمنه
  (9)  إعادة 15m الموقوف: ≥ 40 فرصة ظل مستقلة محسومة (TF15M_PAUSE)، مرشّح للإعادة إن متوسطها ≥ +0.1R **و** ≥ نصف متوسط 1h الحي بنفس الفترة
  (10) الذهب والمعادن على 15m (الاستثناء، حي من 08/11): ≥ 30 قراراً جديداً، مرشّح للإيقاف أيضاً بنفس شرط (2): < نصف 1h و< +0.1R
(2026-11-09، المالك: "نبقيها لمدة اسبوع ومن ثم ندرسها ونقررها") عملات جديدة بالظل من 10/11 (crypto_registry.py):
  (11) لكل عملة على 1h و4h (فرص ظل مستقلة محسومة، NEW_COIN_TRIAL): ≥ 10 ← مرشّحة للفتح إن المتوسط ≥ +0.1R و≥ نصف الكريبتو
       الحي 1h/4h بنفس الفترة؛ سالبة ← لا تُفتح؛ بينهما أو أقل من 10 ← تمديد أسبوع. القراءة الأولى ~17/11. المالك يقرر.

    docker exec moshapi_backend python diag_watch.py
"""
from datetime import datetime, timedelta, timezone

WATCH_START = datetime(2026, 10, 28, tzinfo=timezone.utc)
GBPJPY_START = datetime(2026, 10, 31, tzinfo=timezone.utc)
TP1_CAP_START = datetime(2026, 10, 14, tzinfo=timezone.utc)
RULES_7_8_START = datetime(2026, 11, 7, tzinfo=timezone.utc)


def _aware(d):
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _avg(rs):
    return sum(rs) / len(rs) if rs else None


def _fmt(rs):
    if not rs:
        return "0 قرار"
    w = sum(1 for r in rs if r > 0)
    return f"{len(rs)} قراراً ({w}/{len(rs) - w})، مجموع {sum(rs):+.1f}R، متوسط {_avg(rs):+.2f}R"


def rule_simple(rs, need, thr=-0.3):
    """(1)/(3): الحالة والنص."""
    if len(rs) < need:
        return "waiting", f"⏳ {len(rs)}/{need} — لا حكم"
    return ("candidate", "🟠 مرشّح — يُعرض على المالك") if _avg(rs) < thr else ("ok", "✅ لم تتحقق — يبقى كما هو")


def rule_restore(shadow, live1h, need=40):
    """(9) عكس القاعدة (2): الموقوف يعود إن صار جيداً بما يكفي مقارنة بالحي."""
    if len(shadow) < need:
        return "waiting", f"⏳ {len(shadow)}/{need} — لا حكم، الإيقاف باقٍ"
    a, b = _avg(shadow), _avg(live1h)
    if b is None:
        return "waiting", "⏳ لا قرارات 1h حية للمقارنة"
    return ("candidate", "🟢 مرشّح للإعادة — يُعرض على المالك") if a >= 0.1 and a >= b / 2 else ("ok", "⛔ لم تتحقق — الإيقاف باقٍ")


def rule_new_coin(rs, live_crypto, need=10):
    """(11) عملة بالتجربة تُفتح للعملاء إن بلغت need ومتوسطها ≥ +0.1R و≥ نصف الكريبتو الحي (نفس شرط (9))؛
    سالبة = لا تُفتح؛ وبينهما تمديد أسبوع. المالك يقرر في كل الحالات."""
    if len(rs) < need:
        return "waiting", f"⏳ {len(rs)}/{need} — لا حكم، تمديد أسبوع"
    a, b = _avg(rs), _avg(live_crypto)
    if a < 0:
        return "reject", "⛔ سالبة — لا تُفتح"
    if a >= 0.1 and (b is None or a >= b / 2):
        return "candidate", "🟢 مرشّحة للفتح — تُعرض على المالك"
    return "extend", "🟡 موجبة دون الشرط — تمديد أسبوع"


def late_session(t) -> bool:
    """(7): نفس تعريف تقرير الجودة — ساعة الإنشاء بتوقيت UTC من 21 فصاعداً."""
    return _aware(t).hour >= 21


def rule_15m(rs15, rs1h, need=40):
    if len(rs15) < need:
        return "waiting", f"⏳ {len(rs15)}/{need} — لا حكم"
    a15, a1h = _avg(rs15), _avg(rs1h)
    if a1h is None:
        return "waiting", "⏳ لا قرارات 1h جديدة للمقارنة"
    return ("candidate", "🟠 مرشّح للدراسة") if a15 < a1h / 2 and a15 < 0.1 else ("ok", "✅ لم تتحقق — يبقى كما هو")


def rule_tp2(rs, need=30, thr=-0.3):
    """(6): نفس القاعدة (1) — العدد، والمتوسط، وسالب بالنصفين. rs مرتبة زمنياً."""
    if len(rs) < need:
        return "waiting", f"⏳ {len(rs)}/{need} — لا حكم"
    h = len(rs) // 2
    bad = _avg(rs) < thr and _avg(rs[:h]) < 0 and _avg(rs[h:]) < 0
    return ("candidate", "🟠 مرشّح — يُعرض على المالك") if bad else ("ok", "✅ لم تتحقق — لا منع")


def iso_weeks(now):
    """الأسابيع ISO المكتملة منذ WATCH_START (تبدأ الاثنين). WATCH_START أربعاء، فأسبوعه الأول جزئي ويُحسب من البداية."""
    out = []
    monday = (WATCH_START - timedelta(days=WATCH_START.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    while monday + timedelta(days=7) <= now:
        out.append((max(monday, WATCH_START), monday + timedelta(days=7)))
        monday += timedelta(days=7)
    return out


def rule_premium(items, now, need=20):
    """items = [(created_at, net_or_None)] لفرص محسومة. أسبوعان مكتملان متتاليان: صافٍ موجب بكلٍّ منهما ومجموعهما ≥ need."""
    weeks = []
    for a, b in iso_weeks(now):
        nets = [nr for t, nr in items if a <= _aware(t) < b and nr is not None]
        weeks.append((a, len(nets), sum(nets)))
    lines = [f"      {a:%Y-%m-%d}: {n} فرصة، بعد السبريد {s:+.2f}R" for a, n, s in weeks]
    for (a1, n1, s1), (a2, n2, s2) in zip(weeks, weeks[1:]):
        if s1 > 0 and s2 > 0 and n1 + n2 >= need:
            return "candidate", "🟠 مرشّح لتخفيف 15m/1h — قرار المالك", lines
    if len(weeks) < 2:
        return "waiting", f"⏳ {len(weeks)}/2 أسبوع مكتمل — لا حكم", lines
    return "ok", "✅ لم تتحقق بعد — المنع باقٍ", lines


def main():
    from app.database import SessionLocal
    from app.models.shadow_signal import ShadowSignal
    from app.models.signal import Signal
    from app.services import shadow_stats as st
    from app.services.weekly_markets import closed_decisions
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    decs = [d for d in closed_decisions(db, WATCH_START) if d["status"] != "BREAKEVEN"]
    kz = {s.id: s.killzone for s in db.query(Signal.id, Signal.killzone).filter(Signal.id.in_([d["id"] for d in decs]))} \
        if decs else {}
    print(f"قواعد المراقبة — بيانات جديدة من {WATCH_START:%Y-%m-%d} حتى {now:%Y-%m-%d %H:%M} UTC: {len(decs)} قراراً محسوماً\n")

    rs = [d["r"] for d in decs if d["group"] == "stock"]
    print(f"(1) الأسهم الأمريكية — {_fmt(rs)}\n      {rule_simple(rs, 15)[1]}\n")

    rs15 = [d["r"] for d in decs if d["timeframe"] == "15m"]
    rs1h = [d["r"] for d in decs if d["timeframe"] == "1h"]
    print(f"(2) فريم 15m — {_fmt(rs15)} | 1h للمقارنة: {_fmt(rs1h)}\n      {rule_15m(rs15, rs1h)[1]}\n")

    rs = [d["r"] for d in decs if kz.get(d["id"]) == "Midnight_Open"]
    print(f"(3) كيلزون Midnight_Open — {_fmt(rs)}\n      {rule_simple(rs, 10)[1]}\n")

    rows = st.filter_scope(db.query(ShadowSignal).filter(ShadowSignal.reason == "ZONE_CONFLICT_BUY_IN_PREMIUM",
                                                         ShadowSignal.created_at >= WATCH_START).all(), "clean")
    reps = [s for s in st.representatives(rows) if s.outcome in st.DECIDED and s.r_multiple is not None]
    _, label, lines = rule_premium([(s.created_at, st.net_r(s)) for s in reps], now)
    print(f"(4) ظل شراء في منطقة علاوة — {len(reps)} فرصة محسومة جديدة (الأسابيع المكتملة فقط):")
    print("\n".join(lines) if lines else "      لا أسبوع مكتمل بعد")
    print(f"      {label}\n")

    rs = [d["r"] for d in decs if d["market"] == "GBPJPY" and d["created_at"] >= GBPJPY_START]
    print(f"(5) GBPJPY (من {GBPJPY_START:%Y-%m-%d}) — {_fmt(rs)}\n      {rule_simple(rs, 15)[1]}\n")

    tp2r = lambda d: abs((d.get("far") or d["tp2"] or d["entry"]) - d["entry"]) / max(1e-12, abs(d["entry"] - d["stop_loss"]))
    capped = sorted((d for d in closed_decisions(db, TP1_CAP_START) if d["status"] != "BREAKEVEN" and tp2r(d) >= 8),
                    key=lambda d: d["created_at"])
    rs = [d["r"] for d in capped]
    print(f"(6) الهدف الثاني ≥ 8R (من {TP1_CAP_START:%Y-%m-%d}) — {_fmt(rs)}\n      {rule_tp2(rs)[1]}\n")

    new = [d for d in decs if d["created_at"] >= RULES_7_8_START]
    rs = [d["r"] for d in new if late_session(d["created_at"])]
    print(f"(7) الجلسة المتأخرة 21–24 UTC (من {RULES_7_8_START:%Y-%m-%d}) — {_fmt(rs)}\n      {rule_simple(rs, 30)[1]}\n")
    rs = [d["r"] for d in new if d["group"] == "crypto" and d["timeframe"] == "15m"]   # بعد 08/11 ضمن الإيقاف: لا قرارات حية
    print(f"(8) الكريبتو على 15m (من {RULES_7_8_START:%Y-%m-%d}) — {_fmt(rs)}\n      {rule_simple(rs, 20)[1]}\n")

    from app.services.timeframe_pause import EXEMPT_GROUPS, PAUSE_START, REASON
    live1h = [d["r"] for d in decs if d["timeframe"] == "1h" and d["created_at"] >= PAUSE_START]
    rows = st.filter_scope(db.query(ShadowSignal).filter(ShadowSignal.reason == REASON,
                                                         ShadowSignal.created_at >= PAUSE_START).all(), "clean")
    sh = [s.r_multiple for s in st.representatives(rows) if s.outcome in st.DECIDED and s.r_multiple is not None]
    print(f"(9) 15m الموقوف بالظل (من {PAUSE_START:%Y-%m-%d}) — {_fmt(sh)} | 1h الحي: {_fmt(live1h)}\n      {rule_restore(sh, live1h)[1]}\n")
    rs = [d["r"] for d in decs if d["timeframe"] == "15m" and d["group"] in EXEMPT_GROUPS and d["created_at"] >= PAUSE_START]
    print(f"(10) الذهب والمعادن على 15m (من {PAUSE_START:%Y-%m-%d}) — {_fmt(rs)}\n      {rule_15m(rs, live1h, need=30)[1]}\n")
    from app.services import crypto_registry as CR
    live_c = [d["r"] for d in decs if d["group"] == "crypto" and d["timeframe"] in ("1h", "4h")
              and d["created_at"] >= CR.TRIAL_START]
    rows = st.filter_scope(db.query(ShadowSignal).filter(ShadowSignal.reason == CR.REASON,
                                                         ShadowSignal.created_at >= CR.TRIAL_START).all(), "clean")
    reps = [s for s in st.representatives(rows) if s.outcome in st.DECIDED and s.r_multiple is not None]
    print(f"(11) العملات الجديدة بالظل (من {CR.TRIAL_START:%Y-%m-%d}، 1h و4h) | الكريبتو الحي 1h/4h: {_fmt(live_c)}")
    for sym in CR.symbols("trial"):
        rs = [s.r_multiple for s in reps if (s.market or "").upper() == sym and s.timeframe in ("1h", "4h")]
        print(f"      {sym:<8} {_fmt(rs)}\n               {rule_new_coin(rs, live_c)[1]}")
    rs15 = [s.r_multiple for s in reps if s.timeframe == "15m"]
    print(f"      (15m للاطلاع فقط — الكريبتو على 15m موقوف: {_fmt(rs15)})\n")
    print("⚠️ \"مرشّح\" = يُعرض على المالك. لا شيء يُطبَّق من هنا، والعتبات لا تُعدَّل بعد رؤية الأرقام.")
    db.close()


if __name__ == "__main__":
    main()
