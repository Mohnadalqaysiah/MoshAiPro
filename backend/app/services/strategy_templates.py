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
- (2026-10-15) حالة الاختبار تُحسم بشروط القبول المسجّلة مسبقاً (DECISIONS.md 15/10)، لا بالانطباع:
  صافٍ موجب بعد السبريد على 30 و45 يوماً + 20 صفقة فأكثر + أغلب الأسابيع رابحة + أقصى تراجع أقل من 6R.
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


def _session_sniper(side, trend_tf=None):
    s = _SIDE[side]
    trend = [_g("اتجاه السوق", "AND", [
        _c("indicators", "trend", "اتجاه EMA50", trend_tf, s["dir"]),
    ])] if trend_tf else []
    return trend + [
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


def _silver_bullet(side):
    """(2026-11-03) ICT Silver Bullet بنسخة 15 دقيقة: الأصل على 1-5 دقائق، والمنصة تفحص من 15 دقيقة فصاعداً.
    الدخول من FVG وحده (لا Order Block) بشرط fvg_retrace، لأن شرط fvg لا يتحقق أبداً (DECISIONS 03/11). وسحب السيولة وكسر الهيكل
    يُقرآن من آخر 150 شمعة بلا ترتيب بينهما، فالنص المعروض لا يَعِد بترتيب الأصل."""
    s = _SIDE[side]
    return [
        _g("نافذة الطلقة الفضية", "AND", [
            _c("sessions", "silverbullet", "Silver Bullet", "15m"),
        ]),
        _g("سحب السيولة", "AND", [
            _c("smc", "liquidity", "Liquidity Sweep", "15m", s["dir"]),
        ]),
        _g("تأكيد الهيكل", "OR", [
            _c("smc", "choch", "CHoCH", "15m", s["dir"]),
            _c("smc", "bos", "BOS", "15m", s["dir"]),
        ]),
        _g("منطقة الدخول", "AND", [
            _c("smc", "fvg_retrace", "FVG Retrace", "15m", s["dir"]),
        ]),
    ]


_SB_DESC_AR = ("نسخة مبسّطة على 15 دقيقة من استراتيجية ICT Silver Bullet (الأصل على 1-5 دقائق): داخل نوافذها الثلاث فقط، 03-04 و10-11 و14-15 "
               "بتوقيت نيويورك، يدخل عند عودة السعر إلى FVG تكوّنت خلال آخر 3 ساعات، بوجود سحب سيولة وكسر هيكل، دون اشتراط ترتيبهما كما في الأصل.")
_SB_DESC_EN = ("A simplified 15-minute version of the ICT Silver Bullet (the original runs on 1-5 minutes): only inside its three windows, 03-04, "
               "10-11 and 14-15 New York time, it enters when price returns to an FVG formed in the last 3 hours, with a liquidity sweep and "
               "a structure break present, without requiring their exact order as the original does.")

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
        # (2026-10-15) الخطوة التالية بعد اختبار القوالب: قنّاص الجلسات ربح بيعاً وخسر شراءً بنفس الشهر الهابط —
        # الفاصل اتجاه السوق. هنا يُشترط اتجاه EMA50 على الساعة (4 ساعات جعلت قوالب الاتجاه نادرة جداً).
        "family": "gold_session_trend", "build": lambda side: _session_sniper(side, "1H"), "symbols": ["XAU/USD"],
        "timeframes": ["1H", "15m"], "style": "session", "name": "Gold Session Sniper + Trend",
        "name_ar": "قنّاص الجلسات مع الاتجاه — الذهب",
        "desc_ar": "قنّاص الجلسات نفسه، لكنه لا يدخل إلا مع اتجاه الذهب على الساعة (EMA50 مع ميله): شراء فقط والسوق صاعد، "
                   "وبيع فقط والسوق هابط. فعّل النسختين معاً ليعمل في الاتجاهين.",
        "desc_en": "The same Session Sniper, but it only trades with gold's 1H trend (EMA50 and its slope): buys only in an "
                   "uptrend, sells only in a downtrend. Activate both copies to cover both directions.",
    },
    {
        "family": "silver_trend", "build": lambda side: _gold_trend(side), "symbols": ["XAG/USD"], "timeframes": ["4H", "15m"],
        "style": "trend", "name": "Silver Trend Pro", "name_ar": "الفضة مع الاتجاه",
        "desc_ar": "نفس منطق الذهب مع الاتجاه على الفضة: اتجاه 4 ساعات + تراجع لمنطقة مناسبة + تأكيد هيكلي + منطقة دخول "
                   "على 15 دقيقة. الفضة أكثر تقلباً — الوقف يُبنى من هيكل الفضة نفسها لا من قيم الذهب.",
        "desc_en": "The gold trend logic applied to silver: 4H trend + pullback into the right zone + structure confirmation "
                   "+ entry zone on 15m. Silver is more volatile — the stop comes from silver's own structure.",
    },
    # (2026-11-03، طلب المالك) الطلقة الفضية وقوالب الناسداك والأسواق الأخرى. الشروط نفسها المختبرة على الذهب، تُحكم بشروط القبول نفسها.
    {
        "family": "gold_silver_bullet", "build": _silver_bullet, "symbols": ["XAU/USD"], "timeframes": ["15m"],
        "style": "silver_bullet", "name": "Gold Silver Bullet", "name_ar": "الطلقة الفضية — الذهب",
        "desc_ar": _SB_DESC_AR, "desc_en": _SB_DESC_EN,
    },
    {
        "family": "nas_silver_bullet", "build": _silver_bullet, "symbols": ["NAS100"], "timeframes": ["15m"],
        "style": "silver_bullet", "name": "Nasdaq Silver Bullet", "name_ar": "الطلقة الفضية — ناسداك",
        "desc_ar": _SB_DESC_AR, "desc_en": _SB_DESC_EN,
    },
    {
        "family": "nas_trend", "build": _gold_trend, "symbols": ["NAS100"], "timeframes": ["4H", "15m"],
        "style": "trend", "name": "Nasdaq Trend Pro", "name_ar": "ناسداك مع الاتجاه",
        "desc_ar": "يتداول مع اتجاه ناسداك على 4 ساعات بعد تراجع السعر لمنطقة مناسبة (خصم للشراء، علاوة للبيع)، بشرط تأكيد هيكلي "
                   "(BOS أو CHoCH) ومنطقة دخول (Order Block أو FVG) على 15 دقيقة.",
        "desc_en": "Trades with the Nasdaq's 4H trend after a pullback into the right zone (discount for buys, premium for sells), "
                   "requiring a structure confirmation (BOS or CHoCH) and an entry zone (Order Block or FVG) on 15m.",
    },
    {
        "family": "nas_liquidity", "build": _liquidity_hunter, "symbols": ["NAS100"], "timeframes": ["1H", "15m"],
        "style": "liquidity_reversal", "name": "Nasdaq Liquidity Hunter", "name_ar": "صياد السيولة — ناسداك",
        "desc_ar": "سحب سيولة على 15 دقيقة (إلزامي) في منطقة مناسبة على الساعة، ثم تأكيد انعكاس (CHoCH أو BOS) ومنطقة دخول. "
                   "سحب السيولة وحده لا يكفي.",
        "desc_en": "A liquidity sweep on 15m (mandatory) in the right 1H zone, then a reversal confirmation (CHoCH or BOS) and "
                   "an entry zone. A sweep alone is never enough.",
    },
    {
        "family": "btc_trend", "build": _gold_trend, "symbols": ["BTC/USD"], "timeframes": ["4H", "15m"],
        "style": "trend", "name": "Bitcoin Trend Pro", "name_ar": "البيتكوين مع الاتجاه",
        "desc_ar": "يتداول مع اتجاه البيتكوين على 4 ساعات بعد تراجع السعر لمنطقة مناسبة، بشرط تأكيد هيكلي ومنطقة دخول على 15 دقيقة.",
        "desc_en": "Trades with Bitcoin's 4H trend after a pullback into the right zone, requiring a structure confirmation and "
                   "an entry zone on 15m.",
    },
    {
        "family": "btc_liquidity", "build": _liquidity_hunter, "symbols": ["BTC/USD"], "timeframes": ["1H", "15m"],
        "style": "liquidity_reversal", "name": "Bitcoin Liquidity Hunter", "name_ar": "صياد السيولة — البيتكوين",
        "desc_ar": "سحب سيولة على 15 دقيقة (إلزامي) في منطقة مناسبة على الساعة، ثم تأكيد انعكاس ومنطقة دخول. سحب السيولة وحده لا يكفي.",
        "desc_en": "A liquidity sweep on 15m (mandatory) in the right 1H zone, then a reversal confirmation and an entry zone. "
                   "A sweep alone is never enough.",
    },
    {
        "family": "oil_trend", "build": _gold_trend, "symbols": ["USOIL"], "timeframes": ["4H", "15m"],
        "style": "trend", "name": "Oil Trend Pro", "name_ar": "النفط مع الاتجاه",
        "desc_ar": "يتداول مع اتجاه النفط على 4 ساعات بعد تراجع السعر لمنطقة مناسبة، بشرط تأكيد هيكلي ومنطقة دخول على 15 دقيقة.",
        "desc_en": "Trades with oil's 4H trend after a pullback into the right zone, requiring a structure confirmation and "
                   "an entry zone on 15m.",
    },
    {
        "family": "eur_session", "build": _session_sniper, "symbols": ["EUR/USD"], "timeframes": ["15m"],
        "style": "session", "name": "EUR/USD Session Sniper", "name_ar": "قنّاص الجلسات — يورو/دولار",
        "desc_ar": "فرص اليورو/دولار خلال جلستي لندن ونيويورك فقط: سحب سيولة + تأكيد هيكلي + منطقة دخول، كلها على 15 دقيقة. "
                   "الجلسة وحدها لا تطلق إشارة.",
        "desc_en": "EUR/USD setups during the London and New York sessions only: liquidity sweep + structure confirmation + "
                   "entry zone, all on 15m. The session alone never fires a signal.",
    },
]


# (2026-11-03) إعادة الاختبار بعد إصلاح شرط FVG (DECISIONS 03/11): diag_template_backtest، 45 يوماً حتى 03/11، باكتيست واقعي
# (حد أدنى للوقف + خصم السبريد)، بشروط القبول المسجّلة 15/10 كما هي. نتائج أكتوبر حُذفت لأنها قيست بشرط FVG المعطوب،
# والقوالب التي لم يُعَد اختبارها تظهر "قيد الاختبار" بلا أرقام. 16 قالباً اختُبرت معاً، فقالب يجتاز بفارق ضئيل ليس دليلاً قوياً.
_TEST_RESULTS = {
    "gold_session_sell":       {"status": "tested",   "days": 45, "trades": 62, "net_r": 16.16, "weeks_won": 5, "weeks": 7, "max_dd_r": 3.76},
    "gold_session_trend_sell": {"status": "tested",   "days": 45, "trades": 50, "net_r": 12.17, "weeks_won": 6, "weeks": 7, "max_dd_r": 4.40},
    "nas_liquidity_buy":       {"status": "tested",   "days": 45, "trades": 31, "net_r": 0.49,  "weeks_won": 4, "weeks": 7, "max_dd_r": 4.32},
    "nas_liquidity_sell":      {"status": "testing",  "days": 45, "trades": 22, "net_r": 1.55,  "weeks_won": 3, "weeks": 6, "max_dd_r": 4.35},
    "nas_trend_buy":           {"status": "negative", "days": 45, "trades": 15, "net_r": -1.06, "weeks_won": 2, "weeks": 4, "max_dd_r": 2.29},
    "nas_trend_sell":          {"status": "negative", "days": 45, "trades": 11, "net_r": -0.43, "weeks_won": 2, "weeks": 4, "max_dd_r": 4.29},
    "gold_silver_bullet_buy":  {"status": "testing",  "days": 45, "trades": 4,  "net_r": 0.77,  "weeks_won": 2, "weeks": 4, "max_dd_r": 1.10},
    "gold_silver_bullet_sell": {"status": "testing",  "days": 45, "trades": 5,  "net_r": 2.89,  "weeks_won": 2, "weeks": 3, "max_dd_r": 1.01},
    "nas_silver_bullet_buy":   {"status": "testing",  "days": 45, "trades": 5,  "net_r": 0.40,  "weeks_won": 1, "weeks": 3, "max_dd_r": 1.55},
    "nas_silver_bullet_sell":  {"status": "negative", "days": 45, "trades": 4,  "net_r": -1.78, "weeks_won": 1, "weeks": 4, "max_dd_r": 2.27},
}
# حال السوق أثناء الاختبار (21/09 → 03/11، عقود آجلة): يفسّر نجاح البيع وخسارة الشراء
MARKET_NOTE = {
    "XAU/USD": {"ar": "خلال فترة الاختبار هبط الذهب نحو 10%", "en": "gold fell about 10% during the test period"},
    "NAS100":  {"ar": "خلال فترة الاختبار هبط ناسداك نحو 8%", "en": "the Nasdaq fell about 8% during the test period"},
}


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
                "test_status": _TEST_RESULTS.get(f"{f['family']}_{side.lower()}", {}).get("status", "testing"),
                "test_result": _TEST_RESULTS.get(f"{f['family']}_{side.lower()}"),
                "test_note": MARKET_NOTE.get(f["symbols"][0]) if f"{f['family']}_{side.lower()}" in _TEST_RESULTS else None,
                "groups": groups,
            })
    return out


def get_template(key: str):
    return next((t for t in all_templates() if t["key"] == key), None)
