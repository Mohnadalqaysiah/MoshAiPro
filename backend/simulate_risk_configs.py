"""
simulate_risk_configs.py
===========================
قراءة محضة — لا يعدّل صفاً ولا يمسّ المحرك ولا يُصدر إشارة.

الغرض: اختبار تعديلات إدارة المخاطرة **قبل** تطبيقها على المستخدمين،
والهدف المعلن رفع **نسبة الإشارات الرابحة** لا التوقّع وحده: نسبة ربح
29.5% لا تُباع مهما كان التوقّع موجباً، لأن المشترك يرى سبع خسائر من عشر
ويلغي قبل بلوغ الصفقة الرابحة.

لماذا لا يعتمد على النتائج المسجّلة إطلاقاً
--------------------------------------------
كل النتائج المسجّلة قبل 2026-09-16 أنتجتها حلقة رصد معطوبة (راجع
DECISIONS.md)، فالبناء عليها يقيس العطل. لكن **مدخلات** الإشارة —
الوقت والرمز والاتجاه وسعر الدخول — مكتوبة لحظة الإصدار ولا تمسّها تلك
الأعطال. فنأخذ المدخلات وحدها، ونعيد بناء المستويات بالقواعد المقترحة،
ثم **نمشي على شموع السوق الحقيقية** لنرى ماذا كانت ستفعل. الحكم من
السوق مباشرة لا من سجلّنا.

المحاذير مطبوعة لا مخفية
------------------------
 • الشموع لا تعود إلى ما لا نهاية. يُطبع بالضبط كم إشارة أمكن محاكاتها
   وكم سقطت لنقص البيانات. العينة الصغيرة مؤشر لا برهان.
 • المحاكاة تفترض التنفيذ عند سعر الدخول المسجّل بالضبط، بلا سبريد ولا
   انزلاق. فالنتائج سقف متفائل، والفروق بين الإعدادات أصدق من قيمها
   المطلقة.
 • الترتيب داخل الشمعة الواحدة غير معلوم: إن لمست الشمعة الوقف والهدف
   معاً يُرجَّح الوقف (تحفّظ) — نفس قاعدة أداة التحقق.

التشغيل:
  docker cp simulate_risk_configs.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/simulate_risk_configs.py [أيام]
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ── الإعدادات المختبَرة ────────────────────────────────────────────────
# min_sl_pct : أقل مسافة وقف مسموحة (٪ من سعر الدخول)
# mode       : "floor"  = يُوسَّع الوقف للحد الأدنى والإشارة تُتداول
#              "reject" = تُستبعد الإشارة كلياً إن كان وقفها أضيق
#              الفرق جوهري: الأول يحتفظ بالتغطية، والثاني يقلّصها.
# tp1_r/tp2_r: موضع الهدف بمضاعف المخاطرة (None = إبقاء الهدف الأصلي)
CONFIGS = [
    {"name": "الحالي (بلا تغيير)",              "min_sl_pct": None, "mode": None,     "tp1_r": None, "tp2_r": None},
    {"name": "توسيع الوقف ≥0.30%",              "min_sl_pct": 0.30, "mode": "floor",  "tp1_r": None, "tp2_r": None},
    {"name": "توسيع الوقف ≥0.50%",              "min_sl_pct": 0.50, "mode": "floor",  "tp1_r": None, "tp2_r": None},
    {"name": "استبعاد ما وقفه <0.30%",          "min_sl_pct": 0.30, "mode": "reject", "tp1_r": None, "tp2_r": None},
    {"name": "استبعاد ما وقفه <0.50%",          "min_sl_pct": 0.50, "mode": "reject", "tp1_r": None, "tp2_r": None},
    {"name": "هدف أول عند 1.0R فقط",            "min_sl_pct": None, "mode": None,     "tp1_r": 1.0,  "tp2_r": 2.0},
    {"name": "وقف ≥0.50% + هدف أول 1.0R",       "min_sl_pct": 0.50, "mode": "floor",  "tp1_r": 1.0,  "tp2_r": 2.0},
    {"name": "وقف ≥0.50% + هدف أول 1.5R",       "min_sl_pct": 0.50, "mode": "floor",  "tp1_r": 1.5,  "tp2_r": 3.0},
    {"name": "استبعاد <0.50% + هدف أول 1.0R",   "min_sl_pct": 0.50, "mode": "reject", "tp1_r": 1.0,  "tp2_r": 2.0},
]

TF_HOURS = {"1m": 2, "5m": 4, "15m": 8, "30m": 12, "1h": 24, "4h": 72, "1d": 168, "1w": 336}


def build_levels(entry, sl, tp1, tp2, is_buy, cfg):
    """
    يُعيد (الوقف، الهدف1، الهدف2) بعد تطبيق الإعداد، أو None إن استُبعدت.
    """
    risk_pct = abs(entry - sl) / entry * 100 if entry else 0
    m = cfg["min_sl_pct"]

    if m is not None and risk_pct < m:
        if cfg["mode"] == "reject":
            return None
        # floor: يُدفع الوقف لأبعد حتى يبلغ الحد الأدنى
        dist = entry * m / 100.0
        sl = entry - dist if is_buy else entry + dist

    risk = abs(entry - sl)
    if risk <= 0:
        return None

    if cfg["tp1_r"] is not None:
        tp1 = entry + risk * cfg["tp1_r"] if is_buy else entry - risk * cfg["tp1_r"]
    if cfg["tp2_r"] is not None:
        tp2 = entry + risk * cfg["tp2_r"] if is_buy else entry - risk * cfg["tp2_r"]

    return sl, tp1, tp2


def walk(candles, entry, sl, tp1, tp2, is_buy):
    """
    يمشي الشموع بالترتيب ويُعيد (النتيجة، مضاعف R، غموض).

    نفس قواعد الإنتاج: الوقف يُنهي فوراً، والهدف الأول لا يُنهي (نكمل
    لنرى هل يُبلَغ الثاني قبل الوقف)، والتعادل داخل الشمعة يُرجَّح للوقف.

    "غموض" = شمعة تحوي الوقف والهدف معاً، فالترتيب داخلها مجهول ونحكم
    بالوقف تحفّظاً. وهذا **يُحابي الإعداد الحالي** لا الجديد: الهدف
    الأقرب أكثر عرضة للوقوع بنفس شمعة الوقف. فالانحياز ضد ما نختبره —
    وإن تفوّق رغمه فالتفوّق حقيقي لا صنيعة المنهج. يُعدّ ويُطبع بدل أن
    يُفترض صغيراً.
    """
    risk = abs(entry - sl)
    has_tp2 = (tp2 > tp1) if is_buy else (tp2 < tp1)
    best = None
    ambiguous = False
    for _ts, hi, lo in candles:
        sl_hit  = (lo <= sl) if is_buy else (hi >= sl)
        tp2_hit = has_tp2 and ((hi >= tp2) if is_buy else (lo <= tp2))
        tp1_hit = (hi >= tp1) if is_buy else (lo <= tp1)
        if sl_hit and (tp1_hit or tp2_hit) and best is None:
            ambiguous = True
        if sl_hit:
            if best is None:
                return "SL", -1.0, ambiguous
            break                      # بلغ الهدف الأول ثم ارتد للوقف ⇒ يبقى ربحاً
        if tp2_hit:
            return "TP2", round(abs(tp2 - entry) / risk, 3), ambiguous
        if tp1_hit and best is None:
            best = ("TP1", round(abs(tp1 - entry) / risk, 3))
    if best:
        return best[0], best[1], ambiguous
    return None, None, ambiguous


async def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
    # (2026-09-16) شمعة 15m افتراضاً لا 5m: تشغيل 5m غطّى 4.6–6.7 أيام فقط
    # لمعظم الرموز، أي نظام سوق واحد — ولا يُبنى تعديل على المحرك عليه.
    # 15m تصل ~50 يوماً بنفس عدد الشموع، فتشمل أنظمة متعددة. الثمن خشونة
    # أكبر ⇒ غموض أكثر داخل الشمعة، وهو محسوب ومطبوع لا مُفترَض.
    tf = "15m"
    for i, a in enumerate(sys.argv):
        if a == "--tf" and i + 1 < len(sys.argv):
            tf = sys.argv[i + 1]

    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.services.decision_grouping import group_unique_decisions
    from app.services.smart_data import smart_data as _sd
    import pandas as pd

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        raw = db.query(Signal).filter(Signal.created_at >= cutoff).all()
        decisions = group_unique_decisions(raw)
        meta = {s.id: s for s in raw}

        print("=" * 100)
        print(f"محاكاة إعدادات إدارة المخاطرة — آخر {days} يوماً · شمعة {tf}")
        print("=" * 100)
        print(f"  قرارات فريدة بالفترة: {len(decisions)}")
        print("  الحكم من شموع السوق الحقيقية — لا من النتائج المسجّلة.\n")

        # ── الشموع تُجلب مرة واحدة لكل رمز ────────────────────────────
        by_symbol = defaultdict(list)
        for d in decisions:
            s = meta.get(d["id"])
            if s is not None:
                by_symbol[s.market.upper()].append(s)

        candle_cache = {}
        print(f"  جلب الشموع لـ{len(by_symbol)} رمزاً...")
        for sym in by_symbol:
            try:
                df = await _sd.get_ohlcv(sym, tf, bars=5000)
                if df is not None and len(df):
                    tcol = df["datetime"] if "datetime" in df.columns else df.index
                    ts = pd.to_datetime(tcol, utc=True)
                    rows = sorted(
                        ((t.timestamp(), float(h), float(l))
                         for t, h, l in zip(ts, df["high"], df["low"])),
                        key=lambda r: r[0],
                    )
                    candle_cache[sym] = rows
                    span_h = (rows[-1][0] - rows[0][0]) / 3600 if len(rows) > 1 else 0
                    print(f"    {sym:<10} {len(rows):>5} شمعة — تغطي {span_h/24:.1f} يوماً")
                else:
                    print(f"    {sym:<10} لا بيانات")
            except Exception as e:
                print(f"    {sym:<10} فشل: {type(e).__name__}")
            await asyncio.sleep(0.25)

        # ── المحاكاة ──────────────────────────────────────────────────
        # نقطة الانتصاف الزمنية — أساس فحص ثبات كل إعداد عبر نظامَي سوق
        stamps = sorted(
            (meta[d["id"]].created_at for d in decisions if meta.get(d["id"]) and meta[d["id"]].created_at)
        )
        def _epoch(dt):
            return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()

        split_ts = _epoch(stamps[len(stamps) // 2]) if len(stamps) >= 20 else None

        results = {c["name"]: {"rows": [], "rejected": 0, "ambig": 0} for c in CONFIGS}
        skipped_nodata = 0
        simulated = 0

        for d in decisions:
            s = meta.get(d["id"])
            if s is None:
                continue
            sym = s.market.upper()
            rows = candle_cache.get(sym)
            if not rows:
                skipped_nodata += 1
                continue

            created = s.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if not created:
                skipped_nodata += 1
                continue
            c_ts = created.timestamp()

            # الشموع يجب أن تعود للحظة الإنشاء، وإلا فالحكم على نافذة أخرى
            if rows[0][0] > c_ts:
                skipped_nodata += 1
                continue

            horizon = c_ts + TF_HOURS.get(s.timeframe, 24) * 3600
            window = [r for r in rows if c_ts <= r[0] <= horizon]
            if not window:
                skipped_nodata += 1
                continue

            try:
                entry = float(s.entry_price); sl0 = float(s.stop_loss)
                tp1_0 = float(s.take_profit_1); tp2_0 = float(s.take_profit_2 or tp1_0)
            except (TypeError, ValueError):
                skipped_nodata += 1
                continue
            is_buy = (s.signal_type.value if hasattr(s.signal_type, "value")
                      else s.signal_type) == "BUY"
            simulated += 1

            for cfg in CONFIGS:
                lv = build_levels(entry, sl0, tp1_0, tp2_0, is_buy, cfg)
                if lv is None:
                    results[cfg["name"]]["rejected"] += 1
                    continue
                sl, tp1, tp2 = lv
                outcome, r, amb = walk(window, entry, sl, tp1, tp2, is_buy)
                if outcome is None:
                    continue          # لم تُحسم داخل أفق الإشارة
                if amb:
                    results[cfg["name"]]["ambig"] += 1
                half = "أول" if (split_ts and c_ts < split_ts) else "ثانٍ"
                results[cfg["name"]]["rows"].append((sym, outcome, r, half))

        # ── التقرير ───────────────────────────────────────────────────
        print("\n" + "=" * 100)
        print("التغطية")
        print("=" * 100)
        print(f"  أمكن محاكاتها: {simulated} من {len(decisions)}")
        print(f"  سقطت لنقص شموع: {skipped_nodata}")
        if simulated < 40:
            print("  ⚠️ العينة دون 40 — النتائج مؤشر لا برهان، والفروق الصغيرة")
            print("     بين الإعدادات لا يُعتدّ بها.")

        print("\n" + "=" * 100)
        print("النتائج — مرتّبة بنسبة الربح (وهي الهدف المعلن)")
        print("=" * 100)
        print(f"  {'الإعداد':<32}{'مُتداوَلة':>9}{'مستبعَدة':>10}"
              f"{'نسبة الربح':>12}{'التوقّع':>10}{'غموض':>7}   الثبات (نصف أول ← ثانٍ)")
        print("  " + "-" * 104)

        table = []
        for cfg in CONFIGS:
            res = results[cfg["name"]]
            rows_ = res["rows"]
            n = len(rows_)
            if not n:
                continue
            wins = sum(1 for _, o, _, _ in rows_ if o in ("TP1", "TP2"))
            rs = [r for _, _, r, _ in rows_ if r is not None]
            exp = sum(rs) / len(rs) if rs else 0.0

            # نسبة الربح بكل نصف زمني — الإعداد الذي ينقلب بينهما ليس
            # تحسيناً بل ملاءمة لنظام سوق واحد.
            halves = {}
            for h in ("أول", "ثانٍ"):
                sub = [x for x in rows_ if x[3] == h]
                halves[h] = (len(sub),
                             sum(1 for x in sub if x[1] in ("TP1", "TP2")) / len(sub) * 100
                             if sub else None)
            table.append({
                "name": cfg["name"], "n": n, "rejected": res["rejected"],
                "wr": wins / n * 100, "exp": exp, "rtot": sum(rs),
                "ambig": res["ambig"], "halves": halves,
            })

        base = next((t for t in table if t["name"].startswith("الحالي")), None)
        for t in sorted(table, key=lambda x: -x["wr"]):
            mark = ""
            if base and t is not base:
                if t["wr"] > base["wr"] + 5 and t["exp"] >= base["exp"]:
                    mark = "  ★"
                elif t["wr"] < base["wr"] or t["exp"] < base["exp"]:
                    mark = "  ↓"
            n1, w1 = t["halves"]["أول"]
            n2, w2 = t["halves"]["ثانٍ"]
            if w1 is None or w2 is None or min(n1, n2) < 10:
                stab = f"عينة نصف صغيرة ({n1}←{n2})"
            else:
                gap = abs(w1 - w2)
                sign = "✓" if gap <= 15 else "⚠"
                stab = f"{sign} {w1:.0f}% ← {w2:.0f}%"
                if w1 < base["wr"] or w2 < base["wr"]:
                    stab += " (نصف دون الأساس)"
            print(f"  {t['name']:<32}{t['n']:>9}{t['rejected']:>10}"
                  f"{t['wr']:>11.1f}%{t['exp']:>+10.2f}{t['ambig']:>7}   {stab}{mark}")

        print("  " + "-" * 104)
        print("  ★ = نسبة ربح أعلى بـ5 نقاط فأكثر بلا تضحية بالتوقّع")
        print("  ↓ = أسوأ من الحالي بأحد المقياسين")
        print("  غموض = صفقات لمست الوقف والهدف بنفس الشمعة فرُجّح الوقف تحفّظاً.")
        print("          الانحياز ضد الإعداد الجديد لا معه — الهدف الأقرب أكثر")
        print("          عرضة لذلك. فتفوّقه رغم هذا الانحياز يقوّيه لا يضعفه.")
        print("  الثبات = نسبة الربح بالنصف الأول ← الثاني. الانقلاب أو فجوة")
        print("            تتجاوز 15 نقطة ⇒ ملاءمة لنظام سوق لا تحسين بنيوي.")

        # ── الأثر على الرموز المهمة ───────────────────────────────────
        print("\n" + "=" * 100)
        print("الأثر على كل رمز — نسبة الربح (الحالي ← أفضل إعداد)")
        print("=" * 100)
        # يُختار أفضل إعداد **لا يستبعد أي إشارة**: التغطية الواسعة مطلب
        # صريح من صاحب المنتج (الذهب/الفضة/النفط/الناسداك)، وإعداد يحذف
        # ثلثي الإشارات ليس مقارَناً عادلاً مهما علت نسبة ربحه.
        keeps_all = [t for t in table if t["rejected"] == 0]
        best = max(keeps_all, key=lambda x: x["wr"]) if keeps_all else None
        if base and best and best["name"] != base["name"]:
            def per_symbol(name):
                agg = defaultdict(lambda: [0, 0])
                for sym, o, _, _ in results[name]["rows"]:
                    agg[sym][0] += 1
                    if o in ("TP1", "TP2"):
                        agg[sym][1] += 1
                return agg
            a, b = per_symbol(base["name"]), per_symbol(best["name"])
            print(f"  الأفضل: {best['name']}\n")
            print(f"  {'الرمز':<12}{'عدد الآن':>9}{'عدد بعد':>9}{'ربح الآن':>11}{'ربح بعد':>11}")
            print("  " + "-" * 54)
            for sym in sorted(set(a) | set(b), key=lambda s: -a.get(s, [0])[0]):
                na, wa = a.get(sym, [0, 0])
                nb, wb = b.get(sym, [0, 0])
                if na == 0 and nb == 0:
                    continue
                print(f"  {sym:<12}{na:>9}{nb:>9}"
                      f"{(wa/na*100 if na else 0):>10.0f}%{(wb/nb*100 if nb else 0):>10.0f}%")
        else:
            print("  لا إعداد يتفوّق على الحالي بهذه العينة.")

        print("\n  ⚠️ بلا سبريد ولا انزلاق — النتائج سقف متفائل،")
        print("     والفروق بين الإعدادات أصدق من قيمها المطلقة.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
