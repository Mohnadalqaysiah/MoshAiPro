"""
diag_shadow_audit.py (2026-10-18) — تدقيق كمي لصفقات الظل. **قراءة فقط**: لا يكتب بأي جدول، لا يغيّر فلتراً.

يقرأ الصفوف الفعلية من shadow_signals (و signals للمقارنة) ويحسب من القيم المخزّنة فقط:
  A) المستويات غير الصالحة/المعكوسة — حسب السبب والرمز والفريم.
  B) نتائج كل سبب قبل وبعد استبعاد غير الصالحة (عدد، مستبعد، صافي R، متوسط R، نسبة الربح).
  C) السبريد: لا توجد أسعار bid/ask مخزّنة بأي جدول (لا في shadow_signals ولا signals ولا signal_features)،
     فالسبريد الفعلي وقت كل صفقة **غير قابل للقياس**. المتاح هو جدول السبريد الثابت (spread_table.TYPICAL_SPREAD،
     "تقدير محافظ لا قياس حي") — نفس الجدول الذي تستخدمه قاعدة SL_INSIDE_SPREAD_NOISE. يُعرض الأثر كحساسية
     (×0.5، ×1، ×1.5 من الجدول) لا كرقم مقيس، مع توزيع نسبة السبريد/الوقف لكل صفقة.
  D) NO_DATA / بالانتظار / منتهية / لم تتفعّل — حسب الفريم، مع أعمار NO_DATA لتحديد ما يمكن إعادة تقييمه.
  E) التكرار: (1) تكرار الصف أو التقييم — يُفحص من البيانات، (2) نفس الفرصة عبر أسباب/فريمات مختلفة،
     (3) تداخل صفقات الظل مع صفقات أُرسلت فعلاً (جدول signals).
  F) اتساق R: يعيد حساب R من المستويات المخزّنة بصيغة الصفقات الفعلية (quality_report._r_multiple) ويقارنه بالمخزّن.

التشغيل على السيرفر (بلا إعادة بناء):
  docker exec -i moshapi_backend python - < backend/diag_shadow_audit.py
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.shadow_signal import ShadowSignal
from app.models.signal import Signal
from app.services.spread_table import typical_spread
from app.services.quality_report import _r_multiple as live_r
from app.services.shadow_levels import final_levels_valid

DECIDED = ("TP1_HIT", "TP2_HIT", "SL_HIT")
WINS = ("TP1_HIT", "TP2_HIT")


def aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def invalid_kind(s):
    """سبب عدم الصلاحية أو None. يعتمد على القيم المخزّنة فقط."""
    e, sl, t1, t2 = s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2
    if not e or not sl or not t1:
        return "missing"
    if abs(e - sl) == 0:
        return "zero_risk"
    buy = s.signal_type == "BUY"
    if (sl >= e) if buy else (sl <= e):
        return "sl_wrong_side"
    if (t1 <= e) if buy else (t1 >= e):
        return "tp1_wrong_side"
    if t2 is not None and ((t2 < t1) if buy else (t2 > t1)):
        return "tp2_before_tp1"
    return None


def stats(ss):
    d = [s for s in ss if s.outcome in DECIDED and s.r_multiple is not None]
    rs = [s.r_multiple for s in d]
    w = sum(1 for s in d if s.outcome in WINS)
    return {"n": len(d), "net": round(sum(rs), 2), "avg": round(sum(rs) / len(rs), 3) if rs else None,
            "win": round(100 * w / len(d), 1) if d else None}


def fmt(st):
    return f"ن={st['n']:<4} صافي={st['net']:>8} متوسط={str(st['avg']):>7} ربح%={st['win']}"


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "—"


def main():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    allrows = db.query(ShadowSignal).order_by(ShadowSignal.created_at).all()
    rows = [s for s in allrows if not (s.reason or "").startswith("tpl:")]
    tpl = [s for s in allrows if (s.reason or "").startswith("tpl:")]
    print(f"قراءة فعلية: shadow_signals = {len(allrows)} صفاً (قواعد رفض/عطلة: {len(rows)}، قوالب: {len(tpl)})")
    if rows:
        print(f"المدى: {aware(rows[0].created_at):%Y-%m-%d} → {aware(rows[-1].created_at):%Y-%m-%d}")

    # ── A) غير الصالحة ────────────────────────────────────────────────────────
    print("\n" + "═" * 110 + "\nA) المستويات غير الصالحة/المعكوسة\n" + "═" * 110)
    by_reason = defaultdict(list)
    for s in rows:
        by_reason[s.reason].append(s)
    for reason, ss in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        bad = [(s, invalid_kind(s)) for s in ss if invalid_kind(s)]
        print(f"\n▸ {reason}: {len(bad)} من {len(ss)} ({pct(len(bad), len(ss))})  أنواع: {dict(Counter(k for _, k in bad))}")
        if bad:
            print("   حسب الرمز:", dict(Counter(s.market for s, _ in bad).most_common(10)))
            print("   حسب الفريم:", dict(Counter(s.timeframe for s, _ in bad)))
            print("   نتائجها:", dict(Counter(s.outcome or "PENDING" for s, _ in bad)))

    # ── B) قبل/بعد الاستبعاد ─────────────────────────────────────────────────
    print("\n" + "═" * 110 + "\nB) نتائج كل سبب قبل وبعد استبعاد غير الصالحة (TP1/TP2/SL فقط — نفس ما يحسبه التقرير وdiag_review)\n" + "═" * 110)
    for reason, ss in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        ok = [s for s in ss if not invalid_kind(s)]
        before, after = stats(ss), stats(ok)
        print(f"\n▸ {reason}\n   قبل: {fmt(before)}\n   بعد: {fmt(after)}   (مستبعد من المحسومة: {before['n'] - after['n']})")

    # ── C) السبريد ───────────────────────────────────────────────────────────
    print("\n" + "═" * 110 + "\nC) السبريد — من جدول spread_table الثابت (لا bid/ask مخزّن → السبريد الفعلي غير قابل للقياس)\n" + "═" * 110)
    print("   الطريقة: تكلفة الصفقة بوحدات R = سبريد الجدول ÷ |الدخول − الوقف| (دخول+خروج = سبريد واحد كما بالباكتيست).")
    for reason, ss in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        d = [s for s in ss if not invalid_kind(s) and s.outcome in DECIDED and s.r_multiple is not None]
        cr, miss = [], 0
        for s in d:
            sp = typical_spread(s.market, s.entry_price)
            if sp is None:
                miss += 1
                continue
            cr.append((s, sp / abs(s.entry_price - s.stop_loss)))
        if not d:
            continue
        line = [f"\n▸ {reason}: محسومة صالحة={len(d)}، بلا سبريد بالجدول={miss}"]
        if cr:
            costs = sorted(c for _, c in cr)
            med = costs[len(costs) // 2]
            line.append(f"   سبريد/وقف: أدنى={costs[0]:.3f}R وسيط={med:.3f}R أقصى={costs[-1]:.3f}R")
            base = sum(s.r_multiple for s, _ in cr)
            for k in (0.0, 0.5, 1.0, 1.5):
                net = base - k * sum(c for _, c in cr)
                line.append(f"   سبريد ×{k:<3}: صافي={net:8.2f}R متوسط={net / len(cr):7.3f}R")
            if reason.startswith("SL_INSIDE_SPREAD_NOISE"):
                under = sum(1 for c in costs if c > 1 / 3)
                line.append(f"   صفقات سبريدها > ثلث الوقف (شرط القاعدة بنفس الجدول): {under} من {len(costs)}"
                            " — إن لم تكن كلها فالجدول تغيّر بعد التسجيل أو الوقف تعدّل بعد الرفض")
        print("\n".join(line))

    # ── D) حسب الفريم ────────────────────────────────────────────────────────
    print("\n" + "═" * 110 + "\nD) الحالات حسب الفريم\n" + "═" * 110)
    tf = defaultdict(Counter)
    for s in rows:
        st = s.outcome
        if st is None:
            st = "PENDING_open" if s.expires_at and aware(s.expires_at) > now else "PENDING_closed"
        tf[s.timeframe][st] += 1
    cols = ["TP1_HIT", "TP2_HIT", "SL_HIT", "EXPIRED_PROFIT", "EXPIRED_LOSS", "EXPIRED_NO_RESULT",
            "NOT_TRIGGERED", "NO_DATA", "PENDING_open", "PENDING_closed"]
    print("   فريم | " + " | ".join(c.replace("_HIT", "").replace("EXPIRED_", "EXP_") for c in cols))
    for k, c in sorted(tf.items(), key=lambda kv: str(kv[0])):
        print(f"   {str(k):>4}  | " + " | ".join(f"{c[x]:>4}" for x in cols) + f"   (ن={sum(c.values())})")
    nod = [s for s in rows if s.outcome == "NO_DATA"]
    if nod:
        ages = Counter()
        for s in nod:
            a = (now - aware(s.created_at)).days
            ages["≤55 يوماً (شموع 15m متاحة بـyfinance)" if a <= 55 else "56-700 يوم (شموع 1h فقط)" if a <= 700 else ">700 يوم"] += 1
        print("   أعمار NO_DATA:", dict(ages))
        print("   NO_DATA حسب الرمز:", dict(Counter(s.market for s in nod).most_common(10)))
    pend_closed = [s for s in rows if s.outcome is None and s.expires_at and aware(s.expires_at) <= now]
    print(f"   بالانتظار رغم انتهاء مدتها: {len(pend_closed)}"
          + (f" — أقدمها {aware(min(s.created_at for s in pend_closed)):%Y-%m-%d}" if pend_closed else ""))

    # ── E) التكرار ───────────────────────────────────────────────────────────
    print("\n" + "═" * 110 + "\nE) التكرار\n" + "═" * 110)
    hashes = Counter(s.signal_hash for s in allrows)
    print(f"   (1) صفوف بنفس البصمة: {sum(1 for v in hashes.values() if v > 1)} — "
          "والتقييم مرة واحدة لكل صف بالكود (shadow_evaluator يختار outcome IS NULL فقط)")
    # (2) نفس الفرصة: نفس الرمز والاتجاه، خلال ساعتين، والدخول ضمن 0.3%
    srt = sorted(rows, key=lambda s: (s.market, s.signal_type, aware(s.created_at)))
    clusters, cur = [], []
    for s in srt:
        if cur and cur[-1].market == s.market and cur[-1].signal_type == s.signal_type \
                and aware(s.created_at) - aware(cur[0].created_at) <= timedelta(hours=2) \
                and abs(s.entry_price - cur[0].entry_price) <= 0.003 * cur[0].entry_price:
            cur.append(s)
        else:
            if cur:
                clusters.append(cur)
            cur = [s]
    if cur:
        clusters.append(cur)
    multi = [c for c in clusters if len(c) > 1]
    print(f"   (2) {len(rows)} صفاً = {len(clusters)} فرصة مستقلة (رمز+اتجاه، ≤ساعتين، دخول ±0.3%) — "
          f"{len(multi)} فرصة مكررة تغطي {sum(len(c) for c in multi)} صفاً")
    print("       مكررة عبر أسباب مختلفة:", sum(1 for c in multi if len({s.reason for s in c}) > 1),
          "| عبر فريمات مختلفة:", sum(1 for c in multi if len({s.timeframe for s in c}) > 1))
    pairs = Counter()
    for c in multi:
        rs = sorted({s.reason for s in c})
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                pairs[(rs[i], rs[j])] += 1
    if pairs:
        print("       أكثر أزواج الأسباب تكراراً:", dict(pairs.most_common(5)))
    # (3) تداخل مع صفقات أُرسلت فعلاً
    if rows:
        live = db.query(Signal.market, Signal.signal_type, Signal.created_at, Signal.entry_price).filter(
            Signal.created_at >= rows[0].created_at - timedelta(hours=2)).all()
        idx = defaultdict(list)
        for m, t, c, e in live:
            idx[(m.upper(), t.value if hasattr(t, "value") else t)].append((aware(c), float(e or 0)))
        ov = Counter()
        for s in rows:
            for c, e in idx.get((s.market, s.signal_type), []):
                if abs(c - aware(s.created_at)) <= timedelta(hours=2) and e and abs(e - s.entry_price) <= 0.003 * e:
                    ov[s.reason] += 1
                    break
        print("   (3) صفقات ظل لها صفقة مُرسلة فعلاً بنفس الرمز والاتجاه (±ساعتين، ±0.3%):", dict(ov) or "لا شيء")

    # ── F) اتساق R ───────────────────────────────────────────────────────────
    print("\n" + "═" * 110 + "\nF) اتساق R مع صيغة الصفقات الفعلية (quality_report._r_multiple)\n" + "═" * 110)
    mism = []
    chk = 0
    for s in rows:
        if s.outcome in DECIDED and s.r_multiple is not None and not invalid_kind(s):
            lr = live_r(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, s.outcome)
            if lr is None:
                continue
            chk += 1
            if abs(lr - s.r_multiple) > 0.02:
                mism.append((s.id, s.reason, s.outcome, s.r_multiple, lr))
    print(f"   فُحص {chk} صفاً — اختلاف > 0.02R: {len(mism)}")
    for m in mism[:10]:
        print("     ", m)
    exp = Counter(s.outcome for s in rows if (s.outcome or "").startswith("EXPIRED"))
    print(f"   منتهية بلا هدف ولا وقف (مستبعدة من R بالتقرير كما بالصفقات الفعلية): {dict(exp) or 'لا شيء'}")

    # ── G) قديم مقابل جديد (levels_version) ───────────────────────────────────
    print("\n" + "═" * 110 + "\nG) السجلات قبل إصلاح المستويات (levels_version فارغ) مقابل بعده (=1)\n" + "═" * 110)
    has_ver = hasattr(ShadowSignal, "levels_version")
    old = [s for s in rows if not has_ver or s.levels_version is None]
    new = [s for s in rows if has_ver and s.levels_version is not None]
    print(f"   قديمة (قبل الإصلاح، لا تُعدَّل ولا تُحذف): {len(old)} | جديدة (بعد الإصلاح): {len(new)}")
    print("   تطبيق فحص الجهة الجديد (shadow_levels.final_levels_valid) على القديمة — قراءة فقط:")
    verdict = defaultdict(Counter)
    for s in old:
        verdict[s.reason][final_levels_valid(s.signal_type, s.entry_price, s.stop_loss,
                                             s.take_profit_1, s.take_profit_2) or "PASS"] += 1
    for reason, c in sorted(verdict.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(c.values())
        rej = {k: v for k, v in c.items() if k != "PASS"}
        print(f"     {reason}: يجتاز {c['PASS']} من {n} ({pct(c['PASS'], n)}) | يُرفض: {rej or 0}")
    if new:
        print("   الجديدة — نتائج كل سبب:")
        nb = defaultdict(list)
        for s in new:
            nb[s.reason].append(s)
        for reason, ss in sorted(nb.items(), key=lambda kv: -len(kv[1])):
            bad = sum(1 for s in ss if final_levels_valid(s.signal_type, s.entry_price, s.stop_loss,
                                                          s.take_profit_1, s.take_profit_2))
            print(f"     {reason}: {fmt(stats(ss))} | غير صالحة (يجب 0): {bad}")

    if tpl:
        print("\n" + "═" * 110 + "\nقوالب (tpl:) — محاكاة الباكتيست: نصف عند TP1 + تعادل + خصم سبريد الجدول\n" + "═" * 110)
        bt = defaultdict(list)
        for s in tpl:
            bt[s.reason].append(s.r_multiple or 0)
        for k, v in bt.items():
            print(f"   {k}: ن={len(v)} صافي={sum(v):.2f}R متوسط={sum(v) / len(v):.3f}R")
    db.close()


if __name__ == "__main__":
    main()
