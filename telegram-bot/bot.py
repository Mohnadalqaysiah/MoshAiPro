"""
Qaffel AI Bot v2 — Professional Edition
إعادة كتابة كاملة: تصفح احترافي، بث إشارات الأدمن، إحصائيات، إحالات
"""

import os, asyncio, aiohttp
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from loguru import logger

# ─── Config ───────────────────────────────────────────────────────────────────
API_URL      = os.getenv("API_URL",             "http://backend:8000")
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN",  "")
FRONTEND_URL = os.getenv("FRONTEND_URL",        "https://qaffel.com")
BOT_SECRET   = os.getenv("BOT_SECRET",          "mosh-bot-secret-2026")
BOT_HEADERS  = {"X-Bot-Secret": BOT_SECRET}

# ─── Market catalogue ─────────────────────────────────────────────────────────
CATEGORIES: dict[str, dict] = {
    "metals":      {"label": "🥇 معادن",   "symbols": ["XAUUSD", "XAGUSD"]},
    "crypto":      {"label": "₿ كريبتو",  "symbols": ["BTCUSD", "ETHUSD", "BNBUSD"]},
    "forex":       {"label": "💱 فوركس",   "symbols": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]},
    "commodities": {"label": "🛢 سلع",    "symbols": ["USOIL", "NATGAS"]},
    "indices":     {"label": "📈 مؤشرات", "symbols": ["NAS100", "US30", "SP500"]},
    "gulf":        {"label": "🕌 أسواق خليجية", "symbols": [
        "ARAMCO", "RAJHI", "SABIC", "STC", "SNB", "MAADEN", "ALMARAI", "BAHRI", "ALINMA",
        "EMAAR", "EMIRATESNBD", "DIB", "FAB", "ADNOCDIST", "QNBK",
    ]},
}

MARKET_NAMES: dict[str, str] = {
    "XAUUSD":"🥇 الذهب",    "XAGUSD":"🥈 الفضة",
    "BTCUSD":"₿ بيتكوين",  "ETHUSD":"Ξ إيثيريوم", "BNBUSD":"🔷 BNB",
    "EURUSD":"💶 EUR/USD",  "GBPUSD":"💷 GBP/USD",
    "USDJPY":"💴 USD/JPY",  "USDCHF":"🇨🇭 USD/CHF", "AUDUSD":"🦘 AUD/USD", "USDCAD":"🍁 USD/CAD",
    "USOIL": "🛢 نفط",     "NATGAS":"🔥 غاز",
    "NAS100":"📈 ناسداك",  "US30":  "📊 داو",       "SP500": "📉 S&P500",
    "ARAMCO":"🇸🇦 أرامكو", "RAJHI":"🇸🇦 الراجحي", "SABIC":"🇸🇦 سابك", "STC":"🇸🇦 إس تي سي",
    "SNB":"🇸🇦 الأهلي",    "MAADEN":"🇸🇦 معادن",  "ALMARAI":"🇸🇦 المراعي",
    "BAHRI":"🇸🇦 البحري",  "ALINMA":"🇸🇦 الإنماء",
    "EMAAR": "🇦🇪 إعمار",  "EMIRATESNBD":"🇦🇪 بنك الإمارات دبي الوطني", "DIB":"🇦🇪 دبي الإسلامي",
    "FAB":"🇦🇪 أبوظبي الأول", "ADNOCDIST":"🇦🇪 أدنوك للتوزيع",
    "QNBK":"🇶🇦 قطر الوطني",
}

# رموز الأسواق الخليجية — جدول تداول خاص (أيام/ساعات) مختلف عن أسبوع الفوركس،
# مطابق لـ GULF_SYMBOL_MAP/GULF_EXCHANGE_HOURS في backend/app/services/smart_data.py
GULF_MARKETS: dict[str, str] = {
    "ARAMCO": "TADAWUL", "RAJHI": "TADAWUL", "SABIC": "TADAWUL", "STC": "TADAWUL",
    "SNB": "TADAWUL", "MAADEN": "TADAWUL", "ALMARAI": "TADAWUL", "BAHRI": "TADAWUL", "ALINMA": "TADAWUL",
    "EMAAR": "DFM", "EMIRATESNBD": "DFM", "DIB": "DFM",
    "FAB": "ADX", "ADNOCDIST": "ADX",
    "QNBK": "QSE",
}
GULF_EXCHANGE_HOURS = {
    # تداول: الأحد-الخميس 10:00-15:00 بتوقيت الرياض (UTC+3) → 07:00-12:00 UTC
    "TADAWUL": ({6, 0, 1, 2, 3}, 7 * 60, 12 * 60),
    # سوق دبي المالي: الاثنين-الجمعة 10:00-14:45 بتوقيت الإمارات (UTC+4) → 06:00-10:45 UTC
    "DFM":     ({0, 1, 2, 3, 4}, 6 * 60, 10 * 60 + 45),
    # سوق أبوظبي: الاثنين-الجمعة 10:00-14:45 بتوقيت الإمارات (UTC+4) → 06:00-10:45 UTC
    "ADX":     ({0, 1, 2, 3, 4}, 6 * 60, 10 * 60 + 45),
    # بورصة قطر: الأحد-الخميس 09:30-13:00 بتوقيت الدوحة (UTC+3) → 06:30-10:00 UTC
    "QSE":     ({6, 0, 1, 2, 3}, 6 * 60 + 30, 10 * 60),
}

CRYPTO_MARKETS = {
    "BTCUSD","ETHUSD","BNBUSD","SOLUSD","XRPUSD","ADAUSD","DOTUSD",
    "LTCUSD","LINKUSD","MATICUSD","AVAXUSD","ATOMUSD","UNIUSD","TRXUSD",
}

# مجموعة الرموز المعتمدة حالياً — تُستخدم لتنقية قوائم المراقبة القديمة
_VALID_SYMBOLS: set = {sym for cat in CATEGORIES.values() for sym in cat["symbols"]}

TF_LABELS = {"15m":"15 دقيقة", "1h":"1 ساعة", "4h":"4 ساعات", "1day":"يومي"}
TIMEFRAMES = ["15m", "1h", "4h", "1day"]

# ─── Intervals ────────────────────────────────────────────────────────────────
MONITOR_INTERVAL    = 900    # 15 min — watchlist monitoring
BROADCAST_INTERVAL  = 60     # 1 min  — new admin signals
EXPIRY_INTERVAL     = 3600   # 1 hr   — subscription expiry
ALERT_COOLDOWN      = 30     # min    — per-user per-symbol same-direction cooldown (كان 60)
DIRECTION_LOCK_MIN  = 120    # min    — قفل الاتجاه (كان 240 — خُفِّف لـ 2 ساعة)

# ─── In-memory state ──────────────────────────────────────────────────────────
# uid → set of symbols
_wl_symbols:  dict[int, set]  = {}
_wl_tf:       dict[int, str]  = {}
_wl_conf:     dict[int, int]  = {}
_wl_notif:    dict[int, bool] = {}
# (uid, symbol) → {"time": datetime, "direction": "BUY"/"SELL"}
last_alert:   dict            = {}
notified_expiry: set          = set()


# عرض بشري لوقت فتح كل بورصة خليجية (محلي) — يُستخدم برسالة "السوق مغلق"
_GULF_OPEN_LOCAL = {
    "TADAWUL": ("10:00", "بتوقيت الرياض"),
    "DFM":     ("10:00", "بتوقيت الإمارات"),
    "ADX":     ("10:00", "بتوقيت الإمارات"),
    "QSE":     ("09:30", "بتوقيت الدوحة"),
}
_AR_WEEKDAY = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}


def gulf_reopen_text(exchange: str) -> str:
    """نص عربي دقيق بمتى تفتح البورصة الخليجية القادمة — بديل رسالة
    "يفتح يوم الاثنين" العامة يلي كانت مكتوبة لكل الأسواق بدون تفريق."""
    days, open_min, close_min = GULF_EXCHANGE_HOURS[exchange]
    open_label, tz_label = _GULF_OPEN_LOCAL[exchange]
    now = datetime.now(timezone.utc)
    wd = now.weekday()
    minute_of_day = now.hour * 60 + now.minute

    if wd in days and minute_of_day < open_min:
        return f"يفتح اليوم الساعة {open_label} {tz_label}"

    for delta in range(1, 8):
        cand = (wd + delta) % 7
        if cand in days:
            day_label = "غداً" if delta == 1 else _AR_WEEKDAY[cand]
            return f"يفتح {day_label} الساعة {open_label} {tz_label}"
    return f"يفتح الساعة {open_label} {tz_label}"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_market_open(symbol: str) -> bool:
    """
    فحص دقيق لحالة السوق:
    - كريبتو: مفتوح 24/7
    - أسواق خليجية: جدول أيام/ساعات خاص بكل بورصة (تداول/DFM)
    - فوركس/ذهب/نفط/مؤشرات: مغلق السبت كاملاً + الأحد حتى 22:00 UTC + الجمعة بعد 22:00 UTC
    """
    sym_up = symbol.upper()
    if sym_up in CRYPTO_MARKETS:
        return True  # كريبتو 24/7

    exchange = GULF_MARKETS.get(sym_up)
    if exchange:
        days, open_min, close_min = GULF_EXCHANGE_HOURS[exchange]
        now = datetime.now(timezone.utc)
        if now.weekday() not in days:
            return False
        minute_of_day = now.hour * 60 + now.minute
        return open_min <= minute_of_day < close_min

    now = datetime.now(timezone.utc)
    wd  = now.weekday()   # 0=Mon … 4=Fri 5=Sat 6=Sun
    # السبت كله مغلق
    if wd == 5:
        return False
    # الجمعة بعد 22:00 UTC → مغلق
    if wd == 4 and now.hour >= 22:
        return False
    # الأحد قبل 22:00 UTC → مغلق
    if wd == 6 and now.hour < 22:
        return False
    return True


def _fmt_price(v) -> str:
    if v is None:
        return "—"
    f = float(v)
    if f > 999:
        return f"{f:,.2f}"
    return f"{f:.5f}".rstrip("0").rstrip(".")


def _fmt_pts(v) -> str:
    return f"{float(v):.2f}" if v is not None else "—"


def get_confidence(data: dict) -> float:
    if not isinstance(data, dict):
        return 0.0
    return float(
        data.get("ai_confidence_score")
        or data.get("ai_confidence")
        or data.get("confidence_score")
        or (data.get("out") or {}).get("confidence")
        or (data.get("confluence") or {}).get("confidence")
        or 0
    )


async def _get(path: str, params: dict = None, timeout: int = 15) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{API_URL}{path}", params=params,
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                if r.status == 200:
                    return await r.json()
    except Exception as e:
        logger.error(f"GET {path}: {e}")
    return {}


async def _post(path: str, json=None, params: dict = None, timeout: int = 15) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{API_URL}{path}", json=json, params=params,
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                if r.status == 200:
                    return await r.json()
                body = await r.text()
                logger.warning(f"POST {path} → {r.status}: {body[:200]}")
                return {}
    except Exception as e:
        logger.error(f"POST {path}: {e}")
    return {}


async def _load_wl_from_db(uid: int, telegram_id: str):
    """يحمّل إعدادات المراقبة من DB إلى الذاكرة"""
    d = await _get("/api/v1/bot/watchlist", {"telegram_id": telegram_id})
    if d.get("linked"):
        # نفلتر فقط الرموز المعتمدة حالياً — نتجاهل أي رموز قديمة في DB
        raw = set(s.upper() for s in d.get("watchlist", []))
        _wl_symbols[uid] = raw & _VALID_SYMBOLS
        _wl_tf[uid]      = d.get("timeframe", "1h")
        _wl_conf[uid]    = d.get("min_confidence", 65)
        _wl_notif[uid]   = d.get("notifications_enabled", True)


async def _save_wl_to_db(uid: int, telegram_id: str):
    """يحفظ إعدادات المراقبة من الذاكرة إلى DB"""
    await _post(
        "/api/v1/bot/save-watchlist",
        params={
            "telegram_id":           telegram_id,
            "timeframe":             _wl_tf.get(uid, "1h"),
            "min_confidence":        str(_wl_conf.get(uid, 65)),
            "notifications_enabled": str(_wl_notif.get(uid, True)).lower(),
        },
        json=list(_wl_symbols.get(uid, set())),
    )


# ─── Keyboards ────────────────────────────────────────────────────────────────
def kb_main():
    return InlineKeyboardMarkup([
        # ── تحليل وإشارات ──
        [InlineKeyboardButton("⚡ تحليل فوري",   callback_data="m_analyze"),
         InlineKeyboardButton("📡 آخر الإشارات", callback_data="m_signals")],
        # ── مراقبة وإحصائيات ──
        [InlineKeyboardButton("👁 المراقبة",      callback_data="m_watchlist"),
         InlineKeyboardButton("📊 إحصائياتي",    callback_data="m_stats")],
        # ── إحالة ومساعدة ──
        [InlineKeyboardButton("🎁 نقاط الإحالة", callback_data="m_referral"),
         InlineKeyboardButton("❓ المساعدة",      callback_data="m_help")],
        # ── داشبورد ──
        [InlineKeyboardButton("🌐 فتح الداشبورد", url=FRONTEND_URL)],
    ])


def kb_categories(action: str):
    rows = []
    items = list(CATEGORIES.items())
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(v["label"], callback_data=f"cat_{action}_{k}")
               for k, v in items[i:i+2]]
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="m_back")])
    return InlineKeyboardMarkup(rows)


def kb_pairs(cat: str, action: str):
    syms = CATEGORIES.get(cat, {}).get("symbols", [])
    rows = []
    for i in range(0, len(syms), 2):
        row = [InlineKeyboardButton(MARKET_NAMES.get(m, m), callback_data=f"{action}_{m}")
               for m in syms[i:i+2]]
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="m_analyze")])
    return InlineKeyboardMarkup(rows)


def kb_timeframe(symbol: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TF_LABELS["15m"], callback_data=f"an_{symbol}_15m"),
         InlineKeyboardButton(TF_LABELS["1h"],  callback_data=f"an_{symbol}_1h")],
        [InlineKeyboardButton(TF_LABELS["4h"],  callback_data=f"an_{symbol}_4h"),
         InlineKeyboardButton(TF_LABELS["1day"],callback_data=f"an_{symbol}_1day")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="m_analyze")],
    ])


def kb_watchlist(uid: int):
    wl = _wl_symbols.get(uid, set())
    rows = []
    for cat_k, cat_v in CATEGORIES.items():
        rows.append([InlineKeyboardButton(f"── {cat_v['label']} ──", callback_data="noop")])
        syms = cat_v["symbols"]
        for i in range(0, len(syms), 2):
            row = []
            for m in syms[i:i+2]:
                icon = "✅" if m in wl else "○"
                row.append(InlineKeyboardButton(f"{icon} {MARKET_NAMES.get(m,m)}", callback_data=f"wl_t_{m}"))
            rows.append(row)
    rows.append([
        InlineKeyboardButton("✅ تحديد الكل", callback_data="wl_all"),
        InlineKeyboardButton("✖ إلغاء الكل", callback_data="wl_none"),
    ])
    notif = _wl_notif.get(uid, True)
    notif_icon = "🔔" if notif else "🔕"
    rows.append([
        InlineKeyboardButton("⏱ الإطار الزمني",       callback_data="wl_tf"),
        InlineKeyboardButton("🎯 الحد الأدنى للثقة", callback_data="wl_conf"),
    ])
    rows.append([
        InlineKeyboardButton(f"{notif_icon} الإشعارات: {'مفعّل' if notif else 'موقف'}", callback_data="wl_notif"),
    ])
    rows.append([
        InlineKeyboardButton("💾 حفظ الإعدادات", callback_data="wl_save"),
        InlineKeyboardButton("🔙 رجوع",           callback_data="m_back"),
    ])
    return InlineKeyboardMarkup(rows)


def kb_tf_select(back: str = "m_watchlist"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TF_LABELS["15m"], callback_data="wltf_15m"),
         InlineKeyboardButton(TF_LABELS["1h"],  callback_data="wltf_1h")],
        [InlineKeyboardButton(TF_LABELS["4h"],  callback_data="wltf_4h"),
         InlineKeyboardButton(TF_LABELS["1day"],callback_data="wltf_1day")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=back)],
    ])


def kb_conf_select():
    lvls = [50, 60, 65, 70, 75, 80]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{l}%", callback_data=f"wlconf_{l}") for l in lvls[:3]],
        [InlineKeyboardButton(f"{l}%", callback_data=f"wlconf_{l}") for l in lvls[3:]],
        [InlineKeyboardButton("🔙 رجوع", callback_data="m_watchlist")],
    ])


# ─── Formatters ───────────────────────────────────────────────────────────────
def fmt_analysis(data: dict, symbol: str, timeframe: str) -> str:
    if not data or data.get("error"):
        return f"❌ تعذر تحليل {symbol}."

    rec        = data.get("recommendation", "WATCH")
    emoji      = {"BUY":"🟢","SELL":"🔴","WATCH":"⚪","WAIT":"⚪"}.get(rec, "⚪")
    rec_ar     = {"BUY":"شراء","SELL":"بيع","WATCH":"مراقبة","WAIT":"انتظار"}.get(rec, rec)
    conf       = get_confidence(data)
    price      = data.get("current_price", 0)
    lvls       = data.get("levels", {})
    trade_type = data.get("trade_type", "")        # SWING | SCALP | WAIT
    tt_label   = data.get("trade_type_label", "")  # Arabic label with emoji
    tt_warning = data.get("trade_type_warning")    # Optional warning string

    entry_min = lvls.get("entry_zone_min")
    entry_max = lvls.get("entry_zone_max")
    entry_v   = lvls.get("entry") or (data.get("entry_zones") or [None])[0]
    sl  = lvls.get("stop_loss") or data.get("stop_loss_zone")
    tp1 = lvls.get("tp1") or (data.get("take_profit_zones") or [None])[0]
    tp2 = lvls.get("tp2")
    if not tp2 and len(data.get("take_profit_zones") or []) > 1:
        tp2 = data["take_profit_zones"][1]
    rr  = lvls.get("risk_reward") or data.get("risk_reward_ratio")

    # ── Smart Mode header ─────────────────────────────────────────────────────
    if rec in ("BUY", "SELL") and tt_label:
        mode_line = f"{tt_label}\n"
        if trade_type == "SWING":
            mode_line += "🎯 اتجاه رئيسي مع HTF\n"
        elif trade_type == "SCALP":
            mode_line += "⏱️ صفقة سريعة — خروج عند TP1\n"
        if tt_warning:
            mode_line += f"{tt_warning}\n"
        mode_line += "\n"
    elif rec == "WAIT":
        mode_line = "⏳ *انتظار (NO TRADE)*\nلا يوجد إعداد واضح حالياً.\n\n"
    else:
        mode_line = ""

    msg = (
        f"🤖 *Qaffel AI — تحليل*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{MARKET_NAMES.get(symbol,symbol)}*  │  `{timeframe}`  │  `{_fmt_price(price)}`\n\n"
        + mode_line +
        f"{emoji} *{rec_ar}*   ·   ثقة `{conf:.1f}%`\n\n"
    )
    if entry_min and entry_max:
        msg += f"🎯 دخول:  `{_fmt_price(entry_min)} – {_fmt_price(entry_max)}`\n"
    elif entry_v:
        msg += f"🎯 دخول:  `{_fmt_price(entry_v)}`\n"
    if sl:  msg += f"🛑 وقف:   `{_fmt_price(sl)}`\n"
    if tp1: msg += f"✅ هدف 1: `{_fmt_price(tp1)}`\n"
    if tp2: msg += f"✅ هدف 2: `{_fmt_price(tp2)}`\n"
    if rr:  msg += f"⚖️ R/R:   `{float(rr):.2f}x`\n"

    ob  = data.get("order_blocks", {})
    wyc = data.get("wyckoff_analysis") or data.get("wyckoff", {})
    pdz = data.get("premium_discount", {})
    liq = data.get("liquidity_analysis") or data.get("liquidity", {})

    bull_obs = ob.get("bullish_obs") or []
    bear_obs = ob.get("bearish_obs") or []
    if bull_obs and isinstance(bull_obs[0], dict):
        o = bull_obs[0]
        msg += f"🟢 OB دعم:      `{_fmt_price(o.get('low'))} – {_fmt_price(o.get('high'))}`\n"
    if bear_obs and isinstance(bear_obs[0], dict):
        o = bear_obs[0]
        msg += f"🔴 OB مقاومة:   `{_fmt_price(o.get('low'))} – {_fmt_price(o.get('high'))}`\n"

    liq_bias = (liq.get("bias", {}) if isinstance(liq, dict) else {})
    liq_bias = liq_bias if isinstance(liq_bias, dict) else {}
    ssl = (liq.get("nearest_ssl") if isinstance(liq, dict) else None) or liq_bias.get("below_price")
    bsl = (liq.get("nearest_bsl") if isinstance(liq, dict) else None) or liq_bias.get("above_price")
    if ssl: msg += f"🧲 سيولة تحت:  `{_fmt_price(ssl)}`\n"
    if bsl: msg += f"🧲 سيولة فوق:  `{_fmt_price(bsl)}`\n"

    PHASE_AR = {"ACCUMULATION":"تراكم","DISTRIBUTION":"توزيع","MARKUP":"صعود",
                "MARKDOWN":"هبوط","RE_ACCUMULATION":"إعادة تراكم","ACCUMULATION_START":"بداية تراكم"}
    ZONE_AR  = {"PREMIUM":"منطقة مرتفعة","DISCOUNT":"منطقة منخفضة","EQUILIBRIUM":"توازن"}
    phase = wyc.get("phase") if isinstance(wyc, dict) else None
    zone  = (pdz.get("current_zone") or pdz.get("zone")) if isinstance(pdz, dict) else None
    if phase: msg += f"📐 Wyckoff:     `{PHASE_AR.get(phase, phase)}`\n"
    if zone:  msg += f"💹 Zone:        `{ZONE_AR.get(zone, zone)}`\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    return msg


def fmt_new_signal(s: dict) -> str:
    """تنسيق إشارة الأدمن للبث الفوري"""
    stype      = s.get("signal_type", "BUY")
    emoji      = "🟢" if stype == "BUY" else "🔴"
    rec_ar     = "شراء" if stype == "BUY" else "بيع"
    mname      = MARKET_NAMES.get(s.get("market",""), s.get("market",""))
    conf       = get_confidence(s)
    tf         = TF_LABELS.get(s.get("timeframe",""), s.get("timeframe",""))
    entry      = _fmt_price(s.get("entry_price"))
    sl         = _fmt_price(s.get("stop_loss"))
    tp1        = _fmt_price(s.get("take_profit_1"))
    tp2        = _fmt_price(s.get("take_profit_2"))
    rr         = s.get("risk_reward_ratio")
    trade_type = s.get("trade_type", "")
    tt_label   = s.get("trade_type_label", "")
    tt_warning = s.get("trade_type_warning")

    # ── Smart Mode line ───────────────────────────────────────────────────────
    if trade_type == "SWING" and tt_label:
        mode_line = f"{tt_label}  ·  🎯 اتجاه رئيسي\n"
    elif trade_type == "SCALP" and tt_label:
        mode_line = f"{tt_label}  ·  ⏱️ صفقة سريعة\n"
    else:
        mode_line = ""

    msg = (
        f"🚨 *إشارة جديدة │ Qaffel AI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        + (f"{mode_line}" if mode_line else "")
        + f"{emoji} *{rec_ar}*  ─  {mname}\n"
        f"📊 ثقة: *{conf:.0f}%*   ⏱ {tf}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 دخول:  `{entry}`\n"
        f"🛑 وقف:   `{sl}`\n"
        f"✅ هدف 1: `{tp1}`\n"
        f"✅ هدف 2: `{tp2}`\n"
    )
    if rr:
        msg += f"⚖️ R/R:   `{float(rr):.1f}x`\n"
    if tt_warning:
        msg += f"{tt_warning}\n"

    PHASE_AR = {"ACCUMULATION":"تراكم","DISTRIBUTION":"توزيع","MARKUP":"صعود","MARKDOWN":"هبوط"}
    ZONE_AR  = {"PREMIUM":"مرتفعة","DISCOUNT":"منخفضة","EQUILIBRIUM":"توازن"}
    phase = PHASE_AR.get(s.get("wyckoff_phase",""), "")
    zone  = ZONE_AR.get(s.get("premium_discount",""), "")
    if phase: msg += f"📐 Wyckoff: `{phase}`\n"
    if zone:  msg += f"💹 Zone:    `{zone}`\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    return msg


def fmt_outcome(o: dict) -> str:
    status  = o["status"]
    market  = o["market"]
    stype   = o["signal_type"]
    entry   = _fmt_price(o["entry"])
    price   = _fmt_price(o["current_price"])
    tp1     = _fmt_price(o["tp1"])
    tp2     = _fmt_price(o["tp2"])
    sl_p    = _fmt_price(o["sl"])
    pnl     = float(o.get("pnl_points", 0))
    pnl_pct = float(o.get("pnl_pct", 0))
    rec_ar  = "شراء" if stype == "BUY" else "بيع"
    mname   = MARKET_NAMES.get(market, market)

    # علامة الإشارة +/-
    sign_pts = "+" if pnl >= 0 else ""
    sign_pct = "+" if pnl_pct >= 0 else ""

    if status == "TP2_HIT":
        header  = "🏆 *الهدف 2 تحقق!*"
        pnl_line = (
            f"📈 الربح: *{sign_pts}{_fmt_pts(pnl)} نقطة*"
            + (f"  │  *{sign_pct}{pnl_pct:.2f}%*" if pnl_pct else "")
        )
        tip = "صفقة ممتازة — الهدف الكامل 🎯"
    elif status == "TP1_HIT":
        header  = "✅ *الهدف 1 تحقق!*"
        pnl_line = (
            f"📈 الربح: *{sign_pts}{_fmt_pts(pnl)} نقطة*"
            + (f"  │  *{sign_pct}{pnl_pct:.2f}%*" if pnl_pct else "")
        )
        tip = "فكّر بنقل الإيقاف لنقطة التعادل 💡"
    else:
        header  = "🔴 *وقف الخسارة ضُرب*"
        pnl_line = (
            f"📉 الخسارة: *{sign_pts}{_fmt_pts(pnl)} نقطة*"
            + (f"  │  *{sign_pct}{pnl_pct:.2f}%*" if pnl_pct else "")
        )
        tip = "الخسارة جزء من التداول — ثق بالاستراتيجية 💪"

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{mname}*  ─  {rec_ar}\n"
        f"💲 دخول: `{entry}`  ➜  إغلاق: `{price}`\n"
        f"🎯 TP1: `{tp1}`  │  TP2: `{tp2}`\n"
        f"🛑 SL:  `{sl_p}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{pnl_line}\n"
        f"_{tip}_\n\n"
        f"⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    )


# ─── /start ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if args:
        token = args[0].strip()
        async with aiohttp.ClientSession() as s:
            try:
                async with s.post(
                    f"{API_URL}/api/v1/auth/bot-verify",
                    json={
                        "token":            token,
                        "telegram_id":      str(user.id),
                        "telegram_username":user.username or "",
                        "telegram_name":    user.full_name or user.first_name or "",
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as r:
                    res = await r.json()
                    ok  = r.status == 200
            except Exception as e:
                logger.error(f"bot-verify error: {e}")
                res, ok = {}, False

        if ok:
            plan_ar = {"trial":"تجريبي","weekly":"أسبوعي","monthly":"شهري"}.get(
                res.get("plan",""), res.get("plan",""))
            left_an = res.get("trial_analyses_left", "∞")
            left_ch = res.get("trial_chat_left", "∞")
            await update.message.reply_text(
                f"✅ *تم ربط حسابك بنجاح!*\n\n"
                f"أهلاً *{res.get('user_name','')}* 👋\n"
                f"خطتك: *{plan_ar}*   │   تحليلات متبقية: *{left_an}*\n\n"
                f"🚨 ستصلك إشارات التداول مباشرة هنا!\n"
                f"فعّل *👁 المراقبة* لتلقي تنبيهات تلقائية.",
                parse_mode="Markdown",
                reply_markup=kb_main(),
            )
        else:
            await update.message.reply_text(
                f"❌ *فشل ربط الحساب*\n\n"
                f"{res.get('detail','الرابط غير صالح أو استُخدم مسبقاً.')}\n\n"
                f"للحصول على رابط جديد: افتح المنصة ← إعدادات ← ربط تيليجرام",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)
                ]]),
            )
        return

    await update.message.reply_text(
        "🤖 *Qaffel AI*\n\n"
        "منصة تداول ذكية بتقنية ICT/SMC والذكاء الاصطناعي\n\n"
        "🔗 *لربط حسابك:*\n"
        "افتح المنصة ← اضغط «ربط تيليجرام» ← افتح الرابط\n\n"
        "بعد الربط ستصلك الإشارات والتنبيهات تلقائياً 🚀",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Qaffel AI — القائمة الرئيسية*",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )


# ─── Button Handler ───────────────────────────────────────────────────────────
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    await q.answer()
    d   = q.data
    uid = q.from_user.id
    tgid= str(uid)

    # ── Ignore separator buttons
    if d == "noop":
        return

    # ── Back to main menu
    if d in ("m_back", "m_main"):
        await q.edit_message_text(
            "🤖 *Qaffel AI — القائمة الرئيسية*",
            parse_mode="Markdown", reply_markup=kb_main(),
        )
        return

    # ─────────────────────── ANALYZE ──────────────────────────────────────────
    if d == "m_analyze":
        await q.edit_message_text(
            "📊 *تحليل فوري*\nاختر الفئة:",
            parse_mode="Markdown", reply_markup=kb_categories("an"),
        )
        return

    if d.startswith("cat_an_"):
        cat = d[7:]
        info = CATEGORIES.get(cat, {})
        await q.edit_message_text(
            f"📊 *{info.get('label',cat)}* — اختر الزوج:",
            parse_mode="Markdown", reply_markup=kb_pairs(cat, "sym"),
        )
        return

    if d.startswith("sym_"):
        symbol = d[4:]
        if not is_market_open(symbol):
            exchange = GULF_MARKETS.get(symbol.upper())
            if exchange:
                reopen_line = f"السوق مغلق حالياً خارج ساعات التداول اليومية.\n{gulf_reopen_text(exchange)}."
            else:
                reopen_line = "مغلق خلال عطلة نهاية الأسبوع.\nيفتح مجدداً يوم الاثنين."
            await q.edit_message_text(
                f"🔴 *السوق مغلق*\n\n"
                f"{MARKET_NAMES.get(symbol,symbol)} {reopen_line}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data="m_analyze")]
                ]),
            )
            return
        await q.edit_message_text(
            f"⏱ *{MARKET_NAMES.get(symbol,symbol)}* — اختر الإطار الزمني:",
            parse_mode="Markdown", reply_markup=kb_timeframe(symbol),
        )
        return

    if d.startswith("an_"):
        parts  = d.split("_", 2)
        symbol = parts[1]
        tf     = parts[2]

        # Check subscription
        status = await _get("/api/v1/bot/user-status", {"telegram_id": tgid})
        if not status.get("linked"):
            await q.edit_message_text(
                "🔗 *ربط الحساب مطلوب*\n\n"
                "1️⃣ افتح المنصة وسجّل دخول\n"
                "2️⃣ اضغط «ربط تيليجرام»\n"
                "3️⃣ افتح الرابط",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="m_back")],
                ]),
            )
            return
        if not status.get("allowed"):
            await q.edit_message_text(
                f"⛔ *{status.get('reason','الاشتراك منتهي')}*\n\nجدد اشتراكك للمتابعة.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 تجديد الاشتراك", url=f"{FRONTEND_URL}/pricing")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="m_back")],
                ]),
            )
            return

        await q.edit_message_text(f"⏳ جاري تحليل {MARKET_NAMES.get(symbol,symbol)}…")

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{API_URL}/api/v1/bot/analyze",
                    params={"symbol": symbol, "timeframe": tf, "telegram_id": tgid},
                    headers=BOT_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=40),
                ) as r:
                    res  = await r.json()
                    data = res.get("data", {}) if r.status == 200 else {"_error": res.get("detail","")}
        except Exception as e:
            data = {"_error": str(e)}

        if data.get("_error"):
            await q.edit_message_text(
                f"⚠️ {data['_error']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="m_back")]]),
            )
            return

        msg = fmt_analysis(data, symbol, tf)
        await q.edit_message_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث",    callback_data=f"an_{symbol}_{tf}"),
                 InlineKeyboardButton("📊 سوق آخر", callback_data="m_analyze")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="m_back")],
            ]),
        )
        return

    # ─────────────────────── SIGNALS ──────────────────────────────────────────
    if d == "m_signals":
        await q.edit_message_text("⏳ جاري جلب الإشارات…")
        res  = await _get("/api/v1/signals/latest", {"limit": 8})
        sigs = res.get("data", [])

        STATUS_ICONS = {
            "ACTIVE":  "🔵", "TP1_HIT": "✅", "TP2_HIT": "🏆",
            "SL_HIT":  "❌", "PENDING": "⏳", "EXPIRED":  "⚫",
        }
        STATUS_AR = {
            "ACTIVE":"نشطة", "TP1_HIT":"هدف 1 ✅", "TP2_HIT":"هدف 2 🏆",
            "SL_HIT":"وقف ❌", "PENDING":"معلقة", "EXPIRED":"منتهية",
        }

        if not sigs:
            msg = (
                "📡 *آخر الإشارات*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "_لا توجد إشارات حتى الآن._\n\n"
                "حلّل سوقاً من قسم ⚡ تحليل فوري."
            )
        else:
            active_count = sum(1 for s in sigs if s.get("status") == "ACTIVE")
            msg = (
                f"📡 *آخر الإشارات*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔵 نشطة: *{active_count}*  │  إجمالي: *{len(sigs)}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            for s in sigs:
                stype  = s.get("signal_type", "BUY")
                status = s.get("status", "ACTIVE")
                conf   = get_confidence(s)
                mname  = MARKET_NAMES.get(s.get("market",""), s.get("market",""))
                entry  = _fmt_price(s.get("entry_price"))
                tp1    = _fmt_price(s.get("take_profit_1"))
                sl_p   = _fmt_price(s.get("stop_loss"))
                rr     = s.get("risk_reward_ratio")

                dir_emoji   = "▲" if stype == "BUY" else "▼"
                dir_ar      = "شراء" if stype == "BUY" else "بيع"
                status_icon = STATUS_ICONS.get(status, "○")
                status_ar   = STATUS_AR.get(status, status)
                conf_bar    = "█" * int(conf / 20) + "░" * (5 - int(conf / 20))

                msg += (
                    f"{dir_emoji} *{mname}*  `{dir_ar}`  {status_icon} _{status_ar}_\n"
                    f"  🎯 `{entry}`  🛑 `{sl_p}`  ✅ `{tp1}`"
                )
                if rr:
                    msg += f"  ⚖️ `{float(rr):.1f}x`"
                msg += f"\n  [{conf_bar}] `{conf:.0f}%`\n"
                msg += "─────────────────────\n"

        await q.edit_message_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث",        callback_data="m_signals"),
                 InlineKeyboardButton("⚡ تحليل فوري",   callback_data="m_analyze")],
                [InlineKeyboardButton("🌐 الداشبورد",    url=FRONTEND_URL),
                 InlineKeyboardButton("🔙 رجوع",         callback_data="m_back")],
            ]),
        )
        return

    # ─────────────────────── WATCHLIST ────────────────────────────────────────
    if d == "m_watchlist":
        await _load_wl_from_db(uid, tgid)
        wl    = _wl_symbols.get(uid, set())
        tf    = _wl_tf.get(uid, "1h")
        conf  = _wl_conf.get(uid, 65)
        notif = _wl_notif.get(uid, True)
        count = len(wl)
        total = sum(len(v["symbols"]) for v in CATEGORIES.values())

        # شريط بصري لعدد الأزواج المراقبة
        filled = min(count, 10)
        bar = "🟦" * filled + "⬜" * (10 - filled)

        notif_line = "🔔 الإشعارات مفعّلة" if notif else "🔕 الإشعارات موقفة"

        # قائمة الأزواج النشطة مختصرة
        if wl:
            wl_preview = "  ".join(f"`{s}`" for s in sorted(wl)[:8])
            if count > 8:
                wl_preview += f"  …+{count-8}"
        else:
            wl_preview = "_لم يتم اختيار أي زوج بعد_"

        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{bar}  *{count}/{total}* زوج\n\n"
            f"⏱ الإطار: *{TF_LABELS.get(tf,tf)}*   🎯 الحد: *{conf}%*\n"
            f"{notif_line}\n\n"
            f"الأزواج المختارة:\n{wl_preview}\n\n"
            f"💡 لإدارة الأزواج والإعدادات بشكل أفضل افتح الداشبورد:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 إدارة المراقبة من الداشبورد", url=f"{FRONTEND_URL}/dashboard")],
                [InlineKeyboardButton("🔔 تبديل الإشعارات", callback_data="wl_notif"),
                 InlineKeyboardButton("🔙 رجوع",            callback_data="m_back")],
            ]),
        )
        return

    if d == "wl_notif":
        await _load_wl_from_db(uid, tgid)
        _wl_notif[uid] = not _wl_notif.get(uid, True)
        await _save_wl_to_db(uid, tgid)
        st = "مفعّل 🔔" if _wl_notif[uid] else "موقف 🔕"
        await q.answer(f"الإشعارات: {st}")
        # إعادة رسم شاشة المراقبة
        wl    = _wl_symbols.get(uid, set())
        tf    = _wl_tf.get(uid, "1h")
        conf  = _wl_conf.get(uid, 65)
        notif = _wl_notif[uid]
        count = len(wl)
        total = sum(len(v["symbols"]) for v in CATEGORIES.values())
        filled = min(count, 10)
        bar = "🟦" * filled + "⬜" * (10 - filled)
        wl_preview = "  ".join(f"`{s}`" for s in sorted(wl)[:8]) if wl else "_لم يتم اختيار أي زوج_"
        if count > 8: wl_preview += f"  …+{count-8}"
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{bar}  *{count}/{total}* زوج\n\n"
            f"⏱ الإطار: *{TF_LABELS.get(tf,tf)}*   🎯 الحد: *{conf}%*\n"
            f"{'🔔 الإشعارات مفعّلة' if notif else '🔕 الإشعارات موقفة'}\n\n"
            f"الأزواج المختارة:\n{wl_preview}\n\n"
            f"💡 لإدارة الأزواج والإعدادات بشكل أفضل افتح الداشبورد:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 إدارة المراقبة من الداشبورد", url=f"{FRONTEND_URL}/dashboard")],
                [InlineKeyboardButton("🔔 تبديل الإشعارات", callback_data="wl_notif"),
                 InlineKeyboardButton("🔙 رجوع",            callback_data="m_back")],
            ]),
        )
        return

    # handlers قديمة للـ watchlist — احتياطي للتوافق مع أي رسائل قديمة
    if d.startswith("wl_t_") or d in ("wl_all","wl_none","wl_tf","wl_conf","wl_save") \
            or d.startswith("wltf_") or d.startswith("wlconf_"):
        await q.answer("⚙️ أدر المراقبة من الداشبورد")
        return

    # ─────────────────────── STATS ────────────────────────────────────────────
    if d == "m_stats":
        await q.edit_message_text("⏳ جاري جلب إحصائياتك…")
        st = await _get("/api/v1/bot/user-stats", {"telegram_id": tgid})
        if not st.get("linked"):
            await q.edit_message_text(
                "🔗 *ربط الحساب مطلوب لعرض الإحصائيات.*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)],
                    [InlineKeyboardButton("🔙 رجوع",       callback_data="m_back")],
                ]),
            )
            return

        total   = st.get("total_signals", 0)
        wins    = st.get("wins", 0)
        loss    = st.get("losses", 0)
        wr      = st.get("win_rate", 0)
        pts     = st.get("total_points", 0)
        active  = st.get("active_signals", 0)
        best    = st.get("best_trade", 0)
        worst   = st.get("worst_trade", 0)
        recent  = st.get("recent_trades", [])
        plan    = st.get("plan_label", "")
        ends    = st.get("ends_at", "")
        name    = st.get("full_name", "") or "مستخدم"
        ref_pts = st.get("referral_points", 0)

        # ── شريط Win Rate مرئي (10 خانات) ──
        filled_wr  = round(wr / 10)
        wr_bar     = "🟢" * filled_wr + "⚫" * (10 - filled_wr)

        # ── شريط الأداء العام ──
        pts_sign   = "+" if pts >= 0 else ""
        pts_emoji  = "📈" if pts >= 0 else "📉"

        # ── بطاقة الخطة ──
        plan_icons = {"trial": "🔵", "weekly": "🟡", "monthly": "🟣"}
        plan_icon  = plan_icons.get(st.get("plan",""), "⚪")
        plan_line  = f"{plan_icon} *{plan}*"
        if ends:
            plan_line += f"  ·  ينتهي `{ends}`"

        # ── آخر الصفقات بتنسيق أجمل ──
        recent_lines = ""
        if recent:
            recent_lines = "\n📋 *آخر الصفقات:*\n"
            for t in recent[:5]:
                pts_r  = t.get("points", 0)
                sign_r = "+" if pts_r >= 0 else ""
                icon_r = t.get("icon", "○")
                mkt    = t.get("market", "")
                typ    = "▲" if t.get("type") == "BUY" else "▼"
                date   = t.get("closed_at", "")
                pts_fmt = f"`{sign_r}{pts_r:.1f}`"
                recent_lines += f"  {icon_r} {typ} *{mkt}*  {pts_fmt} نق  _{date}_\n"

        text = (
            f"📊 *لوحة إحصائياتك*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *{name}*\n"
            f"{plan_line}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *الصفقات المغلقة:* {total}\n"
            f"  ✅ رابحة: *{wins}*   ❌ خاسرة: *{loss}*   ⏳ نشطة: *{active}*\n\n"
            f"🏆 *نسبة الربح:* *{wr:.1f}%*\n"
            f"  {wr_bar}\n\n"
            f"{pts_emoji} *إجمالي النقاط:* `{pts_sign}{pts:.1f}`\n"
        )
        if best:
            text += f"  🥇 أفضل: `+{best:.1f}` نقطة\n"
        if worst:
            text += f"  💔 أسوأ:  `{worst:.1f}` نقطة\n"
        if ref_pts:
            text += f"  🎁 نقاط إحالة: `{ref_pts}`\n"
        text += recent_lines
        text += f"━━━━━━━━━━━━━━━━━━━━━━"

        await q.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث",        callback_data="m_stats"),
                 InlineKeyboardButton("🌐 الداشبورد",    url=FRONTEND_URL)],
                [InlineKeyboardButton("🔙 رجوع",         callback_data="m_back")],
            ]),
        )
        return

    # ─────────────────────── REFERRAL ─────────────────────────────────────────
    if d == "m_referral":
        st = await _get("/api/v1/bot/user-stats", {"telegram_id": tgid})
        if not st.get("linked"):
            await q.edit_message_text(
                "🔗 *ربط الحساب مطلوب للوصول لبرنامج الإحالة.*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)],
                    [InlineKeyboardButton("🔙 رجوع",       callback_data="m_back")],
                ]),
            )
            return

        code     = st.get("affiliate_code", "")
        count    = st.get("referral_count", 0)
        ref_pts  = st.get("referral_points", 0)
        link     = f"{FRONTEND_URL}/register?ref={code}" if code else f"{FRONTEND_URL}/register"

        # حساب التحليلات المجانية المتاحة (20 نقطة = تحليل)
        free_analyses = ref_pts // 20
        pts_to_next   = 20 - (ref_pts % 20) if ref_pts % 20 != 0 else 0

        # شريط نقاط الإحالة (كل 20 نقطة = مربع)
        bar_filled = min(ref_pts % 20, 20)
        pts_bar    = "🟣" * (bar_filled // 2) + "⬜" * (10 - bar_filled // 2)

        # مستوى الإحالة
        if count >= 25:
            tier_line = "🥇 *مستوى ذهبي* — عمولة 15%"
        elif count >= 10:
            tier_line = "🥈 *مستوى فضي* — عمولة 5% → 15 إحالة للذهب"
        else:
            tier_line = "🥉 *مستوى برونزي* — عمولة 5%"

        text = (
            f"🎁 *نقاط الإحالة*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *نقاطك:* `{ref_pts}`   👥 *مدعوّون:* `{count}`\n"
            f"{pts_bar}\n"
        )
        if free_analyses > 0:
            text += f"🎉 لديك *{free_analyses}* تحليل مجاني جاهز للاستبدال!\n"
        else:
            text += f"⚡ تحتاج *{pts_to_next}* نقطة للتحليل المجاني التالي\n"

        text += (
            f"\n{tier_line}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *كيف تكسب النقاط؟*\n"
            f"  • تسجيل صديق = *+10 نقطة*\n"
            f"  • اشتراك صديق = *+50 نقطة*\n"
            f"  • 20 نقطة = تحليل مجاني 🎯\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 *رابطك:*\n`{link}`"
        )

        await q.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 استبدل النقاط من الداشبورد", url=f"{FRONTEND_URL}/dashboard")],
                [InlineKeyboardButton("📊 تفاصيل البرنامج", url=f"{FRONTEND_URL}/referral"),
                 InlineKeyboardButton("🔙 رجوع",            callback_data="m_back")],
            ]),
        )
        return

    # ─────────────────────── SETTINGS ─────────────────────────────────────────
    if d == "m_settings":
        await _load_wl_from_db(uid, tgid)
        tf   = _wl_tf.get(uid, "1h")
        conf = _wl_conf.get(uid, 65)
        notif= _wl_notif.get(uid, True)
        await q.edit_message_text(
            f"⚙️ *الإعدادات*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔔 الإشعارات:          *{'مفعّل' if notif else 'موقف'}*\n"
            f"⏱ الإطار الزمني:      *{TF_LABELS.get(tf,tf)}*\n"
            f"🎯 الحد الأدنى للثقة: *{conf}%*\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 تبديل الإشعارات",    callback_data="cfg_notif")],
                [InlineKeyboardButton("⏱ تغيير الإطار الزمني", callback_data="cfg_tf")],
                [InlineKeyboardButton("🎯 تغيير الحد الأدنى",   callback_data="cfg_conf")],
                [InlineKeyboardButton("🔙 رجوع",                callback_data="m_back")],
            ]),
        )
        return

    if d == "cfg_notif":
        _wl_notif[uid] = not _wl_notif.get(uid, True)
        await _save_wl_to_db(uid, tgid)
        await q.answer(f"الإشعارات: {'مفعّل 🔔' if _wl_notif[uid] else 'موقف 🔕'}")
        await on_button(update, context)  # re-render settings
        return

    if d == "cfg_tf":
        await q.edit_message_text("⏱ *اختر الإطار الزمني الافتراضي:*",
                                   parse_mode="Markdown",
                                   reply_markup=kb_tf_select(back="m_settings"))
        return

    if d == "cfg_conf":
        await q.edit_message_text(
            "🎯 *اختر الحد الأدنى للثقة:*\n(أعلى = إشارات أقل لكن أقوى)",
            parse_mode="Markdown", reply_markup=kb_conf_select(),
        )
        return

    # ─────────────────────── HELP ─────────────────────────────────────────────
    if d == "m_help":
        await q.edit_message_text(
            "📚 *المساعدة*\n\n"
            "📊 *تحليل فوري*\nاختر الفئة ثم الزوج والإطار الزمني.\n\n"
            "👁 *المراقبة*\nاختر الأزواج التي تريد مراقبتها.\n"
            "البوت يحللها كل 15 دقيقة تلقائياً.\n\n"
            "📡 *الإشارات*\nآخر الإشارات المنشورة من الأدمن.\n\n"
            "📈 *إحصائياتي*\nعرض نسبة ربحك ومجموع نقاطك.\n\n"
            "🎁 *الإحالة*\nرابطك الخاص + تفاصيل العمولة.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)],
                [InlineKeyboardButton("🔙 رجوع",       callback_data="m_back")],
            ]),
        )
        return


# ─── Background: Broadcast new admin signals ──────────────────────────────────
async def broadcast_new_signals(app: Application):
    """يبث إشارات الأدمن الجديدة لجميع المشتركين النشطين — كل 60 ثانية"""
    logger.info("📡 بدء مهمة بث الإشارات الجديدة…")
    await asyncio.sleep(45)

    while True:
        try:
            sigs_data = await _get("/api/v1/bot/new-signals")
            sigs      = sigs_data.get("signals", [])

            if sigs:
                # جلب قوائم المراقبة — كل مستخدم يستلم فقط إشارات أزواجه
                wl_data = await _get("/api/v1/bot/all-watchlists")
                wl_users = wl_data.get("users", [])

                # بناء map: telegram_id → set of symbols
                user_wl: dict[str, set] = {}
                for u in wl_users:
                    tid_str = str(u["telegram_id"])
                    user_wl[tid_str] = set(s.upper() for s in u.get("watchlist", []))

                # المستخدمون بدون watchlist يستلمون كل الإشارات (لم يضبطوا تفضيلاتهم بعد)
                subs_data = await _get("/api/v1/bot/active-subscribers")
                all_subs  = [str(s["telegram_id"]) for s in subs_data.get("subscribers", [])]

                logger.info(f"📡 {len(sigs)} إشارة جديدة → {len(all_subs)} مشترك ({len(user_wl)} لديهم watchlist)")

                now_bc = datetime.now(timezone.utc)
                for sig in sigs:
                    market   = sig.get("market", "").upper()
                    sig_type = sig.get("signal_type", "BUY").upper()
                    sig_tf   = sig.get("timeframe", "")

                    # قفل الاتجاه للإشارات المبثوثة — مفتاح مشترك بين كل المستخدمين،
                    # بس لكل (رمز + فريم) ككيان مستقل (Phase 5, 2026-08-14) — إشارة
                    # 4h ما لازم تكتم إشارة 1h معاكسة لنفس الرمز والعكس، بما إنه
                    # كل فريم صار قرار مستقل بالكامل بمحرك التحليل.
                    bc_key  = ("broadcast", market, sig_tf)
                    bc_last = last_alert.get(bc_key)
                    if bc_last:
                        elapsed_min = (now_bc - bc_last["time"]).total_seconds() / 60
                        if bc_last["direction"] == sig_type and elapsed_min < ALERT_COOLDOWN:
                            logger.debug(f"🔕 broadcast skip [{market}] same dir cooldown")
                            await _post(f"/api/v1/bot/mark-broadcast/{sig['id']}")
                            continue
                        if bc_last["direction"] != sig_type and elapsed_min < DIRECTION_LOCK_MIN:
                            logger.info(f"🔒 broadcast direction lock [{market}] {bc_last['direction']}→{sig_type} ({elapsed_min:.0f}m)")
                            await _post(f"/api/v1/bot/mark-broadcast/{sig['id']}")
                            continue
                    last_alert[bc_key] = {"time": now_bc, "direction": sig_type}

                    msg = fmt_new_signal(sig)
                    kb  = InlineKeyboardMarkup([[
                        InlineKeyboardButton("📊 تحليل هذا الزوج", callback_data=f"sym_{sig['market']}"),
                        InlineKeyboardButton("📡 كل الإشارات",     callback_data="m_signals"),
                    ]])
                    sent = 0
                    for tid in all_subs:
                        # مستخدم بدون watchlist → يستلم كل شيء
                        # مستخدم بـ watchlist → يستلم فقط أزواجه
                        if tid in user_wl and market not in user_wl[tid]:
                            continue
                        try:
                            await app.bot.send_message(
                                chat_id=int(tid), text=msg,
                                parse_mode="Markdown", reply_markup=kb,
                            )
                            sent += 1
                        except Exception as _e:
                            logger.warning(f"فشل إرسال إلى {tid}: {_e}")
                        await asyncio.sleep(0.05)  # rate limit

                    await _post(f"/api/v1/bot/mark-broadcast/{sig['id']}")
                    logger.info(f"✅ إشارة #{sig['id']} [{market}] بُثّت لـ {sent} مشترك")

        except Exception as e:
            logger.error(f"broadcast_new_signals: {e}", exc_info=True)

        await asyncio.sleep(BROADCAST_INTERVAL)


# ─── Background: Monitor watchlists ───────────────────────────────────────────
async def monitor_watchlists(app: Application):
    logger.info("🔍 بدء مراقبة قوائم المشتركين…")
    await asyncio.sleep(60)

    _market_cycle = 0
    # كل 96 دورة × 15 دقيقة = 24 ساعة → تجديد التجارب اليومي
    _DAILY_CYCLES = 96
    while True:
        try:
            _market_cycle += 1

            # ── 0. تجديد الفترة التجريبية (مرة يومياً) ────────────────────
            if _market_cycle % _DAILY_CYCLES == 1:
                try:
                    result = await _post("/api/v1/bot/renew-trials")
                    if result.get("renewed_count", 0) > 0:
                        logger.info(f"🔄 تجديد تلقائي: {result['renewed_count']} مستخدم تجريبي")
                except Exception as _re:
                    logger.warning(f"renew-trials: {_re}")

            # ── 1. نتائج الإشارات (TP/SL) ─────────────────────────────────
            outcomes = (await _get("/api/v1/bot/check-outcomes", timeout=45)).get("triggered", [])

            # نجمع الإشارات المُغلقة لنُعلّم كل واحدة مرة واحدة
            sent_result_ids: set = set()
            for o in outcomes:
                try:
                    await app.bot.send_message(
                        chat_id=int(o["telegram_id"]),
                        text=fmt_outcome(o),
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("📈 إحصائياتي", callback_data="m_stats"),
                            InlineKeyboardButton("📡 الإشارات",  callback_data="m_signals"),
                        ]]),
                    )
                    sent_result_ids.add(o.get("signal_id"))
                    await asyncio.sleep(0.05)
                except Exception as _e:
                    logger.warning(f"outcome send error: {_e}")

            # علامة أن النتيجة بُثّت (لا نُرسل مجدداً)
            for sid in sent_result_ids:
                if sid:
                    try:
                        await _post(f"/api/v1/bot/mark-result-broadcast/{sid}")
                    except Exception:
                        pass

            # ── 2. مراقبة الأزواج
            # المصدر الوحيد للـ Watchlist هو DB — لا merge مع الذاكرة المحلية
            db_users = (await _get("/api/v1/bot/all-watchlists")).get("users", [])
            merged: dict[int, tuple[set, str, int]] = {}
            for u in db_users:
                try:
                    tid = int(u["telegram_id"])
                    wl  = set(s.upper() for s in u.get("watchlist", [])) & _VALID_SYMBOLS
                    if wl:
                        merged[tid] = (wl, u.get("timeframe","1h"), u.get("min_confidence",65))
                except Exception:
                    pass

            logger.info(f"🔍 دورة مراقبة — {len(merged)} مستخدم (من DB)")
            now = datetime.now(timezone.utc)

            # Phase 5 (2026-08-14): كل رمز بمراقبة يُفحص على 3 فريمات مستقلة
            # تماماً (15m/1h/4h) بدل فريم واحد مخزّن بتفضيلات المستخدم — كل
            # فريم قرار كامل ومنفصل بمحرك التحليل (توسيع نطاق الفرص بدل
            # تخفيف معيار أي فريم فردي). تفضيل الفريم المخزّن بقاعدة البيانات
            # (`tf` بالسطر فوق) ما عاد يُستخدم لتحديد أي فريم نفحص — نفحص
            # الثلاثة دايماً لكل مستخدم/رمز.
            SCAN_TIMEFRAMES = "15m,1h,4h"

            # ── تحليل موحّد لكل رمز فريد مرة وحدة بالدورة، مش مرة لكل مستخدم ──
            # قبل هالتعديل: لو 5 مستخدمين عندهم XAUUSD بقائمتهم، كنا نطلب
            # تحليلها 5 مرات منفصلة (×3 فريمات = 15 طلب لنفس الرمز!). محرك
            # التحليل عنده كاش داخلي (TTL) بيلطّف الأثر جزئياً، بس مش ضمان —
            # لو دورة الفحص طالت أكتر من الـ TTL أو تزاحمت الطلبات، ممكن نضغط
            # على yfinance/Finnhub أكتر من اللازم بدون داعي حقيقي. الحل: نجمع
            # كل الرموز الفريدة أولاً، نحللها مرة وحدة بالتوازي المحدود، وبعدين
            # كل مستخدم بس بياخذ نتيجة رمزه من القاموس المشترك.
            all_symbols = set()
            for wl, _, _ in merged.values():
                all_symbols |= wl

            symbol_results: dict[str, dict] = {}
            for symbol in all_symbols:
                if not is_market_open(symbol):
                    continue  # السوق مغلق — صمت تام بدون رسائل
                try:
                    async with aiohttp.ClientSession() as s:
                        async with s.post(
                            f"{API_URL}/api/v1/bot/analyze-multi-tf",
                            params={"symbol": symbol, "timeframes": SCAN_TIMEFRAMES},
                            headers=BOT_HEADERS,
                            timeout=aiohttp.ClientTimeout(total=60),
                        ) as r:
                            res = await r.json() if r.status == 200 else {}
                            symbol_results[symbol] = res.get("data", {})
                except Exception as _e:
                    logger.warning(f"analyze-multi-tf {symbol}: {_e}")
                    symbol_results[symbol] = {}

            logger.info(f"🔍 حُلّل {len(symbol_results)} رمز فريد (بدل {sum(len(wl) for wl,_,_ in merged.values())} طلب لو كل مستخدم لحاله)")

            for uid_, (watchlist, _stored_tf_pref, min_conf) in merged.items():
                for symbol in list(watchlist):
                    tf_results = symbol_results.get(symbol) or {}
                    if not tf_results:
                        continue  # سوق مغلق أو فشل التحليل — تعامل معه فوق مرة وحدة

                    for tf, data in tf_results.items():
                        rec  = data.get("recommendation", "WATCH")
                        conf = get_confidence(data)
                        if rec not in ("BUY", "SELL") or conf < min_conf:
                            continue

                        # قفل الاتجاه لكل (مستخدم، رمز، فريم) ككيان مستقل —
                        # إشارة 4h ما لازم تكتم إشارة 1h معاكسة لنفس الرمز
                        key  = (uid_, symbol, tf)
                        last = last_alert.get(key)
                        if last:
                            elapsed_min = (now - last["time"]).total_seconds() / 60
                            last_dir    = last["direction"]
                            # نفس الاتجاه → كولداون عادي 60 دقيقة
                            if last_dir == rec and elapsed_min < ALERT_COOLDOWN:
                                continue
                            # اتجاه معاكس → قفل 4 ساعات (منع التضارب)
                            if last_dir != rec and elapsed_min < DIRECTION_LOCK_MIN:
                                logger.debug(f"🔒 direction lock [{symbol}/{tf}] {last_dir}→{rec} ({elapsed_min:.0f}m < {DIRECTION_LOCK_MIN}m)")
                                continue

                        last_alert[key] = {"time": now, "direction": rec}
                        emoji  = "🟢" if rec == "BUY" else "🔴"
                        rec_ar = "شراء" if rec == "BUY" else "بيع"
                        alert  = (
                            f"🚨 *تنبيه مراقبة!*\n\n"
                            f"{emoji} *{rec_ar}* — {MARKET_NAMES.get(symbol,symbol)} ({tf})\n"
                            f"📊 الثقة: *{conf:.1f}%*\n\n"
                            f"{fmt_analysis(data, symbol, tf)}"
                        )[:4000]

                        try:
                            await app.bot.send_message(
                                chat_id=uid_, text=alert, parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("🔄 تحديث", callback_data=f"an_{symbol}_{tf}"),
                                    InlineKeyboardButton("🏠 رئيسية", callback_data="m_back"),
                                ]]),
                            )
                            logger.info(f"📨 تنبيه → {uid_} | {symbol}/{tf} | {rec} | {conf:.1f}%")

                            # ── حفظ الإشارة في DB لتتبع PnL تلقائياً ─────────────
                            try:
                                levels = data.get("levels", {})
                                _ez    = data.get("entry_zones") or []
                                _tz    = data.get("take_profit_zones") or []
                                _entry = levels.get("entry") or (_ez[0] if _ez else None)
                                _sl    = levels.get("stop_loss") or data.get("stop_loss_zone")
                                _tp1   = levels.get("tp1") or (_tz[0] if _tz else None)
                                _tp2   = levels.get("tp2") or (_tz[1] if len(_tz) > 1 else _tp1)
                                _rr    = data.get("risk_reward_ratio") or levels.get("risk_reward") or 0
                                if _entry and _sl and _tp1:
                                    await _post("/api/v1/bot/save-alert-signal", params={
                                        "telegram_id": str(uid_),
                                        "symbol":      symbol,
                                        "timeframe":   tf,
                                        "signal_type": rec,
                                        "entry":       _entry,
                                        "sl":          _sl,
                                        "tp1":         _tp1,
                                        "tp2":         _tp2 or _tp1,
                                        "confidence":  conf,
                                        "rr":          _rr,
                                    })
                            except Exception as _save_e:
                                logger.warning(f"save-alert-signal: {_save_e}")

                        except Exception as _e:
                            logger.error(f"alert send {uid_}/{symbol}/{tf}: {_e}")

                        await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"monitor_watchlists: {e}", exc_info=True)

        await asyncio.sleep(MONITOR_INTERVAL)


# ─── Background: Expiry notifications ────────────────────────────────────────
async def notify_expiry(app: Application):
    logger.info("🔔 بدء مراقبة انتهاء الاشتراكات…")
    await asyncio.sleep(120)

    while True:
        try:
            users = (await _get("/api/v1/bot/expiring-soon")).get("users", [])
            for u in users:
                tid = u.get("telegram_id")
                if not tid:
                    continue
                key = f"expiry_{tid}_{u.get('days_left',0)}"
                if key in notified_expiry:
                    continue
                days  = u.get("days_left", 0)
                name  = u.get("full_name","") or u.get("email","")
                plan  = {"weekly":"الأسبوعية","monthly":"الشهرية","trial":"التجريبية"}.get(
                    str(u.get("plan","")), str(u.get("plan","")))
                msg = (
                    f"⏰ *انتهى اشتراكك!*\n\nمرحباً {name} 👋\nانتهت باقتك {plan}.\n\nجدد الآن للاستمرار 📊"
                    if days == 0 else
                    f"⚠️ *اشتراكك ينتهي قريباً!*\n\nمرحباً {name} 👋\n"
                    f"باقتك {plan} ستنتهي خلال *{days} {'يوم' if days==1 else 'أيام'}*.\n\nجدد الآن 🚀"
                )
                try:
                    await app.bot.send_message(
                        chat_id=int(tid), text=msg, parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("💳 تجديد الاشتراك", url=f"{FRONTEND_URL}/pricing")
                        ]]),
                    )
                    notified_expiry.add(key)
                    logger.info(f"🔔 إشعار انتهاء → {tid} | {days} أيام")
                except Exception as _e:
                    logger.error(f"expiry notify {tid}: {_e}")
        except Exception as e:
            logger.error(f"notify_expiry: {e}")
        await asyncio.sleep(EXPIRY_INTERVAL)


# ─── Background: Market Open/Close Notifications ──────────────────────────────
_CLOSE_MSG = """🔔 *إغلاق أسواق الفوركس والذهب*

السلام عليكم ورحمة الله وبركاته 🤲

أسواق الفوركس والمعادن والمؤشرات أغلقت الآن ليستريح المتداولون.

نتمنى أن تكون أسبوعاً موفقاً للجميع 🌟
*شكراً على ثقتكم — نراكم الأسبوع القادم إن شاء الله* 🙏

_أسواق الكريبتو لا تزال مفتوحة 24/7_ ₿"""

_OPEN_MSG = """🌅 *افتتاح أسواق الفوركس والذهب*

بِسْمِ اللهِ الرَّحْمَنِ الرَّحِيمِ 🤲

*اللهم بارك لنا في تجارتنا، وارزقنا من فضلك الواسع.*

أسواق الفوركس والمعادن والمؤشرات فتحت أبوابها للأسبوع الجديد 📈

_بالتوفيق للجميع — تداولوا بحكمة وانضباط_ 💪✨"""


async def market_session_notifier(app: Application):
    """يراقب افتتاح/إغلاق السوق الأسبوعي ويرسل رسائل مناسبة لجميع المشتركين"""
    logger.info("🕐 بدء مراقبة جلسات السوق…")
    await asyncio.sleep(30)

    _last_state: bool | None = None  # None = غير معروف بعد

    while True:
        try:
            # نستخدم EURUSD كمؤشر للسوق العام (ليس كريبتو)
            current_open = is_market_open("EURUSD")

            if _last_state is None:
                # أول دورة — فقط نسجّل الحالة بدون إرسال
                _last_state = current_open
            elif current_open != _last_state:
                # تغيّرت الحالة → أرسل الرسالة المناسبة
                msg = _OPEN_MSG if current_open else _CLOSE_MSG
                _last_state = current_open

                # جلب كل المشتركين النشطين
                subs_data = await _get("/api/v1/bot/active-subscribers")
                subs = subs_data.get("subscribers", [])
                sent = 0
                for s in subs:
                    tid = s.get("telegram_id")
                    if not tid:
                        continue
                    try:
                        await app.bot.send_message(
                            chat_id=int(tid),
                            text=msg,
                            parse_mode="Markdown",
                        )
                        sent += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        pass
                label = "افتتاح" if current_open else "إغلاق"
                logger.info(f"🕐 تنبيه {label} السوق → {sent} مشترك")

        except Exception as e:
            logger.error(f"market_session_notifier: {e}")

        await asyncio.sleep(300)  # فحص كل 5 دقائق


# ─── Background: Session Pre-Alert (30 min before London & NY) ───────────────
# جلسات رئيسية بتوقيت UTC
_SESSIONS = [
    {"name_ar": "🌍 جلسة لندن",    "name_en": "London Session",    "utc_hour": 7,  "utc_min": 30},
    {"name_ar": "🗽 جلسة نيويورك",  "name_en": "New York Session",  "utc_hour": 12, "utc_min": 30},
    {"name_ar": "🌏 جلسة آسيا",     "name_en": "Asian Session",     "utc_hour": 23, "utc_min": 0 },
]

_SESSION_NOTIFIED: set = set()   # (date_str, session_name) — منع التكرار


async def session_pre_alert(app: Application):
    """يرسل تنبيهاً قبل 30 دقيقة من بدء كل جلسة رئيسية"""
    logger.info("⏰ بدء مراقبة الجلسات اليومية…")
    await asyncio.sleep(60)

    while True:
        try:
            now = datetime.now(timezone.utc)
            # فقط أيام العمل (الاثنين–الجمعة)
            if now.weekday() < 5:
                for sess in _SESSIONS:
                    # وقت الجلسة
                    sess_dt = now.replace(hour=sess["utc_hour"], minute=sess["utc_min"], second=0, microsecond=0)
                    delta   = (sess_dt - now).total_seconds()
                    key     = (now.strftime("%Y-%m-%d"), sess["name_en"])

                    # إذا بقي بين 25 و35 دقيقة ولم نُرسل اليوم
                    if 25 * 60 <= delta <= 35 * 60 and key not in _SESSION_NOTIFIED:
                        _SESSION_NOTIFIED.add(key)
                        mins_left = int(delta // 60)

                        msg = (
                            f"⏰ *تنبيه جلسة | {sess['name_ar']}*\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"تفتح الجلسة خلال *{mins_left} دقيقة* 🔔\n\n"
                            f"📋 *جهّز نفسك:*\n"
                            f"• راجع الإعداد على HTF (4H)\n"
                            f"• حدد مناطق OB وFVG الفعّالة\n"
                            f"• لا تدخل صفقة قبل أول 15 دقيقة\n\n"
                            f"_استخدم /menu → تحليل سريع لأي سوق_"
                        )

                        subs_data = await _get("/api/v1/bot/active-subscribers")
                        subs = subs_data.get("subscribers", [])
                        sent = 0
                        for s in subs:
                            tid = s.get("telegram_id")
                            if not tid:
                                continue
                            try:
                                await app.bot.send_message(
                                    chat_id=int(tid), text=msg, parse_mode="Markdown"
                                )
                                sent += 1
                                await asyncio.sleep(0.05)
                            except Exception:
                                pass
                        logger.info(f"⏰ تنبيه {sess['name_ar']} → {sent} مشترك")

        except Exception as e:
            logger.error(f"session_pre_alert: {e}")

        await asyncio.sleep(60)  # فحص كل دقيقة


# ─── Background: Daily Morning Briefing ──────────────────────────────────────
# يُرسل كل يوم عمل الساعة 05:00 UTC (08:00 توقيت الرياض/مكة)
_BRIEFING_SENT_DATE: str = ""


async def daily_briefing(app: Application):
    """رسالة صباحية يومية: نظرة سريعة على XAUUSD + BTCUSD"""
    logger.info("📰 بدء مهمة التقرير الصباحي…")
    await asyncio.sleep(90)

    global _BRIEFING_SENT_DATE
    while True:
        try:
            now      = datetime.now(timezone.utc)
            today    = now.strftime("%Y-%m-%d")
            # 05:00 UTC = 08:00 مكة/الرياض — أيام العمل فقط
            if now.weekday() < 5 and now.hour == 5 and 0 <= now.minute < 5 and _BRIEFING_SENT_DATE != today:
                _BRIEFING_SENT_DATE = today

                # اجلب تحليل سريع من الـ API لـ XAUUSD و BTCUSD
                briefing_lines = []
                for sym in ["XAUUSD", "BTCUSD", "EURUSD"]:
                    try:
                        res = await _post(
                            f"/api/v1/bot/analyze?symbol={sym}&timeframe=4h"
                        )
                        d   = res.get("data", {})
                        if not d or d.get("error") or "recommendation" not in d:
                            briefing_lines.append(f"{MARKET_NAMES.get(sym, sym)}: ⚠️ تعذّر التحليل")
                            continue

                        rec = d.get("recommendation", "WAIT")
                        conf = get_confidence(d)
                        price = float(d.get("current_price") or 0)
                        rec_ar = {"BUY": "📈 شراء", "SELL": "📉 بيع", "WAIT": "⏳ انتظار"}.get(rec, rec)
                        mname  = MARKET_NAMES.get(sym, sym)
                        briefing_lines.append(
                            f"{mname}: {rec_ar} | ثقة `{conf:.0f}%` | `{_fmt_price(price)}`"
                        )
                    except Exception:
                        briefing_lines.append(f"{MARKET_NAMES.get(sym, sym)}: ⚠️ تعذّر التحليل")

                dow_ar = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة"][now.weekday()]
                msg = (
                    f"🌅 *صباح الخير — التقرير اليومي*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 {dow_ar} {now.strftime('%d/%m/%Y')}\n\n"
                    f"📊 *نظرة 4H على الأسواق الرئيسية:*\n"
                    + "\n".join(f"• {l}" for l in briefing_lines) +
                    f"\n\n"
                    f"💡 *نصيحة اليوم:*\n"
                    f"_لا تدخل صفقة دون تأكيد HTF + وجود OB أو FVG واضح_\n\n"
                    f"_استخدم /menu لتحليل سوق محدد 🎯_"
                )

                subs_data = await _get("/api/v1/bot/active-subscribers")
                subs = subs_data.get("subscribers", [])
                sent = 0
                for s in subs:
                    tid = s.get("telegram_id")
                    if not tid:
                        continue
                    try:
                        await app.bot.send_message(
                            chat_id=int(tid), text=msg, parse_mode="Markdown"
                        )
                        sent += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        pass
                logger.info(f"📰 تقرير صباحي → {sent} مشترك")

        except Exception as e:
            logger.error(f"daily_briefing: {e}")

        await asyncio.sleep(60)


# ─── Background: Economic News Warning ────────────────────────────────────────
# جدول أخبار ثابت — يُرسل تنبيه 60 دقيقة قبل كل حدث
# الأوقات UTC — يُحدَّث يدوياً أو يُستبدل بـ API مستقبلاً
_ECON_EVENTS = [
    # كل أول جمعة من الشهر 12:30 UTC — NFP
    {"type": "NFP",   "weekday": 4, "utc_hour": 12, "utc_min": 30,
     "msg_ar": "📊 *تحذير: NFP — وظائف غير الزراعية*\nالخبر بعد ساعة — من أقوى الأخبار تأثيراً على الذهب والدولار.\n⚠️ *لا تفتح صفقات جديدة الآن*\nانتظر 15 دقيقة بعد الإعلان قبل أي دخول."},
    # كل أول أربعاء من الشهر — FOMC Minutes أو Fed Rate
    {"type": "FOMC",  "weekday": 2, "utc_hour": 18, "utc_min": 0,
     "msg_ar": "🏦 *تحذير: قرار الفيدرالي الأمريكي (FOMC)*\nالقرار بعد ساعة — يؤثر بشكل كبير على جميع الأسواق.\n⚠️ *أغلق صفقاتك المفتوحة أو ضيّق الوقف*\nالتقلب سيكون عالياً جداً."},
    # منتصف كل شهر الثلاثاء 12:30 UTC — CPI
    {"type": "CPI",   "weekday": 1, "utc_hour": 12, "utc_min": 30,
     "msg_ar": "📈 *تحذير: مؤشر أسعار المستهلك (CPI)*\nالخبر بعد ساعة — يؤثر على الذهب والعملات تأثيراً كبيراً.\n⚠️ *احذر من الـ stop hunt قبل وبعد الخبر مباشرة*"},
]

_NEWS_NOTIFIED: set = set()  # (date_str, event_type)


async def economic_news_alert(app: Application):
    """يرسل تحذيراً قبل ساعة من الأخبار الاقتصادية المهمة"""
    logger.info("📰 بدء مراقبة الأخبار الاقتصادية…")
    await asyncio.sleep(120)

    while True:
        try:
            now   = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")

            for ev in _ECON_EVENTS:
                if now.weekday() != ev["weekday"]:
                    continue
                ev_dt  = now.replace(hour=ev["utc_hour"], minute=ev["utc_min"], second=0, microsecond=0)
                delta  = (ev_dt - now).total_seconds()
                key    = (today, ev["type"])

                # 55–65 دقيقة قبل الخبر ولم نُرسل اليوم
                if 55 * 60 <= delta <= 65 * 60 and key not in _NEWS_NOTIFIED:
                    _NEWS_NOTIFIED.add(key)

                    subs_data = await _get("/api/v1/bot/active-subscribers")
                    subs = subs_data.get("subscribers", [])
                    sent = 0
                    for s in subs:
                        tid = s.get("telegram_id")
                        if not tid:
                            continue
                        try:
                            await app.bot.send_message(
                                chat_id=int(tid),
                                text=ev["msg_ar"],
                                parse_mode="Markdown",
                            )
                            sent += 1
                            await asyncio.sleep(0.05)
                        except Exception:
                            pass
                    logger.info(f"📰 تنبيه {ev['type']} → {sent} مشترك")

        except Exception as e:
            logger.error(f"economic_news_alert: {e}")

        await asyncio.sleep(60)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير محدد!")
        return

    logger.info("🤖 Qaffel AI Bot v2 — بدء التشغيل…")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu",  cmd_menu))
    app.add_handler(CallbackQueryHandler(on_button))

    async def post_init(application: Application):
        asyncio.create_task(broadcast_new_signals(application))
        asyncio.create_task(monitor_watchlists(application))
        asyncio.create_task(notify_expiry(application))
        asyncio.create_task(market_session_notifier(application))
        asyncio.create_task(session_pre_alert(application))
        asyncio.create_task(daily_briefing(application))
        asyncio.create_task(economic_news_alert(application))

    app.post_init = post_init

    logger.success("✅ البوت يعمل — 7 مهام خلفية نشطة")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # إذا حدث Conflict error — احذر من نسخة قديمة من البوت
    # حاول مرة أخرى بعد انتظار
    while True:
        try:
            main()
        except Exception as e:
            if "Conflict" in str(e):
                logger.error(f"❌ Conflict error: {e}")
                logger.info("⏳ انتظار 30 ثانية قبل المحاولة مرة أخرى...")
                import time
                time.sleep(30)
            else:
                raise
