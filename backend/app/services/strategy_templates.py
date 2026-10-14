"""
مكتبة الاستراتيجيات الجاهزة (2026-10-14) — قوالب ثابتة بالكود، يديرها فريق المنصة لا العميل.

العميل "ينشئ نسخة" ← تصير استراتيجية عادية بحسابه (DRAFT) يعدّلها بحرية، والقالب نفسه لا يتغيّر.
كل قالب باتجاه واحد (شراء أو بيع)، وكل شرط يدعم الاتجاه تُكتب قيمته متوافقة معه — لا شرط مبهم
الاتجاه داخل قالب أحادي الاتجاه. الشروط كلها من SUPPORTED_CONDITION_TYPES فعلاً (strategy_engine.py).

قرارات مقصودة (DECISIONS.md 14/10):
- الاتجاه العام بشرط `trend` (EMA50 مع ميله — تعريف فلتر المعادن المختبر)، **لا** بشرط "اتجاه الصفقة"
  (قرار المحرك، وقد يكون WAIT) ولا بشرط EMA (السعر فوق EMA20 فقط).
- الأوزان من أوزان فئات الواجهة (SMC 18، مؤشرات 10، جلسات 6)، والعتبة = أقل درجة يبلغها أي إعداد يكمل
  كل المجموعات — فالإطلاق يقرّره منطق المجموعات، والعتبة لا تضيف شرطاً خفياً ولا تكفي وحدها.
- الحالة "قيد الاختبار": لا نتائج مثبتة. الدرجة ليست نسبة نجاح.
- القالب E (اختراق الزخم) مُلغى — لا شرط اختراق حقيقي بالمنصة.
"""
from typing import Dict, List

TEMPLATES_VERSION = 1

_W = {"smc": 18, "indicators": 10, "sessions": 6}

_SIDE = {
    "BUY":  {"dir": "صاعد", "zone": "خصم",  "ar": "شراء", "en": "Buy"},
    "SELL": {"dir": "هابط", "zone": "علاوة", "ar": "بيع",  "en": "Sell"},
}


def _c(cat, type_, label, tf, value=""):
    return {"catId": cat, "type": type_, "label": label, "timeframe": tf, "value": value, "weight": _W[cat]}


def _g(name, logic, conditions, at_least=1):
    return {"name": name, "logic": logic, "atLeast": at_least, "conditions": conditions}


def _gold_trend(side, symbol="XAU/USD"):
    s = _SIDE[side]
    return [
        _g("السياق والاتجاه", "AND", [
            _c("indicators", "trend", "اتجاه EMA50", "4H", s["dir"]),
            _c("smc", "premium", "Premium/Discount", "15m", s["zone"]),
        ]),
        _g("تأكيد الهيكل", "OR", [
            _c("smc", "bos", "BOS", "15m", s["dir"]),
            _c("smc", "choch", "CHoCH", "15m", s["dir"]),
        ]),
        _g("منطقة الدخول", "OR", [
            _c("smc", "ob", "Order Block", "15m", s["dir"]),
            _c("smc", "fvg", "FVG", "15m", s["dir"]),
        ]),
    ]


def _liquidity_hunter(side):
    s = _SIDE[side]
    return [
        _g("سحب السيولة (إلزامي)", "AND", [
            _c("smc", "liquidity", "Liquidity Sweep", "15m", s["dir"]),
        ]),
        _g("السياق", "AND", [
            _c("smc", "premium", "Premium/Discount", "1H", s["zone"]),
        ]),
        _g("تأكيد الانعكاس", "OR", [
            _c("smc", "choch", "CHoCH", "15m", s["dir"]),
            _c("smc", "bos", "BOS", "15m", s["dir"]),
        ]),
        _g("منطقة الدخول", "OR", [
            _c("smc", "ob", "Order Block", "15m", s["dir"]),
            _c("smc", "fvg", "FVG", "15m", s["dir"]),
        ]),
    ]


def _session_sniper(side):
    s = _SIDE[side]
    return [
        _g("الجلسة", "OR", [
            _c("sessions", "london", "London Session", "15m"),
            _c("sessions", "newyork", "New York Session", "15m"),
        ]),
        _g("سحب السيولة", "AND", [
            _c("smc", "liquidity", "Liquidity Sweep", "15m", s["dir"]),
        ]),
        _g("تأكيد الهيكل", "OR", [
            _c("smc", "choch", "CHoCH", "15m", s["dir"]),
            _c("smc", "bos", "BOS", "15m", s["dir"]),
        ]),
        _g("منطقة الدخول", "OR", [
            _c("smc", "ob", "Order Block", "15m", s["dir"]),
            _c("smc", "fvg", "FVG", "15m", s["dir"]),
        ]),
    ]


_FAMILIES = [
    {
        "family": "gold_trend", "build": _gold_trend, "symbols": ["XAU/USD"], "timeframes": ["4H", "15m"],
        "style": "trend", "name": "Gold Trend Pro", "name_ar": "الذهب مع الاتجاه",
        "desc_ar": "يتداول مع اتجاه الذهب على 4 ساعات بعد تراجع السعر لمنطقة مناسبة (خصم للشراء، علاوة للبيع)، "
                   "بشرط تأكيد هيكلي (BOS أو CHoCH) ومنطقة دخول (Order Block أو FVG) على 15 دقيقة. "
                   "لا يدخل لمجرد وجود منطقة دخول دون الاتجاه والتأكيد.",
        "desc_en": "Trades with gold's 4H trend after a pullback into the right zone (discount for buys, premium for sells), "
                   "requiring a structure confirmation (BOS or CHoCH) and an entry zone (Order Block or FVG) on 15m.",
    },
    {
        "family": "gold_liquidity", "build": _liquidity_hunter, "symbols": ["XAU/USD"], "timeframes": ["1H", "15m"],
        "style": "liquidity_reversal", "name": "Gold Liquidity Hunter", "name_ar": "صياد السيولة — الذهب",
        "desc_ar": "يبحث عن سحب سيولة على 15 دقيقة (إلزامي) في منطقة مناسبة على الساعة، ثم تأكيد انعكاس (CHoCH أو BOS) "
                   "ومنطقة دخول. سحب السيولة وحده لا يكفي — يلزم التأكيد.",
        "desc_en": "Looks for a liquidity sweep on 15m (mandatory) in the right 1H zone, then a reversal confirmation "
                   "(CHoCH or BOS) and an entry zone. A sweep alone is never enough.",
    },
    {
        "family": "gold_session", "build": _session_sniper, "symbols": ["XAU/USD"], "timeframes": ["15m"],
        "style": "session", "name": "Gold Session Sniper", "name_ar": "قنّاص الجلسات — الذهب",
        "desc_ar": "فرص الذهب خلال جلستي لندن ونيويورك فقط (بالتوقيت المحلي مع التوقيت الصيفي): سحب سيولة + تأكيد هيكلي "
                   "+ منطقة دخول، كلها على 15 دقيقة. الجلسة وحدها لا تطلق إشارة.",
        "desc_en": "Gold setups during the London and New York sessions only (local time, DST-aware): liquidity sweep "
                   "+ structure confirmation + entry zone, all on 15m. The session alone never fires a signal.",
    },
    {
        "family": "silver_trend", "build": lambda side: _gold_trend(side), "symbols": ["XAG/USD"], "timeframes": ["4H", "15m"],
        "style": "trend", "name": "Silver Trend Pro", "name_ar": "الفضة مع الاتجاه",
        "desc_ar": "نفس منطق الذهب مع الاتجاه على الفضة: اتجاه 4 ساعات + تراجع لمنطقة مناسبة + تأكيد هيكلي + منطقة دخول "
                   "على 15 دقيقة. الفضة أكثر تقلباً — الوقف يُبنى من هيكل الفضة نفسها لا من قيم الذهب.",
        "desc_en": "The gold trend logic applied to silver: 4H trend + pullback into the right zone + structure confirmation "
                   "+ entry zone on 15m. Silver is more volatile — the stop comes from silver's own structure.",
    },
]


def _min_score(groups: List[Dict]) -> int:
    """أقل درجة يبلغها أي إعداد يكمل كل المجموعات (AND: الكل، OR: الأخف وزناً)."""
    total = 0
    for g in groups:
        ws = sorted(c["weight"] for c in g["conditions"])
        total += sum(ws) if g["logic"] == "AND" else sum(ws[:max(1, g.get("atLeast") or 1)])
    return min(100, total)


def all_templates() -> List[Dict]:
    out = []
    for f in _FAMILIES:
        for side in ("BUY", "SELL"):
            groups = f["build"](side)
            s = _SIDE[side]
            out.append({
                "key": f"{f['family']}_{side.lower()}",
                "version": TEMPLATES_VERSION,
                "family": f["family"],
                "side": side,
                "name": f"{f['name']} — {s['en']}",
                "name_ar": f"{f['name_ar']} — {s['ar']}",
                "desc_ar": f["desc_ar"], "desc_en": f["desc_en"],
                "style": f["style"],
                "symbols": f["symbols"], "timeframes": f["timeframes"],
                "min_score": _min_score(groups),
                "exec": {"entry": "Market", "sl": "Below Swing Low" if side == "BUY" else "Above Swing High",
                         "tp": "Risk/Reward", "rr": "2"},
                "test_status": "testing",
                "groups": groups,
            })
    return out


def get_template(key: str):
    return next((t for t in all_templates() if t["key"] == key), None)
