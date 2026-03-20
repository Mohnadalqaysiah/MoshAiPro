"""
Mosh AI Pro v5 - Smart Rate Limiter
نظام ذكي للتحكم في معدل الطلبات لـ TwelveData API
Token Bucket Algorithm + Priority Queue + Smart Cache
"""

import asyncio
import time
import requests
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger
from app.config import get_settings

settings = get_settings()


class SmartRateLimiter:
    """
    Token Bucket Rate Limiter مع Smart Cache
    يضمن عدم تجاوز 8 طلبات/دقيقة مع تحديد الأولويات
    """

    def __init__(self, rate: int = 8, per_seconds: int = 60):
        self.rate        = rate          # الحد الأقصى للطلبات
        self.per_seconds = per_seconds   # الفترة الزمنية
        self.tokens      = float(rate)   # رصيد الطلبات الحالي
        self.last_refill = time.monotonic()
        self._lock       = asyncio.Lock()

        # إحصائيات
        self.total_requests  = 0
        self.cached_requests = 0
        self.queued_requests = 0

    def _refill(self):
        """إعادة شحن الرصيد بناءً على الوقت المنقضي"""
        now     = time.monotonic()
        elapsed = now - self.last_refill
        refill  = elapsed * (self.rate / self.per_seconds)
        self.tokens      = min(self.rate, self.tokens + refill)
        self.last_refill = now

    async def acquire(self, tokens: int = 1):
        """انتظر حتى يتوفر رصيد كافٍ"""
        async with self._lock:
            while True:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    self.total_requests += 1
                    return
                # احسب وقت الانتظار
                wait_time = (tokens - self.tokens) / (self.rate / self.per_seconds)
                logger.info(f"⏳ Rate limit: انتظار {wait_time:.1f}ث قبل الطلب التالي")
                await asyncio.sleep(wait_time + 0.1)

    def stats(self) -> dict:
        self._refill()
        return {
            "tokens_available": round(self.tokens, 2),
            "rate_limit": f"{self.rate}/min",
            "total_requests": self.total_requests,
            "cached_requests": self.cached_requests,
            "savings_pct": round(
                self.cached_requests / max(1, self.total_requests + self.cached_requests) * 100, 1
            )
        }


class SmartDataCache:
    """
    Cache ذكي مع TTL مختلف حسب نوع الزوج والإطار الزمني
    """

    # مدة الـ Cache بالثوانٍ حسب الإطار الزمني
    TTL_MAP = {
        "1min":  60,
        "5min":  120,
        "15min": 300,   # 5 دقائق
        "30min": 600,   # 10 دقائق
        "1h":    900,   # 15 دقيقة
        "4h":    1800,  # 30 دقيقة
        "1day":  3600,  # ساعة
        "1week": 7200,  # ساعتان
    }

    def __init__(self):
        self._store: Dict[str, tuple] = {}  # key → (data, timestamp)

    def get(self, key: str, interval: str) -> Optional[pd.DataFrame]:
        if key not in self._store:
            return None
        data, ts = self._store[key]
        ttl = self.TTL_MAP.get(interval, 300)
        if time.time() - ts < ttl:
            return data
        del self._store[key]
        return None

    def set(self, key: str, data: pd.DataFrame):
        self._store[key] = (data, time.time())

    def clear_expired(self):
        """حذف البيانات المنتهية الصلاحية"""
        now = time.time()
        expired = [k for k, (_, ts) in self._store.items() if now - ts > 7200]
        for k in expired:
            del self._store[k]
        return len(expired)

    def info(self) -> dict:
        return {
            "cached_symbols": len(self._store),
            "keys": list(self._store.keys())
        }


class TwelveDataClient:
    """
    عميل TwelveData مع Rate Limiting ذكي وBatch support
    """

    INTERVAL_MAP = {
        "15m":  "15min",
        "30m":  "30min",
        "1h":   "1h",
        "4h":   "4h",
        "1d":   "1day",
        "1day": "1day",
        "1w":   "1week",
    }

    SYMBOL_MAP = {
        "XAUUSD": "XAU/USD",
        "BTCUSD": "BTC/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "USDCHF": "USD/CHF",
        "ETHUSD": "ETH/USD",
    }

    def __init__(self):
        self.api_key     = settings.TWELVEDATA_API_KEY
        self.base_url    = "https://api.twelvedata.com"
        self.limiter     = SmartRateLimiter(rate=settings.TWELVEDATA_RATE_LIMIT, per_seconds=60)
        self.cache       = SmartDataCache()

    def _norm_symbol(self, symbol: str) -> str:
        return self.SYMBOL_MAP.get(symbol.upper(), symbol)

    def _norm_interval(self, interval: str) -> str:
        return self.INTERVAL_MAP.get(interval.lower(), interval)

    async def get_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        outputsize: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        جلب بيانات OHLCV مع Cache ذكي وRate Limiting
        """
        norm_sym = self._norm_symbol(symbol)
        norm_int = self._norm_interval(interval)
        cache_key = f"{norm_sym}_{norm_int}_{outputsize}"

        # تحقق من الـ Cache أولاً
        cached = self.cache.get(cache_key, norm_int)
        if cached is not None:
            self.limiter.cached_requests += 1
            logger.info(f"📦 Cache hit: {symbol} {interval}")
            return cached

        # اطلب من API مع Rate Limiting
        await self.limiter.acquire(1)

        try:
            url = f"{self.base_url}/time_series"
            params = {
                "symbol":     norm_sym,
                "interval":   norm_int,
                "outputsize": outputsize,
                "apikey":     self.api_key,
                "format":     "JSON",
            }

            logger.info(f"📡 TwelveData → {norm_sym} {norm_int} (رصيد: {self.limiter.tokens:.1f}/{self.limiter.rate})")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "values" not in data:
                err = data.get("message", "No data")
                logger.error(f"❌ TwelveData: {symbol}: {err}")
                return None

            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            else:
                df["volume"] = 0.0

            self.cache.set(cache_key, df)
            logger.success(f"✅ {symbol}: {len(df)} شمعة (رصيد متبقٍ: {self.limiter.tokens:.1f})")
            return df

        except Exception as e:
            logger.error(f"❌ خطأ في جلب {symbol}: {e}")
            return None

    async def get_batch_ohlcv(
        self,
        symbols: List[str],
        interval: str = "1h",
        outputsize: int = 100
    ) -> Dict[str, pd.DataFrame]:
        """
        جلب عدة أزواج بطلب واحد للـ API (توفير الـ credits)
        TwelveData يسمح بفصل الأزواج بفاصلة
        """
        norm_int = self._norm_interval(interval)
        results  = {}

        # افصل الأزواج إلى: محتاج طلب ← من الـ Cache
        need_fetch = []
        for sym in symbols:
            norm_sym  = self._norm_symbol(sym)
            cache_key = f"{norm_sym}_{norm_int}_{outputsize}"
            cached = self.cache.get(cache_key, norm_int)
            if cached is not None:
                results[sym] = cached
                self.limiter.cached_requests += 1
                logger.info(f"📦 Cache hit: {sym}")
            else:
                need_fetch.append(sym)

        if not need_fetch:
            return results

        # جلب دفعي
        norm_syms = ",".join(self._norm_symbol(s) for s in need_fetch)

        # كل زوج يحتاج token واحد
        await self.limiter.acquire(len(need_fetch))

        try:
            url = f"{self.base_url}/time_series"
            params = {
                "symbol":     norm_syms,
                "interval":   norm_int,
                "outputsize": outputsize,
                "apikey":     self.api_key,
                "format":     "JSON",
            }

            logger.info(f"📡 Batch fetch: {norm_syms} (tokens: {len(need_fetch)})")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            # إذا زوج واحد → data مباشرة
            # إذا أكثر → data[symbol]
            def parse_single(raw, sym):
                if "values" not in raw:
                    return None
                df = pd.DataFrame(raw["values"])
                df["datetime"] = pd.to_datetime(df["datetime"])
                df = df.sort_values("datetime").reset_index(drop=True)
                for col in ["open", "high", "low", "close"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce") if "volume" in df.columns else 0.0
                return df

            if len(need_fetch) == 1:
                df = parse_single(data, need_fetch[0])
                if df is not None:
                    sym = need_fetch[0]
                    results[sym] = df
                    self.cache.set(f"{self._norm_symbol(sym)}_{norm_int}_{outputsize}", df)
            else:
                for sym in need_fetch:
                    norm_sym = self._norm_symbol(sym)
                    raw = data.get(norm_sym, {})
                    df  = parse_single(raw, sym)
                    if df is not None:
                        results[sym] = df
                        self.cache.set(f"{norm_sym}_{norm_int}_{outputsize}", df)

            logger.success(f"✅ Batch جلب {len(results)}/{len(symbols)} زوج")

        except Exception as e:
            logger.error(f"❌ Batch fetch error: {e}")

        return results

    def get_status(self) -> dict:
        """حالة الـ Rate Limiter والـ Cache"""
        stats = self.limiter.stats()
        cache_info = self.cache.info()
        return {
            "rate_limiter": stats,
            "cache": cache_info,
            "remaining_tokens": round(self.limiter.tokens, 2),
        }


# Singleton
twelvedata_client = TwelveDataClient()
