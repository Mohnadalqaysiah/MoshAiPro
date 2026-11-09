"""
(2026-11-09) سجل الكريبتو الموحّد — طلب المالك "اضف العملات القوية… نبقيها لمدة اسبوع ومن ثم ندرسها ونقررها".

لماذا: إضافة عملة كانت تمر على ~12 مكاناً متفرقاً (خريطة المواضع: crypto_symbols)، ووُجد فيها نقص فعلي
(DOGEUSD غائبة عن قائمة "مفتوح 24/7" بـsmart_data). هنا كل ما تحتاجه العملة سطر واحد، والأماكن تقرأ منه.

status:
  "live"  — تُرسل إشاراتها للعملاء (السبع الأصلية؛ إعداداتها القائمة لم تتغير — هذا الملف لا يعيد تعريفها حيث تعمل).
  "trial" — تُفحص وتُحسب، لكن الإشارة تُسجَّل بجدول الظل (reason=NEW_COIN_TRIAL) بدل Signal: لا بث، ولا تنبيه، ولا إشعار،
            ولا إحصائية، ولا تظهر بقوائم المستخدم (لا صف MarketConfig). تُقاس بقاعدة المراقبة (11) بـdiag_watch.
  الانتقال من trial إلى live قرار المالك بعد القراءة — ثم صف MarketConfig + البوت + الشارت (خريطة المواضع).

الاختيار (09/11): عالية السيولة على Binance، ولها شموع yfinance فعلية (فُحصت: 1436 شمعة ساعة لكلٍّ بحجم تداول)
ورمز Binance على TradingView — فلا مصدر بيانات جديد. استُبعدت TON (حجم yfinance صفر) وTRX (حركة ضعيفة لا تناسب وقفاً وأهدافاً).
الإيقاف الطارئ للتجربة كلها: NEW_COIN_TRIAL=0 بـbackend/.env.prod ← لا تُفحص العملات التجريبية أصلاً.
"""
import os
from datetime import datetime, timezone

REASON = "NEW_COIN_TRIAL"
TRIAL_START = datetime(2026, 11, 10, tzinfo=timezone.utc)   # أول يوم كامل بعد النشر — بداية بيانات القاعدة (11)

# symbol: (status, اسم عربي, اسم إنجليزي, رمز TradingView, رمز yfinance, سبريد تقريبي بوحدة السعر)
COINS = {
    "BTCUSD":  ("live",  "بيتكوين",   "Bitcoin",      "BINANCE:BTCUSDT",  "BTC-USD",      15.0),
    "ETHUSD":  ("live",  "إيثيريوم",  "Ethereum",     "BINANCE:ETHUSDT",  "ETH-USD",      1.5),
    "BNBUSD":  ("live",  "BNB",       "BNB",          "BINANCE:BNBUSDT",  "BNB-USD",      0.5),
    "SOLUSD":  ("live",  "سولانا",    "Solana",       "BINANCE:SOLUSDT",  "SOL-USD",      0.10),
    "XRPUSD":  ("live",  "ريبل",      "XRP",          None,               "XRP-USD",      0.002),
    "ADAUSD":  ("live",  "كاردانو",   "Cardano",      None,               "ADA-USD",      0.0008),
    "DOGEUSD": ("live",  "دوجكوين",   "Dogecoin",     None,               "DOGE-USD",     0.0003),
    # ── تجربة أسبوع بالظل من 10/11 ──  السبريد ≈ 0.25% من السعر يوم الإضافة (نفس نسبة ADA/DOGE تقريباً)
    "AVAXUSD": ("trial", "أفالانش",   "Avalanche",    "BINANCE:AVAXUSDT", "AVAX-USD",     0.02),
    "LINKUSD": ("trial", "تشين لينك", "Chainlink",    "BINANCE:LINKUSDT", "LINK-USD",     0.025),
    "LTCUSD":  ("trial", "لايتكوين",  "Litecoin",     "BINANCE:LTCUSDT",  "LTC-USD",      0.12),
    "BCHUSD":  ("trial", "بيتكوين كاش", "Bitcoin Cash", "BINANCE:BCHUSDT", "BCH-USD",     0.6),
    "DOTUSD":  ("trial", "بولكادوت",  "Polkadot",     "BINANCE:DOTUSDT",  "DOT-USD",      0.002),
    "SUIUSD":  ("trial", "سوي",       "Sui",          "BINANCE:SUIUSDT",  "SUI20947-USD", 0.002),
}


def trial_enabled() -> bool:
    return os.getenv("NEW_COIN_TRIAL", "1").strip().lower() not in ("0", "false", "no", "off")


def symbols(status: str = None) -> list:
    return [s for s, v in COINS.items() if status is None or v[0] == status]


def trial_symbols() -> list:
    return symbols("trial") if trial_enabled() else []


def is_trial(symbol: str) -> bool:
    """True = إشارة هذا الرمز تذهب للظل لا للعملاء."""
    return bool(symbol) and trial_enabled() and COINS.get(symbol.replace("/", "").upper(), ("",))[0] == "trial"


def yf_map(status: str = "trial") -> dict:
    return {s: COINS[s][4] for s in symbols(status) if COINS[s][4]}


def tv_map(status: str = "trial") -> dict:
    return {s: COINS[s][3] for s in symbols(status) if COINS[s][3]}


def spreads(status: str = "trial") -> dict:
    return {s: COINS[s][5] for s in symbols(status)}
