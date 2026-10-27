"""
(2026-10-27) قواعد المراقبة الأربع المسجّلة مسبقاً (DECISIONS.md 27/10 "أربع قواعد مراقبة") — بطلب المالك "نعم سجل".
تُحسب **على البيانات الجديدة وحدها** (من WATCH_START): رأينا أرقام ما قبلها في diag_study فلا تُحكِّم. للقراءة فقط.
العتبات هنا حرفياً كما سُجّلت — لا تُعدَّل بعد رؤية أي رقم جديد.

  (1) الأسهم الأمريكية: ≥ 15 قراراً جديداً، مرشّح إن المتوسط < −0.3R
  (2) فريم 15m: ≥ 40 قراراً جديداً على 15m، مرشّح إن متوسطه < نصف متوسط 1h (الجديد) **و** < +0.1R
  (3) كيلزون Midnight_Open: ≥ 10 قرارات جديدة، مرشّح إن المتوسط < −0.3R
  (4) ظل ZONE_CONFLICT_BUY_IN_PREMIUM (نظيف، فرص مستقلة): أسبوعان ISO مكتملان متتاليان، صافيهما بعد سبريد الجدول موجب
      بكلٍّ منهما، ومجموع فرصهما المحسومة ≥ 20

    docker exec moshapi_backend python diag_watch.py
"""
from datetime import datetime, timedelta, timezone

WATCH_START = datetime(2026, 10, 28, tzinfo=timezone.utc)


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


def rule_15m(rs15, rs1h, need=40):
    if len(rs15) < need:
        return "waiting", f"⏳ {len(rs15)}/{need} — لا حكم"
    a15, a1h = _avg(rs15), _avg(rs1h)
    if a1h is None:
        return "waiting", "⏳ لا قرارات 1h جديدة للمقارنة"
    return ("candidate", "🟠 مرشّح للدراسة") if a15 < a1h / 2 and a15 < 0.1 else ("ok", "✅ لم تتحقق — يبقى كما هو")


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
    print("⚠️ \"مرشّح\" = يُعرض على المالك. لا شيء يُطبَّق من هنا، والعتبات لا تُعدَّل بعد رؤية الأرقام.")
    db.close()


if __name__ == "__main__":
    main()
