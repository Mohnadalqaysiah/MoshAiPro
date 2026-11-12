"""
diag_quality_layer.py — (2026-11-12) المرحلة 1 من "طبقة الجودة" — قراءة فقط، لا يكتب شيئاً.
DECISIONS 12/11، وهي الخطوتان 2 و3 من "المنصة التي تتعلم أسبوعياً" (13/10) اللتان لم تُبنيا.

السؤال: ما ظروف السوق لحظة الإشارة (بصمة signal_features، منذ 13/10) التي تسبق الخسارة أو الربح؟
الفخ الذي يتجنّبه: "خسرنا هنا ← نمنعه" يطارد الماضي. لذلك كل نمط يمر بثلاثة فحوص على بيانات لم يُبنَ عليها:
  1) يُتعلَّم من فترة التعلّم وحدها (TRAIN_START → SPLIT)، ويُختبر على ما بعد SPLIT — أسابيع لم يرها.
  2) يجب أن يتكرر داخل أكثر من سوق (فرق الشرائح قد يكون أثر خليط الأسواق — ثبت ذلك بمسافة الوقف 06/11).
  3) يُقارَن بصفقات الظل (إشارات المحرك المرفوضة بفلتر) كمجتمع مستقل ثالث.
والقيم الرقمية التي يختلف مقياسها بين الأسواق (التقلب، البعد عن EMA…) تُقسَّم نسبةً لسوقها لا مطلقاً.

المقياس: نسبة الربح (الصفقة رابحة إن بلغت الهدف الأول) — لا تتأثر بتفعيل السلّم 01/11 كما يتأثر متوسط R،
والمتوسط بـR (إجمالي، مقياس المنصة) يُعرض بجانبها. التأمين (BREAKEVEN) خارج الحساب كقواعد المراقبة.

العتبات ثابتة هنا قبل رؤية أي رقم. ناتج هذه الأداة **مرشّحات** لا قرارات: المرحلة 2 تسجّل ما صمد كقواعد،
والمرحلة 3 تختبرها أسبوعين بالظل (درجة لكل إشارة بلا أي تغيير للعملاء). التطبيق قرار المالك.

  docker exec -i moshapi_backend python - < backend/diag_quality_layer.py
"""
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

TRAIN_START = datetime(2026, 10, 13, tzinfo=timezone.utc)   # أول بصمة (DECISIONS 13/10)
SPLIT = datetime(2026, 11, 3, tzinfo=timezone.utc)          # التعلّم قبله، والاختبار بعده
MIN_TRAIN = 25      # أقل عدد لشريحة بفترة التعلّم
EDGE_PP = 8.0       # فرق نسبة الربح عن المعدّل (نقطة مئوية) لتُعدّ الشريحة ضعيفة/قوية بالتعلّم
MIN_TEST = 12       # أقل عدد بفترة الاختبار للحكم
HOLD_PP = 4.0       # "صمد" = نفس الاتجاه بالاختبار بنصف الفرق على الأقل
MIN_GROUP = 6       # أقل عدد داخل سوق ليُحسب في فحص التكرار بالأسواق
GROUP_SHARE = 0.6   # نسبة الأسواق التي يجب أن يتكرر فيها النمط
SHADOW_MIN = 30     # أقل عدد بالظل لعرض المقارنة

CAT = ["market_state", "market_regime", "volatility", "tightening", "ltf_mode", "htf_structure", "htf_pd_zone",
       "pd_zone", "wyckoff", "kill_zone", "momentum", "displacement", "range_trap", "relaxed"]
DERIVED = ["group", "side", "timeframe", "session", "weekday", "with_h4_trend", "h4_trend", "htf_with", "ltf_with",
           "mom_with", "btc_with"]
NUM_GLOBAL = ["confidence", "rr", "momentum_score", "pd_pct"]          # مقياس واحد لكل الأسواق
NUM_GROUP = ["atr_pct", "stretch", "slope_with", "ret24_with"]        # مقياسها يختلف بالسوق ← أثلاث داخل كل سوق

NAMES = {
    "market_state": "حالة السوق", "market_regime": "نظام السوق", "volatility": "التقلب", "tightening": "تضييق المعايرة",
    "ltf_mode": "نمط الفريم الأصغر", "htf_structure": "هيكل الفريم الأكبر", "htf_pd_zone": "منطقة الفريم الأكبر",
    "pd_zone": "منطقة الخصم/العلاوة", "wyckoff": "مرحلة وايكوف", "kill_zone": "الكيلزون", "momentum": "قوة الزخم",
    "displacement": "اندفاع سعري", "range_trap": "فخ النطاق", "relaxed": "صفقة مخفَّفة (بيع بمنطقة خصم)", "group": "السوق", "side": "الاتجاه", "timeframe": "الفريم",
    "session": "الجلسة", "weekday": "اليوم", "with_h4_trend": "مع اتجاه 4 ساعات", "h4_trend": "اتجاه 4 ساعات",
    "htf_with": "اتجاه الفريم الأكبر", "ltf_with": "اتجاه الفريم الأصغر", "mom_with": "اتجاه الزخم",
    "btc_with": "اتجاه البيتكوين (للكريبتو)", "confidence": "الثقة", "rr": "العائد/المخاطرة", "momentum_score": "درجة الزخم",
    "pd_pct": "موقع السعر بالنطاق %", "atr_pct": "التقلب ATR% (نسبةً لسوقه)",
    "stretch": "بُعد السعر عن EMA50 باتجاه الصفقة (نسبةً لسوقه)", "slope_with": "ميل EMA50 باتجاه الصفقة (نسبةً لسوقه)",
    "ret24_with": "حركة 24 ساعة باتجاه الصفقة (نسبةً لسوقه)",
}
_DAYS = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


# ─── تحويل البصمة لخصائص قابلة للمقارنة ─────────────────────────────────────
def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cat(v):
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "نعم" if v else "لا"
    return str(v).upper()


def _aligned(trend, side):
    """هل الاتجاه المذكور مع الصفقة أم ضدها؟ BULL/UP مقابل BEAR/DOWN؛ غير ذلك "—"."""
    t = str(trend or "").upper()
    up, down = ("BULL" in t or "UP" in t), ("BEAR" in t or "DOWN" in t)
    if up == down:
        return "—"
    return "مع الصفقة" if up == (side == "BUY") else "ضد الصفقة"


def _session(h):
    if h is None:
        return "—"
    h = int(h)
    return ("آسيا 00-07" if h < 7 else "لندن 07-12" if h < 12 else "نيويورك 12-17" if h < 17
            else "بعد نيويورك 17-21" if h < 21 else "متأخرة 21-24")


def flatten(f: dict, side: str, timeframe: str, group: str):
    """(خصائص وصفية، خصائص رقمية). الرقمية التي لها اتجاه تُضرب بإشارة الصفقة: موجب = باتجاهها."""
    f = f or {}
    side = (side or "").upper()
    sgn = 1 if side == "BUY" else -1
    h4 = f.get("h4") or {}
    cat = {k: _cat(f.get(k)) for k in CAT}
    cat.update({
        "group": group or "—", "side": side or "—", "timeframe": timeframe or "—",
        "session": _session(f.get("hour_utc")),
        "weekday": _DAYS[f["weekday"]] if isinstance(f.get("weekday"), int) and 0 <= f["weekday"] < 7 else "—",
        "with_h4_trend": _cat(f.get("with_h4_trend")), "h4_trend": _cat(h4.get("trend")),
        "htf_with": _aligned(f.get("htf_trend"), side), "ltf_with": _aligned(f.get("ltf_trend"), side),
        "mom_with": _aligned(f.get("momentum_dir"), side),
        "btc_with": _aligned((f.get("btc_h4") or {}).get("trend"), side) if f.get("is_crypto") else "—",
    })

    def signed(v):
        return v * sgn if v is not None else None

    num = {k: _f(f.get(k)) for k in NUM_GLOBAL}
    num.update({"atr_pct": _f(f.get("atr_pct")), "stretch": signed(_f(h4.get("dist_ema_pct"))),
                "slope_with": signed(_f(h4.get("ema_slope_pct"))), "ret24_with": signed(_f(h4.get("ret_24h_pct")))})
    return cat, num


def record(t, group, r, f, side, timeframe):
    cat, num = flatten(f, side, timeframe, group)
    return {"t": t, "group": group, "r": float(r), "win": float(r) > 0, "cat": cat, "num": num}


# ─── الأثلاث (من فترة التعلّم وحدها) ───────────────────────────────────────
def _terciles(vals):
    v = sorted(x for x in vals if x is not None)
    if len(v) < 15:
        return None
    return v[len(v) // 3], v[2 * len(v) // 3]


def fit_cutoffs(train):
    groups = {r["group"] for r in train}
    return {
        "global": {k: _terciles([r["num"].get(k) for r in train]) for k in NUM_GLOBAL},
        "group": {k: {g: _terciles([r["num"].get(k) for r in train if r["group"] == g]) for g in groups} for k in NUM_GROUP},
    }


def _bucket(v, cut, show_range):
    if v is None or cut is None:
        return "—"
    a, b = cut
    name = "منخفض" if v < a else "متوسط" if v < b else "مرتفع"
    if not show_range:
        return name
    return f"{name} (<{a:g})" if v < a else f"{name} ({a:g}–{b:g})" if v < b else f"{name} (≥{b:g})"


def labels(rec, cuts):
    out = dict(rec["cat"])
    for k in NUM_GLOBAL:
        out[k] = _bucket(rec["num"].get(k), cuts["global"].get(k), True)
    for k in NUM_GROUP:
        out[k] = _bucket(rec["num"].get(k), cuts["group"][k].get(rec["group"]), False)
    return out


# ─── التقييم ──────────────────────────────────────────────────────────────
def stats(recs):
    n = len(recs)
    if not n:
        return 0, None, None
    return n, sum(r["win"] for r in recs) / n * 100, sum(r["r"] for r in recs) / n


def evaluate(train, test, shadow, cuts):
    """لكل شريحة (خاصية، قيمة) قوية أو ضعيفة بالتعلّم: هل صمدت بالاختبار؟ هل تتكرر بالأسواق؟ وما حالها بالظل؟"""
    lab = {}
    for r in train + test + shadow:
        lab[id(r)] = labels(r, cuts)
    _, base_tr, _ = stats(train)
    _, base_te, _ = stats(test)
    _, base_sh, _ = stats(shadow)
    shadow_tr = [r for r in shadow if r["t"] < SPLIT]                  # الظل بفترة التعلّم — لاختيار علامات الدرجة بلا تسريب
    _, base_sh_tr, _ = stats(shadow_tr)
    gbase = {g: stats([r for r in train if r["group"] == g])[1] for g in {r["group"] for r in train}}
    bins = {(k, v) for r in train for k, v in lab[id(r)].items() if v != "—"}
    out = []
    for feat, val in sorted(bins):
        tr = [r for r in train if lab[id(r)].get(feat) == val]
        n_tr, wr_tr, ar_tr = stats(tr)
        if n_tr < MIN_TRAIN:
            continue
        d_tr = wr_tr - base_tr
        if abs(d_tr) < EDGE_PP:
            continue
        kind = "weak" if d_tr < 0 else "strong"
        n_te, wr_te, ar_te = stats([r for r in test if lab[id(r)].get(feat) == val])
        d_te = (wr_te - base_te) if n_te else None
        held = bool(n_te >= MIN_TEST and ((kind == "weak" and d_te <= -HOLD_PP) or (kind == "strong" and d_te >= HOLD_PP)))
        k = m = 0
        if feat != "group":
            for g, gb in gbase.items():
                sub = [r for r in tr if r["group"] == g]
                if len(sub) >= MIN_GROUP and gb is not None:
                    m += 1
                    if (stats(sub)[1] < gb) == (kind == "weak"):
                        k += 1
        consistent = feat == "group" or (m >= 2 and k / m >= GROUP_SHARE)
        n_sh, wr_sh, _ = stats([r for r in shadow if lab[id(r)].get(feat) == val])
        d_sh = (wr_sh - base_sh) if n_sh >= SHADOW_MIN else None
        n_sh_tr, wr_sh_tr, _ = stats([r for r in shadow_tr if lab[id(r)].get(feat) == val])
        d_sh_tr = (wr_sh_tr - base_sh_tr) if n_sh_tr >= SHADOW_MIN else None

        def agrees(d):
            return d is not None and ((kind == "weak" and d <= -HOLD_PP) or (kind == "strong" and d >= HOLD_PP))

        out.append({"feat": feat, "val": val, "kind": kind, "n_tr": n_tr, "wr_tr": wr_tr, "ar_tr": ar_tr, "d_tr": d_tr,
                    "n_te": n_te, "wr_te": wr_te, "ar_te": ar_te, "d_te": d_te, "held": held,
                    "k": k, "m": m, "consistent": consistent, "n_sh": n_sh, "d_sh": d_sh,
                    "shadow_ok": agrees(d_sh),
                    # للدرجة: الظل بفترة التعلّم يؤكد، أو لا عيّنة ظل كافية (لا يُعاقَب ما لا يمكن فحصه)
                    "shadow_tr_ok": d_sh_tr is None or agrees(d_sh_tr)})
    return out, lab, (base_tr, base_te, base_sh)


def grade_of(lab_rec, weak_bins):
    """الدرجة من شرائح الضعف المتعلَّمة بالتعلّم وحده (لا تعرف شيئاً عن الاختبار): 0 ← A، 1 ← B، 2+ ← C."""
    hits = sum(1 for f, v in weak_bins if lab_rec.get(f) == v)
    return "A" if hits == 0 else "B" if hits == 1 else "C"


def grade_bins(res):
    """علامات الضعف التي تدخل الدرجة: ضعيفة بالتعلّم، **ومتكررة في أغلب الأسواق بالتعلّم، ويؤكدها الظل بفترة التعلّم**
    — كلها من فترة التعلّم وحدها، فلا يتسرب شيء من الاختبار. الشرطان يُسقطان شرائح الصدفة (يوم بعينه مثلاً) التي
    تميّع الدرجة: اختبار البيانات المصطنعة أظهر أن التكرار بالأسواق وحده يمرّر يوماً عشوائياً."""
    return [(c["feat"], c["val"]) for c in res if c["kind"] == "weak" and c["consistent"] and c["shadow_tr_ok"]]


def grade_table(recs, lab, weak_bins):
    by = defaultdict(list)
    for r in recs:
        g = grade_of(lab[id(r)], weak_bins)
        by[g].append(r)
        if g != "A":
            by["B+C"].append(r)
    return {g: stats(by[g]) for g in ("A", "B", "C", "B+C")}


# ─── التحميل من قاعدة البيانات ─────────────────────────────────────────────
def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def load_live(db):
    """القرارات المغلقة الفريدة (نفس closed_decisions لقواعد المراقبة) مع بصمتها.
    البصمة على ممثّل القرار، وإلا على صف آخر من نفس القرار (نفس مفتاح التجميع وضمن نافذته)."""
    from app.models.signal import Signal
    from app.models.signal_feature import SignalFeature
    from app.services.decision_grouping import DECISION_GROUP_WINDOW_MIN, decision_key
    from app.services.weekly_markets import closed_decisions

    decs = [d for d in closed_decisions(db, TRAIN_START) if d["status"] != "BREAKEVEN"]
    feats = {sf.signal_id: sf for sf in db.query(SignalFeature).filter(
        SignalFeature.signal_id.isnot(None), SignalFeature.created_at >= TRAIN_START - timedelta(days=1)).all()}
    by_key = defaultdict(list)
    ids = list(feats)
    for i in range(0, len(ids), 1000):
        for s in db.query(Signal.id, Signal.market, Signal.timeframe, Signal.signal_type, Signal.entry_price,
                          Signal.created_at).filter(Signal.id.in_(ids[i:i + 1000])).all():
            key = decision_key((s.market or "").upper(), s.timeframe, s.signal_type, s.entry_price)
            by_key[key].append((_utc(s.created_at), feats[s.id]))
    out, missing = [], 0
    for d in decs:
        sf = feats.get(d["id"])
        if sf is None:
            key = decision_key(d["market"], d["timeframe"], d["side"], d["entry"])
            near = [(abs((t - d["created_at"]).total_seconds()), x) for t, x in by_key.get(key, [])
                    if t and abs((t - d["created_at"]).total_seconds()) <= DECISION_GROUP_WINDOW_MIN * 60]
            sf = min(near, key=lambda p: p[0])[1] if near else None
        if sf is None:
            missing += 1
            continue
        out.append(record(d["created_at"], d["group"], d["r"], sf.features, d["side"], d["timeframe"]))
    return out, len(decs), missing


def load_shadow(db):
    """إشارات المحرك المرفوضة بفلتر (الظل النظيف، فرصة مستقلة واحدة، محسومة) مع بصمتها — مجتمع ثالث للمقارنة.
    تُستثنى القوالب (استراتيجية أخرى) ونسخ إصلاح FVG (متغيّر للمحرك نفسه)."""
    from app.models.market_config import MarketConfig
    from app.models.shadow_signal import ShadowSignal
    from app.models.signal_feature import SignalFeature
    from app.services import shadow_stats as st
    from app.services.weekly_markets import market_group

    cat = {r[0].upper(): (r[1] or "") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    rows = [s for s in db.query(ShadowSignal).filter(ShadowSignal.created_at >= TRAIN_START).all()
            if not (s.reason or "").startswith(("tpl:", "FVG_FIX"))]
    by_reason = defaultdict(list)
    for s in st.filter_scope(rows, "clean"):
        by_reason[s.reason].append(s)
    reps = [s for rs in by_reason.values() for s in st.representatives(rs)
            if s.outcome in st.DECIDED and s.r_multiple is not None]
    feats = {}
    ids = [s.id for s in reps]
    for i in range(0, len(ids), 1000):
        for sf in db.query(SignalFeature).filter(SignalFeature.shadow_id.in_(ids[i:i + 1000])).all():
            feats[sf.shadow_id] = sf
    out = []
    for s in reps:
        sf = feats.get(s.id)
        if sf is None:
            continue
        m = (s.market or "").upper()
        out.append(record(_utc(s.created_at), market_group(m, cat.get(m, "")), s.r_multiple, sf.features,
                          s.signal_type, s.timeframe))
    return out, len(reps)


# ─── وضع إعادة البناء ─────────────────────────────────────────────────────
# (2026-11-12) أول تشغيل: 117 من 659 قراراً فقط ببصمة — صفوف المراقبة والظل المرفوض كانت بلا بصمة (أُصلح للأمام
# بنفس اليوم). لا ننتظر أسابيع: قياسات 4 ساعات تُعاد من الشموع **المغلقة قبل لحظة الإشارة فقط** (نفس حساب
# market_fingerprint._trend_metrics حرفياً، ولا شيء من المستقبل)، ومع خصائص الإشارة المحفوظة بصفها (الثقة، العائد/المخاطرة،
# وايكوف، الخصم/العلاوة، الكيلزون، التخفيف). ما يحسبه المحرك وحده (حالة السوق، التقلب، الزخم…) لا يُعاد بناؤه.
MIN_COVERAGE = 0.7   # أقل من هذا من القرارات ببصمة محفوظة ← وضع إعادة البناء


def h4_series(df):
    """(أوقات إغلاق شموع 4h بـUTC، الإغلاق، EMA50). EMA بلا adjust سببية: قيمتها عند أي شمعة = حسابها على المقطع حتى تلك
    الشمعة، فتساوي _trend_metrics على الشموع المغلقة حتى t."""
    import pandas as pd
    if df is None or len(df) == 0 or "close" not in df.columns:
        return None
    col = next((c for c in ("datetime", "time", "timestamp", "date") if c in df.columns), None)
    times = pd.to_datetime(df[col] if col else df.index)
    times = pd.DatetimeIndex(times)
    times = times.tz_convert("UTC") if times.tz is not None else times.tz_localize("UTC")
    close = pd.to_numeric(df["close"], errors="coerce").astype(float)
    ema = close.ewm(span=50, adjust=False).mean()
    ends = [(t + pd.Timedelta(hours=4)).to_pydatetime() for t in times]
    return ends, [float(x) for x in close.values], [float(x) for x in ema.values]


def h4_metrics_at(series, t):
    """نفس market_fingerprint._trend_metrics على الشموع التي أُغلقت حتى t فقط."""
    import bisect
    if not series:
        return {}
    ends, close, ema = series
    j = bisect.bisect_right(ends, t) - 1
    if j + 1 < 56:
        return {}
    px, e_now, e_then = close[j], ema[j], ema[j - 5]
    label = "UP" if px > e_now and e_now > e_then else "DOWN" if px < e_now and e_now < e_then else "FLAT"
    ret_24h = (px / close[j - 6] - 1) * 100 if j + 1 > 7 else None
    return {"trend": label, "dist_ema_pct": round((px / e_now - 1) * 100, 3),
            "ema_slope_pct": round((e_now / e_then - 1) * 100, 3),
            "ret_24h_pct": round(ret_24h, 3) if ret_24h is not None else None}


async def _fetch_series(symbols):
    import asyncio
    from app.services.smart_data import smart_data
    sem, out = asyncio.Semaphore(4), {}

    async def one(sym):
        async with sem:
            try:
                out[sym] = h4_series(await smart_data.get_ohlcv(sym, "4h", bars=2000))
            except Exception:
                out[sym] = None

    await asyncio.gather(*(one(s) for s in symbols))
    return out


def recon_features(t, side, fields, series, btc_series, is_crypto):
    f = {"hour_utc": t.hour, "weekday": t.weekday(), **fields}
    f["h4"] = h4_metrics_at(series, t)
    if f["h4"].get("trend") in ("UP", "DOWN"):
        f["with_h4_trend"] = (f["h4"]["trend"] == "UP") == ((side or "").upper() == "BUY")
    if is_crypto:
        f["is_crypto"] = True
        f["btc_h4"] = h4_metrics_at(btc_series, t)
    return f


def load_reconstructed(db, fetch=None):
    """كل القرارات المغلقة وكل الظل المحسوم (بلا شرط بصمة) بخصائص معاد بناؤها. fetch قابل للاستبدال بالاختبار."""
    import asyncio
    from app.models.market_config import MarketConfig
    from app.models.shadow_signal import ShadowSignal
    from app.models.signal import Signal
    from app.services import shadow_stats as st
    from app.services.weekly_markets import closed_decisions, market_group

    decs = [d for d in closed_decisions(db, TRAIN_START) if d["status"] != "BREAKEVEN"]
    sig = {}
    ids = [d["id"] for d in decs]
    for i in range(0, len(ids), 1000):
        for s in db.query(Signal.id, Signal.wyckoff_phase, Signal.premium_discount, Signal.killzone, Signal.ai_confidence,
                          Signal.risk_reward_ratio, Signal.relaxed_rule).filter(Signal.id.in_(ids[i:i + 1000])).all():
            sig[s.id] = s
    rows = [s for s in db.query(ShadowSignal).filter(ShadowSignal.created_at >= TRAIN_START).all()
            if not (s.reason or "").startswith(("tpl:", "FVG_FIX"))]
    by_reason = defaultdict(list)
    for s in st.filter_scope(rows, "clean"):
        by_reason[s.reason].append(s)
    reps = [s for rs in by_reason.values() for s in st.representatives(rs)
            if s.outcome in st.DECIDED and s.r_multiple is not None]

    symbols = {d["market"] for d in decs} | {(s.market or "").upper() for s in reps} | {"BTCUSD"}
    series = (fetch or (lambda syms: asyncio.run(_fetch_series(syms))))(sorted(symbols))
    btc = series.get("BTCUSD")

    live = []
    for d in decs:
        s = sig.get(d["id"])
        fields = {} if s is None else {"wyckoff": s.wyckoff_phase, "pd_zone": s.premium_discount, "kill_zone": s.killzone,
                                       "confidence": s.ai_confidence, "rr": s.risk_reward_ratio,
                                       "relaxed": bool(s.relaxed_rule)}
        f = recon_features(d["created_at"], d["side"], fields, series.get(d["market"]), btc, d["group"] == "crypto")
        live.append(record(d["created_at"], d["group"], d["r"], f, d["side"], d["timeframe"]))
    cat = {r[0].upper(): (r[1] or "") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    shadow = []
    for s in reps:
        m, t = (s.market or "").upper(), _utc(s.created_at)
        g = market_group(m, cat.get(m, ""))
        f = recon_features(t, s.signal_type, {"confidence": s.ai_confidence, "rr": s.risk_reward_ratio},
                           series.get(m), btc, g == "crypto")
        shadow.append(record(t, g, s.r_multiple, f, s.signal_type, s.timeframe))
    with_h4 = sum(1 for r in live if r["cat"]["h4_trend"] != "—")
    return live, len(decs), with_h4, shadow


# ─── التقرير ───────────────────────────────────────────────────────────────
def _pct(x):
    return "  —  " if x is None else f"{x:4.0f}%"


def _pp(x):
    return " — " if x is None else f"{x:+.0f}"


def _line(c):
    arrow = "⬇" if c["kind"] == "weak" else "⬆"
    if c["held"] and c["consistent"] and c["shadow_ok"]:
        verdict = "✅ صمد بالاختبار، ويتكرر بالأسواق، ويؤكده الظل"
    elif c["held"]:
        missing = [x for x, ok in (("لا يتكرر بالأسواق", c["consistent"]),
                                   ("الظل لا يؤكده" if c["d_sh"] is not None else "عيّنة الظل قليلة", c["shadow_ok"])) if not ok]
        verdict = "🟡 صمد بالاختبار — " + "، ".join(missing)
    elif c["n_te"] < MIN_TEST:
        verdict = "⏳ الاختبار قليل"
    else:
        verdict = "❌ لم يصمد"
    shadow = "ظل %s (%d)" % (_pp(c["d_sh"]), c["n_sh"]) if c["d_sh"] is not None else "ظل — (%d)" % c["n_sh"]
    ar_te = "" if c["ar_te"] is None else " %+.2fR" % c["ar_te"]
    name = NAMES.get(c["feat"], c["feat"])
    return ("  %s %s: %s\n      تعلّم %3d صفقة %s (%s) %+.2fR | اختبار %3d %s (%s)%s | أسواق %d/%d | %s\n      %s"
            % (arrow, name, c["val"], c["n_tr"], _pct(c["wr_tr"]), _pp(c["d_tr"]), c["ar_tr"],
               c["n_te"], _pct(c["wr_te"]), _pp(c["d_te"]), ar_te, c["k"], c["m"], shadow, verdict))


def report(live, n_decs, missing, shadow, n_sh_total, now, mode="stored"):
    train = [r for r in live if r["t"] < SPLIT]
    test = [r for r in live if r["t"] >= SPLIT]
    print(f"طبقة الجودة — المرحلة 1 (قراءة فقط) — حتى {now:%Y-%m-%d %H:%M} UTC\n")
    if mode == "reconstructed":
        print("الوضع: إعادة بناء — قياسات 4 ساعات من الشموع المغلقة قبل لحظة كل إشارة (لا شيء من المستقبل)، مع خصائص")
        print("الإشارة المحفوظة (الثقة، العائد/المخاطرة، وايكوف، الخصم/العلاوة، الكيلزون، التخفيف) والوقت والسوق والفريم.")
        print("ما يحسبه المحرك وحده (حالة السوق، التقلب، الزخم…) غير متاح بهذا الوضع.\n")
        print(f"القرارات المغلقة منذ {TRAIN_START:%Y-%m-%d}: {n_decs} — بقياسات 4 ساعات {n_decs - missing}")
        print(f"صفقات الظل المحسومة (فرص مستقلة): {n_sh_total}\n")
    else:
        print(f"القرارات المغلقة منذ {TRAIN_START:%Y-%m-%d}: {n_decs} — ببصمة {len(live)} (بلا بصمة {missing})")
        print(f"صفقات الظل المحسومة (فرص مستقلة): {n_sh_total} — ببصمة {len(shadow)}\n")
    if len(train) < 100 or len(test) < 40:
        print(f"⚠️ البيانات قليلة (تعلّم {len(train)}، اختبار {len(test)}) — أعد التشغيل لاحقاً.")
        return
    cuts = fit_cutoffs(train)
    res, lab, (b_tr, b_te, b_sh) = evaluate(train, test, shadow, cuts)
    n, w, a = stats(train)
    print(f"فترة التعلّم ({TRAIN_START:%m-%d} → {SPLIT - timedelta(days=1):%m-%d}): {n} صفقة، ربح {w:.0f}%، متوسط {a:+.2f}R")
    n, w, a = stats(test)
    print(f"فترة الاختبار ({SPLIT:%m-%d} → الآن): {n} صفقة، ربح {w:.0f}%، متوسط {a:+.2f}R")
    print(f"الظل: {len(shadow)} صفقة، ربح {_pct(b_sh).strip()}\n")
    print("الأرقام: (الفرق عن معدّل نفس الفترة بالنقاط المئوية). \"أسواق ك/م\" = تكرر النمط في ك من م أسواق بفترة التعلّم.\n")

    for kind, title in (("weak", "⬇ ظروف تسبق الخسارة"), ("strong", "⬆ ظروف تسبق الربح")):
        cs = sorted((c for c in res if c["kind"] == kind),
                    key=lambda c: (not (c["held"] and c["consistent"] and c["shadow_ok"]), not c["held"],
                                   c["d_tr"] if kind == "weak" else -c["d_tr"]))
        good = [c for c in cs if c["held"]]
        rest = [c for c in cs if not c["held"]]
        print("=" * 72)
        print(f"{title} — {len(cs)} شريحة بارزة بالتعلّم، صمد منها بالاختبار {len(good)}")
        print("=" * 72)
        for c in good:
            print(_line(c))
        if rest:
            print(f"\n  لم تصمد أو اختبارها قليل ({len(rest)}): "
                  + "، ".join(f"{NAMES.get(c['feat'], c['feat'])}={c['val']}" for c in rest[:15])
                  + (" …" if len(rest) > 15 else ""))
        print()

    weak_bins = grade_bins(res)
    print("=" * 72)
    print(f"الدرجة المقترحة — {len(weak_bins)} علامة ضعف (من التعلّم وحده: ضعيفة، متكررة بالأسواق، ويؤكدها ظله)، تُقيَّم على ما لم تره")
    print("A = بلا علامة ضعف · B = علامة واحدة · C = علامتان فأكثر · B+C = أي علامة")
    for f_, v_ in weak_bins:
        print(f"   • {NAMES.get(f_, f_)} = {v_}")
    print("=" * 72)
    for name, recs in (("الاختبار (الحي)", test), ("التعلّم (للمقارنة فقط)", train),
                       ("الظل — فترة الاختبار", [r for r in shadow if r["t"] >= SPLIT])):
        gt = grade_table(recs, lab, weak_bins)
        print(f"  {name}:")
        for g in ("A", "B", "C", "B+C"):
            n, w, a = gt[g]
            avg = "—" if a is None else "%+.2fR" % a
            print(f"     {g:<3}: {n:>4} صفقة | ربح {_pct(w)} | متوسط {avg}")
    print("\n  داخل كل سوق (الاختبار) — A مقابل أي علامة ضعف (B+C):")
    for g in sorted({r["group"] for r in test}):
        gt = grade_table([r for r in test if r["group"] == g], lab, weak_bins)
        (na, wa, ra), (nb, wb, rb) = gt["A"], gt["B+C"]
        fa = "" if ra is None else " %+.2fR" % ra
        fb = "" if rb is None else " %+.2fR" % rb
        print(f"     {g:<8} A {na:>3} {_pct(wa)}{fa} | B+C {nb:>3} {_pct(wb)}{fb}")

    print("\nقراءة:")
    print("  • ✅ = مرشّح يُسجَّل بالمرحلة 2 كقاعدة، ثم أسبوعان بالظل (المرحلة 3). لا شيء يُطبَّق من هنا.")
    print("  • الدرجة مفيدة فقط إن كان ربح A أعلى بوضوح من B+C في **الاختبار** وداخل أغلب الأسواق — لا في التعلّم.")
    print("  • مقارنات كثيرة: شريحة واحدة صمدت وحدها قد تكون صدفة؛ الحكم الحقيقي بالظل القادم.")


def main():
    from app.database import SessionLocal
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    db = SessionLocal()
    try:
        live, n_decs, missing = load_live(db)
        mode = "stored"
        if n_decs and len(live) < MIN_COVERAGE * n_decs:
            print(f"البصمة المحفوظة تغطي {len(live)} من {n_decs} قراراً فقط ← وضع إعادة البناء (جلب شموع 4 ساعات، دقيقة تقريباً)…\n")
            live, n_decs, with_h4, shadow = load_reconstructed(db)
            missing, n_sh_total, mode = n_decs - with_h4, len(shadow), "reconstructed"
        else:
            shadow, n_sh_total = load_shadow(db)
    finally:
        db.close()
    report(live, n_decs, missing, shadow, n_sh_total, datetime.now(timezone.utc), mode)


if __name__ == "__main__":
    main()
