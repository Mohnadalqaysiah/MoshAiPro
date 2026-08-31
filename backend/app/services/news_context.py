"""
Mosh AI Pro v5 - Market News Context (advisory only)
Fetches recent Finnhub headlines relevant to a symbol and asks Groq for a
short Arabic sentiment summary. Purely informational — same contract as
Gemini's enrichment step in ai_engine_v5.py::analyze_market(): text only,
never touches recommendation/levels/confidence. Called only for signals
that already passed every decision gate, to keep API usage proportional
to what users actually see.
"""
import time
import asyncio
import requests
from typing import Optional
from loguru import logger

from app.config import get_settings

settings = get_settings()

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/news"
FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"

# رمز → (فئة أخبار Finnhub، كلمات مفتاحية للفلترة بالعنوان/الملخص)
_SYMBOL_NEWS_MAP: dict[str, tuple[str, list[str]]] = {
    "XAUUSD": ("general", ["gold", "bullion", "precious metal"]),
    "XAGUSD": ("general", ["silver", "precious metal"]),
    "COPPER": ("general", ["copper"]),
    "XPTUSD": ("general", ["platinum"]),
    "USOIL":  ("general", ["oil", "crude", "opec", "wti"]),
    "NATGAS": ("general", ["natural gas", "gas price"]),
    "DXY":    ("forex",   ["dollar index", "dxy", "fed", "federal reserve"]),
    "NAS100": ("general", ["nasdaq"]),
    "US30":   ("general", ["dow jones"]),
    "SP500":  ("general", ["s&p 500", "s&p500"]),
    "BTCUSD": ("crypto",  ["bitcoin", "btc"]),
    "ETHUSD": ("crypto",  ["ethereum", "eth"]),
    "BNBUSD": ("crypto",  ["binance", "bnb"]),
    "SOLUSD": ("crypto",  ["solana", "sol"]),
    "XRPUSD": ("crypto",  ["ripple", "xrp"]),
    "ADAUSD": ("crypto",  ["cardano", "ada"]),
    "DOGEUSD": ("crypto", ["dogecoin", "doge"]),
}
_FOREX_PAIRS = {"EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD","NZDUSD","EURGBP","EURJPY","GBPJPY"}
_STOCK_SYMBOLS = {"AAPL","TSLA","NVDA","MSFT","GOOGL","META","AMZN","AMD","NFLX"}

_MAX_NEWS_AGE_SEC = 24 * 3600
_CACHE_TTL_SEC    = 90 * 60   # ساعة ونص — الأخبار ما بتتغير كل دقيقة

_cache: dict[str, tuple[Optional[str], float]] = {}


def _resolve_category_and_keywords(symbol: str) -> tuple[str, list[str]]:
    sym = symbol.upper()
    if sym in _SYMBOL_NEWS_MAP:
        return _SYMBOL_NEWS_MAP[sym]
    if sym in _FOREX_PAIRS:
        return ("forex", [sym[:3].lower(), sym[3:6].lower()])
    if sym in _STOCK_SYMBOLS:
        return ("company", [sym])
    return ("general", [sym.lower()])


def _fetch_headlines(symbol: str, category: str, keywords: list[str]) -> list[dict]:
    fh_key = getattr(settings, "FINNHUB_API_KEY", "")
    if not fh_key:
        return []

    try:
        if category == "company":
            from datetime import datetime, timedelta, timezone
            today = datetime.now(timezone.utc).date()
            resp = requests.get(FINNHUB_COMPANY_NEWS_URL, params={
                "symbol": symbol, "from": str(today - timedelta(days=2)),
                "to": str(today), "token": fh_key,
            }, timeout=8)
        else:
            resp = requests.get(FINNHUB_NEWS_URL, params={
                "category": category, "token": fh_key,
            }, timeout=8)
        items = resp.json()
        if not isinstance(items, list):
            return []
    except Exception as e:
        logger.warning(f"news_context: Finnhub fetch failed [{symbol}]: {e}")
        return []

    now = time.time()
    matched = []
    for it in items:
        ts = it.get("datetime") or 0
        if now - ts > _MAX_NEWS_AGE_SEC:
            continue
        text = f"{it.get('headline','')} {it.get('summary','')}".lower()
        if category == "company" or any(kw in text for kw in keywords):
            matched.append(it)
        if len(matched) >= 6:
            break
    return matched


def _call_groq_summary(symbol: str, headlines: list[dict]) -> Optional[str]:
    groq_key = getattr(settings, "GROQ_API_KEY", "")
    if not groq_key or not headlines:
        return None

    lines = "\n".join(f"- {h.get('headline','')}" for h in headlines[:6])
    prompt = (
        f"هذه عناوين أخبار حديثة متعلقة بـ {symbol}:\n{lines}\n\n"
        "لخّص المزاج العام لهذه الأخبار (إيجابي/سلبي/محايد) بجملة أو جملتين "
        "بالعربي العامية البسيطة. لا تقترح شراء أو بيع، ولا تذكر أي أرقام أو "
        "أسعار أو مستويات دخول/وقف/هدف — وصف عام للأجواء الإخبارية فقط."
    )
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 120,
            },
            timeout=12,
        )
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text or None
    except Exception as e:
        logger.warning(f"news_context: Groq summary failed [{symbol}]: {e}")
        return None


async def get_news_context(symbol: str) -> Optional[str]:
    """يرجّع ملخص مزاج إخباري قصير بالعربي لرمز معيّن، أو None لو ما في
    أخبار ذات صلة أو أي من المفتاحين (Finnhub/Groq) غير مُفعَّل. Advisory
    فقط — لا يُستخدم أبداً كمدخل لقرار BUY/SELL أو أي مستوى سعر."""
    sym = symbol.upper()
    now = time.time()

    cached = _cache.get(sym)
    if cached and (now - cached[1] < _CACHE_TTL_SEC):
        return cached[0]

    def _work():
        category, keywords = _resolve_category_and_keywords(sym)
        headlines = _fetch_headlines(sym, category, keywords)
        if not headlines:
            return None
        return _call_groq_summary(sym, headlines)

    try:
        summary = await asyncio.to_thread(_work)
    except Exception as e:
        logger.warning(f"news_context: unexpected error [{sym}]: {e}")
        summary = None

    _cache[sym] = (summary, now)
    return summary
