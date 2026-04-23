"""
Mosh AI Pro v5 - Master AI Engine (Professional Edition v2)
===========================================================
يجمع:
- SmartDataProvider (yfinance + TwelveData)
- ICT Engine (Order Blocks, FVG, BOS, Liquidity, Wyckoff)
- Gemini AI v2 (Multi-Timeframe HTF+LTF + Position Sizing)
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from app.services.smart_data import smart_data
from app.services.ict_engine import ict_engine
from app.services.gemini_engine import gemini_engine
from app.config import get_settings

settings = get_settings()

# الحد الأقصى لفجوة السعر المسموحة بين current_price في التحليل والسعر الحي (بالدولار/النقطة)
# إذا تجاوز الفارق هذا الحد → التحليل مرفوض ويُعاد كـ WAIT
_MAX_PRICE_GAP_USD = {
    # الذهب يتحرك $20+ في ساعة — نرفض فقط إذا الفارق كبير جداً (>1% من السعر)
    # الغرض: اكتشاف انتهاء صلاحية الإشارة الكاملة، ليس التقلب الطبيعي
    "XAUUSD":  20.0,      # الذهب: $20 (~0.4% عند $4700)
    "XAGUSD":  0.60,      # الفضة
    "BTCUSD":  500.0,     # بيتكوين
    "ETHUSD":  30.0,
    "BNBUSD":  5.0,
    "SOLUSD":  3.0,
    "NAS100":  50.0,      # ناسداك
    "US30":    80.0,
    "SP500":   25.0,
    "USOIL":   0.60,
    "EURUSD":  0.0020,    # فوركس: ~20 pips
    "GBPUSD":  0.0025,
    "USDJPY":  0.35,
    "USDCHF":  0.0020,
    "AUDUSD":  0.0020,
    "USDCAD":  0.0020,
    "NZDUSD":  0.0020,
    "EURGBP":  0.0015,
    "EURJPY":  0.35,
    "GBPJPY":  0.45,
}

# مدة الكاش بالثواني
# منطق: الإطار 1h يعني الشمعة تدوم 60 دقيقة → لا فائدة من إعادة التحليل كل 10 دقائق
# TTL = ربع مدة الشمعة كحد أدنى لإعطاء وقت كافٍ لتشكّل الأنماط
_SIGNAL_CACHE_TTL = {
    "15m":   15 * 60,   # 15 دقيقة  (رُفع من 5  — توفير ~66% من calls الـ 15m)
    "30m":   30 * 60,   # 30 دقيقة  (رُفع من 10 — توفير ~66%)
    "1h":    60 * 60,   # ساعة كاملة (رُفع من 25 — توفير ~58%)
    "4h":   180 * 60,   # 3 ساعات   (رُفع من 50 — توفير ~72%)
    "1d":   480 * 60,   # 8 ساعات   (رُفع من 2  — يومي لا يتغير سريعاً)
}

# نسبة تغير السعر التي تُلغي الكاش — مُشدَّدة لمنع إرسال مستويات قديمة
_CACHE_PRICE_DRIFT = {
    "15m": 0.002,   # 0.2%
    "30m": 0.003,   # 0.3%
    "1h":  0.004,   # 0.4%
    "4h":  0.005,   # 0.5% (كان 1.5% — خُفِّض: $3000 ذهب × 0.5% = $15 فرق مقبول)
    "1d":  0.015,   # 1.5%
}


class MoshAIEngineV5:
    """
    المحرك الرئيسي الموحّد v2

    Pipeline:
    1. جلب البيانات: 4H (HTF) + 1H (LTF) بالتوازي
    2. ICT Analysis على كلا الإطارين
    3. Gemini AI v2: يرى HTF+LTF + يحسب Position Sizing
    4. القرار النهائي مع Weighted Scoring
    """

    def __init__(self):
        self.version = "5.2.0"
        # Signal cache: key → (analysis_dict, timestamp)
        self._signal_cache: Dict[str, tuple] = {}
        # Cooldown: key="{symbol}_{timeframe}" → last signal timestamp
        self._last_signal_time: Dict[str, float] = {}
        # Performance tracking (in-memory, resets on restart — DB is source of truth)
        self._perf: Dict[str, int] = {"wins": 0, "losses": 0}
        # Auto-calibration state: last signal timestamp per symbol (for silence detection)
        self._last_signal_issued: Dict[str, float] = {}
        logger.info(f"Mosh AI Engine v{self.version} initialized")
        logger.info(f"   Gemini v2: {'enabled' if gemini_engine.enabled else 'disabled'}")

    # ─── Cache ──────────────────────────────────────────────────────────────

    def _cache_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol.upper()}_{timeframe.lower()}"

    def _get_cached(self, symbol: str, timeframe: str, current_price: float = None) -> Optional[Dict]:
        key = self._cache_key(symbol, timeframe)
        if key not in self._signal_cache:
            return None
        data, ts = self._signal_cache[key]
        ttl = _SIGNAL_CACHE_TTL.get(timeframe, 1200)
        age = int(time.time() - ts)

        # انتهى TTL؟
        if age >= ttl:
            del self._signal_cache[key]
            return None

        # تغير السعر كثيراً؟ → ألغِ الكاش
        if current_price and data.get("current_price"):
            cached_price = float(data["current_price"])
            drift_limit = _CACHE_PRICE_DRIFT.get(timeframe, 0.008)
            drift = abs(current_price - cached_price) / cached_price
            if drift > drift_limit:
                logger.info(
                    f"🔄 Cache invalidated: {symbol}/{timeframe} "
                    f"سعر تغير {drift*100:.2f}% (حد: {drift_limit*100:.1f}%)"
                )
                del self._signal_cache[key]
                return None

        logger.info(f"📦 Signal cache hit: {symbol}/{timeframe} (عمره: {age}ث)")
        return dict(data)

    def _set_cached(self, symbol: str, timeframe: str, analysis: Dict):
        key = self._cache_key(symbol, timeframe)
        self._signal_cache[key] = (dict(analysis), time.time())

    def clear_cache(self, symbol: str = None, timeframe: str = None):
        if symbol and timeframe:
            self._signal_cache.pop(self._cache_key(symbol, timeframe), None)
        else:
            self._signal_cache.clear()
        logger.info(f"🗑️ Signal cache cleared: {symbol or 'ALL'}")

    # ─── Main Analysis ──────────────────────────────────────────────────────

    async def analyze_market(
        self,
        symbol: str,
        timeframe: str = "1h",
        advanced_mode: bool = True,
        force_refresh: bool = False,
        account_balance: float = 10000.0,
        max_risk_percent: float = 1.5,
    ) -> Dict:
        """
        التحليل الشامل للسوق v2 — HTF+LTF + Position Sizing

        Args:
            symbol: رمز السوق (XAUUSD, BTCUSD, EURUSD...)
            timeframe: الإطار الزمني LTF (1h, 4h...)
            force_refresh: تجاهل الكاش وإعادة التحليل
            account_balance: رأس مال الحساب لحساب حجم الصفقة
            max_risk_percent: نسبة المخاطرة القصوى
        """
        # ── الكاش: فحص أولي مع تحديث السعر الفوري دائماً ────────────────────
        if not force_refresh:
            # جلب السعر الحالي السريع للمقارنة مع الكاش
            live_price_meta = smart_data.get_realtime_price_with_meta(symbol)
            quick_price = live_price_meta["price"] if live_price_meta else None
            cached = self._get_cached(symbol, timeframe, current_price=quick_price)
            if cached is not None:
                # ⚡ تحديث السعر الحالي دائماً حتى من الكاش — هذا يمنع إظهار سعر قديم
                if quick_price:
                    cached["current_price"]    = quick_price
                    cached["price_source"]     = live_price_meta.get("source", "cached")
                    cached["price_fetched_at"] = live_price_meta.get("fetched_at", "")

                # تحقق: هل تجاوز السعر الحالي منطقة الدخول؟ → أبطل الكاش
                rec    = cached.get("recommendation")
                levels = cached.get("levels", {})
                entry  = float(levels.get("entry") or levels.get("entry_zone_max") or 0)
                if quick_price and entry and rec in ("BUY", "SELL"):
                    overshoot = (quick_price - entry) / entry
                    if (rec == "BUY"  and overshoot >  0.003) or \
                       (rec == "SELL" and overshoot < -0.003):
                        logger.info(
                            f"⚠️  Entry overshoot detected {symbol}/{timeframe}: "
                            f"current={quick_price:.5f} entry={entry:.5f} "
                            f"drift={overshoot*100:+.2f}% — إعادة التحليل"
                        )
                        self._signal_cache.pop(self._cache_key(symbol, timeframe), None)
                        # fall through to fresh analysis
                    else:
                        cached["from_cache"] = True
                        return cached
                else:
                    cached["from_cache"] = True
                    return cached

        logger.info(f"📊 Starting analysis v2: {symbol} / {timeframe}")
        start = datetime.now()

        try:
            # ── Step 1: جلب LTF + HTF بالتوازي ─────────────────────────────
            htf_timeframe = "4h" if timeframe in ("1h", "15m", "30m") else "1d"

            df_ltf, df_htf = await asyncio.gather(
                smart_data.get_ohlcv(symbol, timeframe, bars=150),
                smart_data.get_ohlcv(symbol, htf_timeframe, bars=100),
            )

            if df_ltf is None or len(df_ltf) < 30:
                logger.error(f"❌ No LTF data for {symbol}")
                return self._error_response(symbol, "لا توجد بيانات كافية")

            logger.info(
                f"   ✅ LTF ({timeframe}): {len(df_ltf)} bars, "
                f"price={df_ltf['close'].iloc[-1]:.5f}"
            )
            if df_htf is not None:
                logger.info(f"   ✅ HTF ({htf_timeframe}): {len(df_htf)} bars")

            # ── Step 2: ICT Analysis على LTF + HTF ──────────────────────────
            ltf_analysis = ict_engine.full_analysis(df_ltf, symbol, timeframe)

            htf_analysis = None
            if df_htf is not None and len(df_htf) >= 30:
                htf_analysis = ict_engine.full_analysis(df_htf, symbol, htf_timeframe)

            if "error" in ltf_analysis:
                return self._error_response(symbol, ltf_analysis["error"])

            # ── Step 3: Gemini — Arabic summary ONLY (NO direction, NO levels) ─
            # ICT Engine is the SOLE source of direction and trade levels.
            # Gemini is used only to enrich the text output for the user.
            if gemini_engine.enabled:
                try:
                    gemini_result = await gemini_engine.analyze(
                        symbol=symbol,
                        timeframe=timeframe,
                        ltf_data=ltf_analysis,
                        df=df_ltf,
                        htf_data=htf_analysis,
                        account_balance=account_balance,
                        max_risk_percent=max_risk_percent,
                    )
                    if gemini_result:
                        # فقط النص والتأكيدات — لا نغير الاتجاه أو المستويات
                        ltf_analysis["gemini_analysis"] = {
                            "enabled":        True,
                            "arabic_summary": gemini_result.get("arabic_summary", ""),
                            "confirmations":  gemini_result.get("confirmations", []),
                            "warnings":       gemini_result.get("warnings", []),
                            "signal_grade":   gemini_result.get("signal", {}).get("signal_grade", ""),
                        }
                        logger.info(
                            f"   AI summary: {gemini_result.get('arabic_summary', '')[:60]}"
                        )
                except Exception as e:
                    logger.warning(f"   Gemini summary failed (ICT-only mode): {e}")

            # ── Step 4: Final formatting ─────────────────────────────────────
            ms = (datetime.now() - start).total_seconds() * 1000
            analysis = ltf_analysis
            analysis["processing_time_ms"] = int(ms)
            analysis["version"] = self.version
            analysis["market_open"] = smart_data.is_market_open(symbol)
            analysis["htf_timeframe"] = htf_timeframe

            # HTF context للمنصة والبوت
            if htf_analysis:
                analysis["htf_context"] = {
                    "timeframe": htf_timeframe,
                    "trend": htf_analysis.get("market_structure", {}).get("trend", "UNKNOWN"),
                    "structure": htf_analysis.get("market_structure", {}).get("structure", "UNKNOWN"),
                    "premium_discount": htf_analysis.get("premium_discount", {}).get("zone", "UNKNOWN"),
                    "wyckoff_phase": htf_analysis.get("wyckoff", {}).get("phase", "UNKNOWN"),
                }

            # توافق مع API القديم
            analysis["trend"] = {
                "direction": analysis.get("market_structure", {}).get("trend", "RANGING"),
                "strength": analysis.get("ai_confidence_score", 0),
                "htf_trend": analysis.get("htf_context", {}).get("trend", "UNKNOWN"),
            }

            # ── نسخ بيانات السياق من ICT إلى Analysis ───────────────────────
            if "market_mode"    not in analysis: analysis["market_mode"]    = ltf_analysis.get("market_mode", {})
            if "momentum"       not in analysis: analysis["momentum"]       = ltf_analysis.get("momentum", {})
            if "range_conflict" not in analysis: analysis["range_conflict"] = ltf_analysis.get("range_conflict", {})

            # ── AUTO CALIBRATION — adapts thresholds to market + performance ──
            analysis = self._auto_calibrate_thresholds(analysis, symbol, timeframe)

            # ── DECISION FINALIZER — resolves conflicts → BUY/SELL/NO TRADE ──
            analysis = self._decision_finalizer(analysis, symbol, timeframe, htf_analysis)

            # ── INSTITUTIONAL GATE — validates levels if decision was made ────
            if analysis.get("recommendation") in ("BUY", "SELL"):
                analysis = self._institutional_gate(analysis, symbol, timeframe, htf_analysis)
                # Record this signal for silence tracker
                if analysis.get("institutional_gate_passed"):
                    self._record_signal_issued(symbol, timeframe)

            # ── EXPLAINABILITY LAYER — audit-grade trace (runs last, no changes)
            analysis = self._explainability_layer(analysis, symbol, timeframe, htf_analysis)

            # ── NORMALIZE OUTPUT LAYER — unified schema for API/Bot/Dashboard
            analysis = self._normalize_output_layer(analysis, symbol, timeframe)

            rec  = analysis.get("recommendation", "WAIT")
            conf = analysis.get("ai_confidence_score", 0)
            logger.success(f"✅ {symbol}/{timeframe}: {rec} | {conf}% | {int(ms)}ms")

            # ── السعر الفوري + تصحيح Futures→Spot للمعادن والعقود الآجلة ──
            try:
                rt_price = smart_data.get_realtime_price_with_meta(symbol)
                if rt_price:
                    analysis["current_price"]    = rt_price["price"]
                    analysis["price_source"]     = rt_price["source"]
                    analysis["price_fetched_at"] = rt_price["fetched_at"]
                    logger.info(f"   💱 Live price [{rt_price['source']}]: {rt_price['price']}")

                    # ── تصحيح Futures-Spot لأسواق المعادن والعقود ──────────
                    # المشكلة: مستويات ICT محسوبة من بيانات GC=F (Futures)
                    # بينما المتداول يرى سعر XAUUSD Spot في MT4/MT5
                    # الحل: جلب Spot من Finnhub وتطبيق الفارق على كل المستويات
                    analysis = self._apply_spot_basis(symbol, analysis)

                    # ── حارس جودة السعر: رفض أي إشارة يختلف سعرها > الحد ──
                    analysis = self._validate_price_freshness(symbol, analysis)

            except Exception as _pe:
                logger.warning(f"   ⚠️ Could not fetch live price: {_pe}")

            # ── [PRICE SOURCE] log — يساعد في مقارنة Telegram vs Chat ────────
            logger.info(
                f"[PRICE SOURCE] {symbol}/{timeframe}: "
                f"price={analysis.get('current_price', 0):.5f}  "
                f"source={analysis.get('price_source', 'unknown')}  "
                f"rec={analysis.get('recommendation', 'WAIT')}"
            )

            # ── حفظ في الكاش ─────────────────────────────────────────────
            analysis["from_cache"] = False
            analysis["cached_at"] = datetime.now().isoformat()
            analysis["cache_ttl_seconds"] = _SIGNAL_CACHE_TTL.get(timeframe, 1800)
            self._set_cached(symbol, timeframe, analysis)

            return analysis

        except Exception as e:
            logger.error(f"❌ Engine error for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(symbol, str(e))

    # الأسواق التي تستخدم Futures في yfinance (GC=F, SI=F ...)
    _FUTURES_SPOT_SYMBOLS = {"XAUUSD", "XAGUSD"}

    def _fetch_spot_price(self, symbol: str) -> tuple[float, str]:
        """
        يجلب سعر Spot الفوري للمعادن — 5 مصادر بالتسلسل:
          0. TradingView WebSocket  (OANDA Spot — أدق مصدر، لحظي)
          1. yfinance XAUUSD=X / XAGUSD=X (Spot مباشر — بدون حساب basis)
          2. yfinance GC=F theoretical carry basis (احتياطي — أقل دقة)
          3. @fawazahmed0/currency-api CDN  (مجاني، قد يتأخر 24h)
          4. Finnhub quote (fallback أخير)
        يُعيد (0.0, "none") إذا فشل الكل (يُتجاوز التصحيح بأمان).
        """
        import requests as _req
        sym_upper = symbol.upper()

        # رمز XAU في currency-api و yfinance futures
        _CURRENCY_API_SYM = {"XAUUSD": "xau", "XAGUSD": "xag"}
        _FUTURES_SYM      = {"XAUUSD": "GC=F", "XAGUSD": "SI=F"}

        # ── 0. TradingView WebSocket (OANDA Spot — الأدق والأسرع) ───────────
        try:
            from app.services.tv_price_feed import tv_feed
            tv_price = tv_feed.get_price_sync(sym_upper)
            if tv_price and float(tv_price) > 0:
                logger.info(f"   💰 TV spot [{sym_upper}]: {tv_price:.5f}")
                return float(tv_price), "tv_spot"
            else:
                logger.info(f"   📡 TV spot None for [{sym_upper}] (alive={tv_feed.is_alive()}) — falling to yfinance spot")
        except Exception as _tv_e:
            logger.info(f"   TV spot unavailable [{sym_upper}]: {_tv_e}")

        # ── 1. yfinance XAUUSD=X / XAGUSD=X — سعر Spot مباشر (بدون basis) ─
        _YF_SPOT_SYM = {"XAUUSD": "XAUUSD=X", "XAGUSD": "XAGUSD=X"}
        yf_spot_sym = _YF_SPOT_SYM.get(sym_upper)
        if yf_spot_sym:
            try:
                import yfinance as _yf
                ticker = _yf.Ticker(yf_spot_sym)
                hist = ticker.history(period="1d", interval="1m")
                if hist is not None and len(hist) > 0:
                    price = float(hist["Close"].iloc[-1])
                    if price > 0:
                        logger.info(f"   💰 yfinance spot [{sym_upper}]: {price:.5f}")
                        return round(price, 5), "yfinance_spot"
                # fallback: .info
                info = ticker.info
                price = info.get("regularMarketPrice") or info.get("previousClose")
                if price and float(price) > 0:
                    logger.info(f"   💰 yfinance spot info [{sym_upper}]: {price:.5f}")
                    return round(float(price), 5), "yfinance_spot"
            except Exception as _ye:
                logger.debug(f"   yfinance spot failed [{sym_upper}]: {_ye}")

        # ── 2. yfinance: Spot من Futures - theoretical carry basis ──────────
        # احتياطي فقط — قد يكون غير دقيق إذا تغيرت أسعار الفائدة
        futures_sym = _FUTURES_SYM.get(sym_upper)
        if futures_sym:
            try:
                import yfinance as _yf, time as _time
                ticker = _yf.Ticker(futures_sym)
                info = ticker.info
                futures_price = info.get("regularMarketPrice") or info.get("previousClose")
                expire_ts     = info.get("expireDate")  # Unix timestamp
                if futures_price and expire_ts:
                    days = max(1, (expire_ts - _time.time()) / 86400)
                    rate = 0.0525  # US risk-free rate 2026
                    basis = futures_price * rate * (days / 365)
                    spot  = round(futures_price - basis, 5)
                    logger.debug(
                        f"   💰 theoretical spot [{sym_upper}]: futures={futures_price:.2f} "
                        f"days={days:.0f} basis={basis:.2f} → spot={spot:.2f}"
                    )
                    return spot, "theoretical_carry"
            except Exception as _ye:
                logger.debug(f"   theoretical basis failed [{sym_upper}]: {_ye}")

        # ── 3. @fawazahmed0/currency-api CDN (backup — قد يكون متأخر 24h) ─
        currency_sym = _CURRENCY_API_SYM.get(sym_upper)
        if currency_sym:
            for url in [
                f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{currency_sym}.json",
                f"https://latest.currency-api.pages.dev/v1/currencies/{currency_sym}.json",
            ]:
                try:
                    resp = _req.get(url, timeout=5)
                    if resp.status_code == 200:
                        usd = resp.json().get(currency_sym, {}).get("usd")
                        if usd and float(usd) > 0:
                            logger.debug(f"   💰 currency-api spot [{sym_upper}]: {usd:.5f}")
                            return float(usd), "currency_api"
                except Exception:
                    continue

        # ── 4. Finnhub fallback ───────────────────────────────────────────
        if smart_data._fh_key:
            try:
                from app.services.smart_data import FINNHUB_MAP
                fh_sym = FINNHUB_MAP.get(sym_upper)
                if fh_sym:
                    resp = _req.get(
                        f"{smart_data._fh_base}/quote",
                        params={"symbol": fh_sym, "token": smart_data._fh_key},
                        timeout=4,
                    )
                    data = resp.json()
                    price = data.get("c")
                    if not price or float(price) <= 0:
                        price = data.get("l")
                    if price and float(price) > 0:
                        logger.debug(f"   💰 Finnhub spot [{fh_sym}]: {price:.5f}")
                        return float(price), "finnhub_spot"
            except Exception as _fe:
                logger.debug(f"   Finnhub spot failed: {_fe}")

        logger.warning(f"   ⚠️  _fetch_spot_price: all sources failed for {symbol}")
        return 0.0, "none"

    def _apply_spot_basis(self, symbol: str, analysis: dict) -> dict:
        """
        يُصحِّح فارق Futures-Spot لأسواق المعادن.
        GC=F (ذهب futures) دائماً أعلى من XAUUSD spot بـ $10-60.
        نطرح هذا الفارق من كل المستويات ليتطابق مع ما يراه المتداول في MT4/MT5.

        ملاحظة: current_price قد يكون TV Spot (إذا نجح get_realtime_price_with_meta)
        أو GC=F Futures. في كلتا الحالتين نجلب GC=F مباشرة كمرجع لحساب الفارق
        لأن ICT candles دائماً من GC=F.
        """
        if symbol.upper() not in self._FUTURES_SPOT_SYMBOLS:
            return analysis

        try:
            spot, spot_source = self._fetch_spot_price(symbol)
            if spot <= 0:
                return analysis

            # ── جلب سعر Futures مباشرة (GC=F) كمرجع ثابت ──────────────────
            # لا نستخدم current_price لأنه قد يكون TV Spot بالفعل
            _FUTURES_SYM = {"XAUUSD": "GC=F", "XAGUSD": "SI=F"}
            futures_sym = _FUTURES_SYM.get(symbol.upper())
            futures = 0.0
            if futures_sym:
                try:
                    import yfinance as _yf
                    _info = _yf.Ticker(futures_sym).info
                    futures = float(_info.get("regularMarketPrice") or _info.get("previousClose") or 0)
                except Exception:
                    pass
            # fallback: إذا فشل yfinance استخدم current_price إذا كان أكبر من spot
            if futures <= 0:
                cp = float(analysis.get("current_price") or 0)
                futures = cp if cp > spot else 0.0
            if futures <= 0:
                return analysis

            # احفظ السعر الفوري ومصدره ليُعادا استخدامهما في _validate_price_freshness
            analysis["_cached_spot_price"]  = spot
            analysis["_cached_spot_source"] = spot_source

            basis = spot - futures  # عادةً سالب: spot أقل من futures

            # sanity check: الفارق يجب أن يكون معقولاً (0.01% – 4%)
            ratio = abs(basis) / futures
            if ratio < 0.0001 or ratio > 0.04:
                logger.info(f"   ⚠️  Basis out of range for {symbol}: {basis:+.2f} ({ratio*100:.2f}%) — skipped")
                # تصحيح current_price على الأقل
                analysis["current_price"] = round(spot, 5)
                analysis["price_source"]  = spot_source
                analysis["_cached_spot_price"]  = spot
                analysis["_cached_spot_source"] = spot_source
                return analysis

            logger.info(f"   🔧 Spot-Futures basis [{symbol}]: {basis:+.2f}  (futures={futures:.2f} → spot={spot:.2f})")

            # ── تطبيق الفارق على current_price ───────────────────────────
            analysis["current_price"]  = round(spot, 5)
            analysis["price_source"]   = spot_source   # tv_spot / theoretical_carry / etc.
            analysis["futures_basis"]  = round(basis, 2)

            def _shift(v):
                return round(float(v) + basis, 5) if v else v

            # ── المستويات الرئيسية (levels dict) ─────────────────────────
            lvls = analysis.get("levels", {})
            for k in ("entry", "entry_zone_min", "entry_zone_max", "stop_loss", "tp1", "tp2"):
                if lvls.get(k):
                    lvls[k] = _shift(lvls[k])

            # ── entry_zones / stop_loss_zone / take_profit_zones (legacy) ─
            if analysis.get("entry_zones"):
                analysis["entry_zones"] = [_shift(z) for z in analysis["entry_zones"] if z]
            if analysis.get("stop_loss_zone"):
                analysis["stop_loss_zone"] = _shift(analysis["stop_loss_zone"])
            if analysis.get("take_profit_zones"):
                analysis["take_profit_zones"] = [_shift(z) for z in analysis["take_profit_zones"] if z]

            # ── Order Blocks ──────────────────────────────────────────────
            ob = analysis.get("order_blocks", {})
            for ob_list in (ob.get("bullish_obs", []), ob.get("bearish_obs", [])):
                for o in ob_list:
                    if isinstance(o, dict):
                        for k in ("low", "high", "mid"):
                            if o.get(k):
                                o[k] = _shift(o[k])

            # ── Liquidity levels ──────────────────────────────────────────
            liq = analysis.get("liquidity_analysis") or analysis.get("liquidity") or {}
            if isinstance(liq, dict):
                for k in ("nearest_ssl", "nearest_bsl"):
                    if liq.get(k):
                        liq[k] = _shift(liq[k])
                bias = liq.get("bias", {})
                if isinstance(bias, dict):
                    for k in ("below_price", "above_price"):
                        if bias.get(k):
                            bias[k] = _shift(bias[k])

        except Exception as e:
            logger.warning(f"   ⚠️  _apply_spot_basis failed for {symbol}: {e}")

        return analysis

    def _validate_price_freshness(self, symbol: str, analysis: dict) -> dict:
        """
        ✅ حارس جودة السعر (Price Freshness Guard)
        ─────────────────────────────────────────
        بعد كل التحليل وتصحيح Futures-Spot، نجلب السعر الحي مرة أخيرة
        ونتأكد أن current_price لا يختلف عن السوق الفعلي بأكثر من الحد المسموح.

        ⚠️ تنبيه مهم للمعادن (XAUUSD/XAGUSD):
        - بعد _apply_spot_basis، صار current_price = سعر Spot (Finnhub ≈ 4641)
        - لكن get_realtime_price_with_meta يُعيد GC=F Futures (≈ 4661)
        - لذلك يجب مقارنة current_price بـ Finnhub Spot وليس yfinance

        إذا كان الفارق > _MAX_PRICE_GAP_USD[symbol]:
          • نُحدِّث current_price بالسعر الصحيح
          • نرفض الإشارة (WAIT) ونمسح المستويات
          • نحذف الكاش لإجبار إعادة التحليل في الطلب القادم
          • نرسل رسالة واضحة للمستخدم بسبب الرفض
        """
        sym_upper = symbol.upper()

        # ── للمعادن: نستخدم الـ spot المحفوظ من _apply_spot_basis (لا نجلبه مرة ثانية) ──
        # استدعاء _fetch_spot_price مرتين يُسبب تفاوتاً في الأسعار → رفض زائف
        if sym_upper in self._FUTURES_SPOT_SYMBOLS:
            live_price  = analysis.pop("_cached_spot_price", 0)
            live_source = analysis.pop("_cached_spot_source", "spot")
            if not live_price:
                live_price, live_source = self._fetch_spot_price(sym_upper)
            if live_price <= 0:
                return analysis  # لا يمكن التحقق — نتجاوز الفحص
        else:
            # ── للبقية: نجلب السعر الحي العادي ──────────────────────────────
            live_meta = smart_data.get_realtime_price_with_meta(symbol)
            if not live_meta:
                return analysis
            live_price = float(live_meta["price"])
            live_source = live_meta.get("source", "live")

        if live_price <= 0:
            return analysis

        analysis_price = float(analysis.get("current_price") or 0)
        if analysis_price <= 0:
            # لا يوجد سعر في التحليل — نضع السعر الحي
            analysis["current_price"] = live_price
            return analysis

        max_gap = _MAX_PRICE_GAP_USD.get(symbol.upper(), live_price * 0.003)  # 0.3% fallback
        gap = abs(analysis_price - live_price)

        if gap > max_gap:
            logger.warning(
                f"⛔ Price freshness REJECTED [{symbol}]: "
                f"analysis_price={analysis_price:.5f}  live={live_price:.5f}  "
                f"gap={gap:.5f} > max_allowed={max_gap:.5f}"
            )
            # ── تصحيح السعر ───────────────────────────────────────────────
            analysis["current_price"] = live_price
            analysis["price_source"]  = live_source

            # ── رفض الإشارة ───────────────────────────────────────────────
            analysis["recommendation"]   = "WAIT"
            analysis["signal_type"]      = "WAIT"
            analysis["price_gap_rejected"] = True
            analysis["price_gap_value"]    = round(gap, 5)
            analysis["price_gap_max"]      = round(max_gap, 5)
            analysis["rejection_reason"] = (
                f"⚠️ تم رفض الإشارة: السعر في التحليل ({analysis_price:.2f}) "
                f"يختلف عن السوق الفعلي ({live_price:.2f}) "
                f"بمقدار {gap:.2f} — الحد المسموح {max_gap:.2f}.\n"
                f"أعد طلب التحليل للحصول على إشارة محدّثة."
            )

            # ── مسح المستويات (لا نعرض entry/SL/TP خاطئة) ────────────────
            analysis["levels"]          = {}
            analysis["entry_zones"]     = []
            analysis["stop_loss_zone"]  = None
            analysis["take_profit_zones"] = []

            # ── حذف الكاش → سيُعاد التحليل في الطلب القادم ───────────────
            cache_key = self._cache_key(symbol, analysis.get("timeframe", "1h"))
            self._signal_cache.pop(cache_key, None)
            logger.info(f"   🗑️  Cache cleared for {cache_key} — will re-analyze next request")
        else:
            # السعر سليم — نحدّث بالأحدث
            analysis["current_price"] = live_price
            analysis["price_source"]  = live_source

        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # AUTO CALIBRATION ENGINE — Adapts thresholds to market + performance
    # "Adapt thresholds — not logic"
    # ═══════════════════════════════════════════════════════════════════════

    # Hard limits — never exceeded regardless of market conditions
    _CALIB_DELTA_MIN      = 20
    _CALIB_DELTA_MAX      = 35
    _CALIB_RR_MIN         = 1.2
    _CALIB_RR_MAX         = 2.0
    _CALIB_TOL_MIN        = 0.0025   # 0.25%
    _CALIB_TOL_MAX        = 0.0060   # 0.60%
    _CALIB_COOLDOWN_MIN   = 3600     # 1 hour
    _CALIB_COOLDOWN_MAX   = 14400    # 4 hours
    _CALIB_SILENCE_HOURS  = 6        # silence window that triggers relaxed delta

    def _auto_calibrate_thresholds(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
    ) -> dict:
        """
        Auto Calibration Engine.
        Runs BEFORE _decision_finalizer — adjusts thresholds only.
        NEVER changes: entry/SL/TP values, trade direction logic,
        or institutional gate hard rules.
        """
        import time as _t

        # ── 1. Read market state from ICT output ─────────────────────────────
        market_mode    = analysis.get("market_mode", {})
        struct         = analysis.get("market_structure", {})
        raw_trend      = str(struct.get("trend", "RANGING")).upper()
        raw_mode       = str(market_mode.get("mode", "")).upper()
        atr            = float((analysis.get("levels") or {}).get("atr") or 0)
        current_price  = float(analysis.get("current_price") or 1)

        # ── Determine market_state ────────────────────────────────────────────
        if raw_mode in ("VOLATILE", "BREAKOUT"):
            market_state = "VOLATILE"
        elif raw_trend in ("BULLISH", "BEARISH") or raw_mode in ("TRENDING", "TREND"):
            market_state = "TRENDING"
        else:
            market_state = "RANGING"

        # ── Determine volatility from ATR ─────────────────────────────────────
        # ATR as % of price
        atr_pct = (atr / current_price) if current_price > 0 else 0
        if atr_pct == 0:
            volatility = "NORMAL"
        elif atr_pct < 0.003:
            volatility = "LOW"
        elif atr_pct > 0.010:
            volatility = "HIGH"
        else:
            volatility = "NORMAL"

        # ── 2. Dynamic score delta ────────────────────────────────────────────
        if market_state == "TRENDING":
            required_delta = 20
        elif market_state == "RANGING":
            required_delta = 25
        else:  # VOLATILE
            required_delta = 30

        # ── 3. Dynamic min RR (based on winrate) ──────────────────────────────
        wr = self.get_winrate()
        if wr < 0.40:
            min_rr = 1.6
        elif wr < 0.55:
            min_rr = 1.4
        else:
            min_rr = 1.2

        # ── 4. Sweep confirmation requirement ────────────────────────────────
        require_sweep_confirmation = (market_state == "TRENDING")

        # ── 5. Entry tolerance ────────────────────────────────────────────────
        if volatility == "LOW":
            entry_tolerance = 0.0050   # 0.50% — wider in calm market
        elif volatility == "HIGH":
            entry_tolerance = 0.0025   # 0.25% — tighter in chaotic market
        else:
            entry_tolerance = 0.0030   # 0.30% normal

        # ── 6. Cooldown adjustment ────────────────────────────────────────────
        if market_state == "RANGING":
            cooldown_hours = 1
        elif market_state == "TRENDING":
            cooldown_hours = 2
        else:  # VOLATILE
            cooldown_hours = 2
        cooldown_sec = cooldown_hours * 3600

        # ── 7. Fallback: silence > 6h → relax delta once ─────────────────────
        silence_key   = f"{symbol.upper()}_{timeframe}"
        last_issued   = self._last_signal_issued.get(silence_key, 0)
        silence_hours = (_t.time() - last_issued) / 3600 if last_issued > 0 else 0
        silence_relaxed = False
        if silence_hours >= self._CALIB_SILENCE_HOURS:
            required_delta = max(required_delta - 5, self._CALIB_DELTA_MIN)
            silence_relaxed = True

        # ── 8. Apply hard limits (clamp) ──────────────────────────────────────
        required_delta  = max(self._CALIB_DELTA_MIN,    min(self._CALIB_DELTA_MAX,    required_delta))
        min_rr          = max(self._CALIB_RR_MIN,       min(self._CALIB_RR_MAX,       min_rr))
        entry_tolerance = max(self._CALIB_TOL_MIN,      min(self._CALIB_TOL_MAX,      entry_tolerance))
        cooldown_sec    = max(self._CALIB_COOLDOWN_MIN, min(self._CALIB_COOLDOWN_MAX, cooldown_sec))

        # ── 9. Apply calibrated values ────────────────────────────────────────
        # Score delta → read by _decision_finalizer via calibration_params
        # Min RR / tolerance → read by _institutional_gate via same dict
        calibration = {
            "market_state":               market_state,
            "volatility":                 volatility,
            "winrate":                    round(wr, 3),
            "delta":                      required_delta,
            "min_rr":                     round(min_rr, 2),
            "entry_tolerance":            round(entry_tolerance * 100, 3),  # store as %
            "entry_tolerance_raw":        entry_tolerance,
            "cooldown_sec":               cooldown_sec,
            "require_sweep_confirmation": require_sweep_confirmation,
            "silence_hours":              round(silence_hours, 1),
            "silence_relaxed":            silence_relaxed,
            "reason": (
                f"{market_state} + {volatility} volatility"
                + (" | silence relaxed" if silence_relaxed else "")
                + f" | winrate={wr:.0%}"
            ),
        }
        analysis["calibration_params"] = calibration

        # Also inject directly into _ENTRY_TOLERANCE for this call
        # (per-symbol/timeframe override — does NOT mutate class-level dict permanently)
        analysis["_calib_entry_tol"]   = entry_tolerance
        analysis["_calib_min_rr"]      = min_rr
        analysis["_calib_delta"]       = required_delta
        analysis["_calib_cooldown"]    = cooldown_sec
        analysis["_calib_req_sweep"]   = require_sweep_confirmation

        logger.info(
            f"CALIBRATE [{symbol}/{timeframe}] "
            f"state={market_state} vol={volatility} "
            f"Δ={required_delta} RR≥{min_rr} tol={entry_tolerance*100:.2f}% "
            f"cooldown={cooldown_hours}h"
            + (f" [SILENCE {silence_hours:.1f}h → delta relaxed]" if silence_relaxed else "")
        )
        return analysis

    def _record_signal_issued(self, symbol: str, timeframe: str):
        """Called when a BUY/SELL passes all gates — updates silence tracker."""
        self._last_signal_issued[f"{symbol.upper()}_{timeframe}"] = time.time()

    # ═══════════════════════════════════════════════════════════════════════
    # EXPLAINABILITY LAYER — Audit-grade trace for every decision
    # "No trade is valid without a traceable reason"
    # ═══════════════════════════════════════════════════════════════════════

    def _explainability_layer(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        Institutional Explainability Layer.
        Runs AFTER _decision_finalizer + _institutional_gate.
        Does NOT change any decision — only builds reason_trace.

        Produces audit-grade output:
          WHY this trade exists + WHY the other side was rejected.
        """
        decision = analysis.get("recommendation", "WAIT")
        meta     = analysis.get("decision_meta", {})
        struct   = analysis.get("market_structure", {})
        sweep    = analysis.get("liquidity_sweep", {})
        ob       = analysis.get("order_blocks", {})
        pd_zone  = analysis.get("premium_discount", {})
        levels   = analysis.get("levels", {})

        # ── Score breakdown ──────────────────────────────────────────────
        bull_score      = float(meta.get("bull_score") or analysis.get("confluence", {}).get("bull_score") or 0)
        bear_score      = float(meta.get("bear_score") or analysis.get("confluence", {}).get("bear_score") or 0)
        delta           = float(meta.get("score_delta") or (bull_score - bear_score))
        threshold       = float(meta.get("threshold") or self._DECISION_THRESHOLD_TREND)
        structure_bias  = meta.get("structure_bias")
        htf_bias        = meta.get("htf_bias")
        liq_bias        = meta.get("liq_bias")
        zone_bias       = meta.get("zone_bias")
        is_ranging      = bool(meta.get("is_ranging", False))

        # ── 1. Market Structure trace ────────────────────────────────────
        trend        = struct.get("trend", "UNKNOWN")
        bos_events   = struct.get("bos_events", [])
        choch_events = struct.get("choch_events", [])
        bull_bos     = sum(1 for b in bos_events if "BULLISH" in b.get("type", ""))
        bear_bos     = sum(1 for b in bos_events if "BEARISH" in b.get("type", ""))

        ms_parts = [
            f"Trend: {trend}",
            f"BOS: {len(bos_events)} (Bullish×{bull_bos} Bearish×{bear_bos})",
            f"CHoCH: {len(choch_events)} events",
        ]
        if choch_events:
            last_c = choch_events[-1] if isinstance(choch_events[-1], dict) else {}
            ms_parts.append(
                f"Last CHoCH → {last_c.get('type','?')} @ {float(last_c.get('price', 0)):.5f}"
            )
        if bos_events:
            last_b = bos_events[-1] if isinstance(bos_events[-1], dict) else {}
            ms_parts.append(
                f"Last BOS → {last_b.get('type','?')} @ {float(last_b.get('price', 0)):.5f}"
            )
        if structure_bias:
            ms_parts.append(f"Structure Bias → {structure_bias}")
        ms_trace = " | ".join(ms_parts)

        # ── 2. Liquidity trace ───────────────────────────────────────────
        has_bull_sweep = sweep.get("has_bullish_sweep", False)
        has_bear_sweep = sweep.get("has_bearish_sweep", False)
        sq             = sweep.get("sweep_quality", "NONE")
        ssl_info       = sweep.get("ssl_sweep") or {}
        bsl_info       = sweep.get("bsl_sweep") or {}
        has_bos        = bool(bos_events)
        has_choch      = bool(choch_events)

        liq_parts = []
        if has_bull_sweep:
            liq_parts.append(
                f"SSL Stop Hunt CONFIRMED (quality={sq}) "
                f"{ssl_info.get('candles_since','?')}c ago "
                f"wick={ssl_info.get('wick_atr_ratio','?')}×ATR → BULLISH footprint"
            )
        elif ssl_info:
            liq_parts.append("SSL swept — rejection NOT confirmed (weak bullish)")
        if has_bear_sweep:
            liq_parts.append(
                f"BSL Stop Hunt CONFIRMED (quality={sq}) "
                f"{bsl_info.get('candles_since','?')}c ago "
                f"wick={bsl_info.get('wick_atr_ratio','?')}×ATR → BEARISH footprint"
            )
        elif bsl_info:
            liq_parts.append("BSL swept — rejection NOT confirmed (weak bearish)")
        if not liq_parts:
            liq_parts.append("No sweep detected — entry based on OB/zone only")
        liq_trace = " | ".join(liq_parts)

        # ── 3. Order Block trace ─────────────────────────────────────────
        primary_bull  = analysis.get("primary_bull_ob")
        primary_bear  = analysis.get("primary_bear_ob")
        all_bull_obs  = ob.get("bullish_obs", [])
        all_bear_obs  = ob.get("bearish_obs", [])

        ob_parts = []
        if primary_bull:
            n_rejected = max(0, len(all_bull_obs) - 1)
            ob_parts.append(
                f"Primary Bullish OB: {float(primary_bull.get('low',0)):.5f}–"
                f"{float(primary_bull.get('high',0)):.5f} "
                f"(closest of {len(all_bull_obs)}"
                + (f", {n_rejected} others discarded" if n_rejected else "") + ")"
            )
        else:
            ob_parts.append("No bullish OB available")
        if primary_bear:
            n_rejected = max(0, len(all_bear_obs) - 1)
            ob_parts.append(
                f"Primary Bearish OB: {float(primary_bear.get('low',0)):.5f}–"
                f"{float(primary_bear.get('high',0)):.5f} "
                f"(closest of {len(all_bear_obs)}"
                + (f", {n_rejected} others discarded" if n_rejected else "") + ")"
            )
        else:
            ob_parts.append("No bearish OB available")
        ob_trace = " | ".join(ob_parts)

        # ── 4. Zone Logic trace ──────────────────────────────────────────
        pd_name    = pd_zone.get("zone", "UNKNOWN")
        pd_pct     = float(pd_zone.get("pct") or 0)
        pd_raw     = pd_zone.get("bias", "NEUTRAL")
        zone_parts = [f"Zone: {pd_name} ({pd_pct:.1f}% of range) | P/D Bias: {pd_raw}"]

        if decision == "BUY":
            if zone_bias == "BUY":
                zone_parts.append("ALIGNED: BUY from discount/support zone")
            elif zone_bias == "SELL":
                zone_parts.append("CONFLICT: BUY in premium zone — allowed only by strong delta override")
        elif decision == "SELL":
            if zone_bias == "SELL":
                zone_parts.append("ALIGNED: SELL from premium/resistance zone")
            elif zone_bias == "BUY":
                zone_parts.append("CONFLICT: SELL in discount zone — allowed only by strong delta override")
        zone_trace = " | ".join(zone_parts)

        # ── 5. Stop Hunt trace ───────────────────────────────────────────
        if has_bull_sweep or has_bear_sweep:
            sweep_type = "SSL" if has_bull_sweep else "BSL"
            if has_bos or has_choch:
                sh_trace = (
                    f"{sweep_type} Stop Hunt CONFIRMED + structure shift present "
                    f"(BOS={has_bos} CHoCH={has_choch}) — VALID trigger"
                )
            else:
                sh_trace = (
                    f"{sweep_type} sweep detected BUT no BOS/CHoCH — "
                    "REJECTED as trigger (sweep without structure shift)"
                )
        else:
            sh_trace = "No stop hunt — entry driven by OB/zone confluence"

        # ── 6. Conflict detection ────────────────────────────────────────
        conflicts = []
        if structure_bias and htf_bias and structure_bias != htf_bias:
            conflicts.append(
                f"LTF Structure ({structure_bias}) ≠ HTF Trend ({htf_bias}) "
                "→ resolved: Priority 1 (Structure)"
            )
        if structure_bias and zone_bias and structure_bias != zone_bias:
            conflicts.append(
                f"Structure ({structure_bias}) ≠ Zone ({zone_bias}) "
                "→ resolved: Priority 1 (Structure over Zone)"
            )
        if liq_bias and structure_bias and liq_bias != structure_bias:
            conflicts.append(
                f"Liquidity ({liq_bias}) ≠ Structure ({structure_bias}) "
                "→ resolved: Priority 1 (Structure)"
            )
        if decision == "BUY" and zone_bias == "SELL":
            conflicts.append(
                f"BUY in PREMIUM zone (zone_bias=SELL) "
                f"→ allowed: score delta {delta:+.0f} ≥ {self._DECISION_THRESHOLD_STRONG}"
            )
        elif decision == "SELL" and zone_bias == "BUY":
            conflicts.append(
                f"SELL in DISCOUNT zone (zone_bias=BUY) "
                f"→ allowed: score delta {delta:+.0f} ≥ {self._DECISION_THRESHOLD_STRONG}"
            )

        # ── 7. Priority chain used ───────────────────────────────────────
        resolved = meta.get("resolved")
        if structure_bias and resolved == structure_bias:
            priority_used = "Priority 1 — Market Structure (BOS/CHoCH)"
        elif htf_bias and resolved == htf_bias:
            priority_used = "Priority 2 — HTF Trend Bias"
        elif liq_bias and resolved == liq_bias:
            priority_used = "Priority 3 — Liquidity Sweep"
        elif zone_bias and resolved == zone_bias:
            priority_used = "Priority 4 — P/D Zone"
        else:
            priority_used = "Priority 5 — Score Delta (pure confluence)"

        # ── 8. Rejection reasons ─────────────────────────────────────────
        rejection_reasons = []
        gate_rej    = analysis.get("rejection_reason")
        no_trade_r  = analysis.get("no_trade_reason")

        if gate_rej:
            rejection_reasons.append(f"GATE REJECTION: {gate_rej}")
        if no_trade_r:
            rejection_reasons.append(f"DECISION REJECTION: {no_trade_r}")

        if decision == "WAIT":
            if not has_bos and not has_choch:
                rejection_reasons.append(
                    "Missing: No BOS or CHoCH — structure shift required for valid entry"
                )
            if not has_bull_sweep and not has_bear_sweep:
                rejection_reasons.append(
                    "Missing: No liquidity sweep — no institutional order flow confirmation"
                )
            if abs(delta) < threshold:
                rejection_reasons.append(
                    f"Score too balanced: |delta|={abs(delta):.0f} < required {threshold:.0f} "
                    f"(bull={bull_score:.0f} bear={bear_score:.0f})"
                )
            if is_ranging and not rejection_reasons:
                rejection_reasons.append(
                    f"Ranging market — threshold raised to {threshold:.0f}; "
                    "swing setups not permitted without clear directional dominance"
                )

        # ── 9. Level trace ───────────────────────────────────────────────
        level_trace = None
        if decision in ("BUY", "SELL") and levels:
            entry  = float(levels.get("entry") or 0)
            sl     = float(levels.get("stop_loss") or 0)
            tp1    = float(levels.get("tp1") or 0)
            tp2    = float(levels.get("tp2") or 0)
            rr     = float(analysis.get("gate_rr") or levels.get("risk_reward") or 0)
            level_trace = (
                f"Entry={entry:.5f} SL={sl:.5f} "
                f"TP1={tp1:.5f} TP2={tp2:.5f} RR={rr:.2f}"
            )

        # ── 10. WHY THIS TRADE / WHY OTHER SIDE REJECTED ─────────────────
        why_this = why_other = None
        if decision in ("BUY", "SELL"):
            other = "SELL" if decision == "BUY" else "BUY"
            why_this = (
                f"{decision} issued: {priority_used} confirms direction "
                f"| score delta {delta:+.0f} ≥ threshold {threshold:.0f}"
                + (f" | {level_trace}" if level_trace else "")
            )
            if structure_bias and structure_bias != other:
                why_other = (
                    f"{other} rejected: Structure bias is {structure_bias} "
                    f"({bull_bos} bullish vs {bear_bos} bearish BOS"
                    + (f", last CHoCH={choch_events[-1].get('type','?')}" if choch_events and isinstance(choch_events[-1], dict) else "")
                    + ")"
                )
            else:
                why_other = (
                    f"{other} rejected: insufficient confluences "
                    f"({'bull' if decision == 'SELL' else 'bear'} score "
                    f"{bear_score if decision == 'BUY' else bull_score:.0f} < "
                    f"{'bull' if decision == 'BUY' else 'bear'} score "
                    f"{bull_score if decision == 'BUY' else bear_score:.0f})"
                )

        # ── Assemble reason_trace ────────────────────────────────────────
        reason_trace = {
            "decision":             decision,
            "market_structure":     ms_trace,
            "liquidity":            liq_trace,
            "order_blocks":         ob_trace,
            "zone_logic":           zone_trace,
            "stop_hunt":            sh_trace,
            "score_delta":          (
                f"bull={bull_score:.0f} bear={bear_score:.0f} "
                f"delta={delta:+.0f} required≥{threshold:.0f} "
                f"[{'PASS' if abs(delta) >= threshold else 'FAIL'}]"
            ),
            "decision_priority_used": priority_used,
            "conflicts_detected":   conflicts or ["NONE"],
            "rejection_reasons":    rejection_reasons or ["N/A — all checks passed"],
        }
        if why_this:
            reason_trace["why_this_trade"]        = why_this
        if why_other:
            reason_trace["why_other_side_rejected"] = why_other

        # Anti-Fake Sweep trace (only present for RANGING/VOLATILE)
        afs_pass = analysis.get("anti_fake_sweep_pass")
        afs_conf = analysis.get("anti_fake_sweep_conf")
        if afs_pass is not None:
            reason_trace["anti_fake_sweep_pass"]  = afs_pass
            reason_trace["confirmation_used"]     = afs_conf

        analysis["reason_trace"] = reason_trace

        logger.info(
            f"TRACE [{decision}] {symbol}/{timeframe}: "
            f"Δ={delta:+.0f}/{threshold:.0f} "
            f"priority={priority_used.split('—')[0].strip()} "
            f"conflicts={len(conflicts)}"
        )
        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # NORMALIZE OUTPUT LAYER — Unified schema for API / Bot / Dashboard
    # Runs LAST — read-only normalization, never changes decisions
    # ═══════════════════════════════════════════════════════════════════════

    def _normalize_output_layer(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
    ) -> dict:
        """
        Unified Output Schema.
        Reads all existing analysis fields and builds analysis["output"]
        with a stable, typed schema consumed by API / Bot / Dashboard.
        Does NOT change any decision — pure normalization only.
        """
        decision  = analysis.get("recommendation", "WAIT")
        meta      = analysis.get("decision_meta", {})
        struct    = analysis.get("market_structure", {})
        sweep     = analysis.get("liquidity_sweep", {})
        ob        = analysis.get("order_blocks", {})
        pd_zone   = analysis.get("premium_discount", {})
        levels    = analysis.get("levels", {})
        conf      = float(analysis.get("ai_confidence_score") or 0)
        trace     = analysis.get("reason_trace", {})

        # ── decision ─────────────────────────────────────────────────────
        action = "NO TRADE" if decision in ("WAIT", "NO TRADE") else decision
        decision_reason = (
            trace.get("why_this_trade")
            or analysis.get("rejection_reason")
            or analysis.get("no_trade_reason")
            or "N/A"
        )
        out_decision = {
            "action":     action,
            "confidence": round(conf, 1),
            "reason":     str(decision_reason),
        }

        # ── score ─────────────────────────────────────────────────────────
        bull_score = float(meta.get("bull_score") or analysis.get("confluence", {}).get("bull_score") or 0)
        bear_score = float(meta.get("bear_score") or analysis.get("confluence", {}).get("bear_score") or 0)
        delta      = float(meta.get("score_delta") or (bull_score - bear_score))
        threshold  = float(meta.get("threshold") or self._DECISION_THRESHOLD_TREND)
        out_score  = {
            "bull":     round(bull_score, 1),
            "bear":     round(bear_score, 1),
            "delta":    round(delta, 1),
            "required": round(threshold, 1),
            "status":   "PASS" if abs(delta) >= threshold else "FAIL",
        }

        # ── market_structure ──────────────────────────────────────────────
        raw_trend    = struct.get("trend", "RANGING")
        bos_events   = struct.get("bos_events", [])
        choch_events = struct.get("choch_events", [])
        bull_bos     = sum(1 for b in bos_events if "BULLISH" in b.get("type", ""))
        bear_bos     = sum(1 for b in bos_events if "BEARISH" in b.get("type", ""))
        # normalise trend string
        if raw_trend in ("BULLISH", "BEARISH", "RANGING"):
            norm_trend = raw_trend
        elif "BULL" in str(raw_trend).upper():
            norm_trend = "BULLISH"
        elif "BEAR" in str(raw_trend).upper():
            norm_trend = "BEARISH"
        else:
            norm_trend = "RANGING"

        last_choch = "NONE"
        if choch_events:
            lc = choch_events[-1] if isinstance(choch_events[-1], dict) else {}
            raw_lc = lc.get("type", "")
            if "BULL" in str(raw_lc).upper():
                last_choch = "BULLISH"
            elif "BEAR" in str(raw_lc).upper():
                last_choch = "BEARISH"

        out_structure = {
            "trend":      norm_trend,
            "bos_bull":   bull_bos,
            "bos_bear":   bear_bos,
            "last_choch": last_choch,
        }

        # ── liquidity ─────────────────────────────────────────────────────
        has_bull_sweep = sweep.get("has_bullish_sweep", False)
        has_bear_sweep = sweep.get("has_bearish_sweep", False)
        sweep_detected = has_bull_sweep or has_bear_sweep

        if has_bull_sweep:
            sweep_type_out = "SSL"
            sweep_info     = sweep.get("ssl_sweep") or {}
        elif has_bear_sweep:
            sweep_type_out = "BSL"
            sweep_info     = sweep.get("bsl_sweep") or {}
        else:
            sweep_type_out = "NONE"
            sweep_info     = {}

        sq_raw = str(sweep.get("sweep_quality", "NONE")).upper()
        if sq_raw in ("STRONG", "HIGH"):
            strength = "STRONG"
        elif sq_raw in ("MODERATE", "MEDIUM", "CONFIRMED"):
            strength = "MODERATE"
        elif sweep_detected:
            strength = "WEAK"
        else:
            strength = "NONE"

        sweep_confirmed = has_bull_sweep or has_bear_sweep  # quality-confirmed sweep
        candles_since   = int(sweep_info.get("candles_since") or 0)

        out_liquidity = {
            "sweep_detected": sweep_detected,
            "sweep_type":     sweep_type_out,
            "sweep_confirmed": sweep_confirmed,
            "strength":       strength,
            "candles_since":  candles_since,
        }

        # ── order_blocks ──────────────────────────────────────────────────
        current_price = float(analysis.get("current_price") or 0)
        primary_bull_ob = analysis.get("primary_bull_ob")
        primary_bear_ob = analysis.get("primary_bear_ob")
        all_bull_obs    = ob.get("bullish_obs", [])
        all_bear_obs    = ob.get("bearish_obs", [])

        primary_ob   = primary_bull_ob if action == "BUY" else (primary_bear_ob if action == "SELL" else (primary_bull_ob or primary_bear_ob))
        ob_type      = "BULLISH" if primary_ob is primary_bull_ob else ("BEARISH" if primary_ob is primary_bear_ob else "NONE")
        total_obs    = (len(all_bull_obs) if action in ("BUY", "NO TRADE") else len(all_bear_obs)) or len(all_bull_obs) + len(all_bear_obs)
        rejected_cnt = max(0, total_obs - 1) if primary_ob else 0

        rej_reason = "NONE"
        gate_rej = analysis.get("rejection_reason", "")
        if "DISTANCE" in str(gate_rej):
            rej_reason = "DISTANCE"
        elif "OVERLAP" in str(gate_rej) or "CONFLICT" in str(gate_rej):
            rej_reason = "CONFLICT"
        elif "WEAK" in str(gate_rej):
            rej_reason = "WEAK"

        if primary_ob and isinstance(primary_ob, dict):
            ob_low  = float(primary_ob.get("low", 0))
            ob_high = float(primary_ob.get("high", 0))
            mid     = (ob_low + ob_high) / 2
            dist_pct = round(abs(current_price - mid) / mid * 100, 3) if mid else 0
            out_ob = {
                "primary": {
                    "type":         ob_type,
                    "range":        [round(ob_low, 5), round(ob_high, 5)],
                    "distance_pct": dist_pct,
                },
                "rejected_count":   rejected_cnt,
                "rejection_reason": rej_reason,
            }
        else:
            out_ob = {
                "primary":          None,
                "rejected_count":   rejected_cnt,
                "rejection_reason": rej_reason,
            }

        # ── zone ──────────────────────────────────────────────────────────
        pd_name = str(pd_zone.get("zone", "EQUILIBRIUM")).upper()
        if "DISCOUNT" in pd_name:
            zone_type = "DISCOUNT"
        elif "PREMIUM" in pd_name:
            zone_type = "PREMIUM"
        else:
            zone_type = "EQUILIBRIUM"

        zone_pct = round(float(pd_zone.get("pct") or 0), 2)

        if action == "BUY":
            aligned = zone_type == "DISCOUNT"
        elif action == "SELL":
            aligned = zone_type == "PREMIUM"
        else:
            aligned = False

        out_zone = {
            "type":              zone_type,
            "value_pct":         zone_pct,
            "aligned_with_trade": aligned,
        }

        # ── conflicts ─────────────────────────────────────────────────────
        raw_conflicts = trace.get("conflicts_detected", [])
        out_conflicts = []
        for c in raw_conflicts:
            if c == "NONE":
                continue
            # parse "A ≠ B → resolved: X" format from explainability layer
            parts = str(c).split("→")
            details  = parts[0].strip()
            resolved = parts[1].replace("resolved:", "").strip() if len(parts) > 1 else "unknown"
            # infer conflict type
            if "HTF" in details:
                c_type = "HTF_CONFLICT"
            elif "Zone" in details:
                c_type = "ZONE_CONFLICT"
            elif "Liquidity" in details:
                c_type = "LIQUIDITY_CONFLICT"
            else:
                c_type = "STRUCTURE_CONFLICT"
            out_conflicts.append({
                "type":        c_type,
                "details":     details,
                "resolved_by": resolved,
            })

        # ── no_trade_reason ───────────────────────────────────────────────
        no_trade_reasons = []
        if action == "NO TRADE":
            gate_rej_str = analysis.get("rejection_reason")
            dec_rej_str  = analysis.get("no_trade_reason")
            if gate_rej_str:
                no_trade_reasons.append(str(gate_rej_str))
            elif dec_rej_str:
                no_trade_reasons.append(str(dec_rej_str))
            else:
                # build from trace
                for r in trace.get("rejection_reasons", []):
                    if r and r != "N/A — all checks passed":
                        no_trade_reasons.append(r)
            if not no_trade_reasons:
                if out_score["status"] == "FAIL":
                    no_trade_reasons.append("SCORE_DELTA_INSUFFICIENT")
                if not sweep_detected:
                    no_trade_reasons.append("NO_LIQUIDITY_SWEEP")
                if bull_bos == 0 and bear_bos == 0 and last_choch == "NONE":
                    no_trade_reasons.append("NO_BOS_NO_CHOCH")

        # ── assemble final output ─────────────────────────────────────────
        analysis["output"] = {
            "decision":        out_decision,
            "score":           out_score,
            "market_structure": out_structure,
            "liquidity":       out_liquidity,
            "order_blocks":    out_ob,
            "zone":            out_zone,
            "conflicts":       out_conflicts,
            "no_trade_reason": no_trade_reasons,
            "auto_calibration": analysis.get("calibration_params"),
        }

        logger.debug(
            f"OUTPUT NORMALIZED [{action}] {symbol}/{timeframe}: "
            f"score={out_score['status']} sweep={sweep_type_out} "
            f"zone={zone_type} conflicts={len(out_conflicts)}"
        )
        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # DECISION FINALIZER — Converts analysis to single clean decision
    # "If it is not clear, it is not a trade"
    # ═══════════════════════════════════════════════════════════════════════

    # Min score delta to issue a trade (trending vs ranging markets)
    _DECISION_THRESHOLD_TREND  = 20   # need 20-pt lead in trending market
    _DECISION_THRESHOLD_RANGE  = 35   # stricter in ranging/sideways market
    _DECISION_THRESHOLD_STRONG = 40   # override HTF/zone conflicts if lead ≥40

    def _decision_finalizer(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        Decision-Grade Trading Engine.
        Converts multi-signal ICT analysis → single BUY / SELL / NO TRADE.
        Must run BEFORE _institutional_gate.

        Priority chain (conflict resolution):
          1. Market Structure (BOS / CHoCH)
          2. HTF bias
          3. Liquidity (sweep direction)
          4. P/D Zone bias
        """
        confluence  = analysis.get("confluence", {})
        struct      = analysis.get("market_structure", {})
        sweep       = analysis.get("liquidity_sweep", {})
        ob          = analysis.get("order_blocks", {})
        pd_zone     = analysis.get("premium_discount", {})
        market_mode = analysis.get("market_mode", {})
        rng_conflict= analysis.get("range_conflict", {})

        bull_score  = float(confluence.get("bull_score", 0))
        bear_score  = float(confluence.get("bear_score", 0))
        score_delta = bull_score - bear_score   # >0 = bullish lean, <0 = bearish lean

        # ── 1. Range Trap → immediate NO TRADE ──────────────────────────────
        if rng_conflict.get("in_range_trap") or rng_conflict.get("avoid_entry"):
            return self._hard_reject(analysis, "RANGE_TRAP_OB_OVERLAP_NO_BOS")

        # ── 2. Market Regime detection ───────────────────────────────────────
        mode  = (market_mode.get("mode") or "TREND").upper()
        trend = (struct.get("trend") or "RANGING").upper()
        is_ranging = mode == "RANGE" or trend == "RANGING"

        # Use calibrated threshold if available (from _auto_calibrate_thresholds)
        calib_delta = analysis.get("_calib_delta")
        if calib_delta is not None:
            threshold = float(calib_delta)
        else:
            threshold = (
                self._DECISION_THRESHOLD_RANGE  if is_ranging
                else self._DECISION_THRESHOLD_TREND
            )

        # ── 3. Stop Hunt validation — sweep MUST have structure shift ────────
        has_bullish_sweep = sweep.get("has_bullish_sweep", False)
        has_bearish_sweep = sweep.get("has_bearish_sweep", False)
        has_bos   = bool(struct.get("bos_events"))
        has_choch = bool(struct.get("choch_events"))
        any_sweep = has_bullish_sweep or has_bearish_sweep

        # In TRENDING market → sweep MUST have structure shift (BOS/CHoCH)
        # In RANGING/VOLATILE → run Anti-Fake Sweep filter instead
        req_sweep_conf = analysis.get("_calib_req_sweep", True)
        if any_sweep and not has_bos and not has_choch:
            if req_sweep_conf:
                # TRENDING: hard reject — no structure = no trade
                return self._hard_reject(analysis, "SWEEP_WITHOUT_STRUCTURE_SHIFT")
            else:
                # RANGING/VOLATILE: check at least one quality confirmation
                # determine likely direction from sweep type
                sweep_dir = "BUY" if has_bullish_sweep else "SELL"
                afs_pass, afs_conf = self._anti_fake_sweep_check(analysis, sweep_dir)
                analysis["anti_fake_sweep_pass"]  = afs_pass
                analysis["anti_fake_sweep_conf"]  = afs_conf
                if not afs_pass:
                    return self._hard_reject(analysis, f"FAKE_SWEEP_{afs_conf}")

        # ── 4. Score delta check ─────────────────────────────────────────────
        if abs(score_delta) < threshold:
            return self._hard_reject(
                analysis,
                f"SCORE_DELTA_{abs(score_delta):.0f}_BELOW_{threshold}"
            )

        # ── 5. Conflict Resolver (priority 1→4) ──────────────────────────────
        #  Priority 1: Market Structure dominance (BOS / CHoCH count)
        bos_list    = struct.get("bos_events", [])
        choch_list  = struct.get("choch_events", [])
        bull_bos    = sum(1 for b in bos_list if "BULLISH" in b.get("type", ""))
        bear_bos    = sum(1 for b in bos_list if "BEARISH" in b.get("type", ""))

        # Last CHoCH is most meaningful (recent structure reversal)
        last_choch_dir = None
        if choch_list:
            last_c = choch_list[-1] if isinstance(choch_list, list) else None
            if isinstance(last_c, dict):
                last_choch_dir = "BUY" if "BULLISH" in last_c.get("type", "") else "SELL"

        structure_bias: Optional[str] = None
        if last_choch_dir:
            structure_bias = last_choch_dir          # CHoCH beats BOS count
        elif bull_bos > bear_bos:
            structure_bias = "BUY"
        elif bear_bos > bull_bos:
            structure_bias = "SELL"

        #  Priority 2: HTF bias
        htf_bias: Optional[str] = None
        if htf_analysis:
            htf_trend = (htf_analysis.get("market_structure", {}).get("trend") or "RANGING").upper()
            if htf_trend == "BULLISH":
                htf_bias = "BUY"
            elif htf_trend == "BEARISH":
                htf_bias = "SELL"

        #  Priority 3: Liquidity sweep direction
        liq_bias: Optional[str] = None
        if has_bullish_sweep and not has_bearish_sweep:
            liq_bias = "BUY"
        elif has_bearish_sweep and not has_bullish_sweep:
            liq_bias = "SELL"

        #  Priority 4: Premium / Discount zone
        pd_raw  = (pd_zone.get("bias") or "NEUTRAL").upper()
        zone_bias: Optional[str] = "BUY" if pd_raw == "BUY" else ("SELL" if pd_raw == "SELL" else None)

        # ── Score direction (raw ICT answer) ────────────────────────────────
        score_dir = "BUY" if score_delta > 0 else "SELL"

        # ── Apply priority chain to resolve direction ────────────────────────
        if structure_bias:
            resolved = structure_bias
            # If score strongly disagrees with structure → NO TRADE
            if score_dir != structure_bias and abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
                return self._hard_reject(analysis, "SCORE_CONFLICTS_STRUCTURE")
        elif htf_bias:
            resolved = htf_bias
            if score_dir != htf_bias and abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
                return self._hard_reject(analysis, "SCORE_CONFLICTS_HTF")
        elif liq_bias:
            resolved = liq_bias
        else:
            resolved = score_dir   # fallback: pure score

        # ── 6. HTF conflict penalty ──────────────────────────────────────────
        if htf_bias and htf_bias != resolved and abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
            return self._hard_reject(analysis, "HTF_DIRECTION_CONFLICT")

        # ── 7. Execution zone validation ──────────────────────────────────────
        #  BUY must enter from discount/support, SELL from premium/resistance
        if resolved == "BUY" and zone_bias == "SELL":
            if abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
                return self._hard_reject(analysis, "BUY_IN_PREMIUM_ZONE")
        elif resolved == "SELL" and zone_bias == "BUY":
            if abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
                return self._hard_reject(analysis, "SELL_IN_DISCOUNT_ZONE")

        # ── 8. Primary OB selection (single zone, no overlap) ────────────────
        current_p     = float(analysis.get("current_price") or 0) or float(confluence.get("entry", 0) or 0)
        primary_bull_ob = self._closest_zone(current_p, ob.get("bullish_obs", []))
        primary_bear_ob = self._closest_zone(current_p, ob.get("bearish_obs", []))

        # Reject if the two primary zones overlap each other
        if primary_bull_ob and primary_bear_ob:
            if float(primary_bull_ob.get("high", 0)) > float(primary_bear_ob.get("low", 0)):
                return self._hard_reject(analysis, "PRIMARY_OB_ZONES_OVERLAP")

        # Store primary zones for gate to use
        analysis["primary_bull_ob"] = primary_bull_ob
        analysis["primary_bear_ob"] = primary_bear_ob

        # ── 9. Commit decision ───────────────────────────────────────────────
        analysis["recommendation"]  = resolved
        analysis["signal_type"]     = resolved
        analysis["confluence"]["direction"] = resolved

        # Decision metadata (useful for debugging / frontend display)
        analysis["decision_meta"] = {
            "bull_score":      bull_score,
            "bear_score":      bear_score,
            "score_delta":     round(score_delta, 1),
            "threshold":       threshold,
            "structure_bias":  structure_bias,
            "htf_bias":        htf_bias,
            "liq_bias":        liq_bias,
            "zone_bias":       zone_bias,
            "resolved":        resolved,
            "is_ranging":      is_ranging,
        }
        logger.info(
            f"DECISION [{resolved}] {symbol}/{timeframe}: "
            f"bull={bull_score:.0f} bear={bear_score:.0f} Δ={score_delta:+.0f} "
            f"struct={structure_bias} htf={htf_bias} liq={liq_bias}"
        )
        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # INSTITUTIONAL GATE — Single authoritative validation (Rules 1-16)
    # ═══════════════════════════════════════════════════════════════════════

    # Rule 5 — entry tolerance per timeframe
    _ENTRY_TOLERANCE = {
        "1m": 0.001, "5m": 0.001, "15m": 0.001,
        "30m": 0.002, "1h": 0.002, "4h": 0.003, "1d": 0.003,
    }

    # Rule 11 — cooldown per timeframe (seconds)
    _COOLDOWN_SEC = {
        "1m": 300, "5m": 900, "15m": 2700,
        "30m": 3600, "1h": 7200, "4h": 14400, "1d": 43200,
    }

    # Rule 9 — default spread per symbol
    _DEFAULT_SPREAD = {
        "XAUUSD": 0.30, "XAGUSD": 0.02, "BTCUSD": 8.0, "ETHUSD": 0.8,
        "EURUSD": 0.0001, "GBPUSD": 0.0002, "USDJPY": 0.02, "USDCHF": 0.0002,
        "NAS100": 1.0, "US30": 2.0, "USOIL": 0.04, "BRENT": 0.04,
    }

    def _institutional_gate(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        INSTITUTIONAL MODE Hard Rejection Gate (Rules 1-16).
        ICT Engine is the SOLE source of direction and trade levels.
        Any single check failure -> REJECT immediately, no exceptions.
        """
        rec = analysis.get("recommendation")
        if rec not in ("BUY", "SELL"):
            return analysis

        levels  = analysis.get("levels", {})
        entry   = float(levels.get("entry") or 0)
        sl      = float(levels.get("stop_loss") or 0)
        tp1_raw = float(levels.get("tp1") or 0)
        tp2_raw = float(levels.get("tp2") or 0)

        if not entry or not sl or not tp1_raw:
            return self._hard_reject(analysis, "MISSING_LEVELS")

        # Rule 2: Direction must match ICT confluence
        ict_dir = analysis.get("confluence", {}).get("direction", "WAIT")
        if ict_dir != rec:
            return self._hard_reject(analysis, "DIRECTION_MISMATCH_ICT")

        # Rule 3: Structure validation — sweep + aligned BOS/CHOCH
        struct   = analysis.get("market_structure", {})
        sweep    = analysis.get("liquidity_sweep", {})
        bos_list = struct.get("bos_events", [])

        has_sweep = (
            sweep.get("has_bullish_sweep") if rec == "BUY"
            else sweep.get("has_bearish_sweep")
        )
        has_aligned_bos = (
            any("BULLISH" in b.get("type", "") for b in bos_list) if rec == "BUY"
            else any("BEARISH" in b.get("type", "") for b in bos_list)
        )
        has_choch = bool(struct.get("choch_events"))

        if not has_sweep:
            return self._hard_reject(analysis, "NO_LIQUIDITY_SWEEP")
        # BOS/CHoCH required only when calibration demands it (TRENDING market)
        # In RANGING/VOLATILE: anti-fake sweep filter was already run in
        # _decision_finalizer — here we only re-check if it wasn't run yet
        req_sweep_conf = analysis.get("_calib_req_sweep", True)
        if not has_aligned_bos and not has_choch:
            if req_sweep_conf:
                return self._hard_reject(analysis, "NO_BOS_NO_CHOCH")
            else:
                # Only re-run if decision_finalizer didn't already check
                if not analysis.get("anti_fake_sweep_pass") and analysis.get("anti_fake_sweep_conf") is None:
                    afs_pass, afs_conf = self._anti_fake_sweep_check(analysis, rec)
                    analysis["anti_fake_sweep_pass"] = afs_pass
                    analysis["anti_fake_sweep_conf"] = afs_conf
                if not analysis.get("anti_fake_sweep_pass", False):
                    afs_conf = analysis.get("anti_fake_sweep_conf", "NO_CONFIRMATION")
                    return self._hard_reject(analysis, f"FAKE_SWEEP_{afs_conf}")

        # Rule 4: Closest zone only, no overlap
        ob           = analysis.get("order_blocks", {})
        current_p    = float(analysis.get("current_price") or entry)
        support_zone = self._closest_zone(current_p, ob.get("bullish_obs", []))
        resist_zone  = self._closest_zone(current_p, ob.get("bearish_obs", []))

        if support_zone and resist_zone:
            if float(support_zone["high"]) > float(resist_zone["low"]):
                return self._hard_reject(analysis, "ZONE_OVERLAP")

        # Rule 5: Entry vs zone (dynamic tolerance)
        # Use calibrated tolerance if available, else fall back to per-timeframe default
        tol = analysis.get("_calib_entry_tol") or self._ENTRY_TOLERANCE.get(timeframe, 0.002)
        if rec == "BUY" and support_zone:
            z_lo, z_hi = float(support_zone["low"]), float(support_zone["high"])
            if not (z_lo <= entry <= z_hi or abs(entry - z_hi) / entry <= tol):
                return self._hard_reject(analysis, "BUY_ENTRY_NOT_NEAR_SUPPORT")
        elif rec == "SELL" and resist_zone:
            z_lo, z_hi = float(resist_zone["low"]), float(resist_zone["high"])
            if not (z_lo <= entry <= z_hi or abs(entry - z_lo) / entry <= tol):
                return self._hard_reject(analysis, "SELL_ENTRY_NOT_NEAR_RESISTANCE")

        # Rule 6: TP/SL ordering + auto-fix swap
        tp1, tp2 = tp1_raw, tp2_raw
        if rec == "BUY":
            if sl >= entry:
                return self._hard_reject(analysis, "BUY_SL_ABOVE_ENTRY")
            if tp1 <= entry:
                return self._hard_reject(analysis, "BUY_TP1_BELOW_ENTRY")
            if tp2 and tp1 > tp2:
                levels["tp1"], levels["tp2"] = tp2, tp1
                tp1, tp2 = tp2, tp1
        else:
            if sl <= entry:
                return self._hard_reject(analysis, "SELL_SL_BELOW_ENTRY")
            if tp1 >= entry:
                return self._hard_reject(analysis, "SELL_TP1_ABOVE_ENTRY")
            if tp2 and tp1 < tp2:
                levels["tp1"], levels["tp2"] = tp2, tp1
                tp1, tp2 = tp2, tp1

        # Rule 7: Dynamic RR threshold
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp1 - entry)
        if sl_dist <= 0:
            return self._hard_reject(analysis, "ZERO_SL_DISTANCE")
        rr = round(tp_dist / sl_dist, 2)
        levels["risk_reward"] = rr
        analysis["risk_reward_ratio"] = rr
        # Use calibrated min_rr if available, else use performance-based dynamic RR
        calib_rr = analysis.get("_calib_min_rr")
        min_rr = calib_rr if calib_rr is not None else self._get_min_rr()
        if rr < min_rr:
            return self._hard_reject(analysis, f"RR_{rr:.2f}_BELOW_MIN_{min_rr:.1f}")

        # Rule 8: Distance filter
        if tp_dist / entry < 0.003:
            return self._hard_reject(analysis, "TP_TOO_CLOSE")
        if sl_dist / entry < 0.002:
            return self._hard_reject(analysis, "SL_TOO_CLOSE")

        # Rule 9: Spread filter (ATR*0.05 or default)
        atr    = float(levels.get("atr") or 0)
        spread = atr * 0.05 if atr > 0 else self._DEFAULT_SPREAD.get(symbol.upper(), entry * 0.0002)
        if spread / sl_dist > 0.30:
            return self._hard_reject(analysis, "SPREAD_EATS_RISK")

        # Rule 10: Liquidity-based TP override
        liquidity   = analysis.get("liquidity", {})
        nearest_bsl = liquidity.get("nearest_bsl")
        nearest_ssl = liquidity.get("nearest_ssl")

        if rec == "BUY" and nearest_bsl and float(nearest_bsl) > entry:
            liq_tp1 = float(nearest_bsl)
            liq_tp2 = round(liq_tp1 + (atr * 2 if atr else liq_tp1 * 0.005), 5)
            if abs(liq_tp1 - entry) / entry > 0.003:
                levels["tp1"] = round(liq_tp1, 5)
                levels["tp2"] = liq_tp2
                tp1 = liq_tp1
        elif rec == "SELL" and nearest_ssl and float(nearest_ssl) < entry:
            liq_tp1 = float(nearest_ssl)
            liq_tp2 = round(liq_tp1 - (atr * 2 if atr else liq_tp1 * 0.005), 5)
            if abs(entry - liq_tp1) / entry > 0.003:
                levels["tp1"] = round(liq_tp1, 5)
                levels["tp2"] = liq_tp2
                tp1 = liq_tp1

        # Rule 11: Cooldown (use calibrated cooldown if available)
        calib_cooldown = analysis.get("_calib_cooldown")
        if not self.check_cooldown(symbol, timeframe, override_sec=calib_cooldown):
            return self._hard_reject(analysis, "COOLDOWN_ACTIVE")

        # Rule 14: Confidence system
        conf = float(analysis.get("ai_confidence_score") or 0)

        # HTF alignment
        if htf_analysis:
            htf_trend = htf_analysis.get("market_structure", {}).get("trend", "RANGING")
            if (rec == "BUY" and htf_trend == "BULLISH") or                (rec == "SELL" and htf_trend == "BEARISH"):
                conf = min(conf + 8, 95)
            elif (rec == "BUY" and htf_trend == "BEARISH") or                  (rec == "SELL" and htf_trend == "BULLISH"):
                conf = max(conf - 15, 0)
                if conf < 50:
                    return self._hard_reject(analysis, "HTF_CONFLICT")

        # Confidence cap by R/R (Rule 14)
        rr_final = round(abs(levels.get("tp1", tp1) - entry) / sl_dist, 2)
        conf = min(conf, 75.0) if rr_final < 2.0 else min(conf, 90.0)

        if conf < 55:
            return self._hard_reject(analysis, f"CONF_TOO_LOW_{conf:.0f}")

        analysis["ai_confidence_score"]    = conf
        analysis["institutional_gate_passed"] = True
        analysis["gate_rr"]               = rr_final
        logger.info(
            f"GATE PASSED [{rec}] {symbol}/{timeframe}: "
            f"entry={entry} rr={rr_final} conf={conf:.0f}%"
        )
        return analysis

    @staticmethod
    def _closest_zone(price: float, obs: list) -> Optional[dict]:
        valid = [o for o in obs if isinstance(o, dict) and o.get("low") and o.get("high")]
        if not valid:
            return None
        return min(valid, key=lambda o: abs((float(o["low"]) + float(o["high"])) / 2 - price))

    def _anti_fake_sweep_check(
        self,
        analysis: dict,
        rec: str,
    ) -> tuple[bool, str]:
        """
        Anti-Fake Sweep Filter — only for RANGING / VOLATILE markets.
        Called after sweep is confirmed but BOS/CHoCH is absent.

        Requires at LEAST ONE of:
          A) Strong rejection candle: body >= 0.4×ATR AND wick_ratio >= 1.5
          B) Entry inside valid OB: not overlapping + distance <= 0.3%
          C) Proximity to SSL/BSL: distance <= 0.2%

        Also rejects if:
          - candles_since_sweep > 10   (stale sweep)
          - sweep_quality == "WEAK"    (low-conviction sweep)

        Returns: (passed: bool, confirmation_used: str)
        """
        sweep   = analysis.get("liquidity_sweep", {})
        ob      = analysis.get("order_blocks", {})
        levels  = analysis.get("levels", {})
        liquidity = analysis.get("liquidity", {})

        entry   = float(levels.get("entry") or analysis.get("current_price") or 0)
        atr     = float(levels.get("atr") or 0)

        # ── Safety gates: reject outright before checking confirmations ───────
        sweep_info = sweep.get("ssl_sweep" if rec == "BUY" else "bsl_sweep") or {}
        candles_since = int(sweep_info.get("candles_since") or 0)
        sweep_quality = str(sweep.get("sweep_quality", "NONE")).upper()

        if candles_since > 10:
            logger.warning(
                f"ANTI_FAKE_SWEEP: stale sweep candles_since={candles_since} > 10"
            )
            return False, "STALE_SWEEP"

        if sweep_quality == "WEAK":
            logger.warning("ANTI_FAKE_SWEEP: sweep_quality=WEAK rejected")
            return False, "WEAK_SWEEP_QUALITY"

        # ── Confirmation A: Strong rejection candle ───────────────────────────
        wick_atr   = float(sweep_info.get("wick_atr_ratio") or 0)
        body_ratio = float(sweep_info.get("body_atr_ratio") or 0)
        conf_a     = (body_ratio >= 0.4 and wick_atr >= 1.5) if atr > 0 else False

        # ── Confirmation B: Entry inside valid OB (not overlapping, <= 0.3%) ──
        conf_b          = False
        ob_key          = "bullish_obs" if rec == "BUY" else "bearish_obs"
        nearest_ob      = self._closest_zone(entry, ob.get(ob_key, []))
        support_zone_b  = self._closest_zone(entry, ob.get("bullish_obs", []))
        resist_zone_b   = self._closest_zone(entry, ob.get("bearish_obs", []))

        # check no overlap
        ob_overlap = (
            support_zone_b and resist_zone_b
            and float(support_zone_b["high"]) > float(resist_zone_b["low"])
        )
        if nearest_ob and not ob_overlap and entry > 0:
            ob_lo  = float(nearest_ob.get("low", 0))
            ob_hi  = float(nearest_ob.get("high", 0))
            ob_mid = (ob_lo + ob_hi) / 2
            dist   = abs(entry - ob_mid) / entry if entry else 1
            conf_b = (ob_lo <= entry <= ob_hi or dist <= 0.003)

        # ── Confirmation C: Close to SSL/BSL (within 0.2%) ───────────────────
        conf_c     = False
        target_liq = liquidity.get("nearest_bsl") if rec == "BUY" else liquidity.get("nearest_ssl")
        if target_liq and entry > 0:
            liq_dist = abs(entry - float(target_liq)) / entry
            conf_c   = liq_dist <= 0.002

        # ── Pick first passing confirmation ───────────────────────────────────
        if conf_a:
            return True, "rejection_candle"
        if conf_b:
            return True, "OB_alignment"
        if conf_c:
            return True, "liquidity_proximity"

        logger.warning(
            f"ANTI_FAKE_SWEEP: no confirmation — "
            f"body={body_ratio:.2f} wick={wick_atr:.2f} "
            f"ob_ok={conf_b} liq_ok={conf_c} "
            f"candles={candles_since} quality={sweep_quality}"
        )
        return False, "NO_CONFIRMATION"

    def _hard_reject(self, analysis: dict, reason: str) -> dict:
        rec = analysis.get("recommendation", "?")
        logger.warning(f"REJECTED [{rec}] {reason}")
        analysis.update({
            "recommendation":         "WAIT",
            "signal_type":            "WAIT",
            "ai_confidence_score":    min(float(analysis.get("ai_confidence_score") or 0), 45.0),
            "institutional_rejected": True,
            "rejection_reason":       reason,
            "levels":                 {},
            "entry_zones":            [],
            "stop_loss_zone":         None,
            "take_profit_zones":      [],
        })
        return analysis

    def _get_min_rr(self) -> float:
        wr = self.get_winrate()
        if wr > 0.60:  return 1.3
        if wr >= 0.40: return 1.5
        if wr >= 0.30: return 1.7
        return 2.0

    def check_cooldown(self, symbol: str, timeframe: str, override_sec: float = None) -> bool:
        import time as _t
        key = f"{symbol.upper()}_{timeframe}"
        cooldown = override_sec if override_sec is not None else self._COOLDOWN_SEC.get(timeframe, 3600)
        last = self._last_signal_time.get(key, 0)
        if _t.time() - last < cooldown:
            remaining = int(cooldown - (_t.time() - last))
            logger.info(f"Cooldown [{symbol}/{timeframe}]: {remaining}s left (cooldown={cooldown}s)")
            return False
        return True

    def record_signal_sent(self, symbol: str, timeframe: str):
        import time as _t
        self._last_signal_time[f"{symbol.upper()}_{timeframe}"] = _t.time()

    def update_performance(self, result: str):
        if result == "WIN":    self._perf["wins"]   += 1
        elif result == "LOSS": self._perf["losses"] += 1

    def get_winrate(self) -> float:
        total = self._perf["wins"] + self._perf["losses"]
        return self._perf["wins"] / total if total > 0 else 0.55

    def load_performance_from_db(self, db_session) -> None:
        try:
            from app.models.signal import Signal, SignalStatus
            wins   = db_session.query(Signal).filter(
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT])
            ).count()
            losses = db_session.query(Signal).filter(
                Signal.status == SignalStatus.SL_HIT
            ).count()
            self._perf = {"wins": wins, "losses": losses}
            logger.info(
                f"Performance loaded: {wins}W/{losses}L "
                f"winrate={self.get_winrate():.0%} "
                f"min_rr={self._get_min_rr()}"
            )
        except Exception as e:
            logger.warning(f"Could not load performance from DB: {e}")

    def _error_response(self, symbol: str, error: str) -> Dict:
        return {
            "symbol": symbol,
            "error": error,
            "ai_confidence_score": 0,
            "recommendation": "WAIT",
            "signal_type": "ERROR",
            "entry_zones": [],
            "stop_loss_zone": 0,
            "take_profit_zones": [],
            "risk_reward_ratio": 0,
            "timestamp": datetime.now().isoformat(),
        }


# Singleton
mosh_ai_engine_v5 = MoshAIEngineV5()
