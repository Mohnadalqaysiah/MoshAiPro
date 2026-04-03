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

FOREX_MARKETS = {
    "XAUUSD","XAGUSD","EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD",
    "USOIL","NATGAS","NAS100","US30","SP500",
}

TF_LABELS = {"15m":"15 دقيقة", "1h":"1 ساعة", "4h":"4 ساعات", "1day":"يومي"}
TIMEFRAMES = ["15m", "1h", "4h", "1day"]

# ─── Intervals ────────────────────────────────────────────────────────────────
MONITOR_INTERVAL   = 900    # 15 min — watchlist monitoring
BROADCAST_INTERVAL = 60     # 1 min  — new admin signals
EXPIRY_INTERVAL    = 3600   # 1 hr   — subscription expiry
ALERT_COOLDOWN     = 60     # min    — per-user per-symbol cooldown

# ─── In-memory state ──────────────────────────────────────────────────────────
# uid → set of symbols
_wl_symbols:  dict[int, set]  = {}
_wl_tf:       dict[int, str]  = {}
_wl_conf:     dict[int, int]  = {}
_wl_notif:    dict[int, bool] = {}
last_alert:   dict            = {}
notified_expiry: set          = set()


# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_market_open(symbol: str) -> bool:
    """
    فحص دقيق لحالة السوق:
    - كريبتو: مفتوح 24/7
    - فوركس/ذهب/نفط/مؤشرات: مغلق السبت كاملاً + الأحد حتى 22:00 UTC + الجمعة بعد 22:00 UTC
    """
    if symbol.upper() not in FOREX_MARKETS:
        return True
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


async def _post(path: str, json: dict = None, params: dict = None, timeout: int = 15) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{API_URL}{path}", json=json, params=params,
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                return await r.json() if r.status == 200 else {}
    except Exception as e:
        logger.error(f"POST {path}: {e}")
    return {}


async def _load_wl_from_db(uid: int, telegram_id: str):
    """يحمّل إعدادات المراقبة من DB إلى الذاكرة"""
    d = await _get("/api/v1/bot/watchlist", {"telegram_id": telegram_id})
    if d.get("linked"):
        _wl_symbols[uid] = set(d.get("watchlist", []))
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
        [InlineKeyboardButton("📊 تحليل فوري",  callback_data="m_analyze"),
         InlineKeyboardButton("📡 الإشارات",    callback_data="m_signals")],
        [InlineKeyboardButton("👁 المراقبة",     callback_data="m_watchlist"),
         InlineKeyboardButton("📈 إحصائياتي",   callback_data="m_stats")],
        [InlineKeyboardButton("🎁 الإحالة",      callback_data="m_referral"),
         InlineKeyboardButton("⚙️ الإعدادات",    callback_data="m_settings")],
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

    rec    = data.get("recommendation", "WATCH")
    emoji  = {"BUY":"🟢","SELL":"🔴","WATCH":"⚪","WAIT":"⚪"}.get(rec, "⚪")
    rec_ar = {"BUY":"شراء","SELL":"بيع","WATCH":"مراقبة","WAIT":"انتظار"}.get(rec, rec)
    conf   = data.get("ai_confidence_score", 0)
    price  = data.get("current_price", 0)
    lvls   = data.get("levels", {})

    entry_min = lvls.get("entry_zone_min")
    entry_max = lvls.get("entry_zone_max")
    entry_v   = lvls.get("entry") or (data.get("entry_zones") or [None])[0]
    sl  = lvls.get("stop_loss") or data.get("stop_loss_zone")
    tp1 = lvls.get("tp1") or (data.get("take_profit_zones") or [None])[0]
    tp2 = lvls.get("tp2")
    if not tp2 and len(data.get("take_profit_zones") or []) > 1:
        tp2 = data["take_profit_zones"][1]
    rr  = lvls.get("risk_reward") or data.get("risk_reward_ratio")

    msg = (
        f"🤖 *Qaffel AI — تحليل*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{MARKET_NAMES.get(symbol,symbol)}*  │  `{timeframe}`  │  `{_fmt_price(price)}`\n\n"
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
    stype  = s.get("signal_type", "BUY")
    emoji  = "🟢" if stype == "BUY" else "🔴"
    rec_ar = "شراء" if stype == "BUY" else "بيع"
    mname  = MARKET_NAMES.get(s.get("market",""), s.get("market",""))
    conf   = s.get("ai_confidence", 0)
    tf     = TF_LABELS.get(s.get("timeframe",""), s.get("timeframe",""))
    entry  = _fmt_price(s.get("entry_price"))
    sl     = _fmt_price(s.get("stop_loss"))
    tp1    = _fmt_price(s.get("take_profit_1"))
    tp2    = _fmt_price(s.get("take_profit_2"))
    rr     = s.get("risk_reward_ratio")

    msg = (
        f"🚨 *إشارة جديدة │ Qaffel AI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} *{rec_ar}*  ─  {mname}\n"
        f"📊 ثقة: *{conf:.0f}%*   ⏱ {tf}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 دخول:  `{entry}`\n"
        f"🛑 وقف:   `{sl}`\n"
        f"✅ هدف 1: `{tp1}`\n"
        f"✅ هدف 2: `{tp2}`\n"
    )
    if rr:
        msg += f"⚖️ R/R:   `{float(rr):.1f}x`\n"

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
        res  = await _get("/api/v1/signals/latest", {"limit": 6})
        sigs = res.get("data", [])
        if not sigs:
            msg = "📡 لا توجد إشارات حتى الآن."
        else:
            msg = "📡 *آخر الإشارات*\n━━━━━━━━━━━━━━━━━━━━━━\n"
            STATUS_AR = {"ACTIVE":"نشطة","TP1_HIT":"هدف 1 ✅","TP2_HIT":"هدف 2 🏆","SL_HIT":"وقف خسارة ❌","PENDING":"معلقة","EXPIRED":"منتهية"}
            for s in sigs:
                e      = "🟢" if s.get("signal_type") == "BUY" else "🔴"
                status = STATUS_AR.get(s.get("status",""), s.get("status",""))
                conf   = s.get("ai_confidence", 0)
                mname  = MARKET_NAMES.get(s.get("market",""), s.get("market",""))
                entry  = _fmt_price(s.get("entry_price"))
                tp1    = _fmt_price(s.get("take_profit_1"))
                sl     = _fmt_price(s.get("stop_loss"))
                msg += (
                    f"{e} *{mname}*  ·  `{s.get('timeframe','')}` · {conf:.0f}%\n"
                    f"   دخول `{entry}` │ TP1 `{tp1}` │ SL `{sl}`\n"
                    f"   الحالة: *{status}*\n"
                    f"─────────────────────\n"
                )
        await q.edit_message_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث",    callback_data="m_signals"),
                 InlineKeyboardButton("🏠 الرئيسية", callback_data="m_back")],
            ]),
        )
        return

    # ─────────────────────── WATCHLIST ────────────────────────────────────────
    if d == "m_watchlist":
        await _load_wl_from_db(uid, tgid)
        wl   = _wl_symbols.get(uid, set())
        tf   = _wl_tf.get(uid, "1h")
        conf = _wl_conf.get(uid, 65)
        notif= _wl_notif.get(uid, True)
        count = len(wl)
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"الأزواج المراقبة: *{count}* من {sum(len(v['symbols']) for v in CATEGORIES.values())}\n"
            f"الإطار: *{TF_LABELS.get(tf,tf)}*  │  الحد الأدنى للثقة: *{conf}%*\n"
            f"الإشعارات: *{'مفعّل 🔔' if notif else 'موقف 🔕'}*\n\n"
            f"اضغط على الزوج لإضافته أو إزالته:",
            parse_mode="Markdown",
            reply_markup=kb_watchlist(uid),
        )
        return

    if d.startswith("wl_t_"):
        m = d[5:]
        if uid not in _wl_symbols:
            _wl_symbols[uid] = set()
        if m in _wl_symbols[uid]:
            _wl_symbols[uid].remove(m)
            await q.answer(f"○ أُزيل {MARKET_NAMES.get(m,m)}")
        else:
            _wl_symbols[uid].add(m)
            await q.answer(f"✅ أُضيف {MARKET_NAMES.get(m,m)}")
        wl = _wl_symbols[uid]; tf = _wl_tf.get(uid,"1h"); conf = _wl_conf.get(uid,65); notif = _wl_notif.get(uid,True)
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\nالأزواج: *{len(wl)}*  │  الإطار: *{TF_LABELS.get(tf,tf)}*  │  الحد: *{conf}%*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=kb_watchlist(uid),
        )
        return

    if d == "wl_all":
        _wl_symbols[uid] = set(m for cat in CATEGORIES.values() for m in cat["symbols"])
        await q.answer("✅ تم تحديد الكل")
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\nالأزواج: *{len(_wl_symbols[uid])}* — جميعها محددة\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=kb_watchlist(uid),
        )
        return

    if d == "wl_none":
        _wl_symbols[uid] = set()
        await q.answer("✖ تم إلغاء الكل")
        await q.edit_message_text(
            "👁 *قائمة المراقبة*\nلا توجد أزواج محددة.\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=kb_watchlist(uid),
        )
        return

    if d == "wl_notif":
        _wl_notif[uid] = not _wl_notif.get(uid, True)
        st = "مفعّل 🔔" if _wl_notif[uid] else "موقف 🔕"
        await q.answer(f"الإشعارات: {st}")
        wl = _wl_symbols.get(uid, set()); tf = _wl_tf.get(uid,"1h"); conf = _wl_conf.get(uid,65)
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\nالأزواج: *{len(wl)}*  │  الإطار: *{TF_LABELS.get(tf,tf)}*  │  الحد: *{conf}%*\nالإشعارات: *{st}*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=kb_watchlist(uid),
        )
        return

    if d == "wl_tf":
        await q.edit_message_text("⏱ *اختر الإطار الزمني للمراقبة:*",
                                   parse_mode="Markdown", reply_markup=kb_tf_select())
        return

    if d.startswith("wltf_"):
        tf = d[5:]
        _wl_tf[uid] = tf
        await q.answer(f"✅ الإطار: {TF_LABELS.get(tf,tf)}")
        wl = _wl_symbols.get(uid,set()); conf = _wl_conf.get(uid,65); notif = _wl_notif.get(uid,True)
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\nالأزواج: *{len(wl)}*  │  الإطار: *{TF_LABELS.get(tf,tf)}*  │  الحد: *{conf}%*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=kb_watchlist(uid),
        )
        return

    if d == "wl_conf":
        await q.edit_message_text(
            "🎯 *الحد الأدنى للثقة*\n\nنسبة أعلى = إشارات أقل لكن أقوى:",
            parse_mode="Markdown", reply_markup=kb_conf_select(),
        )
        return

    if d.startswith("wlconf_"):
        conf = int(d[7:])
        _wl_conf[uid] = conf
        await q.answer(f"✅ الحد: {conf}%")
        wl = _wl_symbols.get(uid,set()); tf = _wl_tf.get(uid,"1h"); notif = _wl_notif.get(uid,True)
        await q.edit_message_text(
            f"👁 *قائمة المراقبة*\nالأزواج: *{len(wl)}*  │  الإطار: *{TF_LABELS.get(tf,tf)}*  │  الحد: *{conf}%*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=kb_watchlist(uid),
        )
        return

    if d == "wl_save":
        await q.edit_message_text("⏳ جاري الحفظ…")
        await _save_wl_to_db(uid, tgid)
        wl = _wl_symbols.get(uid,set())
        await q.edit_message_text(
            f"✅ *تم الحفظ بنجاح!*\n\n"
            f"الأزواج المراقبة: *{len(wl)}*\n"
            f"الإطار: *{TF_LABELS.get(_wl_tf.get(uid,'1h'),'—')}*\n"
            f"الحد الأدنى للثقة: *{_wl_conf.get(uid,65)}%*\n"
            f"الإشعارات: *{'مفعّل 🔔' if _wl_notif.get(uid,True) else 'موقف 🔕'}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁 تعديل",     callback_data="m_watchlist"),
                 InlineKeyboardButton("🏠 الرئيسية", callback_data="m_back")],
            ]),
        )
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
        plan    = st.get("plan_label","")
        ends    = st.get("ends_at","")
        name    = st.get("full_name","")
        wr_bar  = "🟩" * int(wr/10) + "⬜" * (10 - int(wr/10))

        pts_sign = "+" if pts >= 0 else ""
        recent_lines = ""
        if recent:
            recent_lines = "\n*آخر الصفقات:*\n"
            for t in recent:
                pts_r = t.get("points", 0)
                sign_r = "+" if pts_r >= 0 else ""
                recent_lines += (
                    f"{t['icon']} {t['market']} {t['type']}  "
                    f"`{sign_r}{pts_r:.1f}` نقطة  {t['closed_at']}\n"
                )

        text = (
            f"📈 *إحصائياتك*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *{name}*\n"
            f"💳 خطة: *{plan}*" + (f"  │  تنتهي: {ends}" if ends else "") + "\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 مغلقة: *{total}*  │  ✅ رابحة: *{wins}*  │  ❌ خاسرة: *{loss}*\n"
            f"⏳ نشطة حالياً: *{active}*\n"
            f"🏆 نسبة الربح: *{wr:.1f}%*\n"
            f"{wr_bar}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ إجمالي النقاط: *{pts_sign}{pts:.2f}*\n"
            + (f"🥇 أفضل صفقة:  `+{best:.2f}` نقطة\n" if best else "")
            + (f"💔 أسوأ صفقة:  `{worst:.2f}` نقطة\n" if worst else "")
            + recent_lines
            + f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 فتح المنصة",  url=FRONTEND_URL),
                 InlineKeyboardButton("🔙 رجوع",        callback_data="m_back")],
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
        code  = st.get("affiliate_code","")
        count = st.get("referral_count", 0)
        link  = f"{FRONTEND_URL}/register?ref={code}" if code else f"{FRONTEND_URL}/register"
        await q.edit_message_text(
            f"🎁 *برنامج الإحالة*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"رابطك الخاص:\n"
            f"`{link}`\n\n"
            f"👥 إجمالي إحالاتك: *{count}*\n\n"
            f"كل مشترك تُحيله يمنحك عمولة شهرية مستمرة 💰\n"
            f"5% برونزي → 15% ذهبي بعد 25 إحالة",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 تفاصيل البرنامج", url=f"{FRONTEND_URL}/referral")],
                [InlineKeyboardButton("🔙 رجوع",            callback_data="m_back")],
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

                for sig in sigs:
                    market = sig.get("market", "").upper()
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
                    wl  = set(s.upper() for s in u.get("watchlist", []))
                    if wl:
                        merged[tid] = (wl, u.get("timeframe","1h"), u.get("min_confidence",65))
                except Exception:
                    pass
            for uid_, wl in list(_wl_symbols.items()):
                if uid_ not in merged and wl:
                    merged[uid_] = (set(s.upper() for s in wl), _wl_tf.get(uid_,"1h"), _wl_conf.get(uid_,65))

            logger.info(f"🔍 دورة مراقبة — {len(merged)} مستخدم")
            now = datetime.now(timezone.utc)

            for uid_, (watchlist, tf, min_conf) in merged.items():
                for symbol in list(watchlist):
                    if not is_market_open(symbol):
                        key = (uid_, f"{symbol}_closed_{now.date()}")
                        if key not in last_alert:
                            last_alert[key] = now
                            try:
                                await app.bot.send_message(
                                    chat_id=uid_,
                                    text=f"🔴 *{MARKET_NAMES.get(symbol,symbol)} مغلق*\nيفتح يوم الاثنين.",
                                    parse_mode="Markdown")
                            except Exception:
                                pass
                        continue

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
                    if last and (now - last).total_seconds() < ALERT_COOLDOWN * 60:
                        continue

                    last_alert[key] = now
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

    app.post_init = post_init

    logger.success("✅ البوت يعمل — 3 مهام خلفية نشطة")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
