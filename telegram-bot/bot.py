"""
Mosh AI Pro v5 - Telegram Bot
بوت تيليجرام لإشارات التداول بالذكاء الاصطناعي مع نظام المراقبة والتنبيهات
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
API_URL    = os.getenv("API_URL", "http://backend:8000")
BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")

MARKETS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
TIMEFRAMES = ["15m", "1h", "4h", "1day"]

MARKET_NAMES = {
    "XAUUSD": "🥇 الذهب",
    "BTCUSD": "₿ بيتكوين",
    "EURUSD": "💶 يورو/دولار",
    "GBPUSD": "💷 جنيه/دولار",
    "USDJPY": "💴 دولار/ين",
    "USDCHF": "🇨🇭 دولار/فرنك",
}

FOREX_MARKETS = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"}

ALERT_COOLDOWN_MINUTES = 60
MONITOR_INTERVAL = 900   # 15 دقيقة

# ─── State ────────────────────────────────────────────────────────────────────
user_watchlist: dict     = {}   # uid -> set of symbols
user_timeframe: dict     = {}   # uid -> timeframe str
user_min_confidence: dict = {}  # uid -> float
last_alert: dict         = {}   # (uid, symbol) -> datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_market_open(symbol: str) -> bool:
    if symbol not in FOREX_MARKETS:
        return True
    return datetime.now(timezone.utc).weekday() < 5


def format_analysis(data: dict, symbol: str, timeframe: str) -> str:
    if not data or data.get("error"):
        return f"❌ تعذر تحليل {symbol}."

    rec = data.get("recommendation", "WATCH")
    emoji  = {"BUY": "🟢", "SELL": "🔴", "WATCH": "⚪", "WAIT": "⚪"}.get(rec, "⚪")
    rec_ar = {"BUY": "شراء", "SELL": "بيع", "WATCH": "مراقبة", "WAIT": "انتظار"}.get(rec, rec)
    conf   = data.get("ai_confidence_score", 0)
    trend  = data.get("trend", {})

    msg = (
        f"🤖 *تحليل Mosh AI Pro v5*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 الزوج: `{symbol}` | الإطار: `{timeframe}`\n\n"
        f"{emoji} *التوصية: {rec_ar}*\n"
        f"📊 نسبة الثقة: `{conf:.1f}%`\n\n"
        f"📈 *الاتجاه:* `{trend.get('direction','N/A')}` ({trend.get('strength',0)}%)\n\n"
    )

    entry = data.get("entry_zones", [])
    sl    = data.get("stop_loss_zone")
    tps   = data.get("take_profit_zones", [])
    rr    = data.get("risk_reward_ratio") or data.get("risk_reward")

    if entry:  msg += f"🎯 *دخول:* `{entry[0]}`\n"
    if sl:     msg += f"🛑 *وقف الخسارة:* `{sl}`\n"
    for i, tp in enumerate(tps[:2], 1):
        msg += f"✅ *هدف {i}:* `{tp}`\n"
    if rr:
        msg += f"\n⚖️ *Risk/Reward:* `{float(rr):.2f}x`\n"

    wyckoff = data.get("wyckoff_analysis", {})
    premium = data.get("premium_discount", {})
    if wyckoff and wyckoff.get("phase"):
        msg += f"📐 Wyckoff: `{wyckoff['phase']}`\n"
    if premium and premium.get("current_zone"):
        msg += f"💹 Zone: `{premium['current_zone']}`\n"

    msg += "\n━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    return msg


async def fetch_analysis(symbol: str, timeframe: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/api/v1/signals/analyze"
            params = {"symbol": symbol, "timeframe": timeframe, "advanced_mode": "true"}
            async with session.post(url, params=params, timeout=aiohttp.ClientTimeout(total=40)) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("data", {})
    except Exception as e:
        logger.error(f"fetch_analysis error: {e}")
    return {}


async def fetch_latest_signals(limit: int = 5) -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/api/v1/signals/latest",
                                   params={"limit": limit},
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("data", [])
    except Exception as e:
        logger.error(f"fetch_latest_signals error: {e}")
    return []


# ─── Keyboards ────────────────────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تحليل سوق",      callback_data="menu_analyze"),
         InlineKeyboardButton("📡 آخر الإشارات",    callback_data="menu_latest")],
        [InlineKeyboardButton("👁 قائمة المراقبة",  callback_data="menu_watchlist"),
         InlineKeyboardButton("ℹ️ مساعدة",           callback_data="menu_help")],
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
        InlineKeyboardButton("⏱ الإطار الزمني",       callback_data="wl_timeframe"),
        InlineKeyboardButton("🎯 الحد الأدنى للثقة",  callback_data="wl_confidence"),
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


# ─── Button Handler ────────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid  = query.from_user.id

    # ── Main menu ──────────────────────────────────────────────────────────
    if data == "menu_back":
        await query.edit_message_text(
            "🤖 *Mosh AI Pro v5* — القائمة الرئيسية",
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
            "اختر الأزواج التي تريد مراقبتها. سيحللها البوت كل 15 دقيقة "
            "ويرسل تنبيهاً فورياً عند ظهور فرصة شراء أو بيع.\n\n"
            "🔴 *توقف السوق*\n"
            "الفوركس والذهب مغلقان عطلة نهاية الأسبوع — لا تُرسل تنبيهات.\n"
            "البيتكوين والكريبتو مفتوح 24/7.\n\n"
            "⚙️ *الإعدادات*\n"
            "• الإطار الزمني للتحليل\n"
            "• الحد الأدنى للثقة (الافتراضي 65%)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

    # ── Market / Analyze ───────────────────────────────────────────────────
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

        await query.edit_message_text(f"⏳ جاري تحليل {MARKET_NAMES.get(market, market)}...")
        result = await fetch_analysis(market, timeframe)
        msg = format_analysis(result, market, timeframe)
        kb = [
            [InlineKeyboardButton("🔄 تحديث", callback_data=f"analyze_{market}_{timeframe}"),
             InlineKeyboardButton("📊 سوق آخر", callback_data="menu_analyze")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="menu_back")],
        ]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    # ── Watchlist ──────────────────────────────────────────────────────────
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
        # refresh keyboard
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
async def monitor_markets(app: Application):
    logger.info("🔍 بدء المراقبة التلقائية...")
    await asyncio.sleep(30)

    while True:
        try:
            for uid, watchlist in list(user_watchlist.items()):
                if not watchlist:
                    continue

                tf       = user_timeframe.get(uid, "1h")
                min_conf = user_min_confidence.get(uid, 65)

                for symbol in list(watchlist):
                    now = datetime.now(timezone.utc)

                    # السوق مغلق
                    if not is_market_open(symbol):
                        key = (uid, f"{symbol}_closed_{now.date()}")
                        if key not in last_alert:
                            last_alert[key] = now
                            try:
                                await app.bot.send_message(
                                    chat_id=uid,
                                    text=(f"🔴 *السوق مغلق*\n"
                                          f"{MARKET_NAMES.get(symbol, symbol)} مغلق الآن (عطلة نهاية الأسبوع).\n"
                                          f"ستُستأنف التنبيهات يوم الاثنين."),
                                    parse_mode="Markdown")
                            except Exception:
                                pass
                        continue

                    # جلب التحليل
                    result = await fetch_analysis(symbol, tf)
                    if not result or result.get("error"):
                        continue

                    rec  = result.get("recommendation", "WATCH")
                    conf = result.get("ai_confidence_score", 0)

                    if rec not in ("BUY", "SELL") or conf < min_conf:
                        continue

                    # Cooldown
                    key  = (uid, symbol)
                    last = last_alert.get(key)
                    if last and (now - last).total_seconds() < ALERT_COOLDOWN_MINUTES * 60:
                        continue

                    last_alert[key] = now
                    emoji  = "🟢" if rec == "BUY" else "🔴"
                    rec_ar = "شراء" if rec == "BUY" else "بيع"

                    alert_msg = (
                        f"🚨 *تنبيه فرصة تداول!*\n\n"
                        f"{emoji} *{rec_ar}* — {MARKET_NAMES.get(symbol, symbol)}\n"
                        f"📊 الثقة: *{conf:.1f}%*\n\n"
                    ) + format_analysis(result, symbol, tf)

                    try:
                        await app.bot.send_message(chat_id=uid, text=alert_msg, parse_mode="Markdown")
                        logger.info(f"📨 تنبيه → {uid} | {symbol} | {rec} | {conf:.1f}%")
                    except Exception as e:
                        logger.error(f"فشل الإرسال لـ {uid}: {e}")

                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"خطأ في المراقبة: {e}")

        await asyncio.sleep(MONITOR_INTERVAL)


# ─── Main ─────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *مرحباً في Mosh AI Pro v5*\n\n"
        "نظام تحليل الأسواق المالية بالذكاء الاصطناعي\n"
        "مع تنبيهات تلقائية عند ظهور الفرص 🚨\n\n"
        "اختر *👁 قائمة المراقبة* لتفعيل التنبيهات التلقائية.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير محدد!")
        return

    logger.info("🤖 بدء تشغيل Mosh AI Pro v5 Bot...")

    builder = Application.builder().token(BOT_TOKEN)
    app = builder.build()

    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("watchlist", lambda u, c: button_handler(
        type('obj', (object,), {'callback_query': type('q', (object,), {
            'answer': lambda: None, 'data': 'menu_watchlist',
            'from_user': u.effective_user,
            'edit_message_text': u.message.reply_text
        })()})(), c)))
    app.add_handler(CallbackQueryHandler(button_handler))

    async def post_init(application: Application):
        asyncio.create_task(monitor_markets(application))

    app.post_init = post_init

    logger.success("✅ البوت يعمل مع المراقبة التلقائية!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
