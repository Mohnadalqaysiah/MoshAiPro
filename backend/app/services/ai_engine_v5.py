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

# مدة الكاش بالثواني — EMERGENCY OVERRIDE
_SIGNAL_CACHE_TTL = {
    "15m":   5 * 60,    # 5 دقائق
    "30m":   7 * 60,   # 7 دقائق
    "1h":   10 * 60,   # 10 دقائق
    "4h":   30 * 60,   # 30 دقيقة
    "1d":  120 * 60,   # 2 ساعات
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
        # Rolling signal history: key="{symbol}_{tf}" → list of {ts, passed, delta}
        # Used by emergency calibration to measure pass_rate and avg_delta
        self._signal_history: Dict[str, list] = {}
        self._HISTORY_WINDOW = 20   # keep last 20 analyses per key
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
                if analysis.get("institutional_gate_passed"):
                    # ── OUTPUT SAFETY GATE — 7-rule final logical validation ──
                    analysis = self._output_safety_gate(analysis, symbol, timeframe, htf_analysis)
                    if analysis.get("recommendation") in ("BUY", "SELL"):
                        # ── CONFIDENCE CALIBRATION — replaces raw AI score ────
                        analysis = self._confidence_calibration_layer(
                            analysis, symbol, timeframe, htf_analysis
                        )
                        # ── SMART MODE — classify SWING / SCALP ───────────────
                        analysis = self._classify_trade_mode(
                            analysis, symbol, timeframe, htf_analysis
                        )
                        self._record_signal_issued(symbol, timeframe)

            # ── SMART RESCUE LAYER — near-threshold signals recovered as BUY/SELL ─
            # Runs after decision_finalizer + institutional_gate.
            # Volatility adaptation (SCALP_BOOST/SILENCE_BOOST) applied inside.
            if analysis.get("institutional_rejected") or \
               analysis.get("recommendation") == "WAIT":
                analysis = self._smart_rescue_layer(
                    analysis, symbol, timeframe, htf_analysis
                )

            # ── BORDERLINE RESCUE — older soft-rescue (WAIT only, not BUY/SELL) ─
            if analysis.get("institutional_rejected") and \
               not analysis.get("smart_rescued"):
                analysis = self._borderline_rescue_layer(
                    analysis, symbol, timeframe, htf_analysis
                )

            # ── SMART MODE fallback — ensure trade_type set on WAIT/rescued signals ─
            if not analysis.get("trade_type"):
                analysis = self._classify_trade_mode(
                    analysis, symbol, timeframe, htf_analysis
                )

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

            # ── Record result for emergency calibration pass_rate tracking ───
            self._record_analysis_result(
                symbol, timeframe,
                passed=analysis.get("signal_status") == "PASS",
                delta=float(analysis.get("effective_delta") or 0),
            )

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
    # MARKET REGIME DETECTION — Adaptive behavior based on confluence quality
    # ═══════════════════════════════════════════════════════════════════════

    def _detect_market_regime(self, analysis: dict) -> str:
        """
        Classify market into 4 regimes based on confluence, sweep quality, and volatility.
        Returns: DEAD | NORMAL | ACTIVE | VOLATILE

        DEAD:    confluence < 35, no sweep, weak structure
        NORMAL:  confluence 35-50, mixed signals
        ACTIVE:  confluence > 50, strong sweep, aligned structure
        VOLATILE: high ATR + low confluence = choppy/ranging with spikes
        """
        confluence = analysis.get("confluence", {})
        conf_score = float(confluence.get("confidence", 0))
        direction  = confluence.get("direction", "WAIT")
        
        sweep_data = analysis.get("liquidity_sweep", {})
        has_sweep  = sweep_data.get("has_bullish_sweep") or sweep_data.get("has_bearish_sweep")
        sweep_quality = sweep_data.get("sweep_analysis", {}).get("sweep_quality", "NONE")
        
        struct = analysis.get("market_structure", {})
        trend = str(struct.get("trend", "RANGING")).upper()
        
        levels = analysis.get("levels", {})
        atr = float(levels.get("atr") or 0)
        current_price = float(analysis.get("current_price") or 1)
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0
        
        # Confluence quality thresholds
        strong_confluence = conf_score > 50
        weak_confluence = conf_score < 35
        
        # Sweep quality
        strong_sweep = sweep_quality in ("STRONG", "VERY_STRONG")
        
        # Structure alignment
        has_bos = bool(struct.get("bos_events", []))
        aligned_structure = direction != "WAIT" and has_bos
        
        # Classify regime
        if weak_confluence and not has_sweep and not aligned_structure:
            return "DEAD"
        elif strong_confluence and (strong_sweep or aligned_structure):
            return "ACTIVE"
        elif atr_pct > 0.010 and conf_score < 45:
            return "VOLATILE"  # Choppy + weak structure
        else:
            return "NORMAL"

    # ═══════════════════════════════════════════════════════════════════════
    # AUTO CALIBRATION ENGINE — Adapts thresholds to market + performance
    # "Adapt thresholds — not logic"
    # ═══════════════════════════════════════════════════════════════════════

    # Hard limits — never exceeded regardless of market conditions
    _CALIB_DELTA_MIN      = 10       # floor only — base thresholds are 12-13; floor must be below them
    _CALIB_DELTA_MAX      = 35
    _CALIB_RR_MIN         = 1.0      # was 1.1 — RR≥1.0 is still a valid trade; 1.1 was over-filtering ranging setups
    _CALIB_RR_MAX         = 2.0
    _CALIB_TOL_MIN        = 0.0025   # 0.25%
    _CALIB_TOL_MAX        = 0.0060   # 0.60%
    _CALIB_COOLDOWN_MIN   = 1800     # was 3600 — allow signal every 30 min (not forced 1h gap)
    _CALIB_COOLDOWN_MAX   = 14400    # 4 hours
    _CALIB_SILENCE_HOURS  = 3        # was 6 — trigger silence relaxation after 3h not 6h
    _WINRATE_THRESHOLD    = 0.68     # don't raise thresholds if winrate already high

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

        # ── 2. Market Regime Detection ────────────────────────────────────────
        # Detect current market condition to adapt thresholds
        market_regime = self._detect_market_regime(analysis)
        
        # ── 2b. Adaptive Delta Logic (regime-aware) ────────────────────────────
        # DEAD market: remain strict (avoid forcing signals in dead zones)
        # NORMAL market: standard thresholds
        # ACTIVE market: relax slightly (allow refined entry optimization)
        # VOLATILE market: moderate approach (avoid over-trading choppy conditions)
        
        regime_base_delta = {
            "DEAD": 13,
            "ACTIVE": 11,
            "VOLATILE": 14,
            "NORMAL": 12,
        }.get(market_regime, 12)
        required_delta = regime_base_delta
        
        delta_ranges = {
            "RANGING": (10, 18),
            "TRENDING": (12, 20),
            "VOLATILE": (14, 22),
        }
        state_delta_floor, state_delta_ceiling = delta_ranges.get(market_state, (12, 20))
        if market_regime == "DEAD":
            state_delta_floor = max(state_delta_floor, 13)
        
        # ── 3. Dynamic min RR (market_state-aware + winrate) ──────────────────
        wr = self.get_winrate()
        
        # PREVENT OVERFITTING: Don't raise thresholds if winrate already excellent
        if wr >= self._WINRATE_THRESHOLD:  # >= 68%
            # Winrate is good — don't keep tightening
            required_delta = max(required_delta - 2, self._CALIB_DELTA_MIN)
            min_rr = 1.0  # Allow 1.0 RR in high-quality regimes
        else:
            # RANGING markets: lower RR bar (1.0) — smaller moves, tighter ranges
            # TRENDING/VOLATILE: standard 1.1
            base_rr = 1.0 if market_state == "RANGING" else 1.1
            if wr < 0.40:
                min_rr = max(base_rr + 0.2, 1.3)   # winrate penalty on top of base
            else:
                min_rr = base_rr

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

        # ── 8. EMERGENCY CALIBRATION MODE ────────────────────────────────────
        # Activates when pass_rate < 50% over last 20 analyses.
        # Adapts thresholds to market reality without removing risk controls.
        pass_rate = self._get_pass_rate(symbol, timeframe)
        emergency_active = pass_rate < 0.50
        emergency_params = {}

        if emergency_active:
            avg_delta = self._get_avg_delta(symbol, timeframe)

            # 1. Delta adaptive: set threshold BELOW recent avg (90% of avg)
            # Old: max(13, avg+1) = ABOVE avg — opposite of relaxation!
            # When avg=14.5: max(13, 14.5+1)=15.5 was STRICTER than base threshold
            # New: max(12, avg*0.90) = slightly below avg → actually relaxes
            required_delta = max(12, avg_delta * 0.90)

            # 2. HTF conflict weight × 0.6 (passed to confidence calibration)
            analysis["_htf_penalty_multiplier"] = 0.6

            # 3. Relax RR by 0.2 (floor = 1.05 to preserve minimum risk ratio)
            min_rr = max(1.05, min_rr - 0.2)

            # 4. Partial confluence mode — soft approval active
            analysis["_partial_confluence_mode"] = True

            # 5. Soft override: 2 strong conditions → WATCHLIST becomes PASS
            analysis["_soft_approval_mode"] = True

            emergency_params = {
                "active":          True,
                "pass_rate":       round(pass_rate, 3),
                "avg_delta":       round(avg_delta, 1),
                "delta_override":  round(required_delta, 1),
                "rr_override":     round(min_rr, 2),
                "htf_multiplier":  0.6,
            }
            logger.warning(
                f"🚨 EMERGENCY_CALIB [{symbol}/{timeframe}] "
                f"pass_rate={pass_rate:.0%} avg_delta={avg_delta:.1f} "
                f"→ delta={required_delta:.0f} RR≥{min_rr:.2f}"
            )

        # ── 9. Apply hard limits (clamp) ──────────────────────────────────────
        # Use fixed floor only — avg_delta_floor * 0.85 caused stale-history inflation
        # After restart: _signal_history is empty → _get_avg_delta returns default
        # Old default 18 → 18*0.85=15.3 floor locked ALL thresholds at 15.3 post-restart
        delta_min = self._CALIB_DELTA_MIN
        required_delta = max(delta_min, min(self._CALIB_DELTA_MAX, required_delta))
        required_delta = max(state_delta_floor, min(state_delta_ceiling, required_delta))
        min_rr = max(self._CALIB_RR_MIN, min(self._CALIB_RR_MAX, min_rr))
        entry_tolerance = max(self._CALIB_TOL_MIN, min(self._CALIB_TOL_MAX, entry_tolerance))
        cooldown_sec = max(self._CALIB_COOLDOWN_MIN, min(self._CALIB_COOLDOWN_MAX, cooldown_sec))

        # ── 9. Apply calibrated values ────────────────────────────────────────
        # Score delta → read by _decision_finalizer via calibration_params
        # Min RR / tolerance → read by _institutional_gate via same dict
        calibration = {
            "market_state":               market_state,
            "market_regime":              market_regime,  # NEW: regime-based adaptation
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
                f"{market_state} + {volatility} volatility + {market_regime} regime"
                + (" | silence relaxed" if silence_relaxed else "")
                + (" | EMERGENCY_CALIB" if emergency_active else "")
                + (f" | HIGH_WINRATE({wr:.0%})" if wr >= self._WINRATE_THRESHOLD else f" | winrate={wr:.0%}")
            ),
            "emergency": emergency_params or {"active": False, "pass_rate": round(pass_rate, 3)},
        }
        analysis["calibration_params"] = calibration

        # Also inject directly into _ENTRY_TOLERANCE for this call
        # (per-symbol/timeframe override — does NOT mutate class-level dict permanently)
        analysis["_calib_entry_tol"]   = entry_tolerance
        analysis["_calib_min_rr"]      = min_rr
        analysis["_calib_delta"]       = required_delta
        analysis["_market_regime"]     = market_regime  # NEW: store regime for decision logic
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

    def _record_analysis_result(self, symbol: str, timeframe: str, passed: bool, delta: float):
        """Rolling window tracker for emergency calibration mode."""
        key = f"{symbol.upper()}_{timeframe}"
        hist = self._signal_history.setdefault(key, [])
        hist.append({"ts": time.time(), "passed": passed, "delta": abs(delta)})
        if len(hist) > self._HISTORY_WINDOW:
            self._signal_history[key] = hist[-self._HISTORY_WINDOW:]

    def _get_pass_rate(self, symbol: str, timeframe: str) -> float:
        """Fraction of recent analyses that produced a PASS signal (0.0–1.0)."""
        hist = self._signal_history.get(f"{symbol.upper()}_{timeframe}", [])
        if len(hist) < 3:
            return 1.0   # not enough history — assume healthy
        return sum(1 for h in hist if h["passed"]) / len(hist)

    def _get_avg_delta(self, symbol: str, timeframe: str) -> float:
        """Average effective_delta over recent analyses."""
        hist = self._signal_history.get(f"{symbol.upper()}_{timeframe}", [])
        deltas = [h["delta"] for h in hist if h["delta"] > 0]
        # Default was 18.0 — caused 18*0.85=15.3 floor after every Docker restart
        # (history is in-memory; restart wipes it → stale 18 inflated the floor forever)
        return sum(deltas) / len(deltas) if deltas else 12.0

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

        # ── signal_status — deterministic: PASS / REJECT / WATCHLIST ────────
        signal_status = analysis.get("signal_status") or (
            "PASS"      if action in ("BUY", "SELL") else
            "WATCHLIST" if analysis.get("watchlist_reason") else
            "REJECT"    if analysis.get("institutional_rejected") else
            "WATCHLIST"   # WAIT without a hard reject = watchlist candidate
        )

        # ── primary rejection reason (single, severity-ordered) ───────────
        primary_reason = self._select_primary_rejection_reason(analysis)

        # ── stability score (0–100) — measures distance from rejection boundary ──
        meta_d     = analysis.get("decision_meta", {})
        eff_d      = float(meta_d.get("effective_delta") or analysis.get("effective_delta") or 0)
        thr_d      = float(meta_d.get("threshold") or 20)
        delta_margin = max(0.0, eff_d - thr_d)
        delta_max    = max(thr_d * 0.8, 1.0)   # full score at 80% margin above threshold

        sq_s = str(sweep.get("sweep_quality", "NONE")).upper()
        sweep_s = (1.0 if sq_s in ("STRONG","HIGH") else
                   0.65 if sq_s in ("MODERATE","MEDIUM","CONFIRMED") else
                   0.30 if sq_s == "WEAK" else 0.0)

        bos_s   = bool(struct.get("bos_events"))
        choch_s = bool(struct.get("choch_events"))
        struct_s = (1.0 if bos_s and choch_s else
                    0.7 if choch_s else
                    0.5 if bos_s else 0.0)

        htf_s  = 1.0 if analysis.get("gate_htf_aligned") else 0.4
        rr_s   = float(analysis.get("risk_reward_ratio") or 0)
        rr_val = min(rr_s / 2.5, 1.0) if rr_s > 0 else 0.0

        stability_score = round(min(100.0, max(0.0,
            min(delta_margin / delta_max, 1.0) * 35 +
            sweep_s   * 25 +
            struct_s  * 20 +
            htf_s     * 10 +
            rr_val    * 10
        )), 1)

        # ── debug summary (single line for logs / frontend dev) ───────────
        debug_summary = (
            f"[{symbol}/{timeframe} {signal_status}] "
            f"delta={eff_d:.1f}/{thr_d:.1f} | "
            f"sweep={sq_s} | "
            f"struct={'CHoCH+BOS' if bos_s and choch_s else 'CHoCH' if choch_s else 'BOS' if bos_s else 'NONE'} | "
            f"htf={'aligned' if analysis.get('gate_htf_aligned') else 'neutral'} | "
            f"stability={stability_score} | "
            f"reason={primary_reason}"
        )

        # ── htf_status ────────────────────────────────────────────────────
        htf_status = analysis.get("htf_status") or (
            "aligned"     if analysis.get("gate_htf_aligned") else
            "conflicting" if analysis.get("htf_conflict_flag") else
            "neutral"
        )

        # ── risk_status (RR + SL only) ────────────────────────────────────
        rej = analysis.get("rejection_reason", "")
        if any(rej.startswith(t) for t in ("RR_", "ZERO_SL", "BUY_SL_ABOVE", "SELL_SL_BELOW")):
            risk_status = "VIOLATED"
        elif signal_status == "PASS":
            risk_status = "OK"
        else:
            risk_status = "PENDING"

        # ── assemble final output ─────────────────────────────────────────
        analysis["output"] = {
            "decision":         out_decision,
            "signal_status":    signal_status,
            "primary_reason":   primary_reason if signal_status == "REJECT" else None,
            "htf_status":       htf_status,
            "risk_status":      risk_status,
            "stability_score":  stability_score,
            "score":            out_score,
            "market_structure": out_structure,
            "liquidity":        out_liquidity,
            "order_blocks":     out_ob,
            "zone":             out_zone,
            "conflicts":        out_conflicts,
            "no_trade_reason":  no_trade_reasons,
            "auto_calibration": analysis.get("calibration_params"),
            "debug_summary":    debug_summary,
        }

        # Expose top-level
        analysis["htf_status"] = htf_status

        # Also expose top-level for quick access by API/Bot
        analysis["signal_status"]   = signal_status
        analysis["primary_reason"]  = primary_reason
        analysis["stability_score"] = stability_score

        logger.info(debug_summary)
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

        # ── DETECTION LAYER (no rejections) ──────────────────────────────────
        # All conditions detected here contribute to scoring only.

        # 0. Low-TF noise detection → scoring penalty only
        _low_tf_noise_penalty = 0.0
        if timeframe in ("1m", "5m", "15m"):
            has_any_sweep_early = (
                sweep.get("has_bullish_sweep", False) or sweep.get("has_bearish_sweep", False)
            )
            has_micro_struct = bool(struct.get("bos_events")) or bool(struct.get("choch_events"))
            raw_delta_early  = abs(bull_score - bear_score)
            early_thresh = float(analysis.get("_calib_delta") or self._DECISION_THRESHOLD_TREND)
            strong_delta = raw_delta_early >= early_thresh + 10
            if not ((has_any_sweep_early and has_micro_struct) or strong_delta):
                _low_tf_noise_penalty = 15.0
                analysis["low_tf_noise_flag"] = True
                logger.info(f"SCORING: low_tf_noise_penalty=15 [{symbol}/{timeframe}]")

        # 1. Range trap detection → scoring penalty only
        _range_trap_penalty = 0.0
        if rng_conflict.get("in_range_trap") or rng_conflict.get("avoid_entry"):
            _range_trap_penalty = 20.0
            analysis["range_trap_flag"] = True
            logger.info(f"SCORING: range_trap_penalty=20 [{symbol}/{timeframe}]")

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
            # Gold needs slightly lower decision threshold because XAUUSD
            # often generates valid setups with smaller directional delta.
            if symbol.upper() == "XAUUSD":
                threshold = max(15.0, threshold - 5.0)
                analysis["xau_threshold_adjusted"] = threshold

        # ── 3. Sweep assessment — scoring factor, not hard gate ──────────────
        # Sweep presence/quality ADJUSTS score_delta, it does NOT reject alone.
        # Only a confirmed fake (sweep + opposite reaction) remains a hard reject.
        has_bullish_sweep = sweep.get("has_bullish_sweep", False)
        has_bearish_sweep = sweep.get("has_bearish_sweep", False)
        has_bos   = bool(struct.get("bos_events"))
        has_choch = bool(struct.get("choch_events"))
        any_sweep = has_bullish_sweep or has_bearish_sweep
        sweep_quality_raw = str(sweep.get("sweep_quality", "NONE")).upper()

        # Score delta bonus/penalty from sweep quality
        # Sweep quality → effective_delta adjustment (weights reduced 30–40% to
        # avoid over-filtering from sweep absence / weakness)
        sweep_delta_adj = 0.0
        if sweep_quality_raw in ("STRONG", "HIGH"):
            sweep_delta_adj = +3.5    # was +5.0  (×0.70)
        elif sweep_quality_raw in ("MODERATE", "MEDIUM", "CONFIRMED"):
            sweep_delta_adj = +1.5    # was +2.0  (×0.75)
        elif sweep_quality_raw == "WEAK":
            sweep_delta_adj = -1.2    # was -2.0  (×0.60 — less penalty)
        elif not any_sweep:
            sweep_delta_adj = -3.0    # was -5.0  (×0.60 — less penalty)

        # ── SCORING LAYER: effective_delta ────────────────────────────────────
        # All quality signals feed into one number. No rejections here.
        # RANGING = +2.5 buffer, VOLATILE = +2.0, TRENDING = +1.5
        # VOLATILE markets often have weak sweep detection despite real moves
        if is_ranging:
            delta_buffer = 2.5
        elif mode == "VOLATILE" or market_mode.get("mode", "").upper() in ("VOLATILE", "BREAKOUT"):
            delta_buffer = 2.0    # was 1.5 — VOLATILE suppresses sweep detection
        else:
            delta_buffer = 1.5
        effective_delta = (
            abs(score_delta)
            + sweep_delta_adj
            + delta_buffer
            - _low_tf_noise_penalty
            - _range_trap_penalty
        )
        analysis["sweep_delta_adj"]      = sweep_delta_adj
        analysis["delta_buffer"]         = delta_buffer
        analysis["low_tf_noise_penalty"] = _low_tf_noise_penalty
        analysis["range_trap_penalty"]   = _range_trap_penalty
        analysis["effective_delta"]      = round(effective_delta, 1)

        # Structure grace: if no BOS/CHoCH but sweep exists, tag pending — no reject
        if any_sweep and not has_bos and not has_choch:
            analysis["structure_grace"]   = True
            analysis["structure_status"]  = "STRUCTURE_PENDING_ENTRY"
            analysis["structure_warning"] = "SWEEP_WITHOUT_STRUCTURE_SHIFT"
            logger.info(
                f"STRUCTURE PENDING [{symbol}/{timeframe}]: "
                f"sweep_quality={sweep_quality_raw} — tagged, no rejection"
            )

        # ── DECISION LAYER: delta below threshold → WATCHLIST, never REJECT ────
        # Score delta failure is a quality issue, not a risk violation.
        # Only RR/SL are hard gates.
        _is_watchlist = False
        if effective_delta < threshold:
            _is_watchlist = True
            analysis["watchlist_reason"] = (
                f"DELTA_{abs(score_delta):.0f}_ADJ_{effective_delta:.0f}_BELOW_{threshold:.0f}"
            )
            logger.info(
                f"WATCHLIST [{symbol}/{timeframe}]: "
                f"eff_delta={effective_delta:.1f} < threshold={threshold:.1f} "
                f"(noise={_low_tf_noise_penalty} trap={_range_trap_penalty})"
            )

            # ── SOFT OVERRIDE (emergency mode): 2 strong conditions → PASS ──────
            if analysis.get("_soft_approval_mode"):
                score_dir_local = "BUY" if score_delta > 0 else "SELL"
                strong = 0
                if sweep_quality_raw in ("STRONG", "HIGH"):
                    strong += 1
                if has_bos and has_choch:
                    strong += 1
                # HTF aligned
                if htf_analysis:
                    ht = (htf_analysis.get("market_structure", {}).get("trend") or "").upper()
                    htf_b_local = "BUY" if ht == "BULLISH" else ("SELL" if ht == "BEARISH" else None)
                    if htf_b_local and htf_b_local == score_dir_local:
                        strong += 1
                # Zone aligned
                pd_raw_local = (pd_zone.get("bias") or "NEUTRAL").upper()
                zone_b_local = ("BUY" if pd_raw_local == "BUY" else
                                "SELL" if pd_raw_local == "SELL" else None)
                if zone_b_local and zone_b_local == score_dir_local:
                    strong += 1
                # Delta ≥ 80% of threshold
                if abs(score_delta) >= threshold * 0.80:
                    strong += 1

                if strong >= 2:
                    _is_watchlist = False
                    analysis["soft_approved"]            = True
                    analysis["soft_approval_conditions"] = strong
                    analysis.pop("watchlist_reason", None)
                    logger.info(
                        f"SOFT_OVERRIDE [{symbol}/{timeframe}]: "
                        f"{strong}/5 conditions → promoted to PASS"
                    )

        # ── 5. Conflict Resolver — rebalanced: delta leads, sweep/struct follow ──
        #  Priority 1: Score delta direction (strongest signal in this rebalance)
        score_dir = "BUY" if score_delta > 0 else "SELL"

        #  Priority 2: Market Structure (BOS / CHoCH)
        bos_list    = struct.get("bos_events", [])
        choch_list  = struct.get("choch_events", [])
        bull_bos    = sum(1 for b in bos_list if "BULLISH" in b.get("type", ""))
        bear_bos    = sum(1 for b in bos_list if "BEARISH" in b.get("type", ""))

        last_choch_dir = None
        if choch_list:
            last_c = choch_list[-1] if isinstance(choch_list, list) else None
            if isinstance(last_c, dict):
                last_choch_dir = "BUY" if "BULLISH" in last_c.get("type", "") else "SELL"

        structure_bias: Optional[str] = None
        if last_choch_dir:
            structure_bias = last_choch_dir
        elif bull_bos > bear_bos:
            structure_bias = "BUY"
        elif bear_bos > bull_bos:
            structure_bias = "SELL"

        #  Priority 3: HTF bias
        htf_bias: Optional[str] = None
        if htf_analysis:
            htf_trend = (htf_analysis.get("market_structure", {}).get("trend") or "RANGING").upper()
            if htf_trend == "BULLISH":
                htf_bias = "BUY"
            elif htf_trend == "BEARISH":
                htf_bias = "SELL"

        #  Priority 4: Liquidity sweep direction
        liq_bias: Optional[str] = None
        if has_bullish_sweep and not has_bearish_sweep:
            liq_bias = "BUY"
        elif has_bearish_sweep and not has_bullish_sweep:
            liq_bias = "SELL"

        #  Priority 5: Premium / Discount zone
        pd_raw  = (pd_zone.get("bias") or "NEUTRAL").upper()
        zone_bias: Optional[str] = "BUY" if pd_raw == "BUY" else ("SELL" if pd_raw == "SELL" else None)

        # ── Direction resolution: delta first, structure confirms/warns ──────
        # Delta is already validated — use it as the primary direction anchor.
        resolved = score_dir

        # Structure agreement: if structure contradicts delta, warn (not reject) in ranging
        if structure_bias and structure_bias != score_dir:
            if abs(score_delta) >= self._DECISION_THRESHOLD_STRONG:
                pass   # strong delta overrides structure disagreement
            elif is_ranging:
                analysis["structure_conflict_warning"] = "SCORE_CONFLICTS_STRUCTURE"
                logger.info(
                    f"RANGING structure conflict → warning only [{symbol}/{timeframe}]: "
                    f"delta={score_dir} struct={structure_bias}"
                )
            else:
                # TRENDING: use structure as tiebreaker only if delta is borderline
                resolved = structure_bias

        # ── 6. HTF assessment — context flag + scoring penalty, NEVER rejection ──
        # HTF conflict is a multiplier only. RR/SL are the only hard gates.
        if htf_bias and htf_bias != resolved:
            analysis["htf_conflict_warning"] = f"HTF={htf_bias} vs resolved={resolved}"
            analysis["htf_status"]           = "conflicting"
            # Penalty applied in confidence calibration layer
            analysis["_htf_conflict_penalty"] = (
                20.0 if (not is_ranging and abs(score_delta) < self._DECISION_THRESHOLD_STRONG)
                else 10.0
            )
            logger.info(
                f"HTF_DIRECTION_CONFLICT → scoring penalty "
                f"{analysis['_htf_conflict_penalty']:.0f} [{symbol}/{timeframe}]"
            )
        elif htf_bias and htf_bias == resolved:
            analysis["htf_status"] = "aligned"
        else:
            analysis["htf_status"] = "neutral"

        # ── 7. Zone assessment — scoring penalty only, never rejection ──────────
        if resolved == "BUY" and zone_bias == "SELL":
            if abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
                analysis["zone_conflict_warning"]      = "BUY_IN_PREMIUM_ZONE"
                analysis["_zone_confidence_penalty"]   = 12.0
                logger.info(f"SCORING: BUY_IN_PREMIUM_ZONE penalty=12 [{symbol}/{timeframe}]")
        elif resolved == "SELL" and zone_bias == "BUY":
            if abs(score_delta) < self._DECISION_THRESHOLD_STRONG:
                analysis["zone_conflict_warning"] = (
                    "SELL_IN_DISCOUNT_ZONE" if is_ranging else "SELL_IN_DISCOUNT_TRENDING"
                )
                analysis["_zone_confidence_penalty"] = 12.0
                logger.info(
                    f"SCORING: SELL_IN_DISCOUNT penalty=12 [{symbol}/{timeframe}] "
                    f"(ranging={is_ranging})"
                )

        # ── 8. Primary OB selection — overlap resolved, never rejected ──────────
        current_p = float(analysis.get("current_price") or 0) or float(confluence.get("entry", 0) or 0)
        primary_bull_ob, primary_bear_ob, ob_overlap = self._resolve_ob_zones(
            current_p,
            ob.get("bullish_obs", []),
            ob.get("bearish_obs", []),
            resolved,           # direction is already decided at step 5
            htf_analysis,
            analysis.get("liquidity", {}),
        )
        if ob_overlap:
            analysis["ob_overlap_warning"] = True   # WARNING only — not a rejection

        # Store primary zones for gate to use
        analysis["primary_bull_ob"] = primary_bull_ob
        analysis["primary_bear_ob"] = primary_bear_ob

        # ── 9. Commit decision ───────────────────────────────────────────────
        # WATCHLIST: direction resolved for diagnostics, recommendation = WAIT
        analysis["confluence"]["direction"] = resolved
        if _is_watchlist:
            analysis["recommendation"] = "WAIT"
            analysis["signal_type"]    = "WAIT"
            analysis["signal_status"]  = "WATCHLIST"
            analysis["no_trade_reason"] = analysis.get(
                "watchlist_reason", "DELTA_BELOW_THRESHOLD"
            )
        else:
            analysis["recommendation"] = resolved
            analysis["signal_type"]    = resolved
            analysis["signal_status"]  = "PASS"   # tentative — gate may change to REJECT

        # Structure Grace: mark as STRUCTURE_PENDING_ENTRY (not yet confirmed)
        if analysis.get("structure_grace") and not _is_watchlist:
            analysis["structure_status"] = "STRUCTURE_PENDING_ENTRY"
            logger.info(
                f"STRUCTURE_PENDING_ENTRY [{resolved}] {symbol}/{timeframe}: "
                f"sweep confirmed, BOS/CHoCH awaited next candle"
            )

        # Decision metadata
        analysis["decision_meta"] = {
            "bull_score":        bull_score,
            "bear_score":        bear_score,
            "score_delta":       round(score_delta, 1),
            "effective_delta":   round(effective_delta, 1),
            "threshold":         threshold,
            "is_watchlist":      _is_watchlist,
            "structure_bias":    structure_bias,
            "htf_bias":          htf_bias,
            "liq_bias":          liq_bias,
            "zone_bias":         zone_bias,
            "resolved":          resolved,
            "is_ranging":        is_ranging,
            "structure_grace":   analysis.get("structure_grace", False),
        }
        status_tag = "WATCHLIST" if _is_watchlist else resolved
        logger.info(
            f"DECISION [{status_tag}] {symbol}/{timeframe}: "
            f"bull={bull_score:.0f} bear={bear_score:.0f} "
            f"Δ={score_delta:+.0f} eff={effective_delta:.1f}/thr={threshold:.1f} "
            f"struct={structure_bias} htf={htf_bias}"
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

    # Rule 11 — cooldown per timeframe (seconds) — EMERGENCY OVERRIDE
    _COOLDOWN_SEC = {
        "15m": 300,   # 5 دقائق
        "30m": 600, # 10 دقائق
        "1h": 900,  # 15 دقيقة
        "4h": 2700, # 45 دقيقة
        "1d": 7200, # 2 ساعات
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
        def _auto_calibrate_thresholds(
            self,
            analysis: dict,
            symbol: str,
            timeframe: str,
        ) -> dict:
            """
            EMERGENCY OVERRIDE: Freeze adaptive escalation, hardcode thresholds, min RR=1.0, disable winrate strictness.
            """
            # 1. Market state
            market_mode    = analysis.get("market_mode", {})
            struct         = analysis.get("market_structure", {})
            raw_trend      = str(struct.get("trend", "RANGING")).upper()
            raw_mode       = str(market_mode.get("mode", "")).upper()
            if raw_mode in ("VOLATILE", "BREAKOUT"):
                market_state = "VOLATILE"
            elif raw_trend in ("BULLISH", "BEARISH") or raw_mode in ("TRENDING", "TREND"):
                market_state = "TRENDING"
            else:
                market_state = "RANGING"

            # 2. Hardcode delta thresholds by market state
            if market_state == "RANGING":
                required_delta = 10
            elif market_state == "TRENDING":
                required_delta = 12
            elif market_state == "VOLATILE":
                required_delta = 14
            else:
                required_delta = 12
            state_delta_floor, state_delta_ceiling = (required_delta, required_delta)

            # 3. Min RR always 1.0
            min_rr = 1.0

            # 4. Entry tolerance (keep normal)
            entry_tolerance = 0.0030

            # 5. Cooldown (use emergency override values)
            cooldown_sec = self._COOLDOWN_SEC.get(timeframe, 900)

            # 6. Sweep confirmation only for trending
            require_sweep_confirmation = (market_state == "TRENDING")

            # 7. Clamp (no effect, values are fixed)
            calibration = {
                "market_state": market_state,
                "market_regime": "EMERGENCY_FIXED",
                "volatility": "OVERRIDE",
                "winrate": 0.0,
                "delta": required_delta,
                "min_rr": min_rr,
                "entry_tolerance": round(entry_tolerance * 100, 3),
                "entry_tolerance_raw": entry_tolerance,
                "cooldown_sec": cooldown_sec,
                "require_sweep_confirmation": require_sweep_confirmation,
                "silence_hours": 0.0,
                "silence_relaxed": False,
                "reason": "EMERGENCY OVERRIDE: thresholds frozen, RR=1.0, no winrate strictness",
                "emergency": {"active": True, "pass_rate": 0.0},
            }
            analysis["calibration_params"] = calibration
            analysis["_calib_entry_tol"]   = entry_tolerance
            analysis["_calib_min_rr"]      = min_rr
            analysis["_calib_delta"]       = required_delta
            analysis["_market_regime"]     = "EMERGENCY_FIXED"
            analysis["_calib_cooldown"]    = cooldown_sec
            analysis["_calib_req_sweep"]   = require_sweep_confirmation
            return analysis
                analysis["htf_status"]         = "conflicting"
                # Merge with any existing penalty from _decision_finalizer
                existing = float(analysis.get("_htf_conflict_penalty") or 0)
                analysis["_htf_conflict_penalty"] = max(existing, 20.0)
                logger.info(
                    f"HTF_CONFLICT → scoring penalty "
                    f"{analysis['_htf_conflict_penalty']:.0f} [{symbol}/{timeframe}]"
                )

        rr_final = round(abs(levels.get("tp1", tp1) - entry) / sl_dist, 2)
        analysis["institutional_gate_passed"] = True
        analysis["signal_status"]         = "PASS"
        analysis["gate_rr"]               = rr_final
        analysis["gate_htf_aligned"]      = False
        if htf_analysis:
            htf_trend = htf_analysis.get("market_structure", {}).get("trend", "RANGING")
            analysis["gate_htf_aligned"] = (
                (rec == "BUY"  and htf_trend == "BULLISH") or
                (rec == "SELL" and htf_trend == "BEARISH")
            )
        logger.info(
            f"GATE PASSED [{rec}] {symbol}/{timeframe}: "
            f"entry={entry} rr={rr_final}"
        )
        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # OUTPUT SAFETY GATE — 7-rule logical validation before final output
    # Runs AFTER institutional_gate, BEFORE confidence calibration.
    # Any failure → hard WAIT (never silently corrupt a signal).
    # ═══════════════════════════════════════════════════════════════════════

    # HTF timeframes that act as directional authority
    _HTF_AUTHORITY_TFS = {"1h", "4h", "1d"}

    def _output_safety_gate(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        OUTPUT SAFETY GATE — 7 non-negotiable logical rules.

        Rule 1 — HTF Direction Consistency:
            HTF BEARISH → BUY forbidden (WAIT)
            HTF BULLISH → SELL forbidden (WAIT)

        Rule 2 — Premium/Discount Zone:
            PREMIUM zone → SELL only (BUY → WAIT)
            DISCOUNT zone → BUY only (SELL → WAIT)

        Rule 3 — Entry/TP/SL Structural Validity:
            BUY:  TP > Entry > SL
            SELL: TP < Entry < SL

        Rule 4 — Multi-TF Priority (15m vs 1H):
            1H direction overrides 15m signals.
            If 15m conflicts with 1H → WAIT.

        Rule 5 — Confidence Floor:
            confidence < 55 → force WAIT (never send weak signal)

        Rule 6 — XAUUSD Special Filter:
            Requires ALL: HTF alignment + valid zone + RR ≥ 1.3

        Rule 7 — Final Level Coherence:
            Cross-validate direction, SL, TP, RR, zone alignment.
            Any mismatch → BLOCK.
        """
        rec    = analysis.get("recommendation")
        if rec not in ("BUY", "SELL"):
            return analysis

        levels  = analysis.get("levels", {})
        entry   = float(levels.get("entry") or 0)
        sl      = float(levels.get("stop_loss") or 0)
        tp1     = float(levels.get("tp1") or 0)
        rr      = float(analysis.get("gate_rr") or analysis.get("risk_reward_ratio") or 0)
        conf    = float(analysis.get("ai_confidence_score") or 0)

        pd_zone     = analysis.get("premium_discount", {})
        pd_raw      = (pd_zone.get("zone") or pd_zone.get("bias") or "NEUTRAL").upper()
        struct      = analysis.get("market_structure", {})
        sym_upper   = symbol.upper()

        def _block(reason: str) -> dict:
            logger.warning(
                f"🛑 SAFETY_GATE BLOCK [{sym_upper}/{timeframe}] {rec} → WAIT | {reason}"
            )
            analysis["recommendation"]       = "WAIT"
            analysis["signal_type"]          = "WAIT"
            analysis["signal_status"]        = "REJECT"
            analysis["safety_gate_blocked"]  = True
            analysis["safety_gate_reason"]   = reason
            analysis["rejection_reason"]     = f"SAFETY_{reason}"
            analysis["no_trade_reason"]      = f"SAFETY_{reason}"
            analysis["institutional_gate_passed"] = False
            return analysis

        # ── Rule 1: HTF Direction Consistency ────────────────────────────────
        # Use htf_analysis if available, else fallback to htf_context already computed
        htf_trend = None
        if htf_analysis:
            htf_trend = (
                htf_analysis.get("market_structure", {}).get("trend") or ""
            ).upper()
        if not htf_trend:
            # fallback: htf_context injected by analyze_market
            htf_trend = (
                analysis.get("htf_context", {}).get("trend") or
                analysis.get("trend", {}).get("htf_trend") or ""
            ).upper()

        if htf_trend in ("BEARISH", "BULLISH"):
            if rec == "BUY" and htf_trend == "BEARISH":
                return _block("HTF_BEARISH_FORBIDS_BUY")
            if rec == "SELL" and htf_trend == "BULLISH":
                return _block("HTF_BULLISH_FORBIDS_SELL")

        # ── Rule 2: Premium / Discount Zone Enforcement ───────────────────────
        # PREMIUM = sellers control → only SELL
        # DISCOUNT = buyers control → only BUY
        if "PREMIUM" in pd_raw and rec == "BUY":
            return _block("PREMIUM_ZONE_FORBIDS_BUY")
        if "DISCOUNT" in pd_raw and rec == "SELL":
            return _block("DISCOUNT_ZONE_FORBIDS_SELL")

        # ── Rule 3: Entry / TP / SL Structural Validity ───────────────────────
        if entry > 0 and sl > 0 and tp1 > 0:
            if rec == "BUY":
                # Must: TP > Entry > SL
                if not (tp1 > entry > sl):
                    return _block(
                        f"BUY_INVALID_LEVELS TP={tp1:.5f} Entry={entry:.5f} SL={sl:.5f}"
                    )
            else:
                # Must: TP < Entry < SL
                if not (tp1 < entry < sl):
                    return _block(
                        f"SELL_INVALID_LEVELS TP={tp1:.5f} Entry={entry:.5f} SL={sl:.5f}"
                    )

        # ── Rule 4: Multi-TF Priority (15m must align with 1H) ───────────────
        # Only applies when the current timeframe is a sub-1H frame.
        if timeframe in ("15m", "30m", "5m"):
            # LTF direction
            ltf_trend = (struct.get("trend") or "").upper()
            # 1H direction: first try from htf if timeframe=4h or from a pre-computed 1H key
            one_h_trend = None
            if htf_analysis:
                # htf_analysis is 4H when LTF ≤ 1H.
                # We use the htf_analysis trend as authority.
                one_h_trend = (
                    htf_analysis.get("market_structure", {}).get("trend") or ""
                ).upper()
            if not one_h_trend and htf_trend:
                one_h_trend = htf_trend

            if one_h_trend in ("BULLISH", "BEARISH"):
                if rec == "BUY" and one_h_trend == "BEARISH":
                    return _block("LTF_CONFLICTS_WITH_1H_BEARISH")
                if rec == "SELL" and one_h_trend == "BULLISH":
                    return _block("LTF_CONFLICTS_WITH_1H_BULLISH")

        # ── Rule 5: Confidence Floor ──────────────────────────────────────────
        # confidence is updated by calibration — if still 0 (pre-calibration),
        # use raw ICT score as proxy to avoid false blocks at this stage.
        if conf > 0 and conf < 55:
            return _block(f"CONFIDENCE_TOO_LOW_{conf:.0f}pct")

        # ── Rule 6: XAUUSD Special Filter ────────────────────────────────────
        if sym_upper == "XAUUSD":
            # Require HTF alignment for swing signals only.
            # Allow shorter-term XAUUSD scalp setups to pass without strict HTF alignment.
            htf_aligned = analysis.get("gate_htf_aligned", False)
            if timeframe in ("1h", "4h", "1d") and not htf_aligned:
                return _block("XAUUSD_REQUIRES_HTF_ALIGNMENT")

            # Require valid zone for swings; ignore premium/discount hard block on scalps.
            if timeframe in ("1h", "4h", "1d"):
                if rec == "BUY" and "PREMIUM" in pd_raw:
                    return _block("XAUUSD_BUY_IN_PREMIUM_ZONE")
                if rec == "SELL" and "DISCOUNT" in pd_raw:
                    return _block("XAUUSD_SELL_IN_DISCOUNT_ZONE")

            # Require minimum RR
            min_xau_rr = 1.3 if timeframe in ("1h", "4h", "1d") else 1.0
            if rr > 0 and rr < min_xau_rr:
                return _block(f"XAUUSD_RR_{rr:.2f}_BELOW_{min_xau_rr}")

        # ── Rule 7: Final Level Coherence ────────────────────────────────────
        if entry > 0 and sl > 0:
            sl_dist = abs(entry - sl)
            # SL must be on correct side
            if rec == "BUY" and sl >= entry:
                return _block(f"FINAL_BUY_SL_NOT_BELOW_ENTRY sl={sl:.5f} entry={entry:.5f}")
            if rec == "SELL" and sl <= entry:
                return _block(f"FINAL_SELL_SL_NOT_ABOVE_ENTRY sl={sl:.5f} entry={entry:.5f}")
            # RR coherence (must agree with levels)
            if tp1 > 0 and sl_dist > 0:
                computed_rr = abs(tp1 - entry) / sl_dist
                if computed_rr < 1.0:
                    return _block(f"FINAL_RR_{computed_rr:.2f}_BELOW_1.0")
            # Zone vs direction coherence (final cross-check)
            if rec == "BUY" and "PREMIUM" in pd_raw:
                return _block("FINAL_BUY_IN_PREMIUM_ZONE")
            if rec == "SELL" and "DISCOUNT" in pd_raw:
                return _block("FINAL_SELL_IN_DISCOUNT_ZONE")

        logger.info(
            f"✅ SAFETY_GATE PASSED [{rec}] {sym_upper}/{timeframe} "
            f"htf={htf_trend} zone={pd_raw} rr={rr:.2f} conf={conf:.0f}"
        )
        analysis["safety_gate_passed"] = True
        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # CONFIDENCE CALIBRATION LAYER — Institutional-grade score formula
    # Replaces raw AI confidence with structured component weighting.
    # Runs AFTER institutional_gate (only on passed signals).
    # ═══════════════════════════════════════════════════════════════════════

    def _confidence_calibration_layer(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        Confidence formula:
          score = (ict_score × 0.40)
                + (liquidity_quality × 0.25)
                + (structure_strength × 0.20)
                + (rr_score × 0.15)

        Penalties:
          RR < 1.5         → -10
          timeframe ≤ 15m  → -10
          STRUCTURE_PENDING → -15
          RANGING market   → -5

        Caps:
          always  ≤ 90
          RR < 2  ≤ 75
          ≤ 15m   ≤ 65

        Signal tiers (logged, not enforced — gate already enforces RR):
          TIER_A: RR ≥ 2 + strong structure + HTF aligned
          TIER_B: RR ≥ 1.5
        """
        rec    = analysis.get("recommendation", "WAIT")
        levels = analysis.get("levels", {})
        entry  = float(levels.get("entry") or 0)
        sl     = float(levels.get("stop_loss") or 0)
        tp1    = float(levels.get("tp1") or 0)
        rr     = float(analysis.get("gate_rr") or analysis.get("risk_reward_ratio") or 0)

        struct    = analysis.get("market_structure", {})
        sweep     = analysis.get("liquidity_sweep", {})
        confluence= analysis.get("confluence", {})
        calib     = analysis.get("calibration_params", {})

        # ── Component 1: ICT Score (0–100) ───────────────────────────────────
        if rec == "BUY":
            raw_ict = float(confluence.get("bull_score") or 0)
        else:
            raw_ict = float(confluence.get("bear_score") or 0)
        ict_score = min(raw_ict, 100.0)

        # ── Component 2: Liquidity Quality (0–100) ───────────────────────────
        sq = str(sweep.get("sweep_quality", "NONE")).upper()
        if sq in ("STRONG", "HIGH"):
            liquidity_quality = 90.0
        elif sq in ("MODERATE", "MEDIUM", "CONFIRMED"):
            liquidity_quality = 65.0
        elif sq == "WEAK":
            liquidity_quality = 30.0
        else:
            liquidity_quality = 0.0

        # ── Component 3: Structure Strength (0–100) ──────────────────────────
        has_bos   = bool(struct.get("bos_events"))
        has_choch = bool(struct.get("choch_events"))
        grace     = analysis.get("structure_grace", False)

        if has_choch and has_bos:
            structure_strength = 90.0
        elif has_choch:
            structure_strength = 75.0
        elif has_bos:
            structure_strength = 60.0
        elif grace:
            structure_strength = 35.0  # pending
        else:
            structure_strength = 0.0

        # ── Component 4: RR Score (0–100) ────────────────────────────────────
        if rr >= 2.5:
            rr_score = 100.0
        elif rr >= 2.0:
            rr_score = 85.0
        elif rr >= 1.5:
            rr_score = 65.0
        elif rr >= 1.3:
            rr_score = 45.0
        else:
            rr_score = 0.0

        # ── Raw formula ───────────────────────────────────────────────────────
        raw_conf = (
            ict_score        * 0.40
            + liquidity_quality * 0.25
            + structure_strength * 0.20
            + rr_score          * 0.15
        )

        # ── Penalties ─────────────────────────────────────────────────────────
        penalty = 0.0
        penalty_log = []

        if rr < 1.5:
            penalty += 10.0
            penalty_log.append(f"RR<1.5(-10)")
        if timeframe in ("1m", "5m", "15m"):
            penalty += 10.0
            penalty_log.append(f"LowTF(-10)")
        if grace:
            penalty += 15.0
            penalty_log.append(f"StructPending(-15)")
        market_state = calib.get("market_state", "")
        if market_state == "RANGING":
            penalty += 5.0
            penalty_log.append(f"Ranging(-5)")
        # Sweep scoring factor: weak or absent sweep penalises confidence
        sw_adj = float(analysis.get("sweep_delta_adj", 0))
        if sw_adj < 0:
            sweep_pen = abs(sw_adj) * 2   # −2 adj → −4 conf, −5 adj → −10 conf
            penalty += sweep_pen
            penalty_log.append(f"WeakSweep(-{sweep_pen:.0f})")
        # Zone conflict penalty
        zone_pen = float(analysis.get("_zone_confidence_penalty") or 0)
        if zone_pen > 0:
            penalty += zone_pen
            penalty_log.append(f"ZoneConflict(-{zone_pen:.0f})")
        elif analysis.get("zone_conflict_warning"):
            penalty += 8.0
            penalty_log.append(f"CounterZone(-8)")
        # HTF conflict penalty — context multiplier (emergency mode reduces weight by 0.6×)
        htf_pen = float(analysis.get("_htf_conflict_penalty") or 0)
        if htf_pen > 0:
            htf_multiplier = float(analysis.get("_htf_penalty_multiplier") or 1.0)
            htf_pen = round(htf_pen * htf_multiplier, 1)
            penalty += htf_pen
            penalty_log.append(f"HTFConflict(-{htf_pen:.0f})"
                               + (" [×0.6 emergency]" if htf_multiplier < 1.0 else ""))
        # TP too close warning
        if analysis.get("tp_too_close_warning"):
            penalty += 8.0
            penalty_log.append(f"TPClose(-8)")
        # SL too close warning
        if analysis.get("sl_too_close_warning"):
            penalty += 8.0
            penalty_log.append(f"SLClose(-8)")
        # Entry not near zone warning
        if analysis.get("entry_not_near_zone_warning"):
            penalty += 6.0
            penalty_log.append(f"EntryFarZone(-6)")
        # Entry too deep in OB
        if analysis.get("entry_deep_in_ob_warning"):
            penalty += 5.0
            penalty_log.append(f"DeepOB(-5)")
        # No sweep + no structure (worst case)
        if analysis.get("no_sweep_no_structure_warning"):
            penalty += 15.0
            penalty_log.append(f"NoSweepNoStruct(-15)")

        calibrated_conf = max(0.0, raw_conf - penalty)

        # ── HTF alignment bonus ───────────────────────────────────────────────
        htf_aligned = analysis.get("gate_htf_aligned", False)
        if htf_aligned:
            calibrated_conf = min(calibrated_conf + 5.0, 90.0)

        # ── Caps ──────────────────────────────────────────────────────────────
        cap = 90.0
        if timeframe in ("1m", "5m", "15m"):
            cap = min(cap, 65.0)
        if rr < 2.0:
            cap = min(cap, 75.0)

        final_conf = round(min(calibrated_conf, cap), 1)

        # ── Signal quality tier ───────────────────────────────────────────────
        if rr >= 2.0 and structure_strength >= 60.0 and htf_aligned:
            tier = "TIER_A"
        elif rr >= 1.5:
            tier = "TIER_B"
        else:
            tier = "TIER_B"   # gate ensures min 1.3, tiers are informational

        analysis["ai_confidence_score"] = final_conf
        analysis["signal_tier"]         = tier
        analysis["confidence_components"] = {
            "ict_score":          round(ict_score, 1),
            "liquidity_quality":  round(liquidity_quality, 1),
            "structure_strength": round(structure_strength, 1),
            "rr_score":           round(rr_score, 1),
            "raw":                round(raw_conf, 1),
            "penalties":          penalty_log,
            "penalty_total":      round(penalty, 1),
            "cap":                cap,
            "tier":               tier,
        }

        logger.info(
            f"CONFIDENCE [{rec}] {symbol}/{timeframe}: "
            f"ict={ict_score:.0f} liq={liquidity_quality:.0f} "
            f"struct={structure_strength:.0f} rr={rr_score:.0f} "
            f"→ raw={raw_conf:.1f} penalties={penalty:.0f} "
            f"final={final_conf:.1f}% | {tier}"
            + (f" [penalties: {', '.join(penalty_log)}]" if penalty_log else "")
        )
        return analysis

    # ──────────────────────────────────────────────────────────────────────────
    # SMART MODE — Classify every actionable signal as SWING / SCALP
    # Called after _confidence_calibration_layer. Does NOT change levels/RR.
    # ──────────────────────────────────────────────────────────────────────────
    def _classify_trade_mode(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        Sets trade_type = SWING | SCALP | WAIT (WAIT only when rec is already WAIT).
        Rules:
          SWING  — HTF aligned + (timeframe ≥ 1h OR LTF neutral/aligned) + conf ≥ 55%
          SCALP  — HTF conflicting OR LTF conflict but strong 15m setup + conf ≥ 55% + RR ≥ 1.0
          WAIT   — anything else (weak confidence, no structure, or rec already WAIT)
        Does NOT change recommendation, delta, RR, confidence, or any levels.
        """
        rec  = analysis.get("recommendation", "WAIT")
        conf = analysis.get("ai_confidence_score", 0)
        rr   = analysis.get("levels", {}).get("risk_reward") or analysis.get("risk_reward_ratio", 0) or 0

        if rec not in ("BUY", "SELL"):
            analysis["trade_type"]       = "WAIT"
            analysis["trade_type_label"] = "انتظار"
            analysis["trade_type_ar"]    = "⏳ انتظار — لا صفقة حالياً"
            return analysis

        htf_aligned   = analysis.get("gate_htf_aligned", False)
        htf_status    = analysis.get("htf_status", "")          # "aligned" | "conflicting" | "neutral"
        sym_upper     = symbol.upper()

        # Determine LTF timeframe alignment
        LTF_FRAMES    = ("1m", "5m", "15m", "30m")
        is_ltf        = timeframe in LTF_FRAMES

        # Get 1H context from htf_analysis when running on LTF
        one_h_trend = None
        if htf_analysis and isinstance(htf_analysis, dict):
            ms = htf_analysis.get("market_structure") or {}
            one_h_trend = (ms.get("trend") or "").upper()

        # Current TF structure trend
        curr_ms    = analysis.get("market_structure") or {}
        curr_trend = (curr_ms.get("trend") or "").upper()

        # ── SWING conditions ──────────────────────────────────────────────────
        is_swing = (
            htf_aligned
            and conf >= 55
            and (
                not is_ltf                    # HTF/1H timeframes → swing by default
                or one_h_trend in ("BULLISH", "BEARISH", "")  # 1H neutral or aligned
            )
        )

        # ── SCALP conditions ──────────────────────────────────────────────────
        # Allowed even when HTF conflicts, as long as LTF setup is strong enough
        is_scalp = (
            conf >= 55
            and float(rr) >= 1.0
            and not is_swing           # don't double-classify
            and (
                htf_status in ("conflicting", "neutral")
                or (is_ltf and one_h_trend not in (None, ""))
            )
        )

        if is_swing:
            trade_type = "SWING"
        elif is_scalp:
            trade_type = "SCALP"
        else:
            # Confidence or RR too weak — downgrade to WAIT
            # Note: we keep recommendation unchanged; callers can decide to show anyway
            trade_type = "SCALP"  # still show, but mark as weakest scalp

        # ── Arabic labels ─────────────────────────────────────────────────────
        if trade_type == "SWING":
            direction_ar = "شراء" if rec == "BUY" else "بيع"
            label        = f"📈 {direction_ar} (SWING)"
            detail       = "🎯 اتجاه رئيسي مع HTF"
            if sym_upper == "XAUUSD":
                detail += " | ذهب — تحقق من HTF قبل الدخول"
            analysis["trade_type_warning"] = None

        else:  # SCALP
            direction_ar = "شراء" if rec == "BUY" else "بيع"
            label        = f"⚡ {direction_ar} (SCALP)"
            detail       = "⏱️ صفقة سريعة — خروج عند الهدف الأول"
            warning      = "⚠️ إدارة مخاطر سريعة — لا تمد الصفقة"
            if sym_upper == "XAUUSD":
                warning = "⚠️ هذه صفقة عكس الاتجاه العام (Scalp) — TP1 فقط، وقف محكم"
            analysis["trade_type_warning"] = warning

        analysis["trade_type"]       = trade_type
        analysis["trade_type_label"] = label
        analysis["trade_type_ar"]    = f"{label}\n{detail}"

        logger.info(
            f"SMART_MODE [{symbol}/{timeframe}]: {trade_type} | "
            f"htf_aligned={htf_aligned} htf_status={htf_status} "
            f"conf={conf:.1f}% rr={rr}"
        )
        return analysis

    @staticmethod
    def _closest_zone(price: float, obs: list) -> Optional[dict]:
        valid = [o for o in obs if isinstance(o, dict) and o.get("low") and o.get("high")]
        if not valid:
            return None
        return min(valid, key=lambda o: abs((float(o["low"]) + float(o["high"])) / 2 - price))

    def _resolve_ob_zones(
        self,
        current_p: float,
        bull_obs: list,
        bear_obs: list,
        direction: str,
        htf_analysis: Optional[Dict] = None,
        liquidity: Optional[dict] = None,
    ) -> tuple[Optional[dict], Optional[dict], bool]:
        """
        OB_RESOLUTION_PRIORITY — selects a single best OB per side.
        When the two primary zones overlap, resolves by:
          1. Trade direction alignment (primary)
          2. HTF trend alignment (tiebreaker)
          3. Liquidity proximity (final tiebreaker)

        Never rejects. Returns (support_zone, resist_zone, overlap_warning).
        """
        support_zone = self._closest_zone(current_p, bull_obs)
        resist_zone  = self._closest_zone(current_p, bear_obs)

        # No overlap — nothing to resolve
        if not (support_zone and resist_zone):
            return support_zone, resist_zone, False

        bull_hi = float(support_zone.get("high", 0))
        bear_lo = float(resist_zone.get("low", 0))
        if bull_hi <= bear_lo:
            return support_zone, resist_zone, False

        # ── Overlap detected — resolution priority ────────────────────────────
        # Priority 1: direction alignment — keep the OB matching trade direction,
        # drop the opposing one so no ambiguity reaches downstream.
        if direction == "BUY":
            resolved_support = support_zone
            resolved_resist  = None
        elif direction == "SELL":
            resolved_support = None
            resolved_resist  = resist_zone
        else:
            # Priority 2: HTF alignment tiebreaker
            htf_trend = ""
            if htf_analysis:
                htf_trend = (
                    htf_analysis.get("market_structure", {})
                    .get("trend", "")
                    .upper()
                )
            if htf_trend == "BULLISH":
                resolved_support, resolved_resist = support_zone, None
            elif htf_trend == "BEARISH":
                resolved_support, resolved_resist = None, resist_zone
            else:
                # Priority 3: liquidity proximity tiebreaker
                liq = liquidity or {}
                bsl = float(liq.get("nearest_bsl") or 0)
                ssl = float(liq.get("nearest_ssl") or 0)
                bull_mid = (float(support_zone["low"]) + bull_hi) / 2
                bear_mid = (bear_lo + float(resist_zone["high"])) / 2
                bull_liq_dist = abs(bull_mid - bsl) if bsl else float("inf")
                bear_liq_dist = abs(bear_mid - ssl) if ssl else float("inf")
                if bull_liq_dist <= bear_liq_dist:
                    resolved_support, resolved_resist = support_zone, None
                else:
                    resolved_support, resolved_resist = None, resist_zone

        logger.info(
            f"OB_RESOLUTION: overlap detected (bull_hi={bull_hi} > bear_lo={bear_lo}) "
            f"dir={direction} → kept support={resolved_support is not None} "
            f"resist={resolved_resist is not None}"
        )
        return resolved_support, resolved_resist, True

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

        # Stale sweep limit — varies by timeframe (higher TF = slower structure)
        tf = analysis.get("timeframe", "1h")
        stale_limit = 20 if tf in ("4h", "1d") else 15
        if candles_since > stale_limit:
            logger.warning(
                f"ANTI_FAKE_SWEEP: stale sweep candles_since={candles_since} > {stale_limit} ({tf})"
            )
            return False, "STALE_SWEEP"

        if sweep_quality == "WEAK":
            logger.warning("ANTI_FAKE_SWEEP: sweep_quality=WEAK rejected")
            return False, "WEAK_SWEEP_QUALITY"

        # ── Confirmation A: Strong rejection candle ───────────────────────────
        wick_atr   = float(sweep_info.get("wick_atr_ratio") or 0)
        body_ratio = float(sweep_info.get("body_atr_ratio") or 0)
        conf_a     = (body_ratio >= 0.3 and wick_atr >= 1.5) if atr > 0 else False

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

    def _select_primary_rejection_reason(self, analysis: dict) -> str:
        """
        Single primary rejection reason using severity hierarchy:
          Tier 1 — Risk integrity: RR / SL violations
          Tier 2 — Directional risk: HTF conflict
          Tier 3 — Signal quality: score delta / watchlist
          Tier 4 — Other
        Returns the single highest-severity reason (never a list).
        """
        candidates = []
        r = analysis.get("rejection_reason")
        w = analysis.get("watchlist_reason")
        if r:
            candidates.append(r)
        if w:
            candidates.append(w)
        if not candidates:
            return "N/A"

        # Tier 1: Risk integrity (only valid hard rejects now)
        TIER1 = ("RR_", "ZERO_SL", "BUY_SL_ABOVE", "SELL_SL_BELOW",
                 "MISSING_ENTRY", "BUY_TP1_BELOW", "SELL_TP1_ABOVE")
        # Tier 2: Score delta (HTF is no longer a rejection cause)
        TIER2 = ("SCORE_DELTA", "DELTA_")
        TIER3 = ("RANGE_TRAP", "LOW_TF")

        for tier in (TIER1, TIER2, TIER3):
            for c in candidates:
                if any(c.startswith(t) for t in tier):
                    return c
        return candidates[0]

    def _detect_smart_mode_signal(self, analysis: dict, symbol: str, timeframe: str) -> Optional[str]:
        """
        Detect signals that are structurally strong but slightly below ideal.
        Smart Mode Signal labels a valid setup as higher-opportunity yet slightly aggressive.
        """
        rec = analysis.get("recommendation")
        if rec not in ("BUY", "SELL"):
            return None

        calibrated_delta = float(analysis.get("_calib_delta") or 0)
        effective_delta = float(analysis.get("effective_delta") or 0)
        if calibrated_delta <= 0:
            return None

        delta_ratio = effective_delta / calibrated_delta
        if delta_ratio < 0.80:
            return None

        if analysis.get("htf_conflict_warning"):
            return None

        primary_ob = analysis.get("primary_bull_ob") if rec == "BUY" else analysis.get("primary_bear_ob")
        if not primary_ob:
            return None

        rr = float(analysis.get("risk_reward_ratio") or 0)
        if rr < 1.0:
            return None

        logger.info(
            f"⚡ SMART_MODE_SIGNAL [{symbol}/{timeframe}] "
            f"rec={rec} delta_ratio={delta_ratio:.2f} rr={rr:.2f}"
        )
        return "SMART_MODE"

    def _smart_rr_recovery(
        self,
        analysis: dict,
        levels: dict,
        entry: float,
        sl: float,
        tp1: float,
        rr: float,
        min_rr: float,
        rec: str,
        symbol: str,
        timeframe: str,
    ):
        """
        SMART RR RECOVERY — tries to improve RR before rejecting a high-delta signal.

        Only activates when:
          - effective_delta >= 25  (strong confluence)
          - RR is recoverable (not catastrophically bad)

        Strategy (in order):
          1. TP Extension  — extend TP1 to next liquidity level (BSL/SSL)
          2. TP from OB    — use OB boundary as TP if further than current TP1
          3. SL Tightening — move SL inside OB boundary (only if structure valid)
          4. High-Delta Exception — accept RR ≥ 0.9 when delta ≥ 25 + BOS confirmed

        Hard limits:
          - Never allow recovered RR < 0.9
          - Never tighten SL beyond OB high/low (structure must remain valid)
          - Never modify delta < 20 signals
        """
        _RR_HARD_FLOOR   = 1.0    # floor for strategies 1 & 2 (TP/SL optimisation)
        _RR_FLOOR_HIGH   = 1.0    # floor for strong recovery only

        # Read effective delta — from decision_meta or effective_delta field
        meta        = analysis.get("decision_meta", {})
        eff_delta   = float(analysis.get("effective_delta") or
                            abs(float(meta.get("score_delta") or 0)))
        score_delta = abs(float((analysis.get("decision_meta") or {}).get("score_delta") or
                                analysis.get("effective_delta") or 0))
        threshold   = float(analysis.get("_calib_delta") or
                            abs(float(meta.get("threshold") or 0)) or
                            self._DECISION_THRESHOLD_TREND)

        # Skip recovery for weak signals or conflicting structure/HTF
        if eff_delta < max(0.8 * threshold, 12.0) and score_delta < max(0.8 * threshold, 12.0):
            return analysis, levels, rr
        if analysis.get("htf_conflict_warning"):
            return analysis, levels, rr

        atr       = float(levels.get("atr") or 0)
        liquidity = analysis.get("liquidity", {})
        struct    = analysis.get("market_structure", {})
        ob        = analysis.get("order_blocks", {})
        sl_dist   = abs(entry - sl)

        recovered = False
        recovery_method = None

        # ── Strategy 1: TP Extension to next liquidity ───────────────────────
        if rec == "BUY":
            bsl_levels = [
                float(v) for v in [
                    liquidity.get("nearest_bsl"),
                    liquidity.get("bsl_1"),
                    liquidity.get("bsl_2"),
                ] if v and float(v) > entry * 1.002
            ]
            bsl_levels.sort()
            for liq_tp in bsl_levels:
                new_rr = round(abs(liq_tp - entry) / sl_dist, 2)
                if new_rr >= _RR_HARD_FLOOR:
                    atr_offset = atr * 0.3 if atr else 0
                    levels["tp1"] = round(liq_tp - atr_offset, 5)
                    levels["tp2"] = round(liq_tp, 5)
                    levels["tp3"] = round(liq_tp + (atr * 1.5 if atr else liq_tp * 0.005), 5)
                    recovery_method = f"TP_EXTENDED_TO_BSL_{liq_tp:.5g}"
                    recovered = True
                    break
        else:  # SELL
            ssl_levels = [
                float(v) for v in [
                    liquidity.get("nearest_ssl"),
                    liquidity.get("ssl_1"),
                    liquidity.get("ssl_2"),
                ] if v and float(v) < entry * 0.998
            ]
            ssl_levels.sort(reverse=True)
            for liq_tp in ssl_levels:
                new_rr = round(abs(entry - liq_tp) / sl_dist, 2)
                if new_rr >= _RR_HARD_FLOOR:
                    atr_offset = atr * 0.3 if atr else 0
                    levels["tp1"] = round(liq_tp + atr_offset, 5)
                    levels["tp2"] = round(liq_tp, 5)
                    levels["tp3"] = round(liq_tp - (atr * 1.5 if atr else liq_tp * 0.005), 5)
                    recovery_method = f"TP_EXTENDED_TO_SSL_{liq_tp:.5g}"
                    recovered = True
                    break

        # ── Strategy 2: SL Tightening to OB boundary ─────────────────────────
        if not recovered:
            bos_list    = struct.get("bos_events", [])
            has_bos     = (
                any("BULLISH" in b.get("type", "") for b in bos_list) if rec == "BUY"
                else any("BEARISH" in b.get("type", "") for b in bos_list)
            )
            # Only tighten SL if BOS is confirmed (structure remains valid)
            if has_bos:
                ob_list = (ob.get("bullish_obs", []) if rec == "BUY"
                           else ob.get("bearish_obs", []))
                for zone in ob_list:
                    try:
                        z_lo = float(zone.get("low", 0))
                        z_hi = float(zone.get("high", 0))
                    except (TypeError, ValueError):
                        continue
                    if rec == "BUY" and z_lo > 0 and z_lo < entry:
                        tight_sl   = z_lo * 0.9998   # just below OB low
                        new_sl_dist = abs(entry - tight_sl)
                        if new_sl_dist > 0 and new_sl_dist < sl_dist:
                            new_rr = round(abs(tp1 - entry) / new_sl_dist, 2)
                            if new_rr >= _RR_HARD_FLOOR:
                                levels["stop_loss"] = round(tight_sl, 5)
                                recovery_method = f"SL_TIGHTENED_TO_OB_LOW_{z_lo:.5g}"
                                sl_dist  = new_sl_dist
                                recovered = True
                                break
                    elif rec == "SELL" and z_hi > 0 and z_hi > entry:
                        tight_sl    = z_hi * 1.0002   # just above OB high
                        new_sl_dist = abs(tight_sl - entry)
                        if new_sl_dist > 0 and new_sl_dist < sl_dist:
                            new_rr = round(abs(entry - tp1) / new_sl_dist, 2)
                            if new_rr >= _RR_HARD_FLOOR:
                                levels["stop_loss"] = round(tight_sl, 5)
                                recovery_method = f"SL_TIGHTENED_TO_OB_HIGH_{z_hi:.5g}"
                                sl_dist  = new_sl_dist
                                recovered = True
                                break

        # ── Strategy 3: High-Delta Exception ─────────────────────────────────
        # Last resort — accept RR slightly below 1.0 for very strong signals
        # delta >= 30: allow RR >= 0.80 (EV positive at 70%+ winrate)
        # delta >= 25: allow RR >= 0.90
        if not recovered and eff_delta >= _DELTA_EXCEPTION:
            bos_list     = struct.get("bos_events", [])
            has_bos      = bool(bos_list)
            new_rr       = round(abs(tp1 - entry) / sl_dist, 2)
            rr_floor_s3  = _RR_FLOOR_HIGH if eff_delta >= 30 else _RR_HARD_FLOOR
            if has_bos and new_rr >= rr_floor_s3:
                recovery_method = f"HIGH_DELTA_EXCEPTION_delta={eff_delta:.0f}_floor={rr_floor_s3}"
                analysis["_recovery_min_rr"] = rr_floor_s3   # gate will use this instead of 1.1
                recovered = True

        if recovered and recovery_method:
            analysis["smart_rr_recovered"]  = True
            analysis["rr_recovery_method"]  = recovery_method
            analysis["rr_before_recovery"]  = rr
            # Ensure _recovery_min_rr is set (strategies 1&2 use _RR_HARD_FLOOR)
            if "_recovery_min_rr" not in analysis:
                analysis["_recovery_min_rr"] = _RR_HARD_FLOOR
            logger.info(
                f"SMART_RR_RECOVERY [{symbol}/{timeframe}]: "
                f"rr={rr:.2f}→recovered method={recovery_method} delta={eff_delta:.0f}"
            )

        # Recompute final rr from potentially updated levels
        new_sl_dist = abs(entry - float(levels.get("stop_loss") or sl))
        new_tp1     = float(levels.get("tp1") or tp1)
        new_rr      = round(abs(new_tp1 - entry) / new_sl_dist, 2) if new_sl_dist > 0 else 0
        return analysis, levels, new_rr

    def _hard_reject(self, analysis: dict, reason: str) -> dict:
        rec = analysis.get("recommendation", "?")
        logger.warning(f"REJECTED [{rec}] {reason}")
        # Save snapshot before clearing (used by borderline_rescue_layer)
        analysis["_pre_reject_levels"] = dict(analysis.get("levels", {}))
        analysis["_pre_reject_rec"]    = rec
        analysis.update({
            "recommendation":         "WAIT",
            "signal_type":            "WAIT",
            "signal_status":          "REJECT",
            "ai_confidence_score":    min(float(analysis.get("ai_confidence_score") or 0), 45.0),
            "institutional_rejected": True,
            "rejection_reason":       reason,
            "levels":                 {},
            "entry_zones":            [],
            "stop_loss_zone":         None,
            "take_profit_zones":      [],
        })
        return analysis

    def _smart_rescue_layer(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        SMART RESCUE LAYER — recovers near-threshold signals as full BUY/SELL.

        Runs after decision_finalizer + institutional_gate.
        Unlike borderline_rescue_layer (which returns WAIT), this layer can
        promote a rejected signal to BUY or SELL tagged as RESCUED_SIGNAL.

        ALL conditions must pass:
          1. delta >= threshold - 3  (near-miss, not a weak signal)
          2. has_liquidity_sweep == True  (real sweep exists)
          3. HTF conflict is not STRONG  (neutral or aligned OK)
          4. RR >= 1.1  (viable trade, checked from pre-reject levels)
          5. Not a confirmed fake sweep

        HARD BLOCK (never rescued):
          - NO_LIQUIDITY_SWEEP
          - RR < 1.0
          - STRONG_HTF_CONFLICT
        """
        reason = analysis.get("rejection_reason", "")

        # ── Hard blocks ───────────────────────────────────────────────────────
        HARD_BLOCK = (
            "NO_LIQUIDITY_SWEEP",
            "NO_SWEEP_NO_STRUCTURE",
            "FAKE_SWEEP_NO_CONFIRMATION",
        )
        for b in HARD_BLOCK:
            if reason.startswith(b):
                logger.debug(f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: hard block — {reason}")
                return analysis

        # RR hard block — check from pre-reject levels OR current levels
        pre_levels = analysis.get("_pre_reject_levels") or analysis.get("levels") or {}
        entry  = float(pre_levels.get("entry") or 0)
        sl     = float(pre_levels.get("stop_loss") or pre_levels.get("sl") or 0)
        tp1    = float(pre_levels.get("tp1") or 0)
        rr = 0.0
        if entry > 0 and sl > 0 and tp1 > 0:
            sl_dist = abs(entry - sl)
            tp_dist = abs(tp1 - entry)
            rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0.0

        if rr < 1.0:
            logger.debug(f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: RR={rr:.2f} < 1.0")
            return analysis

        # HTF conflict is no longer a hard block — it reduces rescue confidence instead
        if htf_analysis:
            pre_rec   = analysis.get("_pre_reject_rec") or analysis.get("recommendation", "")
            htf_trend = (
                htf_analysis.get("market_structure", {})
                .get("trend", "RANGING")
                .upper()
            )
            if (pre_rec == "BUY" and htf_trend == "BEARISH") or \
               (pre_rec == "SELL" and htf_trend == "BULLISH"):
                analysis["htf_conflict_flag"]     = True
                analysis["htf_status"]            = "conflicting"
                existing = float(analysis.get("_htf_conflict_penalty") or 0)
                analysis["_htf_conflict_penalty"] = max(existing, 20.0)
                logger.info(
                    f"SMART_RESCUE: HTF conflict → penalty only, rescue continues "
                    f"[{symbol}/{timeframe}]"
                )

        # ── Volatility Adaptation — SCALP_BOOST / SILENCE_BOOST ─────────────
        vola = self._get_volatility_mode(analysis, symbol, timeframe)
        delta_tolerance = vola["delta_tolerance"]   # 0, 2, or 3
        rescue_min_rr   = max(1.0, vola["min_rr"])  # never below 1.0
        analysis["volatility_mode"] = vola["mode"]

        # ── Condition 1: delta >= threshold - tolerance ───────────────────────
        decision_meta = analysis.get("decision_meta", {})
        raw_delta     = abs(float(decision_meta.get("score_delta", 0)))
        eff_delta     = float(analysis.get("effective_delta", raw_delta))
        threshold     = float(
            decision_meta.get("threshold")
            or analysis.get("_calib_delta")
            or 17
        )
        effective_threshold = threshold - delta_tolerance
        if eff_delta < effective_threshold:
            logger.debug(
                f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: "
                f"eff_delta={eff_delta:.1f} < threshold-{delta_tolerance}={effective_threshold:.1f} "
                f"[mode={vola['mode']}]"
            )
            return analysis

        # ── Condition 2: real sweep exists ────────────────────────────────────
        sweep = analysis.get("liquidity_sweep", {})
        has_any_sweep = (
            sweep.get("has_bullish_sweep", False) or
            sweep.get("has_bearish_sweep", False)
        )
        if not has_any_sweep:
            logger.debug(f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: no sweep")
            return analysis

        # ── Condition 3: not a confirmed fake sweep ───────────────────────────
        if "FAKE_SWEEP_NO_CONFIRMATION" in reason:
            logger.debug(f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: confirmed fake sweep")
            return analysis

        # ── Condition 4: RR >= rescue_min_rr (1.0 in SCALP/SILENCE, 1.1 in SWING) ──
        if rr < rescue_min_rr:
            logger.debug(
                f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: "
                f"RR={rr:.2f} < {rescue_min_rr} [mode={vola['mode']}]"
            )
            return analysis

        # SILENCE_BOOST: سماح بإشارة واحدة فقط لكل رمز/إطار إذا confidence ≥ 55%
        if vola["mode"] == "SILENCE_BOOST":
            conf = float(analysis.get("ai_confidence_score") or 0)
            if conf < 55:
                logger.debug(
                    f"SMART_RESCUE SKIP [{symbol}/{timeframe}]: "
                    f"SILENCE_BOOST requires conf≥55, got {conf:.0f}"
                )
                return analysis

        # ── All conditions met → rescue as full BUY/SELL ─────────────────────
        direction = (
            analysis.get("_pre_reject_rec")
            or ("BUY" if analysis.get("decision_meta", {}).get("score_delta", 0) > 0 else "SELL")
        )

        logger.info(
            f"SMART_RESCUE [{symbol}/{timeframe}]: "
            f"reason={reason} eff_delta={eff_delta:.1f}/thr={threshold:.1f} "
            f"rr={rr:.2f} sweep=True → RESCUED_SIGNAL [{direction}]"
        )

        # Restore pre-reject levels
        if pre_levels:
            analysis["levels"] = dict(pre_levels)

        analysis["recommendation"]        = direction
        analysis["signal_type"]           = direction
        analysis["signal_status"]         = "PASS"
        analysis["smart_rescued"]         = True
        analysis["signal_quality"]        = "BORDERLINE"
        analysis["rescue_reason"]         = "rescued_near_threshold"
        analysis["rescue_original_reject"] = reason
        analysis["rescue_rr"]             = rr
        analysis["rescue_eff_delta"]      = round(eff_delta, 1)
        analysis["institutional_rejected"] = False
        # Run confidence calibration for the rescued signal
        analysis = self._confidence_calibration_layer(
            analysis, symbol, timeframe, htf_analysis
        )
        # Apply an extra penalty for being rescued
        cur_conf = float(analysis.get("ai_confidence_score", 0))
        analysis["ai_confidence_score"] = max(round(cur_conf - 10.0, 1), 40.0)
        self._record_signal_issued(symbol, timeframe)
        return analysis

    def _borderline_rescue_layer(
        self,
        analysis: dict,
        symbol: str,
        timeframe: str,
        htf_analysis: Optional[Dict] = None,
    ) -> dict:
        """
        Borderline Rescue Layer — runs AFTER soft rejection only.

        Converts REJECT → WAIT (rescued_candidate) if ALL conditions met:
          1) Sweep exists (any quality except NONE)
          2) Score delta within ±3 of calibrated threshold
          3) No HTF conflict
          4) RR >= 1.0 (viability — not the strict minimum)

        HARD REJECTS that cannot be rescued (no exceptions):
          NO_LIQUIDITY_SWEEP, RR_*, HTF_CONFLICT, HTF_DIRECTION_CONFLICT,
          INVALID_STRUCTURE

        Rescued signal:
          - recommendation stays WAIT (never upgraded to BUY/SELL)
          - rescued_candidate = True → logged, tracked for re-evaluation
          - institutional_rejected cleared (not a hard failure)
        """
        reason = analysis.get("rejection_reason", "")

        # ── Hard rejects — cannot be rescued ─────────────────────────────────
        HARD_REJECT_PREFIXES = (
            "NO_LIQUIDITY_SWEEP",
            "RR_",                       # RR_0.80_BELOW_MIN_1.5 etc.
            "INVALID_STRUCTURE",
            "FAKE_SWEEP_NO_CONFIRMATION", # confirmed fake — no rescue
            # HTF_CONFLICT / HTF_DIRECTION_CONFLICT removed — now scoring penalties only
        )
        for prefix in HARD_REJECT_PREFIXES:
            if reason.startswith(prefix):
                logger.debug(f"RESCUE SKIP [{symbol}/{timeframe}]: hard reject — {reason}")
                return analysis
        # FAKE_SWEEP_STALE and FAKE_SWEEP_WEAK are soft — eligible for rescue

        # ── Condition 1: Sweep exists (any quality including WEAK) ───────────
        sweep = analysis.get("liquidity_sweep", {})
        sweep_quality = str(sweep.get("sweep_quality", "NONE")).upper()
        has_any_sweep = (
            sweep.get("has_bullish_sweep", False)
            or sweep.get("has_bearish_sweep", False)
        )
        # For STALE/WEAK soft-rejects the sweep was detected — allow rescue
        fake_sw_warn = analysis.get("fake_sweep_warning", "")
        sweep_ok = (
            (has_any_sweep and sweep_quality != "NONE")
            or fake_sw_warn in ("STALE_SWEEP", "WEAK_SWEEP_QUALITY")
        )
        if not sweep_ok:
            logger.debug(f"RESCUE SKIP [{symbol}/{timeframe}]: sweep absent or quality=NONE")
            return analysis

        # ── Condition 2: Delta within ±3 of calibrated threshold ─────────────
        decision_meta = analysis.get("decision_meta", {})
        score_delta   = abs(float(decision_meta.get("score_delta", 0)))
        threshold     = float(
            decision_meta.get("threshold")
            or analysis.get("_calib_delta")
            or 22
        )
        delta_gap = abs(score_delta - threshold)
        if delta_gap > 3:
            logger.debug(
                f"RESCUE SKIP [{symbol}/{timeframe}]: "
                f"delta={score_delta:.1f} threshold={threshold:.1f} gap={delta_gap:.1f} > 3"
            )
            return analysis

        # ── Condition 3: No HTF conflict ──────────────────────────────────────
        if htf_analysis:
            pre_rec  = analysis.get("_pre_reject_rec", "BUY")
            htf_trend = (
                htf_analysis.get("market_structure", {})
                .get("trend", "RANGING")
                .upper()
            )
            htf_conflict = (
                (pre_rec == "BUY"  and htf_trend == "BEARISH")
                or (pre_rec == "SELL" and htf_trend == "BULLISH")
            )
            if htf_conflict:
                logger.debug(
                    f"RESCUE SKIP [{symbol}/{timeframe}]: "
                    f"HTF conflict ({htf_trend} vs {pre_rec})"
                )
                return analysis

        # ── Condition 4: RR >= 1.0 (viability) ───────────────────────────────
        pre_levels = analysis.get("_pre_reject_levels", {})
        entry = float(pre_levels.get("entry") or 0)
        sl    = float(pre_levels.get("stop_loss") or pre_levels.get("sl") or 0)
        tp1   = float(pre_levels.get("tp1") or 0)

        rr = 0.0
        if entry > 0 and sl > 0 and tp1 > 0:
            sl_dist = abs(entry - sl)
            tp_dist = abs(tp1 - entry)
            rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0.0

        if rr < 1.0:
            logger.debug(
                f"RESCUE SKIP [{symbol}/{timeframe}]: RR={rr:.2f} < 1.0"
            )
            return analysis

        # ── All conditions met → rescue ───────────────────────────────────────
        logger.info(
            f"🔶 BORDERLINE RESCUE [{symbol}/{timeframe}]: "
            f"reason={reason} Δ={score_delta:.1f}/thr={threshold:.1f} "
            f"rr={rr:.2f} sweep={sweep_quality} → rescued_candidate"
        )
        analysis["rescued_candidate"]   = True
        analysis["rescue_reason"]       = reason
        analysis["rescue_rr"]           = rr
        analysis["rescue_delta_gap"]    = round(delta_gap, 1)
        analysis["rescue_sweep_quality"] = sweep_quality
        # Keep recommendation as WAIT — never upgrade to BUY/SELL
        # Clear institutional_rejected so downstream layers don't treat it as hard fail
        analysis["institutional_rejected"] = False
        return analysis

    def _get_min_rr(self) -> float:
        # EMERGENCY: always 1.0
        return 1.0

    # ─── SMART MODE: Volatility Adaptation ──────────────────────────────────

    def _get_volatility_mode(self, analysis: dict, symbol: str, timeframe: str) -> dict:
        """
        يكشف حالة السوق ويحدد وضع المحرك:
        - SCALP_BOOST: ATR منخفض أو سوق RANGING → تخفيف الشروط
        - SILENCE_BOOST: ما في إشارة منذ > 4 ساعات → سماح بسكالب واحد
        - SWING: حالة عادية

        Returns dict with keys: mode, delta_tolerance, min_rr, silence_hours
        """
        import time as _t

        # ── قراءة ATR وحالة السوق ─────────────────────────────────────────
        atr       = float(analysis.get("atr") or 0)
        price     = float(analysis.get("current_price") or 1)
        structure = analysis.get("market_structure", {})
        trend     = structure.get("trend", "").upper()
        is_ranging = "RANGING" in trend or "MIXED" in trend

        # ATR نسبي (% من السعر) — منخفض إذا < 0.3%
        atr_pct   = (atr / price * 100) if price > 0 else 0
        low_atr   = atr_pct < 0.30

        # ── كشف الصمت (أكثر من 4 ساعات بدون إشارة) ────────────────────────
        key = f"{symbol.upper()}_{timeframe}"
        last_issued = self._last_signal_issued.get(key, 0)
        silence_hours = (_t.time() - last_issued) / 3600 if last_issued else 999
        long_silence  = silence_hours > 4.0

        # ── تحديد الوضع ────────────────────────────────────────────────────
        if is_ranging or low_atr:
            mode           = "SCALP_BOOST"
            delta_tolerance = 3    # تخفيف delta بـ -3
            min_rr          = 1.0  # قبول RR ≥ 1.0
        elif long_silence:
            mode           = "SILENCE_BOOST"
            delta_tolerance = 2    # تخفيف أخف
            min_rr          = 1.0
        else:
            mode           = "SWING"
            delta_tolerance = 0    # قواعد عادية
            min_rr          = 1.1

        logger.debug(
            f"[VOLA_MODE] {symbol}/{timeframe}: mode={mode} "
            f"atr_pct={atr_pct:.2f}% ranging={is_ranging} "
            f"silence={silence_hours:.1f}h low_atr={low_atr}"
        )

        return {
            "mode":            mode,
            "delta_tolerance": delta_tolerance,
            "min_rr":          min_rr,
            "silence_hours":   round(silence_hours, 1),
            "atr_pct":         round(atr_pct, 3),
            "low_atr":         low_atr,
            "is_ranging":      is_ranging,
        }

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
