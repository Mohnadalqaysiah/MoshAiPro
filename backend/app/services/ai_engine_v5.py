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
        logger.info(f"🚀 Mosh AI Engine v{self.version} initialized")
        logger.info(f"   └─ Gemini v2: {'✅' if gemini_engine.enabled else '❌'}")

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

            # ── Step 3: Gemini v2 Enhancement ───────────────────────────────
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
                        ltf_analysis = gemini_engine.merge_with_ict(ltf_analysis, gemini_result)
                        sig = gemini_result.get("signal", {})
                        logger.success(
                            f"   🤖 Gemini v2: {sig.get('recommendation')} | "
                            f"Grade: {sig.get('signal_grade')} | "
                            f"Score: {gemini_result.get('scoring_breakdown', {}).get('total', 0)}/100"
                        )
                except Exception as e:
                    logger.warning(f"   ⚠️ Gemini v2 failed (using ICT only): {e}")

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

            # ── بوابة السيولة الذكية (Smart Money Gate) ──────────────────────
            analysis = self._validate_sweep_gate(analysis)

            # ── التحقق الإجباري من صحة المستويات ────────────────────────────
            analysis = self._validate_trade_levels(analysis)

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

    def _validate_sweep_gate(self, analysis: dict) -> dict:
        """
        بوابة السيولة المحدّثة — تعتمد على Market Mode:

        RANGE Mode: Sweep إجباري (كما كان دائماً)
        TREND Mode: Sweep اختياري إذا توفر Momentum + BOS
        """
        rec = analysis.get("recommendation")
        if rec not in ("BUY", "SELL"):
            return analysis

        # ── جلب بيانات السياق ─────────────────────────────────────────────
        sweep = (
            analysis.get("liquidity_sweep")
            or analysis.get("liquidity", {}).get("sweep_analysis")
            or {}
        )
        market_mode    = analysis.get("market_mode", {}).get("mode", "RANGE")
        momentum_str   = analysis.get("momentum", {}).get("strength", "WEAK")
        range_conflict = analysis.get("range_conflict", {}).get("avoid_entry", False)

        has_confirmed_sweep = (
            sweep.get("has_bullish_sweep") if rec == "BUY"
            else sweep.get("has_bearish_sweep")
        )

        # ── حالة 1: Range Trap — يُمنع دائماً بغض النظر عن أي شيء ─────────
        if range_conflict:
            reason = "تداخل OBs بدون BOS واضح — سوق Range متضارب"
            short  = "RANGE_TRAP"
            return self._block_signal(analysis, rec, reason, short)

        # ── حالة 2: Sweep موجود → يجب تأكيد BOS أو CHOCH أيضاً ──────────
        if has_confirmed_sweep:
            sweep_quality = sweep.get("sweep_quality", "MODERATE")
            # BOS/CHOCH confirmation required — sweep وحده لا يكفي
            bos_data = analysis.get("market_structure", {})
            has_bos   = bos_data.get("has_bos",   False)
            has_choch = bos_data.get("has_choch", False)
            structure_confirmed = has_bos or has_choch

            if not structure_confirmed:
                logger.warning(
                    f"⚠️ Sweep Gate: sweep detected but no BOS/CHOCH confirmation [{rec}] → conf -10"
                )
                current_conf = float(analysis.get("ai_confidence_score") or 0)
                analysis["ai_confidence_score"] = max(0, current_conf - 10)
                analysis["sweep_no_structure"] = True

            logger.debug(
                f"✅ Sweep Gate PASSED [{rec}]: quality={sweep_quality} "
                f"structure={'✅' if structure_confirmed else '⚠️ missing'}"
            )
            return analysis

        # ── حالة 3: TREND Mode → Sweep اختياري ────────────────────────────
        if market_mode == "TREND":
            bos_present = analysis.get("market_mode", {}).get("has_bos", False)
            if bos_present and momentum_str in ("STRONG", "MODERATE"):
                # الدخول مسموح في Trend — لكن نخفّض الثقة
                logger.info(
                    f"✅ Sweep Gate BYPASSED [TREND mode] [{rec}]: "
                    f"momentum={momentum_str} BOS=True"
                )
                current_conf = float(analysis.get("ai_confidence_score") or 0)
                analysis["ai_confidence_score"] = max(0, current_conf - 15)
                analysis["trend_entry_no_sweep"] = True
                return analysis
            elif bos_present and momentum_str == "WEAK":
                reason = "Trend Mode لكن Momentum ضعيف — انتظر Pullback أو Retest"
                short  = "TREND_WEAK_MOMENTUM"
                return self._block_signal(analysis, rec, reason, short)
            else:
                reason = "Trend بدون BOS مؤكد — غير مؤهل للدخول"
                short  = "TREND_NO_BOS"
                return self._block_signal(analysis, rec, reason, short)

        # ── حالة 4: RANGE Mode بدون Sweep ─────────────────────────────────
        has_any_sweep = (
            bool(sweep.get("ssl_sweep")) if rec == "BUY"
            else bool(sweep.get("bsl_sweep"))
        )
        if has_any_sweep:
            reason = "اكتساح سيولة بدون رفض مؤكد (Sweep ≠ Rejection)"
            short  = "SWEEP_NO_REJECTION"
        else:
            reason = "Range Mode — لم يُكتشف اكتساح سيولة (شرط ICT الأساسي)"
            short  = "NO_SWEEP"

        return self._block_signal(analysis, rec, reason, short)

    def _block_signal(self, analysis: dict, rec: str, reason: str, short: str) -> dict:
        """تحويل إشارة لـ WAIT مع مسح المستويات وتسجيل السبب"""
        logger.warning(
            f"🚫 Sweep Gate BLOCKED [{rec}] → WAIT | reason={short}"
        )
        analysis["recommendation"]      = "WAIT"
        analysis["signal_type"]         = "WAIT"
        analysis["ai_confidence_score"] = min(
            float(analysis.get("ai_confidence_score") or 0), 39.0
        )
        analysis["sweep_gate_blocked"]  = True
        analysis["sweep_gate_reason"]   = short

        conf_data = analysis.get("confluence", {})
        if isinstance(conf_data, dict):
            factors = conf_data.get("factors", [])
            if isinstance(factors, list):
                factors.insert(0, f"🚫 Sweep Gate: {reason}")

        # مسح المستويات — لا نعرض entry/SL/TP من إشارة محظورة
        analysis["levels"]            = {}
        analysis["entry_zones"]       = []
        analysis["stop_loss_zone"]    = None
        analysis["take_profit_zones"] = []

        return analysis

    def _validate_trade_levels(self, analysis: dict) -> dict:
        """
        ─── Validation Layer الشامل ─────────────────────────────────────────
        يُنفَّذ بعد كل توليد إشارة ويفحص:
          1. TP ordering: BUY → TP1<TP2، SELL → TP1>TP2  (يصحّح تلقائياً)
          2. Direction sanity: sl/entry/tp في الاتجاه الصحيح
          3. R/R calculation صحيح + رفض إذا < 1.2
          4. Distance sanity: SL/Entry/TP ليست متطابقة أو صفر
          5. Zone alignment: SELL قرب resistance، BUY قرب support
          6. OB conflict: support.max < resistance.min
          7. Wyckoff / Premium-Discount consistency
          8. Confidence cap: إذا R/R < 1.5 → max 75%
        """
        rec    = analysis.get("recommendation")
        levels = analysis.get("levels", {})
        if rec not in ("BUY", "SELL") or not levels:
            return analysis

        entry = float(levels.get("entry") or 0)
        sl    = float(levels.get("stop_loss") or 0)
        tp1   = float(levels.get("tp1") or 0)
        tp2   = float(levels.get("tp2") or 0)

        if not entry or not sl or not tp1:
            return analysis

        # ── 1. تصحيح ترتيب TP ────────────────────────────────────────────
        if rec == "BUY":
            # BUY: يجب tp1 < tp2
            if tp2 and tp1 > tp2:
                logger.info(f"🔧 TP order fix [BUY]: swapping tp1={tp1} <> tp2={tp2}")
                levels["tp1"], levels["tp2"] = tp2, tp1
                tp1, tp2 = tp2, tp1
        elif rec == "SELL":
            # SELL: يجب tp1 > tp2
            if tp2 and tp1 < tp2:
                logger.info(f"🔧 TP order fix [SELL]: swapping tp1={tp1} <> tp2={tp2}")
                levels["tp1"], levels["tp2"] = tp2, tp1
                tp1, tp2 = tp2, tp1

        # ── 2. Direction sanity ───────────────────────────────────────────
        if rec == "BUY"  and not (sl < entry < tp1):
            logger.warning(f"⛔ Levels INVALID [BUY]: sl={sl} entry={entry} tp1={tp1} → WAIT")
            return self._reject_signal(analysis, "INVALID_LEVELS_BUY")
        if rec == "SELL" and not (tp1 < entry < sl):
            logger.warning(f"⛔ Levels INVALID [SELL]: tp1={tp1} entry={entry} sl={sl} → WAIT")
            return self._reject_signal(analysis, "INVALID_LEVELS_SELL")

        # ── 3. R/R حساب صحيح + رفض < 1.2 ────────────────────────────────
        sl_dist  = abs(entry - sl)
        tp1_dist = abs(tp1 - entry)
        if sl_dist <= 0:
            return self._reject_signal(analysis, "ZERO_SL_DISTANCE")

        rr = round(tp1_dist / sl_dist, 2)
        levels["risk_reward"] = rr
        analysis["risk_reward_ratio"] = rr

        if rr < 1.2:
            logger.warning(f"⛔ R/R too low [{rec}]: rr={rr} < 1.2 → WAIT")
            return self._reject_signal(analysis, f"LOW_RR_{rr}")

        # ── 4. Confidence cap: R/R < 1.5 → max 75% ───────────────────────
        if rr < 1.5:
            current_conf = float(analysis.get("ai_confidence_score") or 0)
            if current_conf > 75:
                logger.info(f"📉 Conf capped 75% [R/R={rr}]: {current_conf}% → 75%")
                analysis["ai_confidence_score"] = 75.0

        # ── 5. Distance sanity: SL/TP لا يكونوا قريبين جداً (< 0.01%) ────
        price_ref = entry
        min_dist_pct = 0.0001  # 0.01%
        if sl_dist / price_ref < min_dist_pct:
            return self._reject_signal(analysis, "SL_TOO_CLOSE")

        # ── 6. OB conflict: support.max < resistance.min ─────────────────
        ob = analysis.get("order_blocks", {})
        bull_obs = ob.get("bullish_obs", [])
        bear_obs = ob.get("bearish_obs", [])
        if bull_obs and bear_obs:
            try:
                support_max    = max(float(o.get("high", 0)) for o in bull_obs if isinstance(o, dict))
                resistance_min = min(float(o.get("low",  0)) for o in bear_obs if isinstance(o, dict))
                if support_max > 0 and resistance_min > 0 and support_max > resistance_min:
                    logger.warning(
                        f"⛔ OB Conflict [{rec}]: support.max={support_max} > resistance.min={resistance_min} → WAIT"
                    )
                    return self._reject_signal(analysis, "OB_OVERLAP_CONFLICT")
            except Exception:
                pass

        # ── 7. Wyckoff consistency ────────────────────────────────────────
        wyckoff_phase = (
            analysis.get("wyckoff", {}).get("phase")
            or analysis.get("wyckoff_phase", "")
            or ""
        ).upper()

        if wyckoff_phase:
            is_accumulation = any(w in wyckoff_phase for w in ("ACCUMULATION", "SPRING", "REACCUMULATION"))
            is_distribution  = any(w in wyckoff_phase for w in ("DISTRIBUTION", "UPTHRUST", "REDISTRIBUTION"))

            if is_distribution and rec == "BUY":
                logger.warning(f"⛔ Wyckoff conflict: phase={wyckoff_phase} vs BUY → downgrade")
                current_conf = float(analysis.get("ai_confidence_score") or 0)
                analysis["ai_confidence_score"] = min(current_conf, 55.0)
                if current_conf >= 65:
                    return self._reject_signal(analysis, "WYCKOFF_DISTRIBUTION_VS_BUY")

            if is_accumulation and rec == "SELL":
                logger.warning(f"⛔ Wyckoff conflict: phase={wyckoff_phase} vs SELL → downgrade")
                current_conf = float(analysis.get("ai_confidence_score") or 0)
                analysis["ai_confidence_score"] = min(current_conf, 55.0)
                if current_conf >= 65:
                    return self._reject_signal(analysis, "WYCKOFF_ACCUMULATION_VS_SELL")

        # ── 8. Premium/Discount zone consistency ─────────────────────────
        pd_zone = (
            analysis.get("premium_discount", {}).get("zone")
            if isinstance(analysis.get("premium_discount"), dict)
            else str(analysis.get("premium_discount", ""))
        ).upper() if analysis.get("premium_discount") else ""

        if pd_zone:
            in_premium  = "PREMIUM"  in pd_zone
            in_discount = "DISCOUNT" in pd_zone
            if in_premium and rec == "BUY":
                logger.warning(f"⛔ Zone conflict: PREMIUM zone + BUY → conf penalty")
                current_conf = float(analysis.get("ai_confidence_score") or 0)
                analysis["ai_confidence_score"] = min(current_conf, 60.0)
            if in_discount and rec == "SELL":
                logger.warning(f"⛔ Zone conflict: DISCOUNT zone + SELL → conf penalty")
                current_conf = float(analysis.get("ai_confidence_score") or 0)
                analysis["ai_confidence_score"] = min(current_conf, 60.0)

        logger.info(
            f"✅ Trade Validation PASSED [{rec}]: "
            f"entry={entry} sl={sl} tp1={tp1} rr={rr}"
        )
        return analysis

    def _reject_signal(self, analysis: dict, reason: str) -> dict:
        """رفض الإشارة وتحويلها لـ WAIT مع تسجيل السبب"""
        rec = analysis.get("recommendation", "?")
        logger.warning(f"🚫 Signal REJECTED [{rec}] → WAIT | reason={reason}")
        analysis["recommendation"]      = "WAIT"
        analysis["signal_type"]         = "WAIT"
        analysis["ai_confidence_score"] = min(
            float(analysis.get("ai_confidence_score") or 0), 45.0
        )
        analysis["validation_rejected"] = True
        analysis["rejection_reason"]    = reason
        analysis["levels"]              = {}
        analysis["entry_zones"]         = []
        analysis["stop_loss_zone"]      = None
        analysis["take_profit_zones"]   = []
        return analysis

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
