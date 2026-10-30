"""
Qaffel AI Bot v2 — Professional Edition
إعادة كتابة كاملة: تصفح احترافي، بث إشارات الأدمن، إحصائيات، إحالات
"""

import os, asyncio, aiohttp
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, WebAppInfo, Poll
import messages as M   # (2026-10-19) نصوص الرسائل الموحّدة (HTML) — راجع messages.py
import review_flow as RF   # (2026-10-24) إرسال رأي من البوت بنص وصورة/فيديو
import messages_en as ME   # (2026-10-24) نفس الرسائل بالإنجليزية لمن اختار الإنجليزية بحسابه
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, PollAnswerHandler, TypeHandler,
    MessageHandler, filters,
)
from loguru import logger

# ─── Config ───────────────────────────────────────────────────────────────────
API_URL      = os.getenv("API_URL",             "http://backend:8000")
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN",  "")
FRONTEND_URL = os.getenv("FRONTEND_URL",        "https://qaffel.com")
BOT_SECRET   = os.getenv("BOT_SECRET",          "mosh-bot-secret-2026")
# (2026-10-24) القناة العامة: زر بكل رسالة رئيسية، والبوت (مشرف فيها) ينشر الإشارات المموّهة بسقف يومي
CHANNEL_URL  = os.getenv("TELEGRAM_CHANNEL_URL", "https://t.me/QaffelPlatform")
CHANNEL_ID   = os.getenv("TELEGRAM_CHANNEL_ID",  "@QaffelPlatform")
CHANNEL_TEASER_DAILY_MAX = int(os.getenv("CHANNEL_TEASER_DAILY_MAX", "6"))     # 0 = إيقاف النشر بالقناة
CHANNEL_TEASER_MIN_GAP   = int(os.getenv("CHANNEL_TEASER_MIN_GAP_MIN", "60"))
BOT_HEADERS  = {"X-Bot-Secret": BOT_SECRET}
SETTINGS_URL = f"{FRONTEND_URL}/profile#watchlist"   # صفحة تخصيص الأزواج والفريمات

# ─── Market catalogue ─────────────────────────────────────────────────────────
CATEGORIES: dict[str, dict] = {
    "metals":      {"label": "🥇 معادن",   "symbols": ["XAUUSD", "XAGUSD", "COPPER", "XPTUSD"]},
    "crypto":      {"label": "₿ كريبتو",  "symbols": ["BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD"]},
    "forex":       {"label": "💱 فوركس",   "symbols": [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
        "EURGBP", "EURJPY", "GBPJPY", "DXY",
    ]},
    "commodities": {"label": "🛢 سلع",    "symbols": ["USOIL", "NATGAS"]},
    "indices":     {"label": "📈 مؤشرات", "symbols": ["NAS100", "US30", "SP500"]},
    "stocks":      {"label": "📈 أسهم أمريكية", "symbols": ["AMD", "NFLX"]},
    "gulf":        {"label": "🕌 أسواق خليجية", "symbols": [
        "ARAMCO", "RAJHI", "SABIC", "STC", "SNB", "MAADEN", "ALMARAI", "BAHRI", "ALINMA",
        "EMAAR", "EMIRATESNBD", "DIB", "FAB", "ADNOCDIST", "QNBK",
    ]},
}

MARKET_NAMES: dict[str, str] = {
    "XAUUSD":"🥇 الذهب",    "XAGUSD":"🥈 الفضة", "COPPER":"🟤 النحاس", "XPTUSD":"⚪ البلاتين",
    "BTCUSD":"₿ بيتكوين",  "ETHUSD":"Ξ إيثيريوم", "BNBUSD":"🔷 BNB",
    "SOLUSD":"◎ سولانا",   "XRPUSD":"✕ ريبل",     "ADAUSD":"🔵 كاردانو", "DOGEUSD":"🐕 دوجكوين",
    "EURUSD":"💶 EUR/USD",  "GBPUSD":"💷 GBP/USD",
    "USDJPY":"💴 USD/JPY",  "USDCHF":"🇨🇭 USD/CHF", "AUDUSD":"🦘 AUD/USD", "USDCAD":"🍁 USD/CAD",
    "NZDUSD":"🥝 NZD/USD",  "EURGBP":"💶 EUR/GBP",  "EURJPY":"💶 EUR/JPY", "GBPJPY":"💷 GBP/JPY",
    "DXY":   "💵 مؤشر الدولار",
    "USOIL": "🛢 نفط",     "NATGAS":"🔥 غاز",
    "NAS100":"📈 ناسداك",  "US30":  "📊 داو",       "SP500": "📉 S&P500",
    "AMD":   "🖥 AMD",      "NFLX":  "🎬 نتفليكس",
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


# (2026-09-27) استطلاع الميزات: "عداد وقت متبقي لكل إشارة" (10 أصوات، أعلى
# طلب). رسالة تلغرام ثابتة بمجرد إرسالها — عداد حي غير ممكن هون فعلياً،
# فنعرض الموعد المطلق (وقت الرياض/مكة، نفس مرجع بقية البوت) بدل "متبقي".
# نفس الجدول المستخدم فعلياً بالخادم عند حفظ الإشارة (save-alert-signal/
# signals.py) — مكرَّر عمداً هون لأن telegram-bot عملية منفصلة بلا وصول
# مباشر لكود الباك-إند.
# (2026-10-03) 15m نزلت من 8 لـ3 ساعات (32× حجم الشمعة كانت شذوذاً عن
# الانحدار المتدرّج حولها: 5m=48×، 30m=24× — بنية 15m تتغيّر فعلياً خلال
# ساعات قليلة). نفس القيمة محدَّثة بالخادم (bot.py/signals.py) — الثلاثة
# لازم يبقوا متطابقين دائماً.
_EXPIRY_HOURS = {"1m": 2, "5m": 4, "15m": 3, "30m": 12, "1h": 24, "4h": 72, "1d": 168, "1w": 336}


def _fmt_expiry(expires_at_iso: str | None) -> str:
    if not expires_at_iso:
        return ""
    try:
        dt = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(timezone(timedelta(hours=3)))
        # (2026-10-03) "صالحة حتى" كانت توحي بضمان صلاحية الإعداد لحظة
        # بلحظة لحد هالوقت — والسوق متقلب، البنية ممكن تتغيّر قبلها
        # بكثير. "أقصى مهلة" + تنبيه صريح يوضّح إنه سقف احترازي لا وعد.
        return (
            f"⏳ أقصى مهلة: `{local.strftime('%H:%M')}` ({local.strftime('%d/%m')})"
            f" — راقب السوق، الإعداد قد يتغيّر قبلها\n"
        )
    except Exception:
        return ""


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
def ch_btn(lang: str = "ar"):
    return InlineKeyboardButton("📢 Qaffel channel" if lang == "en" else "📢 قناة Qaffel", url=CHANNEL_URL)


# (2026-10-24) لغة كل مستخدم من حسابه (users.language) — تصل مع قوائم المشتركين والنتائج والإحصائيات وتُحفظ هنا للقوائم.
# غير المرتبط: لغة تيليجرام نفسه (en* ← en).
_user_lang: dict = {}


def lang_for(user) -> str:
    if user is None:
        return "ar"
    cached = _user_lang.get(str(user.id))
    if cached in ("ar", "en"):
        return cached
    return "en" if (getattr(user, "language_code", "") or "").lower().startswith("en") else "ar"


def L(lang: str):
    return ME if lang == "en" else M


def _t(lg: str, ar: str, en: str) -> str:
    return en if lg == "en" else ar


async def ensure_lang(user):
    """(2026-10-24) أول تفاعل للمستخدم: لغته من حسابه (لا ننتظر بثاً يملأ الذاكرة). مرة لكل مستخدم بعمر البوت."""
    if user is None or str(user.id) in _user_lang:
        return
    try:
        res = await _get("/api/v1/bot/user-lang", {"telegram_id": str(user.id)})
        if res.get("lang") in ("ar", "en"):
            _user_lang[str(user.id)] = res["lang"]
    except Exception:
        pass


CAT_EN = {"metals": "🥇 Metals", "crypto": "₿ Crypto", "forex": "💱 Forex", "commodities": "🛢 Commodities",
          "indices": "📈 Indices", "stocks": "📈 US stocks", "gulf": "🕌 Gulf markets"}
TF_EN = {"15m": "15 min", "1h": "1 hour", "4h": "4 hours", "1day": "Daily"}


def mname(sym: str, lg: str) -> str:
    return sym if lg == "en" else MARKET_NAMES.get(sym, sym)


def tf_label(tf: str, lg: str) -> str:
    return (TF_EN if lg == "en" else TF_LABELS).get(tf, tf)


def cat_label(k: str, lg: str) -> str:
    return CAT_EN.get(k, k) if lg == "en" else CATEGORIES.get(k, {}).get("label", k)


_teasers = None   # TeaserGate — يُنشأ عند أول استخدام (messages مستورد كـM)


async def post_channel_teaser(app, sig: dict, text: str):
    """(2026-10-24) ينشر الإشارة المموّهة بالقناة العامة — مرة لكل قرار، بسقف يومي وفاصل أدنى."""
    global _teasers
    if not CHANNEL_ID:
        return
    if _teasers is None:
        _teasers = M.TeaserGate(CHANNEL_TEASER_DAILY_MAX, CHANNEL_TEASER_MIN_GAP)
    key = (sig.get("market"), sig.get("timeframe"), sig.get("signal_type"), round(float(sig.get("entry_price") or 0), 5))
    now = datetime.now(timezone.utc)
    if not _teasers.allow(key, now):
        return
    try:
        bot_url = f"https://t.me/{app.bot.username}" if getattr(app.bot, "username", None) else FRONTEND_URL
        await app.bot.send_message(
            chat_id=CHANNEL_ID, text=text.replace("\n\n" + M.CHANNEL_LINE, ""), parse_mode="HTML",   # لا "تابع قناتنا" داخل القناة
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💳 الاشتراك", url=f"{FRONTEND_URL}/pricing"),
                InlineKeyboardButton("🤖 جرّب البوت", url=bot_url),
            ]]),
        )
        _teasers.mark(key, now)
        logger.info(f"📢 قناة: إشارة مموّهة {key[0]}/{key[1]} ({_teasers.count}/{_teasers.daily_max} اليوم)")
    except Exception as e:
        logger.warning(f"channel teaser {key}: {e}")


def kb_main(lang: str = "ar"):
    if lang == "en":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Quick analysis", callback_data="m_analyze"),
             InlineKeyboardButton("📡 Latest signals", callback_data="m_signals")],
            [InlineKeyboardButton("👁 Watchlist", callback_data="m_watchlist"),
             InlineKeyboardButton("📊 My stats", callback_data="m_stats")],
            [InlineKeyboardButton("🎁 Referral points", callback_data="m_referral"),
             InlineKeyboardButton("❓ Help", callback_data="m_help")],
            [InlineKeyboardButton("🌐 Open dashboard", web_app=WebAppInfo(url=FRONTEND_URL))],
            [InlineKeyboardButton("⭐ Send a review", callback_data="m_review"), ch_btn("en")],
        ])
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
        [InlineKeyboardButton("🌐 فتح الداشبورد", web_app=WebAppInfo(url=FRONTEND_URL))],
        [InlineKeyboardButton("⭐ أرسل رأيك", callback_data="m_review"), ch_btn()],
    ])


def back_btn(lg: str = "ar", data: str = "m_back"):
    return InlineKeyboardButton("🔙 Back" if lg == "en" else "🔙 رجوع", callback_data=data)


def kb_categories(action: str, lg: str = "ar"):
    rows = []
    keys = list(CATEGORIES.keys())
    for i in range(0, len(keys), 2):
        rows.append([InlineKeyboardButton(cat_label(k, lg), callback_data=f"cat_{action}_{k}") for k in keys[i:i+2]])
    rows.append([back_btn(lg)])
    return InlineKeyboardMarkup(rows)


def kb_pairs(cat: str, action: str, lg: str = "ar"):
    syms = CATEGORIES.get(cat, {}).get("symbols", [])
    rows = []
    for i in range(0, len(syms), 2):
        rows.append([InlineKeyboardButton(mname(m, lg), callback_data=f"{action}_{m}") for m in syms[i:i+2]])
    rows.append([back_btn(lg, "m_analyze")])
    return InlineKeyboardMarkup(rows)


def kb_timeframe(symbol: str, lg: str = "ar"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tf_label("15m", lg), callback_data=f"an_{symbol}_15m"),
         InlineKeyboardButton(tf_label("1h", lg),  callback_data=f"an_{symbol}_1h")],
        [InlineKeyboardButton(tf_label("4h", lg),  callback_data=f"an_{symbol}_4h"),
         InlineKeyboardButton(tf_label("1day", lg), callback_data=f"an_{symbol}_1day")],
        [back_btn(lg, "m_analyze")],
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


def kb_tf_select(back: str = "m_watchlist", lg: str = "ar"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tf_label("15m", lg), callback_data="wltf_15m"),
         InlineKeyboardButton(tf_label("1h", lg),  callback_data="wltf_1h")],
        [InlineKeyboardButton(tf_label("4h", lg),  callback_data="wltf_4h"),
         InlineKeyboardButton(tf_label("1day", lg), callback_data="wltf_1day")],
        [back_btn(lg, back)],
    ])


def kb_conf_select(lg: str = "ar"):
    lvls = [50, 60, 65, 70, 75, 80]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{l}%", callback_data=f"wlconf_{l}") for l in lvls[:3]],
        [InlineKeyboardButton(f"{l}%", callback_data=f"wlconf_{l}") for l in lvls[3:]],
        [back_btn(lg, "m_watchlist")],
    ])


# ─── Formatters ───────────────────────────────────────────────────────────────
def fmt_analysis_en(data: dict, symbol: str, timeframe: str) -> str:
    """(2026-10-24) نفس fmt_analysis بالإنجليزية. trade_type_label وtrade_type_warning ومرحلة Wyckoff عربية من المحرك ← لا تُعرض."""
    if not data or data.get("error"):
        return f"❌ Couldn't analyze {symbol}."
    rec   = data.get("recommendation", "WATCH")
    emoji = {"BUY": "🟢", "SELL": "🔴", "WATCH": "⚪", "WAIT": "⚪"}.get(rec, "⚪")
    conf  = get_confidence(data)
    lvls  = data.get("levels", {})
    entry_min, entry_max = lvls.get("entry_zone_min"), lvls.get("entry_zone_max")
    entry_v = lvls.get("entry") or (data.get("entry_zones") or [None])[0]
    sl  = lvls.get("stop_loss") or data.get("stop_loss_zone")
    tp1 = lvls.get("tp1") or (data.get("take_profit_zones") or [None])[0]
    tp2 = lvls.get("tp2") or ((data.get("take_profit_zones") or [None, None])[1] if len(data.get("take_profit_zones") or []) > 1 else None)
    rr  = lvls.get("risk_reward") or data.get("risk_reward_ratio")
    mode = {"SWING": "🎯 Main trend with HTF\n", "SCALP": "⏱️ Quick trade — exit at TP1\n"}.get(data.get("trade_type", ""), "")
    head = (mode + "\n") if rec in ("BUY", "SELL") and mode else ("⏳ *WAIT (NO TRADE)*\nNo clear setup right now.\n\n" if rec == "WAIT" else "")
    msg = (f"🤖 *Qaffel AI — Analysis*\n━━━━━━━━━━━━━━━━━━━━━━\n"
           f"📌 *{symbol}*  │  `{timeframe}`  │  `{_fmt_price(data.get('current_price', 0))}`\n\n" + head +
           f"{emoji} *{rec}*   ·   confidence `{conf:.1f}%`\n\n")
    if entry_min and entry_max:
        msg += f"🎯 Entry:  `{_fmt_price(entry_min)} – {_fmt_price(entry_max)}`\n"
    elif entry_v:
        msg += f"🎯 Entry:  `{_fmt_price(entry_v)}`\n"
    if sl:  msg += f"🛑 Stop:   `{_fmt_price(sl)}`\n"
    if tp1: msg += f"✅ TP1:    `{_fmt_price(tp1)}`\n"
    if tp2: msg += f"✅ TP2:    `{_fmt_price(tp2)}`\n"
    if lvls.get("ladder_tp3"): msg += f"✅ TP3:    `{_fmt_price(lvls['ladder_tp3'])}`\n"
    if rr:  msg += f"⚖️ R/R:    `{float(rr):.2f}x`\n"
    if rec in ("BUY", "SELL"):
        msg += "💡 At TP1, consider moving your stop to entry to lock the trade\n"
        _exp = datetime.now(timezone.utc) + timedelta(hours=_EXPIRY_HOURS.get(timeframe, 24))
        msg += f"⏳ Valid until `{_exp:%H:%M}` UTC ({_exp:%d/%m})\n"
    ob = data.get("order_blocks", {})
    liq = data.get("liquidity_analysis") or data.get("liquidity", {})
    if (ob.get("bullish_obs") or []) and isinstance(ob["bullish_obs"][0], dict):
        o = ob["bullish_obs"][0]
        msg += f"🟢 Support OB:     `{_fmt_price(o.get('low'))} – {_fmt_price(o.get('high'))}`\n"
    if (ob.get("bearish_obs") or []) and isinstance(ob["bearish_obs"][0], dict):
        o = ob["bearish_obs"][0]
        msg += f"🔴 Resistance OB:  `{_fmt_price(o.get('low'))} – {_fmt_price(o.get('high'))}`\n"
    if isinstance(liq, dict):
        if liq.get("nearest_ssl"): msg += f"🧲 Liquidity below: `{_fmt_price(liq.get('nearest_ssl'))}`\n"
        if liq.get("nearest_bsl"): msg += f"🧲 Liquidity above: `{_fmt_price(liq.get('nearest_bsl'))}`\n"
    pdz = data.get("premium_discount", {})
    zone = (pdz.get("current_zone") or pdz.get("zone")) if isinstance(pdz, dict) else None
    if zone: msg += f"💹 Zone:           `{zone}`\n"
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━\n⚠️ _For information only — not investment advice._"
    return msg


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
    if lvls.get("ladder_tp3"): msg += f"✅ هدف 3: `{_fmt_price(lvls['ladder_tp3'])}`\n"
    if rr:  msg += f"⚖️ R/R:   `{float(rr):.2f}x`\n"
    if rec in ("BUY", "SELL"):
        # (2026-10-03) نفس تنبيه "تأمين الصفقة" بـfmt_new_signal — موحَّد
        # عبر كل مصادر الإشارة الأولى (بث تلقائي أو تحليل يدوي)، لا رسالة
        # تحقق الهدف بعد فوات الأوان.
        msg += "💡 عند تحقيق الهدف 1، فكّر بنقل وقف الخسارة لنقطة الدخول لتأمين الصفقة\n"
        # لا expires_at فعلي هون (data تحليل حي، لا صف Signal محفوظ بعد) —
        # نفس tf_hours المستخدم فعلياً عند save-alert-signal بالخادم لحظات لاحقاً.
        _exp_h  = _EXPIRY_HOURS.get(timeframe, 24)
        _exp_dt = datetime.now(timezone.utc) + timedelta(hours=_exp_h)
        msg += _fmt_expiry(_exp_dt.isoformat())

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
        + (f"✅ هدف 3: `{_fmt_price(s['take_profit_3'])}`\n" if s.get("take_profit_3") else "")
    )
    if rr:
        msg += f"⚖️ R/R:   `{float(rr):.1f}x`\n"
    # (2026-10-03) نقل تنبيه "تأمين الصفقة" (نقل الوقف لنقطة الدخول) من
    # رسالة تحقق الهدف 1 (كان بعد فوات الأوان لمن ما يتابع تلغرام لحظياً)
    # لنفس الإشارة الأولى — المتداول يعرف الخطة مسبقاً بدل ما يُفاجأ فيها
    # بعد تحقق الهدف.
    msg += "💡 عند تحقيق الهدف 1، فكّر بنقل وقف الخسارة لنقطة الدخول لتأمين الصفقة\n"
    msg += _fmt_expiry(s.get("expires_at"))
    if tt_warning:
        msg += f"{tt_warning}\n"

    PHASE_AR = {"ACCUMULATION":"تراكم","DISTRIBUTION":"توزيع","MARKUP":"صعود","MARKDOWN":"هبوط"}
    ZONE_AR  = {"PREMIUM":"مرتفعة","DISCOUNT":"منخفضة","EQUILIBRIUM":"توازن"}
    phase = PHASE_AR.get(s.get("wyckoff_phase",""), "")
    zone  = ZONE_AR.get(s.get("premium_discount",""), "")
    if phase: msg += f"📐 Wyckoff: `{phase}`\n"
    if zone:  msg += f"💹 Zone:    `{zone}`\n"

    news_ctx = s.get("news_context")
    if news_ctx:
        msg += f"📰 سياق السوق: _{news_ctx}_\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    return msg


def fmt_new_signal_masked(s: dict) -> str:
    """نسخة مموّهة لمستخدمي التجربة بعد استهلاك حصتهم اليومية المجانية —
    تؤكد وجود إشارة (الاتجاه + الثقة) بدون تفاصيل الدخول/SL/TP القابلة للتداول
    فعلياً. القرار المنتجي: نكمل نبعت إشعار حتى لو ما عندهم اشتراك فعّال،
    عشان "بنواصل إرسال الإشارات بحال وجدت" — بس التفاصيل مقفلة."""
    stype  = s.get("signal_type", "BUY")
    emoji  = "🟢" if stype == "BUY" else "🔴"
    rec_ar = "شراء" if stype == "BUY" else "بيع"
    mname  = MARKET_NAMES.get(s.get("market", ""), s.get("market", ""))
    conf   = get_confidence(s)
    tf     = TF_LABELS.get(s.get("timeframe", ""), s.get("timeframe", ""))

    return (
        f"🚨 *إشارة جديدة │ Qaffel AI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} *{rec_ar}*  ─  {mname}\n"
        f"📊 ثقة: *{conf:.0f}%*   ⏱ {tf}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔒 استهلكت حصتك المجانية اليوم — تفاصيل الدخول/الوقف/الأهداف مقفلة\n"
        f"💳 اشترك لرؤية التفاصيل الكاملة لهذه الإشارة وكل الإشارات القادمة\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ _للمعلومات فقط، ليس توصية استثمارية._"
    )


def fmt_outcome(o: dict) -> str:
    status  = o["status"]
    market  = o["market"]
    stype   = o["signal_type"]
    entry   = _fmt_price(o["entry"])
    # (2026-10-16) "إغلاق" = المستوى الذي أُغلقت عنده الصفقة لا سعر لحظة الاكتشاف — الحلقة ترصد كل ~90ث فالسعر
    # الحالي قد يكون تجاوز الوقف/الهدف (XRP: وقف 1.30405 وعُرض 1.3054؛ AMD: وقف 536.78 وعُرض 534.99) فيبدو
    # الخروج أسوأ/أفضل مما حدث. النسبة والنقاط محسوبة أصلاً من المستوى (_pnl_for_outcome).
    _exit = {"SL_HIT": o.get("sl"), "TP1_HIT": o.get("tp1"), "TP2_HIT": o.get("tp2"), "TP3_HIT": o.get("tp3"),
             "BREAKEVEN": o.get("entry")}.get(o["status"])
    price   = _fmt_price(_exit if _exit is not None else o["current_price"])
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

    # (2026-10-03) النسبة % صارت الرقم الرئيسي لا النقاط — النقاط ليست
    # عملة موحّدة بين الرموز (فارق المضاعف يبلغ 1200 ضعفاً، راجع
    # _calc_points بـadmin.py وDECISIONS.md)، فعميل يراقب الفضة بيشوف
    # نقاطاً صغيرة جداً مقابل نفس جودة صفقة على الذهب تبان نقاطها ضخمة —
    # فرق مظهري بحت سببه السعر المطلق للرمز، لا جودة القرار. % مقارنة
    # عادلة بين كل الرموز، فصارت هي البارزة والنقاط تفصيل ثانوي بعدها.
    if status in ("TP2_HIT", "TP3_HIT"):
        header  = "🏆 *الهدف 3 تحقق!*" if status == "TP3_HIT" else "🏆 *الهدف 2 تحقق!*"
        pnl_line = (
            f"📈 الربح: *{sign_pct}{pnl_pct:.2f}%*"
            f"  │  {sign_pts}{_fmt_pts(pnl)} نقطة"
        )
        tip = "الهدف التالي هدف 3 — استمر بالمتابعة 🎯" if status == "TP2_HIT" and o.get("tp3") else "صفقة ممتازة — الهدف الكامل 🎯"
    elif status == "TP1_HIT":
        header  = "✅ *الهدف 1 تحقق!*"
        pnl_line = (
            f"📈 الربح: *{sign_pct}{pnl_pct:.2f}%*"
            f"  │  {sign_pts}{_fmt_pts(pnl)} نقطة"
        )
        tip = "الهدف التالي هدف 2 — استمر بالمتابعة 🎯"
    elif status == "BREAKEVEN":
        # (2026-10-16) وصلته رسالة التأمين ثم عاد للدخول — من نقل الوقف للدخول خرج بلا خسارة
        header  = "⚖️ *أُغلقت على التأمين (نقطة الدخول)*"
        pnl_line = "📊 النتيجة: *0%* — بلا ربح ولا خسارة لمن نقل الوقف للدخول"
        tip = "التأمين حمى رأس المال — هذا دوره 🛡️"
    else:
        header  = "🔴 *وقف الخسارة ضُرب*"
        pnl_line = (
            f"📉 الخسارة: *{sign_pct}{pnl_pct:.2f}%*"
            f"  │  {sign_pts}{_fmt_pts(pnl)} نقطة"
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

        if ok and (_user_lang.pop(str(user.id), None) or True) and (await ensure_lang(user) or True) \
                and lang_for(user) == "en":
            plan_en = {"trial": "Trial", "weekly": "Weekly", "monthly": "Monthly"}.get(res.get("plan", ""), res.get("plan", ""))
            await update.message.reply_text(
                f"✅ *Your account is linked!*\n\n"
                f"Welcome *{res.get('user_name','')}* 👋\n"
                f"Plan: *{plan_en}*   │   Analyses left: *{res.get('trial_analyses_left', '∞')}*\n\n"
                f"🚨 Trading signals will arrive right here!\n"
                f"Turn on *👁 Watchlist* for automatic alerts.",
                parse_mode="Markdown",
                reply_markup=kb_main("en"),
            )
        elif ok:
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
                    InlineKeyboardButton("🌐 فتح المنصة", web_app=WebAppInfo(url=FRONTEND_URL))
                ]]),
            )
        return

    await ensure_lang(update.effective_user)
    _lg = lang_for(update.effective_user)
    if _lg == "en":
        await update.message.reply_text(
            "🤖 *Qaffel AI*\n\n"
            "Smart trading platform powered by ICT/SMC and AI\n\n"
            "🔗 *To link your account:*\n"
            "Open the platform → tap «Link Telegram» → open the link\n\n"
            "Once linked, signals and alerts reach you here automatically 🚀",
            parse_mode="Markdown",
            reply_markup=kb_main("en"),
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
    await ensure_lang(update.effective_user)
    _lg = lang_for(update.effective_user)
    await update.message.reply_text(
        "🤖 *Qaffel AI — Main menu*" if _lg == "en" else "🤖 *Qaffel AI — القائمة الرئيسية*",
        parse_mode="Markdown",
        reply_markup=kb_main(_lg),
    )


# (2026-09-23) نفس نص شاشة "❓ المساعدة" بالضبط (راجع فرع d == "m_help" أسفل) —
# أُضيف كأمر /help مستقل عشان يظهر بقائمة أوامر تيليجرام الأصلية (set_my_commands
# بـmain()) بدل ما يكون الوصول الوحيد له عبر ضغطتين. تحسين واجهة بحت، لا علاقة
# له بحلقة الرصد/البث المجمَّدة (DECISIONS.md 17/09) — ما يلمسها إطلاقاً.
HELP_EN = (
    "📚 *Help*\n\n"
    "📊 *Quick analysis*\nChoose a category, then a pair and a timeframe.\n\n"
    "👁 *Watchlist*\nPick the pairs you want monitored.\nThe bot analyzes them every 15 minutes automatically.\n\n"
    "📡 *Signals*\nThe latest signals published.\n\n"
    "📈 *My stats*\nYour win rate and results.\n\n"
    "🎁 *Referral*\nYour personal link + commission details."
)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_lang(update.effective_user)
    lg = lang_for(update.effective_user)
    await update.message.reply_text(
        HELP_EN if lg == "en" else (
        "📚 *المساعدة*\n\n"
        "📊 *تحليل فوري*\nاختر الفئة ثم الزوج والإطار الزمني.\n\n"
        "👁 *المراقبة*\nاختر الأزواج التي تريد مراقبتها.\n"
        "البوت يحللها كل 15 دقيقة تلقائياً.\n\n"
        "📡 *الإشارات*\nآخر الإشارات المنشورة من الأدمن.\n\n"
        "📈 *إحصائياتي*\nعرض نسبة ربحك ومجموع نقاطك.\n\n"
        "🎁 *الإحالة*\nرابطك الخاص + تفاصيل العمولة."),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(_t(lg, "🌐 فتح المنصة", "🌐 Open platform"), web_app=WebAppInfo(url=FRONTEND_URL))],
            [InlineKeyboardButton(_t(lg, "🔙 القائمة الرئيسية", "🔙 Main menu"), callback_data="m_back")],
        ]),
    )


# ─── Button Handler ───────────────────────────────────────────────────────────
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    await q.answer()
    d   = q.data
    uid = q.from_user.id
    tgid= str(uid)
    await ensure_lang(q.from_user)
    lg  = lang_for(q.from_user)

    # ── Ignore separator buttons
    if d == "noop":
        return

    # ── Back to main menu
    if d in ("m_back", "m_main"):
        _lg = lang_for(q.from_user)
        await q.edit_message_text(
            "🤖 *Qaffel AI — Main menu*" if _lg == "en" else "🤖 *Qaffel AI — القائمة الرئيسية*",
            parse_mode="Markdown", reply_markup=kb_main(_lg),
        )
        return

    # ─────────────────────── ANALYZE ──────────────────────────────────────────
    if d == "m_analyze":
        await q.edit_message_text(
            _t(lg, "📊 *تحليل فوري*\nاختر الفئة:", "📊 *Quick analysis*\nChoose a category:"),
            parse_mode="Markdown", reply_markup=kb_categories("an", lg),
        )
        return

    # (2026-10-12) "🔕 أوقف إشارات X" تحت الإشارة — تخصيص بضغطة دون فتح الموقع
    if d.startswith("mute_"):
        symbol = d[5:].upper()
        r = await _post("/api/v1/bot/mute-symbol",
                        json={"telegram_id": tgid, "symbol": symbol, "all_symbols": sorted(_VALID_SYMBOLS)})
        if not r or not r.get("ok"):
            text = (_t(lg, "اربط حسابك في كفيل أولاً لتتحكم بالإشارات التي تصلك 👇", "Link your Qaffel account first to control which signals you get 👇")
                    if r and r.get("reason") == "not_linked"
                    else _t(lg, "تعذّر التعديل الآن، جرّب بعد قليل.", "Couldn't update right now, try again shortly."))
        elif r.get("all_muted"):
            text = _t(lg, f"🔕 أوقفنا إشارات {symbol}، ولم يبقَ زوج آخر في قائمتك فأوقفنا الإشعارات كلها. فعّلها من الإعدادات متى أردت.",
                      f"🔕 {symbol} signals muted. No other pair is left in your list, so all notifications are off. Turn them back on in settings anytime.")
        else:
            text = _t(lg, f"🔕 لن تصلك إشارات {symbol} بعد الآن ({r.get('remaining', 0)} زوجاً في قائمتك).\nتقدر ترجعها أو تغيّر الفريمات بأي وقت من الإعدادات.",
                      f"🔕 You won't get {symbol} signals anymore ({r.get('remaining', 0)} pairs left in your list).\nYou can restore it or change timeframes anytime in settings.")
        await context.bot.send_message(
            chat_id=uid, text=text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(lg, "⚙️ الإعدادات", "⚙️ Settings"), url=SETTINGS_URL)]]),
        )
        return

    if d.startswith("cat_an_"):
        cat = d[7:]
        info = CATEGORIES.get(cat, {})
        await q.edit_message_text(
            _t(lg, f"📊 *{info.get('label',cat)}* — اختر الزوج:", f"📊 *{cat_label(cat, 'en')}* — choose a pair:"),
            parse_mode="Markdown", reply_markup=kb_pairs(cat, "sym", lg),
        )
        return

    if d.startswith("sym_"):
        symbol = d[4:]
        if not is_market_open(symbol):
            exchange = GULF_MARKETS.get(symbol.upper())
            if lg == "en":
                reopen_line = ("is closed outside its daily trading hours." if exchange
                               else "is closed for the weekend.\nIt reopens on Monday.")
            elif exchange:
                reopen_line = f"السوق مغلق حالياً خارج ساعات التداول اليومية.\n{gulf_reopen_text(exchange)}."
            else:
                reopen_line = "مغلق خلال عطلة نهاية الأسبوع.\nيفتح مجدداً يوم الاثنين."
            await q.edit_message_text(
                _t(lg, "🔴 *السوق مغلق*", "🔴 *Market closed*") + "\n\n"
                f"{mname(symbol, lg)} {reopen_line}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[back_btn(lg, "m_analyze")]]),
            )
            return
        await q.edit_message_text(
            _t(lg, f"⏱ *{mname(symbol, lg)}* — اختر الإطار الزمني:", f"⏱ *{symbol}* — choose a timeframe:"),
            parse_mode="Markdown", reply_markup=kb_timeframe(symbol, lg),
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
                _t(lg, "🔗 *ربط الحساب مطلوب*\n\n1️⃣ افتح المنصة وسجّل دخول\n2️⃣ اضغط «ربط تيليجرام»\n3️⃣ افتح الرابط",
                   "🔗 *Account link required*\n\n1️⃣ Open the platform and log in\n2️⃣ Tap «Link Telegram»\n3️⃣ Open the link"),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(_t(lg, "🌐 فتح المنصة", "🌐 Open platform"), web_app=WebAppInfo(url=FRONTEND_URL))],
                    [back_btn(lg)],
                ]),
            )
            return
        if not status.get("allowed"):
            await q.edit_message_text(
                (f"⛔ *{status.get('reason','الاشتراك منتهي')}*\n\nجدد اشتراكك للمتابعة." if lg != "en"
                 else "⛔ *Your plan doesn't allow this right now*\n\nRenew your subscription to continue."),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(_t(lg, "💳 تجديد الاشتراك", "💳 Renew subscription"), url=f"{FRONTEND_URL}/pricing")],
                    [back_btn(lg)],
                ]),
            )
            return

        await q.edit_message_text(_t(lg, f"⏳ جاري تحليل {mname(symbol, lg)}…", f"⏳ Analyzing {symbol}…"))

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
                reply_markup=InlineKeyboardMarkup([[back_btn(lg)]]),
            )
            return

        msg = fmt_analysis_en(data, symbol, tf) if lg == "en" else fmt_analysis(data, symbol, tf)
        await q.edit_message_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_t(lg, "🔄 تحديث", "🔄 Refresh"), callback_data=f"an_{symbol}_{tf}"),
                 InlineKeyboardButton(_t(lg, "📊 سوق آخر", "📊 Another market"), callback_data="m_analyze")],
                [InlineKeyboardButton(_t(lg, "🏠 الرئيسية", "🏠 Home"), callback_data="m_back")],
            ]),
        )
        return

    # ─────────────────────── SIGNALS ──────────────────────────────────────────
    if d == "m_signals":
        await q.edit_message_text(_t(lg, "⏳ جاري جلب الإشارات…", "⏳ Fetching signals…"))
        # (2026-10-19) كان /signals/latest بمفتاح البوت ← 401 دائماً ← "لا توجد إشارات" للجميع
        res  = await _get("/api/v1/bot/latest-signals", {"telegram_id": tgid, "limit": 8})
        if not res.get("linked"):
            await q.edit_message_text(
                _t(lg, "🔗 *ربط الحساب مطلوب لعرض الإشارات.*", "🔗 *Link your account to see signals.*"),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(_t(lg, "🌐 فتح المنصة", "🌐 Open platform"), web_app=WebAppInfo(url=FRONTEND_URL))],
                    [back_btn(lg)],
                ]),
            )
            return
        sigs = res.get("data", [])

        STATUS_ICONS = {
            "ACTIVE":  "🔵", "TP1_HIT": "✅", "TP2_HIT": "🏆", "TP3_HIT": "🏆",
            "SL_HIT":  "❌", "PENDING": "⏳", "EXPIRED":  "⚫", "BREAKEVEN": "⚖️",
        }
        STATUS_AR = {
            "ACTIVE":"نشطة", "TP1_HIT":"هدف 1 ✅", "TP2_HIT":"هدف 2 🏆", "TP3_HIT":"هدف 3 🏆",
            "SL_HIT":"وقف ❌", "PENDING":"معلقة", "EXPIRED":"منتهية", "BREAKEVEN":"تأمين ⚖️",
        } if lg != "en" else {
            "ACTIVE":"active", "TP1_HIT":"TP1 ✅", "TP2_HIT":"TP2 🏆", "TP3_HIT":"TP3 🏆",
            "SL_HIT":"stop ❌", "PENDING":"pending", "EXPIRED":"expired", "BREAKEVEN":"breakeven ⚖️",
        }

        if not sigs:
            msg = _t(lg, "📡 *آخر الإشارات*\n━━━━━━━━━━━━━━━━━━━━━━\n_لا توجد إشارات حتى الآن._\n\nحلّل سوقاً من قسم ⚡ تحليل فوري.",
                     "📡 *Latest signals*\n━━━━━━━━━━━━━━━━━━━━━━\n_No signals yet._\n\nAnalyze a market from ⚡ Quick analysis.")
        else:
            active_count = sum(1 for s in sigs if s.get("status") == "ACTIVE")
            msg = (
                _t(lg, "📡 *آخر الإشارات*", "📡 *Latest signals*") + "\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                + _t(lg, f"🔵 نشطة: *{active_count}*  │  إجمالي: *{len(sigs)}*", f"🔵 Active: *{active_count}*  │  Total: *{len(sigs)}*") + "\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            for s in sigs:
                if s.get("locked"):   # (2026-10-19) مموّهة: بلا اتجاه ولا ثقة ولا مستويات
                    _mn = mname(s.get("market", ""), lg)
                    msg += _t(lg, f"🔒 *{_mn}*  إشارة — تفاصيلها لمشتركي الخطط", f"🔒 *{_mn}*  signal — details for subscribers") + "\n─────────────────────\n"
                    continue
                stype  = s.get("signal_type", "BUY")
                status = s.get("status", "ACTIVE")
                conf   = get_confidence(s)
                _mn    = mname(s.get("market", ""), lg)
                entry  = _fmt_price(s.get("entry_price"))
                tp1    = _fmt_price(s.get("take_profit_1"))
                sl_p   = _fmt_price(s.get("stop_loss"))
                rr     = s.get("risk_reward_ratio")

                dir_emoji   = "▲" if stype == "BUY" else "▼"
                dir_ar      = (("BUY" if stype == "BUY" else "SELL") if lg == "en" else ("شراء" if stype == "BUY" else "بيع"))
                _st_show    = "TP3_HIT" if s.get("tp3_hit") else status
                status_icon = STATUS_ICONS.get(_st_show, "○")
                status_ar   = STATUS_AR.get(_st_show, status)
                conf_bar    = "█" * int(conf / 20) + "░" * (5 - int(conf / 20))

                msg += (
                    f"{dir_emoji} *{_mn}*  `{dir_ar}`  {status_icon} _{status_ar}_\n"
                    f"  🎯 `{entry}`  🛑 `{sl_p}`  ✅ `{tp1}`"
                )
                if rr:
                    msg += f"  ⚖️ `{float(rr):.1f}x`"
                msg += f"\n  [{conf_bar}] `{conf:.0f}%`\n"
                msg += "─────────────────────\n"

        await q.edit_message_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_t(lg, "🔄 تحديث", "🔄 Refresh"), callback_data="m_signals"),
                 InlineKeyboardButton(_t(lg, "⚡ تحليل فوري", "⚡ Quick analysis"), callback_data="m_analyze")],
                [InlineKeyboardButton(_t(lg, "🌐 الداشبورد", "🌐 Dashboard"), web_app=WebAppInfo(url=FRONTEND_URL)),
                 back_btn(lg)],
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

        notif_line = _t(lg, "🔔 الإشعارات مفعّلة" if notif else "🔕 الإشعارات موقفة",
                        "🔔 Notifications on" if notif else "🔕 Notifications off")

        # قائمة الأزواج النشطة مختصرة
        if wl:
            wl_preview = "  ".join(f"`{s}`" for s in sorted(wl)[:8])
            if count > 8:
                wl_preview += f"  …+{count-8}"
        else:
            wl_preview = _t(lg, "_لم يتم اختيار أي زوج بعد_", "_No pairs selected yet_")

        await q.edit_message_text(
            (_t(lg, "👁 *قائمة المراقبة*", "👁 *Watchlist*") + "\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            + _t(lg, f"{bar}  *{count}/{total}* زوج", f"{bar}  *{count}/{total}* pairs") + "\n\n"
            + _t(lg, f"⏱ الإطار: *{TF_LABELS.get(tf,tf)}*   🎯 الحد: *{conf}%*", f"⏱ Timeframe: *{tf_label(tf, 'en')}*   🎯 Min: *{conf}%*") + "\n")
            +
            f"{notif_line}\n\n"
            + _t(lg, "الأزواج المختارة:", "Selected pairs:") + f"\n{wl_preview}\n\n"
            + _t(lg, "💡 لإدارة الأزواج والإعدادات بشكل أفضل افتح الداشبورد:", "💡 Manage pairs and settings more easily from the dashboard:"),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_t(lg, "🌐 إدارة المراقبة من الداشبورد", "🌐 Manage watchlist in the dashboard"), web_app=WebAppInfo(url=f"{FRONTEND_URL}/dashboard"))],
                [InlineKeyboardButton(_t(lg, "🔔 تبديل الإشعارات", "🔔 Toggle notifications"), callback_data="wl_notif"),
                 back_btn(lg)],
            ]),
        )
        return

    if d == "wl_notif":
        await _load_wl_from_db(uid, tgid)
        _wl_notif[uid] = not _wl_notif.get(uid, True)
        await _save_wl_to_db(uid, tgid)
        st = _t(lg, "مفعّل 🔔" if _wl_notif[uid] else "موقف 🔕", "on 🔔" if _wl_notif[uid] else "off 🔕")
        await q.answer(_t(lg, f"الإشعارات: {st}", f"Notifications: {st}"))
        notif_line = _t(lg, "🔔 الإشعارات مفعّلة" if _wl_notif[uid] else "🔕 الإشعارات موقفة",
                        "🔔 Notifications on" if _wl_notif[uid] else "🔕 Notifications off")
        # إعادة رسم شاشة المراقبة
        wl    = _wl_symbols.get(uid, set())
        tf    = _wl_tf.get(uid, "1h")
        conf  = _wl_conf.get(uid, 65)
        notif = _wl_notif[uid]
        count = len(wl)
        total = sum(len(v["symbols"]) for v in CATEGORIES.values())
        filled = min(count, 10)
        bar = "🟦" * filled + "⬜" * (10 - filled)
        wl_preview = "  ".join(f"`{s}`" for s in sorted(wl)[:8]) if wl else _t(lg, "_لم يتم اختيار أي زوج_", "_No pairs selected_")
        if count > 8: wl_preview += f"  …+{count-8}"
        await q.edit_message_text(
            (_t(lg, "👁 *قائمة المراقبة*", "👁 *Watchlist*") + "\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            + _t(lg, f"{bar}  *{count}/{total}* زوج", f"{bar}  *{count}/{total}* pairs") + "\n\n"
            + _t(lg, f"⏱ الإطار: *{TF_LABELS.get(tf,tf)}*   🎯 الحد: *{conf}%*", f"⏱ Timeframe: *{tf_label(tf, 'en')}*   🎯 Min: *{conf}%*") + "\n")
            +
            f"{notif_line}\n\n"
            + _t(lg, "الأزواج المختارة:", "Selected pairs:") + f"\n{wl_preview}\n\n"
            + _t(lg, "💡 لإدارة الأزواج والإعدادات بشكل أفضل افتح الداشبورد:", "💡 Manage pairs and settings more easily from the dashboard:"),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_t(lg, "🌐 إدارة المراقبة من الداشبورد", "🌐 Manage watchlist in the dashboard"), web_app=WebAppInfo(url=f"{FRONTEND_URL}/dashboard"))],
                [InlineKeyboardButton(_t(lg, "🔔 تبديل الإشعارات", "🔔 Toggle notifications"), callback_data="wl_notif"),
                 back_btn(lg)],
            ]),
        )
        return

    # handlers قديمة للـ watchlist — احتياطي للتوافق مع أي رسائل قديمة
    if d.startswith("wl_t_") or d in ("wl_all","wl_none","wl_tf","wl_conf","wl_save") \
            or d.startswith("wltf_") or d.startswith("wlconf_"):
        await q.answer(_t(lg, "⚙️ أدر المراقبة من الداشبورد", "⚙️ Manage your watchlist from the dashboard"))
        return

    # ─────────────────────── STATS ────────────────────────────────────────────
    if d == "m_stats":
        await q.edit_message_text(_t(lg, "⏳ جاري جلب إحصائياتك…", "⏳ Fetching your stats…"))
        st = await _get("/api/v1/bot/user-stats", {"telegram_id": tgid})
        if not st.get("linked"):
            await q.edit_message_text(
                _t(lg, "🔗 *ربط الحساب مطلوب لعرض الإحصائيات.*", "🔗 *Link your account to see your stats.*"),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح المنصة", web_app=WebAppInfo(url=FRONTEND_URL))],
                    [InlineKeyboardButton("🔙 رجوع",       callback_data="m_back")],
                ]),
            )
            return

        # (2026-10-19) بطاقة موحّدة بـR (messages.stats_card) — "إجمالي النقاط" كان يجمع نقاطاً غير قابلة للجمع بين
        # الرموز (فارق المضاعف 1200 ضعف — DECISIONS.md) فيُظهر رقماً سالباً ضخماً بينما النتيجة بالمخاطرة موجبة.
        _lg = st.get("lang") or "ar"
        _user_lang[tgid] = _lg
        text = ME.stats_card(st) if _lg == "en" else M.stats_card(st, MARKET_NAMES)

        await q.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh" if _lg == "en" else "🔄 تحديث", callback_data="m_stats"),
                 InlineKeyboardButton("🌐 Dashboard" if _lg == "en" else "🌐 الداشبورد", web_app=WebAppInfo(url=FRONTEND_URL))],
                [ch_btn(_lg)],
                [back_btn(_lg)],
            ]),
        )
        return

    # ─────────────────────── REFERRAL ─────────────────────────────────────────
    if d == "m_referral":
        st = await _get("/api/v1/bot/user-stats", {"telegram_id": tgid})
        if not st.get("linked"):
            await q.edit_message_text(
                _t(lg, "🔗 *ربط الحساب مطلوب للوصول لبرنامج الإحالة.*", "🔗 *Link your account to access the referral program.*"),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح المنصة", web_app=WebAppInfo(url=FRONTEND_URL))],
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
        if lg == "en":
            tier_line = ("🥇 *Gold tier* — 15% commission" if count >= 25 else
                         "🥈 *Silver tier* — 5% commission → 15 referrals to gold" if count >= 10 else
                         "🥉 *Bronze tier* — 5% commission")
            text = (f"🎁 *Referral points*\n━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✨ *Your points:* `{ref_pts}`   👥 *Invited:* `{count}`\n{pts_bar}\n")
            text += (f"🎉 You have *{free_analyses}* free analyses ready to redeem!\n" if free_analyses > 0
                     else f"⚡ You need *{pts_to_next}* points for your next free analysis\n")
            text += (f"\n{tier_line}\n━━━━━━━━━━━━━━━━━━━━━━\n💡 *How to earn points*\n"
                     f"  • Friend signs up = *+10 points*\n  • Friend subscribes = *+50 points*\n"
                     f"  • 20 points = one free analysis 🎯\n━━━━━━━━━━━━━━━━━━━━━━\n🔗 *Your link:*\n`{link}`")
        elif count >= 25:
            tier_line = "🥇 *مستوى ذهبي* — عمولة 15%"
        elif count >= 10:
            tier_line = "🥈 *مستوى فضي* — عمولة 5% → 15 إحالة للذهب"
        else:
            tier_line = "🥉 *مستوى برونزي* — عمولة 5%"

        if lg != "en":
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
                [InlineKeyboardButton(_t(lg, "🌐 استبدل النقاط من الداشبورد", "🌐 Redeem points in the dashboard"), web_app=WebAppInfo(url=f"{FRONTEND_URL}/dashboard"))],
                [InlineKeyboardButton(_t(lg, "📊 تفاصيل البرنامج", "📊 Program details"), web_app=WebAppInfo(url=f"{FRONTEND_URL}/referral")),
                 back_btn(lg)],
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
            (f"⚙️ *الإعدادات*\n"
             f"━━━━━━━━━━━━━━━━━━━━━━\n"
             f"🔔 الإشعارات:          *{'مفعّل' if notif else 'موقف'}*\n"
             f"⏱ الإطار الزمني:      *{TF_LABELS.get(tf,tf)}*\n"
             f"🎯 الحد الأدنى للثقة: *{conf}%*\n") if lg != "en" else
            (f"⚙️ *Settings*\n━━━━━━━━━━━━━━━━━━━━━━\n"
             f"🔔 Notifications:   *{'on' if notif else 'off'}*\n"
             f"⏱ Timeframe:       *{tf_label(tf, 'en')}*\n"
             f"🎯 Min confidence: *{conf}%*\n"),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_t(lg, "🔔 تبديل الإشعارات", "🔔 Toggle notifications"), callback_data="cfg_notif")],
                [InlineKeyboardButton(_t(lg, "⏱ تغيير الإطار الزمني", "⏱ Change timeframe"), callback_data="cfg_tf")],
                [InlineKeyboardButton(_t(lg, "🎯 تغيير الحد الأدنى", "🎯 Change minimum"), callback_data="cfg_conf")],
                [back_btn(lg)],
            ]),
        )
        return

    if d == "cfg_notif":
        _wl_notif[uid] = not _wl_notif.get(uid, True)
        await _save_wl_to_db(uid, tgid)
        await q.answer(_t(lg, f"الإشعارات: {'مفعّل 🔔' if _wl_notif[uid] else 'موقف 🔕'}", f"Notifications: {'on 🔔' if _wl_notif[uid] else 'off 🔕'}"))
        await on_button(update, context)  # re-render settings
        return

    if d == "cfg_tf":
        await q.edit_message_text(_t(lg, "⏱ *اختر الإطار الزمني الافتراضي:*", "⏱ *Choose the default timeframe:*"),
                                   parse_mode="Markdown",
                                   reply_markup=kb_tf_select(back="m_settings", lg=lg))
        return

    if d == "cfg_conf":
        await q.edit_message_text(
            _t(lg, "🎯 *اختر الحد الأدنى للثقة:*\n(أعلى = إشارات أقل لكن أقوى)", "🎯 *Choose the minimum confidence:*\n(higher = fewer but stronger signals)"),
            parse_mode="Markdown", reply_markup=kb_conf_select(lg),
        )
        return

    # ─────────────────────── HELP ─────────────────────────────────────────────
    if d == "m_help":
        await q.edit_message_text(
            HELP_EN if lg == "en" else (
            "📚 *المساعدة*\n\n"
            "📊 *تحليل فوري*\nاختر الفئة ثم الزوج والإطار الزمني.\n\n"
            "👁 *المراقبة*\nاختر الأزواج التي تريد مراقبتها.\n"
            "البوت يحللها كل 15 دقيقة تلقائياً.\n\n"
            "📡 *الإشارات*\nآخر الإشارات المنشورة من الأدمن.\n\n"
            "📈 *إحصائياتي*\nعرض نسبة ربحك ومجموع نقاطك.\n\n"
            "🎁 *الإحالة*\nرابطك الخاص + تفاصيل العمولة."),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(_t(lg, "🌐 فتح المنصة", "🌐 Open platform"), web_app=WebAppInfo(url=FRONTEND_URL))],
                [back_btn(lg)],
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
                # (2026-10-12) تفضيلات كل مشترك من مصدر واحد (/active-subscribers).
                # قبلها: فلتر الأزواج من /all-watchlists التي تستبعد من أطفأ
                # الإشعارات ومن لم يؤكّد بريده — فكان هؤلاء يُعاملون كـ"بلا تخصيص"
                # ويستلمون كل الإشارات، عكس اختيارهم تماماً.
                # المستخدمون بدون watchlist يستلمون كل الإشارات (لم يضبطوا تفضيلاتهم بعد)
                # full_access: أدمن/مشترك فعلي — full لدايماً. الباقي (تجربة نشطة أو
                # منتهية) يستمرون بالاستلام لكن بنسخة مموّهة بعد حصتهم اليومية
                # المجانية (2026-08-21 — قرار: لا نقطع الإشعارات نهائياً عن التجربة
                # المنتهية، القفل يكون على التفاصيل فقط).
                subs_data      = await _get("/api/v1/bot/active-subscribers")
                subs_list      = subs_data.get("subscribers", [])
                full_access_of = {str(s["telegram_id"]): bool(s.get("full_access")) for s in subs_list}
                lang_of        = {str(s["telegram_id"]): (s.get("lang") or "ar") for s in subs_list}
                _user_lang.update(lang_of)
                muted          = {str(s["telegram_id"]) for s in subs_list if s.get("notifications_enabled") is False}
                user_wl: dict[str, set] = {
                    str(s["telegram_id"]): set(s.get("watchlist") or [])
                    for s in subs_list if s.get("watchlist")
                }
                all_subs       = [t for t in full_access_of if t not in muted]
                # (2026-10-12) الفريمات وحد الثقة — كانا محفوظين ولا يُطبَّقان إطلاقاً.
                # فارغ أو 'all' = كل الفريمات؛ 0 = كل النسب. القيم التلقائية القديمة
                # (ساعة/65%) صُفّرت بـmigrate_reset_default_prefs.py قبل التطبيق.
                _TF_ALIAS = {"1day": "1d"}
                user_tfs: dict[str, set] = {}
                user_conf: dict[str, float] = {}
                for s in subs_list:
                    tfs = {_TF_ALIAS.get(t, t) for t in (s.get("timeframes") or []) if t != "all"}
                    if tfs:
                        user_tfs[str(s["telegram_id"])] = tfs
                    mc = float(s.get("min_confidence") or 0)
                    if mc > 0:
                        user_conf[str(s["telegram_id"])] = mc

                logger.info(f"📡 {len(sigs)} إشارة جديدة → {len(all_subs)} مشترك ({len(user_wl)} لديهم watchlist، {len(muted)} أطفؤوا الإشعارات)")

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

                    # (2026-10-19) تصميم موحّد (messages.py): المموّهة بلا اتجاه ولا ثقة ولا مستويات، وزر لفتح
                    # الإشارة نفسها بالحساب (/dashboard?signal=ID — الربط موجود بـDashboard.jsx منذ 28/09).
                    _mname = MARKET_NAMES.get(sig.get("market", ""), sig.get("market", ""))
                    _tfl   = TF_LABELS.get(sig.get("timeframe", ""), sig.get("timeframe", ""))
                    msg_full   = M.signal_full(sig, _mname, _tfl, get_confidence(sig))
                    msg_masked = M.signal_masked(sig, _mname, _tfl)
                    kb_full    = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📱 عرض في حسابي", url=f"{FRONTEND_URL}/dashboard?signal={sig['id']}")],
                        [
                            InlineKeyboardButton("📊 تحليل هذا الزوج", callback_data=f"sym_{sig['market']}"),
                            InlineKeyboardButton("📡 كل الإشارات",     callback_data="m_signals"),
                        ],
                        # (2026-10-12) تخصيص بضغطة من الإشارة نفسها
                        [
                            InlineKeyboardButton(f"🔕 أوقف إشارات {sig['market']}", callback_data=f"mute_{sig['market']}"),
                            InlineKeyboardButton("⚙️ تخصيص", url=SETTINGS_URL),
                        ],
                        [ch_btn()],
                    ])
                    kb_masked  = InlineKeyboardMarkup([[
                        InlineKeyboardButton("💳 فعّل اشتراكك", url=f"{FRONTEND_URL}/pricing"),
                        ch_btn(),
                    ]])
                    await post_channel_teaser(app, sig, msg_masked)
                    # (2026-10-24) النسخة الإنجليزية لمن اختار الإنجليزية بحسابه — اسم السوق = الرمز
                    msg_full_en   = ME.signal_full(sig, sig.get("market", ""), sig.get("timeframe", ""), get_confidence(sig))
                    msg_masked_en = ME.signal_masked(sig, sig.get("market", ""), sig.get("timeframe", ""))
                    kb_full_en = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📱 View in my account", url=f"{FRONTEND_URL}/dashboard?signal={sig['id']}")],
                        [InlineKeyboardButton("📊 Analyze this pair", callback_data=f"sym_{sig['market']}"),
                         InlineKeyboardButton("📡 All signals", callback_data="m_signals")],
                        [InlineKeyboardButton(f"🔕 Mute {sig['market']}", callback_data=f"mute_{sig['market']}"),
                         InlineKeyboardButton("⚙️ Customize", url=SETTINGS_URL)],
                        [ch_btn("en")],
                    ])
                    kb_masked_en = InlineKeyboardMarkup([[
                        InlineKeyboardButton("💳 Activate subscription", url=f"{FRONTEND_URL}/pricing"), ch_btn("en"),
                    ]])
                    # (2026-08-31) إشارات المراقبة الشخصية (monitor_watchlists)
                    # محفوظة بـuser_id صاحبها، وهو أصلاً استلم تنبيه شخصي عنها
                    # لحاله. نستثنيه هون عشان ما توصله نفس الفرصة مرتين —
                    # تنبيه شخصي + بث عام لنفس الصفقة بالضبط.
                    owner_tid = str(sig.get("owner_telegram_id") or "")
                    # (2026-10-12) كل من عنده صف مراقبة شخصية مفتوح لنفس الصفقة، لا صاحب صف واحد
                    owner_tids = {str(t) for t in (sig.get("owner_telegram_ids") or [])}

                    sent = 0
                    # (2026-09-16) سجل التسليم: كان البث يزيد عدّاداً محلياً
                    # فقط بلا أي أثر دائم لمن استلم — فبدت الإشارة وكأنها
                    # وصلت لشخص واحد بلوحة الإدارة (وهي تعدّ صفوف Signal)
                    # بينما البث الحقيقي ~60 مشتركاً. نجمع هنا ونرسل دفعة
                    # واحدة بعد الحلقة، ونسجّل الفشل أيضاً لأنه يكشف من
                    # حظر البوت أو صار chat_id لديه غير صالح.
                    deliveries = []
                    for tid in all_subs:
                        # مستخدم بدون watchlist → يستلم كل شيء
                        # مستخدم بـ watchlist → يستلم فقط أزواجه
                        if tid in user_wl and market not in user_wl[tid]:
                            continue
                        if tid in user_tfs and sig_tf not in user_tfs[tid]:
                            continue
                        if tid in user_conf and float(sig.get("ai_confidence") or 0) < user_conf[tid]:
                            continue
                        if (owner_tid and tid == owner_tid) or tid in owner_tids:
                            continue

                        # full_access (أدمن/مشترك فعلي) → دايماً كاملة، بدون استهلاك حصة.
                        # غيرهم (تجربة نشطة أو منتهية) → نستهلك من حصتهم اليومية
                        # المجانية عبر الباكيند؛ لو خلصت الحصة يستلمون النسخة المموّهة
                        # بدل ما ينقطع عنهم البث بالكامل.
                        unlocked = full_access_of.get(tid, False)
                        if not unlocked:
                            consume  = await _post("/api/v1/bot/consume-signal-notification",
                                                   json={"telegram_id": tid, "signal_id": sig.get("id")})
                            unlocked = bool(consume.get("unlocked"))

                        if lang_of.get(tid) == "en":
                            msg = msg_full_en if unlocked else msg_masked_en
                            kb  = kb_full_en  if unlocked else kb_masked_en
                        else:
                            msg = msg_full if unlocked else msg_masked
                            kb  = kb_full  if unlocked else kb_masked
                        variant = "full" if unlocked else "masked"
                        try:
                            await app.bot.send_message(
                                chat_id=int(tid), text=msg,
                                parse_mode="HTML", reply_markup=kb,
                            )
                            sent += 1
                            deliveries.append({"telegram_id": tid, "ok": True,
                                               "variant": variant})
                        except Exception as _e:
                            logger.warning(f"فشل إرسال إلى {tid}: {_e}")
                            deliveries.append({"telegram_id": tid, "ok": False,
                                               "variant": variant, "error": str(_e)})
                        await asyncio.sleep(0.05)  # rate limit

                    await _post(f"/api/v1/bot/mark-broadcast/{sig['id']}")
                    if deliveries:
                        try:
                            await _post(f"/api/v1/bot/record-deliveries/{sig['id']}",
                                        json={"deliveries": deliveries})
                        except Exception as _re:
                            logger.warning(f"تعذّر حفظ سجل التسليم لـ#{sig['id']}: {_re}")
                    failed = len(deliveries) - sent
                    logger.info(
                        f"✅ إشارة #{sig['id']} [{market}] بُثّت لـ {sent} مشترك"
                        + (f" (فشل {failed})" if failed else "")
                    )

        except Exception as e:
            logger.error(f"broadcast_new_signals: {e}", exc_info=True)

        await asyncio.sleep(BROADCAST_INTERVAL)


# ─── Background: Outcome checker ──────────────────────────────────────────────
# (2026-09-10) بلاغ حقيقي: حالة الإشارة كانت تتحدث لـTP/SL كل 15 دقيقة فقط
# (كانت مدمجة بحلقة monitor_watchlists)، فتبقى ACTIVE دقايق طويلة بعد ما
# ضربت المستوى فعلياً. حلقة مخصصة كل 90ث: فحص السعر اللحظي (رخيص، مكاش 30ث)
# لرصد شبه فوري، + فحص المدى الكامل (wicks) كل ~9 دورات (~13.5 دقيقة).
OUTCOME_CHECK_INTERVAL = 90    # ثانية
_DEEP_EVERY = 9               # كل كام دورة نعمل range_check كامل (~13.5 دقيقة)

async def outcome_checker(app: Application):
    logger.info("🎯 بدء حلقة رصد نتائج الإشارات (كل 90ث)…")
    await asyncio.sleep(35)
    _cycle = 0
    while True:
        try:
            _cycle += 1
            deep = (_cycle % _DEEP_EVERY == 1)   # أول دورة + كل 9 دورات
            outcomes = (await _get(
                "/api/v1/bot/check-outcomes",
                params={"range_check": "true" if deep else "false"},
                timeout=45,
            )).get("triggered", [])

            sent_result_ids: set = set()
            for o in outcomes:
                try:
                    # (2026-10-19) جمهوران: المشترك (نتيجة + زر للصفقة بحسابه)، والمنتهي اشتراكه (audience=expired —
                    # الرابحة مفصّلة مع دعوة للاشتراك، الخاسرة مختصرة؛ كل النتائج تصل ولا تُخفى خسارة).
                    _lg = o.get("lang") or "ar"
                    if o.get("telegram_id"):
                        _user_lang[str(o["telegram_id"])] = _lg
                    _mname = o.get("market", "") if _lg == "en" else MARKET_NAMES.get(o.get("market", ""), o.get("market", ""))
                    if _lg == "en":
                        if o.get("audience") == "expired":
                            _txt = ME.outcome_expired(o, _mname)
                            _kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Renew subscription", url=f"{FRONTEND_URL}/pricing"), ch_btn("en")]]) \
                                if o.get("status") in ("TP1_HIT", "TP2_HIT", "TP3_HIT") else InlineKeyboardMarkup([[ch_btn("en")]])
                        else:
                            _txt = ME.outcome_subscriber(o, _mname)
                            _kb = InlineKeyboardMarkup([
                                [InlineKeyboardButton("📱 View in my account", url=f"{FRONTEND_URL}/dashboard?signal={o.get('signal_id')}")],
                                [InlineKeyboardButton("📈 My stats", callback_data="m_stats"),
                                 InlineKeyboardButton("📡 Signals", callback_data="m_signals")],
                                [ch_btn("en")],
                            ])
                    elif o.get("audience") == "expired":
                        _txt = M.outcome_expired(o, _mname)
                        _kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 جدّد اشتراكك", url=f"{FRONTEND_URL}/pricing"), ch_btn()]]) \
                            if o.get("status") in ("TP1_HIT", "TP2_HIT", "TP3_HIT") else InlineKeyboardMarkup([[ch_btn()]])
                    else:
                        _txt = M.outcome_subscriber(o, _mname)
                        _kb = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📱 عرض في حسابي", url=f"{FRONTEND_URL}/dashboard?signal={o.get('signal_id')}")],
                            [InlineKeyboardButton("📈 إحصائياتي", callback_data="m_stats"),
                             InlineKeyboardButton("📡 الإشارات",  callback_data="m_signals")],
                            [ch_btn()],
                        ])
                    await app.bot.send_message(
                        chat_id=int(o["telegram_id"]),
                        text=_txt,
                        parse_mode="HTML",
                        reply_markup=_kb,
                    )
                    sent_result_ids.add(o.get("signal_id"))
                    await asyncio.sleep(0.05)
                except Exception as _e:
                    logger.warning(f"outcome send error: {_e}")

            for sid in sent_result_ids:
                if sid:
                    try:
                        await _post(f"/api/v1/bot/mark-result-broadcast/{sid}")
                    except Exception:
                        pass

            if outcomes:
                logger.info(f"🎯 رصد {len(outcomes)} نتيجة (deep={deep})")
        except Exception as e:
            logger.error(f"outcome_checker: {e}", exc_info=True)
        await asyncio.sleep(OUTCOME_CHECK_INTERVAL)


# ─── Background: Breakeven alerts ─────────────────────────────────────────────
# (2026-10-11) تنبيه "حرّك الستوب للدخول" حين تبلغ صفقة مفتوحة ربحاً يساوي
# مخاطرتها (+1R). الباك إند يحدد الصفقات والمستلمين ويعلّمها مرة واحدة — هنا
# الإرسال فقط. اقتراح إدارة مخاطر لا أمر؛ النتيجة المقاسة لا تتغيّر.
BREAKEVEN_CHECK_INTERVAL = 300   # ثانية

def fmt_breakeven(a: dict, lg: str = "ar") -> str:
    if lg == "en":
        side = "BUY 🟢" if a.get("signal_type") == "BUY" else "SELL 🔴"
        return (f"🛡️ *Protect your trade — {a.get('market')}*\n"
                f"{side} trade ({a.get('timeframe')}) reached a profit equal to its risk (+1R).\n\n"
                f"💡 Consider moving your stop loss to entry `{a.get('entry')}` — you lose nothing if price reverses, "
                f"and the trade stays open toward the target `{a.get('tp1')}`.\n\n_A risk-management suggestion; the decision is yours._")
    side = "شراء 🟢" if a.get("signal_type") == "BUY" else "بيع 🔴"
    return (
        f"🛡️ *حماية صفقة — {a.get('market')}*\n"
        f"صفقة {side} ({a.get('timeframe')}) وصلت لربح يساوي مخاطرتها (+1R).\n\n"
        f"💡 يُنصح بنقل وقف الخسارة إلى سعر الدخول `{a.get('entry')}` — "
        f"هكذا لا تخسر شيئاً لو انعكس السعر، وتبقى الصفقة مفتوحة نحو الهدف `{a.get('tp1')}`.\n\n"
        f"_اقتراح لإدارة المخاطر، والقرار لك._"
    )

async def breakeven_alerts(app: Application):
    logger.info("🛡️ بدء حلقة تنبيهات حماية الصفقات (كل 5 دقائق)…")
    await asyncio.sleep(50)
    while True:
        try:
            alerts = (await _get("/api/v1/bot/breakeven-alerts", timeout=60)).get("alerts", [])
            for a in alerts:
                try:
                    await app.bot.send_message(
                        chat_id=int(a["telegram_id"]),
                        text=fmt_breakeven(a, _user_lang.get(str(a["telegram_id"]), "ar")),
                        parse_mode="Markdown",
                    )
                    await asyncio.sleep(0.05)
                except Exception as _e:
                    logger.warning(f"breakeven send error: {_e}")
            if alerts:
                logger.info(f"🛡️ أُرسل {len(alerts)} تنبيه حماية")
        except Exception as e:
            logger.error(f"breakeven_alerts: {e}", exc_info=True)
        await asyncio.sleep(BREAKEVEN_CHECK_INTERVAL)


# ─── Background: Daily challenge (quiz) ───────────────────────────────────────
# (2026-10-11) سؤال تعليمي واحد كل يوم 06:00 UTC (09:00 مكة) كاختبار Quiz
# تيليجرام، نفسه للكل. الإجابة تُصحَّح على الخادم وتُضاف لنقاط الألعاب ولوحة
# المتصدّرين، مع سلسلة أيام متتالية — سبب يومي للرجوع للمنصة.
_DAILY_CHALLENGE_DATE = None
_POLL_CHALLENGE: dict[str, str] = {}   # poll_id → challenge_id (لضياعها بعد إعادة تشغيل: التاريخ الحالي)
GAMES_URL = f"{FRONTEND_URL}/games/challenge"

async def daily_challenge(app: Application):
    global _DAILY_CHALLENGE_DATE
    logger.info("🎯 بدء مهمة التحدّي اليومي…")
    await asyncio.sleep(70)
    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            if now.hour == 6 and now.minute < 5 and _DAILY_CHALLENGE_DATE != today:
                _DAILY_CHALLENGE_DATE = today
                q = await _get("/api/v1/bot/daily-challenge")
                if q and q.get("options"):
                    subs = (await _get("/api/v1/bot/active-subscribers")).get("subscribers", [])
                    sent = 0
                    for s in subs:
                        tid = s.get("telegram_id")
                        if not tid or s.get("notifications_enabled") is False:
                            continue
                        if (s.get("lang") or "ar") == "en":   # (2026-10-24) أسئلة التحدّي عربية — لا نرسلها لمن اختار الإنجليزية
                            continue
                        try:
                            msg = await app.bot.send_poll(
                                chat_id=int(tid),
                                question=("🎯 تحدّي كفيل اليومي\n" + q["question"])[:300],
                                options=q["options"],
                                type=Poll.QUIZ,
                                correct_option_id=q["correct"],
                                explanation=q.get("explanation", "")[:200],
                                is_anonymous=False,
                            )
                            if msg.poll:
                                _POLL_CHALLENGE[msg.poll.id] = q["id"]
                            sent += 1
                            await asyncio.sleep(0.05)
                        except Exception:
                            pass
                    logger.info(f"🎯 تحدّي اليوم ({q['id']}) → {sent} مشترك")
                    if len(_POLL_CHALLENGE) > 20000:   # لا تكبر الذاكرة بلا حد
                        _POLL_CHALLENGE.clear()
        except Exception as e:
            logger.error(f"daily_challenge: {e}")
        await asyncio.sleep(60)

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/settings — (2026-10-12) تخصيص الإشارات: الأزواج والفريمات وحد الثقة."""
    await ensure_lang(update.effective_user)
    if lang_for(update.effective_user) == "en":
        await update.message.reply_text(
            "⚙️ *Customize the signals you receive*\n\n"
            "• Pick only the pairs you trade\n"
            "• Choose timeframes: 15 min, 1 hour, 4 hours\n"
            "• Set a minimum signal confidence\n"
            "• Or pause notifications\n\n"
            "You can also mute any pair straight from the 🔕 button under a signal.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Open settings", url=SETTINGS_URL)]]),
        )
        return
    await update.message.reply_text(
        "⚙️ *خصّص الإشارات التي تصلك*\n\n"
        "• اختر الأزواج التي تتداولها فقط\n"
        "• اختر الفريمات: 15 دقيقة، ساعة، 4 ساعات\n"
        "• حدّد أقل نسبة ثقة للإشارة\n"
        "• أو أوقف الإشعارات مؤقتاً\n\n"
        "وتقدر توقف أي زوج مباشرة من زر 🔕 تحت الإشارة.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ فتح الإعدادات", url=SETTINGS_URL)]]),
    )

async def cmd_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/challenge — تحدّي اليوم عند الطلب (نفس سؤال الإرسال الصباحي)."""
    await ensure_lang(update.effective_user)
    if lang_for(update.effective_user) == "en":
        await update.message.reply_text("🎯 The daily challenge is available in Arabic only for now.\n"
                                        "Try the learning games on the platform instead 👇\n" + GAMES_URL)
        return
    q = await _get("/api/v1/bot/daily-challenge")
    if not q or not q.get("options"):
        await update.message.reply_text("تعذّر جلب تحدّي اليوم، جرّب بعد قليل.")
        return
    msg = await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=("🎯 تحدّي كفيل اليومي\n" + q["question"])[:300],
        options=q["options"], type=Poll.QUIZ, correct_option_id=q["correct"],
        explanation=q.get("explanation", "")[:200], is_anonymous=False,
    )
    if msg.poll:
        _POLL_CHALLENGE[msg.poll.id] = q["id"]

async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pa = update.poll_answer
    if not pa or not pa.option_ids:
        return
    cid = _POLL_CHALLENGE.get(pa.poll_id) or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        r = await _post("/api/v1/bot/daily-challenge/answer",
                        json={"telegram_id": str(pa.user.id), "challenge_id": cid, "option": pa.option_ids[0]})
    except Exception as e:
        logger.warning(f"daily answer: {e}")
        return
    if not r or not r.get("ok") or r.get("already"):
        return
    if not r.get("linked"):
        text = ("✅ إجابة صحيحة!" if r.get("correct") else "❌ ليست الإجابة الصحيحة هذه المرة.") + \
               f"\n\nاربط حسابك في كفيل لتُحفظ نقاطك وتدخل لوحة المتصدّرين 👇\n{GAMES_URL}"
    else:
        streak = r.get("streak", 1)
        fire = f"🔥 سلسلتك: {streak} " + ("يوم" if streak == 1 else "أيام")
        if r.get("correct"):
            text = f"✅ إجابة صحيحة! +{r.get('awarded', 0)} نقطة\n{fire}\n\n🏆 ترتيبك في متصدّري الأسبوع والمزيد من التحديات:\n{GAMES_URL}"
        else:
            text = f"❌ ليست الصحيحة، لكن سلسلتك مستمرة.\n{fire}\n\n🎮 درّب نفسك أكثر:\n{GAMES_URL}"
    try:
        await context.bot.send_message(chat_id=pa.user.id, text=text, disable_web_page_preview=True)
    except Exception:
        pass


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

            # ── 1. نتائج الإشارات (TP/SL) — نُقلت لحلقة outcome_checker
            #      المخصصة (كل ~90ث بدل 15 دقيقة) لرصد شبه فوري. (2026-09-10)

            # ── 2. مراقبة الأزواج
            # المصدر الوحيد للـ Watchlist هو DB — لا merge مع الذاكرة المحلية
            db_users = (await _get("/api/v1/bot/all-watchlists")).get("users", [])
            merged: dict[int, tuple[set, str, int, bool]] = {}
            for u in db_users:
                try:
                    tid = int(u["telegram_id"])
                    wl  = set(s.upper() for s in u.get("watchlist", [])) & _VALID_SYMBOLS
                    if wl:
                        merged[tid] = (wl, u.get("timeframe","1h"), u.get("min_confidence",65), bool(u.get("full_access")))
                except Exception:
                    pass

            logger.info(f"🔍 دورة مراقبة — {len(merged)} مستخدم (من DB)")

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
            for wl, _, _, _ in merged.values():
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

            logger.info(f"🔍 حُلّل {len(symbol_results)} رمز فريد (بدل {sum(len(wl) for wl,_,_,_ in merged.values())} طلب لو كل مستخدم لحاله)")

            for uid_, (watchlist, _stored_tf_pref, min_conf, full_access) in merged.items():
                for symbol in list(watchlist):
                    tf_results = symbol_results.get(symbol) or {}
                    if not tf_results:
                        continue  # سوق مغلق أو فشل التحليل — تعامل معه فوق مرة وحدة

                    for tf, data in tf_results.items():
                        rec  = data.get("recommendation", "WATCH")
                        conf = get_confidence(data)
                        if rec not in ("BUY", "SELL") or conf < min_conf:
                            continue

                        # (2026-08-31) بدل القفل الزمني الثابت (كان يعيد نفس
                        # التنبيه كل 30 دقيقة طول ما الصفقة قايمة، حتى لو
                        # ما تغيّر فيها شي): نحاول حفظ الإشارة بقاعدة
                        # البيانات أولاً. save-alert-signal يتحقق الآن على
                        # مستوى المستخدم: هل عند هالمستخدم بالذات صفقة نشطة
                        # لسا صالحة (ما انقفلت SL/TP ولا انتهت) بنفس
                        # الرمز/الفريم؟ لو نعم، نتخطى — تنبيه واحد لكل صفقة
                        # حقيقية طول ما هي مفتوحة، مو تكرار زمني. لما تُغلق
                        # أو تنتهي، أول فحص بعدها بيقدر يبعت تنبيه جديد —
                        # بما فيه انعكاس الاتجاه، بدون حاجة لقفل ساعتين منفصل.
                        levels = data.get("levels", {})
                        _ez    = data.get("entry_zones") or []
                        _tz    = data.get("take_profit_zones") or []
                        _entry = levels.get("entry") or (_ez[0] if _ez else None)
                        _sl    = levels.get("stop_loss") or data.get("stop_loss_zone")
                        _tp1   = levels.get("tp1") or (_tz[0] if _tz else None)
                        _tp2   = levels.get("tp2") or (_tz[1] if len(_tz) > 1 else _tp1)
                        _rr    = data.get("risk_reward_ratio") or levels.get("risk_reward") or 0

                        if not (_entry and _sl and _tp1):
                            continue  # ما فيه مستويات كاملة — ما نقدر نتحقق أو نتتبّع الصفقة

                        try:
                            save_res = await _post("/api/v1/bot/save-alert-signal", params={
                                "telegram_id": str(uid_),
                                "symbol":      symbol,
                                "timeframe":   tf,
                                "signal_type": rec,
                                "entry":       _entry,
                                "sl":          _sl,
                                "tp1":         _tp1,
                                "tp2":         _tp2 or _tp1,
                                **({"tp3": levels["ladder_tp3"]} if levels.get("ladder_tp3") else {}),   # (2026-10-30) سلّم الأهداف
                                "confidence":  conf,
                                "rr":          _rr,
                                # (2026-10-24) وسم التخفيف الجزئي — يُحفظ بالصف للقياس وقاعدة الرجوع
                                **({"relaxed_rule": data["relaxed_rule"]} if data.get("relaxed_rule") else {}),
                                # (2026-10-16) سياق ICT لتقرير الجودة — كان يُحفظ بمسار الماسح فقط (تغطية 26%)
                                **{k: v for k, v in (
                                    ("wyckoff_phase", (data.get("wyckoff") or {}).get("phase") if isinstance(data.get("wyckoff"), dict) else data.get("wyckoff")),
                                    ("premium_discount", (data.get("premium_discount") or {}).get("zone") if isinstance(data.get("premium_discount"), dict) else data.get("premium_discount")),
                                    ("killzone", (data.get("kill_zone") or {}).get("active_session") if isinstance(data.get("kill_zone"), dict) else data.get("kill_zone")),
                                ) if v},
                            })
                        except Exception as _save_e:
                            logger.warning(f"save-alert-signal: {_save_e}")
                            continue

                        if not save_res.get("saved"):
                            logger.debug(f"🔕 watch alert skip [{uid_}/{symbol}/{tf}] {save_res.get('reason')}")
                            continue

                        emoji  = "🟢" if rec == "BUY" else "🔴"
                        rec_ar = "شراء" if rec == "BUY" else "بيع"

                        # (2026-09-27) استطلاع الميزات: تحذير صفقات مرتبطة (نفس
                        # الرمز) — 10 أصوات. concurrent_same_symbol من
                        # save-alert-signal فوق (فحص server-side، لا حساب هون).
                        concurrent_n = save_res.get("concurrent_same_symbol", 0)
                        concurrent_line = (
                            f"⚠️ *عندك {concurrent_n} صفقة أخرى مفتوحة بنفس الرمز* "
                            f"({MARKET_NAMES.get(symbol,symbol)}) — انتبه لتركّز المخاطرة.\n\n"
                            if concurrent_n else ""
                        )

                        # full_access (أدمن/مشترك فعلي) → دايماً كاملة. غيرهم (تجربة
                        # نشطة أو منتهية) → نستهلك من حصتهم اليومية المجانية؛ لو
                        # خلصت، تنبيه مموّه بدل قطع المراقبة الشخصية بالكامل عنهم.
                        unlocked = full_access
                        if not unlocked:
                            consume  = await _post("/api/v1/bot/consume-signal-notification",
                                                   json={"telegram_id": str(uid_), "signal_id": save_res.get("signal_id")})
                            unlocked = bool(consume.get("unlocked"))

                        _wlg = _user_lang.get(str(uid_), "ar")
                        if _wlg == "en":
                            _cl = (f"⚠️ *You have {concurrent_n} other open trade(s) on this symbol* ({symbol}) — watch your risk concentration.\n\n"
                                   if concurrent_n else "")
                            if unlocked:
                                alert = (f"🚨 *Watchlist alert!*\n\n{emoji} *{rec}* — {symbol} ({tf})\n"
                                         f"📊 Confidence: *{conf:.1f}%*\n\n{_cl}{fmt_analysis_en(data, symbol, tf)}")[:4000]
                                kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data=f"an_{symbol}_{tf}"),
                                                            InlineKeyboardButton("🏠 Home", callback_data="m_back")]])
                            else:
                                alert = (f"🚨 *Watchlist alert!*\n\n{emoji} *{rec}* — {symbol} ({tf})\n"
                                         f"📊 Confidence: *{conf:.1f}%*\n\n{_cl}"
                                         f"🔒 You've used today's free quota — entry/stop/targets are locked\n"
                                         f"💳 Subscribe to see full details")
                                kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Subscribe now", url=f"{FRONTEND_URL}/pricing")]])
                        elif unlocked:
                            alert = (
                                f"🚨 *تنبيه مراقبة!*\n\n"
                                f"{emoji} *{rec_ar}* — {MARKET_NAMES.get(symbol,symbol)} ({tf})\n"
                                f"📊 الثقة: *{conf:.1f}%*\n\n"
                                f"{concurrent_line}"
                                f"{fmt_analysis(data, symbol, tf)}"
                            )[:4000]
                            kb = InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔄 تحديث", callback_data=f"an_{symbol}_{tf}"),
                                InlineKeyboardButton("🏠 رئيسية", callback_data="m_back"),
                            ]])
                        else:
                            alert = (
                                f"🚨 *تنبيه مراقبة!*\n\n"
                                f"{emoji} *{rec_ar}* — {MARKET_NAMES.get(symbol,symbol)} ({tf})\n"
                                f"📊 الثقة: *{conf:.1f}%*\n\n"
                                f"{concurrent_line}"
                                f"🔒 استهلكت حصتك المجانية اليوم — تفاصيل الدخول/الوقف/الأهداف مقفلة\n"
                                f"💳 اشترك لرؤية التفاصيل الكاملة"
                            )
                            kb = InlineKeyboardMarkup([[
                                InlineKeyboardButton("💳 اشترك الآن", url=f"{FRONTEND_URL}/pricing"),
                            ]])

                        try:
                            await app.bot.send_message(
                                chat_id=uid_, text=alert, parse_mode="Markdown",
                                reply_markup=kb,
                            )
                            logger.info(f"📨 تنبيه → {uid_} | {symbol}/{tf} | {rec} | {conf:.1f}% | unlocked={unlocked}")
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
                _elg = _user_lang.get(str(tid), "ar")
                msg = ((f"⏰ *Your subscription has ended!*\n\nHi {name} 👋\nYour plan has ended.\n\nRenew now to continue 📊"
                        if days == 0 else
                        f"⚠️ *Your subscription ends soon!*\n\nHi {name} 👋\n"
                        f"Your plan ends in *{days} day{'s' if days != 1 else ''}*.\n\nRenew now 🚀")
                       if _elg == "en" else None) or (
                    f"⏰ *انتهى اشتراكك!*\n\nمرحباً {name} 👋\nانتهت باقتك {plan}.\n\nجدد الآن للاستمرار 📊"
                    if days == 0 else
                    f"⚠️ *اشتراكك ينتهي قريباً!*\n\nمرحباً {name} 👋\n"
                    f"باقتك {plan} ستنتهي خلال *{days} {'يوم' if days==1 else 'أيام'}*.\n\nجدد الآن 🚀"
                )
                try:
                    await app.bot.send_message(
                        chat_id=int(tid), text=msg, parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("💳 Renew subscription" if _elg == "en" else "💳 تجديد الاشتراك", url=f"{FRONTEND_URL}/pricing")
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


_CLOSE_MSG_EN = """🔔 *Forex & gold markets closed*

Forex, metals and indices markets are now closed for the weekend.

We hope you had a good week 🌟
*Thank you for your trust — see you next week* 🙏

_Crypto markets remain open 24/7_ ₿"""

_OPEN_MSG_EN = """🌅 *Forex & gold markets open*

Forex, metals and indices markets are open for the new week 📈

_Good luck everyone — trade wisely and with discipline_ 💪✨"""


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
                        _m = (_OPEN_MSG_EN if current_open else _CLOSE_MSG_EN) if (s.get("lang") or "ar") == "en" else msg
                        await app.bot.send_message(
                            chat_id=int(tid),
                            text=_m,
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
                        msg_en = (
                            f"⏰ *Session alert | {sess['name_en']}*\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"The session opens in *{mins_left} min* 🔔\n\n"
                            f"📋 *Get ready:*\n"
                            f"• Review the HTF (4H) setup\n"
                            f"• Mark the active OB and FVG zones\n"
                            f"• Don't enter in the first 15 minutes\n\n"
                            f"_Use /menu → Quick analysis for any market_"
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
                                    chat_id=int(tid), text=(msg_en if (s.get("lang") or "ar") == "en" else msg), parse_mode="Markdown"
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
                briefing_en = []
                for sym in ["XAUUSD", "BTCUSD", "EURUSD"]:
                    try:
                        res = await _post(
                            f"/api/v1/bot/analyze?symbol={sym}&timeframe=4h"
                        )
                        d   = res.get("data", {})
                        if not d or d.get("error") or "recommendation" not in d:
                            briefing_lines.append(f"{MARKET_NAMES.get(sym, sym)}: ⚠️ تعذّر التحليل")
                            briefing_en.append(f"{sym}: ⚠️ analysis unavailable")
                            continue

                        rec = d.get("recommendation", "WAIT")
                        conf = get_confidence(d)
                        price = float(d.get("current_price") or 0)
                        rec_ar = {"BUY": "📈 شراء", "SELL": "📉 بيع", "WAIT": "⏳ انتظار"}.get(rec, rec)
                        mname  = MARKET_NAMES.get(sym, sym)
                        briefing_lines.append(
                            f"{mname}: {rec_ar} | ثقة `{conf:.0f}%` | `{_fmt_price(price)}`"
                        )
                        _rec_en = {"BUY": "📈 BUY", "SELL": "📉 SELL", "WAIT": "⏳ WAIT"}.get(rec, rec)
                        briefing_en.append(f"{sym}: {_rec_en} | confidence `{conf:.0f}%` | `{_fmt_price(price)}`")
                    except Exception:
                        briefing_lines.append(f"{MARKET_NAMES.get(sym, sym)}: ⚠️ تعذّر التحليل")
                        briefing_en.append(f"{sym}: ⚠️ analysis unavailable")

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
                msg_en = (
                    f"🌅 *Good morning — daily briefing*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 {now.strftime('%A %d/%m/%Y')}\n\n"
                    f"📊 *4H view of the main markets:*\n"
                    + "\n".join(f"• {l}" for l in briefing_en) +
                    f"\n\n💡 *Tip of the day:*\n"
                    f"_Don't enter without HTF confirmation plus a clear OB or FVG_\n\n"
                    f"_Use /menu to analyze a specific market 🎯_"
                )

                subs_data = await _get("/api/v1/bot/active-subscribers")
                subs = subs_data.get("subscribers", [])
                sent = 0
                for s in subs:
                    tid = s.get("telegram_id")
                    if not tid or s.get("notifications_enabled") is False:   # (2026-10-12) احترام الإيقاف
                        continue
                    try:
                        await app.bot.send_message(
                            chat_id=int(tid), text=(msg_en if (s.get("lang") or "ar") == "en" else msg), parse_mode="Markdown"
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
     "msg_en": "📊 *Warning: NFP — Non-Farm Payrolls*\nOut in one hour — one of the strongest movers for gold and the dollar.\n⚠️ *Don't open new trades now*\nWait 15 minutes after the release before any entry.",
     "msg_ar": "📊 *تحذير: NFP — وظائف غير الزراعية*\nالخبر بعد ساعة — من أقوى الأخبار تأثيراً على الذهب والدولار.\n⚠️ *لا تفتح صفقات جديدة الآن*\nانتظر 15 دقيقة بعد الإعلان قبل أي دخول."},
    # كل أول أربعاء من الشهر — FOMC Minutes أو Fed Rate
    {"type": "FOMC",  "weekday": 2, "utc_hour": 18, "utc_min": 0,
     "msg_en": "🏦 *Warning: US Fed decision (FOMC)*\nThe decision is in one hour — it moves every market strongly.\n⚠️ *Close open trades or tighten your stop*\nVolatility will be very high.",
     "msg_ar": "🏦 *تحذير: قرار الفيدرالي الأمريكي (FOMC)*\nالقرار بعد ساعة — يؤثر بشكل كبير على جميع الأسواق.\n⚠️ *أغلق صفقاتك المفتوحة أو ضيّق الوقف*\nالتقلب سيكون عالياً جداً."},
    # منتصف كل شهر الثلاثاء 12:30 UTC — CPI
    {"type": "CPI",   "weekday": 1, "utc_hour": 12, "utc_min": 30,
     "msg_en": "📈 *Warning: Consumer Price Index (CPI)*\nOut in one hour — a big mover for gold and currencies.\n⚠️ *Watch for stop hunts right before and after the release*",
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
                                text=(ev["msg_en"] if (s.get("lang") or "ar") == "en" else ev["msg_ar"]),
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
# (2026-10-19) من حظر البوت يُستبعد من الإرسال (telegram_reach.py بالباكيند). أي تفاعل منه يعني أنه فكّ الحظر ←
# نبلغ الباكيند فيرجع لقوائم الإرسال فوراً. مرة كل ساعة لكل مستخدم كحد أقصى (لا طلب لكل ضغطة زر).
_seen_sent: dict = {}


async def _mark_telegram_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not u:
        return
    now = datetime.now(timezone.utc)
    last = _seen_sent.get(u.id)
    if last and (now - last).total_seconds() < 3600:
        return
    _seen_sent[u.id] = now
    try:
        await _post("/api/v1/bot/telegram-seen", json={"telegram_id": str(u.id)})
    except Exception as e:
        logger.debug(f"telegram-seen {u.id}: {e}")


# ─────────────────────── آراء العملاء من البوت (2026-10-24) ───────────────────────
_rf = RF.ReviewFlow()
_RV_CANCEL = [InlineKeyboardButton("❌ إلغاء", callback_data="rv_cancel")]


def _kb_rating():
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"{n}⭐", callback_data=f"rv_r_{n}") for n in range(1, 6)],
                                 _RV_CANCEL])


async def on_review_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid, d = q.from_user.id, q.data
    await ensure_lang(q.from_user)
    lg = _rf.lang(uid) if _rf.active(uid) else lang_for(q.from_user)
    _cancel = [InlineKeyboardButton("❌ Cancel" if lg == "en" else "❌ إلغاء", callback_data="rv_cancel")]
    if d == "m_review":
        st = await _get("/api/v1/bot/review-status", {"telegram_id": str(uid)})
        if not st.get("linked"):
            await q.message.reply_text(_t(lg, "🔗 اربط حسابك بالمنصة أولاً لإرسال رأيك.", "🔗 Link your platform account first to send a review."),
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                           _t(lg, "🌐 فتح المنصة", "🌐 Open platform"), web_app=WebAppInfo(url=FRONTEND_URL))]]))
            return
        if not st.get("eligible"):
            if lg == "en":
                why = ("Reviews are open to subscribers 7 days after their first paid plan — so your review reflects real experience."
                       if st.get("reason") == "no_paid" else f"You can send your review in {st.get('days_left')} day(s).")
            else:
                why = ("إرسال الرأي متاح للمشتركين بعد 7 أيام من أول اشتراك مدفوع — حتى يكون رأيك عن تجربة حقيقية."
                       if st.get("reason") == "no_paid" else f"يمكنك إرسال رأيك بعد {st.get('days_left')} يوم من اشتراكك.")
            await q.message.reply_text(f"⏳ {why}")
            return
        _rf.start(uid, lg)
        note = (_t(lg, "\n<i>رأيك السابق سيُستبدل بالجديد بعد المراجعة.</i>", "\n<i>Your previous review will be replaced after review.</i>")
                if st.get("existing") else "")
        await q.message.reply_text(_t(lg, "⭐ <b>كيف تقيّم تجربتك مع Qaffel؟</b>", "⭐ <b>How would you rate your experience with Qaffel?</b>") + note,
                                   parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
                                       [[InlineKeyboardButton(f"{n}⭐", callback_data=f"rv_r_{n}") for n in range(1, 6)], _cancel]))
        return
    if d == "rv_cancel":
        await q.message.reply_text(_rf.cancel(uid))
        return
    if d.startswith("rv_r_"):
        txt = _rf.on_rating(uid, int(d.split("_")[-1]))
        if txt:
            await q.message.reply_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t(lg, "⏭ تخطّي", "⏭ Skip"), callback_data="rv_skip")], _cancel]))
        return
    if d == "rv_skip":
        txt = _rf.on_skip(uid)
        if txt:
            await q.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([_cancel]))
        return
    if d in ("rv_pub_name", "rv_pub_anon"):
        payload = _rf.on_consent(uid, anonymous=(d == "rv_pub_anon"))
        if not payload:
            return
        res = await _post("/api/v1/bot/reviews", json={"telegram_id": str(uid), **payload})
        if res.get("ok"):
            await q.message.reply_text(RF.EN["THANKS"] if lg == "en" else RF.THANKS, parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup([[ch_btn(lg)]]))
        else:
            await q.message.reply_text(f"⚠️ {res.get('error') or _t(lg, 'تعذّر الإرسال — حاول بعد قليل.', 'Could not send — try again shortly.')}")


async def on_review_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نص أو صورة أو فيديو — يُعالج فقط إن كان المستخدم داخل خطوات الرأي؛ غير ذلك يُتجاهل كما كان."""
    msg, uid = update.message, update.effective_user.id if update.effective_user else None
    if not msg or uid is None or not _rf.active(uid):
        return
    step = _rf.step(uid)
    lg = _rf.lang(uid)
    _cancel = [InlineKeyboardButton("❌ Cancel" if lg == "en" else "❌ إلغاء", callback_data="rv_cancel")]
    if step == "media" and (msg.photo or msg.video):
        kind = "photo" if msg.photo else "video"
        fid = msg.photo[-1].file_id if msg.photo else msg.video.file_id
        size = (msg.video.file_size or 0) if msg.video else 0
        ok, txt = _rf.on_media(uid, kind, fid, size)
        await msg.reply_text(txt, parse_mode="HTML",
                             reply_markup=InlineKeyboardMarkup([_cancel]) if ok else None)
        return
    if step == "text" and msg.text:
        ok, txt = _rf.on_text(uid, msg.text)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(_t(lg, "✅ انشره باسمي", "✅ Publish with my name"), callback_data="rv_pub_name"),
                                    InlineKeyboardButton(_t(lg, "🙈 بدون اسمي", "🙈 Without my name"), callback_data="rv_pub_anon")],
                                   _cancel]) if ok else InlineKeyboardMarkup([_cancel])
        await msg.reply_text(txt, parse_mode="HTML", reply_markup=kb)
        return
    hint = ({"rating": "Pick the number of stars from the buttons.", "media": "Send a photo or video, or tap Skip.",
             "text": "Write your review as text.", "consent": "Choose how to publish from the buttons."} if lg == "en" else
            {"rating": "اختر عدد النجوم من الأزرار.", "media": "أرسل صورة أو فيديو، أو اضغط تخطّي.",
             "text": "اكتب رأيك نصاً.", "consent": "اختر طريقة النشر من الأزرار."}).get(step)
    if hint:
        await msg.reply_text(hint)


def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير محدد!")
        return

    logger.info("🤖 Qaffel AI Bot v2 — بدء التشغيل…")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(TypeHandler(Update, _mark_telegram_seen), group=-1)   # قبل كل المعالجات، لا يوقفها
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu",  cmd_menu))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("challenge", cmd_challenge))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(on_review_button, pattern=r"^(m_review|rv_)"))   # قبل المعالج العام
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO | filters.VIDEO,
                                   on_review_message))
    app.add_handler(PollAnswerHandler(on_poll_answer))

    async def post_init(application: Application):
        # (2026-09-23) قائمة أوامر تيليجرام الأصلية (زر "/" جانب حقل الكتابة) —
        # كانت فاضية تماماً رغم وجود /start و/menu فعلياً، فتبدو للمستخدم الجديد
        # كأنه بوت بلا أوامر حقيقية. تحسين واجهة بحت — لا علاقة له بحلقة
        # الرصد/البث المجمَّدة.
        # (2026-10-11) بلاغ: القائمة تُظهر /start فقط. تيليجرام يقدّم قائمة النطاق
        # الأخص (محادثات خاصة / لغة المستخدم) على الافتراضي — فقائمة قديمة بنطاق
        # أخص (من BotFather مثلاً) كانت تحجب هذه. نضبطها صراحة لكل نطاق ولغة.
        from telegram import BotCommandScopeDefault, BotCommandScopeAllPrivateChats
        cmds = [
            BotCommand("start",     "بدء التشغيل وربط الحساب"),
            BotCommand("menu",      "القائمة الرئيسية"),
            BotCommand("challenge", "تحدّي اليوم 🎯"),
            BotCommand("settings",  "تخصيص الأزواج والفريمات ⚙️"),
            BotCommand("help",      "المساعدة وشرح الأوامر"),
        ]
        for scope in (BotCommandScopeDefault(), BotCommandScopeAllPrivateChats()):
            for lang in (None, "ar", "en"):
                try:
                    await application.bot.set_my_commands(cmds, scope=scope, language_code=lang)
                except Exception as _ce:
                    logger.warning(f"set_my_commands {scope.type}/{lang}: {_ce}")
        asyncio.create_task(broadcast_new_signals(application))
        asyncio.create_task(outcome_checker(application))
        asyncio.create_task(breakeven_alerts(application))
        asyncio.create_task(daily_challenge(application))
        asyncio.create_task(monitor_watchlists(application))
        asyncio.create_task(notify_expiry(application))
        asyncio.create_task(market_session_notifier(application))
        asyncio.create_task(session_pre_alert(application))
        asyncio.create_task(daily_briefing(application))
        asyncio.create_task(economic_news_alert(application))

    app.post_init = post_init

    logger.success("✅ البوت يعمل — 8 مهام خلفية نشطة")
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
