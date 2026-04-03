"""
Mosh AI Pro v5 - Smart Data Provider
Primary: yfinance (free, unlimited)
Secondary: TwelveData (paid, for real-time)

يجلب بيانات OHLCV حقيقية مع fallback تلقائي
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger
import requests

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception as _yf_err:
    YFINANCE_AVAILABLE = False
    logger.warning(f"yfinance unavailable: {_yf_err}")

from app.config import get_settings

settings = get_settings()

# ─── Symbol Maps ──────────────────────────────────────────────────────────────

YFINANCE_MAP = {
    "XAUUSD": "GC=F",       # Gold Futures
    "BTCUSD": "BTC-USD",    # Bitcoin
    "ETHUSD": "ETH-USD",    # Ethereum
    "EURUSD": "EURUSD=X",   # Euro/Dollar
    "GBPUSD": "GBPUSD=X",   # Pound/Dollar
    "USDJPY": "USDJPY=X",   # Dollar/Yen
    "USDCHF": "USDCHF=X",   # Dollar/Franc
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
    "NAS100":  "NQ=F",      # Nasdaq Futures
    "NASDAQ":  "NQ=F",
    "US100":   "NQ=F",
    "SP500":   "ES=F",      # S&P 500 Futures
    "US500":   "ES=F",
    "DOW":     "YM=F",      # Dow Jones Futures
    "US30":    "YM=F",
    "USOIL":   "CL=F",      # WTI Crude Oil
    "OIL":     "CL=F",
    "XAGUSD":  "SI=F",      # Silver
    "NATGAS":  "NG=F",      # Natural Gas
    "USDINDEX":"DX-Y.NYB",  # US Dollar Index
    "DXY":     "DX-Y.NYB",
    # أسهم أمريكية شائعة — yfinance يستخدمها مباشرة
    "AAPL":  "AAPL",  "TSLA": "TSLA",  "MSFT": "MSFT",
    "NVDA":  "NVDA",  "AMZN": "AMZN",  "GOOGL":"GOOGL",
    "META":  "META",  "NFLX": "NFLX",  "AMD":  "AMD",
}

TWELVEDATA_MAP = {
    "XAUUSD": "XAU/USD",
    "BTCUSD": "BTC/USD",
    "ETHUSD": "ETH/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF",
    "AUDUSD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
}

# Finnhub symbols (رموز للـ quote endpoint)
FINNHUB_MAP = {
    "XAUUSD": "OANDA:XAU_USD",
    "BTCUSD": "BINANCE:BTCUSDT",
    "ETHUSD": "BINANCE:ETHUSDT",
    "EURUSD": "OANDA:EUR_USD",
    "GBPUSD": "OANDA:GBP_USD",
    "USDJPY": "OANDA:USD_JPY",
    "USDCHF": "OANDA:USD_CHF",
    "AUDUSD": "OANDA:AUD_USD",
    "USDCAD": "OANDA:USD_CAD",
    "NZDUSD": "OANDA:NZD_USD",
    "NAS100":  "OANDA:NAS100_USD",
    "NASDAQ":  "OANDA:NAS100_USD",
    "US100":   "OANDA:NAS100_USD",
    "SP500":   "OANDA:SPX500_USD",
    "US500":   "OANDA:SPX500_USD",
    "DOW":     "OANDA:US30_USD",
    "US30":    "OANDA:US30_USD",
    "USOIL":   "OANDA:WTICO_USD",
    "OIL":     "OANDA:WTICO_USD",
    "XAGUSD":  "OANDA:XAG_USD",
    "NATGAS":  "OANDA:NATGAS_USD",
}

# yfinance interval map
YF_INTERVAL_MAP = {
    "1m":  "1m",
    "5m":  "5m",
    "15m": "15m",
    "30m": "30m",
    "1h":  "1h",
    "4h":  "1h",   # resample from 1h
    "1d":  "1d",
    "1day": "1d",
    "1w":  "1wk",
}

# yfinance period map (how far back to fetch)
YF_PERIOD_MAP = {
    "1m":  "1d",
    "5m":  "5d",
    "15m": "5d",
    "30m": "30d",
    "1h":  "60d",
    "4h":  "60d",
    "1d":  "1y",
    "1day": "1y",
    "1w":  "5y",
}

TD_INTERVAL_MAP = {
    "15m": "15min", "30m": "30min",
    "1h": "1h", "4h": "4h",
    "1d": "1day", "1day": "1day",
}


class SmartDataProvider:
    """
    مزود البيانات الذكي:
    - يجرب yfinance أولاً (مجاني، بلا حدود)
    - إذا فشل → يجرب TwelveData
    - يحسب المؤشرات التقنية الكاملة
    """

    def __init__(self):
        self.td_key  = settings.TWELVEDATA_API_KEY
        self.td_base = "https://api.twelvedata.com"
        self._cache: Dict[str, tuple] = {}
        # كاش السعر الفوري — TTL 30 ثانية (أسرع تحديث لمنع فوارق السعر)
        self._price_cache: Dict[str, tuple] = {}   # symbol → (price, source, fetched_at, ts)
        self._PRICE_TTL = 30  # ثانية (كان 180 — خُفِّض لأن الذهب يتحرك $1+ كل دقيقة)

        # Finnhub (مجاني 60 req/min) — بديل TwelveData
        self._fh_key  = getattr(settings, "FINNHUB_API_KEY", None)
        self._fh_base = "https://finnhub.io/api/v1"

        # TwelveData — معطّل افتراضياً، يُفعَّل من لوحة الإدارة فقط
        self._td_enabled = False
        self._td_runtime_key: str = ""

    # ─── Public: fetch OHLCV ───────────────────────────────────────────────

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", bars: int = 150) -> Optional[pd.DataFrame]:
        """
        جلب بيانات OHLCV مع fallback تلقائي وحساب المؤشرات
        """
        cache_key = f"{symbol}_{timeframe}"
        ttl = self._get_ttl(timeframe)

        # Cache check
        if cache_key in self._cache:
            df_cached, ts = self._cache[cache_key]
            if (datetime.now() - ts).total_seconds() < ttl:
                logger.debug(f"📦 Cache hit: {symbol} {timeframe}")
                return df_cached

        # 1. yfinance أولاً
        df = None
        if YFINANCE_AVAILABLE:
            df = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_yfinance, symbol, timeframe, bars
            )

        # 2. Finnhub candles — مجاني 60/min
        if df is None and self._fh_key:
            df = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_finnhub_candles, symbol, timeframe, bars
            )

        # 3. TwelveData — فقط إذا فعّله الأدمن صراحةً
        if df is None and self._td_enabled and self._td_runtime_key:
            df = await self._fetch_twelvedata(symbol, timeframe, bars)

        if df is None or len(df) < 30:
            logger.error(f"❌ Failed to fetch data for {symbol}")
            return None

        # Add technical indicators
        df = self._add_indicators(df)

        self._cache[cache_key] = (df, datetime.now())
        logger.success(f"✅ {symbol} {timeframe}: {len(df)} bars fetched")
        return df

    # ─── yfinance ─────────────────────────────────────────────────────────

    def _fetch_yfinance(self, symbol: str, timeframe: str, bars: int) -> Optional[pd.DataFrame]:
        try:
            yf_symbol = YFINANCE_MAP.get(symbol.upper(), symbol)
            yf_interval = YF_INTERVAL_MAP.get(timeframe, "1h")
            yf_period = YF_PERIOD_MAP.get(timeframe, "60d")

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=yf_period, interval=yf_interval, auto_adjust=True)

            if df is None or len(df) < 10:
                logger.warning(f"⚠️ yfinance returned no data for {yf_symbol}")
                return None

            # Normalize columns
            df = df.rename(columns={
                "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume"
            })
            df.index = pd.to_datetime(df.index)
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df = df.dropna(subset=["open", "high", "low", "close"])

            # Resample 1h → 4h if needed
            if timeframe == "4h":
                df = df.resample("4h").agg({
                    "open": "first", "high": "max",
                    "low": "min", "close": "last", "volume": "sum"
                }).dropna()

            df = df.tail(bars).reset_index()
            df = df.rename(columns={"index": "datetime", "Datetime": "datetime", "Date": "datetime"})

            if "volume" not in df.columns:
                df["volume"] = 0.0
            df["volume"] = df["volume"].fillna(0.0)

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.info(f"📊 yfinance: {yf_symbol} → {len(df)} bars")
            return df

        except Exception as e:
            logger.warning(f"⚠️ yfinance error for {symbol}: {e}")
            return None

    # ─── Finnhub Candles ──────────────────────────────────────────────────

    def _fetch_finnhub_candles(self, symbol: str, timeframe: str, bars: int) -> Optional[pd.DataFrame]:
        """Finnhub OHLCV — مجاني 60 req/min، يدعم forex/metals/crypto"""
        if not self._fh_key:
            return None
        try:
            import time as _time
            fh_symbol = FINNHUB_MAP.get(symbol.upper())
            if not fh_symbol:
                return None

            # تحويل الفريم لـ Finnhub resolution
            res_map = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"60","1d":"D","1day":"D","1w":"W"}
            resolution = res_map.get(timeframe, "60")

            # نطاق زمني
            to_ts   = int(_time.time())
            bars_needed = bars * 2 if timeframe == "4h" else bars
            seconds = {"1":"60","5":300,"15":900,"30":1800,"60":3600,"D":86400,"W":604800}.get(resolution, 3600)
            from_ts = to_ts - (bars_needed * seconds)

            # نختار الـ endpoint بناءً على نوع الأصل
            sym_up = symbol.upper()
            if sym_up in ("BTCUSD","ETHUSD"):
                endpoint = f"{self._fh_base}/crypto/candle"
            else:
                endpoint = f"{self._fh_base}/forex/candle"

            resp = requests.get(endpoint, params={
                "symbol": fh_symbol, "resolution": resolution,
                "from": from_ts, "to": to_ts, "token": self._fh_key
            }, timeout=15)
            data = resp.json()

            if data.get("s") != "ok" or not data.get("t"):
                logger.warning(f"Finnhub candles: no data for {symbol} ({data.get('s')})")
                return None

            df = pd.DataFrame({
                "datetime": pd.to_datetime(data["t"], unit="s", utc=True),
                "open":  data["o"], "high": data["h"],
                "low":   data["l"], "close": data["c"],
                "volume": data.get("v", [0]*len(data["t"]))
            })
            df = df.set_index("datetime")

            # Resample 1h → 4h
            if timeframe == "4h":
                df = df.resample("4h").agg({
                    "open":"first","high":"max","low":"min","close":"last","volume":"sum"
                }).dropna()

            df = df.tail(bars).reset_index()
            for col in ["open","high","low","close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["open","high","low","close"])
            if len(df) < 10:
                return None

            logger.info(f"✅ Finnhub candles: {symbol} {timeframe} — {len(df)} bars")
            return df

        except Exception as e:
            logger.warning(f"Finnhub candles error {symbol}: {e}")
            return None

    # ─── TwelveData ───────────────────────────────────────────────────────

    async def _fetch_twelvedata(self, symbol: str, timeframe: str, bars: int) -> Optional[pd.DataFrame]:
        try:
            td_symbol = TWELVEDATA_MAP.get(symbol.upper(), symbol)
            td_interval = TD_INTERVAL_MAP.get(timeframe, timeframe)

            url = f"{self.td_base}/time_series"
            params = {
                "symbol": td_symbol,
                "interval": td_interval,
                "outputsize": bars,
                "apikey": self.td_key,
                "format": "JSON"
            }

            resp = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.get(url, params=params, timeout=15)
            )
            resp.raise_for_status()
            data = resp.json()

            if "values" not in data:
                logger.error(f"❌ TwelveData no values: {data.get('message', '')}")
                return None

            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
            else:
                df["volume"] = 0.0

            logger.info(f"📡 TwelveData: {td_symbol} → {len(df)} bars")
            return df

        except Exception as e:
            logger.error(f"❌ TwelveData error for {symbol}: {e}")
            return None

    # ─── Technical Indicators ──────────────────────────────────────────────

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """يضيف المؤشرات التقنية المهمة"""
        try:
            c = df["close"]
            h = df["high"]
            l = df["low"]

            # ATR (14)
            tr = pd.concat([
                h - l,
                (h - c.shift()).abs(),
                (l - c.shift()).abs()
            ], axis=1).max(axis=1)
            df["atr"] = tr.rolling(14).mean()

            # RSI (14)
            delta = c.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            df["rsi"] = 100 - (100 / (1 + rs))

            # EMA
            df["ema_20"] = c.ewm(span=20, adjust=False).mean()
            df["ema_50"] = c.ewm(span=50, adjust=False).mean()
            df["ema_200"] = c.ewm(span=200, adjust=False).mean()

            # MACD
            ema12 = c.ewm(span=12, adjust=False).mean()
            ema26 = c.ewm(span=26, adjust=False).mean()
            df["macd"] = ema12 - ema26
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_hist"] = df["macd"] - df["macd_signal"]

            # Bollinger Bands (20, 2)
            ma20 = c.rolling(20).mean()
            std20 = c.rolling(20).std()
            df["bb_upper"] = ma20 + 2 * std20
            df["bb_lower"] = ma20 - 2 * std20
            df["bb_mid"] = ma20

            # Stochastic (14,3)
            low14 = l.rolling(14).min()
            high14 = h.rolling(14).max()
            df["stoch_k"] = 100 * (c - low14) / (high14 - low14 + 1e-10)
            df["stoch_d"] = df["stoch_k"].rolling(3).mean()

            # Candle body size
            df["body"] = (c - df["open"]).abs()
            df["is_bullish"] = c > df["open"]

            df = df.fillna(method="bfill").fillna(0)

        except Exception as e:
            logger.warning(f"⚠️ Indicator calculation partial error: {e}")

        return df

    def _get_ttl(self, timeframe: str) -> int:
        """Cache TTL بالثواني حسب الإطار الزمني"""
        ttls = {
            "1m": 30, "5m": 60, "15m": 180,
            "30m": 300, "1h": 600, "4h": 1800,
            "1d": 3600, "1day": 3600, "1w": 7200
        }
        return ttls.get(timeframe, 300)

    # الأسواق التي تستخدم Futures في yfinance — البيانات التاريخية والسعر الفوري
    # يجب أن يكونا من نفس المصدر لتفادي فارق Spot vs Futures
    _FUTURES_SYMBOLS = {"XAUUSD", "XAGUSD", "NAS100", "US30", "SP500", "USOIL", "NATGAS"}

    def get_realtime_price_with_meta(self, symbol: str) -> Optional[Dict]:
        """
        جلب السعر الفوري مع المصدر والوقت.

        ⚠️  مبدأ الاتساق: يجب أن يكون السعر الفوري من نفس المصدر الذي جُلبت منه
        البيانات التاريخية (OHLCV)، لأن مستويات ICT (Entry/SL/TP) محسوبة على
        أساس تلك البيانات. خلط Spot مع Futures يُنتج فوارق $5-20 للذهب.

        الأولوية:
        - Futures (XAUUSD/NAS100...): yfinance دائماً (نفس مصدر الكاندلز)
        - Forex/Crypto: Finnhub أولاً (spot حقيقي) → yfinance
        """
        sym = symbol.upper()
        now_ts = datetime.utcnow().timestamp()

        # ─── 0. كاش ───────────────────────────────────────────────────────────
        cached = self._price_cache.get(sym)
        if cached:
            price, source, fetched_at, ts = cached
            if now_ts - ts < self._PRICE_TTL:
                return {"price": price, "source": f"{source}(cached)", "fetched_at": fetched_at}

        fetched_at = datetime.utcnow().isoformat() + "Z"

        # ─── 0.5 للمعادن: TV Spot أولاً — هذا ما يراه المستخدم في MT4 ─────────
        # GC=F Futures تختلف عن XAUUSD Spot بـ $10-60 → نعرض Spot للمستخدم
        _METALS = {"XAUUSD", "XAGUSD"}
        if sym in _METALS:
            try:
                from app.services.tv_price_feed import tv_feed
                tv_p = tv_feed.get_price_sync(sym)
                if tv_p and float(tv_p) > 0:
                    price = float(tv_p)
                    self._price_cache[sym] = (price, "tv_spot", fetched_at, now_ts)
                    logger.debug(f"💱 [tv_spot] {sym}: {price}")
                    return {"price": price, "source": "tv_spot", "fetched_at": fetched_at}
            except Exception as _tv_e:
                logger.debug(f"TV spot fallback for {sym}: {_tv_e}")
            # إذا TV غير متاح → نكمل بـ yfinance Futures وتطبيق basis لاحقاً

        # ─── 1. Futures symbols → yfinance دائماً (تطابق مصدر الكاندلز) ──────
        if sym in self._FUTURES_SYMBOLS:
            try:
                if YFINANCE_AVAILABLE:
                    yf_symbol = YFINANCE_MAP.get(sym, sym)
                    ticker = yf.Ticker(yf_symbol)
                    hist = ticker.history(period="1d", interval="1m")
                    if hist is not None and len(hist) > 0:
                        price = float(hist["Close"].iloc[-1])
                        src = "yfinance_futures"
                        self._price_cache[sym] = (price, src, fetched_at, now_ts)
                        logger.debug(f"💱 [{src}] {sym}: {price}")
                        return {"price": price, "source": src, "fetched_at": fetched_at}
            except Exception as e:
                logger.warning(f"yfinance futures price error for {symbol}: {e}")
            # Finnhub كـ fallback للفيوتشرز فقط عند فشل yfinance
            if self._fh_key:
                try:
                    fh_symbol = FINNHUB_MAP.get(sym)
                    if fh_symbol:
                        resp = requests.get(
                            f"{self._fh_base}/quote",
                            params={"symbol": fh_symbol, "token": self._fh_key},
                            timeout=5,
                        )
                        data = resp.json()
                        price = data.get("c") or data.get("l")
                        if price and float(price) > 0:
                            price = float(price)
                            self._price_cache[sym] = (price, "finnhub_fallback", fetched_at, now_ts)
                            return {"price": price, "source": "finnhub_fallback", "fetched_at": fetched_at}
                except Exception as e:
                    logger.warning(f"Finnhub fallback price error for {symbol}: {e}")
            return None

        # ─── 2. Forex / Crypto → Finnhub spot أولاً ──────────────────────────
        if self._fh_key:
            try:
                fh_symbol = FINNHUB_MAP.get(sym)
                if fh_symbol:
                    resp = requests.get(
                        f"{self._fh_base}/quote",
                        params={"symbol": fh_symbol, "token": self._fh_key},
                        timeout=5,
                    )
                    data = resp.json()
                    price = data.get("c") or data.get("l")
                    if price and float(price) > 0:
                        price = float(price)
                        self._price_cache[sym] = (price, "finnhub_spot", fetched_at, now_ts)
                        return {"price": price, "source": "finnhub_spot", "fetched_at": fetched_at}
            except Exception as e:
                logger.warning(f"Finnhub price error for {symbol}: {e}")

        # ─── 3. yfinance fallback ─────────────────────────────────────────────
        try:
            if YFINANCE_AVAILABLE:
                yf_symbol = YFINANCE_MAP.get(sym, sym)
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period="1d", interval="1m")
                if hist is not None and len(hist) > 0:
                    price = float(hist["Close"].iloc[-1])
                    self._price_cache[sym] = (price, "yfinance", fetched_at, now_ts)
                    return {"price": price, "source": "yfinance", "fetched_at": fetched_at}
        except Exception as e:
            logger.warning(f"yfinance price error for {symbol}: {e}")

        return None

    def update_twelvedata_config(self, api_key: str, enabled: bool) -> None:
        """يُستدعى من لوحة الإدارة لتفعيل/تعطيل TwelveData بدون إعادة تشغيل"""
        self._td_runtime_key = api_key.strip()
        self._td_enabled     = enabled and bool(self._td_runtime_key)
        logger.info(f"TwelveData config updated: enabled={self._td_enabled}")
        # امسح الكاش لإجبار إعادة الجلب
        self._price_cache.clear()

    def _try_twelvedata_price(self, symbol: str) -> Optional[float]:
        """استخدام TwelveData فقط عند التفعيل الصريح من الإدارة"""
        if not (self._td_enabled and self._td_runtime_key):
            return None
        try:
            td_symbol = TWELVEDATA_MAP.get(symbol.upper(), symbol)
            resp = requests.get(
                f"{self.td_base}/price",
                params={"symbol": td_symbol, "apikey": self._td_runtime_key},
                timeout=5,
            )
            data = resp.json()
            if "price" in data:
                return float(data["price"])
        except Exception as e:
            logger.warning(f"TwelveData price error for {symbol}: {e}")
        return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """السعر الحالي (للتوافق مع الكود القديم)"""
        meta = self.get_realtime_price_with_meta(symbol)
        return meta["price"] if meta else None

    def is_market_open(self, symbol: str) -> bool:
        """
        فحص دقيق لحالة السوق:
        - كريبتو: مفتوح 24/7
        - فوركس/ذهب/نفط/مؤشرات: مغلق السبت كاملاً + الأحد حتى 22:00 UTC + الجمعة بعد 22:00 UTC
        """
        crypto = {"BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "BNBUSD"}
        if symbol.upper() in crypto:
            return True
        from datetime import timezone as _tz
        now = datetime.now(_tz.utc)
        wd  = now.weekday()   # 0=Mon … 4=Fri 5=Sat 6=Sun
        if wd == 5:                         # السبت كاملاً
            return False
        if wd == 4 and now.hour >= 22:      # الجمعة بعد 22:00 UTC
            return False
        if wd == 6 and now.hour < 22:       # الأحد قبل 22:00 UTC
            return False
        return True


# Singleton
smart_data = SmartDataProvider()
