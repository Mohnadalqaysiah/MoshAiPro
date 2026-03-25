"""
Qaffel AI v5 - Telegram Bot
بوت تيليجرام مع ربط الحسابات وإشعارات انتهاء الاشتراك
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)
from loguru import logger

# ─── Config ───────────────────────────────────────────────────────────────────
API_URL      = os.getenv("API_URL", "http://backend:8000")
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BOT_SECRET   = os.getenv("BOT_SECRET", "mosh-bot-secret-2026")

# Header ترسله لكل طلب للـ API
BOT_HEADERS  = {"X-Bot-Secret": BOT_SECRET}

# ─── قوائم الأزواج — تُحدَّث من API عند البدء ────────────────────────────────
MARKETS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]  # fallback
TIMEFRAMES = ["15m", "1h", "4h", "1day"]

# emoji لكل فئة
_CATEGORY_EMOJI = {
    "forex":     {"XAUUSD":"🥇","EURUSD":"💶","GBPUSD":"💷","USDJPY":"💴","USDCHF":"🇨🇭","AUDUSD":"🦘","default":"💱"},
    "crypto":    "₿",
    "commodity": "🛢️",
    "stock":     "📈",
}

MARKET_NAMES: dict[str, str] = {
    "XAUUSD": "🥇 الذهب",
    "BTCUSD": "₿ بيتكوين",
    "EURUSD": "💶 يورو/دولار",
    "GBPUSD": "💷 جنيه/دولار",
    "USDJPY": "💴 دولار/ين",
    "USDCHF": "🇨🇭 دولار/فرنك",
}

# الأسواق التي تُغلق في عطلة نهاية الأسبوع (فوركس وسلع)
FOREX_MARKETS: set[str] = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
                            "XAGUSD", "USOIL", "NATGAS", "NAS100", "SP500", "US30"}


async def load_markets_from_api():
    """يجلب الأزواج النشطة من /api/v1/markets/list ويحدّث MARKETS و MARKET_NAMES"""
    global MARKETS, MARKET_NAMES
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/api/v1/markets/list",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = (await resp.json()).get("data", [])
                    if data:
                        MARKETS = [m["symbol"] for m in data]
                        new_names = {}
                        for m in data:
                            sym  = m["symbol"]
                            cat  = m.get("category", "forex")
                            name = m.get("name_ar") or m.get("name", sym)
                            if cat == "crypto":
                                emoji = "₿" if sym == "BTCUSD" else "🔷"
                            elif cat == "stock":
                                emoji = "📈"
                            elif cat == "commodity":
                                emoji = "🛢️"
                            else:
                                emoji = MARKET_NAMES.get(sym, "💱").split()[0]
                            new_names[sym] = f"{emoji} {name}"
                        MARKET_NAMES = new_names
                        logger.info(f"✅ تحميل {len(MARKETS)} زوج من API")
                        return
    except Exception as e:
        logger.warning(f"load_markets_from_api: {e} — سيُستخدم الافتراضي")

ALERT_COOLDOWN_MINUTES = 60
MONITOR_INTERVAL = 900       # 15 دقيقة
EXPIRY_CHECK_INTERVAL = 3600  # كل ساعة

# ─── State ────────────────────────────────────────────────────────────────────
user_watchlist: dict      = {}
user_timeframe: dict      = {}
user_min_confidence: dict = {}
last_alert: dict          = {}
notified_expiry: set      = set()   # user telegram_ids that got expiry notice today


# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_market_open(symbol: str) -> bool:
    if symbol not in FOREX_MARKETS:
        return True
    return datetime.now(timezone.utc).weekday() < 5


def format_analysis(data: dict, symbol: str, timeframe: str) -> str:
    if not data or data.get("error"):
        return f"❌ تعذر تحليل {symbol}."

    rec    = data.get("recommendation", "WATCH")
    emoji  = {"BUY": "🟢", "SELL": "🔴", "WATCH": "⚪", "WAIT": "⚪"}.get(rec, "⚪")
    rec_ar = {"BUY": "شراء", "SELL": "بيع", "WATCH": "مراقبة", "WAIT": "انتظار"}.get(rec, rec)
    conf   = data.get("ai_confidence_score", 0)
    price  = data.get("current_price", 0)

    msg = (
        f"🤖 *Qaffel AI — تحليل*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 `{symbol}` | `{timeframe}` | السعر: `{price}`\n\n"
        f"{emoji} *التوصية: {rec_ar}*\n"
        f"📊 الثقة: `{conf:.1f}%`\n\n"
    )

    levels = data.get("levels", {})
    # support both ICT engine v5 (levels.*) and legacy Gemini fields
    entry_v = levels.get("entry") or (data.get("entry_zones") or [None])[0]
    entry_min = levels.get("entry_zone_min")
    entry_max = levels.get("entry_zone_max")
    sl    = levels.get("stop_loss") or data.get("stop_loss_zone")
    tp1   = levels.get("tp1") or (data.get("take_profit_zones") or [None])[0]
    tp2   = levels.get("tp2") or (data.get("take_profit_zones") or [None, None])[1] if len(data.get("take_profit_zones") or []) > 1 else levels.get("tp2")
    rr    = levels.get("risk_reward") or data.get("risk_reward_ratio") or data.get("risk_reward")

    if entry_min and entry_max:
        msg += f"🎯 *دخول:* `{entry_min} — {entry_max}`\n"
    elif entry_v:
        msg += f"🎯 *دخول:* `{entry_v}`\n"
    if sl:     msg += f"🛑 *وقف الخسارة:* `{sl}`\n"
    if tp1:    msg += f"✅ *هدف 1:* `{tp1}`\n"
    if tp2:    msg += f"✅ *هدف 2:* `{tp2}`\n"
    if rr:     msg += f"\n⚖️ *R/R:* `{float(rr):.2f}x`\n"

    ob      = data.get("order_blocks", {})
    wyckoff = data.get("wyckoff_analysis") or data.get("wyckoff", {})
    pd_z    = data.get("premium_discount", {})
    liq     = data.get("liquidity_analysis") or data.get("liquidity", {})

    def fmt_ob(o):
        """تحويل dict الـ OB إلى نص مقروء"""
        if isinstance(o, dict):
            low  = o.get("low",  "")
            high = o.get("high", "")
            mid  = o.get("mid",  "")
            strength = o.get("strength", "")
            if low and high:
                return f"{low} — {high}" + (f" (وسط: {round(float(mid),2)})" if mid else "") + (f" [{strength}]" if strength else "")
        return str(o)

    bull_obs = ob.get("bullish_obs") or []
    bear_obs = ob.get("bearish_obs") or []

    if bull_obs:
        msg += f"🟢 *OB دعم:* `{fmt_ob(bull_obs[0])}`\n"
    if bear_obs:
        msg += f"🔴 *OB مقاومة:* `{fmt_ob(bear_obs[0])}`\n"

    # ICT engine nests under bias.below_price / above_price; legacy uses nearest_ssl/nearest_bsl
    _liq_bias_raw = liq.get("bias", {}) if isinstance(liq, dict) else {}
    liq_bias = _liq_bias_raw if isinstance(_liq_bias_raw, dict) else {}
    ssl = liq.get("nearest_ssl") or liq_bias.get("below_price")
    bsl = liq.get("nearest_bsl") or liq_bias.get("above_price")
    if ssl:
        msg += f"🧲 *سيولة تحت:* `{ssl}`\n"
    if bsl:
        msg += f"🧲 *سيولة فوق:* `{bsl}`\n"

    phase = wyckoff.get("phase") if isinstance(wyckoff, dict) else None
    # ICT engine uses current_zone; legacy uses zone
    zone  = pd_z.get("current_zone") or pd_z.get("zone") if isinstance(pd_z, dict) else None
    if phase:
        phase_ar = {
            "ACCUMULATION": "تراكم", "DISTRIBUTION": "توزيع",
            "ACCUMULATION_START": "بداية تراكم", "DISTRIBUTION_START": "بداية توزيع",
            "MARKUP": "صعود", "MARKDOWN": "هبوط", "RE_ACCUMULATION": "إعادة تراكم",
        }.get(phase, phase)
        msg += f"📐 *Wyckoff:* `{phase_ar}`\n"
    if zone:
        zone_ar = {"PREMIUM": "منطقة مرتفعة", "DISCOUNT": "منطقة منخفضة", "EQUILIBRIUM": "توازن"}.get(zone, zone)
        msg += f"💹 *Zone:* `{zone_ar}`\n"

    msg += "\n━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    return msg


async def fetch_analysis(symbol: str, timeframe: str, telegram_id: str = "") -> dict:
    """جلب التحليل عبر bot endpoint المحمي بـ BOT_SECRET"""
    try:
        params = {"symbol": symbol, "timeframe": timeframe}
        if telegram_id:
            params["telegram_id"] = telegram_id
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/api/v1/bot/analyze",
                params=params,
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=40)
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return data.get("data", {})
                elif resp.status == 403:
                    return {"_error": data.get("detail", "غير مصرح")}
    except Exception as e:
        logger.error(f"fetch_analysis error: {e}")
    return {}


async def get_user_status(telegram_id: str) -> dict:
    """يجلب حالة المستخدم من API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/api/v1/bot/user-status",
                params={"telegram_id": str(telegram_id)},
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.error(f"get_user_status error: {e}")
    return {"linked": False}


async def fetch_latest_signals() -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/api/v1/signals/latest",
                params={"limit": 5},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("data", [])
    except Exception as e:
        logger.error(f"fetch_latest_signals error: {e}")
    return []


async def verify_telegram_link(token: str, telegram_id: str, telegram_username: str, telegram_name: str) -> dict:
    """ربط حساب تيليجرام بالمنصة"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/api/v1/auth/bot-verify",
                json={
                    "token": token,
                    "telegram_id": str(telegram_id),
                    "telegram_username": telegram_username,
                    "telegram_name": telegram_name,
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return {"success": True, **data}
                return {"success": False, "detail": data.get("detail", "خطأ غير معروف")}
    except Exception as e:
        logger.error(f"verify_telegram_link error: {e}")
        return {"success": False, "detail": "فشل الاتصال بالخادم"}


async def get_expiring_users() -> list:
    """جلب المستخدمين الذين اشتراكهم ينتهي قريباً"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/api/v1/bot/expiring-soon",
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("users", [])
    except Exception as e:
        logger.error(f"get_expiring_users error: {e}")
    return []


# ─── Keyboards ────────────────────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تحليل سوق",     callback_data="menu_analyze"),
         InlineKeyboardButton("📡 آخر الإشارات",  callback_data="menu_latest")],
        [InlineKeyboardButton("👁 قائمة المراقبة", callback_data="menu_watchlist"),
         InlineKeyboardButton("ℹ️ مساعدة",          callback_data="menu_help")],
    ])


def watchlist_keyboard(uid: int):
    wl = user_watchlist.get(uid, set())
    rows = []
    for i in range(0, len(MARKETS), 2):
        row = []
        for m in MARKETS[i:i+2]:
            tick = "✅ " if m in wl else ""
            row.append(InlineKeyboardButton(f"{tick}{MARKET_NAMES.get(m,m)}", callback_data=f"wl_toggle_{m}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⏱ الإطار الزمني",      callback_data="wl_timeframe"),
        InlineKeyboardButton("🎯 الحد الأدنى للثقة", callback_data="wl_confidence"),
    ])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def timeframe_keyboard():
    tf_labels = {"15m": "15 دقيقة", "1h": "ساعة", "4h": "4 ساعات", "1day": "يومي"}
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tf_labels[tf], callback_data=f"wl_tf_{tf}") for tf in TIMEFRAMES[:2]],
        [InlineKeyboardButton(tf_labels[tf], callback_data=f"wl_tf_{tf}") for tf in TIMEFRAMES[2:]],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_watchlist")],
    ])


def confidence_keyboard():
    levels = [50, 60, 65, 70, 75, 80]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{l}%", callback_data=f"wl_conf_{l}") for l in levels[:3]],
        [InlineKeyboardButton(f"{l}%", callback_data=f"wl_conf_{l}") for l in levels[3:]],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_watchlist")],
    ])


# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # رمز الربط إذا وجد

    # /start TOKEN — ربط الحساب
    if args and len(args) > 0:
        token = args[0].strip()
        result = await verify_telegram_link(
            token=token,
            telegram_id=str(user.id),
            telegram_username=user.username or "",
            telegram_name=user.full_name or user.first_name or "",
        )
        if result["success"]:
            plan_ar = {
                "trial": "تجريبي",
                "weekly": "أسبوعي",
                "monthly": "شهري",
            }.get(result.get("plan", ""), result.get("plan", ""))

            await update.message.reply_text(
                f"✅ *تم ربط حسابك بنجاح!*\n\n"
                f"مرحباً {result.get('user_name', '')} 👋\n"
                f"خطتك الحالية: *{plan_ar}*\n\n"
                f"🔥 *تحليلات متبقية:* {result.get('trial_analyses_left', '∞')}\n"
                f"💬 *رسائل شات متبقية:* {result.get('trial_chat_left', '∞')}\n\n"
                f"الآن ستصلك إشعارات فرص التداول مباشرة هنا! 🚀",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ *فشل ربط الحساب*\n\n"
                f"{result.get('detail', 'الرابط غير صالح أو استُخدم مسبقاً.')}\n\n"
                f"للحصول على رابط جديد: سجّل دخول للمنصة → إعدادات → ربط تيليجرام",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)
                ]])
            )
        return

    # /start عادي
    await update.message.reply_text(
        "🤖 *مرحباً في Qaffel AI*\n\n"
        "نظام تحليل الأسواق المالية بالذكاء الاصطناعي\n"
        "مع تنبيهات تلقائية عند ظهور الفرص 🚨\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔗 *لربط حسابك في المنصة:*\n"
        "افتح المنصة ← انقر 'ربط تيليجرام'\n"
        "أو أرسل الرابط الخاص بك هنا\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "اختر *👁 قائمة المراقبة* لتفعيل التنبيهات التلقائية.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


# ─── Button Handler ────────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid  = query.from_user.id

    if data == "menu_back":
        await query.edit_message_text(
            "🤖 *Qaffel AI — القائمة الرئيسية*",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )

    elif data == "menu_analyze":
        kb = []
        for i in range(0, len(MARKETS), 2):
            kb.append([InlineKeyboardButton(MARKET_NAMES.get(m,m), callback_data=f"market_{m}")
                       for m in MARKETS[i:i+2]])
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")])
        await query.edit_message_text("📊 *اختر السوق:*", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(kb))

    elif data == "menu_latest":
        await query.edit_message_text("⏳ جاري الجلب...")
        signals = await fetch_latest_signals()
        if not signals:
            msg = "📡 لا توجد إشارات حتى الآن."
        else:
            msg = "📡 *آخر الإشارات:*\n━━━━━━━━━━━━━━━━━━\n"
            for s in signals:
                e = {"BUY": "🟢", "SELL": "🔴"}.get(s.get("signal_type",""), "⚪")
                msg += f"{e} `{s.get('market','N/A')}` | {s.get('ai_confidence',0):.0f}% | {s.get('status','N/A')}\n"
        await query.edit_message_text(msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

    elif data == "menu_help":
        await query.edit_message_text(
            "📚 *المساعدة:*\n\n"
            "👁 *قائمة المراقبة*\n"
            "اختر الأزواج وسيحللها البوت كل 15 دقيقة.\n\n"
            "🔗 *ربط حسابك*\n"
            "افتح المنصة ← انقر 'ربط تيليجرام' وستصلك فرص مخصصة.\n\n"
            "🔴 *توقف السوق*\n"
            "الفوركس والذهب مغلقان عطلة نهاية الأسبوع.\n"
            "البيتكوين والكريبتو مفتوح 24/7.\n\n"
            "⚙️ *الإعدادات*\n"
            "• الإطار الزمني للتحليل\n"
            "• الحد الأدنى للثقة (الافتراضي 65%)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)],
                [InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]
            ]))

    elif data.startswith("market_"):
        market = data.replace("market_", "")
        tf_labels = {"15m": "15 دقيقة", "1h": "ساعة", "4h": "4 ساعات", "1day": "يومي"}
        kb = [
            [InlineKeyboardButton(tf_labels[tf], callback_data=f"analyze_{market}_{tf}") for tf in TIMEFRAMES[:2]],
            [InlineKeyboardButton(tf_labels[tf], callback_data=f"analyze_{market}_{tf}") for tf in TIMEFRAMES[2:]],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_analyze")],
        ]
        await query.edit_message_text(
            f"⏱ اختر الإطار لـ *{MARKET_NAMES.get(market, market)}*:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("analyze_"):
        _, market, timeframe = data.split("_", 2)

        if not is_market_open(market):
            await query.edit_message_text(
                f"🔴 *السوق مغلق*\n\n"
                f"{MARKET_NAMES.get(market, market)} مغلق خلال عطلة نهاية الأسبوع.\n"
                f"يفتح السوق يوم الاثنين.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_analyze")]]))
            return

        # تحقق من ارتباط الحساب أولاً
        status = await get_user_status(str(uid))
        if not status.get("linked"):
            await query.edit_message_text(
                "🔗 *ربط الحساب مطلوب*\n\n"
                "لاستخدام التحليلات، يجب ربط حسابك في المنصة أولاً.\n\n"
                "📌 الخطوات:\n"
                "1️⃣ افتح المنصة وسجّل دخول\n"
                "2️⃣ اضغط على 'احصل على الرابط' في شريط الربط\n"
                "3️⃣ افتح الرابط وسيتم الربط تلقائياً\n\n"
                "✅ بعد الربط، ستتمكن من الحصول على جميع التحليلات هنا!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح المنصة", url=FRONTEND_URL)],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")],
                ]))
            return

        if not status.get("allowed"):
            reason = status.get("reason", "الاشتراك منتهي")
            await query.edit_message_text(
                f"⛔ *{reason}*\n\n"
                f"جدد اشتراكك للاستمرار في الحصول على التحليلات.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 تجديد الاشتراك", url=f"{FRONTEND_URL}/pricing")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")],
                ]))
            return

        await query.edit_message_text(f"⏳ جاري تحليل {MARKET_NAMES.get(market, market)}...")
        result = await fetch_analysis(market, timeframe, telegram_id=str(uid))

        # خطأ من API
        if result.get("_error"):
            await query.edit_message_text(
                f"⚠️ {result['_error']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))
            return

        msg = format_analysis(result, market, timeframe)
        kb = [
            [InlineKeyboardButton("🔄 تحديث", callback_data=f"analyze_{market}_{timeframe}"),
             InlineKeyboardButton("📊 سوق آخر", callback_data="menu_analyze")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="menu_back")],
        ]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "menu_watchlist":
        wl = user_watchlist.get(uid, set())
        tf = user_timeframe.get(uid, "1h")
        mc = user_min_confidence.get(uid, 65)
        txt = (
            f"👁 *قائمة المراقبة*\n\n"
            f"الأزواج المراقبة: *{len(wl)}* من {len(MARKETS)}\n"
            f"الإطار الزمني: *{tf}*\n"
            f"الحد الأدنى للثقة: *{mc}%*\n\n"
            f"اضغط على الزوج لإضافته أو إزالته:"
        )
        await query.edit_message_text(txt, parse_mode="Markdown", reply_markup=watchlist_keyboard(uid))

    elif data.startswith("wl_toggle_"):
        market = data.replace("wl_toggle_", "")
        if uid not in user_watchlist:
            user_watchlist[uid] = set()
        if market in user_watchlist[uid]:
            user_watchlist[uid].remove(market)
            await query.answer(f"❌ إزالة {market}")
        else:
            user_watchlist[uid].add(market)
            await query.answer(f"✅ إضافة {market}")
        wl = user_watchlist.get(uid, set())
        tf = user_timeframe.get(uid, "1h")
        mc = user_min_confidence.get(uid, 65)
        await query.edit_message_text(
            f"👁 *قائمة المراقبة*\n\nالأزواج: *{len(wl)}* | الإطار: *{tf}* | الحد: *{mc}%*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=watchlist_keyboard(uid))

    elif data == "wl_timeframe":
        await query.edit_message_text("⏱ *اختر الإطار الزمني:*",
                                      parse_mode="Markdown", reply_markup=timeframe_keyboard())

    elif data.startswith("wl_tf_"):
        tf = data.replace("wl_tf_", "")
        user_timeframe[uid] = tf
        await query.answer(f"✅ الإطار: {tf}")
        wl = user_watchlist.get(uid, set())
        mc = user_min_confidence.get(uid, 65)
        await query.edit_message_text(
            f"👁 *قائمة المراقبة*\n\nالأزواج: *{len(wl)}* | الإطار: *{tf}* | الحد: *{mc}%*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=watchlist_keyboard(uid))

    elif data == "wl_confidence":
        await query.edit_message_text(
            "🎯 *اختر الحد الأدنى لنسبة الثقة:*\n(نسبة أعلى = إشارات أقل لكن أقوى)",
            parse_mode="Markdown", reply_markup=confidence_keyboard())

    elif data.startswith("wl_conf_"):
        conf = int(data.replace("wl_conf_", ""))
        user_min_confidence[uid] = conf
        await query.answer(f"✅ الحد الأدنى: {conf}%")
        wl = user_watchlist.get(uid, set())
        tf = user_timeframe.get(uid, "1h")
        await query.edit_message_text(
            f"👁 *قائمة المراقبة*\n\nالأزواج: *{len(wl)}* | الإطار: *{tf}* | الحد: *{conf}%*\n\nاضغط للإضافة/الإزالة:",
            parse_mode="Markdown", reply_markup=watchlist_keyboard(uid))


# ─── Background Monitor ───────────────────────────────────────────────────────
async def fetch_all_db_watchlists() -> list:
    """يجلب قوائم المراقبة من DB عبر API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/api/v1/bot/all-watchlists",
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("users", [])
    except Exception as e:
        logger.error(f"fetch_all_db_watchlists error: {e}")
    return []


async def fetch_signal_outcomes() -> list:
    """يجلب الإشارات التي ضربت TP أو SL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/api/v1/bot/check-outcomes",
                headers=BOT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("triggered", [])
    except Exception as e:
        logger.error(f"fetch_signal_outcomes error: {e}")
    return []


async def monitor_markets(app: Application):
    logger.info("🔍 بدء المراقبة التلقائية...")
    await asyncio.sleep(30)

    _market_reload_counter = 0
    while True:
        try:
            # تحديث قائمة الأزواج كل 4 دورات (~ساعة)
            _market_reload_counter += 1
            if _market_reload_counter % 4 == 0:
                await load_markets_from_api()

            # ── 1. فحص نتائج الإشارات (TP/SL) ──────────────────────────────
            outcomes = await fetch_signal_outcomes()
            for o in outcomes:
                try:
                    tid    = int(o["telegram_id"])
                    status = o["status"]
                    market = o["market"]
                    pnl    = o["pnl_points"]
                    price  = o["current_price"]
                    entry  = o["entry"]
                    tp1    = o["tp1"]
                    tp2    = o["tp2"]
                    sl     = o["sl"]
                    stype  = o["signal_type"]

                    if status == "SL_HIT":
                        header = f"🔴 *وقف الخسارة ضُرب!*"
                        pnl_txt = f"📉 الخسارة: `{abs(pnl):.5f}` نقطة"
                        pnl_usd = f"⚠️ الصفقة أُغلقت بخسارة"
                    elif status == "TP2_HIT":
                        header = f"🎯 *الهدف 2 تحقق!*"
                        pnl_txt = f"📈 الربح: `{pnl:.5f}` نقطة"
                        pnl_usd = f"🏆 صفقة ناجحة — الهدف الكامل"
                    else:
                        header = f"✅ *الهدف 1 تحقق!*"
                        pnl_txt = f"📈 الربح: `{pnl:.5f}` نقطة"
                        pnl_usd = f"💡 فكّر بنقل الإيقاف لنقطة التعادل"

                    rec_ar = "شراء" if stype == "BUY" else "بيع"
                    outcome_msg = (
                        f"{header}\n\n"
                        f"📌 `{market}` — {rec_ar}\n"
                        f"💲 سعر الدخول: `{entry}`\n"
                        f"💲 السعر الحالي: `{price}`\n"
                        f"🎯 TP1: `{tp1}` | TP2: `{tp2}`\n"
                        f"🛑 SL: `{sl}`\n\n"
                        f"{pnl_txt}\n"
                        f"{pnl_usd}\n\n"
                        f"⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
                    )
                    await app.bot.send_message(chat_id=tid, text=outcome_msg, parse_mode="Markdown")
                    logger.info(f"🏁 نتيجة إشارة → {tid} | {market} | {status} | {pnl:+.5f}")
                except Exception as _e:
                    logger.error(f"خطأ إرسال نتيجة: {_e}")

            # ── 2. مراقبة الأزواج وإرسال تنبيهات جديدة ───────────────────
            db_users = await fetch_all_db_watchlists()
            merged: dict[int, tuple[set, str, int]] = {}

            for entry in db_users:
                try:
                    tid = int(entry["telegram_id"])
                    wl  = set(s.upper() for s in entry.get("watchlist", []))
                    if wl:
                        merged[tid] = (wl, entry.get("timeframe", "1h"), entry.get("min_confidence", 65))
                except Exception:
                    pass

            # fallback: قوائم in-memory من أزرار البوت
            for uid, watchlist in list(user_watchlist.items()):
                if uid not in merged and watchlist:
                    merged[uid] = (
                        set(s.upper() for s in watchlist),
                        user_timeframe.get(uid, "1h"),
                        user_min_confidence.get(uid, 65),
                    )

            logger.info(f"🔍 دورة مراقبة — {len(merged)} مستخدم نشط")

            for uid, (watchlist, tf, min_conf) in merged.items():
                for symbol in list(watchlist):
                    now = datetime.now(timezone.utc)

                    if not is_market_open(symbol):
                        # إشعار واحد فقط عند الإغلاق
                        key = (uid, f"{symbol}_closed_{now.date()}")
                        if key not in last_alert:
                            last_alert[key] = now
                            try:
                                await app.bot.send_message(
                                    chat_id=uid,
                                    text=(f"🔴 *السوق مغلق*\n"
                                          f"{MARKET_NAMES.get(symbol, symbol)} مغلق الآن.\n"
                                          f"ستُستأنف التنبيهات يوم الاثنين."),
                                    parse_mode="Markdown")
                            except Exception:
                                pass
                        continue

                    # التحليل بدون خصم كريدت (telegram_id="")
                    result = await fetch_analysis(symbol, tf, telegram_id="")
                    if not result or result.get("error") or result.get("_error"):
                        logger.warning(f"⚠️ تحليل فاشل: {symbol}/{tf} → {result.get('_error', result.get('error', '?'))}")
                        continue

                    rec  = result.get("recommendation", "WATCH")
                    conf = result.get("ai_confidence_score", 0)

                    logger.debug(f"  {symbol}/{tf}: {rec} {conf:.1f}% (حد:{min_conf}%)")

                    if rec not in ("BUY", "SELL") or conf < min_conf:
                        continue

                    # cooldown check
                    key  = (uid, symbol)
                    last = last_alert.get(key)
                    if last and (now - last).total_seconds() < ALERT_COOLDOWN_MINUTES * 60:
                        logger.debug(f"  ⏳ cooldown نشط لـ {symbol} ({uid})")
                        continue

                    last_alert[key] = now
                    emoji  = "🟢" if rec == "BUY" else "🔴"
                    rec_ar = "شراء" if rec == "BUY" else "بيع"

                    # بناء الرسالة مع حماية من الأخطاء
                    try:
                        analysis_text = format_analysis(result, symbol, tf)
                    except Exception as _fe:
                        logger.warning(f"format_analysis خطأ: {_fe}")
                        analysis_text = ""

                    alert_msg = (
                        f"🚨 *فرصة تداول!*\n\n"
                        f"{emoji} *{rec_ar}* — {MARKET_NAMES.get(symbol, symbol)}\n"
                        f"📊 الثقة: *{conf:.1f}%*\n\n"
                        f"{analysis_text}"
                    )[:4000]  # حد Telegram

                    try:
                        await app.bot.send_message(chat_id=uid, text=alert_msg, parse_mode="Markdown")
                        logger.info(f"📨 تنبيه أُرسل → {uid} | {symbol} | {rec} | {conf:.1f}%")
                    except Exception as e:
                        logger.error(f"فشل إرسال تنبيه {uid}/{symbol}: {e}")

                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"خطأ عام في المراقبة: {e}", exc_info=True)

        await asyncio.sleep(MONITOR_INTERVAL)


# ─── Expiry Notification ──────────────────────────────────────────────────────
async def check_expiry_and_notify(app: Application):
    """يرسل إشعار تجديد للمستخدمين قبل انتهاء الاشتراك بيومين"""
    logger.info("🔔 بدء مراقبة انتهاء الاشتراكات...")
    await asyncio.sleep(60)

    while True:
        try:
            users = await get_expiring_users()
            for u in users:
                tg_id = u.get("telegram_id")
                if not tg_id:
                    continue

                key = f"expiry_{tg_id}_{u.get('days_left', 0)}"
                if key in notified_expiry:
                    continue

                days_left = u.get("days_left", 0)
                name      = u.get("full_name") or u.get("email", "")
                plan_ar   = {"weekly": "الأسبوعية", "monthly": "الشهرية", "trial": "التجريبية"}.get(
                    u.get("plan", ""), ""
                )

                if days_left == 0:
                    msg = (
                        f"⏰ *انتهى اشتراكك!*\n\n"
                        f"مرحباً {name} 👋\n"
                        f"انتهت باقتك {plan_ar}.\n\n"
                        f"جدد الآن للاستمرار في الحصول على إشارات التداول 📊\n"
                    )
                else:
                    msg = (
                        f"⚠️ *اشتراكك ينتهي قريباً!*\n\n"
                        f"مرحباً {name} 👋\n"
                        f"باقتك {plan_ar} ستنتهي خلال *{days_left} {'يوم' if days_left == 1 else 'أيام'}*.\n\n"
                        f"جدد الآن لضمان استمرار خدمتك 🚀\n"
                    )

                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("💳 تجديد الاشتراك", url=f"{FRONTEND_URL}/pricing")
                ]])

                try:
                    await app.bot.send_message(
                        chat_id=int(tg_id),
                        text=msg,
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                    notified_expiry.add(key)
                    logger.info(f"🔔 إشعار انتهاء → {tg_id} | {days_left} أيام")
                except Exception as e:
                    logger.error(f"فشل إشعار انتهاء لـ {tg_id}: {e}")

        except Exception as e:
            logger.error(f"خطأ في مراقبة الاشتراكات: {e}")

        await asyncio.sleep(EXPIRY_CHECK_INTERVAL)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير محدد!")
        return

    logger.info("🤖 بدء تشغيل Qaffel AI Bot...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    async def post_init(application: Application):
        await load_markets_from_api()   # تحميل الأزواج فور البدء
        asyncio.create_task(monitor_markets(application))
        asyncio.create_task(check_expiry_and_notify(application))

    app.post_init = post_init

    logger.success("✅ البوت يعمل مع المراقبة التلقائية!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
