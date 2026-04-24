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
}

MARKET_NAMES: dict[str, str] = {
    "XAUUSD":"🥇 الذهب",    "XAGUSD":"🥈 الفضة",
    "BTCUSD":"₿ بيتكوين",  "ETHUSD":"Ξ إيثيريوم", "BNBUSD":"🔷 BNB",
    "EURUSD":"💶 EUR/USD",  "GBPUSD":"💷 GBP/USD",
    "USDJPY":"💴 USD/JPY",  "USDCHF":"🇨🇭 USD/CHF", "AUDUSD":"🦘 AUD/USD", "USDCAD":"🍁 USD/CAD",
    "USOIL": "🛢 نفط",     "NATGAS":"🔥 غاز",
    "NAS100":"📈 ناسداك",  "US30":  "📊 داو",       "SP500": "📉 S&P500",
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
ALERT_COOLDOWN      = 60     # min    — per-user per-symbol same-direction cooldown
DIRECTION_LOCK_MIN  = 240    # min    — قفل الاتجاه: بعد BUY لا يُرسل SELL لـ 4 ساعات

# ─── In-memory state ──────────────────────────────────────────────────────────
# uid → set of symbols
_wl_symbols:  dict[int, set]  = {}
_wl_tf:       dict[int, str]  = {}
_wl_conf:     dict[int, int]  = {}
_wl_notif:    dict[int, bool] = {}
# (uid, symbol) → {"time": datetime, "direction": "BUY"/"SELL"}
last_alert:   dict            = {}
notified_expiry: set          = set()


# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_market_open(symbol: str) -> bool:
    """
    فحص دقيق لحالة السوق:
    - كريبتو: مفتوح 24/7
    - فوركس/ذهب/نفط/مؤشرات: مغلق السبت كاملاً + الأحد حتى 22:00 UTC + الجمعة بعد 22:00 UTC
    """
    if symbol.upper() in CRYPTO_MARKETS:
        return True  # كريبتو 24/7
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
    conf       = data.get("ai_confidence_score", 0)
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
    conf       = s.get("ai_confidence", 0)
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
            await q.edit_message_text(
                f"🔴 *السوق مغلق*\n\n"
                f"{MARKET_NAMES.get(symbol,symbol)} مغلق خلال عطلة نهاية الأسبوع.\n"
                f"يفتح مجدداً يوم الاثنين.",
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
                conf   = s.get("ai_confidence") or s.get("ai_confidence_score") or 0
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

                    # قفل الاتجاه للإشارات المبثوثة — مفتاح مشترك بين كل المستخدمين
                    bc_key  = ("broadcast", market)
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
            db_users = (await _get("/api/v1/bot/all-watchlists")).get("users", [])
            merged: dict[int, tuple[set, str, int]] = {}
            for u in db_users:
                try:
                    tid = int(u["telegram_id"])
                    # فلترة إلى الرموز المعتمدة فقط — تتجاهل الرموز القديمة في DB
                    wl  = set(s.upper() for s in u.get("watchlist", [])) & _VALID_SYMBOLS
                    if wl:
                        merged[tid] = (wl, u.get("timeframe","1h"), u.get("min_confidence",65))
                except Exception:
                    pass
            for uid_, wl in list(_wl_symbols.items()):
                if uid_ not in merged and wl:
                    filtered = set(s.upper() for s in wl) & _VALID_SYMBOLS
                    if filtered:
                        merged[uid_] = (filtered, _wl_tf.get(uid_,"1h"), _wl_conf.get(uid_,65))

            logger.info(f"🔍 دورة مراقبة — {len(merged)} مستخدم")
            now = datetime.now(timezone.utc)

            for uid_, (watchlist, tf, min_conf) in merged.items():
                for symbol in list(watchlist):
                    if not is_market_open(symbol):
                        continue  # السوق مغلق — صمت تام بدون رسائل

                    try:
                        async with aiohttp.ClientSession() as s:
                            async with s.post(
                                f"{API_URL}/api/v1/bot/analyze",
                                params={"symbol":symbol,"timeframe":tf},
                                headers=BOT_HEADERS,
                                timeout=aiohttp.ClientTimeout(total=40),
                            ) as r:
                                res  = await r.json() if r.status == 200 else {}
                                data = res.get("data", {})
                    except Exception as _e:
                        logger.warning(f"analyze {symbol}: {_e}")
                        continue

                    rec  = data.get("recommendation","WATCH")
                    conf = data.get("ai_confidence_score", 0)
                    if rec not in ("BUY","SELL") or conf < min_conf:
                        continue

                    key  = (uid_, symbol)
                    last = last_alert.get(key)
                    if last:
                        elapsed_min = (now - last["time"]).total_seconds() / 60
                        last_dir    = last["direction"]
                        # نفس الاتجاه → كولداون عادي 60 دقيقة
                        if last_dir == rec and elapsed_min < ALERT_COOLDOWN:
                            continue
                        # اتجاه معاكس → قفل 4 ساعات (منع التضارب)
                        if last_dir != rec and elapsed_min < DIRECTION_LOCK_MIN:
                            logger.debug(f"🔒 direction lock [{symbol}] {last_dir}→{rec} ({elapsed_min:.0f}m < {DIRECTION_LOCK_MIN}m)")
                            continue

                    last_alert[key] = {"time": now, "direction": rec}
                    emoji  = "🟢" if rec == "BUY" else "🔴"
                    rec_ar = "شراء" if rec == "BUY" else "بيع"
                    alert  = (
                        f"🚨 *تنبيه مراقبة!*\n\n"
                        f"{emoji} *{rec_ar}* — {MARKET_NAMES.get(symbol,symbol)}\n"
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
                        logger.info(f"📨 تنبيه → {uid_} | {symbol} | {rec} | {conf:.1f}%")

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
                        logger.error(f"alert send {uid_}/{symbol}: {_e}")

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

    app.post_init = post_init

    logger.success("✅ البوت يعمل — 4 مهام خلفية نشطة")
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
